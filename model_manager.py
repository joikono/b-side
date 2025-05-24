# model_manager.py - Handle model loading efficiently

import os
from magenta.models.melody_rnn import melody_rnn_sequence_generator
from magenta.models.drums_rnn import drums_rnn_sequence_generator
from magenta.models.shared import sequence_generator_bundle

class MagentaModelManager:
    """
    Singleton class to manage Magenta model loading.
    Models are loaded once and reused across the application.
    """
    _instance = None
    _models_loaded = False
    _bass_rnn = None
    _drum_rnn = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MagentaModelManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if not self._models_loaded:
            self.initialize_models()
    
    def initialize_models(self):
        """Load and initialize Magenta models once."""
        if self._models_loaded:
            print("✅ Models already loaded!")
            return
        
        print("🔄 Loading Magenta models...")
        
        # Check if model files exist
        bass_bundle_path = 'basic_rnn.mag'
        drum_bundle_path = 'drum_kit_rnn.mag'
        
        if not os.path.exists(bass_bundle_path):
            raise FileNotFoundError(f"Model file not found: {bass_bundle_path}")
        if not os.path.exists(drum_bundle_path):
            raise FileNotFoundError(f"Model file not found: {drum_bundle_path}")
        
        try:
            # Load bundles
            bass_bundle = sequence_generator_bundle.read_bundle_file(bass_bundle_path)
            drum_bundle = sequence_generator_bundle.read_bundle_file(drum_bundle_path)
            
            # Initialize generators
            bass_map = melody_rnn_sequence_generator.get_generator_map()
            drum_map = drums_rnn_sequence_generator.get_generator_map()
            
            self._bass_rnn = bass_map['basic_rnn'](checkpoint=None, bundle=bass_bundle)
            self._drum_rnn = drum_map['drum_kit'](checkpoint=None, bundle=drum_bundle)
            
            # Initialize models (this is the slow part)
            print("🧠 Initializing bass model...")
            self._bass_rnn.initialize()
            print("🥁 Initializing drum model...")
            self._drum_rnn.initialize()
            
            self._models_loaded = True
            print("✅ All Magenta models loaded successfully!")
            
        except Exception as e:
            print(f"❌ Error loading models: {e}")
            raise
    
    @property
    def bass_rnn(self):
        """Get the bass RNN generator."""
        if not self._models_loaded:
            self.initialize_models()
        return self._bass_rnn
    
    @property
    def drum_rnn(self):
        """Get the drum RNN generator."""
        if not self._models_loaded:
            self.initialize_models()
        return self._drum_rnn
    
    def is_loaded(self):
        """Check if models are loaded."""
        return self._models_loaded

# Global instance - models loaded once per Python session
model_manager = MagentaModelManager()

def get_models():
    """
    Convenience function to get both models.
    Returns: (bass_rnn, drum_rnn)
    """
    return model_manager.bass_rnn, model_manager.drum_rnn