"""
This module analyzes MIDI files to detect chord progressions using advanced 
bass-prioritized chord detection with timing tolerance for anticipatory playing.

KEY FEATURES:
- 🎵 Bass-prioritized chord detection (lower pitches weighted more heavily)
- ⏰ Timing tolerance for anticipatory/early playing (handles real musician timing)
- 🎯 2-beat segment analysis (optimal for most musical styles)
- 📊 Comprehensive visualization with timing adjustment indicators
- 🌍 Universal compatibility (works with any MIDI file regardless of genre)

TEMPO & TIME SIGNATURE INDEPENDENCE:
- The algorithm works entirely in "beat units" as defined by MIDI ticks_per_beat
- NO explicit BPM detection - works at any tempo (60 BPM to 200+ BPM)
- NO time signature assumptions - works in 4/4, 3/4, 7/8, or any time signature
- Timing tolerance is beat-relative (0.15 beats = 15% of a beat, regardless of actual tempo)

TIMING TOLERANCE INNOVATION:
Musicians often play chords slightly early (anticipatory playing). This algorithm:
- Detects notes played up to 0.15 beats before their "correct" time
- Only applies timing correction if it significantly improves chord detection
- Visually indicates where timing corrections were applied
- Solves common issues like "Am → F → F → F" becoming correct "Am → Am → F → F"

CHORD DETECTION METHODOLOGY:
- Supports all 12 major and minor triads (C, Cm, C#, C#m, D, Dm, etc.)
- Bass note (lowest pitch) is the strongest chord indicator
- Complete triads get bonus scoring
- Non-chord tones receive penalties
- Confidence scoring helps resolve ambiguous cases

SEGMENT ANALYSIS:
- Uses 2-beat segments as optimal balance for most music styles
- Handles both fast chord changes (jazz, complex progressions) and slow changes (pop, rock)
- Each segment represents half a measure in 4/4 time (but works in any time signature)

TYPICAL OUTPUT EXAMPLES:
- Pop progression: C → C → G → G → Am → Am → F → F  (one chord per measure)
- Jazz progression: C → Dm → Em → F → G → Am → Dm → C  (two chords per measure)
- Complex: F → F → Em → Em  (mixed with melodic content)

USAGE:
    progression, segments = analyze_midi_chord_progression(
        'your_file.mid',
        segment_size=2,        # beats per segment (2 recommended)
        tolerance_beats=0.15   # timing tolerance (0.1-0.2 recommended)
    )

VISUALIZATION OUTPUT:
- Green segments: Normal timing detection
- Blue segments: Timing tolerance was applied
- Red dashed lines: Locations where early notes were detected
- Musical note emoji (🎵): Visual indicator of timing corrections

PARAMETERS TO ADJUST:
- tolerance_beats: 0.1 (strict) to 0.2 (lenient) - how early notes can be played
- segment_size: Usually 2, could use 1 for very complex music or 4 for very simple

DEPENDENCIES:
- miditoolkit: MIDI file loading and manipulation
- matplotlib: Visualization and plotting
- numpy: Numerical operations
- collections.Counter: Chord voting/consensus

AUTHOR NOTES:
Designed for real-world MIDI analysis where human timing isn't perfect.
Prioritizes musical intuition (bass notes matter most) over mathematical precision.
Handles both composed MIDI (exact timing) and performed MIDI (human timing variations).
=============================================================================
"""

import miditoolkit
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter

# COMPATIBILITY FIX - Add this after your imports
import mido

original_mido_init = mido.MidiFile.__init__

def patched_mido_init(self, filename=None, file=None, type=1, ticks_per_beat=480, 
                     charset='latin-1', debug=False, clip=None, **kwargs):
    """Ignore the 'clip' parameter that miditoolkit tries to pass"""
    original_mido_init(self, filename=filename, file=file, type=type, 
                      ticks_per_beat=ticks_per_beat, charset=charset, debug=debug, **kwargs)

mido.MidiFile.__init__ = patched_mido_init
# print("✅ Mido compatibility patch applied")

# Chord definitions - all 12 major and minor triads
CHORD_DEFINITIONS = {
    # Major triads (root, major third, perfect fifth)
    'C': [0, 4, 7], 'C#': [1, 5, 8], 'D': [2, 6, 9], 'D#': [3, 7, 10], 
    'E': [4, 8, 11], 'F': [5, 9, 0], 'F#': [6, 10, 1], 'G': [7, 11, 2], 
    'G#': [8, 0, 3], 'A': [9, 1, 4], 'A#': [10, 2, 5], 'B': [11, 3, 6],
    
    # Minor triads (root, minor third, perfect fifth)
    'Cm': [0, 3, 7], 'C#m': [1, 4, 8], 'Dm': [2, 5, 9], 'D#m': [3, 6, 10], 
    'Em': [4, 7, 11], 'Fm': [5, 8, 0], 'F#m': [6, 9, 1], 'Gm': [7, 10, 2], 
    'G#m': [8, 11, 3], 'Am': [9, 0, 4], 'A#m': [10, 1, 5], 'Bm': [11, 2, 6],
    
    # Major 7th chords (for jazz contexts)
    'Cmaj7': [0, 4, 7, 11], 'C#maj7': [1, 5, 8, 0], 'Dmaj7': [2, 6, 9, 1],
    # And so on for other chord types...
}

def identify_chord_with_confidence(notes):
    """
    Enhanced chord identification that also returns a confidence score.
    """
    if not notes:
        return None, 0
    
    # Extract pitch classes from notes
    all_pitches = [note['pitch'] for note in notes]
    pitch_classes = sorted(set(pitch % 12 for pitch in all_pitches))
    
    # Get bass note
    sorted_notes = sorted(notes, key=lambda x: x['pitch'])
    bass_pc = sorted_notes[0]['pitch'] % 12
    
    # Calculate scores for all possible chords
    chord_scores = {}
    
    for chord_name, chord_pcs in CHORD_DEFINITIONS.items():
        score = 0
        
        # Check how many chord tones are present
        matched_tones = set(pitch_classes).intersection(set(chord_pcs))
        score += len(matched_tones) * 1.0
        
        # Penalize for non-chord tones
        non_chord_tones = set(pitch_classes) - set(chord_pcs)
        score -= len(non_chord_tones) * 0.2
        
        # Bass note bonus/penalty
        if bass_pc == chord_pcs[0]:  # Root in bass
            score += 2.0
        elif bass_pc in chord_pcs:  # Chord tone in bass
            score += 0.5
        else:  # Non-chord tone in bass
            score -= 1.0
        
        # Complete triad bonus
        if len(matched_tones) >= 3:
            score += 1.0
            
        chord_scores[chord_name] = score
    
    # Find the best chord and confidence
    if not chord_scores:
        return None, 0
    
    max_score = max(chord_scores.values())
    best_chords = [name for name, score in chord_scores.items() if score == max_score]
    
    # Confidence is based on how much better the best chord is vs alternatives
    sorted_scores = sorted(chord_scores.values(), reverse=True)
    if len(sorted_scores) > 1:
        confidence = max_score - sorted_scores[1]  # Gap between best and second-best
    else:
        confidence = max_score
    
    # Prefer simpler chords in case of ties
    if len(best_chords) > 1:
        simple_chords = [c for c in best_chords if len(c) <= 2]
        best_chord = simple_chords[0] if simple_chords else best_chords[0]
    else:
        best_chord = best_chords[0] if best_chords else None
    
    return best_chord, max(0, confidence)

def extract_notes_with_timing_tolerance(midi_file, tolerance_beats=0.15):
    """
    Extract notes with timing tolerance to handle early/anticipatory playing.
    
    Parameters:
    - tolerance_beats: How many beats early a note can be to still count for the next segment
    """
    beat_notes = {}
    max_beat = 0
    early_notes = {}  # Store notes that might belong to the next segment
    
    for instrument in midi_file.instruments:
        for note in instrument.notes:
            # Calculate precise beat positions
            precise_start = note.start / midi_file.ticks_per_beat
            precise_end = note.end / midi_file.ticks_per_beat
            
            beat_start = int(precise_start)
            beat_end = int(precise_end)
            
            # Check if note starts close to the next beat boundary
            fractional_part = precise_start - beat_start
            is_anticipatory = fractional_part >= (1.0 - tolerance_beats)
            
            note_data = {
                'pitch': note.pitch,
                'velocity': note.velocity,
                'start': note.start,
                'end': note.end,
                'precise_start': precise_start,
                'is_anticipatory': is_anticipatory
            }
            
            # Add note to all beats it spans
            for beat in range(beat_start, beat_end + 1):
                if beat not in beat_notes:
                    beat_notes[beat] = []
                beat_notes[beat].append(note_data)
                max_beat = max(max_beat, beat)
            
            # If note is anticipatory, also consider it for the next beat
            if is_anticipatory and beat_start + 1 <= beat_end + 1:
                next_beat = beat_start + 1
                if next_beat not in early_notes:
                    early_notes[next_beat] = []
                early_notes[next_beat].append(note_data)
                max_beat = max(max_beat, next_beat)
    
    return beat_notes, early_notes, max_beat

def identify_chord_with_early_notes(regular_notes, early_notes=None):
    """
    Identify chord considering both regular notes and potentially early notes.
    """
    # First, try with just regular notes
    if regular_notes:
        regular_chord, regular_confidence = identify_chord_with_confidence(regular_notes)
    else:
        regular_chord, regular_confidence = None, 0
    
    # If we have early notes, try including them
    if early_notes:
        combined_notes = regular_notes + early_notes
        combined_chord, combined_confidence = identify_chord_with_confidence(combined_notes)
        
        # If including early notes gives a much better result, use it
        if combined_confidence > regular_confidence + 0.5:  # Threshold for improvement
            return combined_chord, combined_confidence, True  # True = used early notes
    
    return regular_chord, regular_confidence, False  # False = didn't use early notes

def analyze_midi_chord_progression(midi_file_path, segment_size=2, tolerance_beats=0.15):
    """
    Analyze MIDI file with timing tolerance for anticipatory playing.
    """
    midi_file = miditoolkit.MidiFile(midi_file_path)
    print(f"Analyzing MIDI file: {midi_file_path}")
    print(f"Ticks per beat: {midi_file.ticks_per_beat}")
    print(f"Using timing tolerance: {tolerance_beats} beats")
    
    # Extract notes with timing tolerance
    beat_notes, early_notes, max_beat = extract_notes_with_timing_tolerance(
        midi_file, tolerance_beats
    )
    
    # Analyze each beat with timing tolerance
    beat_analysis = []
    timing_adjustments = []
    
    for beat in range(max_beat + 1):
        regular_notes = beat_notes.get(beat, [])
        early_notes_for_beat = early_notes.get(beat, [])
        
        if not regular_notes and not early_notes_for_beat:
            continue
        
        # Try chord detection with timing tolerance
        chord, confidence, used_early = identify_chord_with_early_notes(
            regular_notes, early_notes_for_beat
        )
        
        # Track when we use timing adjustments
        if used_early:
            timing_adjustments.append(beat)
            print(f"🎵 Beat {beat}: Used timing tolerance (early notes detected)")
        
        # Extract pitch classes for debugging
        all_notes = regular_notes + (early_notes_for_beat if used_early else [])
        pitch_classes = sorted(set(note['pitch'] % 12 for note in all_notes))
        
        print(f"Beat {beat}: Pitch Classes {pitch_classes}, Detected: {chord}" + 
              (" (with early notes)" if used_early else ""))
        
        beat_analysis.append((beat, pitch_classes, chord, used_early))
    
    # Group into 2-beat segments
    segments = []
    
    for seg_idx in range((max_beat + segment_size - 1) // segment_size):
        start_beat = seg_idx * segment_size
        end_beat = min(start_beat + segment_size - 1, max_beat)
        
        # Collect all notes for this segment (including timing-adjusted ones)
        segment_notes = []
        segment_used_early = False
        
        for beat in range(start_beat, end_beat + 1):
            regular_notes = beat_notes.get(beat, [])
            early_notes_for_beat = early_notes.get(beat, [])
            
            # Check if this beat used early notes in our analysis
            beat_used_early = any(beat == b for b, _, _, used in beat_analysis if used)
            
            if beat_used_early:
                segment_notes.extend(regular_notes + early_notes_for_beat)
                segment_used_early = True
            else:
                segment_notes.extend(regular_notes)
        
        if not segment_notes:
            continue
        
        # Get the dominant chord for this segment using voting
        segment_chords = [chord for b, _, chord, _ in beat_analysis 
                         if start_beat <= b <= end_beat and chord is not None]
        
        if segment_chords:
            chord_counts = Counter(segment_chords)
            dominant_chord = chord_counts.most_common(1)[0][0]
        else:
            dominant_chord = None
        
        segments.append({
            'start_beat': start_beat,
            'end_beat': end_beat,
            'chord': dominant_chord,
            'used_timing_tolerance': segment_used_early,
            'segment_idx': seg_idx
        })
        
        timing_note = " (timing adjusted)" if segment_used_early else ""
        print(f"Segment {seg_idx+1} (Beats {start_beat}-{end_beat}): {dominant_chord}{timing_note}")
    
    # Create visualization
    create_tolerance_visualization(midi_file, segments, timing_adjustments, 
                                 f"chord_analysis_tolerance.png", midi_file_path)
    
    # Extract final progression
    chord_progression = [s['chord'] for s in segments if s['chord'] is not None]
    
    print(f"\nTiming adjustments made at beats: {timing_adjustments}")
    print("\nFinal Chord Progression:")
    print(" → ".join(chord_progression))
    
    return chord_progression, segments

def create_tolerance_visualization(midi_file, segments, timing_adjustments, output_file):
    """Create visualization highlighting timing tolerance adjustments"""
    import os
    
    # Create output directory
    output_dir = "generated_visualizations"
    os.makedirs(output_dir, exist_ok=True)
    
    # Get filename for title from the midi_file object
    if hasattr(midi_file, 'filename') and midi_file.filename:
        midi_filename = os.path.splitext(os.path.basename(midi_file.filename))[0]
    else:
        # Fallback: extract from output_file name
        midi_filename = os.path.splitext(output_file)[0].replace('chord_analysis_tolerance', '').replace('_', '')
    
    # Update output file path to include directory
    output_file = os.path.join(output_dir, output_file)
    
    plt.figure(figsize=(14, 6))
    
    # Extract note data
    note_data = []
    for instrument in midi_file.instruments:
        for note in instrument.notes:
            beat_start = note.start / midi_file.ticks_per_beat
            beat_end = note.end / midi_file.ticks_per_beat
            note_data.append((beat_start, beat_end, note.pitch))
    
    # Plot notes
    for start, end, pitch in note_data:
        plt.plot([start, end], [pitch, pitch], linewidth=2)
    
    # Mark segments with chords
    y_pos = 50
    for segment in segments:
        if segment['chord'] is not None:
            start = segment['start_beat']
            end = segment['end_beat'] + 1
            
            # Use different colors for timing-adjusted segments
            color = 'lightblue' if segment['used_timing_tolerance'] else 'lightgreen'
            plt.axvspan(start, end, alpha=0.3, color=color)
            
            plt.text((start + end) / 2, y_pos, segment['chord'], 
                     horizontalalignment='center', fontsize=12, fontweight='bold')
    
    # Highlight beats where timing tolerance was used
    for beat in timing_adjustments:
        plt.axvline(x=beat, color='red', linestyle='--', alpha=0.7, linewidth=1)
        plt.text(beat, 45, 'T', fontsize=8, ha='center')
    
    plt.xlabel('Time (beats)')
    plt.ylabel('MIDI Pitch')
    plt.title(f'Chord Analysis - {midi_filename} - Timing Tolerance')
    plt.grid(True, alpha=0.3)
    
    # Add legend
    plt.text(0.02, 0.98, 'Green: Normal timing\nBlue: Timing adjusted\nRed dashed: Early notes detected', 
             transform=plt.gca().transAxes, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.savefig(output_file)
    print(f"\nVisualization saved as '{output_file}'")

def main():
    midi_file_path = 'midi_samples/2 4ths.mid'
    
    print("=== CHORD DETECTION WITH TIMING TOLERANCE ===")
    progression, segments = analyze_midi_chord_progression(
        midi_file_path, 
        segment_size=2, 
        tolerance_beats=0.15  # 0.15 beats = about 150ms at 100 BPM
    )

if __name__ == "__main__":
    main()