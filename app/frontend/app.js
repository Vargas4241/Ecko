/**
 * Ecko - Frontend JavaScript
 * Maneja la interfaz de chat y comunicación con la API
 * Incluye reconocimiento de voz y modo oscuro/claro
 */

// Definir la clase PRIMERO
class EckoChat {
    constructor() {
        this.apiUrl = window.location.origin;
        this.sessionId = null;
        this.messageInput = document.getElementById('message-input');
        this.chatForm = document.getElementById('chat-form');
        this.chatMessages = document.getElementById('chat-messages');
        this.sendButton = document.getElementById('send-button');
        this.voiceButton = document.getElementById('voice-button');
        // voice-status eliminado - ahora solo se usa status-indicator (SISTEMA ONLINE / ESCUCHANDO)
        this.notificationsContainer = document.getElementById('notifications-container');
        
        // Elementos del diseño Jarvis
        this.dataDisplay = document.getElementById('data-display');
        this.statusIndicator = document.getElementById('status-indicator');
        this.statusVoiceLine = document.getElementById('status-voice');
        
        // Sistema de notificaciones
        this.notificationInterval = null;
        this.lastReminderCheck = null;
        
        // Speech Recognition y Synthesis
        this.recognition = null;
        this.isListening = false;
        this.supportedSpeech = false;
        this.voiceFromAudio = false;
        this.eckoVoice = null;
        this.pendingVoiceMessage = null;
        this.voiceMessageSent = false;
        
        // Modo Jarvis - Voice-first
        this.jarvisMode = true; // Siempre activo ahora
        
        // Timeout para el display de datos
        this.dataDisplayTimeout = null;
        
        // Wake word detection - "Hey Ecko" / "Eco"
        this.wakeWordEnabled = false;
        this.wakeWordRecognition = null;
        this.isWakeWordListening = false;
        this.lastWakeWordTime = null;
        this.detectedWakeWord = null;
        this.fromWakeWord = false;
        
        console.log('🔧 Constructor EckoChat ejecutado (Modo Jarvis)');
        this.init();
    }

    init() {
        console.log('🔧 Inicializando componentes...');
        
        // Inicializar tema
        this.initTheme();
        
        // Inicializar reconocimiento de voz
        this.initSpeechRecognition();
        
        // Inicializar wake word detection ("Hey Ecko" / "Eco")
        this.initWakeWordDetection();
        
        // Cargar voces disponibles para TTS
        this.initTextToSpeech();
        
        // Configurar form
        if (this.chatForm) {
            this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
            console.log('✅ Form submit listener agregado');
        } else {
            console.error('❌ chatForm no encontrado');
        }
        
        // Configurar botones
        this.setupButtons();
        
        // Crear sesión inicial
        this.createSession().then(() => {
            // Iniciar polling de recordatorios después de crear sesión
            this.startReminderPolling();
            // Registrar para push notifications
            this.initPushNotifications();
            // Activar wake word detection después de inicializar todo
            if (this.wakeWordRecognition && !this.wakeWordEnabled) {
                // Esperar un poco para asegurar que todo esté listo
                setTimeout(() => {
                    this.enableWakeWord();
                }, 1500);
            }
        });
        
        // Registrar Service Worker para PWA y Push
        this.registerServiceWorker();
        
        // Focus en input
        if (this.messageInput) {
            this.messageInput.focus();
        }
    }

    setupButtons() {
        console.log('🔘 Configurando botones...');
        
        // Botón de tema - Configuración directa
        const themeBtn = document.getElementById('theme-toggle');
        console.log('🔍 Botón de tema encontrado:', !!themeBtn);
        if (themeBtn) {
            // Limpiar cualquier listener previo
            themeBtn.replaceWith(themeBtn.cloneNode(true));
            const newThemeBtn = document.getElementById('theme-toggle');
            
            newThemeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('🎨 Click en botón de tema detectado');
                this.toggleTheme();
            });
            console.log('✅ Botón de tema configurado');
        } else {
            console.error('❌ Botón de tema no encontrado');
        }
        
        // Botón de voz - Configuración directa
        const voiceBtn = document.getElementById('voice-button');
        console.log('🔍 Botón de voz encontrado:', !!voiceBtn);
        if (voiceBtn) {
            // Limpiar cualquier listener previo
            voiceBtn.replaceWith(voiceBtn.cloneNode(true));
            const newVoiceBtn = document.getElementById('voice-button');
            
            newVoiceBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('🎤 Click en botón de voz detectado');
                this.toggleVoiceRecognition(e);
            });
            
            this.voiceButton = newVoiceBtn;
            console.log('✅ Botón de voz configurado');
        } else {
            console.error('❌ Botón de voz no encontrado');
        }
    }

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('ecko-theme', newTheme);
        console.log('🎨 Tema cambiado a:', newTheme);
    }

    initTheme() {
        const savedTheme = localStorage.getItem('ecko-theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
        console.log('🎨 Tema inicial aplicado:', savedTheme);
    }

    initSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        
        if (!SpeechRecognition) {
            console.warn('⚠️ Speech Recognition no disponible');
            if (this.voiceButton) {
                this.voiceButton.style.display = 'none';
            }
            return;
        }

        this.supportedSpeech = true;
        this.recognition = new SpeechRecognition();
        this.recognition.lang = 'es-ES';
        this.recognition.continuous = true;  // Continuar escuchando
        this.recognition.interimResults = true;  // Mostrar resultados provisionales
        this.recognition.maxAlternatives = 1;
        
        // Variables para controlar el timeout de silencio
        this.silenceTimeout = null;
        this.lastTranscriptTime = null;
        this.silenceDuration = 2000;  // 2 segundos de silencio antes de enviar

        this.recognition.onstart = () => {
            console.log('🎤 Reconocimiento iniciado');
            this.isListening = true;
            this.isWakeWordListening = false; // Asegurar que wake word esté detenido
            this.updateVoiceButton(true);
            // Solo usar updateStatus - muestra "ESCUCHANDO" en el status-indicator
            this.updateStatus('Escuchando', true);
        };

        this.recognition.onresult = async (event) => {
            // Obtener el texto completo de todos los resultados
            let finalTranscript = '';
            let interimTranscript = '';
            
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript + ' ';
                } else {
                    interimTranscript += transcript;
                }
            }
            
            // Actualizar el tiempo de último transcript
            this.lastTranscriptTime = Date.now();
            
            // Combinar todos los resultados finales hasta ahora
            const allFinal = finalTranscript.trim();
            const currentTranscript = allFinal || interimTranscript.trim();
            
            console.log('✅ Texto reconocido:', currentTranscript, 'Final:', !!allFinal, 'Interim:', interimTranscript);
            
            if (!currentTranscript) {
                this.updateStatus('No se detectó habla', false);
                setTimeout(() => this.updateStatus('Listo', false), 2000);
                return;
            }
            
            // Guardar el mensaje pendiente (actualizar con lo más reciente)
            // Si viene del wake word, asegurarse de filtrar el wake word del transcript
            let messageToStore = allFinal || currentTranscript;
            
            // Si viene del wake word, filtrar el wake word inmediatamente
            if (this.fromWakeWord) {
                const wakeWordsToRemove = ['hey ecko', 'hey eco', 'hola ecko', 'hola eco', 'ecko', 'eco'];
                for (const wakeWord of wakeWordsToRemove) {
                    // Remover del inicio
                    messageToStore = messageToStore.replace(new RegExp(`^${wakeWord}\\s+`, 'i'), '');
                    // Remover del medio o final
                    messageToStore = messageToStore.replace(new RegExp(`\\s+${wakeWord}(\\s|$)`, 'gi'), ' ');
                }
                messageToStore = messageToStore.trim();
            }
            
            if (allFinal) {
                this.pendingVoiceMessage = messageToStore;
            } else {
                this.pendingVoiceMessage = messageToStore;
            }
            this.voiceMessageSent = false;
            this.voiceFromAudio = true;
            
            if (this.messageInput) {
                this.messageInput.value = currentTranscript;
            }
            
            // Si hay resultados finales, esperar silencio antes de enviar
            if (allFinal) {
                // Solo usar updateStatus
                this.updateStatus('Escuchando', true);
                
                // Cancelar timeout anterior
                if (this.silenceTimeout) {
                    clearTimeout(this.silenceTimeout);
                }
                
                // Configurar nuevo timeout para esperar silencio
                this.silenceTimeout = setTimeout(() => {
                    if (this.pendingVoiceMessage && !this.voiceMessageSent) {
                        console.log('⏱️ Silencio detectado, enviando mensaje...');
                // Solo usar updateStatus
                this.updateStatus('Enviando...', false);
                        this.sendPendingVoiceMessage();
                    }
                }, this.silenceDuration);
            } else {
                // Resultados provisionales - mostrar que está escuchando
                // Solo usar updateStatus
                this.updateStatus('Escuchando', true);
                
                // Resetear timeout si hay actividad
                if (this.silenceTimeout) {
                    clearTimeout(this.silenceTimeout);
                }
                
                // Si hay un mensaje pendiente de antes, esperar silencio
                if (this.pendingVoiceMessage) {
                    this.silenceTimeout = setTimeout(() => {
                        if (this.pendingVoiceMessage && !this.voiceMessageSent) {
                            console.log('⏱️ Silencio después de interim, enviando...');
                // Solo usar updateStatus
                this.updateStatus('Enviando...', false);
                            this.sendPendingVoiceMessage();
                        }
                    }, this.silenceDuration);
                }
            }
        };

        this.recognition.onerror = (event) => {
            console.error('❌ Error:', event.error);
            this.isListening = false;
            this.updateVoiceButton(false);
            // No usar hideVoiceStatus, solo actualizar estado
            this.updateStatus('Error', false);
            
            let errorMsg = 'Error al reconocer voz. ';
            switch(event.error) {
                case 'no-speech':
                    errorMsg = 'No se detectó habla. Intenta de nuevo.';
                    break;
                case 'audio-capture':
                    errorMsg = 'No se pudo acceder al micrófono. Verifica los permisos.';
                    break;
                case 'not-allowed':
                    errorMsg = 'Permiso de micrófono denegado.';
                    break;
            }
            
            // Mostrar error en el status
            this.updateStatus('Error', false);
            setTimeout(() => this.updateStatus('Listo', false), 4000);
        };

        this.recognition.onend = () => {
            console.log('🛑 Reconocimiento finalizado', {
                pendingMessage: this.pendingVoiceMessage,
                messageSent: this.voiceMessageSent
            });
            
            // Limpiar timeout de silencio
            if (this.silenceTimeout) {
                clearTimeout(this.silenceTimeout);
                this.silenceTimeout = null;
            }
            
            this.isListening = false;
            this.isWakeWordListening = false;
            this.updateVoiceButton(false);
            this.updateStatus('Procesando', false);
            
            // Si hay un mensaje pendiente que no se ha enviado, esperar un poco más y enviarlo
            if (this.pendingVoiceMessage && !this.voiceMessageSent) {
                console.log('📤 Enviando mensaje pendiente desde onend después de timeout');
                this.updateStatus('Enviando...', false);
                // Esperar un poco más para asegurar que capturamos todo
                setTimeout(() => {
                    if (this.pendingVoiceMessage && !this.voiceMessageSent) {
                        this.updateStatus('Enviando...', false);
                        this.sendPendingVoiceMessage();
                    }
                }, 500);
            }
            
            // Reiniciar wake word detection después de enviar
            setTimeout(() => {
                if (this.wakeWordEnabled && !this.isListening && !this.isWakeWordListening) {
                    this.startWakeWordDetection();
                }
            }, 2000);
            
            // Si no hay mensaje pendiente, volver a estado normal
            if (!this.pendingVoiceMessage && !this.voiceFromAudio) {
                setTimeout(() => {
                    this.updateStatus('Listo', false);
                }, 1000);
            }
        };
    }

    initTextToSpeech() {
        if (!('speechSynthesis' in window)) {
            console.warn('⚠️ Text-to-Speech no disponible');
            return;
        }

        const loadVoices = () => {
            const voices = window.speechSynthesis.getVoices();
            console.log(`📋 Voces disponibles: ${voices.length}`);
            
            if (voices.length === 0) {
                console.log('⏳ No hay voces disponibles aún, se cargarán después...');
                return;
            }

            // Lista de voces preferidas en orden de prioridad (mejor calidad primero)
            const preferredVoices = [
                // Primero: voces neurales/premium (mejor calidad)
                voices.find(v => 
                    v.lang.startsWith('es-') && 
                    (v.name.toLowerCase().includes('neural') || 
                     v.name.toLowerCase().includes('premium') ||
                     v.name.toLowerCase().includes('enhanced'))
                ),
                // Segundo: voces masculinas latinoamericanas
                voices.find(v => v.lang.startsWith('es-') && (
                    v.lang === 'es-MX' || v.lang === 'es-AR' || v.lang === 'es-CO' || 
                    v.lang === 'es-CL' || v.lang === 'es-PE'
                ) && (
                    v.name.toLowerCase().includes('male') || 
                    v.name.toLowerCase().includes('hombre') ||
                    v.name.toLowerCase().includes('masculino')
                )),
                // Tercero: cualquier voz latinoamericana
                voices.find(v => (v.lang === 'es-MX' || v.lang === 'es-AR' || v.lang === 'es-CO' || v.lang === 'es-CL' || v.lang === 'es-PE')),
                // Cuarto: cualquier voz en español
                voices.find(v => v.lang.startsWith('es-')),
            ].filter(Boolean);

            if (preferredVoices.length > 0) {
                this.eckoVoice = preferredVoices[0];
                console.log('✅ Voz seleccionada:', this.eckoVoice.name, this.eckoVoice.lang);
            } else {
                console.log('⚠️ No se encontró voz en español, se usará la voz por defecto del navegador');
                // Intentar obtener la primera voz disponible
                if (voices.length > 0) {
                    this.eckoVoice = voices[0];
                    console.log('📝 Usando voz por defecto:', voices[0].name, voices[0].lang);
                }
            }
        };

        // Cargar voces inmediatamente
        loadVoices();
        
        // También escuchar cuando las voces se carguen (importante para algunos navegadores)
        if (window.speechSynthesis.onvoiceschanged !== undefined) {
            window.speechSynthesis.onvoiceschanged = () => {
                console.log('🔄 Voces cambiadas/cargadas, recargando...');
                loadVoices();
            };
        }

        // En algunos navegadores, las voces solo se cargan después de una interacción del usuario
        // Pre-cargar las voces con un utterance silencioso si es posible
        try {
            const testUtterance = new SpeechSynthesisUtterance('');
            testUtterance.volume = 0;
            window.speechSynthesis.speak(testUtterance);
            window.speechSynthesis.cancel();
            console.log('✅ Pre-carga de voces iniciada');
        } catch (e) {
            console.log('ℹ️ Pre-carga de voces no disponible:', e.message);
        }
    }

    initWakeWordDetection() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        
        if (!SpeechRecognition) {
            console.warn('⚠️ Wake word detection no disponible (Speech Recognition requerido)');
            return;
        }

        // Crear reconocimiento separado para wake word
        this.wakeWordRecognition = new SpeechRecognition();
        this.wakeWordRecognition.lang = 'es-ES';
        this.wakeWordRecognition.continuous = true;
        this.wakeWordRecognition.interimResults = true;
        this.wakeWordRecognition.maxAlternatives = 1;

        // Palabras clave para activar
        const wakeWords = ['ecko', 'eco', 'hey ecko', 'hey eco', 'hola ecko', 'hola eco'];
        
        this.wakeWordRecognition.onresult = (event) => {
            let transcript = '';
            
            for (let i = event.resultIndex; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript.toLowerCase().trim() + ' ';
            }
            
            transcript = transcript.trim();
            
            // Verificar si contiene alguna palabra de activación
            const containsWakeWord = wakeWords.some(word => 
                transcript.includes(word.toLowerCase())
            );
            
            if (containsWakeWord && !this.isListening && !this.isWakeWordListening) {
                console.log('🔊 Wake word detectado:', transcript);
                this.lastWakeWordTime = Date.now();
                
                // Guardar el wake word detectado para filtrarlo después
                this.detectedWakeWord = transcript;
                
                // Detener wake word recognition temporalmente
                try {
                    this.wakeWordRecognition.stop();
                } catch (e) {
                    // Ya estaba detenido
                }
                
                // Guardar el transcript completo del wake word para incluirlo en el mensaje
                // Si el transcript completo es "hola ecko" o similar, enviar directamente
                const wakeWordPhrases = ['hola ecko', 'hola eco', 'hey ecko', 'hey eco'];
                const isCompleteGreeting = wakeWordPhrases.some(phrase => transcript.includes(phrase));
                
                if (isCompleteGreeting && transcript.trim().length < 20) {
                    // Es solo un saludo, enviarlo directamente sin esperar más reconocimiento
                    console.log('✅ Saludo completo detectado, enviando directamente:', transcript);
                    this.wakeWordRecognition.stop();
                    setTimeout(() => {
                        // Filtrar solo el wake word, mantener el saludo
                        let message = transcript.replace(/hey\s*(ecko|eco)/gi, '').trim();
                        if (!message) {
                            message = transcript.replace(/(ecko|eco)/gi, 'hola').trim();
                        }
                        if (message) {
                            this.sendMessageFromVoice(message);
                        }
                        // Reiniciar wake word después
                        setTimeout(() => {
                            if (this.wakeWordEnabled && !this.isListening) {
                                this.startWakeWordDetection();
                            }
                        }, 2000);
                    }, 100);
                } else {
                    // Hay más contenido después del wake word, activar reconocimiento principal
                    // NO guardar el transcript del wake word - empezar desde cero
                    setTimeout(() => {
                        if (this.recognition && !this.isListening) {
                            console.log('🎤 Activando reconocimiento principal después de wake word');
                            this.voiceFromAudio = true; // Marcar que viene de wake word
                            // NO guardar el transcript del wake word - empezar limpio
                            this.pendingVoiceMessage = null;
                            this.voiceMessageSent = false;
                            this.isWakeWordListening = false; // Asegurar que esté detenido
                            this.fromWakeWord = true; // Marcar que viene de wake word para filtrar después
                            
                            // Limpiar input
                            if (this.messageInput) {
                                this.messageInput.value = '';
                            }
                            
                            try {
                                this.recognition.start();
                                // Mostrar feedback visual
                                this.updateStatus('Escuchando', true);
                                // Opcional: reproducir sonido de confirmación
                                this.playActivationSound();
                            } catch (error) {
                                console.error('❌ Error activando reconocimiento:', error);
                                // Reiniciar wake word detection si falla
                                setTimeout(() => {
                                    if (this.wakeWordEnabled && !this.isListening) {
                                        this.startWakeWordDetection();
                                    }
                                }, 1000);
                            }
                        }
                    }, 300);
                }
            }
        };

        this.wakeWordRecognition.onerror = (event) => {
            // Ignorar errores comunes (como 'no-speech')
            if (event.error === 'no-speech' || event.error === 'aborted') {
                // Reiniciar automáticamente
                setTimeout(() => {
                    if (!this.isListening && !this.isWakeWordListening) {
                        this.startWakeWordDetection();
                    }
                }, 1000);
            } else {
                console.error('❌ Error en wake word detection:', event.error);
            }
        };

        this.wakeWordRecognition.onend = () => {
            this.isWakeWordListening = false;
            // Si no estamos escuchando activamente, reiniciar wake word detection
            if (!this.isListening && this.wakeWordEnabled) {
                setTimeout(() => {
                    if (!this.isListening && !this.isWakeWordListening && this.wakeWordEnabled) {
                        this.startWakeWordDetection();
                    }
                }, 500);
            }
        };

        // NO habilitar wake word automáticamente - se habilitará después de inicializar todo
        // this.enableWakeWord(); // Comentado - se habilitará en init()
    }

    enableWakeWord() {
        if (!this.wakeWordRecognition) {
            console.warn('⚠️ Wake word recognition no está inicializado');
            return;
        }

        if (this.wakeWordEnabled) {
            return; // Ya está habilitado
        }

        this.wakeWordEnabled = true;
        this.startWakeWordDetection();
        console.log('✅ Wake word detection activado - Di "Hey Ecko" o "Eco" para activar');
        this.updateStatus('Wake word activado', false);
        setTimeout(() => this.updateStatus('Listo', false), 2000);
    }

    disableWakeWord() {
        this.wakeWordEnabled = false;
        if (this.isWakeWordListening) {
            try {
                this.wakeWordRecognition.stop();
            } catch (e) {
                // Ya estaba detenido
            }
        }
        console.log('🔇 Wake word detection desactivado');
    }

    startWakeWordDetection() {
        if (!this.wakeWordEnabled || !this.wakeWordRecognition) {
            return;
        }

        if (this.isListening) {
            // Si ya estamos escuchando activamente, no iniciar wake word
            return;
        }

        try {
            this.isWakeWordListening = true;
            this.wakeWordRecognition.start();
            console.log('👂 Escuchando wake word...');
        } catch (error) {
            // Si ya está iniciado, ignorar el error
            if (!error.message || !error.message.includes('already started')) {
                console.error('❌ Error iniciando wake word detection:', error);
                // Reintentar después de un delay
                setTimeout(() => {
                    this.startWakeWordDetection();
                }, 2000);
            }
        }
    }

    playActivationSound() {
        // Reproducir un sonido breve de confirmación (opcional)
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 800; // Frecuencia agradable
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.1);
        } catch (e) {
            // Si no se puede reproducir sonido, continuar sin él
            console.log('ℹ️ No se pudo reproducir sonido de activación');
        }
    }

    toggleVoiceRecognition(e) {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }

        console.log('🎤 toggleVoiceRecognition llamado', {
            supportedSpeech: this.supportedSpeech,
            recognition: !!this.recognition,
            isListening: this.isListening
        });

        if (!this.supportedSpeech || !this.recognition) {
            alert('Tu navegador no soporta reconocimiento de voz. Usa Chrome, Edge o Safari.');
            return;
        }

        if (this.isListening) {
            console.log('🛑 Deteniendo reconocimiento...');
            
            // Limpiar timeout de silencio
            if (this.silenceTimeout) {
                clearTimeout(this.silenceTimeout);
                this.silenceTimeout = null;
            }
            
            // Si hay un mensaje pendiente, enviarlo antes de detener
            if (this.pendingVoiceMessage && !this.voiceMessageSent) {
                console.log('📤 Enviando mensaje antes de detener manualmente');
                this.sendPendingVoiceMessage();
            }
            this.recognition.stop();
        } else {
            try {
                // IMPORTANTE: Detener wake word antes de iniciar reconocimiento normal
                // En muchos navegadores solo se puede usar una instancia a la vez
                if (this.isWakeWordListening && this.wakeWordRecognition) {
                    console.log('🛑 Deteniendo wake word detection...');
                    try {
                        this.wakeWordRecognition.stop();
                        this.isWakeWordListening = false;
                    } catch (e) {
                        console.log('⚠️ Error deteniendo wake word:', e);
                    }
                }
                
                // Resetear estado de voz
                this.voiceFromAudio = false;
                this.pendingVoiceMessage = null;
                this.voiceMessageSent = false;
                this.lastTranscriptTime = null;
                if (this.silenceTimeout) {
                    clearTimeout(this.silenceTimeout);
                    this.silenceTimeout = null;
                }
                
                console.log('▶️ Iniciando reconocimiento...');
                this.recognition.start();
            } catch (error) {
                console.error('❌ Error:', error);
                if (!error.message || !error.message.includes('already started')) {
                    alert('Error al iniciar el reconocimiento. Intenta de nuevo.');
                    // Reiniciar wake word si falla
                    if (this.wakeWordEnabled && !this.isListening) {
                        setTimeout(() => this.startWakeWordDetection(), 1000);
                    }
                }
            }
        }
    }

    updateVoiceButton(listening) {
        if (!this.voiceButton) {
            this.voiceButton = document.getElementById('voice-button');
        }
        
        if (!this.voiceButton) return;
        
        if (listening) {
            this.voiceButton.classList.add('listening');
            this.voiceButton.style.background = '#ef4444';
            this.voiceButton.style.borderColor = '#ef4444';
            this.voiceButton.style.color = 'white';
            this.voiceButton.title = 'Detener grabación';
        } else {
            this.voiceButton.classList.remove('listening');
            this.voiceButton.style.background = '';
            this.voiceButton.style.borderColor = '';
            this.voiceButton.style.color = '';
            this.voiceButton.title = 'Hablar con Ecko';
        }
    }

    showVoiceStatus(text, type = 'info') {
        // Eliminado - ahora solo se usa el status-indicator
        // El estado se muestra en "Sistema Online" y "Escuchando" / "Listo"
    }

    hideVoiceStatus() {
        // Eliminado - ahora solo se usa el status-indicator
    }

    sendPendingVoiceMessage() {
        if (!this.pendingVoiceMessage || this.voiceMessageSent) {
            console.log('⚠️ No hay mensaje pendiente o ya fue enviado');
            return;
        }
        
        let message = this.pendingVoiceMessage;
        
        // Si viene del wake word, filtrar el wake word del mensaje
        if (this.fromWakeWord) {
            console.log('🔧 Filtrando wake word del mensaje:', message);
            // Filtrar palabras de wake word del mensaje (al inicio, medio o final)
            const wakeWordsToRemove = ['hey ecko', 'hey eco', 'hola ecko', 'hola eco'];
            let cleanedMessage = message;
            
            // Primero remover frases completas de wake word
            for (const wakeWord of wakeWordsToRemove) {
                cleanedMessage = cleanedMessage.replace(new RegExp(`^${wakeWord}\\s*`, 'i'), '');
                cleanedMessage = cleanedMessage.replace(new RegExp(`\\s*${wakeWord}\\s*`, 'i'), ' ');
                cleanedMessage = cleanedMessage.replace(new RegExp(`\\s*${wakeWord}$`, 'i'), '');
            }
            
            // Luego remover palabras individuales "ecko" o "eco" al inicio del mensaje
            cleanedMessage = cleanedMessage.replace(/^(ecko|eco)\s+/i, '');
            cleanedMessage = cleanedMessage.replace(/\s+(ecko|eco)\s+/gi, ' ');
            cleanedMessage = cleanedMessage.replace(/\s+(ecko|eco)$/i, '');
            
            message = cleanedMessage.trim();
            
            console.log('🔧 Mensaje filtrado (removido wake word):', message);
            this.detectedWakeWord = null;
            this.fromWakeWord = false;
        }
        
        // Si el mensaje está vacío después de filtrar, no enviar
        if (!message || message.trim().length === 0) {
            console.log('⚠️ Mensaje vacío después de filtrar wake word, no se envía');
            this.voiceMessageSent = false;
            this.pendingVoiceMessage = null;
            this.updateStatus('No se detectó mensaje', false);
            setTimeout(() => {
                this.updateStatus('Listo', false);
                // Reiniciar wake word
                if (this.wakeWordEnabled && !this.isListening) {
                    setTimeout(() => this.startWakeWordDetection(), 1000);
                }
            }, 2000);
            return;
        }
        
        this.voiceMessageSent = true;
        this.pendingVoiceMessage = null;
        
        console.log('📤 Enviando mensaje de voz:', message);
        this.sendMessageFromVoice(message);
    }

    async sendMessageFromVoice(message) {
        const messageText = message.trim();
        if (!messageText) {
            this.voiceMessageSent = false;
            return;
        }

            // Asegurar que el reconocimiento esté detenido
        if (this.isListening && this.recognition) {
            try {
                this.recognition.stop();
            } catch (e) {
                // Ya estaba detenido, no importa
            }
        }
        
        // Detener wake word detection temporalmente
        if (this.isWakeWordListening && this.wakeWordRecognition) {
            try {
                this.wakeWordRecognition.stop();
                this.isWakeWordListening = false;
            } catch (e) {
                // Ya estaba detenido
            }
        }

        this.setInputDisabled(true);
        this.addMessage('user', messageText);
        if (this.messageInput) {
            this.messageInput.value = '';
        }
        // Solo usar updateStatus
        this.updateStatus('Enviando...', false);

        try {
            const typingId = this.showTypingIndicator();
            const response = await this.sendMessage(messageText);
            this.removeTypingIndicator(typingId);
            this.addMessage('assistant', response.response);
            this.updateStatus('Listo', false);
            
            // SIEMPRE hablar la respuesta cuando viene de voz (tipo Jarvis)
            // En móviles, TTS debe ejecutarse lo más rápido posible después de la interacción
            console.log('🎤 Mensaje de voz enviado, hablando respuesta inmediatamente...');
            // En móviles, especialmente iOS, TTS debe ejecutarse inmediatamente después de la interacción
            // Usar requestAnimationFrame para asegurar que se ejecute en el siguiente frame
            requestAnimationFrame(() => {
                this.speakResponse(response.response);
            });
            
            // Reiniciar wake word detection después de procesar respuesta
            setTimeout(() => {
                if (this.wakeWordEnabled && !this.isListening) {
                    this.startWakeWordDetection();
                }
            }, 3000); // Esperar 3 segundos después de la respuesta
            
            if (response.session_id) {
                this.sessionId = response.session_id;
            }
            
            // Estado ya actualizado arriba
        } catch (error) {
            console.error('Error:', error);
            this.addMessage('assistant', '❌ Lo siento, hubo un error. Por favor intenta de nuevo.');
            this.updateStatus('Error', false);
            setTimeout(() => this.updateStatus('Listo', false), 3000);
        } finally {
            this.setInputDisabled(false);
            this.voiceFromAudio = false;
        }
    }

    async createSession() {
        // Intentar cargar sessionId guardado del localStorage
        const savedSessionId = localStorage.getItem('ecko_session_id');
        if (savedSessionId) {
            console.log('📋 Sesión cargada desde localStorage:', savedSessionId);
            // Verificar que la sesión sigue siendo válida
            try {
                const response = await fetch(`${this.apiUrl}/api/sessions/${savedSessionId}/exists`);
                if (response.ok) {
                    const data = await response.json();
                    if (data.exists) {
                        this.sessionId = savedSessionId;
                        console.log('✅ Sesión válida restaurada');
                        return savedSessionId;
                    } else {
                        console.log('⚠️ Sesión guardada no existe, creando nueva...');
                        localStorage.removeItem('ecko_session_id');
                    }
                } else {
                    console.log('⚠️ Error verificando sesión, creando nueva...');
                    localStorage.removeItem('ecko_session_id');
                }
            } catch (error) {
                console.log('⚠️ Error verificando sesión, creando nueva...', error);
                localStorage.removeItem('ecko_session_id');
            }
        }
        
        // Crear nueva sesión
        try {
            const response = await fetch(`${this.apiUrl}/api/sessions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            this.sessionId = data.session_id;
            // Guardar en localStorage para persistir entre sesiones
            localStorage.setItem('ecko_session_id', this.sessionId);
            console.log('✅ Nueva sesión creada y guardada:', this.sessionId);
            return this.sessionId;
        } catch (error) {
            console.error('❌ Error creando sesión:', error);
            return null;
        }
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        const message = this.messageInput ? this.messageInput.value.trim() : '';
        if (!message) return;

        if (this.isListening && this.recognition) {
            this.recognition.stop();
        }

        const wasFromVoice = this.voiceFromAudio;
        this.voiceFromAudio = false;

        this.setInputDisabled(true);
        this.addMessage('user', message);
        if (this.messageInput) {
            this.messageInput.value = '';
        }
        // Solo usar updateStatus
        this.updateStatus('Procesando...', false);

        try {
            const typingId = this.showTypingIndicator();
            const response = await this.sendMessage(message);
            this.removeTypingIndicator(typingId);
            this.addMessage('assistant', response.response);
            this.updateStatus('Listo', false);
            
            // SIEMPRE hablar cuando viene de voz (tipo Jarvis - todo audio)
            if (wasFromVoice) {
                // Forzar TTS inmediatamente (iOS Safari requiere interacción del usuario)
                setTimeout(() => {
                    this.speakResponse(response.response);
                }, 100);
            }
            
            if (response.session_id) {
                this.sessionId = response.session_id;
            }
        } catch (error) {
            console.error('Error:', error);
            this.addMessage('assistant', '❌ Lo siento, hubo un error. Por favor intenta de nuevo.');
        } finally {
            this.setInputDisabled(false);
            if (this.messageInput) {
                this.messageInput.focus();
            }
        }
    }

    async sendMessage(message) {
        const response = await fetch(`${this.apiUrl}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                session_id: this.sessionId
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error en la respuesta del servidor');
        }

        return await response.json();
    }

    addMessage(role, content) {
        // En modo Jarvis, NO mostramos mensajes normales - solo datos importantes
        // El resto se habla
        
        // Extraer datos importantes de la respuesta
        const extractedData = this.extractImportantData(content);
        
        if (extractedData && this.jarvisMode) {
            // Mostrar solo datos importantes en el display central
            this.updateDataDisplay(extractedData);
        } else if (!this.jarvisMode) {
            // Modo chat tradicional (backup)
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;
            
            const time = new Date().toLocaleTimeString('es-ES', { 
                hour: '2-digit', 
                minute: '2-digit' 
            });

            messageDiv.innerHTML = `
                <div class="message-content">
                    ${this.formatMessage(content)}
                </div>
                <div class="message-time">${time}</div>
            `;

            if (this.chatMessages) {
                this.chatMessages.appendChild(messageDiv);
                this.scrollToBottom();
            }
        }
        
        // NO hablar aquí - se hablará desde handleSubmit/sendMessageFromVoice para evitar duplicados
    }
    
    extractImportantData(text) {
        /**
         * Extrae datos importantes de una respuesta para mostrar en el display Jarvis
         * Retorna null si no hay datos importantes
         */
        
        // Datos a extraer: horas, fechas, números, nombres de notas, tareas, etc.
        const data = {
            type: null,
            value: null,
            label: null
        };
        
        // Horas/fechas
        const timeMatch = text.match(/(?:a las|las|son las)\s+(\d{1,2}:\d{2})/i);
        if (timeMatch) {
            data.type = 'time';
            data.value = timeMatch[1];
            data.label = 'Hora';
            return data;
        }
        
        // Recordatorios creados
        if (text.includes('Recordatorio creado') || text.includes('recordatorio')) {
            const reminderMatch = text.match(/['"]([^'"]+)['"]/);
            if (reminderMatch) {
                data.type = 'reminder';
                data.value = reminderMatch[1];
                data.label = 'Recordatorio';
                return data;
            }
        }
        
        // Notas
        if (text.includes('Nota') && (text.includes('creada') || text.includes('Nota:'))) {
            const noteMatch = text.match(/Nota\s+['"]([^'"]+)['"]/i) || text.match(/Nota\s+'([^']+)'/i);
            if (noteMatch) {
                data.type = 'note';
                data.value = noteMatch[1];
                data.label = 'Nota';
                
                // Si hay contenido, extraerlo también
                const contentMatch = text.match(/:\s*(.+?)(?:\n|$)/);
                if (contentMatch && contentMatch[1].length < 100) {
                    data.value = noteMatch[1] + ': ' + contentMatch[1];
                }
                return data;
            }
        }
        
        // Números/estadísticas
        const numberMatch = text.match(/(\d+)\s+(?:nota|recordatorio|tarea|evento)/i);
        if (numberMatch) {
            data.type = 'count';
            data.value = numberMatch[0];
            data.label = 'Total';
            return data;
        }
        
        // Si no hay datos importantes, retornar null
        return null;
    }
    
    updateDataDisplay(data) {
        /**
         * Actualiza el display central tipo Jarvis con datos importantes
         * Después de 3 segundos, vuelve a mostrar "Sistema Activo"
         */
        if (!this.dataDisplay) return;
        
        // Limpiar cualquier timeout anterior
        if (this.dataDisplayTimeout) {
            clearTimeout(this.dataDisplayTimeout);
            this.dataDisplayTimeout = null;
        }
        
        if (data && data.value) {
            this.dataDisplay.classList.remove('empty');
            this.dataDisplay.innerHTML = `
                <div class="data-label">${data.label || 'Información'}</div>
                <div class="data-value">${data.value}</div>
            `;
            
            // Después de 3 segundos, volver a "Sistema Activo"
            this.dataDisplayTimeout = setTimeout(() => {
                this.dataDisplay.classList.add('empty');
                this.dataDisplay.innerHTML = '<div class="data-item">Sistema Activo</div>';
                this.dataDisplayTimeout = null;
            }, 3000);
        } else {
            // Si no hay datos, mostrar "Sistema Activo" inmediatamente
            this.dataDisplay.classList.add('empty');
            this.dataDisplay.innerHTML = '<div class="data-item">Sistema Activo</div>';
        }
    }
    
    updateStatus(status, listening = false) {
        /**
         * Actualiza el indicador de estado tipo Jarvis
         * Solo actualiza la segunda línea (status-voice), manteniendo "SISTEMA ONLINE" arriba
         */
        if (this.statusVoiceLine) {
            // Convertir a mayúsculas para mantener consistencia visual
            const statusUpper = status.toUpperCase();
            this.statusVoiceLine.textContent = statusUpper;
            this.statusVoiceLine.classList.toggle('active', true);
            this.statusVoiceLine.classList.toggle('listening', listening);
        }
    }

    formatMessage(content) {
        return content.replace(/\n/g, '<br>');
    }

    showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message assistant';
        typingDiv.id = 'typing-indicator';
        
        typingDiv.innerHTML = `
            <div class="message-content">
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;

        if (this.chatMessages) {
            this.chatMessages.appendChild(typingDiv);
            this.scrollToBottom();
        }
        
        return 'typing-indicator';
    }

    removeTypingIndicator(id) {
        const indicator = document.getElementById(id);
        if (indicator) {
            indicator.remove();
        }
    }

    setInputDisabled(disabled) {
        if (this.messageInput) this.messageInput.disabled = disabled;
        if (this.sendButton) this.sendButton.disabled = disabled;
        if (this.voiceButton) this.voiceButton.disabled = disabled;
    }

    speakResponse(text) {
        console.log('🔊 Intentando hablar respuesta:', text.substring(0, 50) + '...');
        
        if (!('speechSynthesis' in window)) {
            console.warn('⚠️ Speech Synthesis no está disponible en este navegador');
            return;
        }

        // En móviles, especialmente iOS, el TTS debe ejecutarse en el contexto de la interacción
        // Usar requestAnimationFrame para asegurar que se ejecute inmediatamente
        const speakNow = () => {
            try {
                // Cancelar cualquier síntesis anterior
                window.speechSynthesis.cancel();
                // Ejecutar inmediatamente en el siguiente frame
                requestAnimationFrame(() => {
                    this._doSpeak(text);
                });
            } catch (e) {
                console.error('❌ Error cancelando síntesis anterior:', e);
                // Si falla, intentar de todas formas
                this._doSpeak(text);
            }
        };
        
        // Si viene de voz (interacción del usuario), ejecutar inmediatamente
        if (this.voiceFromAudio) {
            speakNow();
        } else {
            // Si viene de otra fuente, pequeño delay para móviles
            setTimeout(speakNow, 50);
        }
    }

    _doSpeak(text) {

        // Limpiar y mejorar el texto para mejor pronunciación
        let cleanText = text
            .replace(/[^\w\s.,;:!?¿¡áéíóúñÁÉÍÓÚÑ\-'"]/g, ' ') // Remover caracteres especiales
            .replace(/\s+/g, ' ') // Espacios múltiples a uno solo
            .replace(/\n/g, '. ') // Nueva línea a punto
            .replace(/\.{2,}/g, '.') // Múltiples puntos a uno solo
            .replace(/[✅❌⚠️🔔⏰📋💡🤖🔍]/g, '') // Remover emojis que pueden causar problemas
            .trim();

        if (!cleanText) {
            console.warn('⚠️ Texto vacío después de limpiar');
            return;
        }

        // Dividir texto largo en frases más pequeñas para evitar trabas
        // Reducir tamaño máximo para evitar que se trabe
        const maxLength = 150; // Máximo de caracteres por frase (reducido de 200 para evitar trabas)
        
        const splitIntoPhrases = (text) => {
            // Dividir por puntuación primero
            const sentences = text.match(/[^.!?]+[.!?]+/g) || [text];
            const phrases = [];
            
            for (const sentence of sentences) {
                if (sentence.length <= maxLength) {
                    phrases.push(sentence.trim());
                } else {
                    // Si la frase es muy larga, dividir por comas
                    const parts = sentence.split(/[,;]/);
                    let currentPhrase = '';
                    
                    for (const part of parts) {
                        const trimmed = part.trim();
                        if (currentPhrase.length + trimmed.length + 2 <= maxLength) {
                            currentPhrase += (currentPhrase ? ', ' : '') + trimmed;
                        } else {
                            if (currentPhrase) phrases.push(currentPhrase);
                            currentPhrase = trimmed;
                        }
                    }
                    if (currentPhrase) phrases.push(currentPhrase);
                }
            }
            
            return phrases.filter(p => p.length > 0);
        };

        const phrases = splitIntoPhrases(cleanText);
        console.log(`🔊 Texto dividido en ${phrases.length} frase(s):`, phrases.map(p => p.substring(0, 50) + '...'));

        // Función para seleccionar la mejor voz
        const selectBestVoice = (voices) => {
            // Prioridad 1: Voces neurales/premium (suelen tener "Neural" o "Premium" en el nombre)
            let voice = voices.find(v => 
                v.lang.startsWith('es-') && 
                (v.name.toLowerCase().includes('neural') || 
                 v.name.toLowerCase().includes('premium') ||
                 v.name.toLowerCase().includes('enhanced'))
            );
            
            if (voice) {
                console.log('🎯 Voz premium/neural encontrada:', voice.name);
                return voice;
            }
            
            // Prioridad 2: Voces masculinas latinoamericanas
            voice = voices.find(v => 
                v.lang.startsWith('es-') && 
                (v.lang === 'es-MX' || v.lang === 'es-AR' || v.lang === 'es-CO' || 
                 v.lang === 'es-CL' || v.lang === 'es-PE') &&
                (v.name.toLowerCase().includes('male') || 
                 v.name.toLowerCase().includes('hombre') ||
                 v.name.toLowerCase().includes('masculino'))
            );
            
            if (voice) {
                console.log('🎯 Voz masculina latinoamericana encontrada:', voice.name);
                return voice;
            }
            
            // Prioridad 3: Cualquier voz latinoamericana
            voice = voices.find(v => 
                v.lang === 'es-MX' || v.lang === 'es-AR' || v.lang === 'es-CO' || 
                v.lang === 'es-CL' || v.lang === 'es-PE'
            );
            
            if (voice) {
                console.log('🎯 Voz latinoamericana encontrada:', voice.name);
                return voice;
            }
            
            // Prioridad 4: Cualquier voz en español
            voice = voices.find(v => v.lang.startsWith('es-'));
            
            if (voice) {
                console.log('🎯 Voz en español encontrada:', voice.name);
                return voice;
            }
            
            return voices[0] || null;
        };

        // Función para hablar con mejor configuración
        const speakPhrases = (phraseIndex = 0) => {
            if (phraseIndex >= phrases.length) {
                console.log('✅ Todas las frases habladas');
                return;
            }

            const phrase = phrases[phraseIndex];
            const utterance = new SpeechSynthesisUtterance(phrase);
            
            // Seleccionar la mejor voz disponible
            const voices = window.speechSynthesis.getVoices();
            const selectedVoice = this.eckoVoice || selectBestVoice(voices);
            
            if (selectedVoice) {
                utterance.voice = selectedVoice;
                console.log(`🔊 Frase ${phraseIndex + 1}/${phrases.length} - Voz:`, selectedVoice.name);
            } else {
                utterance.lang = 'es-ES';
                console.log('⚠️ Usando idioma por defecto (es-ES)');
            }
            
            // Parámetros optimizados para sonido más natural y MENOS robótico
            // Rate más lento para sonar más natural y menos robótico
            utterance.rate = 0.95;  // Más lento para sonar más natural y menos robótico
            utterance.pitch = 0.98; // Tono más bajo para sonar más natural (como voz humana real)
            utterance.volume = 1.0;
            
            // Asegurar que se use la mejor voz disponible en cada frase
            if (selectedVoice) {
                utterance.voice = selectedVoice;
                utterance.lang = selectedVoice.lang;
            } else {
                utterance.lang = 'es-ES';
            }

            // Manejar eventos
            utterance.onstart = () => {
                console.log(`✅ Iniciando frase ${phraseIndex + 1}/${phrases.length}`);
                // Animar display central cuando Ecko habla
                if (this.dataDisplay) {
                    this.dataDisplay.classList.add('speaking');
                }
            };

            utterance.onerror = (event) => {
                console.error(`❌ Error en frase ${phraseIndex + 1}:`, event.error);
                // Continuar con la siguiente frase aunque haya error (evita trabas)
                setTimeout(() => {
                    speakPhrases(phraseIndex + 1);
                }, 200);
            };

            utterance.onend = () => {
                console.log(`✅ Frase ${phraseIndex + 1}/${phrases.length} completada`);
                // Si es la última frase, quitar animación
                if (phraseIndex + 1 >= phrases.length) {
                    if (this.dataDisplay) {
                        this.dataDisplay.classList.remove('speaking');
                    }
                }
                // Pausa más larga entre frases para sonar más natural (como pausa de respiración)
                setTimeout(() => {
                    speakPhrases(phraseIndex + 1);
                }, 300); // 300ms de pausa entre frases para sonido más natural
            };

            try {
                window.speechSynthesis.speak(utterance);
            } catch (error) {
                console.error('❌ Error al ejecutar speak():', error);
            }
        };

        // Asegurar que las voces estén cargadas
        const voices = window.speechSynthesis.getVoices();
        if (voices.length === 0) {
            console.log('⏳ Esperando a que las voces se carguen...');
            window.speechSynthesis.onvoiceschanged = () => {
                console.log('✅ Voces cargadas, hablando ahora...');
                window.speechSynthesis.onvoiceschanged = null;
                speakPhrases();
            };
            // Timeout de seguridad
            setTimeout(() => {
                if (window.speechSynthesis.onvoiceschanged) {
                    console.log('⚠️ Timeout esperando voces, intentando hablar de todas formas...');
                    window.speechSynthesis.onvoiceschanged = null;
                    speakPhrases();
                }
            }, 1000);
        } else {
            speakPhrases();
        }
    }

    scrollToBottom() {
        if (this.chatMessages) {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }
    }

    // ========== SISTEMA DE NOTIFICACIONES Y RECORDATORIOS ==========
    
    startReminderPolling() {
        // Verificar recordatorios cada 5 segundos para notificaciones más rápidas
        if (this.notificationInterval) {
            clearInterval(this.notificationInterval);
        }
        
        this.notificationInterval = setInterval(() => {
            this.checkReminders();
        }, 5000); // 5 segundos - para recibir notificaciones rápidamente
        
        // Verificar inmediatamente
        this.checkReminders();
        
        console.log('✅ Polling de recordatorios iniciado (cada 5 segundos)');
    }

    stopReminderPolling() {
        if (this.notificationInterval) {
            clearInterval(this.notificationInterval);
            this.notificationInterval = null;
            console.log('🛑 Polling de recordatorios detenido');
        }
    }

    async checkReminders() {
        if (!this.sessionId) {
            return;
        }

        try {
            const response = await fetch(`${this.apiUrl}/api/reminders/${this.sessionId}`);
            if (!response.ok) {
                // Si el servicio no está disponible, no mostrar error
                if (response.status === 503) {
                    return;
                }
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            const reminders = data.reminders || [];
            const notifications = data.notifications || [];

            // Mostrar notificaciones pendientes
            if (notifications.length > 0) {
                console.log('🔔 Notificaciones recibidas:', notifications);
                notifications.forEach(notification => {
                    // Mostrar notificación en la UI
                    this.showNotification(notification.message, 'info', 10000);
                    
                    // También agregar al chat como mensaje del asistente
                    this.addMessage('assistant', notification.message);
                    
                    // Hablar la notificación
                    this.speakResponse(notification.message);
                });
            }
            
        } catch (error) {
            // Silenciosamente ignorar errores de polling
            // No queremos spammear la consola
            console.debug('Error en polling de recordatorios:', error);
        }
    }

    showNotification(message, type = 'info', duration = 5000) {
        if (!this.notificationsContainer) {
            console.warn('⚠️ Contenedor de notificaciones no encontrado');
            return;
        }

        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        
        const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : type === 'warning' ? '⚠️' : 'ℹ️';
        
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-icon">${icon}</span>
                <span class="notification-message">${this.formatMessage(message)}</span>
                <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;

        this.notificationsContainer.appendChild(notification);

        // Animar entrada
        setTimeout(() => {
            notification.classList.add('notification-show');
        }, 10);

        // Auto-remover después de duration
        setTimeout(() => {
            notification.classList.remove('notification-show');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300); // Tiempo de animación de salida
        }, duration);

        // Hablar la notificación si es importante
        if (type === 'success' || type === 'warning') {
            this.speakResponse(message);
        }
    }

    async getReminders() {
        if (!this.sessionId) {
            return [];
        }

        try {
            const response = await fetch(`${this.apiUrl}/api/reminders/${this.sessionId}`);
            if (!response.ok) {
                return [];
            }
            const data = await response.json();
            return data.reminders || [];
        } catch (error) {
            console.error('Error obteniendo recordatorios:', error);
            return [];
        }
    }

    async deleteReminder(reminderId) {
        if (!this.sessionId) {
            return false;
        }

        try {
            const response = await fetch(`${this.apiUrl}/api/reminders/${this.sessionId}/${reminderId}`, {
                method: 'DELETE'
            });
            return response.ok;
        } catch (error) {
            console.error('Error eliminando recordatorio:', error);
            return false;
        }
    }

    // ========== PUSH NOTIFICATIONS Y PWA ==========
    
    async registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
                const registration = await navigator.serviceWorker.register('/static/sw.js');
                console.log('✅ Service Worker registrado:', registration.scope);
                
                // Verificar actualizaciones
                registration.addEventListener('updatefound', () => {
                    const newWorker = registration.installing;
                    newWorker.addEventListener('statechange', () => {
                        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                            console.log('🔄 Nueva versión de Ecko disponible');
                        }
                    });
                });
            } catch (error) {
                console.error('❌ Error registrando Service Worker:', error);
            }
        } else {
            console.warn('⚠️ Service Workers no soportados en este navegador');
        }
    }
    
    async initPushNotifications() {
        if (!('Notification' in window)) {
            console.warn('⚠️ Notificaciones no soportadas en este navegador');
            return;
        }
        
        if (!('serviceWorker' in navigator)) {
            console.warn('⚠️ Service Worker no disponible');
            return;
        }
        
        // Verificar si ya tenemos permiso
        if (Notification.permission === 'granted') {
            console.log('✅ Permiso de notificaciones ya concedido');
            await this.subscribeToPush();
        } else if (Notification.permission === 'default') {
            console.log('⏳ Permiso de notificaciones pendiente - El usuario puede activarlo después');
        } else {
            console.log('❌ Permiso de notificaciones denegado');
        }
    }
    
    async requestNotificationPermission() {
        if (!('Notification' in window)) {
            return false;
        }
        
        if (Notification.permission === 'granted') {
            return true;
        }
        
        if (Notification.permission === 'default') {
            const permission = await Notification.requestPermission();
            if (permission === 'granted') {
                console.log('✅ Permiso de notificaciones concedido');
                await this.subscribeToPush();
                return true;
            }
        }
        
        return false;
    }
    
    async subscribeToPush() {
        try {
            const registration = await navigator.serviceWorker.ready;
            
            // Obtener clave pública VAPID del servidor
            const vapidResponse = await fetch(`${this.apiUrl}/api/push/vapid-public-key`);
            const { publicKey } = await vapidResponse.json();
            
            if (!publicKey) {
                console.warn('⚠️ No se obtuvo clave pública VAPID');
                return;
            }
            
            // Convertir clave pública a formato Uint8Array
            const applicationServerKey = this.urlBase64ToUint8Array(publicKey);
            
            // Suscribirse a push notifications
            const subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: applicationServerKey
            });
            
            console.log('✅ Suscrito a push notifications');
            
            // Enviar suscripción al backend
            await this.sendSubscriptionToServer(subscription);
            
            return subscription;
        } catch (error) {
            console.error('❌ Error suscribiéndose a push:', error);
            return null;
        }
    }
    
    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/\-/g, '+')
            .replace(/_/g, '/');
        
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }
    
    async sendSubscriptionToServer(subscription) {
        if (!this.sessionId) {
            console.warn('⚠️ No hay sessionId para guardar suscripción');
            return;
        }
        
        try {
            const response = await fetch(`${this.apiUrl}/api/push/subscribe`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    subscription: subscription
                })
            });
            
            if (response.ok) {
                console.log('✅ Suscripción guardada en el servidor');
                this.showNotification('🔔 Notificaciones push activadas', 'success');
            } else {
                console.error('❌ Error guardando suscripción:', await response.text());
            }
        } catch (error) {
            console.error('❌ Error enviando suscripción:', error);
        }
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Inicializando Ecko Chat...');
    try {
        window.eckoChat = new EckoChat();
        console.log('✅ EckoChat instanciado correctamente:', window.eckoChat);
    } catch (error) {
        console.error('❌ Error al crear EckoChat:', error);
    }
});
