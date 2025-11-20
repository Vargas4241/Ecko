/**
 * Ecko - Frontend JavaScript
 * Maneja la interfaz de chat y comunicación con la API
 */

class EckoChat {
    constructor() {
        this.apiUrl = window.location.origin; // Usar la misma URL del servidor
        this.sessionId = null;
        this.messageInput = document.getElementById('message-input');
        this.chatForm = document.getElementById('chat-form');
        this.chatMessages = document.getElementById('chat-messages');
        this.sendButton = document.getElementById('send-button');
        
        this.init();
    }

    init() {
        // Event listeners
        this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        
        // Crear sesión inicial
        this.createSession();
        
        // Focus en input al cargar
        this.messageInput.focus();
        
        // Auto-resize input (opcional para futuro)
        // this.messageInput.addEventListener('input', () => this.adjustInputHeight());
    }

    async createSession() {
        try {
            const response = await fetch(`${this.apiUrl}/api/sessions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
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
        
        const message = this.messageInput.value.trim();
        if (!message) return;

        // Deshabilitar input mientras se procesa
        this.setInputDisabled(true);
        
        // Mostrar mensaje del usuario
        this.addMessage('user', message);
        
        // Limpiar input
        this.messageInput.value = '';

        try {
            // Mostrar indicador de escritura
            const typingId = this.showTypingIndicator();
            
            // Enviar mensaje a la API
            const response = await this.sendMessage(message);
            
            // Remover indicador de escritura
            this.removeTypingIndicator(typingId);
            
            // Mostrar respuesta
            this.addMessage('assistant', response.response);
            
            // Actualizar session ID si es necesario
            if (response.session_id) {
                this.sessionId = response.session_id;
            }
        } catch (error) {
            console.error('Error enviando mensaje:', error);
            this.addMessage('assistant', '❌ Lo siento, hubo un error. Por favor intenta de nuevo.');
        } finally {
            this.setInputDisabled(false);
            this.messageInput.focus();
        }
    }

    async sendMessage(message) {
        const response = await fetch(`${this.apiUrl}/api/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
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

        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    formatMessage(content) {
        // Convertir saltos de línea en <br>
        let formatted = content.replace(/\n/g, '<br>');
        
        // Convertir emojis y códigos simples en HTML
        // Por ahora solo preservamos el HTML básico
        
        return formatted;
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

        this.chatMessages.appendChild(typingDiv);
        this.scrollToBottom();
        
        return 'typing-indicator';
    }

    removeTypingIndicator(id) {
        const indicator = document.getElementById(id);
        if (indicator) {
            indicator.remove();
        }
    }

    setInputDisabled(disabled) {
        this.messageInput.disabled = disabled;
        this.sendButton.disabled = disabled;
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    // Método para ajustar altura del input (futuro)
    adjustInputHeight() {
        // Implementación futura para input multilínea
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    new EckoChat();
});

