"""Service for file operations and MIDI processing."""

import os
import tempfile
from typing import Optional
from fastapi import UploadFile
from fastapi.responses import FileResponse
from mido import MidiFile, MidiTrack, Message, MetaMessage

from ..config import settings
from ..core.exceptions import InvalidMidiFileError
from ..utils.helpers import save_upload_to_temp, cleanup_temp_file, validate_midi_file
from ..utils.logging import get_logger

logger = get_logger(__name__)


class FileService:
    """Service for handling file operations and MIDI processing."""
    
    async def download_arrangement(self, filename: str) -> FileResponse:
        """Download generated MIDI arrangement files."""
        file_path = os.path.join(settings.generated_arrangements_dir, filename)
        
        if not os.path.exists(file_path):
            raise InvalidMidiFileError("File not found")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='audio/midi'
        )
    
    async def download_visualization(self, filename: str) -> FileResponse:
        """Download generated visualization files."""
        file_path = os.path.join(settings.generated_visualizations_dir, filename)
        
        if not os.path.exists(file_path):
            raise InvalidMidiFileError("Visualization file not found")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='image/png'
        )
    
    async def fix_midi_duration(self, file: UploadFile, target_seconds: float = 9.6) -> FileResponse:
        """Force MIDI file to exactly specified duration - extend short files, truncate long files."""
        if not validate_midi_file(file.filename):
            raise InvalidMidiFileError("File must be a MIDI file (.mid or .midi)")
        
        temp_input_path = await save_upload_to_temp(file)
        
        try:
            # Load with mido
            midi = MidiFile(temp_input_path)
            
            # Calculate exact target in ticks
            ticks_per_beat = midi.ticks_per_beat or 480
            target_ticks = int(target_seconds * 100 * ticks_per_beat / 60)  # at 100 BPM
            
            logger.info(f"🎯 Target: {target_ticks} ticks for {target_seconds}s at 100 BPM")
            logger.info(f"🎵 Original MIDI Type: {midi.type}, Tracks: {len(midi.tracks)}")
            
            if len(midi.tracks) == 0:
                raise InvalidMidiFileError("MIDI file has no tracks")
            
            # Process user's track with precise timing control
            original_track = midi.tracks[0]
            processed_messages = []
            current_ticks = 0
            
            for msg in original_track:
                current_ticks += msg.time
                
                if msg.type == 'end_of_track':
                    continue  # Skip end_of_track, we'll add it later
                
                # Truncation logic: Only include events that start before target duration
                if current_ticks <= target_ticks:
                    processed_messages.append({
                        'message': msg.copy(),
                        'absolute_time': current_ticks,
                        'delta_time': msg.time
                    })
                    
                    # Special case: If this is a note_on, ensure corresponding note_off at target duration max
                    if hasattr(msg, 'type') and msg.type == 'note_on' and hasattr(msg, 'note'):
                        # Look ahead for the corresponding note_off
                        temp_ticks = current_ticks
                        
                        for future_msg in original_track[original_track.index(msg) + 1:]:
                            temp_ticks += future_msg.time
                            
                            if (hasattr(future_msg, 'type') and future_msg.type == 'note_off' and
                                hasattr(future_msg, 'note') and future_msg.note == msg.note and
                                hasattr(future_msg, 'channel') and future_msg.channel == msg.channel):
                                
                                if temp_ticks > target_ticks:
                                    # Add truncated note_off at exactly target duration
                                    note_off_time = target_ticks
                                    processed_messages.append({
                                        'message': Message('note_off', channel=msg.channel, 
                                                         note=msg.note, velocity=0),
                                        'absolute_time': note_off_time,
                                        'delta_time': 0  # Will be calculated later
                                    })
                                    logger.info(f"🔪 Truncated note {msg.note} to end at {target_seconds}s")
                                break
                else:
                    logger.info(f"🔪 Truncated event at {current_ticks} ticks (beyond {target_seconds}s)")
            
            original_duration = current_ticks
            logger.info(f"🎵 Original duration: {original_duration} ticks ({original_duration * 60 / (100 * ticks_per_beat):.2f}s)")
            
            # Sort messages by absolute time and rebuild with correct delta times
            processed_messages.sort(key=lambda x: x['absolute_time'])
            
            # Create clean track with corrected timing
            clean_track = MidiTrack()
            last_time = 0
            
            for msg_data in processed_messages:
                delta = msg_data['absolute_time'] - last_time
                msg_data['message'].time = delta
                clean_track.append(msg_data['message'])
                last_time = msg_data['absolute_time']
            
            # Handle final timing
            final_track_duration = last_time if processed_messages else 0
            
            if final_track_duration < target_ticks:
                # Need to extend
                remaining_ticks = target_ticks - final_track_duration
                clean_track.append(Message('control_change', channel=15, control=7, value=0, 
                                         time=remaining_ticks))
                logger.info(f"🔧 Extended by {remaining_ticks} ticks to reach {target_seconds}s")
            elif final_track_duration > target_ticks:
                logger.info(f"🔪 Truncated from {final_track_duration} to {target_ticks} ticks")
            else:
                logger.info(f"✅ Duration already exactly {target_ticks} ticks")
            
            # Add final end_of_track
            clean_track.append(MetaMessage('end_of_track', time=0))
            
            # Create final MIDI file
            final_midi = MidiFile(type=0, ticks_per_beat=midi.ticks_per_beat)
            final_midi.tracks.append(clean_track)
            
            # Save final file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mid') as temp_output:
                temp_output_path = temp_output.name
            
            final_midi.save(temp_output_path)
            
            action = "extended" if original_duration < target_ticks else "truncated" if original_duration > target_ticks else "maintained"
            logger.info(f"🎯 Successfully {action} MIDI to exactly {target_seconds}s duration")
            
            return FileResponse(
                temp_output_path,
                media_type='audio/midi',
                filename='duration_fixed_clean.mid'
            )
            
        except Exception as e:
            logger.error(f"Duration fix error: {e}")
            raise InvalidMidiFileError(f"MIDI duration fix failed: {str(e)}")
        finally:
            cleanup_temp_file(temp_input_path)


# Global file service instance
file_service = FileService()