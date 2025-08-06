# B-Side
A music composition co-pilot designed to assist musicians and music learners to materialize their ideas. Offering FastAPI-based MIDI analysis, an arrangement generation system and creative assistance with voice integration and frontend support.

**[Project Portfolio](https://www.johnoikonomou.com/b-side)** | **[Thesis Documentation](https://www.johnoikonomou.com/_files/ugd/d49114_6c851729d85e4f3cb2272b7ad23db074.pdf)**

## Quick Start

```bash
# Create and activate virtual environment
python -m venv midi-venv
midi-venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Run backend (OpenAI API key detected from system environment)
python main.py

# Run frontend (in separate terminal)
cd astro-midi-app
npm install
npm run dev
```

**Access Points:**
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:4321

## Core Features

- **Smart MIDI Analysis** - Automatic chord progression and melody detection
- **AI Arrangement Generation** - Create backing tracks with bass and drums
- **Voice Commands** - Natural language interaction for musical tasks  
- **8-Chord Harmonization** - Consistent harmonic analysis system
- **Real-time Visualization** - Interactive chord and melody displays

## Technology Stack

- **Backend**: FastAPI + Python
- **AI Models**: Magenta, OpenAI, Web Speech API
- **Frontend**: Astro + JavaScript
- **MIDI Processing**: mido, miditoolkit, pretty-midi, note-seq

## Project Structure

```
├── main.py                # Application entry point
├── app/                   # FastAPI application core
│   ├── config.py         # Configuration settings
│   ├── core/             # Business logic and services
│   └── models/           # Pydantic schemas
├── astro-midi-app/       # Frontend application
├── requirements.txt      # Python dependencies
└── README.md
```

## Available Magenta Models
- Melody RNN (basic_rnn, mono_rnn, lookback_rnn, attention_rnn)
- Improv RNN (basic_improv, attention_improv, chord_pitches_improv)  
- Drums RNN (one_drum, drum_kit)

## License

This project uses Google Magenta (Apache 2.0 License) and OpenAI API services.

```
├── main.py                # Application entry point
├── app/                   # Fast
