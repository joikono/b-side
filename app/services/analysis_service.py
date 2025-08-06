"""Service for MIDI analysis operations."""

import os
import time
from typing import Tuple, Dict, Any, List
from fastapi import UploadFile

from ..config import settings
from ..core.exceptions import AnalysisFailedError, InvalidMidiFileError
from ..utils.helpers import save_upload_to_temp, cleanup_temp_file, get_base_filename, ensure_directories_exist
from ..utils.logging import get_logger

logger = get_logger(__name__)

# Import existing analysis modules from project root
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from chord_analyzer import analyze_chord_progression_with_stretching
    from melody_analyzer2 import force_exactly_8_chords_analysis, create_track_visualization, create_four_way_visualization, extract_melody_with_timing
    from chord_or_melody import detect_midi_type, detect_midi_type_with_stretching_and_viz
    ANALYSIS_MODULES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Analysis modules not available: {e}. Analysis service running in limited mode.")
    ANALYSIS_MODULES_AVAILABLE = False
    
    # Create mock functions for testing
    def detect_midi_type(*args, **kwargs):
        return "melody"
    
    def detect_midi_type_with_stretching_and_viz(*args, **kwargs):
        return "melody", None
    
    def analyze_chord_progression_with_stretching(*args, **kwargs):
        return ["C", "F", "G", "C"], []
    
    def force_exactly_8_chords_analysis(*args, **kwargs):
        return "C", [["C", "F", "G", "C", "Am", "F", "G", "C"]] * 4, [0.8] * 4, [], []
    
    def create_track_visualization(*args, **kwargs):
        pass
    
    def create_four_way_visualization(*args, **kwargs):
        pass
    
    def extract_melody_with_timing(*args, **kwargs):
        return [], []


class AnalysisService:
    """Service for handling MIDI analysis operations."""
    
    def __init__(self):
        ensure_directories_exist(settings.generated_visualizations_dir)
    
    async def detect_midi_type(self, file: UploadFile) -> Dict[str, Any]:
        """Detect if uploaded MIDI is chord progression or melody."""
        temp_path = await save_upload_to_temp(file)
        
        try:
            midi_type = detect_midi_type(temp_path)
            return {
                "filename": file.filename,
                "type": midi_type,
                "message": f"Detected as {midi_type}"
            }
        except Exception as e:
            logger.error(f"MIDI type detection failed for {file.filename}: {e}")
            raise AnalysisFailedError(f"Analysis failed: {str(e)}")
        finally:
            cleanup_temp_file(temp_path)
    
    async def analyze_chord_progression(
        self, 
        file: UploadFile, 
        segment_size: int = None, 
        tolerance_beats: float = None
    ) -> Dict[str, Any]:
        """Analyze chord progression from uploaded MIDI."""
        segment_size = segment_size or settings.default_segment_size
        tolerance_beats = tolerance_beats or settings.default_tolerance_beats
        
        temp_path = await save_upload_to_temp(file)
        
        try:
            progression, segments = analyze_chord_progression_with_stretching(
                temp_path, 
                segment_size=segment_size, 
                tolerance_beats=tolerance_beats
            )
            
            return {
                "filename": file.filename,
                "chord_progression": progression,
                "segments": len(segments),
                "analysis_type": "chord_progression"
            }
        except Exception as e:
            logger.error(f"Chord analysis failed for {file.filename}: {e}")
            raise AnalysisFailedError(f"Chord analysis failed: {str(e)}")
        finally:
            cleanup_temp_file(temp_path)
    
    async def analyze_melody_with_harmonization(
        self, 
        file: UploadFile,
        segment_size: int = None,
        tolerance_beats: float = None
    ) -> Dict[str, Any]:
        """Comprehensive melody analysis with harmonization and visualization."""
        segment_size = segment_size or settings.default_segment_size
        tolerance_beats = tolerance_beats or settings.default_tolerance_beats
        
        temp_path = await save_upload_to_temp(file)
        
        try:
            logger.info("🎵 STEP 1: CHORD/MELODY DETECTION")
            
            # Detect type with visualization
            detected_type, chord_melody_viz_file = detect_midi_type_with_stretching_and_viz(
                temp_path, 
                output_dir=settings.generated_visualizations_dir
            )
            
            logger.info(f"🎵 STEP 2: {detected_type.upper()} ANALYSIS + VISUALIZATION")
            
            timestamp = int(time.time())
            base_name = get_base_filename(file.filename)
            viz_success = False
            viz_filename = None
            
            if detected_type == "chord_progression":
                # Analyze as chord progression
                result = analyze_chord_progression_with_stretching(
                    temp_path,
                    segment_size=segment_size,
                    tolerance_beats=tolerance_beats
                )
                
                logger.info(f"✅ Chord progression analysis complete!")
                logger.info(f"   Detected progression: {' → '.join(result['chord_progression'])}")
                
                viz_filename = result.get('visualization_file')
                viz_success = viz_filename is not None
            else:
                # Use forced 8-chord analysis for melody
                key, progressions, confidences, segments, processed_notes = force_exactly_8_chords_analysis(temp_path)
                
                simple_prog, folk_prog, bass_prog, phrase_prog = progressions
                simple_conf, folk_conf, bass_conf, phrase_conf = confidences
                
                logger.info(f"🎼 Melody analysis complete - Key: {key}")
                logger.info(f"🎵 8-Chord Progressions Generated:")
                logger.info(f"  Simple: {' → '.join(simple_prog)}")
                logger.info(f"  Folk: {' → '.join(folk_prog)}")
                logger.info(f"  Bass: {' → '.join(bass_prog)}")
                logger.info(f"  Phrase: {' → '.join(phrase_prog)}")
                
                # Generate melody visualization
                viz_filename = f"{base_name}_analysis_{timestamp}.png"
                
                try:
                    logger.info("📊 Generating melody visualization...")
                    create_track_visualization(
                        temp_path,
                        segments,
                        bass_prog,
                        phrase_prog,
                        key,
                        processed_notes,
                        viz_filename
                    )
                    viz_success = True
                    logger.info("✅ Melody visualization successful!")
                except Exception as e:
                    logger.error(f"❌ Track visualization failed: {e}")
                    viz_success = False
                
                # Package melody results
                result = {
                    'analysis_type': 'melody_harmonization',
                    'key': key,
                    'chord_progression': simple_prog,
                    'harmonizations': {
                        'simple_pop': {'progression': simple_prog, 'confidence': simple_conf},
                        'folk_acoustic': {'progression': folk_prog, 'confidence': folk_conf},
                        'bass_foundation': {'progression': bass_prog, 'confidence': bass_conf},
                        'phrase_foundation': {'progression': phrase_prog, 'confidence': phrase_conf}
                    },
                    'segments': segments,
                    'processed_notes': processed_notes,
                    'forced_8_chords': True,
                    'visualization_file': viz_filename if viz_success else None
                }
            
            logger.info("🎵 ANALYSIS COMPLETE - RETURNING RESULTS")
            
            # Build unified response
            response = {
                "filename": file.filename,
                "detected_type": detected_type,
                "analysis_path": "chord_progression" if detected_type == "chord_progression" else "melody_harmonization",
                
                # Chord/Melody detection results
                "chord_melody_detection": {
                    "detected_type": detected_type,
                    "visualization_file": chord_melody_viz_file,
                    "download_url": f"/download/viz/{chord_melody_viz_file}" if chord_melody_viz_file else None
                },
                
                # Main analysis results
                "analysis_type": result.get('analysis_type', 'unknown'),
                "key": result.get('key', 'C'),
                "chord_progression": result.get('chord_progression', []),
                
                # Main visualization
                "visualization": {
                    "success": viz_success,
                    "file": viz_filename if viz_success else None,
                    "download_url": f"/download/viz/{viz_filename}" if viz_success else None,
                    "type": "chord_progression" if detected_type == "chord_progression" else "four_way_harmonization"
                }
            }
            
            # Add harmonizations if melody path was taken
            if detected_type != "chord_progression" and 'harmonizations' in result:
                response["harmonizations"] = result['harmonizations']
                response["segments"] = len(result.get('segments', []))
                response["forced_8_chords"] = result.get('forced_8_chords', False)
            
            # Add chord analysis specific data if chord path was taken
            if detected_type == "chord_progression":
                response["chord_analysis"] = {
                    "segments": result.get('segments', []),
                    "timing_adjustments": result.get('timing_adjustments', []),
                    "tolerance_used": result.get('tolerance_used', False)
                }
            
            return response
            
        except Exception as e:
            logger.error(f"MIDI analysis error for {file.filename}: {e}")
            raise AnalysisFailedError(f"MIDI analysis failed: {str(e)}")
        finally:
            cleanup_temp_file(temp_path)
    
    async def analyze_melody_with_four_way_viz(
        self,
        file: UploadFile,
        harmonization_style: str = "simple_pop",
        segment_size: int = None,
        tolerance_beats: float = None
    ) -> Dict[str, Any]:
        """Analyze melody and create four-way visualization."""
        segment_size = segment_size or settings.default_segment_size
        tolerance_beats = tolerance_beats or settings.default_tolerance_beats
        
        temp_path = await save_upload_to_temp(file)
        
        try:
            # Analyze melody with forced 8-chord analysis
            logger.info(f"🎵 Analyzing melody for chord progression: {file.filename}")
            key, progressions, confidences, segments, _ = force_exactly_8_chords_analysis(temp_path)
            
            simple_prog, folk_prog, bass_prog, phrase_prog = progressions
            simple_conf, folk_conf, bass_conf, phrase_conf = confidences
            
            # Map harmonization styles
            style_map = {
                "simple_pop": (simple_prog, simple_conf),
                "folk_acoustic": (folk_prog, folk_conf),
                "bass_foundation": (bass_prog, bass_conf),
                "phrase_foundation": (phrase_prog, phrase_conf)
            }
            
            if harmonization_style not in style_map:
                raise InvalidMidiFileError(f"Invalid harmonization style: {harmonization_style}")
            
            selected_progression, selected_confidence = style_map[harmonization_style]
            
            logger.info(f"🎼 Selected {harmonization_style}: {' → '.join(selected_progression)}")
            logger.info(f"🎯 Key: {key}, Confidence: {selected_confidence:.1f}%")
            
            # Create four-way visualization
            timestamp = int(time.time())
            base_name = get_base_filename(file.filename)
            viz_filename = f"{base_name}_{harmonization_style}_{timestamp}_four_ways.png"
            viz_path = os.path.join(settings.generated_visualizations_dir, viz_filename)
            
            logger.info("📊 Creating four-way chord progression visualization...")
            try:
                # Extract notes for visualization
                extracted_notes, _ = extract_melody_with_timing(temp_path, tolerance_beats=tolerance_beats)
                
                # Use existing four-way visualization function
                create_four_way_visualization(
                    temp_path,
                    segments,
                    bass_prog,
                    phrase_prog,
                    key,
                    extracted_notes,
                    viz_path
                )
                viz_success = True
                logger.info("✅ Four-way visualization successful!")
            except Exception as e:
                logger.error(f"Visualization error: {e}")
                viz_success = False
            
            return {
                "success": True,
                "message": "MIDI melody analyzed with FORCED 8-chord rule and visualization",
                "filename": file.filename,
                "key": key,
                "selected_harmonization": {
                    "style": harmonization_style,
                    "progression": selected_progression,
                    "confidence": selected_confidence
                },
                "all_harmonizations": {
                    "simple_pop": {"progression": simple_prog, "confidence": simple_conf},
                    "folk_acoustic": {"progression": folk_prog, "confidence": folk_conf},
                    "bass_foundation": {"progression": bass_prog, "confidence": bass_conf},
                    "phrase_foundation": {"progression": phrase_prog, "confidence": phrase_conf}
                },
                "visualization": {
                    "success": viz_success,
                    "file": viz_filename if viz_success else None,
                    "path": viz_path if viz_success else None,
                    "download_url": f"/download/viz/{viz_filename}" if viz_success else None
                },
                "analysis_details": {
                    "segments": len(segments),
                    "segment_size": segment_size,
                    "tolerance_beats": tolerance_beats,
                    "forced_8_chords": True
                }
            }
            
        except Exception as e:
            logger.error(f"MIDI melody analysis error for {file.filename}: {e}")
            raise AnalysisFailedError(f"MIDI melody analysis failed: {str(e)}")
        finally:
            cleanup_temp_file(temp_path)


# Global analysis service instance
analysis_service = AnalysisService()