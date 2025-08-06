"""Pydantic models for API request/response schemas."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel


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


class HealthCheckResponse(BaseModel):
    status: str
    models_loaded: bool
    bass_model: bool
    drum_model: bool
    architecture: str


class MidiTypeResponse(BaseModel):
    filename: str
    type: str
    message: str


class ChordAnalysisResponse(BaseModel):
    filename: str
    chord_progression: List[str]
    segments: int
    analysis_type: str


class VisualizationInfo(BaseModel):
    success: bool
    file: Optional[str] = None
    download_url: Optional[str] = None
    type: Optional[str] = None


class HarmonizationInfo(BaseModel):
    progression: List[str]
    confidence: float


class MelodyAnalysisResponse(BaseModel):
    filename: str
    detected_type: str
    analysis_path: str
    analysis_type: str
    key: str
    chord_progression: List[str]
    visualization: VisualizationInfo
    chord_melody_detection: Dict[str, Any]
    harmonizations: Optional[Dict[str, HarmonizationInfo]] = None
    segments: Optional[int] = None
    forced_8_chords: Optional[bool] = None


class ArrangementResponse(BaseModel):
    message: str
    chord_progression: List[str]
    settings: Dict[str, Any]
    output_file: str
    download_url: str


class IntentClassificationResponse(BaseModel):
    intent: str
    confidence: float
    parameters: Optional[Dict[str, Any]] = None


class ConversationalChatResponse(BaseModel):
    response: str