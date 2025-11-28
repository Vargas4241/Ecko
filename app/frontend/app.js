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
        this.notificationsContainer = document.getElementById('notifications-container');
        
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
        this.createSession().then(() => {
            // Iniciar polling de recordatorios después de crear sesión
            this.startReminderPolling();
            // Registrar para push notifications
            this.initPushNotifications();
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
                this.showVoiceStatus('No se detectó habla. Intenta de nuevo.', 'error');
                return;
            }
            
            // Guardar el mensaje pendiente (actualizar con lo más reciente)
            if (allFinal) {
                this.pendingVoiceMessage = allFinal;
            } else {
                this.pendingVoiceMessage = currentTranscript;
            }
            this.voiceMessageSent = false;
            this.voiceFromAudio = true;
            
            if (this.messageInput) {
                this.messageInput.value = currentTranscript;
            }
            
            // Si hay resultados finales, esperar silencio antes de enviar
            if (allFinal) {
                this.showVoiceStatus('🎤 Escuchando... (esperando más o finaliza con silencio)', 'info');
                
                // Cancelar timeout anterior
                if (this.silenceTimeout) {
                    clearTimeout(this.silenceTimeout);
                }
                
                // Configurar nuevo timeout para esperar silencio
                this.silenceTimeout = setTimeout(() => {
                    if (this.pendingVoiceMessage && !this.voiceMessageSent) {
                        console.log('⏱️ Silencio detectado, enviando mensaje...');
                        this.showVoiceStatus('✅ Mensaje reconocido. Enviando...', 'info');
                        this.sendPendingVoiceMessage();
                    }
                }, this.silenceDuration);
            } else {
                // Resultados provisionales - mostrar que está escuchando
                this.showVoiceStatus('🎤 Escuchando...', 'info');
                
                // Resetear timeout si hay actividad
                if (this.silenceTimeout) {
                    clearTimeout(this.silenceTimeout);
                }
                
                // Si hay un mensaje pendiente de antes, esperar silencio
                if (this.pendingVoiceMessage) {
                    this.silenceTimeout = setTimeout(() => {
                        if (this.pendingVoiceMessage && !this.voiceMessageSent) {
                            console.log('⏱️ Silencio después de interim, enviando...');
                            this.showVoiceStatus('✅ Mensaje reconocido. Enviando...', 'info');
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
            
            // Limpiar timeout de silencio
            if (this.silenceTimeout) {
                clearTimeout(this.silenceTimeout);
                this.silenceTimeout = null;
            }
            
            this.isListening = false;
            this.updateVoiceButton(false);
            
            // Si hay un mensaje pendiente que no se ha enviado, esperar un poco más y enviarlo
            if (this.pendingVoiceMessage && !this.voiceMessageSent) {
                console.log('📤 Enviando mensaje pendiente desde onend después de timeout');
                // Esperar un poco más para asegurar que capturamos todo
                setTimeout(() => {
                    if (this.pendingVoiceMessage && !this.voiceMessageSent) {
                        this.showVoiceStatus('✅ Mensaje reconocido. Enviando...', 'info');
                        this.sendPendingVoiceMessage();
                    }
                }, 500);
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
            
            // Parámetros optimizados para sonido más natural y fluido
            // Rate: 1.1 hace que suene más natural (la velocidad humana es ligeramente más rápida)
            utterance.rate = 1.1;  // Ligeramente más rápido para sonar más natural
            utterance.pitch = 1.05; // Tono ligeramente más alto para menos robótico
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
