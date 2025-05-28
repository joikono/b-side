# live_midi_capture.py - Real-time MIDI input capture and analysis

import rtmidi
import time
import threading
from collections import deque
from typing import List, Tuple, Optional, Callable, Any, TYPE_CHECKING
import note_seq
from dataclasses import dataclass

# Import for type checking only
if TYPE_CHECKING:
    from note_seq import NoteSequence

@dataclass
class MidiEvent:
    """Simple MIDI event structure"""
    timestamp: float
    message: List[int]
    note: Optional[int] = None
    velocity: Optional[int] = None
    is_note_on: bool = False
    is_note_off: bool = False

class LiveMidiCapture:
    """
    Captures live MIDI input and converts to NoteSequence for analysis.
    Supports multiple capture modes: time-based, silence-based, manual.
    """
    
    def __init__(self):
        self.midi_in = None
        self.is_capturing = False
        self.midi_events = deque()
        self.capture_thread = None
        self.start_time = None
        
        # Capture settings
        self.max_capture_duration = 30.0  # Max 30 seconds
        self.silence_threshold = 2.0      # Stop after 2 seconds of silence
        self.min_capture_duration = 1.0   # Minimum 1 second to analyze
        
        # Callbacks
        self.on_analysis_ready: Optional[Callable] = None
        
    def get_available_devices(self) -> List[Tuple[int, str]]:
        """Get list of available MIDI input devices."""
        try:
            midi_in = rtmidi.MidiIn()
            devices = []
            for i in range(midi_in.get_port_count()):
                port_name = midi_in.get_port_name(i)
                devices.append((i, port_name))
            midi_in.close_port()
            del midi_in
            return devices
        except Exception as e:
            print(f"❌ Error getting MIDI devices: {e}")
            return []
    
    def connect_device(self, device_id: int = 0) -> bool:
        """Connect to a MIDI device."""
        try:
            self.midi_in = rtmidi.MidiIn()
            
            if device_id >= self.midi_in.get_port_count():
                print(f"❌ Device {device_id} not found")
                return False
            
            device_name = self.midi_in.get_port_name(device_id)
            self.midi_in.open_port(device_id)
            self.midi_in.set_callback(self._midi_callback)
            
            print(f"✅ Connected to MIDI device: {device_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error connecting to MIDI device: {e}")
            return False
    
    def disconnect_device(self):
        """Disconnect from MIDI device."""
        if self.midi_in:
            self.stop_capture()
            self.midi_in.close_port()
            del self.midi_in
            self.midi_in = None
            print("✅ MIDI device disconnected")
    
    def _midi_callback(self, message, data=None):
        """Handle incoming MIDI messages."""
        if not self.is_capturing:
            return
        
        msg, timestamp = message
        current_time = time.time()
        
        # Parse MIDI message
        event = MidiEvent(timestamp=current_time, message=msg)
        
        if len(msg) >= 3:
            status = msg[0]
            note = msg[1]
            velocity = msg[2]
            
            # Note on (velocity > 0) or note off (velocity = 0 or status = 0x80)
            if (status & 0xF0) == 0x90:  # Note on channel
                event.note = note
                event.velocity = velocity
                event.is_note_on = velocity > 0
                event.is_note_off = velocity == 0
            elif (status & 0xF0) == 0x80:  # Note off channel
                event.note = note
                event.velocity = velocity
                event.is_note_off = True
        
        self.midi_events.append(event)
    
    def start_capture(self, mode: str = "time", duration: float = 8.0):
        """
        Start capturing MIDI input.
        
        Args:
            mode: "time" (fixed duration), "silence" (until silence), "manual" (until stopped)
            duration: For time mode, how long to capture
        """
        if not self.midi_in:
            print("❌ No MIDI device connected")
            return False
        
        if self.is_capturing:
            print("⚠️  Already capturing MIDI")
            return False
        
        self.midi_events.clear()
        self.is_capturing = True
        self.start_time = time.time()
        
        print(f"🎹 Started MIDI capture (mode: {mode}, duration: {duration}s)")
        
        if mode == "time":
            # Capture for fixed duration
            self.capture_thread = threading.Thread(
                target=self._time_based_capture, 
                args=(duration,)
            )
        elif mode == "silence":
            # Capture until silence
            self.capture_thread = threading.Thread(
                target=self._silence_based_capture
            )
        elif mode == "manual":
            # Capture until manually stopped
            print("🎹 Manual capture started - call stop_capture() when done")
            return True
        
        self.capture_thread.start()
        return True
    
    def _time_based_capture(self, duration: float):
        """Capture for a fixed duration."""
        time.sleep(duration)
        self.stop_capture()
        self._trigger_analysis()
    
    def _silence_based_capture(self):
        """Capture until silence threshold is reached."""
        last_note_time = time.time()
        
        while self.is_capturing:
            time.sleep(0.1)  # Check every 100ms
            
            # Check if we have recent note events
            current_time = time.time()
            recent_notes = [e for e in self.midi_events 
                          if e.is_note_on and current_time - e.timestamp < self.silence_threshold]
            
            if recent_notes:
                last_note_time = current_time
            elif current_time - last_note_time > self.silence_threshold:
                # Silence threshold reached
                if current_time - self.start_time > self.min_capture_duration:
                    break
            
            # Safety: Max capture duration
            if current_time - self.start_time > self.max_capture_duration:
                break
        
        self.stop_capture()
        self._trigger_analysis()
    
    def stop_capture(self):
        """Stop capturing MIDI input."""
        if not self.is_capturing:
            return
        
        self.is_capturing = False
        duration = time.time() - self.start_time if self.start_time else 0
        note_count = sum(1 for e in self.midi_events if e.is_note_on)
        
        print(f"🎹 MIDI capture stopped - Duration: {duration:.1f}s, Notes: {note_count}")
        
        # FIXED: Don't join thread if we're calling from within the same thread
        if self.capture_thread and self.capture_thread.is_alive():
            current_thread = threading.current_thread()
            if current_thread != self.capture_thread:
                self.capture_thread.join(timeout=1.0)
    
    def _trigger_analysis(self):
        """Trigger analysis of captured MIDI data."""
        if self.on_analysis_ready:
            note_sequence = self.convert_to_note_sequence()
            if note_sequence:
                self.on_analysis_ready(note_sequence)
    
    def convert_to_note_sequence(self) -> Optional[Any]:
        """Convert captured MIDI events to NoteSequence."""
        if not self.midi_events:
            print("⚠️  No MIDI events captured")
            return None
        
        # Create NoteSequence
        sequence = note_seq.NoteSequence()
        sequence.tempos.add(qpm=120)  # Default tempo
        sequence.ticks_per_quarter = 220
        
        # Track note on/off events
        active_notes = {}  # note -> start_time
        
        # Process events chronologically
        events = sorted(self.midi_events, key=lambda e: e.timestamp)
        start_time = events[0].timestamp if events else time.time()
        
        for event in events:
            if event.note is None:
                continue
            
            relative_time = event.timestamp - start_time
            
            if event.is_note_on:
                # Start a note
                active_notes[event.note] = relative_time
            
            elif event.is_note_off or (event.note in active_notes):
                # End a note
                if event.note in active_notes:
                    note_start = active_notes[event.note]
                    note_end = relative_time
                    
                    # Add note to sequence
                    sequence.notes.add(
                        pitch=event.note,
                        velocity=event.velocity or 80,
                        start_time=note_start,
                        end_time=max(note_end, note_start + 0.1),  # Minimum duration
                        is_drum=False
                    )
                    
                    del active_notes[event.note]
        
        # Close any remaining active notes
        final_time = (events[-1].timestamp - start_time) if events else 0
        for note, start_time in active_notes.items():
            sequence.notes.add(
                pitch=note,
                velocity=80,
                start_time=start_time,
                end_time=final_time + 0.1,
                is_drum=False
            )
        
        # Set total time
        if sequence.notes:
            sequence.total_time = max(note.end_time for note in sequence.notes)
            print(f"✅ Converted to NoteSequence: {len(sequence.notes)} notes, {sequence.total_time:.1f}s")
            return sequence
        else:
            print("⚠️  No notes in captured sequence")
            return None
    
    def get_status(self) -> dict:
        """Get current capture status."""
        return {
            "is_capturing": self.is_capturing,
            "device_connected": self.midi_in is not None,
            "events_captured": len(self.midi_events),
            "capture_duration": time.time() - self.start_time if self.start_time else 0
        }

# Global instance
live_midi = LiveMidiCapture()