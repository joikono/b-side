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
            // Wake word detection (fixed)
            if (command.includes("hey beside") || command.includes("hey b side") || command.includes("hey b-side")) {
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
            console.log("🔗 Attempting to connect to backend at http://localhost:8000/api/chat/intent-classification");
            console.log("📤 Sending command:", command);
            
            const response = await fetch("http://localhost:8000/api/chat/intent-classification", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    command: command
                }),
            });

            console.log("📡 Backend response status:", response.status);

            if (!response.ok) {
                const errorText = await response.text();
                console.error("❌ Backend error response:", errorText);
                throw new Error(`Backend error: ${response.status} - ${errorText}`);
            }

            const intentData = await response.json();
            console.log("✅ Intent classification successful:", intentData);
            this.executeIntent(intentData, command);

        } catch (error) {
            console.error("❌ Intent classification failed:", error);
            console.error("🔄 Falling back to conversational mode");
            
            // Check if it's a network connectivity issue
            if (error.message.includes('fetch') || error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
                console.error("🌐 Network error detected - is the backend running at http://localhost:8000?");
                this.speakSmart("Backend connection failed. Please check if the server is running.", 'quick');
                return;
            }
            
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
            
            case "demo":
                console.log("🎭 Intent: Demo detected");
                this.startDemoGreeting();
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
            // Check if user has recorded anything yet
            const hasCurrentAnalysis = !!window.uploadedMidiResult;

            // Prepare analysis context if available
            let analysisContext = null;
            if (hasCurrentAnalysis) {
                const result = window.uploadedMidiResult;
                analysisContext = {
                    detected_type: result.detected_type,
                    chord_progression: result.chord_progression,
                    key: result.key,
                    harmonizations: result.harmonizations
                };
            }

            console.log("💬 Sending to backend - hasRecording:", hasCurrentAnalysis);
            console.log("🔗 Attempting conversational endpoint at http://localhost:8000/api/chat/conversational");

            const response = await fetch("http://localhost:8000/api/chat/conversational", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    command: command,
                    has_current_analysis: hasCurrentAnalysis,
                    analysis_context: analysisContext
                }),
            });

            console.log("📡 Conversational response status:", response.status);

            if (!response.ok) {
                const errorText = await response.text();
                console.error("❌ Conversational backend error:", errorText);
                throw new Error(`Backend error: ${response.status} - ${errorText}`);
            }

            const result = await response.json();
            const aiResponse = result.response;
            console.log("💬 AI response:", aiResponse);

            // Use Google TTS for conversational responses
            this.speakWithGoogle(aiResponse, 'conversational');

        } catch (error) {
            console.error("❌ Backend request failed:", error);

            // Check if it's a network connectivity issue
            if (error.message.includes('fetch') || error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
                console.error("🌐 Network error in conversational mode - is the backend running?");
                this.speakSmart("I can't connect to my brain right now. Please check if the backend server is running.", 'quick');
                return;
            }

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

    async startDemoGreeting() {
        const demoGreeting = 
            "Hi there folks! Thanks for coming out today. This hot weather is unbearable, thank god for air condition! But hey, we're here to make music, so let's get this demo rolling!";

        // Use the high-quality Google TTS for the demo greeting
        this.speakSmart(demoGreeting, 'conversational');
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