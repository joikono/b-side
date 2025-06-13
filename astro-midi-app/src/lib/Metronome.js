export class Metronome {
    constructor() {
        this.isPlaying = false;
        this.bpm = 100;
        this.beatCount = 0;
        this.isCountingIn = false;
        this.countInBeat = 0;
        this.recordingStarted = false;
        this.audioContext = null;
        this.intervalId = null;
        this.nextNoteTime = 0;
        this.lookahead = 25.0;
        this.scheduleAheadTime = 0.1;
    }

    async initAudio() {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext ||
                window.webkitAudioContext)();

            if (this.audioContext.state === "suspended") {
                await this.audioContext.resume();
            }
        }
    }

    playClick(time, isCountIn) {
        const osc = this.audioContext.createOscillator();
        const envelope = this.audioContext.createGain();

        osc.connect(envelope);
        envelope.connect(this.audioContext.destination);

        osc.frequency.value = isCountIn ? 800 : 400;

        envelope.gain.setValueAtTime(0, time);
        envelope.gain.linearRampToValueAtTime(0.3, time + 0.001);
        envelope.gain.exponentialRampToValueAtTime(0.001, time + 0.1);

        osc.start(time);
        osc.stop(time + 0.1);
    }

    nextNote() {
        const secondsPerBeat = 60.0 / this.bpm;
        this.nextNoteTime += secondsPerBeat;

        if (this.isCountingIn) {
            this.countInBeat++;
            this.updateVisualIndicator(this.countInBeat, true);

            if (this.countInBeat >= 4) {
                this.isCountingIn = false;
                this.beatCount = 0;
                this.recordingStarted = true;
                setTimeout(() => this.startMIDIRecording(), 50);
            }
        } else {
            this.beatCount++;
            this.updateVisualIndicator(this.beatCount, false);
        }
    }

    scheduleNote() {
        while (
            this.nextNoteTime <
            this.audioContext.currentTime + this.scheduleAheadTime
        ) {
            this.playClick(this.nextNoteTime, this.isCountingIn);
            this.nextNote();
        }
    }

    scheduler() {
        this.scheduleNote();

        if (this.isPlaying) {
            this.intervalId = setTimeout(
                () => this.scheduler(),
                this.lookahead,
            );
        }
    }

    async start(bpm, countIn = true) {
        try {
            await this.initAudio();

            this.bpm = bpm;
            this.beatCount = 0;
            this.countInBeat = 0;
            this.isCountingIn = countIn;
            this.recordingStarted = false;
            this.isPlaying = true;

            this.nextNoteTime = this.audioContext.currentTime;
            this.scheduler();
        } catch (error) {
            console.error("Error initializing metronome:", error);
            throw error;
        }
    }

    updateVisualIndicator(beat, isCountIn) {
        const beatCircle = document.getElementById("beatCircle");
        const beatCount = document.getElementById("beatCount");

        if (!beatCircle || !beatCount) return;

        beatCircle.classList.remove("active", "count-in");
        beatCount.classList.remove("count-in", "recording");

        if (isCountIn) {
            beatCircle.classList.add("count-in");
            beatCount.classList.add("count-in");
            beatCount.textContent = beat.toString();
        } else {
            beatCircle.classList.add("active");
            beatCount.classList.add("recording");
            beatCount.textContent = `Beat ${beat}`;
        }

        setTimeout(() => {
            beatCircle.classList.remove("active", "count-in");
        }, 150);
    }

    stop() {
        if (this.isPlaying) {
            this.isPlaying = false;
            this.isCountingIn = false;
            this.recordingStarted = false;

            if (this.intervalId) {
                clearTimeout(this.intervalId);
                this.intervalId = null;
            }

            // Reset beat indicator whenever metronome stops
            const beatCircle = document.getElementById("beatCircle");
            const beatCount = document.getElementById("beatCount");

            if (beatCircle && beatCount) {
                beatCircle.classList.remove("active", "count-in");
                beatCount.classList.remove("count-in", "recording");
                beatCount.textContent = "";
            }

            console.log("🥁 Metronome stopped");
        }
    }

    startMIDIRecording() {
        console.log("🎵 Starting MIDI recording after count-in...");

        // Calculate much longer buffer time to ensure we capture everything
        const currentTempo = 100; // Fixed tempo
        const beatsPerSecond = currentTempo / 60;
        const durationFor16Beats = 16 / beatsPerSecond;

        // Add 3 second buffer to absolutely ensure we don't cut off
        const bufferedDuration = durationFor16Beats + 3.0;

        console.log(
            `Recording: ${bufferedDuration.toFixed(1)}s (${durationFor16Beats.toFixed(1)}s + 3s buffer) for 16 beats at ${currentTempo} BPM`,
        );

        // Wait a tiny bit to ensure metronome timing is perfect
        setTimeout(() => {
            startDirectCapture(bufferedDuration);
        }, 50); // 50ms delay for perfect sync
    }
}