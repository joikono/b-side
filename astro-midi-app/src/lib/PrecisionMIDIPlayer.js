export class PrecisionMIDIPlayer {
    constructor() {
        this.synth = null;
        this.forcedDuration = 9.6; // exactly 16 beats at 100 BPM
        this.isPlaying = false;
        this.currentMidiData = null;
        this.scheduledEvents = [];
    }

    async init() {
        if (!this.synth) {
            // Use your existing pianoSynth's audio context for consistency
            this.synth = new Tone.PolySynth().toDestination();

            // Connect to your existing visualizer if available
            if (pianoSynth && pianoSynth.audioContext) {
                Tone.setContext(pianoSynth.audioContext);
            }
        }
    }

    async loadAndPlayWithDuration(midiUrl, forcedDuration = null) {
        await this.init();

        const duration = forcedDuration || this.forcedDuration;

        try {
            // Import @tonejs/midi dynamically (since it's not in your CDN)
            const { Midi } = await import(
                "https://cdn.skypack.dev/@tonejs/midi"
            );

            const midi = await Midi.fromUrl(midiUrl);
            this.currentMidiData = midi;

            console.log(
                `🎵 Loading MIDI with forced duration: ${duration}s`,
            );

            // Clear any existing scheduled events
            this.stop();

            // Schedule forced stop at exactly the specified duration
            const stopEvent = Tone.Transport.schedule(() => {
                this.stop();
                console.log(`⏰ Playback stopped at exactly ${duration}s`);
            }, duration);

            this.scheduledEvents.push(stopEvent);

            // Schedule all notes with duration checking
            midi.tracks.forEach((track) => {
                track.notes.forEach((note) => {
                    if (note.time < duration) {
                        const adjustedDuration = Math.min(
                            note.duration,
                            duration - note.time,
                        );

                        const noteEvent = Tone.Transport.schedule(
                            (time) => {
                                this.synth.triggerAttackRelease(
                                    note.name,
                                    adjustedDuration,
                                    time,
                                    note.velocity,
                                );
                            },
                            note.time,
                        );

                        this.scheduledEvents.push(noteEvent);
                    }
                });
            });

            // Start transport
            Tone.Transport.start();
            this.isPlaying = true;

            console.log(
                `🎵 Precision playback started - will stop at ${duration}s`,
            );

            // Update your existing UI
            this.updatePlaybackStatus(true);

            return true;
        } catch (error) {
            console.error("❌ Precision MIDI playback failed:", error);
            return false;
        }
    }

    stop() {
        if (this.isPlaying) {
            Tone.Transport.stop();

            // Clear all scheduled events
            this.scheduledEvents.forEach((event) => {
                Tone.Transport.clear(event);
            });
            this.scheduledEvents = [];

            this.isPlaying = false;
            this.updatePlaybackStatus(false);

            console.log("🛑 Precision playback stopped");
        }
    }

    pause() {
        if (this.isPlaying) {
            Tone.Transport.pause();
            this.updatePlaybackStatus(false);
        }
    }

    resume() {
        if (!this.isPlaying && Tone.Transport.state === "paused") {
            Tone.Transport.start();
            this.updatePlaybackStatus(true);
        }
    }

    updatePlaybackStatus(playing) {
        // Update your existing UI elements
        const statusElements = document.querySelectorAll(
            ".midi-player-status",
        );
        statusElements.forEach((el) => {
            el.textContent = playing
                ? "Playing (Precision Mode)"
                : "Stopped";
        });
    }

    // Enhanced loop functionality with precise timing
    async playWithLoop(midiUrl, loopCount = -1) {
        let currentLoop = 0;

        const playLoop = async () => {
            if (loopCount !== -1 && currentLoop >= loopCount) {
                console.log(
                    `🔄 Loop sequence completed (${currentLoop} loops)`,
                );
                return;
            }

            await this.loadAndPlayWithDuration(midiUrl);
            currentLoop++;

            if (loopCount === -1 || currentLoop < loopCount) {
                // Schedule next loop at exactly the right time
                setTimeout(
                    () => {
                        if (this.isPlaying) {
                            // Only continue if not manually stopped
                            playLoop();
                        }
                    },
                    this.forcedDuration * 1000 + 50,
                ); // 50ms gap between loops
            }
        };

        await playLoop();
    }
}