"""
Analyze a MIDI file to determine if it contains chord progressions or melody.

Args:
    midi_file: Path to MIDI file
    
Returns:
    str: "chord_progression" or "melody"
"""

import mido
import numpy as np
from collections import defaultdict

def detect_midi_type(midi_file):

    try:
        # Load MIDI file
        midi_data = mido.MidiFile(midi_file)
        print(f"Successfully loaded MIDI file: {midi_file}")
        
        # Extract note events
        note_events = extract_note_events(midi_data)
        if not note_events:
            print("No notes found in MIDI file")
            return "unknown"
        
        # Analyze simultaneous notes
        notes_by_time = defaultdict(list)
        times_with_multiple_notes = 0
        total_time_points = 0
        
        # First pass: collect all active notes at each time position
        active_notes = {}  # {track_num: {note_num: start_time}}
        
        # Process all tracks
        for track_idx, track in enumerate(midi_data.tracks):
            current_time = 0
            track_active_notes = {}
            
            for msg in track:
                current_time += msg.time
                
                # Note on event
                if msg.type == 'note_on' and msg.velocity > 0:
                    note_num = msg.note
                    track_active_notes[note_num] = current_time
                
                # Note off event
                elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                    note_num = msg.note
                    if note_num in track_active_notes:
                        start_time = track_active_notes[note_num]
                        del track_active_notes[note_num]
                        
                        # Round time to help group slightly offset notes (common in MIDI recordings)
                        rounded_time = round(start_time * 4) / 4  # Round to nearest 0.25
                        notes_by_time[rounded_time].append(note_num)
        
        # Count polyphony
        polyphony_counts = [len(notes) for _, notes in notes_by_time.items()]
        total_time_points = len(polyphony_counts)
        times_with_multiple_notes = sum(1 for count in polyphony_counts if count >= 2)
        
        # Calculate metrics
        if total_time_points > 0:
            avg_polyphony = sum(polyphony_counts) / total_time_points
            chord_ratio = times_with_multiple_notes / total_time_points
            max_polyphony = max(polyphony_counts) if polyphony_counts else 0
        else:
            avg_polyphony = 0
            chord_ratio = 0
            max_polyphony = 0
        
        # Print detailed diagnostics
        print(f"Total time points: {total_time_points}")
        print(f"Average notes per time point: {avg_polyphony:.2f}")
        print(f"Maximum notes at any time point: {max_polyphony}")
        print(f"Percentage of time points with multiple notes: {chord_ratio*100:.1f}%")
        
        # Analyze consecutive/simultaneous patterns
        note_pattern = "mixed"
        if avg_polyphony < 1.2 and chord_ratio < 0.1:
            note_pattern = "sequential"
        elif avg_polyphony > 1.5 or chord_ratio > 0.15:
            note_pattern = "simultaneous"
        
        print(f"Note pattern: {note_pattern}")
        
        # Decision based on metrics
        result = "chord_progression" if (avg_polyphony >= 1.5 or chord_ratio >= 0.15) else "melody"
        print(f"Classification: {result}")
        
        # Print sample of time points
        if polyphony_counts:
            print("\nSample of time points (time: number of notes):")
            times = sorted(notes_by_time.keys())
            for i, time in enumerate(times[:10]):  # Show first 10 time points
                if i < len(times):
                    print(f"  {time:.2f}s: {len(notes_by_time[time])} notes")
        
        return result
        
    except Exception as e:
        print(f"Error analyzing MIDI file: {e}")
        return "error"

def extract_note_events(midi_data):
    """
    Extract note events (note on/off) from MIDI data.
    
    Args:
        midi_data: A mido.MidiFile object
        
    Returns:
        list: List of (note, start_time, duration) tuples
    """
    notes = []
    
    # Process all tracks
    for track_idx, track in enumerate(midi_data.tracks):
        current_time = 0
        active_notes = {}  # {note_num: start_time}
        
        for msg in track:
            current_time += msg.time
            
            # Note on event
            if msg.type == 'note_on' and msg.velocity > 0:
                note_num = msg.note
                active_notes[note_num] = current_time
            
            # Note off event
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                note_num = msg.note
                if note_num in active_notes:
                    start_time = active_notes[note_num]
                    duration = current_time - start_time
                    notes.append((note_num, start_time, duration))
                    del active_notes[note_num]
    
    return notes

if __name__ == "__main__":
    # Replace this with your MIDI file path
    midi_file = "midi_samples/2 4ths.mid"  # Change this path
    
    # Detect type
    result = detect_midi_type(midi_file)
    
    # Final output
    print(f"\nFinal result: This MIDI file contains a {result}")