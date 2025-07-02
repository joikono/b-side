export class VoiceCommands {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        this.isWakeWordMode = true;
        this.activeSession = false;
        this.sessionTimeout = null;
        this.isSpeaking = false; // Flag to track when we're speaking

        // 🆕 NEW: Google TTS properties
        this.googleApiKey = import.meta.env.PUBLIC_GOOGLE_TTS_API_KEY;
        this.useGoogleTTS = true; // Toggle for testing
        this.selectedVoice = null; // Will store the best Google voice
        this.monthlyCharacterCount = 0; // Track usage for free tier

        this.setupSpeechRecognition();
        this.initializeGoogleVoices();

        this.isGeneratingArrangement = false;
        this.awaitingPlayConfirmation = false;
        this.shouldAutoPlay = false; // 🆕 NEW: Flag for auto-play after generation
    }

    // 🆕 NEW: Initialize Google TTS voices
    async initializeGoogleVoices() {
        if (!this.googleApiKey) {
            console.log("🔑 No Google API key found, falling back to system TTS");
            this.useGoogleTTS = false;
            return;
        }

        try {
            const response = await fetch(`https://texttospeech.googleapis.com/v1/voices?key=${this.googleApiKey}`);
            const data = await response.json();

            if (data.voices) {
                // Find the best English voices
                const englishVoices = data.voices.filter(voice =>
                    voice.languageCodes.includes('en-US') &&
                    voice.name.includes('Wavenet') // Premium voices
                );

                // Pick a great male voice for your music app
                this.selectedVoice = englishVoices.find(v =>
                    v.name.includes('Wavenet-B')   // Fallback
                ) || englishVoices[0];

                console.log(`🎭 Selected Google voice: ${this.selectedVoice.name}`);
                console.log(`📊 Available voices: ${englishVoices.length} Wavenet voices found`);
            }
        } catch (error) {
            console.error("❌ Failed to load Google voices:", error);
            this.useGoogleTTS = false;
        }
    }

    setupSpeechRecognition() {
        if (
            "webkitSpeechRecognition" in window ||
            "SpeechRecognition" in window
        ) {
            const SpeechRecognition =
                window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            this.recognition.continuous = true;
            this.recognition.interimResults = false;
            this.recognition.lang = "en-US";

            this.recognition.onresult = (event) => {
                const command =
                    event.results[
                        event.results.length - 1
                    ][0].transcript.toLowerCase();
                console.log("🎤 Heard:", command);
                this.processCommand(command);
            };

            this.recognition.onend = () => {
                console.log("🎤 Recognition ended, restarting...");
                // Add delay and state check before restarting
                setTimeout(() => {
                    if (this.isListening && !this.isSpeaking) {
                        try {
                            this.recognition.start();
                        } catch (error) {
                            console.log(
                                "🎤 Restart failed:",
                                error.message,
                            );
                            // Try again after longer delay
                            setTimeout(() => {
                                if (this.isListening && !this.isSpeaking) {
                                    try {
                                        this.recognition.start();
                                    } catch (e) {
                                        console.log(
                                            "🎤 Second restart failed:",
                                            e.message,
                                        );
                                    }
                                }
                            }, 2000);
                        }
                    }
                }, 500);
            };

            this.recognition.onerror = (event) => {
                console.log("🎤 Speech error:", event.error);
                if (event.error !== "not-allowed") {
                    setTimeout(() => {
                        if (this.isListening && !this.isSpeaking) {
                            try {
                                this.recognition.start();
                            } catch (error) {
                                console.log(
                                    "🎤 Error restart failed:",
                                    error.message,
                                );
                            }
                        }
                    }, 1000);
                }
            };
        }
    }

    processCommand(command) {
        // 🛡️ IGNORE commands while we're speaking
        if (this.isSpeaking) {
            console.log("🔇 Ignoring command - system is speaking");
            return;
        }

        if (this.isWakeWordMode && !this.activeSession) {
            // Wake word detection (unchanged)
            if (command.includes("hey" || "hey bside")) {
                console.log("👋 Wake word detected!");

                const responses = [
                    "What can I help with your music journey today?",
                    "Ready to create some amazing music together?",
                    "Let's make some beautiful music! What's on your mind?",
                    "I'm here to help bring your musical ideas to life!",
                    "What musical magic are we creating today?",
                    "Ready to turn your melodies into full arrangements?",
                    "Let's explore your musical creativity! What would you like to work on?",
                    "I'm excited to help with your music! What can I do?",
                    "Time to make some music! What's your vision?",
                    "Ready to jam? What musical ideas are you working with?",
                    "Let's create something awesome together! What's the plan?",
                    "Your musical co-pilot is ready! What can I help you build?",
                    "Ready to transform your musical ideas into reality?",
                    "Let's bring your music to life! What are you thinking?",
                    "I'm here to help you create amazing arrangements! What's up?"
                ];

                const randomResponse = responses[Math.floor(Math.random() * responses.length)];
                this.speakSmart(randomResponse, 'quick');

                this.isWakeWordMode = false;
                this.startActiveSession();
                return;
            }
        } else {
            // 🆕 NEW: Use AI intent classification for ALL commands
            console.log("🤖 Classifying intent for:", command);
            this.handleIntentClassification(command);
        }
    }

    // Intent classification method
    async handleIntentClassification(command) {
        this.extendActiveSession();

        try {
            const apiKey = import.meta.env.PUBLIC_OPENAI_API_KEY;

            const systemPrompt = `You are a voice command classifier for a music application. 
        
        Analyze the user's voice command and return ONLY a JSON response with this structure:
        {
            "intent": "record|play|stop|generate|loop|toggle_recording|chat",
            "confidence": 0.0-1.0,
            "parameters": {...any additional params...}
        }
    
        Intent definitions:
        - "record": User wants to start recording MIDI input (examples: "record", "capture", "start recording")
        - "play": User wants to play/hear music or arrangements (examples: "play", "jam", "hear it", "play it", "can you play", "let me hear", "start playing")
        - "stop": User wants to stop playback (examples: "stop", "pause", "cancel")
        - "generate": User wants to create/arrange music (examples: "generate", "arrange", "make music")
        - "loop": User wants to enable/toggle looping (examples: "loop", "repeat")
        - "toggle_recording": User wants to include/exclude their recording in playback (examples: "add my recording", "include my recording", "turn on my recording", "play my recording too", "remove my recording", "turn off my recording", "don't play my recording")
        - "chat": General conversation, questions, or unclear commands
    
        Examples:
        "let's record this" → {"intent": "record", "confidence": 0.9}
        "play that arrangement" → {"intent": "play", "confidence": 0.9}
        "add my recording to the mix" → {"intent": "toggle_recording", "confidence": 0.9}
        "include my recording" → {"intent": "toggle_recording", "confidence": 0.8}
        "turn off my recording" → {"intent": "toggle_recording", "confidence": 0.9}
        "play my recording with the arrangement" → {"intent": "toggle_recording", "confidence": 0.8}`;

            const response = await fetch("https://api.openai.com/v1/chat/completions", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${apiKey}`,
                },
                body: JSON.stringify({
                    model: "gpt-3.5-turbo",
                    messages: [
                        { role: "system", content: systemPrompt },
                        { role: "user", content: command }
                    ],
                    max_tokens: 100,
                    temperature: 0.1,
                }),
            });

            const result = await response.json();
            const aiResponse = result.choices[0].message.content;

            const intentData = JSON.parse(aiResponse);
            this.executeIntent(intentData, command);

        } catch (error) {
            console.error("❌ Intent classification failed:", error);
            this.handleConversationalCommand(command);
        }
    }
    

    executeIntent(intentData, originalCommand) {
        const { intent, confidence } = intentData;

        console.log(`🤖 Intent detected: "${intent}" with ${(confidence * 100).toFixed(0)}% confidence`);

        if (confidence < 0.6 || intent === "chat") {
            console.log(`💬 Using conversational mode (intent: ${intent}, confidence: ${confidence})`);
            this.handleConversationalCommand(originalCommand);
            return;
        }

        if (intent === "play" && this.awaitingPlayConfirmation) {
            console.log("🎵 User confirmed - starting immediate play");
            this.awaitingPlayConfirmation = false;
            this.startImmediatePlay();
            return;
        }

        switch (intent) {
            case "record":
                console.log("▶️ Intent: Recording detected");
                this.speakSmart("Starting recording");
                startCapture();
                this.extendActiveSession();
                break;

            case "play":
                console.log("🎵 Intent: Play detected");
                const playResponses = [
                    "Playing arrangement",
                    "Here we go!",
                    "Let's hear it",
                    "Starting playback",
                    "Playing now",
                ];
                const randomPlay = playResponses[Math.floor(Math.random() * playResponses.length)];
                this.speakSmart(randomPlay, 'quick');
                playCombinedTrack();
                this.extendActiveSession();
                break;

            case "stop":
                console.log("⏹️ Intent: Stop detected");
                this.awaitingPlayConfirmation = false;
                this.isGeneratingArrangement = false;

                const stopResponses = [
                    "Stopping playback",
                    "All stopped",
                    "Paused",
                    "Stopping now",
                    "Done",
                ];
                const randomStop = stopResponses[Math.floor(Math.random() * stopResponses.length)];
                this.speakSmart(randomStop, 'instant');
                stopCombinedTrack();
                this.extendActiveSession();
                break;

            case "generate":
                console.log("🎼 Intent: Generate detected");

                // 🚨 CHECK IF USER HAS RECORDED ANYTHING FIRST
                const hasRecording = !!window.uploadedMidiResult;

                if (!hasRecording) {
                    console.log("🎼 No recording found - guiding user to record first");

                    const introResponses = [
                        "That sounds awesome! First, let's capture your melody. Ask me to record you when you're ready to play it!",
                        "Great idea! Let's start by recording your melody, then I'll add instruments to it.",
                        "I'd love to help! First ask me to record you and play your melody, then I'll create backing instruments.",
                        "Perfect! Step one: ask me to record you and play your tune. Then I'll build an arrangement around it.",
                        "Sounds like a plan! First we need to capture your melody - ask me to record you when ready!"
                    ];

                    const randomIntro = introResponses[Math.floor(Math.random() * introResponses.length)];
                    this.speakSmart(randomIntro, 'conversational');
                    this.extendActiveSession();
                    return; // Don't try to generate anything
                }

                this.isGeneratingArrangement = true;
                this.shouldAutoPlay = true; // 🆕 NEW: Flag to auto-play after generation
                analyzeAndGenerate();
                this.extendActiveSession();
                break;

            case "loop":
                console.log("🔄 Intent: Loop detected");
                this.speakSmart("Loop toggled", 'instant');
                toggleCombinedTrackLoop();
                this.extendActiveSession();
                break;

            // 🆕 NEW: Toggle recording inclusion
            case "toggle_recording":
                console.log("🎹 Intent: Toggle recording detected");
                this.toggleRecordingInclusion();
                this.extendActiveSession();
                break;

            default:
                this.handleConversationalCommand(originalCommand);
        }
    }

    toggleRecordingInclusion() {
        const userTrackCheckbox = document.getElementById('userTrackToggle');

        if (userTrackCheckbox) {
            // Toggle the checkbox state
            userTrackCheckbox.checked = !userTrackCheckbox.checked;

            const isNowIncluded = userTrackCheckbox.checked;

            // Call your existing function to handle the toggle
            toggleUserTrack(isNowIncluded);

            const responses = isNowIncluded ? [
                "Your recording is now included",
                "Added your recording to the mix",
                "Recording included",
                "Your part is now playing",
                "Recording turned on"
            ] : [
                "Your recording is now excluded",
                "Removed your recording from the mix",
                "Recording excluded",
                "Your part is now muted",
                "Recording turned off"
            ];

            const randomResponse = responses[Math.floor(Math.random() * responses.length)];
            this.speakSmart(randomResponse, 'quick');

            console.log(`🎹 User track toggled: ${isNowIncluded ? 'ON' : 'OFF'}`);

        } else {
            console.error("❌ User track checkbox not found");
            this.speakSmart("Sorry, couldn't find the recording control", 'quick');
        }
    }

    hasUserRecordedAnything() {
        return !!window.uploadedMidiResult;
    }

    // Add this new method to your VoiceCommands class:
    async onArrangementComplete() {
        console.log("🎵 onArrangementComplete called - isGeneratingArrangement:", this.isGeneratingArrangement);

        if (!this.isGeneratingArrangement) return;

        this.isGeneratingArrangement = false;
        
        // 🆕 NEW: Check if we should auto-play
        if (this.shouldAutoPlay) {
            console.log("🎵 Auto-playing arrangement after generation");
            this.shouldAutoPlay = false;
            
            // Brief pause, then announce and play
            this.speakSmart("Your arrangement is ready! Here we go!", 'quick');
            
            setTimeout(() => {
                playCombinedTrack();
                console.log("🎵 Auto-started arrangement playback");
            }, 1200); // Give time for the speech to finish
            
            this.extendActiveSession();
            return;
        }

        // Original behavior for manual play confirmation
        console.log("🎵 Arrangement complete - asking for confirmation");
        this.speakSmart("Your arrangement is ready! Just say 'play'!", 'conversational');
        this.awaitingPlayConfirmation = true;
        this.extendActiveSession();

        console.log("🎵 Now awaiting play confirmation - awaitingPlayConfirmation:", this.awaitingPlayConfirmation);
    }

    // Simplified immediate play method
    async startImmediatePlay() {
        this.speakSmart("Here we go!", 'instant');

        // Very short pause, then start the music
        setTimeout(() => {
            console.log("🎵 Starting arrangement playback immediately");
            playCombinedTrack();
        }, 800); // Just enough time for "Here we go!" to finish
    }

    // Add this debug method to check current state:
    debugState() {
        console.log("🐛 VoiceCommands Debug State:");
        console.log("  isGeneratingArrangement:", this.isGeneratingArrangement);
        console.log("  awaitingPlayConfirmation:", this.awaitingPlayConfirmation);
        console.log("  shouldAutoPlay:", this.shouldAutoPlay);
        console.log("  activeSession:", this.activeSession);
        console.log("  isWakeWordMode:", this.isWakeWordMode);
        console.log("  isSpeaking:", this.isSpeaking);
        console.log("  isListening:", this.isListening);
    }

    // Conversational command handler
    async handleConversationalCommand(command) {
        this.extendActiveSession();

        console.log("💬 Handling conversational command:", command);

        try {
            const apiKey = import.meta.env.PUBLIC_OPENAI_API_KEY;

            if (!apiKey) {
                console.error("❌ No OpenAI API key found");
                this.speakSmart("Sorry, I need an API key to respond to that", 'quick');
                return;
            }

            // Check if user has recorded anything yet
            const hasCurrentAnalysis = !!window.uploadedMidiResult;

            let contextMessage = "";
            if (hasCurrentAnalysis) {
                const result = window.uploadedMidiResult;
                if (result.detected_type === "chord_progression") {
                    const chords = result.chord_progression || [];
                    contextMessage = `Current analyzed chord progression: ${chords.join(" → ")}. Key: ${result.key || "Unknown"}.`;
                } else if (result.harmonizations) {
                    const style = document.getElementById("stickyHarmonyStyle")?.value || "simple_pop";
                    const chords = result.harmonizations[style]?.progression || [];
                    contextMessage = `Current melody harmonized as: ${chords.join(" → ")}. Key: ${result.key || "Unknown"}.`;
                }
            }

            // Different system prompts based on whether they've recorded anything
            const systemPrompt = hasCurrentAnalysis
                ? `You're a music co-pilot for songwriters and composers. Keep responses under 30 words since this is voice interaction.
    
    The user has already recorded and analyzed their music. For ANY requests about arrangements, instruments, backing tracks, or making music fuller, always suggest they say "generate" to create an arrangement.
    
    Your role:
    - For arrangement requests: Always suggest saying "generate" to create backing instruments
    - For musical questions: Give specific, actionable advice about their chord progression
    - For general music chat: Be supportive and knowledgeable
    - Keep everything concise and natural
    
    If they ask about adding instruments, backing tracks, fuller sound, or arrangements, respond like: "Say 'generate' and I'll create backing instruments for your [melody/chords]!"`

                : `You're a music co-pilot for songwriters and composers. Keep responses under 30 words since this is voice interaction.
    
    The user hasn't recorded anything yet. Your main job is to recognize when they're describing musical goals (especially about arrangements, adding instruments, or making music fuller) and guide them to record first.
    
    RECOGNIZE THESE AS ARRANGEMENT INTENTIONS:
    - "I have a melody and want to see how it sounds with instruments"
    - "I'd like to add backing to this tune I have"
    - "How would this sound with more instruments"
    - "I want to create an arrangement"
    - "Can we build on this melody"
    - Any mention of adding instruments, backing tracks, fuller sound, arrangements
    
    FOR ARRANGEMENT INTENTIONS: Respond enthusiastically and guide them to record first, like:
    "That sounds awesome! First, let's capture your melody. Ask me to record you when you're ready to play it, then I'll help add instruments!"
    
    FOR OTHER MUSIC QUESTIONS: Be helpful and supportive but concise.
    
    Always be encouraging about their musical ideas!`;

            const messages = [
                { role: "system", content: systemPrompt }
            ];

            // Add context about current analysis if available
            if (contextMessage) {
                messages.push({ role: "system", content: contextMessage });
            }

            // Add user command
            messages.push({ role: "user", content: command });

            console.log("💬 Sending to OpenAI - hasRecording:", hasCurrentAnalysis);

            const response = await fetch("https://api.openai.com/v1/chat/completions", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${apiKey}`,
                },
                body: JSON.stringify({
                    model: "gpt-3.5-turbo",
                    messages: messages,
                    max_tokens: 100,
                    temperature: 0.7,
                }),
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(`OpenAI API error: ${response.status} - ${result.error?.message || "Unknown error"}`);
            }

            const aiResponse = result.choices[0].message.content;
            console.log("💬 AI response:", aiResponse);

            // Use Google TTS for conversational responses
            this.speakWithGoogle(aiResponse, 'conversational');

        } catch (error) {
            console.error("❌ OpenAI request failed:", error);

            // Smart fallback for arrangement intentions when AI fails
            const lowerCommand = command.toLowerCase();
            if ((lowerCommand.includes("melody") && (lowerCommand.includes("instrument") || lowerCommand.includes("sound"))) ||
                lowerCommand.includes("arrangement") || lowerCommand.includes("backing") ||
                lowerCommand.includes("add") && lowerCommand.includes("instrument")) {

                const hasRecording = !!window.uploadedMidiResult;
                if (hasRecording) {
                    this.speakSmart("Say 'generate' and I'll add instruments to your music!", 'quick');
                } else {
                    this.speakSmart("That sounds great! Ask me to record you first, then I'll help add instruments.", 'quick');
                }
            } else {
                this.speakSmart("Sorry, I couldn't process that right now", 'quick');
            }
        }
    }

    // 🆕 NEW: Google TTS method
    async speakWithGoogle(text, priority = 'normal') {
        if (!this.googleApiKey || !this.useGoogleTTS || !this.selectedVoice) {
            // Fallback to system TTS
            this.speakLonger(text);
            return;
        }

        // Track character usage (free tier: 1M Wavenet chars/month)
        this.monthlyCharacterCount += text.length;
        if (this.monthlyCharacterCount > 900000) { // Leave some buffer
            console.log("🚨 Approaching Google TTS free tier limit, falling back to system TTS");
            this.speakLonger(text);
            return;
        }

        // STOP LISTENING while speaking to prevent feedback loop
        if (this.recognition) {
            this.recognition.stop();
        }

        this.isSpeaking = true;
        console.log("🔇 Speaking mode ON (Google TTS) - commands blocked");

        try {
            const startTime = performance.now();

            const requestBody = {
                input: { text: this.preprocessMusicalText(text) },
                voice: {
                    languageCode: 'en-US',
                    name: this.selectedVoice.name,
                    ssmlGender: this.selectedVoice.ssmlGender
                },
                audioConfig: {
                    audioEncoding: 'MP3',
                    speakingRate: priority === 'quick' ? 1.1 : 1.0, // Slightly faster for quick responses
                    pitch: 0.0,
                    volumeGainDb: 0.0
                }
            };

            const response = await fetch(`https://texttospeech.googleapis.com/v1/text:synthesize?key=${this.googleApiKey}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) {
                throw new Error(`Google TTS API error: ${response.status}`);
            }

            const data = await response.json();

            // Convert base64 audio to blob
            const audioBytes = Uint8Array.from(atob(data.audioContent), c => c.charCodeAt(0));
            const audioBlob = new Blob([audioBytes], { type: 'audio/mp3' });
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);

            const processingTime = performance.now() - startTime;
            console.log(`⚡ Google TTS processing time: ${processingTime.toFixed(0)}ms`);
            console.log(`📊 Characters used this month: ${this.monthlyCharacterCount}`);

            // Play the audio
            audio.onended = () => {
                URL.revokeObjectURL(audioUrl); // Clean up
                setTimeout(() => {
                    this.isSpeaking = false;
                    // RESTART LISTENING after speaking
                    if (this.isListening && this.recognition) {
                        this.recognition.start();
                    }
                    console.log("🎤 Speaking mode OFF - commands enabled (Google TTS)");
                }, priority === 'quick' ? 800 : 1500);
            };

            audio.onerror = () => {
                URL.revokeObjectURL(audioUrl);
                console.error("❌ Google TTS audio playback failed, falling back to system TTS");
                this.speakLonger(text); // Fallback
            };

            audio.play();
            console.log(`🗣️ Speaking with Google TTS: "${text}"`);

        } catch (error) {
            console.error("❌ Google TTS request failed:", error);
            this.isSpeaking = false;
            // RESTART LISTENING after error
            if (this.isListening && this.recognition) {
                this.recognition.start();
            }
            // Fallback to system TTS
            this.speakLonger(text);
        }
    }

    // 🆕 NEW: Smart TTS selection with Google
    speakSmart(text, type = 'quick') {
        // Use system TTS for very quick responses, Google TTS for everything else
        if (type === 'instant' || text.length < 10) {
            this.speakWithGoogle(text, type); // System TTS - instant for super short responses
        } else {
            this.speakWithGoogle(text, type); // Google TTS - much better quality
        }
    }

    // Longer speaking method for AI responses (fallback)
    speakLonger(text) {
        if ("speechSynthesis" in window) {
            // STOP LISTENING while speaking to prevent feedback loop
            if (this.recognition) {
                this.recognition.stop();
            }

            this.isSpeaking = true;
            console.log(
                "🔇 Speaking mode ON (AI response) - commands blocked",
            );

            const utterance = new SpeechSynthesisUtterance(this.preprocessMusicalText(text));

            // Remove Mark voice preference - use default
            const voices = speechSynthesis.getVoices();
            if (voices.length > 0) {
                // Just use the first available voice instead of searching for Mark
                utterance.voice = voices[0];
            }

            utterance.rate = 0.9;
            utterance.volume = 0.7;

            utterance.onend = () => {
                // 🔧 LONGER BUFFER for AI responses (3 seconds vs 1 second)
                setTimeout(() => {
                    this.isSpeaking = false;
                    // RESTART LISTENING after speaking
                    if (this.isListening && this.recognition) {
                        this.recognition.start();
                    }
                    console.log(
                        "🎤 Speaking mode OFF - commands enabled (after AI response)",
                    );
                }, 3000); // 3 second buffer instead of 1
            };

            utterance.onerror = () => {
                setTimeout(() => {
                    this.isSpeaking = false;
                    // RESTART LISTENING after error
                    if (this.isListening && this.recognition) {
                        this.recognition.start();
                    }
                    console.log("🎤 Speaking mode OFF after error");
                }, 2000);
            };

            speechSynthesis.speak(utterance);
            console.log("🗣️ Speaking AI response:", text);
        }
    }

    // Start active session (stays awake for commands)
    startActiveSession() {
        this.activeSession = true;
        this.isWakeWordMode = false;
        console.log("🔥 Active session started - no wake word needed");

        // Set timeout to end session after 30 seconds of inactivity
        this.sessionTimeout = setTimeout(() => {
            this.endActiveSession();
        }, 36000000); // 30 seconds
    }

    // Extend active session (reset the timeout)
    extendActiveSession() {
        if (this.activeSession) {
            // Clear existing timeout
            if (this.sessionTimeout) {
                clearTimeout(this.sessionTimeout);
            }

            // Set new timeout
            this.sessionTimeout = setTimeout(() => {
                this.endActiveSession();
            }, 36000000); // Another 30 seconds

            console.log("⏰ Active session extended - 30 more seconds");
        }
    }

    // End active session (back to wake word mode)
    endActiveSession() {
        this.activeSession = false;
        this.isWakeWordMode = true;

        if (this.sessionTimeout) {
            clearTimeout(this.sessionTimeout);
            this.sessionTimeout = null;
        }

        console.log("😴 Session ended - say 'Hey Wave' to start again");
        this.speakSmart("Session ended", 'quick'); // Optional: notify user
    }

    // Simple flag-based speak method (system TTS)
    speak(text) {
        if ("speechSynthesis" in window) {
            // STOP LISTENING while speaking to prevent feedback loop
            if (this.recognition) {
                this.recognition.stop();
            }

            this.isSpeaking = true; // 🚫 Block commands while speaking
            console.log("🔇 Speaking mode ON - commands blocked");

            const utterance = new SpeechSynthesisUtterance(this.preprocessMusicalText(text));
            
            // Remove Mark voice preference - use default
            const voices = speechSynthesis.getVoices();
            if (voices.length > 0) {
                // Just use the first available voice instead of searching for Mark
                utterance.voice = voices[0];
            }

            utterance.rate = 0.9;
            utterance.volume = 0.7;

            utterance.onend = () => {
                // Add delay before allowing commands again
                setTimeout(() => {
                    this.isSpeaking = false; // ✅ Allow commands again
                    // RESTART LISTENING after speaking
                    if (this.isListening && this.recognition) {
                        this.recognition.start();
                    }
                    console.log("🎤 Speaking mode OFF - commands enabled");
                }, 200); // Short buffer
            };

            utterance.onerror = () => {
                setTimeout(() => {
                    this.isSpeaking = false;
                    // RESTART LISTENING after error
                    if (this.isListening && this.recognition) {
                        this.recognition.start();
                    }
                    console.log("🎤 Speaking mode OFF after error");
                }, 1000);
            };

            speechSynthesis.speak(utterance);
            console.log("🗣️ Speaking:", text);
        }
    }

    startListening() {
        if (this.recognition && !this.isListening) {
            // Add !this.isListening check
            this.isListening = true;
            this.recognition.start();
            console.log('👂 Always listening for "Hey Wave"...');
        }
    }

    stopListening() {
        this.isListening = false;
        if (this.recognition) {
            this.recognition.stop();
        }
    }

    // 🆕 NEW: Test Google TTS voices
    async testGoogleVoice() {
        const testText = "Hey! Let's record that chord progression and see what we can build on top of it.";

        console.log("🎭 Testing system TTS...");
        this.speak(testText);

        setTimeout(async () => {
            console.log("🎭 Testing Google Cloud TTS...");
            await this.speakWithGoogle(testText);
        }, 5000);
    }

    // 🆕 NEW: Set your preferred voice permanently
    async setVoice(voiceName) {
        if (!this.googleApiKey) {
            console.log("❌ No Google API key found");
            return;
        }

        try {
            const response = await fetch(`https://texttospeech.googleapis.com/v1/voices?key=${this.googleApiKey}`);
            const data = await response.json();

            const voice = data.voices.find(v => v.name === voiceName);

            if (voice) {
                this.selectedVoice = voice;
                console.log(`🎭 Voice changed to: ${voice.name}`);

                // Test the new voice
                await this.speakWithGoogle("Voice changed! How does this sound?", 'quick');
            } else {
                console.log(`❌ Voice '${voiceName}' not found`);
            }
        } catch (error) {
            console.error("❌ Failed to set voice:", error);
        }
    }

    // Add this comprehensive method to your VoiceCommands class:
    preprocessMusicalText(text) {
        // Fix sharp symbol pronunciation first
        text = text.replace(/#/g, " sharp");

        // Fix all minor chords (natural notes)
        text = text.replace(/\bAm\b/g, "A minor");
        text = text.replace(/\bBm\b/g, "B minor");
        text = text.replace(/\bCm\b/g, "C minor");
        text = text.replace(/\bDm\b/g, "D minor");
        text = text.replace(/\bEm\b/g, "E minor");
        text = text.replace(/\bFm\b/g, "F minor");
        text = text.replace(/\bGm\b/g, "G minor");

        // Fix sharp minor chords
        text = text.replace(/\bA sharp m\b/g, "A sharp minor");
        text = text.replace(/\bB sharp m\b/g, "B sharp minor");
        text = text.replace(/\bC sharp m\b/g, "C sharp minor");
        text = text.replace(/\bD sharp m\b/g, "D sharp minor");
        text = text.replace(/\bF sharp m\b/g, "F sharp minor");
        text = text.replace(/\bG sharp m\b/g, "G sharp minor");

        // Fix seventh chords (natural notes)
        text = text.replace(/\bA7\b/g, "A seven");
        text = text.replace(/\bB7\b/g, "B seven");
        text = text.replace(/\bC7\b/g, "C seven");
        text = text.replace(/\bD7\b/g, "D seven");
        text = text.replace(/\bE7\b/g, "E seven");
        text = text.replace(/\bF7\b/g, "F seven");
        text = text.replace(/\bG7\b/g, "G seven");

        // Fix sharp seventh chords
        text = text.replace(/\bA sharp 7\b/g, "A sharp seven");
        text = text.replace(/\bC sharp 7\b/g, "C sharp seven");
        text = text.replace(/\bD sharp 7\b/g, "D sharp seven");
        text = text.replace(/\bF sharp 7\b/g, "F sharp seven");
        text = text.replace(/\bG sharp 7\b/g, "G sharp seven");

        // Fix minor seventh chords
        text = text.replace(/\bAm7\b/g, "A minor seven");
        text = text.replace(/\bBm7\b/g, "B minor seven");
        text = text.replace(/\bCm7\b/g, "C minor seven");
        text = text.replace(/\bDm7\b/g, "D minor seven");
        text = text.replace(/\bEm7\b/g, "E minor seven");
        text = text.replace(/\bFm7\b/g, "F minor seven");
        text = text.replace(/\bGm7\b/g, "G minor seven");

        // Fix sharp minor seventh chords
        text = text.replace(/\bA sharp m7\b/g, "A sharp minor seven");
        text = text.replace(/\bC sharp m7\b/g, "C sharp minor seven");
        text = text.replace(/\bD sharp m7\b/g, "D sharp minor seven");
        text = text.replace(/\bF sharp m7\b/g, "F sharp minor seven");
        text = text.replace(/\bG sharp m7\b/g, "G sharp minor seven");

        // Fix major seventh chords
        text = text.replace(/\bAmaj7\b/g, "A major seven");
        text = text.replace(/\bBmaj7\b/g, "B major seven");
        text = text.replace(/\bCmaj7\b/g, "C major seven");
        text = text.replace(/\bDmaj7\b/g, "D major seven");
        text = text.replace(/\bEmaj7\b/g, "E major seven");
        text = text.replace(/\bFmaj7\b/g, "F major seven");
        text = text.replace(/\bGmaj7\b/g, "G major seven");

        // Fix sharp major seventh chords
        text = text.replace(/\bA sharp maj7\b/g, "A sharp major seven");
        text = text.replace(/\bC sharp maj7\b/g, "C sharp major seven");
        text = text.replace(/\bD sharp maj7\b/g, "D sharp major seven");
        text = text.replace(/\bF sharp maj7\b/g, "F sharp major seven");
        text = text.replace(/\bG sharp maj7\b/g, "G sharp major seven");

        // Fix suspended chords
        text = text.replace(/\bsus2\b/g, "suspended two");
        text = text.replace(/\bsus4\b/g, "suspended four");

        // Fix diminished and augmented
        text = text.replace(/\bdim\b/g, "diminished");
        text = text.replace(/\baug\b/g, "augmented");

        // Fix progression arrows
        text = text.replace(/\s*→\s*/g, " to ");
        text = text.replace(/\s*-->\s*/g, " to ");
        text = text.replace(/\s*->\s*/g, " to ");

        // Fix slash chords (like C/E)
        text = text.replace(/\b([A-G](?:\s*sharp)?(?:m|maj|dim|aug)?(?:7|9|11|13)?)\s*\/\s*([A-G](?:\s*sharp)?)\b/g, "$1 over $2");

        return text;
    }

    // 🆕 NEW: Get list of all available voices
    async listAllVoices() {
        if (!this.googleApiKey) {
            console.log("❌ No Google API key found");
            return;
        }

        try {
            const response = await fetch(`https://texttospeech.googleapis.com/v1/voices?key=${this.googleApiKey}`);
            const data = await response.json();

            const englishVoices = data.voices.filter(voice =>
                voice.languageCodes.includes('en-US') &&
                voice.name.includes('Wavenet')
            );

            console.log("🎭 Available English Wavenet Voices:");
            console.log("=".repeat(50));

            const maleVoices = englishVoices.filter(v => v.ssmlGender === 'MALE');
            const femaleVoices = englishVoices.filter(v => v.ssmlGender === 'FEMALE');

            console.log("👨 MALE VOICES:");
            maleVoices.forEach(voice => {
                const current = voice.name === this.selectedVoice?.name ? " ⭐ CURRENT" : "";
                console.log(`  🔹 ${voice.name}${current}`);
            });

            console.log("\n👩 FEMALE VOICES:");
            femaleVoices.forEach(voice => {
                const current = voice.name === this.selectedVoice?.name ? " ⭐ CURRENT" : "";
                console.log(`  🔹 ${voice.name}${current}`);
            });

            console.log("\n🎯 TO CHANGE VOICE:");
            console.log("voiceCommands.setVoice('en-US-Wavenet-F')");

        } catch (error) {
            console.error("❌ Failed to fetch voices:", error);
        }
    }
}