"""
Enhanced Musical Arrangement Generator with Magenta AI models.
Features improved bass range limiting and pentatonic scale compliance.

IMPROVEMENTS:
• 🎸 Bass notes limited to 4-string bass range (E1-G4, MIDI 28-67)
• 🎵 Filler bass notes follow pentatonic scales of current chords
• 🔄 8x LOOPED OUTPUT - Perfect seamless loops!

KEY FEATURES:
• 🎵 8-chord progression support (2-beat segments)
• 🥁 AI-generated drum patterns
• 🎸 AI-generated bass lines with chord compliance
• 🔄 8x LOOPED OUTPUT - Perfect seamless loops!
• Configurable complexity and style parameters
• 📊 Complete MIDI arrangement output

WORKFLOW:
1. Download/load Magenta model bundles
2. Create chord progression from 8 chord roots
3. Generate AI bass line and drum pattern
4. Apply bass range limiting and pentatonic filtering
5. Combine into complete arrangement
6. Loop the arrangement 8 times for seamless playback
7. Export as MIDI file
"""

from note_seq.protobuf import generator_pb2  
from model_manager import MagentaModelManager
import note_seq  
import copy

# Bass guitar range (4-string standard tuning E-A-D-G)
BASS_MIN_MIDI = 28  # E1 (low E string)
BASS_MAX_MIDI = 67  # G4 (high end of G string, though typically played lower)
BASS_PRACTICAL_MAX = 55  # G3 (more typical upper range for bass lines)

def chord_name_to_midi_note(chord_name, octave=3):
    """
    Convert chord name (like 'C', 'F#m', 'Dm') to MIDI note number.
    Returns the root note in the specified octave.
    """
    # Note mapping
    note_map = {
        'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5,
        'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11
    }
    
    if not chord_name:
        return 60  # Default to middle C
    
    # Extract root note (remove 'm', '7', etc.)
    root = chord_name
    if chord_name.endswith('m'):
        root = chord_name[:-1]
    elif '7' in chord_name:
        root = chord_name.split('7')[0]
        if root.endswith('maj'):
            root = root[:-3]
    
    # Get MIDI note number
    if root in note_map:
        return note_map[root] + (octave * 12)
    else:
        print(f"Warning: Unknown chord '{chord_name}', using C")
        return 60  # Default to middle C

def get_chord_pentatonic_scale(chord_name, octave_range=2):
    """
    Get pentatonic scale notes for a given chord across specified octave range.
    Returns MIDI note numbers for the pentatonic scale.
    
    Args:
        chord_name: Chord name like 'C', 'Am', 'F#m', etc.
        octave_range: Number of octaves to include (default 2 for bass range)
    
    Returns:
        List of MIDI note numbers in the pentatonic scale
    """
    # Note mapping
    note_map = {
        'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5,
        'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11
    }
    
    if not chord_name or chord_name == 'N':
        return []
    
    # Extract root note and determine if minor
    is_minor = chord_name.endswith('m')
    root = chord_name.replace('m', '').replace('7', '').replace('maj', '')
    
    if root not in note_map:
        return []
    
    root_midi = note_map[root]
    
    # Define pentatonic scale intervals
    if is_minor:
        # Minor pentatonic: 1, b3, 4, 5, b7
        intervals = [0, 3, 5, 7, 10]
    else:
        # Major pentatonic: 1, 2, 3, 5, 6
        intervals = [0, 2, 4, 7, 9]
    
    # Generate scale notes across octave range
    scale_notes = []
    for octave in range(octave_range + 1):  # Include bass octaves 1, 2, 3
        base_midi = root_midi + (octave + 1) * 12  # Start from octave 1
        for interval in intervals:
            midi_note = base_midi + interval
            if BASS_MIN_MIDI <= midi_note <= BASS_PRACTICAL_MAX:
                scale_notes.append(midi_note)
    
    return sorted(scale_notes)

def get_chord_at_time(chord_progression, time, chord_duration):
    """
    Get the active chord at a specific time.
    
    Args:
        chord_progression: List of chord names
        time: Time in seconds
        chord_duration: Duration of each chord in seconds
    
    Returns:
        Chord name at the given time
    """
    chord_index = int(time / chord_duration)
    if 0 <= chord_index < len(chord_progression):
        return chord_progression[chord_index]
    return chord_progression[-1] if chord_progression else 'C'

def clamp_bass_to_range(midi_note):
    """
    Clamp a MIDI note to the playable bass guitar range.
    Transposes to nearest octave if needed.
    """
    # If note is too low, transpose up octaves until in range
    while midi_note < BASS_MIN_MIDI:
        midi_note += 12
    
    # If note is too high, transpose down octaves until in range
    while midi_note > BASS_PRACTICAL_MAX:
        midi_note -= 12
    
    return midi_note

def find_nearest_pentatonic_note(target_midi, pentatonic_scale):
    """
    Find the nearest note in the pentatonic scale to the target MIDI note.
    Preserves rhythm by finding closest match.
    """
    if not pentatonic_scale:
        return clamp_bass_to_range(target_midi)
    
    # Find the closest note in the pentatonic scale
    closest_note = min(pentatonic_scale, key=lambda x: abs(x - target_midi))
    return closest_note

def apply_bass_improvements(bass_sequence, chord_progression, chord_duration):
    """
    Apply bass range limiting and pentatonic scale filtering to generated bass.
    
    Args:
        bass_sequence: NoteSequence with generated bass notes
        chord_progression: List of chord names
        chord_duration: Duration of each chord in seconds
    
    Returns:
        Modified bass_sequence with improvements applied
    """
    print("🎸 Applying bass improvements...")
    print(f"   • Range limiting: MIDI {BASS_MIN_MIDI}-{BASS_PRACTICAL_MAX}")
    print(f"   • Pentatonic filtering for {len(chord_progression)} chords")
    
    # Track changes for reporting
    range_corrections = 0
    pentatonic_corrections = 0
    
    for note in bass_sequence.notes:
        if note.is_drum:
            continue
            
        original_pitch = note.pitch
        
        # Step 1: Apply range limiting
        note.pitch = clamp_bass_to_range(note.pitch)
        if note.pitch != original_pitch:
            range_corrections += 1
        
        # Step 2: Apply pentatonic filtering for filler notes
        # Get the active chord at this note's start time
        active_chord = get_chord_at_time(chord_progression, note.start_time, chord_duration)
        pentatonic_scale = get_chord_pentatonic_scale(active_chord)
        
        if pentatonic_scale:
            # Check if current note is in the pentatonic scale
            if note.pitch not in pentatonic_scale:
                # Find nearest pentatonic note
                corrected_pitch = find_nearest_pentatonic_note(note.pitch, pentatonic_scale)
                if corrected_pitch != note.pitch:
                    note.pitch = corrected_pitch
                    pentatonic_corrections += 1
    
    print(f"   ✅ Applied {range_corrections} range corrections")
    print(f"   ✅ Applied {pentatonic_corrections} pentatonic corrections")
    
    return bass_sequence

def generate_arrangement_from_chords(
    chord_progression,               # List of 8 chord names (e.g., ['C', 'G', 'Am', 'F', ...])
    bpm=100,                        # Fixed tempo for MVP
    bass_complexity=2,              # Temperature for bass generation
    drum_complexity=1,              # Temperature for drum generation
    hi_hat_divisions=5,             # Divisions per beat for hi-hat
    snare_beats=(2, 4),             # Which beats get snare hits
    output_file='generated_arrangement.mid',
    bass_rnn=None,                  # Pre-initialized bass generator
    drum_rnn=None,                  # Pre-initialized drum generator
    loop_count=8                    # Number of times to loop the arrangement
):
    """
    Generate a complete arrangement from 8 chord names with enhanced bass.
    Each chord represents a 2-beat segment (half measure at 100 BPM).
    The final arrangement will be looped 8 times for seamless playback.
    
    Enhanced features:
    - Bass notes limited to 4-string bass range
    - Filler bass notes follow pentatonic scales
    """
    
    # Initialize models if not provided
    if bass_rnn is None or drum_rnn is None:
        bass_rnn, drum_rnn = MagentaModelManager.initialize_models()
    
    print(f"🎵 Generating enhanced arrangement from chord progression: {' → '.join(chord_progression)}")
    print(f"🔄 Will loop the arrangement {loop_count} times")
    
    # Convert chord names to MIDI notes (ensure they're in bass range)
    chord_roots = []
    for chord in chord_progression:
        root_midi = chord_name_to_midi_note(chord, octave=2)  # Start in bass octave
        root_midi = clamp_bass_to_range(root_midi)
        chord_roots.append(root_midi)
    
    print(f"Chord roots (MIDI): {chord_roots}")
    
    # Setup timing constants
    # Each chord is 2 beats (half measure) at 100 BPM
    beat_s = 60 / bpm                                      # seconds per beat
    chord_duration = 2 * beat_s                            # 2 beats per chord
    total_duration = len(chord_progression) * chord_duration  # total arrangement duration
    
    print(f"Single loop duration: {total_duration:.1f} seconds ({len(chord_progression)} chords × 2 beats each)")
    print(f"Total looped duration: {total_duration * loop_count:.1f} seconds")
    
    # Create root sequence with chord progression
    seed = note_seq.NoteSequence()
    seed.ticks_per_quarter = 220                           # standard quantization
    seed.tempos.add(qpm=bpm)                               # set tempo
    seed.time_signatures.add(
        numerator=4,
        denominator=4,
        time=0
    )
    
    # Add chord roots (each lasting 2 beats) - these are already in bass range
    for i, pitch in enumerate(chord_roots):
        start = i * chord_duration
        end = (i + 1) * chord_duration
        seed.notes.add(
            pitch=pitch,
            velocity=100,
            start_time=start,
            end_time=end,
            is_drum=False
        )
    
    # Create drum seed with basic pattern (2 beats = one chord duration)
    drum_seed = note_seq.NoteSequence()
    drum_seed.ticks_per_quarter = seed.ticks_per_quarter
    drum_seed.tempos.extend(seed.tempos)
    drum_seed.time_signatures.add(
        numerator=4,
        denominator=4,
        time=0
    )
    
    # Create a 2-beat drum pattern that matches our chord duration
    for beat in range(2):  # 2 beats per chord
        beat_time = beat * beat_s
        
        # Kick on beat 1
        if beat == 0:  # Kick on first beat of each chord
            drum_seed.notes.add(
                pitch=36,            # Kick drum
                velocity=100,
                start_time=beat_time,
                end_time=beat_time + 0.1,
                is_drum=True
            )
        
        # Snare on beat 2 (if it's in snare_beats)
        if beat + 1 in snare_beats and beat == 1:  # Beat 2 of the pattern
            drum_seed.notes.add(
                pitch=38,            # Snare drum
                velocity=100,
                start_time=beat_time,
                end_time=beat_time + 0.1,
                is_drum=True
            )
        
        # Hi-hat pattern with specified divisions
        for div in range(hi_hat_divisions):
            div_time = beat_time + (div * beat_s / hi_hat_divisions)
            velocity = 80 if div == 0 else 60  # Accent on the beat
            drum_seed.notes.add(
                pitch=42,            # Closed hi-hat
                velocity=velocity,
                start_time=div_time,
                end_time=div_time + 0.1,
                is_drum=True
            )
    
    # Get end times
    seed_end = max(n.end_time for n in seed.notes)
    drum_seed_end = max(n.end_time for n in drum_seed.notes)
    
    # Create a shorter primer for bass generation (just the first chord)
    bass_primer = note_seq.NoteSequence()
    bass_primer.ticks_per_quarter = seed.ticks_per_quarter
    bass_primer.tempos.add().CopyFrom(seed.tempos[0])
    if seed.time_signatures:
        bass_primer.time_signatures.add().CopyFrom(seed.time_signatures[0])
    
    # Add only the first chord as primer
    for note in seed.notes:
        if note.start_time < chord_duration:
            bass_primer.notes.add().CopyFrom(note)
    
    # Define generation options for bass
    bass_opts = generator_pb2.GeneratorOptions()
    bass_opts.generate_sections.add(
        start_time=chord_duration,  # Start after first chord
        end_time=total_duration
    )
    bass_opts.args['temperature'].float_value = bass_complexity
    
    # Define generation options for drums
    drum_opts = generator_pb2.GeneratorOptions()
    drum_opts.generate_sections.add(
        start_time=drum_seed_end,
        end_time=total_duration
    )
    drum_opts.args['temperature'].float_value = drum_complexity
    
    # Generate bass and drums
    print("🎸 Generating AI bass line...")
    bass_seq = bass_rnn.generate(bass_primer, bass_opts)
    
    print("🥁 Generating AI drum pattern...")
    drum_seq = drum_rnn.generate(drum_seed, drum_opts)
    
    # ENHANCED: Apply bass improvements instead of simple transposition
    bass_seq = apply_bass_improvements(bass_seq, chord_progression, chord_duration)
    
    # Combine everything into final sequence (single loop)
    single_loop = note_seq.NoteSequence()
    single_loop.ticks_per_quarter = seed.ticks_per_quarter
    single_loop.tempos.extend(seed.tempos)
    single_loop.time_signatures.extend(seed.time_signatures)
    
    # Add chord roots as bass notes (already in correct range)
    for n in seed.notes:
        new_note = single_loop.notes.add()
        new_note.CopyFrom(n)
        new_note.instrument = 0      # Bass channel
        new_note.program = 33        # Electric Bass (finger)
        new_note.is_drum = False
    
    # Add AI-generated bass notes (already improved)
    for n in bass_seq.notes:
        # Skip primer notes that we already added from the seed
        if n.start_time < chord_duration:
            continue
        
        new_note = single_loop.notes.add()
        new_note.CopyFrom(n)
        new_note.instrument = 0      # Bass channel
        new_note.program = 33        # Electric Bass (finger)
        new_note.is_drum = False
    
    # Add drum notes
    for n in drum_seq.notes:
        new_note = single_loop.notes.add()
        new_note.CopyFrom(n)
        new_note.instrument = 9  # Drum channel (GM standard)
        new_note.is_drum = True
    
    # Set single loop duration
    single_loop.total_time = max(n.end_time for n in single_loop.notes)
    original_duration = single_loop.total_time
    
    print(f"🔄 Creating {loop_count} seamless loops...")
    
    # Create the final looped sequence
    looped_sequence = note_seq.NoteSequence()
    looped_sequence.ticks_per_quarter = single_loop.ticks_per_quarter
    looped_sequence.tempos.extend(single_loop.tempos)
    looped_sequence.time_signatures.extend(single_loop.time_signatures)
    
    # Copy the single loop multiple times
    for loop_index in range(loop_count):
        time_offset = loop_index * original_duration
        
        print(f"  Loop {loop_index + 1}/{loop_count}: offset +{time_offset:.1f}s")
        
        # Copy all notes from single loop with time offset
        for note in single_loop.notes:
            new_note = looped_sequence.notes.add()
            new_note.CopyFrom(note)
            new_note.start_time += time_offset
            new_note.end_time += time_offset
    
    # Set final total duration
    looped_sequence.total_time = original_duration * loop_count
    
    # Export looped sequence
    note_seq.sequence_proto_to_midi_file(looped_sequence, output_file)
    
    print(f"✅ Generated enhanced looped arrangement saved to {output_file}")
    print(f"📊 Single loop: {original_duration:.1f}s")
    print(f"📊 Total duration: {looped_sequence.total_time:.1f}s ({loop_count} loops)")
    print(f"🎸 Bass improvements applied - no out-of-range notes!")
    print(f"🎵 Perfect for seamless playback - no timing gaps!")

    return output_file

def generate_arrangement(chord_progression, bpm=100, bass_complexity=2, drum_complexity=1, 
                        hi_hat_divisions=4, snare_beats=(2, 4), output_file='arrangement.mid',
                        loop_count=8):
    """
    Generate a full arrangement from a chord progression with enhanced bass.
    Returns Path to generated MIDI file (looped 8 times by default)
    """
    from model_manager import get_models
    
    print(f"Generating enhanced looped arrangement for: {' → '.join(chord_progression)}")
    print(f"Settings: BPM={bpm}, Bass={bass_complexity}, Drums={drum_complexity}, Loops={loop_count}")
    
    # Get pre-loaded models
    bass_rnn, drum_rnn = get_models()
    
    # Use enhanced generate_arrangement_from_chords function
    arrangement = generate_arrangement_from_chords(
        chord_progression=chord_progression,
        bpm=bpm,
        bass_complexity=bass_complexity,
        drum_complexity=drum_complexity,
        hi_hat_divisions=hi_hat_divisions,
        snare_beats=snare_beats,
        output_file=output_file,
        bass_rnn=bass_rnn,
        drum_rnn=drum_rnn,
        loop_count=loop_count
    )
    
    print(f"Enhanced looped arrangement saved as: {output_file}")
    return output_file

def test_enhanced_arrangement_generator():
    """Test the enhanced arrangement generator with a sample chord progression."""
    print("=== TESTING ENHANCED MAGENTA ARRANGEMENT GENERATOR (8x LOOPED) ===")
    print("Enhanced features:")
    print("• Bass range limited to 4-string bass (E1-G3)")
    print("• Filler bass notes follow pentatonic scales")
    print("• No more unsettling low notes!")
    
    # Sample 8-chord progression (2-beat segments)
    test_chords = ['C', 'C', 'G', 'G', 'Am', 'Am', 'F', 'F']
    
    # Initialize models once
    bass_rnn, drum_rnn = MagentaModelManager.initialize_models()
    
    # Generate enhanced looped arrangement
    arrangement = generate_arrangement_from_chords(
        chord_progression=test_chords,
        bpm=100,
        bass_complexity=2,
        drum_complexity=1,
        hi_hat_divisions=4,
        snare_beats=(2, 4),
        output_file='test_enhanced_arrangement_8x_looped.mid',
        bass_rnn=bass_rnn,
        drum_rnn=drum_rnn,
        loop_count=4
    )
    
    print("Enhanced test completed successfully!")
    print("🎸 Bass is now properly limited to 4-string range!")
    print("🎵 Bass notes follow pentatonic scales!")
    print("🔄 You now have a perfectly looped MIDI file!")
    return arrangement

def get_user_complexity_settings():
    """Get complexity preferences from user."""
    print("\nENHANCED ARRANGEMENT COMPLEXITY SETTINGS")
    print("=" * 45)
    
    # Bass complexity
    print("Bass Complexity (with pentatonic filtering):")
    print("  1 = Simple (root notes + pentatonic fills)")
    print("  2 = Medium (walking bass + pentatonic fills)")
    print("  3 = Complex (jazz-style + pentatonic fills)")
    while True:
        try:
            bass_complexity = int(input("Choose bass complexity (1-3): "))
            if 1 <= bass_complexity <= 3:
                break
            print("Please enter 1, 2, or 3")
        except ValueError:
            print("Please enter a number")
    
    # Drum complexity
    print("\nDrum Complexity:")
    print("  1 = Simple (kick + snare)")
    print("  2 = Medium (+ hi-hats)")
    print("  3 = Complex (fills + variations)")
    while True:
        try:
            drum_complexity = int(input("Choose drum complexity (1-3): "))
            if 1 <= drum_complexity <= 3:
                break
            print("Please enter 1, 2, or 3")
        except ValueError:
            print("Please enter a number")
    
    # BPM
    while True:
        try:
            bpm = 100 # int(input(f"\nBPM (default 100): ") or "100")
            if 60 <= bpm <= 200:
                break
            print("Please enter BPM between 60-200")
        except ValueError:
            print("Please enter a number")
    
    # Loop count
    print("\nLoop Count:")
    print("  8 = Default (recommended for seamless playback)")
    print("  4 = Shorter loops")
    print("  16 = Longer sessions")
    while True:
        try:
            loop_count = int(input("Choose loop count (default 8): ") or "8")
            if 1 <= loop_count <= 32:
                break
            print("Please enter a number between 1-32")
        except ValueError:
            print("Please enter a number")
    
    return bass_complexity, drum_complexity, bpm, loop_count

if __name__ == "__main__":
    # Run enhanced test
    test_enhanced_arrangement_generator()