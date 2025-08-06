"""Utility helper functions."""

import os
import tempfile
from fastapi import UploadFile


def validate_midi_file(filename: str) -> bool:
    """Validate if file is a MIDI file by extension."""
    return filename.lower().endswith(('.mid', '.midi'))


async def save_upload_to_temp(file: UploadFile, suffix: str = '.mid') -> str:
    """Save uploaded file to temporary location and return path."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        content = await file.read()
        temp_file.write(content)
        return temp_file.name


def cleanup_temp_file(file_path: str) -> None:
    """Safely remove temporary file."""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
    except Exception:
        # Silently ignore cleanup failures
        pass


def ensure_directories_exist(*directories: str) -> None:
    """Ensure multiple directories exist, creating them if necessary."""
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


def get_base_filename(filename: str) -> str:
    """Extract base filename without extension."""
    return os.path.splitext(filename or "uploaded")[0]


def build_download_url(base_path: str, filename: str) -> str:
    """Build download URL for generated files."""
    return f"/download/{base_path}/{filename}" if filename else None