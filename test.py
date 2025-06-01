import os
from chord_or_melody import detect_midi_type
from chord_analyzer import analyze_midi_chord_progression
from melody_analyzer2 import analyze_midi_melody  # Use your four-style implementation
from arrangement_generator import generate_arrangement, get_user_complexity_settings
from model_manager import get_models

def select_melody_harmonization(progressions):
    """
    Let user choose which harmonization style to use.
    
    Args:
        progressions: Tuple of (simple_prog, folk_prog, bass_prog, phrase_prog)
    
    Returns:
        list: Selected chord progression
    """
    simple_prog, folk_prog, bass_prog, phrase_prog = progressions
    
    print("\nMELODY HARMONIZATION OPTIONS")
    print(f"1. Simple/Pop:        {' → '.join(simple_prog)}")
    print(f"2. Folk/Acoustic:     {' → '.join(folk_prog)}")
    print(f"3. Bass Foundation:   {' → '.join(bass_prog)}")
    print(f"4. Phrase Foundation: {' → '.join(phrase_prog)}")
    
    while True:
        try:
            choice = int(input("\nSelect harmonization style (1-4): "))
            if choice == 1:
                print(f"Selected: Simple/Pop - {' → '.join(simple_prog)}")
                return simple_prog
            elif choice == 2:
                print(f"Selected: Folk/Acoustic - {' → '.join(folk_prog)}")
                return folk_prog
            elif choice == 3:
                print(f"Selected: Bass Foundation - {' → '.join(bass_prog)}")
                return bass_prog
            elif choice == 4:
                print(f"Selected: Phrase Foundation - {' → '.join(phrase_prog)}")
                return phrase_prog
            else:
                print("Please enter 1, 2, 3, or 4")
        except ValueError:
            print("Please enter a number")

def main():
    """Main application flow."""
    print("MIDI ARRANGEMENT GENERATOR")
    
    # Initialize models (happens once)
    print("Loading AI models...")
    bass_rnn, drum_rnn = get_models()  # This loads models once
    
    # Input MIDI file
    midi_file = "midi_samples/C_G_F_F.mid"  # Change this to your file
    print(f"Analyzing: {midi_file}")
    
    if not os.path.exists(midi_file):
        print(f"File not found: {midi_file}")
        return
    
    # Detect if it's chord progression or melody
    print("\nDetecting MIDI type...")
    chord_or_melody = detect_midi_type(midi_file)
    print(f"Detected: {chord_or_melody}")
    
    if chord_or_melody == "chord_progression":
        # Analyze chord progression
        print("\nAnalyzing chord progression...")
        progression, segments = analyze_midi_chord_progression(
            midi_file, 
            segment_size=2, 
            tolerance_beats=0.15
        )
        
        # Debug: Let's see what we actually get
        print(f"DEBUG - progression type: {type(progression)}")
        print(f"DEBUG - progression content: {progression}")
        if progression:
            print(f"DEBUG - first element type: {type(progression[0])}")
            print(f"DEBUG - first element: {progression[0]}")
        
        # Handle different return formats
        if isinstance(progression[0], str):
            # If progression is already a list of chord names
            chord_list = progression
        else:
            # If progression contains tuples
            chord_list = [seg[3] for seg in progression]
            
        print(f"Chord progression: {' → '.join(chord_list)}")
        
    else:
        # Analyze melody and get harmonization options
        print("\nAnalyzing melody...")
        key, progressions, confidences, segments = analyze_midi_melody(
            midi_file,
            segment_size=2,
            tolerance_beats=0.15
        )
        
        print(f"Detected key: {key}")
        
        # Let user choose harmonization style
        chord_list = select_melody_harmonization(progressions)
    
    # Ensure we have chords to work with
    if not chord_list:
        print("No chords detected. Cannot generate arrangement.")
        return
    
    # Get arrangement complexity settings from user
    bass_complexity, drum_complexity, bpm = get_user_complexity_settings()
    
    # Create output directory and generate filename
    output_dir = "astro-midi-app/public/generated_arrangements"
    os.makedirs(output_dir, exist_ok=True)  # Create folder if it doesn't exist
    
    base_name = os.path.splitext(os.path.basename(midi_file))[0]
    output_file = os.path.join(output_dir, f"{base_name}_arrangement.mid")
    
    print(f"\nGenerating arrangement...")
    print(f"Chords: {' → '.join(chord_list)}")
    
    # Generate the arrangement
    try:
        result_file = generate_arrangement(
            chord_progression=chord_list,
            bpm=bpm,
            bass_complexity=bass_complexity,
            drum_complexity=drum_complexity,
            hi_hat_divisions=2,
            snare_beats=(2, 4),
            output_file=output_file
        )
        
        print(f"\nSUCCESS!")
        print(f"Arrangement saved as: {result_file}")
        print(f"You can now play {result_file} in your MIDI player!")
        
    except Exception as e:
        print(f"Error generating arrangement: {e}")

if __name__ == "__main__":
    main()