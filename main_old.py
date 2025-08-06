# main.py - Streamlined FastAPI Backend with FORCED 8-CHORD Analysis

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn
import os
import tempfile
import time
import note_seq
from typing import List, Optional, Dict, Any
import logging
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from mido import MidiFile, MidiTrack, Message, MetaMessage
import requests
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import your existing modules
from model_manager import MagentaModelManager
from chord_analyzer import analyze_chord_progression_with_stretching
from melody_analyzer2 import create_four_way_visualization, force_exactly_8_chords_analysis, create_track_visualization
from chord_or_melody import detect_midi_type
from arrangement_generator import generate_arrangement_from_chords
from chord_or_melody import detect_midi_type_with_stretching_and_viz


from pydantic import BaseModel

# Pydantic models for requests
class ArrangementRequest(BaseModel):
    chord_progression: List[str]
    bpm: int = 100
    bass_complexity: int = 1
    drum_complexity: int = 1
    hi_hat_divisions: int = 2
    snare_beats: List[int] = [2, 4]

class VoiceTranscriptionRequest(BaseModel):
    audio_blob: str  # Base64 encoded audio data

class ChatCompletionRequest(BaseModel):
    command: str
    has_current_analysis: bool = False
    analysis_context: Optional[Dict[str, Any]] = None

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model manager - loaded once on startup
model_manager = None
bass_rnn = None
drum_rnn = None

app = FastAPI(
    title="MIDI Analysis API",
    description="Streamlined MIDI analysis with FORCED 8-chord rule for frontend uploads",
    version="2.1.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def load_models():
    """Load Magenta models ONCE on startup."""
    global model_manager, bass_rnn, drum_rnn

    logger.info("🚀 MIDI Analysis API starting up...")
    logger.info("🔄 Loading Magenta models (this happens ONCE)...")

    try:
        model_manager = MagentaModelManager()
        bass_rnn = model_manager.bass_rnn
        drum_rnn = model_manager.drum_rnn

        logger.info("✅ Models loaded! MIDI Analysis API ready with FORCED 8-chord rule!")

    except Exception as e:
        logger.error(f"❌ Failed to load models: {e}")
        raise e

@app.get("/")
async def root():
    """Health check and welcome message"""
    return {
        "message": "🎹 MIDI Analysis API (Frontend-Only MIDI + Forced 8-Chord Rule)",
        "models_loaded": model_manager.is_loaded() if model_manager else False,
        "version": "2.1.0",
        "features": ["Frontend MIDI Recording", "Forced 8-Chord Analysis", "Arrangement Generation"]
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "models_loaded": model_manager.is_loaded() if model_manager else False,
        "bass_model": bass_rnn is not None,
        "drum_model": drum_rnn is not None,
        "architecture": "frontend_only_midi_forced_8_chords"
    }

# ============================================================================
# CORE ANALYSIS ENDPOINTS (Works with frontend-uploaded MIDI files)
# ============================================================================

@app.post("/analyze/type")
async def analyze_midi_type(file: UploadFile = File(...)):
    """Detect if uploaded MIDI is chord progression or melody"""
    if not file.filename.endswith(('.mid', '.midi')):
        raise HTTPException(status_code=400, detail="File must be a MIDI file (.mid or .midi)")

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mid') as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name

    try:
        # Analyze the type
        midi_type = detect_midi_type(temp_path)

        return {
            "filename": file.filename,
            "type": midi_type,
            "message": f"Detected as {midi_type}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

@app.post("/analyze/chords")
async def analyze_chords(
    file: UploadFile = File(...),
    segment_size: int = 2,
    tolerance_beats: float = 0.15
):
    """Analyze chord progression from uploaded MIDI"""
    if not file.filename.endswith(('.mid', '.midi')):
        raise HTTPException(status_code=400, detail="File must be a MIDI file")

    with tempfile.NamedTemporaryFile(delete=False, suffix='.mid') as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name

    try:
        # Analyze chords
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
        raise HTTPException(status_code=500, detail=f"Chord analysis failed: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

@app.post("/analyze/melody")
async def analyze_melody(
    file: UploadFile = File(...),
    segment_size: int = 2,
    tolerance_beats: float = 0.15
):
    if not file.filename.endswith(('.mid', '.midi')):
        raise HTTPException(status_code=400, detail="File must be a MIDI file")

    # Ensure output directory exists for visualizations
    os.makedirs("generated_visualizations", exist_ok=True)

    with tempfile.NamedTemporaryFile(delete=False, suffix='.mid') as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name

    try:
        print("=" * 80)
        print("🎵 STEP 1: CHORD/MELODY DETECTION")
        print("=" * 80)
                
        # Detect if it's a chord progression or melody (with stretching and visualization)
        detected_type, chord_melody_viz_file = detect_midi_type_with_stretching_and_viz(
            temp_path, 
            output_dir="generated_visualizations"
        )
                
        print("\n" + "=" * 80)
        print(f"🎵 STEP 2: {detected_type.upper()} ANALYSIS + VISUALIZATION")
        print("=" * 80)
        
        # Initialize visualization variables
        timestamp = int(time.time())
        base_name = os.path.splitext(file.filename or "uploaded")[0]
        viz_success = False
        
        # Fix the splitext type error by ensuring we have a string
        filename = file.filename if file.filename is not None else "uploaded"
        base_name = os.path.splitext(filename)[0]
        viz_filename = None
        
        # BRANCHING LOGIC: Different analysis based on detection
        if detected_type == "chord_progression":
            # Analyze as chord progression with stretching (includes visualization)
            result = analyze_chord_progression_with_stretching(
                temp_path,
                segment_size=segment_size,
                tolerance_beats=tolerance_beats
            )
            
            print(f"✅ Chord progression analysis complete!")
            print(f"   Detected progression: {' → '.join(result['chord_progression'])}")
            
            # Extract visualization info from chord analysis result
            viz_filename = result.get('visualization_file')
            viz_success = viz_filename is not None
            if viz_success:
                print(f"✅ Chord progression visualization: {viz_filename}")
            
        else:  # detected_type == "melody" or "unknown"
            # Use forced 8-chord analysis for melody + generate visualization
            key, progressions, confidences, segments, processed_notes = force_exactly_8_chords_analysis(temp_path)

            simple_prog, folk_prog, bass_prog, phrase_prog = progressions
            simple_conf, folk_conf, bass_conf, phrase_conf = confidences

            print(f"🎼 Melody analysis complete - Key: {key}")
            print(f"🎵 8-Chord Progressions Generated:")
            print(f"  Simple: {' → '.join(simple_prog)}")
            print(f"  Folk: {' → '.join(folk_prog)}")
            print(f"  Bass: {' → '.join(bass_prog)}")
            print(f"  Phrase: {' → '.join(phrase_prog)}")
            
            # Generate melody harmonization visualization
            viz_filename = f"{base_name}_analysis_{timestamp}.png"
            
            try:
                print(f"📊 Generating melody visualization...")
                
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
                print(f"✅ Melody visualization successful!")
            except Exception as e:
                print(f"❌ Track visualization failed: {e}")
                viz_success = False
            
            # Package melody results in same format as chord results
            result = {
                'analysis_type': 'melody_harmonization',
                'key': key,
                'chord_progression': simple_prog,  # Use simple as primary
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

        print("\n" + "=" * 80)
        print("🎵 ANALYSIS COMPLETE - RETURNING RESULTS")
        print("=" * 80)

        # Return unified response format
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
            
            # Main analysis results (format depends on path taken)
            "analysis_type": result.get('analysis_type', 'unknown'),
            "key": result.get('key', 'C'),
            "chord_progression": result.get('chord_progression', []),
            
            # Main visualization (now handled in step 2)
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
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ MIDI analysis error: {error_details}")
        raise HTTPException(status_code=500, detail=f"MIDI analysis failed: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

# ============================================================================
# ARRANGEMENT GENERATION
# ============================================================================

@app.post("/generate/arrangement")
async def generate_arrangement(request: ArrangementRequest):
    """Generate arrangement from chord progression"""
    global bass_rnn, drum_rnn

    if not bass_rnn or not drum_rnn:
        raise HTTPException(status_code=503, detail="Models not loaded")

    if not request.chord_progression:
        raise HTTPException(status_code=400, detail="Chord progression cannot be empty")

    try:
        # Ensure output directory exists
        output_dir = "astro-midi-app/public/generated_arrangements"
        os.makedirs(output_dir, exist_ok=True)

        # Generate unique filename
        timestamp = int(time.time())
        output_file = os.path.join(output_dir, f"arrangement_{timestamp}.mid")

        # Generate arrangement
        result_file = generate_arrangement_from_chords(
            chord_progression=request.chord_progression,
            bpm=request.bpm,
            bass_complexity=request.bass_complexity,
            drum_complexity=request.drum_complexity,
            hi_hat_divisions=request.hi_hat_divisions,
            snare_beats=tuple(request.snare_beats),
            output_file=output_file,
            bass_rnn=bass_rnn,
            drum_rnn=drum_rnn
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
        raise HTTPException(status_code=500, detail=f"Arrangement generation failed: {str(e)}")

@app.post("/fix-midi-duration")
async def fix_midi_duration(file: UploadFile = File(...)):
    """Force MIDI file to exactly 9.6 seconds - extend short files, truncate long files"""
    try:
        # Save uploaded file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mid') as temp_input:
            temp_input.write(await file.read())
            temp_input_path = temp_input.name
        
        # Load with mido
        midi = MidiFile(temp_input_path)
        
        # Calculate exact target in ticks
        ticks_per_beat = midi.ticks_per_beat or 480
        target_ticks = int(9.6 * 100 * ticks_per_beat / 60)  # 9.6s at 100 BPM
        
        print(f"🎯 Target: {target_ticks} ticks for 9.6s at 100 BPM")
        print(f"🎵 Original MIDI Type: {midi.type}, Tracks: {len(midi.tracks)}")
        
        if len(midi.tracks) == 0:
            raise HTTPException(status_code=400, detail="MIDI file has no tracks")
        
        # STEP 1: Process user's track with precise timing control
        original_track = midi.tracks[0]
        
        # Analyze all messages and their absolute timing
        processed_messages = []
        current_ticks = 0
        
        for msg in original_track:
            current_ticks += msg.time
            
            if msg.type == 'end_of_track':
                continue  # Skip end_of_track, we'll add it later
            
            # 🔑 TRUNCATION LOGIC: Only include events that start before 9.6s
            if current_ticks <= target_ticks:
                processed_messages.append({
                    'message': msg.copy(),
                    'absolute_time': current_ticks,
                    'delta_time': msg.time
                })
                
                # 🔑 SPECIAL CASE: If this is a note_on, ensure corresponding note_off at 9.6s max
                if hasattr(msg, 'type') and msg.type == 'note_on' and hasattr(msg, 'note'):
                    # Look ahead for the corresponding note_off
                    temp_ticks = current_ticks
                    found_note_off = False
                    
                    for future_msg in original_track[original_track.index(msg) + 1:]:
                        temp_ticks += future_msg.time
                        
                        if (hasattr(future_msg, 'type') and future_msg.type == 'note_off' and
                            hasattr(future_msg, 'note') and future_msg.note == msg.note and
                            hasattr(future_msg, 'channel') and future_msg.channel == msg.channel):
                            
                            if temp_ticks > target_ticks:
                                # Add truncated note_off at exactly 9.6s
                                note_off_time = target_ticks
                                processed_messages.append({
                                    'message': Message('note_off', channel=msg.channel, 
                                                     note=msg.note, velocity=0),
                                    'absolute_time': note_off_time,
                                    'delta_time': 0  # Will be calculated later
                                })
                                print(f"🔪 Truncated note {msg.note} to end at 9.6s")
                            found_note_off = True
                            break
            else:
                print(f"🔪 Truncated event at {current_ticks} ticks (beyond 9.6s)")
        
        original_duration = current_ticks
        print(f"🎵 Original duration: {original_duration} ticks ({original_duration * 60 / (100 * ticks_per_beat):.2f}s)")
        
        # STEP 2: Sort messages by absolute time and rebuild with correct delta times
        processed_messages.sort(key=lambda x: x['absolute_time'])
        
        # Create clean track with corrected timing
        clean_track = MidiTrack()
        last_time = 0
        
        for msg_data in processed_messages:
            delta = msg_data['absolute_time'] - last_time
            msg_data['message'].time = delta
            clean_track.append(msg_data['message'])
            last_time = msg_data['absolute_time']
        
        # STEP 3: Handle final timing
        final_track_duration = last_time if processed_messages else 0
        
        if final_track_duration < target_ticks:
            # Need to extend
            remaining_ticks = target_ticks - final_track_duration
            clean_track.append(Message('control_change', channel=15, control=7, value=0, 
                                     time=remaining_ticks))
            print(f"🔧 Extended by {remaining_ticks} ticks to reach 9.6s")
        elif final_track_duration > target_ticks:
            print(f"🔪 Truncated from {final_track_duration} to {target_ticks} ticks")
        else:
            print(f"✅ Duration already exactly {target_ticks} ticks")
        
        # Add final end_of_track
        clean_track.append(MetaMessage('end_of_track', time=0))
        
        # STEP 4: Create final MIDI file
        final_midi = MidiFile(type=0, ticks_per_beat=midi.ticks_per_beat)
        final_midi.tracks.append(clean_track)
        
        # Save final file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mid') as temp_output:
            temp_output_path = temp_output.name
        
        final_midi.save(temp_output_path)
        os.unlink(temp_input_path)
        
        action = "extended" if original_duration < target_ticks else "truncated" if original_duration > target_ticks else "maintained"
        print(f"🎯 Successfully {action} MIDI to exactly 9.6s duration")
        
        return FileResponse(
            temp_output_path,
            media_type='audio/midi',
            filename='duration_fixed_clean.mid'
        )
        
    except Exception as e:
        print(f"❌ Duration fix error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
# ============================================================================
# COMPLETE WORKFLOW ENDPOINT
# ============================================================================

@app.post("/full-analysis")
async def full_analysis_and_generation(
    file: UploadFile = File(...),
    harmonization_style: Optional[str] = "simple_pop",
    bpm: int = 100,
    bass_complexity: int = 1,
    drum_complexity: int = 1
):
    """Complete workflow: analyze MIDI → detect type → generate arrangement"""
    if not file.filename.endswith(('.mid', '.midi')):
        raise HTTPException(status_code=400, detail="File must be a MIDI file")

    with tempfile.NamedTemporaryFile(delete=False, suffix='.mid') as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name

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
            key, progressions, confidences, segments, _ = force_exactly_8_chords_analysis(temp_path)  # Added _ for notes

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
        output_dir = "astro-midi-app/public/generated_arrangements"
        os.makedirs(output_dir, exist_ok=True)

        timestamp = int(time.time())
        base_name = os.path.splitext(file.filename)[0]
        output_file = os.path.join(output_dir, f"{base_name}_arrangement_{timestamp}.mid")

        result_file = generate_arrangement_from_chords(
            chord_progression=chord_list,
            bpm=bpm,
            bass_complexity=bass_complexity,
            drum_complexity=drum_complexity,
            hi_hat_divisions=2,
            snare_beats=(2, 4),
            output_file=output_file,
            bass_rnn=bass_rnn,
            drum_rnn=drum_rnn
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
        raise HTTPException(status_code=500, detail=f"Full analysis failed: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

# ============================================================================
# FILE DOWNLOAD ENDPOINTS
# ============================================================================

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download generated MIDI files"""
    file_path = os.path.join("astro-midi-app/public/generated_arrangements", filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='audio/midi'
    )

@app.get("/download/viz/{filename}")
async def download_visualization(filename: str):
    """Download generated visualization files"""
    file_path = os.path.join("generated_visualizations", filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Visualization file not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='image/png'
    )

# ============================================================================
# OPTIONAL: Advanced Analysis with Visualization
# ============================================================================

@app.post("/analyze/melody-with-viz")
async def analyze_melody_with_visualization(
    file: UploadFile = File(...),
    harmonization_style: str = "simple_pop",
    segment_size: int = 2,
    tolerance_beats: float = 0.15
):
    """
    Analyze melody and create four-way visualization.
    Enhanced version of /analyze/melody with visualization.
    *** ENFORCES EXACTLY 8 CHORDS ***
    """
    if not file.filename.endswith(('.mid', '.midi')):
        raise HTTPException(status_code=400, detail="File must be a MIDI file")

    # Ensure output directory exists for visualizations
    os.makedirs("generated_visualizations", exist_ok=True)

    with tempfile.NamedTemporaryFile(delete=False, suffix='.mid') as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name

    try:
        # Analyze melody and get chord progressions using FORCED 8-chord analysis
        print(f"🎵 Analyzing melody for chord progression: {file.filename}")
        key, progressions, confidences, segments, _ = force_exactly_8_chords_analysis(temp_path)  # Added _ for notes

        simple_prog, folk_prog, bass_prog, phrase_prog = progressions
        simple_conf, folk_conf, bass_conf, phrase_conf = confidences

        # Map harmonization styles to progressions
        style_map = {
            "simple_pop": (simple_prog, simple_conf),
            "folk_acoustic": (folk_prog, folk_conf),
            "bass_foundation": (bass_prog, bass_conf),
            "phrase_foundation": (phrase_prog, phrase_conf)
        }

        if harmonization_style not in style_map:
            raise HTTPException(status_code=400, detail=f"Invalid harmonization style: {harmonization_style}")

        selected_progression, selected_confidence = style_map[harmonization_style]

        print(f"🎼 Selected {harmonization_style}: {' → '.join(selected_progression)}")
        print(f"🎯 Key: {key}, Confidence: {selected_confidence:.1f}%")

        # Create four-way visualization
        timestamp = int(time.time())
        base_name = os.path.splitext(file.filename)[0]
        viz_filename = f"{base_name}_{harmonization_style}_{timestamp}_four_ways.png"
        viz_path = os.path.join("generated_visualizations", viz_filename)
        
        print(f"📊 Creating four-way chord progression visualization...")
        try:
            # Extract notes for visualization
            from melody_analyzer2 import extract_melody_with_timing
            extracted_notes, _ = extract_melody_with_timing(temp_path, tolerance_beats=tolerance_beats)
            
            # Use existing four-way visualization function with extracted notes
            create_four_way_visualization(
                temp_path,           # midi_file
                segments,            # all_segments  
                bass_prog,           # bass_progression
                phrase_prog,         # phrase_progression
                key,                 # key
                extracted_notes,     # notes (now properly extracted)
                viz_path             # output_file
            )
            viz_success = True
        except Exception as e:
            print(f"Visualization error: {e}")
            viz_success = False

        # Prepare response
        response_data = {
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
                "simple_pop": {
                    "progression": simple_prog,
                    "confidence": simple_conf
                },
                "folk_acoustic": {
                    "progression": folk_prog,
                    "confidence": folk_conf
                },
                "bass_foundation": {
                    "progression": bass_prog,
                    "confidence": bass_conf
                },
                "phrase_foundation": {
                    "progression": phrase_prog,
                    "confidence": phrase_conf
                }
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

        return response_data

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ MIDI melody analysis error: {error_details}")
        raise HTTPException(status_code=500, detail=f"MIDI melody analysis failed: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

# ============================================================================
# OPENAI API ENDPOINTS (Secure backend proxy)
# ============================================================================

@app.post("/api/voice/transcribe")
async def transcribe_voice(request: VoiceTranscriptionRequest):
    """Transcribe voice audio using OpenAI Whisper API"""
    try:
        # Get OpenAI API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable not found")
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")        
        # TODO: Implement voice transcription
        # This would involve:
        # 1. Decode base64 audio data
        # 2. Send to OpenAI Whisper API
        # 3. Return transcription
        
        # For now, return a placeholder
        return {"transcription": "Voice transcription endpoint - implementation needed"}
        
    except Exception as e:
        logger.error(f"Voice transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@app.post("/api/chat/intent-classification")
async def classify_intent(request: ChatCompletionRequest):
    """Classify user intent using OpenAI Chat Completions API"""
    try:
        # Get OpenAI API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable not found")
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
                
        system_prompt = """You are a voice command classifier for a music application. 
        
        Analyze the user's voice command and return ONLY a JSON response with this structure:
        {
            "intent": "record|play|stop|generate|loop|toggle_recording|demo|chat",
            "confidence": 0.0-1.0,
            "parameters": {...any additional params...}
        }
    
        Intent definitions:
        - "record": User wants to start recording MIDI input (examples: "record", "capture", "start recording")
        - "play": User wants to play/hear music or arrangements (examples: "play", "jam", "hear it", "play it", "can you play", "let me hear", "start playing")
        - "stop": User wants to stop playback (examples: "stop", "pause", "cancel")
        - "generate": User wants to create/arrange music (examples: "generate", "arrange", "make music")
        - "loop": User wants to enable/toggle looping (examples: "loop", "repeat")
        - "toggle_recording": User wants to include/exclude their recording in playback (examples: "add my recording", "include my recording", "turn on my recording", "play my recording too", "remove my recording", "turn off my recording", "don't play my recording")
        - "demo": User is starting a demo or presentation (examples: "this is a demo", "we're demoing", "demo mode", "presenting to audience", "show the audience")
        - "chat": General conversation, questions, or unclear commands
    
        Examples:
        "let's record this" → {"intent": "record", "confidence": 0.9}
        "play that arrangement" → {"intent": "play", "confidence": 0.9}
        "add my recording to the mix" → {"intent": "toggle_recording", "confidence": 0.9}
        "include my recording" → {"intent": "toggle_recording", "confidence": 0.8}
        "turn off my recording" → {"intent": "toggle_recording", "confidence": 0.9}
        "play my recording with the arrangement" → {"intent": "toggle_recording", "confidence": 0.8}
        "this is a demo" → {"intent": "demo", "confidence": 0.9}
        "we're presenting this" → {"intent": "demo", "confidence": 0.8}
        "demo mode" → {"intent": "demo", "confidence": 0.9}"""

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.command}
            ],
            "max_tokens": 100,
            "temperature": 0.1
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30.0
        )
        
        if response.status_code != 200:
            error_text = response.text
            logger.error(f"OpenAI API returned status {response.status_code}: {error_text}")
            raise HTTPException(
                status_code=500, 
                detail=f"OpenAI API error {response.status_code}: {error_text}"
            )
        
        result = response.json()
        ai_response = result["choices"][0]["message"]["content"]
        
        # Parse the JSON response
        intent_data = json.loads(ai_response)
        return intent_data
            
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse OpenAI response as JSON: {e}")
        raise HTTPException(status_code=500, detail=f"Invalid response from AI model: {str(e)}")
    except requests.RequestException as e:
        logger.error(f"OpenAI API request failed: {e}")
        raise HTTPException(status_code=500, detail=f"OpenAI API request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Intent classification failed: {str(e)}")

@app.post("/api/chat/conversational")
async def handle_conversational_chat(request: ChatCompletionRequest):
    """Handle conversational chat using OpenAI Chat Completions API"""
    try:
        # Get OpenAI API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable not found")
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
                
        # Build context message from analysis if available
        context_message = ""
        if request.has_current_analysis and request.analysis_context:
            result = request.analysis_context
            if result.get("detected_type") == "chord_progression":
                chords = result.get("chord_progression", [])
                context_message = f"Current analyzed chord progression: {' → '.join(chords)}. Key: {result.get('key', 'Unknown')}."
            elif result.get("harmonizations"):
                # This would need to be adapted based on your actual data structure
                style = "simple_pop"  # Default style
                harmonizations = result.get("harmonizations", {})
                if style in harmonizations:
                    chords = harmonizations[style].get("progression", [])
                    context_message = f"Current melody harmonized as: {' → '.join(chords)}. Key: {result.get('key', 'Unknown')}."
        
        # Different system prompts based on whether they've recorded anything
        system_prompt = ""
        if request.has_current_analysis:
            system_prompt = """You're a music co-pilot for songwriters and composers. Keep responses under 30 words since this is voice interaction.
    
    The user has already recorded and analyzed their music. For ANY requests about arrangements, instruments, backing tracks, or making music fuller, always suggest they say "generate" to create an arrangement.
    
    Your role:
    - For arrangement requests: Always suggest saying "generate" to create backing instruments
    - For musical questions: Give specific, actionable advice about their chord progression
    - For general music chat: Be supportive and knowledgeable
    - Keep everything concise and natural
    
    If they ask about adding instruments, backing tracks, fuller sound, or arrangements, respond like: "Say 'generate' and I'll create backing instruments for your [melody/chords]!"""
        else:
            system_prompt = """You're a music co-pilot for songwriters and composers. Keep responses under 30 words since this is voice interaction.
    
    The user hasn't recorded anything yet. Your main job is to recognize when they're describing musical goals (especially about arrangements, adding instruments, or making music fuller) and guide them to record first.
    
    RECOGNIZE THESE AS ARRANGEMENT INTENTIONS:
    - "I have a melody and want to see how it sounds with instruments"
    - "I'd like to add backing to this tune I have"
    - "How would this sound with more instruments"
    - "I want to create an arrangement"
    - "Can we build on this melody"
    - Any mention of adding instruments, backing tracks, fuller sound, arrangements
    
    FOR ARRANGEMENT INTENTIONS: Respond enthusiastically and guide them to record first, like:
    "That sounds awesome! First, let's capture your melody. Ask me to record you when you're ready to play it, then I'll help add instruments!"
    
    FOR OTHER MUSIC QUESTIONS: Be helpful and supportive but concise.
    
    Always be encouraging about their musical ideas!"""

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add context about current analysis if available
        if context_message:
            messages.append({"role": "system", "content": context_message})
        
        # Add user command
        messages.append({"role": "user", "content": request.command})
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": messages,
            "max_tokens": 100,
            "temperature": 0.7
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30.0
        )
        
        if response.status_code != 200:
            error_text = response.text
            logger.error(f"OpenAI API returned status {response.status_code}: {error_text}")
            raise HTTPException(
                status_code=500, 
                detail=f"OpenAI API error {response.status_code}: {error_text}"
            )
        
        result = response.json()
        ai_response = result["choices"][0]["message"]["content"]
        
        return {"response": ai_response}
            
    except requests.RequestException as e:
        logger.error(f"OpenAI API request failed in conversational chat: {e}")
        raise HTTPException(status_code=500, detail=f"OpenAI API request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Conversational chat failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("astro-midi-app/public/generated_arrangements", exist_ok=True)
    os.makedirs("generated_visualizations", exist_ok=True)

    print("🚀 Starting MIDI Analysis API (Frontend-Only MIDI + Forced 8-Chord Rule)...")
    print("📚 API docs available at: http://localhost:8000/docs")
    print("🎹 Ready for frontend-recorded MIDI files with GUARANTEED 8 chords!")

    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )