# chord_analyzer_adapted.py - Chord analysis with stretching for recorded MIDI

import numpy as np
import matplotlib.pyplot as plt
import os
import time
from collections import Counter, defaultdict

# Chord definitions from original chord_analyzer.py
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
    'D#maj7': [3, 7, 10, 2], 'Emaj7': [4, 8, 11, 3], 'Fmaj7': [5, 9, 0, 4],
    'F#maj7': [6, 10, 1, 5], 'Gmaj7': [7, 11, 2, 6], 'G#maj7': [8, 0, 3, 7],
    'Amaj7': [9, 1, 4, 8], 'A#maj7': [10, 2, 5, 9], 'Bmaj7': [11, 3, 6, 10],
    
    # Minor 7th chords
    'Cm7': [0, 3, 7, 10], 'C#m7': [1, 4, 8, 11], 'Dm7': [2, 5, 9, 0], 
    'D#m7': [3, 6, 10, 1], 'Em7': [4, 7, 11, 2], 'Fm7': [5, 8, 0, 3],
    'F#m7': [6, 9, 1, 4], 'Gm7': [7, 10, 2, 5], 'G#m7': [8, 11, 3, 6],
    'Am7': [9, 0, 4, 7], 'A#m7': [10, 1, 5, 8], 'Bm7': [11, 2, 6, 9],
    
    # Dominant 7th chords
    'C7': [0, 4, 7, 10], 'C#7': [1, 5, 8, 11], 'D7': [2, 6, 9, 0],
    'D#7': [3, 7, 10, 1], 'E7': [4, 8, 11, 2], 'F7': [5, 9, 0, 3],
    'F#7': [6, 10, 1, 4], 'G7': [7, 11, 2, 5], 'G#7': [8, 0, 3, 6],
    'A7': [9, 1, 4, 7], 'A#7': [10, 2, 5, 8], 'B7': [11, 3, 6, 9]
}

def identify_chord_with_confidence(note_group):
    """
    Enhanced chord identification that returns a confidence score.
    Adapted to work with melody_analyzer2 note format.
    """
    if not note_group:
        return None, 0
    
    # Extract pitch classes from notes (melody_analyzer2 format)
    all_pitches = [note['pitch'] for note in note_group]
    pitch_classes = sorted(set(pitch % 12 for pitch in all_pitches))
    
    # Get bass note
    sorted_notes = sorted(note_group, key=lambda x: x['pitch'])
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
        score -= len(non_chord_tones) * 0.3
        
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

def apply_stretching_to_chord_analysis(notes):
    """
    Apply the same stretching logic as force_exactly_8_chords_analysis to chord analysis.
    """
    if not notes:
        return notes
    
    # Find actual musical content span (same logic as force_exactly_8_chords_analysis)
    music_start = min(note['start'] for note in notes)
    music_end = max(note['end'] for note in notes)
    actual_duration = music_end - music_start
    
    print(f"🎵 Chord analysis - Original content span: {music_start:.2f} → {music_end:.2f} beats ({actual_duration:.2f} beats)")
    
    # Apply stretching if content is substantial (same logic as force_exactly_8_chords_analysis)
    if actual_duration > 4.0:  # Only stretch if we have substantial content
        print(f"🎯 Chord analysis - Stretching timing from {actual_duration:.1f} beats to 16.0 beats...")
        
        # Calculate stretch factor (same as force_exactly_8_chords_analysis)
        target_duration = 16.0  # 16 beats
        stretch_factor = target_duration / actual_duration
        stretch_factor *= 0.98  # Apply the same correction factor
        
        offset = music_start
        
        # Normalize and stretch all note timings
        for note in notes:
            note['start'] = (note['start'] - offset) * stretch_factor
            note['end'] = (note['end'] - offset) * stretch_factor
        
        print(f"✅ Chord analysis - Timing stretched by factor {stretch_factor:.2f}x")
    else:
        print(f"⚠️  Chord analysis - Too little content ({actual_duration:.1f} beats). Using original timing.")
        # Still normalize to start at 0
        offset = music_start
        for note in notes:
            note['start'] = note['start'] - offset
            note['end'] = note['end'] - offset
    
    return notes

def group_notes_by_beats_with_tolerance(notes, tolerance_beats=0.15):
    """
    Group notes by beats with timing tolerance for anticipatory playing.
    Uses stretched note timing.
    """
    beat_notes = defaultdict(list)
    early_notes = defaultdict(list)
    max_beat = 0
    
    for note in notes:
        # Use stretched timing (already applied)
        precise_start = note['start']
        precise_end = note['end']
        
        beat_start = int(precise_start)
        beat_end = int(precise_end)
        
        # Check if note starts close to the next beat boundary
        fractional_part = precise_start - beat_start
        is_anticipatory = fractional_part >= (1.0 - tolerance_beats)
        
        # Add note to all beats it spans
        for beat in range(beat_start, beat_end + 1):
            beat_notes[beat].append(note)
            max_beat = max(max_beat, beat)
        
        # If note is anticipatory, also consider it for the next beat
        if is_anticipatory and beat_start + 1 <= beat_end + 1:
            next_beat = beat_start + 1
            early_notes[next_beat].append(note)
            max_beat = max(max_beat, next_beat)
    
    return beat_notes, early_notes, max_beat

def analyze_chord_progression_with_stretching(midi_file_path, segment_size=2, tolerance_beats=0.15):
    """
    ROBUST FIX: Add timing tolerance and note filtering to prevent chord misdetection
    """
    print(f"🎼 Analyzing chord progression: {midi_file_path}")
    print(f"🎯 Using ROBUST timing + chord detection")
    
    # STEP 1: Extract timing (same as before)
    from melody_analyzer2 import extract_melody_with_timing
    
    notes, ticks_per_beat = extract_melody_with_timing(midi_file_path, tolerance_beats=0.2)
    
    if not notes:
        print("❌ No notes found in MIDI file")
        return {
            'analysis_type': 'chord_progression',
            'chord_progression': ['C'] * 8,
            'segments': [],
            'key': 'C',
            'timing_adjustments': [],
            'tolerance_used': False
        }
    
    print(f"📊 Extracted {len(notes)} notes from MIDI")
    
    # STEP 2: Apply timing normalization (same as before)
    if notes:
        music_start = min(note['start'] for note in notes)
        music_end = max(note['end'] for note in notes)
        actual_duration = music_end - music_start
        
        print(f"🎵 Actual musical content: {music_start:.2f} → {music_end:.2f} beats ({actual_duration:.2f} beats)")
        
        if actual_duration > 4.0:
            print(f"🎯 Stretching timing from {actual_duration:.1f} beats to 16.0 beats...")
            
            stretch_factor = 16.0 / actual_duration
            stretch_factor *= 0.98
            offset = music_start
            
            for note in notes:
                note['start'] = (note['start'] - offset) * stretch_factor
                note['end'] = (note['end'] - offset) * stretch_factor
            
            print(f"✅ Timing stretched by factor {stretch_factor:.2f}x")
        else:
            print(f"⚠️  Too little content ({actual_duration:.1f} beats). Using default timing.")
            offset = music_start
            for note in notes:
                note['start'] = note['start'] - offset
                note['end'] = note['end'] - offset

    print(f"🎯 Final analysis timing: 0.00 → 16.00 beats")

    # STEP 3: ROBUST segment creation with improved note filtering
    segment_duration = 2.0
    segments = []
    
    print(f"🎯 Creating exactly 8 segments with ROBUST note filtering:")

    for seg_idx in range(8):
        segment_start = seg_idx * segment_duration
        segment_end = (seg_idx + 1) * segment_duration
        segment_center = (segment_start + segment_end) / 2
        
        print(f"  Segment {seg_idx+1}: {segment_start:.1f} → {segment_end:.1f} beats")

        # ROBUST NOTE SELECTION: Use multiple criteria
        segment_notes = []
        primary_notes = []
        secondary_notes = []
        
        for note in notes:
            note_start = note['start']
            note_end = note['end']
            note_center = (note_start + note_end) / 2
            
            # Primary notes: center falls within segment
            if segment_start <= note_center <= segment_end:
                primary_notes.append(note)
            
            # Secondary notes: any overlap with segment (but not center-based)
            elif (note_start < segment_end and note_end > segment_start):
                secondary_notes.append(note)
        
        # ROBUST SELECTION LOGIC:
        if primary_notes:
            # Use notes whose center falls in the segment (most reliable)
            segment_notes = primary_notes
            selection_method = "primary (center-based)"
        elif secondary_notes:
            # Fallback to overlap-based selection
            segment_notes = secondary_notes
            selection_method = "secondary (overlap-based)"
        else:
            # No notes found
            segment_notes = []
            selection_method = "none"
        
        # ADDITIONAL FILTERING: Remove notes that are too short (likely artifacts)
        if segment_notes:
            filtered_notes = []
            for note in segment_notes:
                note_duration = note['end'] - note['start']
                # Keep notes that are at least 0.1 beats long (filter out very short artifacts)
                if note_duration >= 0.1:
                    filtered_notes.append(note)
            
            if filtered_notes:
                segment_notes = filtered_notes
            # If all notes were filtered out, keep original (better than nothing)

        if segment_notes:
            # ROBUST CHORD DETECTION with additional debugging
            chord, confidence = identify_chord_with_confidence_robust(segment_notes)
            
            if chord is None:
                chord = segments[-1]['chord'] if segments else 'C'
                confidence = 0
            
            # Debug output with selection method
            pcs = sorted(set(note['pitch'] % 12 for note in segment_notes))
            note_details = [(note['pitch'], note['start'], note['end']) for note in segment_notes]
            print(f"    {len(segment_notes)} notes ({selection_method}), PCs: {pcs}")
            print(f"    Note details: {note_details}")
            print(f"    → Chord: {chord} (confidence: {confidence:.2f})")
            
        else:
            print(f"    No notes - using previous chord or C")
            chord = segments[-1]['chord'] if segments else 'C'
            confidence = 0
        
        # Create segment data
        segment_data = {
            'start_beat': segment_start,
            'end_beat': segment_end,
            'chord': chord,
            'confidence': confidence,
            'used_timing_tolerance': False,
            'segment_idx': seg_idx,
            'notes': segment_notes,
            'selection_method': selection_method if segment_notes else 'fallback'
        }
        segments.append(segment_data)
    
    # STEP 4: Extract final progression (same as before)
    chord_progression = [s['chord'] for s in segments]
    
    while len(chord_progression) < 8:
        chord_progression.append(chord_progression[-1] if chord_progression else 'C')
    chord_progression = chord_progression[:8]
    
    # Key detection
    chord_counter = Counter(chord_progression)
    most_common_chord = chord_counter.most_common(1)[0][0] if chord_counter else 'C'
    
    if most_common_chord.endswith('m'):
        detected_key = most_common_chord
    else:
        detected_key = most_common_chord.replace('7', '').replace('maj', '')
    
    # Generate visualization
    create_chord_progression_visualization(
        notes, segments, [], midi_file_path
    )
    
    print(f"\n🎵 ROBUST 8-chord analysis results:")
    print(f"  Progression: {' → '.join(chord_progression)}")
    print(f"🎼 Detected key: {detected_key}")
    print(f"✅ ROBUST: Better timing tolerance + note filtering!")
    
    return {
        'analysis_type': 'chord_progression',
        'chord_progression': chord_progression,
        'segments': segments,
        'key': detected_key,
        'timing_adjustments': [],
        'tolerance_used': False,
        'stretched_notes': notes
    }

def identify_chord_with_confidence_robust(note_group):
    """
    ROBUST chord identification with better handling of timing artifacts
    """
    if not note_group:
        return None, 0
    
    # Extract pitch classes from notes
    all_pitches = [note['pitch'] for note in note_group]
    pitch_classes = sorted(set(pitch % 12 for pitch in all_pitches))
    
    # ROBUST BASS NOTE DETECTION: Use the note with longest duration + lowest pitch
    # This prevents short artifacts from becoming the "bass" note
    bass_candidates = []
    for note in note_group:
        duration = note['end'] - note['start']
        bass_candidates.append((note['pitch'], duration, note))
    
    # Sort by pitch (lowest first), then by duration (longest first)
    bass_candidates.sort(key=lambda x: (x[0], -x[1]))
    bass_pc = bass_candidates[0][0] % 12
    
    # Calculate scores for all possible chords
    chord_scores = {}
    
    for chord_name, chord_pcs in CHORD_DEFINITIONS.items():
        score = 0
        
        # Check how many chord tones are present
        matched_tones = set(pitch_classes).intersection(set(chord_pcs))
        score += len(matched_tones) * 1.0
        
        # REDUCED penalty for non-chord tones (less sensitive to artifacts)
        non_chord_tones = set(pitch_classes) - set(chord_pcs)
        score -= len(non_chord_tones) * 0.2  # Reduced from 0.3
        
        # Bass note bonus/penalty (same as before)
        if bass_pc == chord_pcs[0]:  # Root in bass
            score += 2.0
        elif bass_pc in chord_pcs:  # Chord tone in bass
            score += 0.5
        else:  # Non-chord tone in bass
            score -= 1.0
        
        # Complete triad bonus
        if len(matched_tones) >= 3:
            score += 1.0
        
        # STABILITY BONUS: Prefer simpler chords (triads over 7th chords)
        if len(chord_pcs) == 3:  # Triad
            score += 0.3
            
        chord_scores[chord_name] = score
    
    # Find the best chord and confidence
    if not chord_scores:
        return None, 0
    
    max_score = max(chord_scores.values())
    best_chords = [name for name, score in chord_scores.items() if score == max_score]
    
    # Confidence calculation
    sorted_scores = sorted(chord_scores.values(), reverse=True)
    if len(sorted_scores) > 1:
        confidence = max_score - sorted_scores[1]
    else:
        confidence = max_score
    
    # Prefer simpler chords in case of ties
    if len(best_chords) > 1:
        simple_chords = [c for c in best_chords if len(c) <= 2]
        best_chord = simple_chords[0] if simple_chords else best_chords[0]
    else:
        best_chord = best_chords[0] if best_chords else None
    
    return best_chord, max(0, confidence)


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
        if combined_confidence > regular_confidence + 0.1:  # Threshold for improvement (PLAY WITH THIS)
            return combined_chord, combined_confidence, True  # True = used early notes
    
    return regular_chord, regular_confidence, False  # False = didn't use early notes

def create_chord_progression_visualization(notes, segments, timing_adjustments, midi_file_path):
    """
    Create visualization for chord progression analysis with stretching.
    """
    output_dir = "generated_visualizations"
    os.makedirs(output_dir, exist_ok=True)
    
    # Create filename
    timestamp = int(time.time())
    base_name = os.path.splitext(os.path.basename(midi_file_path))[0]
    viz_filename = f"{base_name}_chord_progression_{timestamp}.png"
    viz_path = os.path.join(output_dir, viz_filename)
    
    plt.figure(figsize=(16, 8))
    
    # Plot 1: Note timeline (piano roll style)
    plt.subplot(2, 1, 1)
    plt.title(f'Chord Progression Analysis - {base_name}\n(With Stretching & Timing Tolerance)', 
              fontsize=16, fontweight='bold', pad=20)
    
    if notes:
        for note in notes:
            plt.plot([note['start'], note['end']], [note['pitch'], note['pitch']], 
                    linewidth=3, alpha=0.7)
            plt.plot(note['start'], note['pitch'], 'o', markersize=4, alpha=0.8)
    
    # Mark segments with chords
    for segment in segments:
        if segment['chord'] is not None:
            start = segment['start_beat']
            end = segment['end_beat'] + 1
            
            # Use different colors for timing-adjusted segments
            color = 'lightblue' if segment['used_timing_tolerance'] else 'lightgreen'
            plt.axvspan(start, end, alpha=0.3, color=color)
            
            # Add chord labels
            plt.text((start + end) / 2, max(note['pitch'] for note in notes) - 5, 
                    segment['chord'], 
                    horizontalalignment='center', fontsize=12, fontweight='bold')
    
    # Highlight beats where timing tolerance was used
    for beat in timing_adjustments:
        plt.axvline(x=beat, color='red', linestyle='--', alpha=0.7, linewidth=1)
        plt.text(beat, min(note['pitch'] for note in notes) + 2, 'T', 
                fontsize=10, ha='center', color='red', fontweight='bold')
    
    plt.ylabel('MIDI Pitch')
    plt.xlabel('Time (normalized beats)')
    plt.grid(True, alpha=0.3)
    plt.xlim(0, 16)
    
    # Plot 2: Chord progression timeline
    plt.subplot(2, 1, 2)
    plt.title('Detected Chord Progression', fontsize=14, fontweight='bold')
    
    chord_colors = {'major': 'lightblue', 'minor': 'lightcoral', 'dominant': 'lightyellow', 'other': 'lightgray'}
    
    for i, segment in enumerate(segments):
        chord = segment['chord']
        if chord:
            # Determine chord color
            if chord.endswith('m') and not chord.endswith('maj'):
                color = chord_colors['minor']
            elif '7' in chord and not 'maj' in chord:
                color = chord_colors['dominant']
            elif any(ext in chord for ext in ['maj', 'M']):
                color = chord_colors['major']
            else:
                color = chord_colors['major'] if not chord.endswith('m') else chord_colors['minor']
            
            plt.barh(0, 2, left=i*2, height=0.5, color=color, alpha=0.7, edgecolor='black')
            plt.text(i*2 + 1, 0, chord, ha='center', va='center', fontweight='bold')
    
    plt.xlim(0, 16)
    plt.ylim(-0.5, 0.5)
    plt.ylabel('Chord')
    plt.xlabel('Time (beats)')
    plt.yticks([])
    plt.grid(True, alpha=0.3, axis='x')
    
    # Add legend
    legend_text = f"""Legend:
    Green: Normal timing | Blue: Timing adjusted | Red dashed: Early notes detected
    Chord progression: {' → '.join([s['chord'] for s in segments if s['chord']])}
    Timing adjustments: {len(timing_adjustments)} beats"""
    
    plt.text(0.02, 0.02, legend_text, transform=plt.gca().transAxes, 
             verticalalignment='bottom', fontsize=10,
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig(viz_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"📊 Chord progression visualization saved: {viz_path}")
    return viz_filename

# Test function
def test_chord_analysis(midi_file_path):
    """Test the adapted chord analysis"""
    result = analyze_chord_progression_with_stretching(midi_file_path)
    print(f"\n🎵 Test Results:")
    print(f"   Key: {result['key']}")
    print(f"   Progression: {' → '.join(result['chord_progression'])}")
    print(f"   Segments: {len(result['segments'])}")
    print(f"   Timing tolerance used: {result['tolerance_used']}")
    return result

if __name__ == "__main__":
    # Test with a MIDI file
    test_file = "midi_samples/test_chord.mid"
    test_chord_analysis(test_file)