# chord_or_melody.py - Enhanced with stretching and visualization for recorded MIDI

import mido
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from collections import defaultdict
import os

def detect_midi_type_with_stretching_and_viz(midi_file, output_dir="generated_visualizations"):
    """
    Detect if MIDI is chord progression or melody, apply stretching like force_exactly_8_chords_analysis,
    and generate a visualization showing the analysis result.
    """
    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"🔍 Analyzing MIDI type with stretching: {midi_file}")
        
        # FIXED: Use the existing melody analyzer timing extraction
        from melody_analyzer2 import extract_melody_with_timing
        
        # Extract notes using the same method as force_exactly_8_chords_analysis
        notes, ticks_per_beat = extract_melody_with_timing(midi_file, tolerance_beats=0.2)
        
        if not notes:
            print("❌ No notes found in MIDI file")
            return "unknown", None
        
        print(f"🎵 Extracted {len(notes)} notes using melody_analyzer2")
        
        # Apply stretching logic (same as force_exactly_8_chords_analysis)
        stretched_events = apply_stretching_to_melody_notes(notes)
        
        # Analyze the stretched events
        analysis_result = analyze_polyphony_patterns(stretched_events)
        
        # Generate visualization
        viz_filename = generate_chord_melody_visualization(
            stretched_events, 
            analysis_result, 
            midi_file, 
            output_dir
        )
        
        print(f"🎵 Classification: {analysis_result['classification']}")
        
        return analysis_result['classification'], viz_filename
        
    except Exception as e:
        print(f"❌ Error analyzing MIDI file: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return "error", None

def apply_stretching_to_melody_notes(melody_notes):
    """
    Apply the same stretching logic as force_exactly_8_chords_analysis to melody analyzer notes.
    """
    if not melody_notes:
        return melody_notes
    
    # Convert melody analyzer format to our analysis format
    note_events = []
    for note in melody_notes:
        note_events.append({
            'note': note.get('pitch', 60),  # MIDI note number
            'start': note['start'],         # Already in beats
            'end': note['end'],             # Already in beats  
            'duration': note['end'] - note['start'],
            'pitch_class': note.get('pitch_class', 0)
        })
    
    # Find actual musical content span (same logic as force_exactly_8_chords_analysis)
    music_start = min(note['start'] for note in note_events)
    music_end = max(note['end'] for note in note_events)
    actual_duration = music_end - music_start
    
    print(f"🎵 Original content span: {music_start:.2f} → {music_end:.2f} beats ({actual_duration:.2f} beats)")
    
    # Apply stretching if content is substantial (same logic as force_exactly_8_chords_analysis)
    if actual_duration > 4.0:  # Only stretch if we have substantial content
        print(f"🎯 Stretching timing from {actual_duration:.1f} beats to 16.0 beats...")
        
        # Calculate stretch factor (same as force_exactly_8_chords_analysis)
        target_duration = 16.0  # 16 beats
        stretch_factor = target_duration / actual_duration
        stretch_factor *= 0.98  # Apply the same correction factor
        
        offset = music_start
        
        # Normalize and stretch all note timings
        for note in note_events:
            note['start'] = (note['start'] - offset) * stretch_factor
            note['end'] = (note['end'] - offset) * stretch_factor
            note['duration'] = note['end'] - note['start']
        
        print(f"✅ Timing stretched by factor {stretch_factor:.2f}x")
    else:
        print(f"⚠️  Too little content ({actual_duration:.1f} beats). Using original timing.")
        # Still normalize to start at 0
        offset = music_start
        for note in note_events:
            note['start'] = note['start'] - offset
            note['end'] = note['end'] - offset
    
    return note_events

def analyze_polyphony_patterns(note_events):
    """
    Analyze polyphony patterns to determine if it's a chord progression or melody.
    Uses the stretched/normalized note events (in beats, not seconds).
    """
    if not note_events:
        return {
            'classification': 'unknown',
            'avg_polyphony': 0,
            'chord_ratio': 0,
            'max_polyphony': 0,
            'total_time_points': 0
        }
    
    # Group notes by time (with rounding to handle slight timing differences)
    # Using smaller rounding for beats (0.25 beats = quarter note resolution)
    notes_by_time = defaultdict(list)
    
    for note in note_events:
        # Round to nearest 0.25 beats to group near-simultaneous notes
        rounded_start = round(note['start'] * 4) / 4  # Quarter-beat resolution
        notes_by_time[rounded_start].append(note['note'])
    
    # Calculate polyphony metrics
    polyphony_counts = [len(notes) for _, notes in notes_by_time.items()]
    total_time_points = len(polyphony_counts)
    
    if total_time_points > 0:
        avg_polyphony = sum(polyphony_counts) / total_time_points
        times_with_multiple_notes = sum(1 for count in polyphony_counts if count >= 2)
        chord_ratio = times_with_multiple_notes / total_time_points
        max_polyphony = max(polyphony_counts)
    else:
        avg_polyphony = 0
        chord_ratio = 0
        max_polyphony = 0
        times_with_multiple_notes = 0
    
    # Classification logic (PLAY WITH THIS)
    if avg_polyphony >= 1.5 or chord_ratio >= 0.15:
        classification = "chord_progression"
    else:
        classification = "melody" # indent
    
    print(f"📊 Analysis metrics:")
    print(f"   Total time points: {total_time_points}")
    print(f"   Average notes per time point: {avg_polyphony:.2f}")
    print(f"   Maximum simultaneous notes: {max_polyphony}")
    print(f"   Percentage with multiple notes: {chord_ratio*100:.1f}%")
    print(f"   Times with multiple notes: {times_with_multiple_notes}")
    
    return {
        'classification': classification,
        'avg_polyphony': avg_polyphony,
        'chord_ratio': chord_ratio,
        'max_polyphony': max_polyphony,
        'total_time_points': total_time_points,
        'times_with_multiple_notes': times_with_multiple_notes,
        'notes_by_time': dict(notes_by_time)  # For visualization
    }

def generate_chord_melody_visualization(note_events, analysis_result, midi_file, output_dir):
    """
    Generate a visualization showing the analysis and classification result.
    """
    import time
    
    # Create unique filename
    timestamp = int(time.time())
    base_name = os.path.splitext(os.path.basename(midi_file))[0]
    viz_filename = f"{base_name}_chord_melody_analysis_{timestamp}.png"
    viz_path = os.path.join(output_dir, viz_filename)
    
    # Create the plot
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 10))
    
    # Plot 1: Note timeline (piano roll style)
    ax1.set_title(f'MIDI Analysis - {base_name}\nClassification: {analysis_result["classification"].upper()}', 
                  fontsize=16, fontweight='bold', pad=20)
    
    if note_events:
        for note in note_events:
            ax1.plot([note['start'], note['end']], [note['note'], note['note']], 
                    linewidth=3, alpha=0.7)
            ax1.plot(note['start'], note['note'], 'o', markersize=4, alpha=0.8)
    
    ax1.set_ylabel('MIDI Note Number')
    ax1.set_xlabel('Time (normalized beats)')
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, 16)  # Show full 16-beat span
    
    # Plot 2: Polyphony over time
    notes_by_time = analysis_result.get('notes_by_time', {})
    if notes_by_time:
        times = sorted(notes_by_time.keys())
        polyphony_values = [len(notes_by_time[t]) for t in times]
        
        ax2.bar(times, polyphony_values, width=0.2, alpha=0.7, 
               color='green' if analysis_result['classification'] == 'melody' else 'blue')
        ax2.axhline(y=1.5, color='red', linestyle='--', alpha=0.7, label='Chord Threshold (1.5)')
        ax2.set_ylabel('Simultaneous Notes')
        ax2.set_xlabel('Time (normalized beats)')
        ax2.set_title('Polyphony Analysis')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim(0, 16)
    
    # Plot 3: Analysis summary
    ax3.axis('off')
    
    # Classification result box
    classification = analysis_result['classification']
    color = 'lightgreen' if classification == 'melody' else 'lightblue'
    
    result_text = f"""
ANALYSIS RESULTS

Classification: {classification.upper()}

Key Metrics:
• Average Polyphony: {analysis_result['avg_polyphony']:.2f}
• Maximum Simultaneous Notes: {analysis_result['max_polyphony']}
• Chord Ratio: {analysis_result['chord_ratio']*100:.1f}%
• Total Time Points: {analysis_result['total_time_points']}
• Times with Multiple Notes: {analysis_result['times_with_multiple_notes']}

Classification Logic:
• CHORD PROGRESSION: Avg polyphony ≥ 1.5 OR chord ratio ≥ 15%
• MELODY: Avg polyphony < 1.5 AND chord ratio < 15%

Note: Timing has been normalized using the same stretching algorithm
as the melody analysis to ensure consistency across the system.
Timing resolution: 0.25 beats (quarter-note precision)
"""
    
    # Add background box
    bbox_props = dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.3)
    ax3.text(0.5, 0.5, result_text, transform=ax3.transAxes, fontsize=12,
             verticalalignment='center', horizontalalignment='center',
             bbox=bbox_props, family='monospace')
    
    plt.tight_layout()
    plt.savefig(viz_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"📊 Chord/Melody visualization saved: {viz_path}")
    return viz_filename

# Legacy function for backward compatibility
def detect_midi_type(midi_file):
    """
    Original function - now calls the enhanced version but returns only classification.
    """
    classification, _ = detect_midi_type_with_stretching_and_viz(midi_file)
    return classification

if __name__ == "__main__":
    # Test with a MIDI file
    midi_file = "midi_samples/test.mid"  # Change this path
    
    # Detect type with visualization
    result, viz_file = detect_midi_type_with_stretching_and_viz(midi_file)
    
    print(f"\n🎵 Final result: This MIDI file contains a {result}")
    if viz_file:
        print(f"📊 Visualization saved as: {viz_file}")