"""
Generates complete musical arrangements using Magenta AI models.
Takes 8 chord roots (from 2-beat melody analysis) and creates
bass lines and drum patterns.

KEY FEATURES:
• 🎵 8-chord progression support (2-beat segments)
• 🥁 AI-generated drum patterns
• 🎸 AI-generated bass lines
• Configurable complexity and style parameters
• 📊 Complete MIDI arrangement output

WORKFLOW:
1. Download/load Magenta model bundles
2. Create chord progression from 8 chord roots
3. Generate AI bass line and drum pattern
4. Combine into complete arrangement
5. Export as MIDI file
"""

from magenta.models.melody_rnn import melody_rnn_sequence_generator  
from magenta.models.drums_rnn import drums_rnn_sequence_generator
from magenta.models.shared import sequence_generator_bundle  
from note_seq.protobuf import generator_pb2  
from note_seq.notebook_utils import download_bundle
import note_seq  
import time
import os

def initialize_magenta_models():
    """
    Download and initialize Magenta models.
    Returns bass_rnn and drum_rnn generators.
    """
    print("Initializing Magenta models...")
    
    # Download bundles if they don't exist
    try:
        bass_bundle = sequence_generator_bundle.read_bundle_file('basic_rnn.mag')
        drum_bundle = sequence_generator_bundle.read_bundle_file('drum_kit_rnn.mag')
        print("Found existing model bundles.")
    except:
        print("Downloading model bundles...")
        download_bundle('basic_rnn.mag', '.')
        download_bundle('drum_kit_rnn.mag', '.')
        bass_bundle = sequence_generator_bundle.read_bundle_file('basic_rnn.mag')
        drum_bundle = sequence_generator_bundle.read_bundle_file('drum_kit_rnn.mag')
        print("Model bundles downloaded successfully.")
    
    # Initialize generators
    bass_map = melody_rnn_sequence_generator.get_generator_map()
    drum_map = drums_rnn_sequence_generator.get_generator_map()
    bass_rnn = bass_map['basic_rnn'](checkpoint=None, bundle=bass_bundle)
    drum_rnn = drum_map['drum_kit'](checkpoint=None, bundle=drum_bundle)
    bass_rnn.initialize()
    drum_rnn.initialize()
    
    print("Magenta models initialized successfully!")
    return bass_rnn, drum_rnn

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

def generate_arrangement_from_chords(
    chord_progression,               # List of 8 chord names (e.g., ['C', 'G', 'Am', 'F', ...])
    bpm=100,                        # Fixed tempo for MVP
    bass_complexity=2,              # Temperature for bass generation
    drum_complexity=1,              # Temperature for drum generation
    hi_hat_divisions=5,             # Divisions per beat for hi-hat
    snare_beats=(2, 4),             # Which beats get snare hits
    output_file='generated_arrangement.mid',
    bass_rnn=None,                  # Pre-initialized bass generator
    drum_rnn=None                   # Pre-initialized drum generator
):
    """
    Generate a complete arrangement from 8 chord names.
    Each chord represents a 2-beat segment (half measure at 100 BPM).
    """
    
    # Initialize models if not provided
    if bass_rnn is None or drum_rnn is None:
        bass_rnn, drum_rnn = initialize_magenta_models()
    
    print(f"🎵 Generating arrangement from chord progression: {' → '.join(chord_progression)}")
    
    # Convert chord names to MIDI notes
    chord_roots = [chord_name_to_midi_note(chord, octave=3) for chord in chord_progression]
    print(f"Chord roots (MIDI): {chord_roots}")
    
    # Setup timing constants
    # Each chord is 2 beats (half measure) at 100 BPM
    beat_s = 60 / bpm                                      # seconds per beat
    chord_duration = 2 * beat_s                            # 2 beats per chord
    total_duration = len(chord_progression) * chord_duration  # total arrangement duration
    
    print(f"Total duration: {total_duration:.1f} seconds ({len(chord_progression)} chords × 2 beats each)")
    
    # Create root sequence with chord progression
    seed = note_seq.NoteSequence()
    seed.ticks_per_quarter = 220                           # standard quantization
    seed.tempos.add(qpm=bpm)                               # set tempo
    seed.time_signatures.add(
        numerator=4,
        denominator=4,
        time=0
    )
    
    # Add chord roots (each lasting 2 beats)
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
    
    # Transpose bass down one octave
    for n in bass_seq.notes:
        n.pitch = max(0, n.pitch - 12)
    
    # Combine everything into final sequence
    combined = note_seq.NoteSequence()
    combined.ticks_per_quarter = seed.ticks_per_quarter
    combined.tempos.extend(seed.tempos)
    combined.time_signatures.extend(seed.time_signatures)
    
    # Add chord roots as bass notes
    for n in seed.notes:
        new_note = combined.notes.add()
        new_note.CopyFrom(n)
        new_note.instrument = 0      # Bass channel
        new_note.program = 33        # Electric Bass (finger)
        new_note.is_drum = False
    
    # Add AI-generated bass notes
    for n in bass_seq.notes:
        # Skip primer notes that we already added from the seed
        if n.start_time < chord_duration:
            continue
        
        new_note = combined.notes.add()
        new_note.CopyFrom(n)
        new_note.instrument = 0      # Bass channel
        new_note.program = 33        # Electric Bass (finger)
        new_note.is_drum = False
    
    # Add drum notes
    for n in drum_seq.notes:
        new_note = combined.notes.add()
        new_note.CopyFrom(n)
        new_note.instrument = 9  # Drum channel (GM standard)
        new_note.is_drum = True
    
    # Set total duration and export
    combined.total_time = max(n.end_time for n in combined.notes)
    note_seq.sequence_proto_to_midi_file(combined, output_file)
    print(f"Generated arrangement saved to {output_file}")
    print(f"Duration: {combined.total_time:.1f} seconds")
    
    return output_file # combined

def test_arrangement_generator():
    """Test the arrangement generator with a sample chord progression."""
    print("=== TESTING MAGENTA ARRANGEMENT GENERATOR ===")
    
    # Sample 8-chord progression (2-beat segments)
    test_chords = ['C', 'C', 'G', 'G', 'Am', 'Am', 'F', 'F']
    
    # Initialize models once
    bass_rnn, drum_rnn = initialize_magenta_models()
    
    # Generate arrangement
    arrangement = generate_arrangement_from_chords(
        chord_progression=test_chords,
        bpm=100,
        bass_complexity=2,
        drum_complexity=1,
        hi_hat_divisions=4,
        snare_beats=(2, 4),
        output_file='test_arrangement.mid',
        bass_rnn=bass_rnn,
        drum_rnn=drum_rnn
    )
    
    print("Test completed successfully!")
    return arrangement

def generate_arrangement(chord_progression, bpm=100, bass_complexity=2, drum_complexity=1, 
                        hi_hat_divisions=4, snare_beats=(2, 4), output_file='arrangement.mid'):
    """
    Generate a full arrangement from a chord progression.
    Returns Path to generated MIDI file
    """
    from model_manager import get_models
    
    print(f"Generating arrangement for: {' → '.join(chord_progression)}")
    print(f"Settings: BPM={bpm}, Bass={bass_complexity}, Drums={drum_complexity}")
    
    # Get pre-loaded models
    bass_rnn, drum_rnn = get_models()
    
    # Use your existing generate_arrangement_from_chords function
    arrangement = generate_arrangement_from_chords(
        chord_progression=chord_progression,
        bpm=bpm,
        bass_complexity=bass_complexity,
        drum_complexity=drum_complexity,
        hi_hat_divisions=hi_hat_divisions,
        snare_beats=snare_beats,
        output_file=output_file,
        bass_rnn=bass_rnn,
        drum_rnn=drum_rnn
    )
    
    print(f"Arrangement saved as: {output_file}")
    return output_file

def get_user_complexity_settings():
    """Get complexity preferences from user."""
    print("\nARRANGEMENT COMPLEXITY SETTINGS")
    print("=" * 40)
    
    # Bass complexity
    print("Bass Complexity:")
    print("  1 = Simple (root notes)")
    print("  2 = Medium (walking bass)")
    print("  3 = Complex (jazz-style)")
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
    
    return bass_complexity, drum_complexity, bpm



if __name__ == "__main__":
    # Run test
    test_arrangement_generator()