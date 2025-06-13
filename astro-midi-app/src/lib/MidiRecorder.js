export class MidiRecorder {
    constructor() {
        this.isRecording = false;
        this.recordedNotes = [];
        this.startTime = null;
        this.recordingDuration = 0;
        this.silenceTimeout = null;
        this.mode = "time";
        this.wasCanceled = false;
        this.internalTimeout = null; // Track internal timeout
    }

    startRecording(mode = "time", duration = 10) {
        // CRITICAL: Clear all previous state first
        this.clearAllState();

        this.isRecording = true;
        this.recordedNotes = [];
        this.startTime = performance.now();
        this.mode = mode;
        this.recordingDuration = duration * 1000;
        this.wasCanceled = false;

        console.log(`🎹 MIDI Recording started (${mode} mode)`);

        if (mode === "time") {
            // Stop after fixed duration
            this.internalTimeout = setTimeout(() => {
                if (this.isRecording) {
                    console.log("⏰ Internal timeout stopping recording");
                    this.stopRecording();
                }
            }, this.recordingDuration);
        } else if (mode === "silence") {
            this.resetSilenceTimer();
        }
    }

    stopRecording() {
        if (!this.isRecording) return;

        this.isRecording = false;

        // Clear all timers
        this.clearAllTimers();

        const totalDuration = (performance.now() - this.startTime) / 1000;
        console.log(
            `🎹 MIDI Recording stopped - Duration: ${totalDuration.toFixed(1)}s, Notes: ${this.recordedNotes.length}`,
        );

        return this.recordedNotes;
    }

    cancelRecording() {
        if (!this.isRecording) {
            console.log("🛑 No recording to cancel");
            return;
        }

        const totalDuration = (performance.now() - this.startTime) / 1000;
        const noteCount = this.recordedNotes.length;

        // Set cancellation flag BEFORE clearing state
        this.wasCanceled = true;
        this.isRecording = false;

        // Clear all timers and state
        this.clearAllTimers();
        this.clearAllState();

        console.log(
            `🛑 MIDI Recording canceled - Duration: ${totalDuration.toFixed(1)}s, Notes discarded: ${noteCount}`,
        );

        return true;
    }

    clearAllTimers() {
        if (this.silenceTimeout) {
            clearTimeout(this.silenceTimeout);
            this.silenceTimeout = null;
        }

        if (this.internalTimeout) {
            clearTimeout(this.internalTimeout);
            this.internalTimeout = null;
        }
    }

    clearAllState() {
        this.recordedNotes = [];
        this.startTime = null;
        this.recordingDuration = 0;
        this.clearAllTimers();
    }

    addNote(note, velocity, timestamp, isNoteOn) {
        if (!this.isRecording) return;

        const relativeTime = (timestamp - this.startTime) / 1000;

        this.recordedNotes.push({
            note: note,
            velocity: velocity,
            time: relativeTime,
            isNoteOn: isNoteOn,
        });

        if (this.mode === "silence" && isNoteOn) {
            this.resetSilenceTimer();
        }
    }

    resetSilenceTimer() {
        if (this.silenceTimeout) {
            clearTimeout(this.silenceTimeout);
        }

        this.silenceTimeout = setTimeout(() => {
            if (this.isRecording) {
                this.stopRecording();
            }
        }, 2000);
    }

    convertToMidiBlob() {
        if (this.recordedNotes.length === 0) {
            throw new Error("No notes recorded");
        }

        // Simple MIDI file creation
        const midiData = this.createMidiData(this.recordedNotes);
        return new Blob([midiData], { type: "audio/midi" });
    }

    createMidiData(notes) {
        // Very simplified MIDI file creation
        const header = new Uint8Array([
            0x4d,
            0x54,
            0x68,
            0x64, // "MThd"
            0x00,
            0x00,
            0x00,
            0x06, // Header length
            0x00,
            0x00, // Format 0
            0x00,
            0x01, // 1 track
            0x00,
            0x60, // 96 ticks per quarter note
        ]);

        const trackData = this.createTrackData(notes);
        const trackHeader = new Uint8Array([
            0x4d,
            0x54,
            0x72,
            0x6b, // "MTrk"
            ...this.int32ToBytes(trackData.length),
        ]);

        // Combine header + track header + track data
        const midiFile = new Uint8Array(
            header.length + trackHeader.length + trackData.length,
        );
        midiFile.set(header, 0);
        midiFile.set(trackHeader, header.length);
        midiFile.set(trackData, header.length + trackHeader.length);

        return midiFile;
    }

    createTrackData(notes) {
        const events = [];
        let currentTime = 0;

        // Sort notes by time
        const sortedNotes = [...notes].sort((a, b) => a.time - b.time);

        // Find the earliest note time to normalize against
        const firstNoteTime =
            sortedNotes.length > 0 ? sortedNotes[0].time : 0;

        // Normalize all note times so the first note starts at 0
        const normalizedNotes = sortedNotes.map((note) => ({
            ...note,
            time: note.time - firstNoteTime,
        }));

        for (const note of normalizedNotes) {
            const deltaTime = Math.max(
                0,
                Math.round((note.time - currentTime) * 160),
            ); // Convert to ticks at 100 BPM
            currentTime = note.time;

            // Add MIDI event
            const status = note.isNoteOn ? 0x90 : 0x80; // Note on/off on channel 1
            events.push(...this.variableLengthQuantity(deltaTime));
            events.push(status, note.note, note.velocity);
        }

        // End of track
        events.push(0x00, 0xff, 0x2f, 0x00);

        return new Uint8Array(events);
    }

    // 🎯 NEW: Create MIDI specifically for user playback with proper padding
    createPlaybackMidiBlob() {
        if (this.recordedNotes.length === 0) {
            throw new Error("No notes recorded");
        }

        const midiData = this.createPlaybackMidiData(this.recordedNotes);
        return new Blob([midiData], { type: "audio/midi" });
    }

    createPlaybackMidiData(notes) {
        // Same header as original
        const header = new Uint8Array([
            0x4d,
            0x54,
            0x68,
            0x64, // "MThd"
            0x00,
            0x00,
            0x00,
            0x06, // Header length
            0x00,
            0x00, // Format 0
            0x00,
            0x01, // 1 track
            0x00,
            0x60, // 96 ticks per quarter note
        ]);

        const trackData = this.createPlaybackTrackData(notes);
        const trackHeader = new Uint8Array([
            0x4d,
            0x54,
            0x72,
            0x6b, // "MTrk"
            ...this.int32ToBytes(trackData.length),
        ]);

        const midiFile = new Uint8Array(
            header.length + trackHeader.length + trackData.length,
        );
        midiFile.set(header, 0);
        midiFile.set(trackHeader, header.length);
        midiFile.set(trackData, header.length + trackHeader.length);

        return midiFile;
    }

    createPlaybackTrackData(notes) {
        const events = [];
        let currentTime = 0;
        const targetDuration = 9.6;

        // Sort notes by time
        const sortedNotes = [...notes].sort((a, b) => a.time - b.time);
        const firstNoteTime =
            sortedNotes.length > 0 ? sortedNotes[0].time : 0;
        const normalizedNotes = sortedNotes.map((note) => ({
            ...note,
            time: note.time - firstNoteTime,
        }));

        // 🎯 NEW APPROACH: Start with a sustain note that lasts the full duration
        // Add a very quiet sustain note at the beginning
        events.push(...this.variableLengthQuantity(0)); // Start immediately
        events.push(0x90, 127, 1); // Very quiet high note (out of way)

        // Add all user notes on top
        for (const note of normalizedNotes) {
            const deltaTime = Math.max(
                0,
                Math.round((note.time - currentTime) * 160),
            );
            currentTime = note.time;

            const status = note.isNoteOn ? 0x90 : 0x80;
            events.push(...this.variableLengthQuantity(deltaTime));
            events.push(status, note.note, note.velocity);
        }

        // End the sustain note at exactly 9.6 seconds
        const remainingTicks = Math.round(
            (targetDuration - currentTime) * 160,
        );
        events.push(...this.variableLengthQuantity(remainingTicks));
        events.push(0x80, 127, 0); // End sustain note at 9.6 seconds

        console.log(`🔍 Sustain note holds for full ${targetDuration}s`);

        // End of track
        events.push(0x00, 0xff, 0x2f, 0x00);
        return new Uint8Array(events);
    }

    variableLengthQuantity(value) {
        const bytes = [];
        bytes.unshift(value & 0x7f);
        value >>= 7;
        while (value > 0) {
            bytes.unshift((value & 0x7f) | 0x80);
            value >>= 7;
        }
        return bytes;
    }

    int32ToBytes(value) {
        return [
            (value >> 24) & 0xff,
            (value >> 16) & 0xff,
            (value >> 8) & 0xff,
            value & 0xff,
        ];
    }
}