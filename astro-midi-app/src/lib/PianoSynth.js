export class PianoSynth {
    constructor() {
        this.audioContext = null;
        this.masterGain = null;
        this.dryGain = null;
        this.wetGain = null;
        this.reverbNode = null;
        this.activeNotes = new Map();
        this.volume = 0.2; // 20% volume (0.2 = 20%)
        this.reverbAmount = 0.15; // 15% reverb by default
        this.soundType = "piano";
    }

    async init() {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext ||
                window.webkitAudioContext)();

            // Create gain nodes for dry/wet mixing
            this.masterGain = this.audioContext.createGain();
            this.dryGain = this.audioContext.createGain();
            this.wetGain = this.audioContext.createGain();

            // Set initial volumes
            this.masterGain.gain.value = this.volume;
            this.updateReverbMix();

            // Create subtle reverb
            await this.createReverb();

            // Connect: dry signal bypasses reverb, wet signal goes through reverb
            this.dryGain.connect(this.masterGain);
            this.wetGain.connect(this.reverbNode);
            this.reverbNode.connect(this.masterGain);
            this.masterGain.connect(this.audioContext.destination);

            if (this.audioContext.state === "suspended") {
                await this.audioContext.resume();
            }
        }
    }

    async createReverb() {
        // Create convolution reverb - MUCH more subtle
        this.reverbNode = this.audioContext.createConvolver();

        // Create shorter, more subtle impulse response
        const length = this.audioContext.sampleRate * 0.5; // Only 0.5 seconds
        const impulse = this.audioContext.createBuffer(
            2,
            length,
            this.audioContext.sampleRate,
        );

        for (let channel = 0; channel < 2; channel++) {
            const channelData = impulse.getChannelData(channel);
            for (let i = 0; i < length; i++) {
                const decay = Math.pow(1 - i / length, 3); // Faster decay
                channelData[i] = (Math.random() * 2 - 1) * decay * 0.03; // Much quieter
            }
        }

        this.reverbNode.buffer = impulse;
    }

    updateReverbMix() {
        if (this.dryGain && this.wetGain) {
            // Mix between dry and wet signal
            this.dryGain.gain.value = 1 - this.reverbAmount;
            this.wetGain.gain.value = this.reverbAmount;
        }
    }

    midiNoteToFrequency(midiNote) {
        return 440 * Math.pow(2, (midiNote - 69) / 12);
    }

    createEnhancedPianoSound(frequency, startTime, duration = 3.0) {
        // Create multiple oscillators for rich harmonics
        const fundamental = this.audioContext.createOscillator();
        const harmonic2 = this.audioContext.createOscillator();
        const harmonic3 = this.audioContext.createOscillator();
        const subharmonic = this.audioContext.createOscillator();

        // Create filters for each oscillator
        const filter1 = this.audioContext.createBiquadFilter();
        const filter2 = this.audioContext.createBiquadFilter();
        const filter3 = this.audioContext.createBiquadFilter();
        const subFilter = this.audioContext.createBiquadFilter();

        // Create gain nodes for mixing
        const fundamentalGain = this.audioContext.createGain();
        const harmonic2Gain = this.audioContext.createGain();
        const harmonic3Gain = this.audioContext.createGain();
        const subGain = this.audioContext.createGain();
        const masterEnvelope = this.audioContext.createGain();

        // Configure oscillators based on sound type
        switch (this.soundType) {
            case "piano":
                fundamental.type = "triangle";
                harmonic2.type = "sine";
                harmonic3.type = "sawtooth";
                subharmonic.type = "sine";

                fundamental.frequency.value = frequency;
                harmonic2.frequency.value = frequency * 2;
                harmonic3.frequency.value = frequency * 3;
                subharmonic.frequency.value = frequency * 0.5;

                filter1.type = "lowpass";
                filter1.frequency.value = 2500;
                filter1.Q.value = 1;

                filter2.type = "bandpass";
                filter2.frequency.value = 1500;
                filter2.Q.value = 2;

                filter3.type = "highpass";
                filter3.frequency.value = 500;
                filter3.Q.value = 1;

                subFilter.type = "lowpass";
                subFilter.frequency.value = 200;
                subFilter.Q.value = 1;

                fundamentalGain.gain.value = 0.6;
                harmonic2Gain.gain.value = 0.3;
                harmonic3Gain.gain.value = 0.15;
                subGain.gain.value = 0.4;
                break;

            case "electric":
                fundamental.type = "sawtooth";
                harmonic2.type = "triangle";
                harmonic3.type = "square";
                subharmonic.type = "sine";

                fundamental.frequency.value = frequency;
                harmonic2.frequency.value = frequency * 2;
                harmonic3.frequency.value = frequency * 4;
                subharmonic.frequency.value = frequency * 0.5;

                filter1.type = "lowpass";
                filter1.frequency.value = 1800;
                filter1.Q.value = 3;

                fundamentalGain.gain.value = 0.7;
                harmonic2Gain.gain.value = 0.4;
                harmonic3Gain.gain.value = 0.2;
                subGain.gain.value = 0.3;
                break;

            case "organ":
                fundamental.type = "sawtooth";
                harmonic2.type = "square";
                harmonic3.type = "triangle";
                subharmonic.type = "square";

                fundamental.frequency.value = frequency;
                harmonic2.frequency.value = frequency * 2;
                harmonic3.frequency.value = frequency * 3;
                subharmonic.frequency.value = frequency;

                filter1.type = "lowpass";
                filter1.frequency.value = 3500;
                filter1.Q.value = 0.5;

                fundamentalGain.gain.value = 0.5;
                harmonic2Gain.gain.value = 0.4;
                harmonic3Gain.gain.value = 0.3;
                subGain.gain.value = 0.6;
                break;

            case "synth":
                fundamental.type = "square";
                harmonic2.type = "sawtooth";
                harmonic3.type = "triangle";
                subharmonic.type = "square";

                fundamental.frequency.value = frequency;
                harmonic2.frequency.value = frequency * 1.5;
                harmonic3.frequency.value = frequency * 0.75;
                subharmonic.frequency.value = frequency * 0.5;

                filter1.type = "bandpass";
                filter1.frequency.value = 1200;
                filter1.Q.value = 8;

                fundamentalGain.gain.value = 0.8;
                harmonic2Gain.gain.value = 0.6;
                harmonic3Gain.gain.value = 0.4;
                subGain.gain.value = 0.5;
                break;
        }

        // Connect the audio graph
        fundamental.connect(filter1);
        filter1.connect(fundamentalGain);

        harmonic2.connect(filter2);
        filter2.connect(harmonic2Gain);

        harmonic3.connect(filter3);
        filter3.connect(harmonic3Gain);

        subharmonic.connect(subFilter);
        subFilter.connect(subGain);

        // Connect to both dry and wet paths
        fundamentalGain.connect(masterEnvelope);
        harmonic2Gain.connect(masterEnvelope);
        harmonic3Gain.connect(masterEnvelope);
        subGain.connect(masterEnvelope);

        // Split signal to dry and wet paths
        masterEnvelope.connect(this.dryGain); // Dry signal (no reverb)
        masterEnvelope.connect(this.wetGain); // Wet signal (with reverb)

        // Create realistic ADSR envelope
        const attackTime = 0.005;
        const decayTime = 0.3;
        const sustainLevel = 0.4;
        const releaseTime = 1.2;

        masterEnvelope.gain.setValueAtTime(0, startTime);
        masterEnvelope.gain.linearRampToValueAtTime(
            0.9,
            startTime + attackTime,
        );
        masterEnvelope.gain.exponentialRampToValueAtTime(
            sustainLevel,
            startTime + attackTime + decayTime,
        );
        masterEnvelope.gain.exponentialRampToValueAtTime(
            0.001,
            startTime + duration,
        );

        // Start all oscillators
        fundamental.start(startTime);
        harmonic2.start(startTime);
        harmonic3.start(startTime);
        subharmonic.start(startTime);

        // Stop all oscillators
        fundamental.stop(startTime + duration);
        harmonic2.stop(startTime + duration);
        harmonic3.stop(startTime + duration);
        subharmonic.stop(startTime + duration);

        return {
            fundamental,
            harmonic2,
            harmonic3,
            subharmonic,
            masterEnvelope,
            filters: [filter1, filter2, filter3, subFilter],
        };
    }

    playNote(midiNote, velocity = 100) {
        if (!this.audioContext) return;

        const frequency = this.midiNoteToFrequency(midiNote);
        const startTime = this.audioContext.currentTime;
        const normalizedVelocity = Math.max(
            0.1,
            Math.min(1.0, velocity / 127),
        );

        const sound = this.createEnhancedPianoSound(
            frequency,
            startTime,
            4.0,
        );
        sound.masterEnvelope.gain.value *= normalizedVelocity;

        this.activeNotes.set(midiNote, sound);

        // console.log(
        //     `🎹 Playing note ${midiNote} (${frequency.toFixed(1)}Hz) at velocity ${velocity}`,
        // );
    }

    stopNote(midiNote) {
        if (this.activeNotes.has(midiNote)) {
            const sound = this.activeNotes.get(midiNote);
            const releaseTime = this.audioContext.currentTime;

            // Natural release envelope
            sound.masterEnvelope.gain.exponentialRampToValueAtTime(
                0.001,
                releaseTime + 0.8,
            );

            this.activeNotes.delete(midiNote);
            // console.log(`🎹 Stopping note ${midiNote}`);
        }
    }

    setVolume(volume) {
        this.volume = Math.max(0, Math.min(1, volume / 100));
        if (this.masterGain) {
            this.masterGain.gain.setTargetAtTime(
                this.volume,
                this.audioContext.currentTime,
                0.1,
            );
        }
    }

    setReverbAmount(amount) {
        this.reverbAmount = Math.max(0, Math.min(1, amount / 100));
        this.updateReverbMix();
    }

    setSoundType(soundType) {
        this.soundType = soundType;
    }

    testSound() {
        // Play a nice chord progression
        this.playNote(60, 80); // C4
        setTimeout(() => this.playNote(64, 70), 150); // E4
        setTimeout(() => this.playNote(67, 70), 300); // G4
        setTimeout(() => this.playNote(72, 60), 450); // C5
    }
}