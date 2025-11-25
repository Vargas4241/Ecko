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
        this.voiceStatus = document.getElementById('voice-status');
        
        // Speech Recognition y Synthesis
        this.recognition = null;
        this.isListening = false;
        this.supportedSpeech = false;
        this.voiceFromAudio = false;
        this.eckoVoice = null;
        this.pendingVoiceMessage = null;
        this.voiceMessageSent = false;
        
        console.log('🔧 Constructor EckoChat ejecutado');
        this.init();
    }

    init() {
        console.log('🔧 Inicializando componentes...');
        
        // Inicializar tema
        this.initTheme();
        
        // Inicializar reconocimiento de voz
        this.initSpeechRecognition();
        
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
        this.createSession();
        
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
        this.recognition.continuous = false;
        this.recognition.interimResults = false;
        this.recognition.maxAlternatives = 1;

        this.recognition.onstart = () => {
            console.log('🎤 Reconocimiento iniciado');
            this.isListening = true;
            this.updateVoiceButton(true);
            this.showVoiceStatus('🎤 Escuchando...');
        };

        this.recognition.onresult = async (event) => {
            // Obtener el texto completo de todos los resultados
            let finalTranscript = '';
            let interimTranscript = '';
            
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }
            
            const transcript = finalTranscript.trim() || interimTranscript.trim();
            console.log('✅ Texto reconocido:', transcript, 'Final:', !!finalTranscript);
            
            if (!transcript) {
                this.showVoiceStatus('No se detectó habla. Intenta de nuevo.', 'error');
                return;
            }
            
            // Guardar el mensaje pendiente
            this.pendingVoiceMessage = transcript;
            this.voiceMessageSent = false;
            this.voiceFromAudio = true;
            
            if (this.messageInput) {
                this.messageInput.value = transcript;
            }
            
            // Si es un resultado final, marcar para enviar
            if (finalTranscript) {
                this.showVoiceStatus('✅ Mensaje reconocido. Enviando...', 'info');
                // Pequeño delay para asegurar que onend se ejecute primero si es necesario
                setTimeout(() => {
                    this.sendPendingVoiceMessage();
                }, 300);
            } else {
                this.showVoiceStatus('🎤 Escuchando...', 'info');
            }
        };

        this.recognition.onerror = (event) => {
            console.error('❌ Error:', event.error);
            this.isListening = false;
            this.updateVoiceButton(false);
            this.hideVoiceStatus();
            
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
            
            this.showVoiceStatus(errorMsg, 'error');
            setTimeout(() => this.hideVoiceStatus(), 4000);
        };

        this.recognition.onend = () => {
            console.log('🛑 Reconocimiento finalizado', {
                pendingMessage: this.pendingVoiceMessage,
                messageSent: this.voiceMessageSent
            });
            this.isListening = false;
            this.updateVoiceButton(false);
            
            // Si hay un mensaje pendiente que no se ha enviado, enviarlo ahora
            if (this.pendingVoiceMessage && !this.voiceMessageSent) {
                console.log('📤 Enviando mensaje pendiente desde onend');
                setTimeout(() => {
                    this.sendPendingVoiceMessage();
                }, 100);
            } else if (!this.voiceFromAudio && !this.pendingVoiceMessage) {
                setTimeout(() => this.hideVoiceStatus(), 1000);
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
            // Si hay un mensaje pendiente, enviarlo antes de detener
            if (this.pendingVoiceMessage && !this.voiceMessageSent) {
                console.log('📤 Enviando mensaje antes de detener');
                this.sendPendingVoiceMessage();
            }
            this.recognition.stop();
        } else {
            try {
                // Resetear estado de voz
                this.voiceFromAudio = false;
                this.pendingVoiceMessage = null;
                this.voiceMessageSent = false;
                console.log('▶️ Iniciando reconocimiento...');
                this.recognition.start();
            } catch (error) {
                console.error('❌ Error:', error);
                if (!error.message || !error.message.includes('already started')) {
                    alert('Error al iniciar el reconocimiento. Intenta de nuevo.');
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
        if (!this.voiceStatus) {
            this.voiceStatus = document.getElementById('voice-status');
        }
        if (!this.voiceStatus) return;
        
        const statusText = this.voiceStatus.querySelector('.voice-status-text');
        if (statusText) statusText.textContent = text;
        this.voiceStatus.className = `voice-status ${type}`;
        this.voiceStatus.style.display = 'block';
    }

    hideVoiceStatus() {
        if (!this.voiceStatus) {
            this.voiceStatus = document.getElementById('voice-status');
        }
        if (this.voiceStatus) {
            this.voiceStatus.style.display = 'none';
        }
    }

    sendPendingVoiceMessage() {
        if (!this.pendingVoiceMessage || this.voiceMessageSent) {
            console.log('⚠️ No hay mensaje pendiente o ya fue enviado');
            return;
        }
        
        const message = this.pendingVoiceMessage;
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

        this.setInputDisabled(true);
        this.addMessage('user', messageText);
        if (this.messageInput) {
            this.messageInput.value = '';
        }
        this.showVoiceStatus('📤 Enviando mensaje...', 'info');

        try {
            const typingId = this.showTypingIndicator();
            const response = await this.sendMessage(messageText);
            this.removeTypingIndicator(typingId);
            this.addMessage('assistant', response.response);
            
            // Hablar la respuesta inmediatamente (ya que vino de voz)
            // En móviles, TTS debe ejecutarse lo más rápido posible después de la interacción
            console.log('🎤 Mensaje de voz enviado, hablando respuesta inmediatamente...');
            this.speakResponse(response.response);
            
            if (response.session_id) {
                this.sessionId = response.session_id;
            }
            
            this.hideVoiceStatus();
        } catch (error) {
            console.error('Error:', error);
            this.addMessage('assistant', '❌ Lo siento, hubo un error. Por favor intenta de nuevo.');
            this.showVoiceStatus('❌ Error al enviar mensaje', 'error');
            setTimeout(() => this.hideVoiceStatus(), 3000);
        } finally {
            this.setInputDisabled(false);
            this.voiceFromAudio = false;
        }
    }

    async createSession() {
        try {
            const response = await fetch(`${this.apiUrl}/api/sessions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            this.sessionId = data.session_id;
            console.log('Sesión creada:', this.sessionId);
        } catch (error) {
            console.error('Error creando sesión:', error);
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
        this.hideVoiceStatus();

        try {
            const typingId = this.showTypingIndicator();
            const response = await this.sendMessage(message);
            this.removeTypingIndicator(typingId);
            this.addMessage('assistant', response.response);
            
            if (wasFromVoice) {
                this.speakResponse(response.response);
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

        // Cancelar cualquier síntesis anterior
        window.speechSynthesis.cancel();

        // Limpiar y mejorar el texto para mejor pronunciación
        let cleanText = text
            .replace(/[^\w\s.,;:!?¿¡áéíóúñÁÉÍÓÚÑ\-'"]/g, ' ') // Remover caracteres especiales
            .replace(/\s+/g, ' ') // Espacios múltiples a uno solo
            .replace(/\n/g, '. ') // Nueva línea a punto
            .replace(/\.{2,}/g, '.') // Múltiples puntos a uno solo
            .trim();

        if (!cleanText) {
            console.warn('⚠️ Texto vacío después de limpiar');
            return;
        }

        // Dividir texto largo en frases más pequeñas para evitar trabas
        const maxLength = 200; // Máximo de caracteres por frase
        
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
            
            // Parámetros optimizados para sonido más natural
            utterance.rate = 1.0;  // Velocidad normal (antes 0.95, más lento = más robótico)
            utterance.pitch = 1.0; // Tono normal (antes 0.85, más bajo = más robótico)
            utterance.volume = 1.0;
            
            // Pausa natural entre frases
            if (phraseIndex > 0) {
                utterance.volume = 1.0;
            }

            // Manejar eventos
            utterance.onstart = () => {
                console.log(`✅ Iniciando frase ${phraseIndex + 1}/${phrases.length}`);
            };

            utterance.onerror = (event) => {
                console.error(`❌ Error en frase ${phraseIndex + 1}:`, event.error);
                // Continuar con la siguiente frase aunque haya error
                speakPhrases(phraseIndex + 1);
            };

            utterance.onend = () => {
                console.log(`✅ Frase ${phraseIndex + 1}/${phrases.length} completada`);
                // Pequeña pausa entre frases (el navegador la maneja automáticamente)
                setTimeout(() => {
                    speakPhrases(phraseIndex + 1);
                }, 150); // 150ms de pausa entre frases
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
