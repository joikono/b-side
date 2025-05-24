# main.py - FastAPI MIDI Beast
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn
import os
import tempfile
from typing import List, Optional
import logging

# Import your existing modules
from model_manager import MagentaModelManager
from chord_analyzer import analyze_midi_chord_progression
from melody_analyzer2 import analyze_midi_melody
from arrangement_generator import generate_arrangement_from_chords
from chord_or_melody import detect_midi_type

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model manager - loaded once!
model_manager = None
bass_rnn = None
drum_rnn = None

app = FastAPI(
    title="MIDI Beast API",
    description="AI-powered MIDI analysis and arrangement generation",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def load_models():
    """Load Magenta models ONCE on startup - this is the magic!"""
    global model_manager, bass_rnn, drum_rnn
    
    logger.info("🚀 MIDI Beast starting up...")
    logger.info("🔄 Loading Magenta models (this happens ONCE)...")
    
    try:
        model_manager = MagentaModelManager()
        bass_rnn = model_manager.bass_rnn
        drum_rnn = model_manager.drum_rnn
        
        logger.info("✅ Models loaded! MIDI Beast is ready to rock!")
        
    except Exception as e:
        logger.error(f"❌ Failed to load models: {e}")
        raise e

@app.get("/")
async def root():
    """Health check and welcome message"""
    return {
        "message": "🎹 MIDI Beast API is alive!",
        "models_loaded": model_manager.is_loaded() if model_manager else False,
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "models_loaded": model_manager.is_loaded() if model_manager else False,
        "bass_model": bass_rnn is not None,
        "drum_model": drum_rnn is not None
    }

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
        # Analyze chords - FAST because models are already loaded!
        progression, segments = analyze_midi_chord_progression(
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
    """Analyze melody and get 4 harmonization options"""
    if not file.filename.endswith(('.mid', '.midi')):
        raise HTTPException(status_code=400, detail="File must be a MIDI file")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mid') as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name
    
    try:
        # Analyze melody - FAST because models are already loaded!
        key, progressions, confidences, segments = analyze_midi_melody(
            temp_path,
            segment_size=segment_size,
            tolerance_beats=tolerance_beats
        )
        
        simple_prog, folk_prog, bass_prog, phrase_prog = progressions
        simple_conf, folk_conf, bass_conf, phrase_conf = confidences
        
        return {
            "filename": file.filename,
            "key": key,
            "harmonizations": {
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
            "analysis_type": "melody"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Melody analysis failed: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

from pydantic import BaseModel

class ArrangementRequest(BaseModel):
    chord_progression: List[str]
    bpm: int = 100
    bass_complexity: int = 2
    drum_complexity: int = 1
    hi_hat_divisions: int = 2
    snare_beats: List[int] = [2, 4]

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
        output_dir = "generated_arrangements"
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate unique filename
        import time
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

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download generated MIDI files"""
    file_path = os.path.join("generated_arrangements", filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='audio/midi'
    )

@app.post("/full-analysis")
async def full_analysis_and_generation(
    file: UploadFile = File(...),
    harmonization_style: Optional[str] = "simple_pop",  # For melodies
    bpm: int = 100,
    bass_complexity: int = 2,
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
            progression, segments = analyze_midi_chord_progression(temp_path)
            chord_list = progression
            analysis_data = {"type": "chord_progression", "progression": progression}
        else:
            key, progressions, confidences, segments = analyze_midi_melody(temp_path)
            
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
        output_dir = "generated_arrangements"
        os.makedirs(output_dir, exist_ok=True)
        
        import time
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
            
if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("generated_arrangements", exist_ok=True)
    os.makedirs("generated_visualizations", exist_ok=True)
    
    print("🚀 Starting MIDI Beast API...")
    print("📚 API docs will be available at: http://localhost:8000/docs")
    print("🎹 Ready to process MIDI files at lightning speed!")
    
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,  # Auto-reload during development
        log_level="info"
    )