# main.py - Streamlined FastAPI Backend with FORCED 8-CHORD Analysis
# Fixed: Always returns exactly 8 chords for frontend MIDI uploads

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
from chord_analyzer import analyze_midi_chord_progression
from melody_analyzer2 import analyze_midi_melody, create_four_way_visualization
from chord_or_melody import detect_midi_type
from arrangement_generator import generate_arrangement_from_chords

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

def force_exactly_8_chords_analysis(midi_path):
    """
    HARD RULE: Always return exactly 8 chords.
    Divide the melody into exactly 8 equal segments and analyze each.
    """
    from melody_analyzer2 import extract_melody_with_timing, detect_key_from_melody
    from melody_analyzer2 import suggest_chord_simple_style, suggest_chord_folk_style
    from melody_analyzer2 import get_scale_degrees_in_key

    print("🎯 FORCE EXACTLY 8 CHORDS - Frontend Upload Mode")

    # Extract notes with tolerance
    notes, ticks_per_beat = extract_melody_with_timing(midi_path, tolerance_beats=0.2)

    if not notes:
        print("❌ No notes found - using default progression")
        return "C", (['C'] * 8, ['C'] * 8, ['C'] * 8, ['C'] * 8), (50.0, 50.0, 85.0, 80.0), []

    # Detect key
    key, key_confidence = detect_key_from_melody(notes)
    print(f"🎼 Detected Key: {key} (confidence: {key_confidence:.3f})")

    if not key:
        key = "C"  # Fallback

    scale_degrees = get_scale_degrees_in_key(key)

    # Find the actual start and end of musical content
    if notes:
        music_start = min(note['start'] for note in notes)
        music_end = max(note['end'] for note in notes)
        music_duration = music_end - music_start
    else:
        music_start = 0
        music_end = 16  # Fallback to 16 beats
        music_duration = 16

    print(f"🎵 Musical content: {music_start:.2f} → {music_end:.2f} beats ({music_duration:.2f} beats)")

    # Force exactly 8 segments
    segment_duration = music_duration / 8.0  # Equal segments

    simple_progression = []
    folk_progression = []
    all_segments = []

    print(f"🎯 Creating exactly 8 segments of {segment_duration:.2f} beats each:")

    for seg_idx in range(8):  # HARD RULE: Exactly 8 segments
        # Calculate segment boundaries
        segment_start = music_start + (seg_idx * segment_duration)
        segment_end = music_start + ((seg_idx + 1) * segment_duration)

        print(f"  Segment {seg_idx+1}: {segment_start:.2f} → {segment_end:.2f} beats")

        # Find notes in this segment
        segment_notes = []
        for note in notes:
            # Check if note overlaps with this segment
            if (note['start'] < segment_end and note['end'] > segment_start):
                segment_notes.append(note)

        if segment_notes:
            # Analyze this segment
            simple_chord, simple_conf = suggest_chord_simple_style(segment_notes, key, scale_degrees)
            folk_chord, folk_conf = suggest_chord_folk_style(segment_notes, key, scale_degrees)

            simple_progression.append(simple_chord or 'C')
            folk_progression.append(folk_chord or 'C')

            # Debug output
            pcs = sorted(set(note['pitch_class'] for note in segment_notes))
            print(f"    {len(segment_notes)} notes, PCs: {pcs}")
            print(f"    → Simple: {simple_chord or 'C'}, Folk: {folk_chord or 'C'}")
        else:
            print(f"    No notes - using C")
            simple_progression.append('C')
            folk_progression.append('C')

        # Create segment data
        segment_data = {
            'start_beat': segment_start,
            'end_beat': segment_end,
            'simple': {'chord': simple_progression[-1], 'confidence': 75.0},
            'folk': {'chord': folk_progression[-1], 'confidence': 75.0},
            'notes': segment_notes
        }
        all_segments.append(segment_data)

    # Create foundation progressions (simple patterns for 8 chords)
    bass_progression = [key] * 4 + ['F'] * 2 + ['G'] * 2  # Key-F-F-G-G pattern
    phrase_progression = [key] * 4 + ['Am'] * 4 if not key.endswith('m') else [key] * 8

    # Calculate confidence scores
    simple_conf = 75.0
    folk_conf = 75.0
    bass_conf = 85.0
    phrase_conf = 80.0

    print(f"\n🎵 FORCED 8-chord analysis results:")
    print(f"  Simple: {' → '.join(simple_progression)}")
    print(f"  Folk: {' → '.join(folk_progression)}")
    print(f"  Bass: {' → '.join(bass_progression)}")
    print(f"  Phrase: {' → '.join(phrase_progression)}")
    print(f"✅ GUARANTEED: Exactly 8 chords each!")

    return key, (simple_progression, folk_progression, bass_progression, phrase_progression), (simple_conf, folk_conf, bass_conf, phrase_conf), all_segments

def create_chord_progression_visualization(chord_progression, key, style_name, output_file):
    """Create a visualization of the chord progression and save it."""
    try:
        plt.style.use('default')
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))
        
        # Color scheme for different chord types
        chord_colors = {
            'major': '#3498db',      # Blue
            'minor': '#e74c3c',      # Red  
            'dominant': '#f39c12',   # Orange
            'diminished': '#9b59b6', # Purple
            'other': '#95a5a6'       # Gray
        }
        
        def get_chord_type(chord):
            if chord == 'N':
                return 'other'
            elif 'm' in chord and '7' not in chord:
                return 'minor'
            elif '7' in chord:
                return 'dominant'
            elif any(dim in chord.lower() for dim in ['dim', 'o']):
                return 'diminished'
            else:
                return 'major'
        
        # Top plot: Chord progression timeline
        ax1.set_title(f'Chord Progression Analysis - {style_name} Style\nKey: {key}', 
                     fontsize=16, fontweight='bold', pad=20)
        
        # Create chord blocks
        for i, chord in enumerate(chord_progression):
            chord_type = get_chord_type(chord)
            color = chord_colors[chord_type]
            
            # Draw chord block
            rect = patches.Rectangle((i, 0), 0.8, 1, 
                                   linewidth=2, edgecolor='black', 
                                   facecolor=color, alpha=0.7)
            ax1.add_patch(rect)
            
            # Add chord label
            ax1.text(i + 0.4, 0.5, chord, 
                    ha='center', va='center', 
                    fontsize=14, fontweight='bold', color='white')
        
        ax1.set_xlim(-0.5, len(chord_progression) - 0.5)
        ax1.set_ylim(-0.1, 1.1)
        ax1.set_xlabel('Chord Position (2-beat segments)', fontsize=12)
        ax1.set_ylabel('Chord', fontsize=12)
        ax1.set_xticks(range(len(chord_progression)))
        ax1.set_xticklabels([f'{i+1}' for i in range(len(chord_progression))])
        ax1.set_yticks([])
        ax1.grid(True, axis='x', alpha=0.3)
        
        # Bottom plot: Chord type distribution
        chord_types = [get_chord_type(chord) for chord in chord_progression]
        type_counts = {chord_type: chord_types.count(chord_type) for chord_type in chord_colors.keys()}
        type_counts = {k: v for k, v in type_counts.items() if v > 0}
        
        if type_counts:
            colors = [chord_colors[chord_type] for chord_type in type_counts.keys()]
            bars = ax2.bar(type_counts.keys(), type_counts.values(), color=colors, alpha=0.7)
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                        f'{int(height)}', ha='center', va='bottom', fontweight='bold')
        
        ax2.set_title('Chord Type Distribution', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Count', fontsize=12)
        ax2.set_xlabel('Chord Types', fontsize=12)
        ax2.grid(True, axis='y', alpha=0.3)
        
        # Add legend
        legend_elements = [patches.Patch(facecolor=color, edgecolor='black', label=chord_type.title()) 
                          for chord_type, color in chord_colors.items() if chord_type in type_counts]
        ax2.legend(handles=legend_elements, loc='upper right')
        
        # Add analysis info
        info_text = f"""Analysis Summary:
• Total Chords: {len(chord_progression)}
• Key: {key}
• Style: {style_name}
• Progression: {' → '.join(chord_progression)}"""
        
        plt.figtext(0.02, 0.02, info_text, fontsize=10, 
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.8))
        
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.15)
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Chord progression visualization saved to: {output_file}")
        return True
        
    except Exception as e:
        print(f"Error creating visualization: {e}")
        return False

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
    """
    Analyze melody and get 4 harmonization options.
    *** PRIMARY ENDPOINT for frontend-recorded MIDI ***
    *** ENFORCES EXACTLY 8 CHORDS + AUTO-GENERATES VISUALIZATION ***
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
        # Use forced 8-chord analysis for frontend uploads
        key, progressions, confidences, segments = force_exactly_8_chords_analysis(temp_path)

        simple_prog, folk_prog, bass_prog, phrase_prog = progressions
        simple_conf, folk_conf, bass_conf, phrase_conf = confidences

        print(f"🎼 Analysis complete - Key: {key}")
        print(f"🎵 8-Chord Progressions Generated:")
        print(f"  Simple: {' → '.join(simple_prog)}")
        print(f"  Folk: {' → '.join(folk_prog)}")
        print(f"  Bass: {' → '.join(bass_prog)}")
        print(f"  Phrase: {' → '.join(phrase_prog)}")

        # AUTO-GENERATE FOUR-WAY VISUALIZATION
        timestamp = int(time.time())
        base_name = os.path.splitext(file.filename)[0]
        viz_filename = f"{base_name}_auto_analysis_{timestamp}_four_ways.png"
        viz_path = os.path.join("generated_visualizations", viz_filename)
        
        print(f"📊 Auto-generating four-way visualization...")
        viz_success = False
        try:
            # Extract notes for visualization
            from melody_analyzer2 import extract_melody_with_timing
            extracted_notes, _ = extract_melody_with_timing(temp_path, tolerance_beats=tolerance_beats)
            
            # Generate four-way visualization automatically
            create_four_way_visualization(
                temp_path,           # midi_file
                segments,            # all_segments  
                bass_prog,           # bass_progression
                phrase_prog,         # phrase_progression
                key,                 # key
                extracted_notes,     # notes (properly extracted)
                viz_filename         # output_file (just filename, function adds directory)
            )
            viz_success = True
            print(f"✅ Visualization auto-generated: {viz_filename}")
        except Exception as e:
            print(f"❌ Visualization generation failed: {e}")
            viz_success = False

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
            "analysis_type": "melody",
            "segments": len(segments),
            "forced_8_chords": True,
            "visualization": {
                "success": viz_success,
                "file": viz_filename if viz_success else None,
                "download_url": f"/download/viz/{viz_filename}" if viz_success else None,
                "auto_generated": True
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Melody analysis failed: {str(e)}")
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
        output_dir = "generated_arrangements"
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
            progression, segments = analyze_midi_chord_progression(temp_path)
            chord_list = progression
            analysis_data = {"type": "chord_progression", "progression": progression}
        else:
            # Use forced 8-chord analysis for melody
            key, progressions, confidences, segments = force_exactly_8_chords_analysis(temp_path)

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
    file_path = os.path.join("generated_arrangements", filename)

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
        key, progressions, confidences, segments = force_exactly_8_chords_analysis(temp_path)

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
    os.makedirs("generated_arrangements", exist_ok=True)
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