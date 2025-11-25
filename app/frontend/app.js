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
            const preferredVoices = [
                voices.find(v => v.lang.includes('es-') && (
                    v.name.includes('Latino') || v.name.includes('Latin') || 
                    v.lang === 'es-MX' || v.lang === 'es-AR' || v.lang === 'es-CO' || 
                    v.lang === 'es-CL' || v.lang === 'es-PE'
                ) && (
                    v.name.toLowerCase().includes('male') || 
                    v.name.toLowerCase().includes('hombre')
                )),
                voices.find(v => (v.lang === 'es-MX' || v.lang === 'es-AR' || v.lang === 'es-CO')),
                voices.find(v => v.lang.startsWith('es-')),
            ].filter(Boolean);

            if (preferredVoices.length > 0) {
                this.eckoVoice = preferredVoices[0];
                console.log('✅ Voz seleccionada:', this.eckoVoice.name);
            }
        };

        loadVoices();
        if (window.speechSynthesis.onvoiceschanged !== undefined) {
            window.speechSynthesis.onvoiceschanged = loadVoices;
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
            
            // Hablar la respuesta ya que vino de voz
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
        if (!('speechSynthesis' in window)) return;

        window.speechSynthesis.cancel();

        const cleanText = text
            .replace(/[^\w\s.,;:!?¿¡áéíóúñÁÉÍÓÚÑ\-'"]/g, ' ')
            .replace(/\s+/g, ' ')
            .replace(/\n/g, '. ')
            .trim();

        if (!cleanText) return;

        const utterance = new SpeechSynthesisUtterance(cleanText);
        
        if (this.eckoVoice) {
            utterance.voice = this.eckoVoice;
        } else {
            utterance.lang = 'es-ES';
        }
        
        utterance.rate = 0.95;
        utterance.pitch = 0.85;
        utterance.volume = 1.0;

        window.speechSynthesis.speak(utterance);
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
