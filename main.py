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
        base_name = os.path.splitext(file.filename)[0]
        viz_success = False
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