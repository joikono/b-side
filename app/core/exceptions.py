"""Custom exceptions for the application."""

from fastapi import HTTPException


class MidiAnalysisError(Exception):
    """Base exception for MIDI analysis errors."""
    pass


class ModelNotLoadedError(MidiAnalysisError):
    """Raised when required ML models are not loaded."""
    pass


class InvalidMidiFileError(MidiAnalysisError):
    """Raised when MIDI file is invalid or corrupted."""
    pass


class AnalysisFailedError(MidiAnalysisError):
    """Raised when MIDI analysis fails."""
    pass


class ArrangementGenerationError(MidiAnalysisError):
    """Raised when arrangement generation fails."""
    pass


class OpenAIAPIError(MidiAnalysisError):
    """Raised when OpenAI API calls fail."""
    pass


def raise_http_exception(status_code: int, detail: str) -> HTTPException:
    """Helper to raise HTTPException with logging."""
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"HTTP {status_code}: {detail}")
    raise HTTPException(status_code=status_code, detail=detail)