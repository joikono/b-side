# debug_magenta.py - Let's see what's available in your Magenta installation

print("🔍 Checking Magenta installation...")

try:
    from magenta.models.melody_rnn import melody_rnn_sequence_generator
    print("✅ melody_rnn_sequence_generator - Available")
    
    # List available melody models
    melody_map = melody_rnn_sequence_generator.get_generator_map()
    print(f"🎵 Available melody models: {list(melody_map.keys())}")
    
except ImportError as e:
    print(f"❌ melody_rnn import error: {e}")

print("\n" + "="*50)

try:
    from magenta.models.improv_rnn import improv_rnn_sequence_generator
    print("✅ improv_rnn_sequence_generator - Available")
    
    # List available improv models
    improv_map = improv_rnn_sequence_generator.get_generator_map()
    print(f"🎸 Available improv models: {list(improv_map.keys())}")
    
except ImportError as e:
    print(f"❌ improv_rnn import error: {e}")
    print("🚨 improv_rnn is not available in your Magenta installation")

print("\n" + "="*50)

try:
    from magenta.models.drums_rnn import drums_rnn_sequence_generator
    print("✅ drums_rnn_sequence_generator - Available")
    
    # List available drum models
    drum_map = drums_rnn_sequence_generator.get_generator_map()
    print(f"🥁 Available drum models: {list(drum_map.keys())}")
    
except ImportError as e:
    print(f"❌ drums_rnn import error: {e}")

print("\n" + "="*50)
print("🔍 Checking what Magenta models are installed...")

try:
    import magenta.models
    import os
    models_dir = os.path.dirname(magenta.models.__file__)
    available_models = [d for d in os.listdir(models_dir) if os.path.isdir(os.path.join(models_dir, d))]
    print(f"📁 Available model directories: {available_models}")
except Exception as e:
    print(f"❌ Error checking models directory: {e}")