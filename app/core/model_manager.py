"""Enhanced model manager with better error handling."""

import logging
import sys
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Try importing the model manager, but handle missing dependencies gracefully
try:
    from model_manager import MagentaModelManager
    MAGENTA_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Magenta not available: {e}. Running in mock mode.")
    MAGENTA_AVAILABLE = False
    
    # Create a mock class for testing
    class MagentaModelManager:
        def __init__(self):
            self.bass_rnn = None
            self.drum_rnn = None

from .exceptions import ModelNotLoadedError


class ModelManagerService:
    """Service for managing Magenta models with lifecycle management."""
    
    def __init__(self):
        self._model_manager: Optional[MagentaModelManager] = None
        self._bass_rnn = None
        self._drum_rnn = None
        self._is_loaded = False
    
    async def load_models(self) -> None:
        """Load Magenta models on startup."""
        logger.info("🚀 MIDI Analysis API starting up...")
        
        if not MAGENTA_AVAILABLE:
            logger.warning("⚠️ Running in MOCK MODE - Magenta models not available")
            self._model_manager = MagentaModelManager()  # Mock version
            self._bass_rnn = None
            self._drum_rnn = None
            self._is_loaded = False
            return
        
        logger.info("🔄 Loading Magenta models (this happens ONCE)...")
        
        try:
            self._model_manager = MagentaModelManager()
            self._bass_rnn = self._model_manager.bass_rnn
            self._drum_rnn = self._model_manager.drum_rnn
            self._is_loaded = True
            
            logger.info("✅ Models loaded! MIDI Analysis API ready with FORCED 8-chord rule!")
            
        except Exception as e:
            logger.error(f"❌ Failed to load models: {e}")
            logger.warning("⚠️ Falling back to MOCK MODE")
            self._model_manager = MagentaModelManager()  # Mock version
            self._bass_rnn = None
            self._drum_rnn = None
            self._is_loaded = False
    
    def is_loaded(self) -> bool:
        """Check if models are loaded."""
        return self._is_loaded and self._model_manager is not None
    
    def get_model_manager(self) -> MagentaModelManager:
        """Get the model manager instance."""
        if not self._is_loaded or self._model_manager is None:
            raise ModelNotLoadedError("Models not loaded. Call load_models() first.")
        return self._model_manager
    
    def get_bass_rnn(self):
        """Get the bass RNN model."""
        if not self._is_loaded or self._bass_rnn is None:
            raise ModelNotLoadedError("Bass RNN model not loaded.")
        return self._bass_rnn
    
    def get_drum_rnn(self):
        """Get the drum RNN model."""
        if not self._is_loaded or self._drum_rnn is None:
            raise ModelNotLoadedError("Drum RNN model not loaded.")
        return self._drum_rnn
    
    def get_health_status(self) -> dict:
        """Get detailed health status of models."""
        return {
            "models_loaded": self.is_loaded(),
            "bass_model": self._bass_rnn is not None,
            "drum_model": self._drum_rnn is not None,
        }


# Global model manager service instance
model_service = ModelManagerService()