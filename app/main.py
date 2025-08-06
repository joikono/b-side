"""Clean FastAPI application with proper separation of concerns."""

from fastapi import FastAPI, File, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .config import settings
from .models.schemas import (
    ArrangementRequest, VoiceTranscriptionRequest, ChatCompletionRequest,
    HealthCheckResponse, MidiTypeResponse, ChordAnalysisResponse,
    MelodyAnalysisResponse, ArrangementResponse, IntentClassificationResponse,
    ConversationalChatResponse
)
from .core.model_manager import model_service
from .core.exceptions import (
    ModelNotLoadedError, InvalidMidiFileError, AnalysisFailedError,
    ArrangementGenerationError, OpenAIAPIError, raise_http_exception
)
from .services.analysis_service import analysis_service
from .services.arrangement_service import arrangement_service
from .services.openai_service import openai_service
from .services.file_service import file_service
from .utils.logging import setup_logging, get_logger
from .utils.helpers import validate_midi_file, ensure_directories_exist
from .core.middleware import ErrorHandlingMiddleware, RequestLoggingMiddleware

# Setup logging
setup_logging(settings.log_level.upper())
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version
)

# Add middleware (order matters!)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to validate MIDI files
def validate_midi_upload(file: UploadFile = File(...)) -> UploadFile:
    """Validate uploaded MIDI file."""
    if not validate_midi_file(file.filename):
        raise_http_exception(400, "File must be a MIDI file (.mid or .midi)")
    return file


# Exception handlers
@app.exception_handler(ModelNotLoadedError)
async def model_not_loaded_handler(request, exc):
    raise_http_exception(503, str(exc))


@app.exception_handler(InvalidMidiFileError)
async def invalid_midi_handler(request, exc):
    raise_http_exception(400, str(exc))


@app.exception_handler(AnalysisFailedError)
async def analysis_failed_handler(request, exc):
    raise_http_exception(500, str(exc))


@app.exception_handler(ArrangementGenerationError)
async def arrangement_failed_handler(request, exc):
    raise_http_exception(500, str(exc))


@app.exception_handler(OpenAIAPIError)
async def openai_error_handler(request, exc):
    raise_http_exception(500, str(exc))


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    try:
        # Create necessary directories
        ensure_directories_exist(
            settings.generated_arrangements_dir,
            settings.generated_visualizations_dir
        )
        
        # Load ML models
        await model_service.load_models()
        
        logger.info("Application startup complete!")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise e


# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@app.get("/", response_model=dict)
async def root():
    """Health check and welcome message."""
    return {
        "message": f"🎹 {settings.app_name} (Frontend-Only MIDI + Forced 8-Chord Rule)",
        "models_loaded": model_service.is_loaded(),
        "version": settings.app_version,
        "features": ["Frontend MIDI Recording", "Forced 8-Chord Analysis", "Arrangement Generation"]
    }


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Detailed health check."""
    health_status = model_service.get_health_status()
    return HealthCheckResponse(
        status="healthy",
        architecture="frontend_only_midi_forced_8_chords",
        **health_status
    )


# ============================================================================
# CORE ANALYSIS ENDPOINTS
# ============================================================================

@app.post("/analyze/type", response_model=MidiTypeResponse)
async def analyze_midi_type(file: UploadFile = Depends(validate_midi_upload)):
    """Detect if uploaded MIDI is chord progression or melody."""
    return await analysis_service.detect_midi_type(file)


@app.post("/analyze/chords", response_model=ChordAnalysisResponse)
async def analyze_chords(
    file: UploadFile = Depends(validate_midi_upload),
    segment_size: int = settings.default_segment_size,
    tolerance_beats: float = settings.default_tolerance_beats
):
    """Analyze chord progression from uploaded MIDI."""
    return await analysis_service.analyze_chord_progression(file, segment_size, tolerance_beats)


@app.post("/analyze/melody", response_model=MelodyAnalysisResponse)
async def analyze_melody(
    file: UploadFile = Depends(validate_midi_upload),
    segment_size: int = settings.default_segment_size,
    tolerance_beats: float = settings.default_tolerance_beats
):
    """Comprehensive melody analysis with harmonization and visualization."""
    return await analysis_service.analyze_melody_with_harmonization(file, segment_size, tolerance_beats)


@app.post("/analyze/melody-with-viz")
async def analyze_melody_with_visualization(
    file: UploadFile = Depends(validate_midi_upload),
    harmonization_style: str = "simple_pop",
    segment_size: int = settings.default_segment_size,
    tolerance_beats: float = settings.default_tolerance_beats
):
    """Analyze melody and create four-way visualization with FORCED 8-chord rule."""
    return await analysis_service.analyze_melody_with_four_way_viz(
        file, harmonization_style, segment_size, tolerance_beats
    )


# ============================================================================
# ARRANGEMENT GENERATION ENDPOINTS
# ============================================================================

@app.post("/generate/arrangement", response_model=ArrangementResponse)
async def generate_arrangement(request: ArrangementRequest):
    """Generate arrangement from chord progression."""
    return await arrangement_service.generate_from_chord_progression(request)


@app.post("/full-analysis")
async def full_analysis_and_generation(
    file: UploadFile = Depends(validate_midi_upload),
    harmonization_style: str = "simple_pop",
    bpm: int = settings.default_bpm,
    bass_complexity: int = 1,
    drum_complexity: int = 1
):
    """Complete workflow: analyze MIDI → detect type → generate arrangement."""
    return await arrangement_service.full_analysis_and_generation(
        file, harmonization_style, bpm, bass_complexity, drum_complexity
    )


# ============================================================================
# FILE PROCESSING ENDPOINTS
# ============================================================================

@app.post("/fix-midi-duration")
async def fix_midi_duration(file: UploadFile = Depends(validate_midi_upload)):
    """Force MIDI file to exactly 9.6 seconds - extend short files, truncate long files."""
    return await file_service.fix_midi_duration(file)


# ============================================================================
# FILE DOWNLOAD ENDPOINTS
# ============================================================================

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download generated MIDI files."""
    return await file_service.download_arrangement(filename)


@app.get("/download/viz/{filename}")
async def download_visualization(filename: str):
    """Download generated visualization files."""
    return await file_service.download_visualization(filename)


# ============================================================================
# OPENAI API ENDPOINTS
# ============================================================================

@app.post("/api/voice/transcribe")
async def transcribe_voice(request: VoiceTranscriptionRequest):
    """Transcribe voice audio using OpenAI Whisper API."""
    return await openai_service.transcribe_voice(request.audio_blob)


@app.post("/api/chat/intent-classification", response_model=IntentClassificationResponse)
async def classify_intent(request: ChatCompletionRequest):
    """Classify user intent using OpenAI Chat Completions API."""
    return await openai_service.classify_intent(request.command)


@app.post("/api/chat/conversational", response_model=ConversationalChatResponse)
async def handle_conversational_chat(request: ChatCompletionRequest):
    """Handle conversational chat using OpenAI Chat Completions API."""
    return await openai_service.handle_conversational_chat(request)


# ============================================================================
# APPLICATION RUNNER
# ============================================================================

def run_app():
    """Run the application."""
    logger.info(f"Starting {settings.app_name}...")
    logger.info("API docs available at: http://localhost:8000/docs")
    logger.info("Ready for frontend-recorded MIDI files with GUARANTEED 8 chords!")
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level
    )


if __name__ == "__main__":
    run_app()