# MIDI Analysis API

A modern FastAPI-based MIDI analysis and arrangement generation system with voice integration and frontend support.

## 🚀 Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key for voice features
   ```

3. **Run the Application**
   ```bash
   python main.py
   ```

4. **Access the API**
   - API Server: http://localhost:8000
   - Interactive Documentation: http://localhost:8000/docs
   - Frontend: Open `astro-midi-app/` directory

## 📁 Project Structure

```
├── app/                    # Refactored FastAPI application
│   ├── config.py          # Configuration settings
│   ├── main.py            # FastAPI app and routes
│   ├── core/              # Core services and utilities
│   ├── models/            # Pydantic schemas
│   ├── services/          # Business logic services
│   └── utils/             # Helper functions
├── astro-midi-app/        # Frontend application
├── main.py                # Application entry point
├── requirements.txt       # Python dependencies
└── .env.example          # Environment configuration template
```

## 🎵 Features

- **MIDI Analysis**: Automatic chord progression and melody detection
- **8-Chord Harmonization**: Forced 8-chord analysis for consistent results
- **Arrangement Generation**: AI-powered backing track creation
- **Voice Commands**: OpenAI-powered intent classification
- **Visualization**: Real-time chord and melody visualization
- **File Processing**: MIDI duration fixing and optimization

## 🤖 AI Integration

- **OpenAI Whisper**: Voice transcription (configurable)
- **OpenAI GPT**: Intent classification and conversational AI
- **Magenta**: MIDI arrangement generation (when available)

## 🔧 Development

The application runs in mock mode when Magenta dependencies are not available, allowing for development and testing of the API structure.



AVAILABLE MODELS:
✅ melody_rnn_sequence_generator - Available
🎵 Available melody models: ['basic_rnn', 'mono_rnn', 'lookback_rnn', 'attention_rnn']

==================================================
✅ improv_rnn_sequence_generator - Available
🎸 Available improv models: ['basic_improv', 'attention_improv', 'chord_pitches_improv']

==================================================
✅ drums_rnn_sequence_generator - Available
🥁 Available drum models: ['one_drum', 'drum_kit']

==================================================
🔍 Checking what Magenta models are installed...
📁 Available model directories: ['arbitrary_image_stylization', 'coconet', 'drums_rnn', 'gansynth', 'image_stylization', 'improv_rnn', 'latent_transfer', 'melody_rnn', 'music_vae', 'nsynth', 'onsets_frames_transcription', 'performance_rnn', 'pianoroll_rnn_nade', 'piano_genie', 'polyphony_rnn', 'rl_tuner', 'score2perf', 'shared', 'sketch_rnn', 'svg_vae', '__pycache__']