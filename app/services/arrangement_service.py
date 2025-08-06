"""Service for arrangement generation operations."""

import os
import time
from typing import List, Dict, Any, Tuple
from fastapi import UploadFile

from ..config import settings
from ..core.exceptions import ArrangementGenerationError, ModelNotLoadedError
from ..core.model_manager import model_service
from ..utils.helpers import save_upload_to_temp, cleanup_temp_file, get_base_filename, ensure_directories_exist
from ..utils.logging import get_logger
from ..models.schemas import ArrangementRequest

logger = get_logger(__name__)

# Import existing modules from project root
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Try importing optional analysis modules
try:
    from arrangement_generator import generate_arrangement_from_chords
    from chord_or_melody import detect_midi_type
    from chord_analyzer import analyze_chord_progression_with_stretching
    from melody_analyzer2 import force_exactly_8_chords_analysis
    ANALYSIS_MODULES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Analysis modules not available: {e}. Arrangement service running in limited mode.")
    ANALYSIS_MODULES_AVAILABLE = False
    
    # Create mock functions
    def generate_arrangement_from_chords(*args, **kwargs):
        raise ArrangementGenerationError("Magenta not available - cannot generate arrangements")
    
    def detect_midi_type(*args, **kwargs):
        return "unknown"
    
    def analyze_chord_progression_with_stretching(*args, **kwargs):
        return [], []
    
    def force_exactly_8_chords_analysis(*args, **kwargs):
        return "C", [["C", "F", "G", "C", "Am", "F", "G", "C"]] * 4, [0.5] * 4, [], []


class ArrangementService:
    """Service for handling arrangement generation operations."""
    
    def __init__(self):
        ensure_directories_exist(settings.generated_arrangements_dir)
    
    async def generate_from_chord_progression(self, request: ArrangementRequest) -> Dict[str, Any]:
        """Generate arrangement from chord progression."""
        if not model_service.is_loaded():
            raise ModelNotLoadedError("Models not loaded")
        
        if not request.chord_progression:
            raise ArrangementGenerationError("Chord progression cannot be empty")
        
        try:
            # Generate unique filename
            timestamp = int(time.time())
            output_file = os.path.join(settings.generated_arrangements_dir, f"arrangement_{timestamp}.mid")
            
            # Generate arrangement
            result_file = generate_arrangement_from_chords(
                chord_progression=request.chord_progression,
                bpm=request.bpm,
                bass_complexity=request.bass_complexity,
                drum_complexity=request.drum_complexity,
                hi_hat_divisions=request.hi_hat_divisions,
                snare_beats=tuple(request.snare_beats),
                output_file=output_file,
                bass_rnn=model_service.get_bass_rnn(),
                drum_rnn=model_service.get_drum_rnn()
            )
            
            return {
                "message": "Arrangement generated successfully!",
                "chord_progression": request.chord_progression,
                "settings": {
                    "bpm": request.bpm,
                    "bass_complexity": request.bass_complexity,
                    "drum_complexity": request.drum_complexity
                },
                "output_file": result_file,
                "download_url": f"/download/{os.path.basename(result_file)}"
            }
            
        except Exception as e:
            logger.error(f"Arrangement generation failed: {e}")
            raise ArrangementGenerationError(f"Arrangement generation failed: {str(e)}")
    
    async def full_analysis_and_generation(
        self,
        file: UploadFile,
        harmonization_style: str = "simple_pop",
        bpm: int = None,
        bass_complexity: int = 1,
        drum_complexity: int = 1
    ) -> Dict[str, Any]:
        """Complete workflow: analyze MIDI → detect type → generate arrangement."""
        if not model_service.is_loaded():
            raise ModelNotLoadedError("Models not loaded")
        
        bpm = bpm or settings.default_bpm
        temp_path = await save_upload_to_temp(file)
        
        try:
            # Step 1: Detect type
            midi_type = detect_midi_type(temp_path)
            
            # Step 2: Analyze based on type
            if midi_type == "chord_progression":
                progression, segments = analyze_chord_progression_with_stretching(temp_path)
                chord_list = progression
                analysis_data = {"type": "chord_progression", "progression": progression}
            else:
                # Use forced 8-chord analysis for melody
                key, progressions, confidences, segments, _ = force_exactly_8_chords_analysis(temp_path)
                
                # Select harmonization style
                style_map = {
                    "simple_pop": 0,
                    "folk_acoustic": 1, 
                    "bass_foundation": 2,
                    "phrase_foundation": 3
                }
                
                style_index = style_map.get(harmonization_style, 0)
                chord_list = progressions[style_index]
                
                analysis_data = {
                    "type": "melody",
                    "key": key,
                    "selected_style": harmonization_style,
                    "all_harmonizations": dict(zip(style_map.keys(), progressions))
                }
            
            # Step 3: Generate arrangement
            timestamp = int(time.time())
            base_name = get_base_filename(file.filename)
            output_file = os.path.join(settings.generated_arrangements_dir, f"{base_name}_arrangement_{timestamp}.mid")
            
            result_file = generate_arrangement_from_chords(
                chord_progression=chord_list,
                bpm=bpm,
                bass_complexity=bass_complexity,
                drum_complexity=drum_complexity,
                hi_hat_divisions=2,
                snare_beats=(2, 4),
                output_file=output_file,
                bass_rnn=model_service.get_bass_rnn(),
                drum_rnn=model_service.get_drum_rnn()
            )
            
            return {
                "message": "Full analysis and arrangement complete!",
                "original_file": file.filename,
                "analysis": analysis_data,
                "chord_progression": chord_list,
                "arrangement_file": result_file,
                "download_url": f"/download/{os.path.basename(result_file)}"
            }
            
        except Exception as e:
            logger.error(f"Full analysis and generation failed for {file.filename}: {e}")
            raise ArrangementGenerationError(f"Full analysis failed: {str(e)}")
        finally:
            cleanup_temp_file(temp_path)


# Global arrangement service instance
arrangement_service = ArrangementService()