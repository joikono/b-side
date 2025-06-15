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
            if (command.includes("hey wave") || command.includes("hey")) {
                console.log("👋 Wake word detected!");

                const responses = [
                    "What's up?",
                    "Yeah?",
                    "I'm listening",
                    "Go ahead",
                    "What can I do?",
                    "I'm here",
                    "Yes?",
                    "Ready!",
                    "What's on your mind?",
                    "How can I help?",
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
            "intent": "record|play|stop|generate|loop|chat",
            "confidence": 0.0-1.0,
            "parameters": {...any additional params...}
        }

        Intent definitions:
        - "record": User wants to start recording MIDI input (examples: "record", "capture", "reh-cord")
        - "play": User wants to play/hear music or arrangements (examples: "play", "jam", "hear it")
        - "stop": User wants to stop playback (examples: "stop", "pause", "cancel")
        - "generate": User wants to create/arrange music (examples: "generate", "arrange", "make music")
        - "loop": User wants to enable/toggle looping (examples: "loop", "repeat")
        - "chat": General conversation, questions, or unclear commands

        Examples:
        "let's record this" → {"intent": "record", "confidence": 0.9}
        "time to capture this fine tune" → {"intent": "record", "confidence": 0.8}
        "play that arrangement" → {"intent": "play", "confidence": 0.9}
        "make some backing music" → {"intent": "generate", "confidence": 0.8}
        "what should I play next?" → {"intent": "chat", "confidence": 0.9}`;

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
                    temperature: 0.1, // Low temperature for consistent classification
                }),
            });

            const result = await response.json();
            const aiResponse = result.choices[0].message.content;

            // Parse the JSON response
            const intentData = JSON.parse(aiResponse);

            // Execute the classified intent
            this.executeIntent(intentData, command);

        } catch (error) {
            console.error("❌ Intent classification failed:", error);
            // Fallback to conversational mode
            this.handleConversationalCommand(command);
        }
    }

    // Execute classified intents
    executeIntent(intentData, originalCommand) {
        const { intent, confidence } = intentData;

        // For low confidence or chat intent, use conversational mode
        if (confidence < 0.6 || intent === "chat") {
            console.log(`💬 Using conversational mode (intent: ${intent}, confidence: ${confidence})`);
            this.handleConversationalCommand(originalCommand);
            return;
        }

        // Execute high-confidence commands directly
        switch (intent) {
            case "record":
                console.log("▶️ Intent: Recording detected");
                this.speakSmart("Starting recording", 'instant');
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
                this.speakSmart("Generating your arrangement", 'quick');
                analyzeAndGenerate();
                this.extendActiveSession();
                break;

            case "loop":
                console.log("🔄 Intent: Loop detected");
                this.speakSmart("Loop toggled", 'instant');
                toggleCombinedTrackLoop();
                this.extendActiveSession();
                break;

            default:
                // Fallback to conversational mode for unrecognized intents
                this.handleConversationalCommand(originalCommand);
        }
    }

    // Conversational command handler
    async handleConversationalCommand(command) {
        this.extendActiveSession();

        try {
            const apiKey = import.meta.env.PUBLIC_OPENAI_API_KEY;

            // Get current analysis results if available (your existing logic)
            let contextMessage = "";

            if (window.uploadedMidiResult) {
                const result = window.uploadedMidiResult;

                if (result.detected_type === "chord_progression") {
                    const chords = result.chord_progression || [];
                    contextMessage = `Current analyzed chord progression: ${chords.join(" → ")}. Key: ${result.key || "Unknown"}.`;
                } else if (result.harmonizations) {
                    const style = document.getElementById("stickyHarmonyStyle")?.value || "simple_pop";
                    const chords = result.harmonizations[style]?.progression || [];
                    contextMessage = `Current melody harmonized as: ${chords.join(" → ")}. Key: ${result.key || "Unknown"}.`;
                }

                if (result.key_confidence) {
                    contextMessage += ` (${(result.key_confidence * 100).toFixed(0)}% confidence)`;
                }
            }

            // Determine if user has current analysis (your existing logic)
            const hasCurrentAnalysis = !!window.uploadedMidiResult;

            const systemPrompt = hasCurrentAnalysis
                ? `You're a music co-pilot for songwriters and composers.
    Your responses are part of a real-time creative flow, so keep replies under 30 words and focused. The user has already recorded and analyzed their music—you can see their chord progression.

    Your role:
    React naturally: use short, supportive phrases like "nice one," "let's build on that," "here's a thought," or "this could be cool."

    MUSICAL SUGGESTIONS:
    - Suggest specific next chords based on the current progression
    - Offer harmonic variations, extensions, or substitutions—musically grounded and in context
    - Recommend arrangement ideas that build on what they've already played
    - Suggest melodic directions that fit and elevate their chords
    - Think like a producer: give actionable, concrete musical feedback
    - Help break creative blocks with quick, specific musical suggestions

    LYRICAL ASSISTANCE:
    - For lyrics: provide actual lyrical help, suggest rhymes, themes, or specific lines that fit the mood
    - Help with song structure, verse/chorus ideas, or lyrical concepts
    - Offer creative writing support for songwriting

    MUSICAL CONVERSATIONS:
    - Answer questions about bands, artists, genres, and musical influences
    - Compare their music to existing artists or songs when asked
    - Discuss musical theory, techniques, and creative approaches
    - Share insights about musical styles, production techniques, or songwriting methods
    - Help identify what genre or style their music fits into

    Keep things flowing—don't over-explain or interrupt creative momentum.

    Avoid:
    Repeating suggestions to re-record—assume the music is already analyzed.
    Abstract or overly vague advice—always be musically useful.

    Tone: Warm, grounded, musically intelligent, and creatively supportive. You're here to help them make confident next moves.`
                : `You are a music co-pilot for songwriters and composers. Keep responses under 30 words since this is voice interaction.

    Your role:
    CREATIVE SUPPORT:
    - Support through creative blocks by suggesting "reh-CORD" to capture their current musical ideas for analysis
    - For chord progressions: always suggest recording what they have so far to recommend the next chord
    - Arrange music around user ideas to help them hear fuller arrangements
    - Act as producer with suggestive feedback, not demanding direction
    - Stay intuitive and flow-friendly - don't over-talk or disrupt creativity
    - For musical ideas that can be played: suggest saying "reh-CORD" to capture and analyze their MIDI input

    LYRICAL ASSISTANCE:
    - For lyrics: provide actual help with writing, rhyming, themes, and song structure
    - Suggest specific lyrical ideas, word choices, or creative directions
    - Help with songwriting techniques and lyrical flow

    MUSICAL CONVERSATIONS:
    - Answer questions about bands, artists, genres, and musical influences  
    - Discuss music theory, production techniques, and creative approaches
    - Help identify genres, styles, or similar artists
    - Share insights about songwriting methods and musical techniques
    - Compare their ideas to existing music when helpful

    When users ask about chord progressions, always suggest they record their current chords first.
    Always use "reh-CORD" (phonetic spelling) instead of "record" for the verb.

    DECLINE ONLY: Non-music topics like politics, general news, or completely unrelated subjects.

    Tone: Supportive, suggestive, concise. You're an extra set of musically intelligent ears in their creative process.`;

            const messages = [
                {
                    role: "system",
                    content: systemPrompt,
                },
            ];

            // Add context about current analysis if available (your existing logic)
            if (contextMessage) {
                messages.push({
                    role: "system",
                    content: contextMessage,
                });
            }

            // Add user command
            messages.push({
                role: "user",
                content: command,
            });

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

            // Use Google TTS for conversational responses
            this.speakWithGoogle(aiResponse, 'conversational');
        } catch (error) {
            console.error("❌ OpenAI request failed:", error);
            this.speakSmart("Sorry, I couldn't process that right now", 'quick');
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
                input: { text: text },
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
            this.speak(text); // System TTS - instant for super short responses
        } else {
            this.speakWithGoogle(text, type); // Google TTS - much better quality
        }
    }

    // Add this helper method to the VoiceCommands class
    async getVisualizationAsBase64(filename) {
        try {
            const response = await fetch(
                `/generated_visualizations/${filename}`,
            );
            if (!response.ok) {
                throw new Error(
                    `Failed to fetch visualization: ${response.status}`,
                );
            }

            const blob = await response.blob();
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => {
                    const base64 = reader.result.split(",")[1]; // Remove data:image/png;base64, prefix
                    resolve(base64);
                };
                reader.onerror = reject;
                reader.readAsDataURL(blob);
            });
        } catch (error) {
            console.error(
                "Error converting visualization to base64:",
                error,
            );
            return null;
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

            const utterance = new SpeechSynthesisUtterance(text);

            // Same voice selection as your regular speak method
            const voices = speechSynthesis.getVoices();
            if (voices.length > 0) {
                const selectedVoice = voices.find((voice) =>
                    voice.name.includes("Mark"),
                );
                if (selectedVoice) {
                    utterance.voice = selectedVoice;
                }
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
                }, 3000);
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
        }, 30000); // 30 seconds
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
            }, 30000); // Another 30 seconds

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

            const utterance = new SpeechSynthesisUtterance(text);

            utterance.voice = speechSynthesis
                .getVoices()
                .find((voice) => voice.name.includes("Mark"));

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
                }, 1000); // 1 second buffer
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

    // 🆕 NEW: Voice comparison tool
    async compareVoices() {
        const testPhrases = [
            "Starting recording",
            "That's a nice chord progression! Try adding a dominant seventh for more tension.",
            "Let's generate a bass line that complements your melody."
        ];

        for (let i = 0; i < testPhrases.length; i++) {
            const phrase = testPhrases[i];

            console.log(`🎭 Testing phrase ${i + 1}: "${phrase}"`);
            console.log("🔹 System TTS version:");
            this.speak(phrase);

            await new Promise(resolve => setTimeout(resolve, 4000));

            console.log("🔹 Google TTS version:");
            await this.speakWithGoogle(phrase);

            if (i < testPhrases.length - 1) {
                await new Promise(resolve => setTimeout(resolve, 4000));
            }
        }
    }

    // 🆕 NEW: Check usage stats
    getUsageStats() {
        const remainingChars = 1000000 - this.monthlyCharacterCount; // 1M free Wavenet chars
        const percentUsed = (this.monthlyCharacterCount / 1000000) * 100;

        console.log(`📊 Google TTS Usage Stats:`);
        console.log(`📊 Characters used: ${this.monthlyCharacterCount.toLocaleString()}`);
        console.log(`📊 Remaining free: ${remainingChars.toLocaleString()}`);
        console.log(`📊 Percentage used: ${percentUsed.toFixed(1)}%`);

        return {
            used: this.monthlyCharacterCount,
            remaining: remainingChars,
            percentUsed: percentUsed
        };
    }

    // 🎭 ADD THESE METHODS TO YOUR VoiceCommands CLASS

    // 🆕 NEW: Test all available male voices
    async testAllMaleVoices() {
        if (!this.googleApiKey) {
            console.log("❌ No Google API key found");
            return;
        }

        try {
            const response = await fetch(`https://texttospeech.googleapis.com/v1/voices?key=${this.googleApiKey}`);
            const data = await response.json();

            // Get all English male Wavenet voices
            const maleVoices = data.voices.filter(voice =>
                voice.languageCodes.includes('en-US') &&
                voice.name.includes('Wavenet') &&
                voice.ssmlGender === 'MALE'
            );

            console.log(`🎭 Found ${maleVoices.length} male Wavenet voices:`);
            maleVoices.forEach(voice => {
                console.log(`🔹 ${voice.name}`);
            });

            // Test each voice with a sample phrase
            const testPhrase = "Hey! Let's create some amazing music together.";

            for (let i = 0; i < maleVoices.length; i++) {
                const voice = maleVoices[i];
                console.log(`🎤 Testing ${voice.name}...`);

                await this.testSpecificVoice(voice, testPhrase);

                // Wait 4 seconds between voices
                if (i < maleVoices.length - 1) {
                    await new Promise(resolve => setTimeout(resolve, 4000));
                }
            }

        } catch (error) {
            console.error("❌ Failed to fetch voices:", error);
        }
    }

    // 🆕 NEW: Test all available female voices  
    async testAllFemaleVoices() {
        if (!this.googleApiKey) {
            console.log("❌ No Google API key found");
            return;
        }

        try {
            const response = await fetch(`https://texttospeech.googleapis.com/v1/voices?key=${this.googleApiKey}`);
            const data = await response.json();

            // Get all English female Wavenet voices
            const femaleVoices = data.voices.filter(voice =>
                voice.languageCodes.includes('en-US') &&
                voice.name.includes('Wavenet') &&
                voice.ssmlGender === 'FEMALE'
            );

            console.log(`🎭 Found ${femaleVoices.length} female Wavenet voices:`);
            femaleVoices.forEach(voice => {
                console.log(`🔹 ${voice.name}`);
            });

            // Test each voice with a sample phrase
            const testPhrase = "Hey! Let's create some amazing music together.";

            for (let i = 0; i < femaleVoices.length; i++) {
                const voice = femaleVoices[i];
                console.log(`🎤 Testing ${voice.name}...`);

                await this.testSpecificVoice(voice, testPhrase);

                // Wait 4 seconds between voices
                if (i < femaleVoices.length - 1) {
                    await new Promise(resolve => setTimeout(resolve, 4000));
                }
            }

        } catch (error) {
            console.error("❌ Failed to fetch voices:", error);
        }
    }

    // 🆕 NEW: Test a specific voice
    async testSpecificVoice(voice, text) {
        const originalVoice = this.selectedVoice;
        this.selectedVoice = voice; // Temporarily use this voice

        await this.speakWithGoogle(text, 'quick');

        this.selectedVoice = originalVoice; // Restore original voice
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
            console.log("\n🎤 TO TEST VOICES:");
            console.log("voiceCommands.testAllMaleVoices()");
            console.log("voiceCommands.testAllFemaleVoices()");

        } catch (error) {
            console.error("❌ Failed to fetch voices:", error);
        }
    }
}