"""
Servicio de procesamiento de mensajes y generación de respuestas
"""

import re
import os
from datetime import datetime
from typing import List, Dict, Optional

# Importar configuración
try:
    from config import USE_AI, GROQ_API_KEY
except ImportError:
    # Fallback si config.py no existe
    USE_AI = os.getenv("USE_AI", "false").lower() == "true"
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

class ChatService:
    """
    Servicio principal para procesar mensajes y generar respuestas
    Ahora soporta IA usando Groq API (gratuita)
    """
    
    def __init__(self):
        self.commands = {
            "hora": self._get_time,
            "fecha": self._get_date,
            "ayuda": self._get_help,
        }
        # Configurar API de IA (Groq - gratis)
        self.use_ai = USE_AI
        self.groq_api_key = GROQ_API_KEY
        self.ai_model = "llama-3.1-8b-instant"  # Modelo rápido y gratis de Groq
        
        # Log de configuración (solo al iniciar)
        if self.use_ai and self.groq_api_key:
            print("✅ IA activada - Usando Groq API")
        else:
            print("ℹ️ Modo básico - IA desactivada o API key no configurada")
    
    async def process_message(self, user_message: str, session_id: str, history: List[Dict]) -> str:
        """
        Procesa el mensaje del usuario y genera una respuesta
        """
        message_lower = user_message.lower().strip()
        
        # Procesar comandos especiales
        for command, handler in self.commands.items():
            if message_lower.startswith(command):
                return handler()
        
        # Verificar si es un comando "recordar"
        if message_lower.startswith("recordar"):
            return await self._handle_remember(user_message, session_id)
        
        # Si la IA está habilitada y hay API key, usar IA PRIMERO
        # Solo usar respuestas básicas si la IA falla o está desactivada
        if self.use_ai and self.groq_api_key:
            try:
                print(f"🤖 [IA] Procesando: '{user_message}' (historial: {len(history)} mensajes)")
                ai_response = await self._generate_ai_response(user_message, history)
                # Verificar que la respuesta de IA no esté vacía
                if ai_response and ai_response.strip():
                    print(f"✅ [IA] Respuesta generada correctamente")
                    return ai_response
                else:
                    print(f"⚠️ [IA] Respuesta vacía, usando fallback")
            except Exception as e:
                print(f"❌ [IA] Error usando IA: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                # Fallback a respuestas básicas si falla la IA
        else:
            print(f"ℹ️ [Básico] Modo básico (IA: {self.use_ai}, API Key: {bool(self.groq_api_key)})")
        
        # Respuesta conversacional básica (fallback)
        return await self._generate_response(user_message, history)
    
    def _get_time(self) -> str:
        """Obtener la hora actual"""
        now = datetime.now()
        return f"Son las {now.strftime('%H:%M:%S')}"
    
    def _get_date(self) -> str:
        """Obtener la fecha actual"""
        now = datetime.now()
        days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        months = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
        ]
        return f"Hoy es {days[now.weekday()]}, {now.day} de {months[now.month-1]} de {now.year}"
    
    def _get_help(self) -> str:
        """Mostrar ayuda de comandos"""
        help_text = """
📋 Comandos disponibles:
• hora - Mostrar la hora actual
• fecha - Mostrar la fecha actual
• recordar [texto] - Guardar una nota
• ayuda - Mostrar esta ayuda

También puedes conversar conmigo normalmente. Estoy aprendiendo contigo!
        """
        return help_text.strip()
    
    async def _handle_remember(self, message: str, session_id: str) -> str:
        """Manejar comando recordar"""
        # Extraer el texto después de "recordar"
        match = re.match(r'recordar\s+(.+)', message, re.IGNORECASE)
        if match:
            note = match.group(1).strip()
            # Aquí se guardaría en el sistema de memoria permanente
            # Por ahora solo respondemos
            return f"✅ Nota guardada: '{note}'. Te recordaré esto más adelante."
        else:
            return "¿Qué te gustaría que recuerde? Usa: recordar [tu texto]"
    
    async def _generate_response(self, user_message: str, history: List[Dict]) -> str:
        """
        Genera una respuesta conversacional básica
        En el futuro aquí se integrará un modelo de IA
        """
        message_lower = user_message.lower().strip()
        
        # Respuestas básicas según palabras clave
        greetings = ["hola", "hi", "hey", "buenos días", "buenas tardes", "buenas noches", "buen día"]
        farewells = ["adiós", "bye", "hasta luego", "nos vemos", "chao", "chau", "hasta pronto"]
        thanks = ["gracias", "thanks", "thank you", "grax", "thx"]
        questions = ["qué", "cómo", "cuándo", "dónde", "por qué", "quién", "cuál", "cuáles"]
        
        # Verificar saludos (debe ser al inicio del mensaje o como palabra completa)
        for greeting in greetings:
            if message_lower == greeting or message_lower.startswith(greeting + " ") or message_lower.endswith(" " + greeting):
                if len(history) > 0:
                    return "¡Hola de nuevo! ¿Qué tal? ¿En qué más puedo ayudarte?"
                return "¡Hola! 👋 Soy Ecko, tu asistente virtual. Es un placer conocerte. ¿En qué puedo ayudarte hoy?"
        
        # Verificar despedidas
        for farewell in farewells:
            if farewell in message_lower:
                return "¡Hasta luego! 👋 Fue un placer ayudarte. Vuelve cuando quieras, estaré aquí."
        
        # Verificar agradecimientos
        for thank in thanks:
            if thank in message_lower:
                return "¡De nada! 😊 Estoy aquí para ayudarte siempre que lo necesites. ¿Hay algo más?"
        
        # Verificar preguntas
        if any(question in message_lower for question in questions):
            # Respuestas más específicas según el tipo de pregunta
            if "cómo" in message_lower:
                return "Buena pregunta. Todavía estoy aprendiendo, pero intentaré ayudarte. ¿Podrías ser más específico sobre qué quieres saber?"
            elif "qué" in message_lower:
                return "Interesante pregunta. Estoy mejorando día a día para poder responderte mejor. ¿Hay algo más específico en lo que pueda ayudarte ahora?"
            else:
                return "Esa es una buena pregunta. Sigo aprendiendo, pero pronto podré ayudarte mejor con eso. ¿Hay algo más en lo que pueda ayudarte ahora?"
        
        # Respuestas basadas en palabras clave comunes
        if "bien" in message_lower or "bien" in message_lower:
            return "¡Me alegra saberlo! 😊 ¿Hay algo en lo que pueda ayudarte?"
        
        if "mal" in message_lower or "triste" in message_lower or "cansado" in message_lower:
            return "Lo siento escuchar eso. 😔 Espero que las cosas mejoren pronto. ¿Hay algo en lo que pueda ayudarte a sentirte mejor?"
        
        if "nombre" in message_lower:
            return "Mi nombre es Ecko. 🤖 Soy tu asistente virtual personal. Estoy aquí para ayudarte en lo que necesites."
        
        # Detectar preguntas sobre capacidades
        if ("qué puedes hacer" in message_lower or "que puedes hacer" in message_lower or 
            "qué puedes hacer por mi" in message_lower or "que puedes hacer por mi" in message_lower or
            "que podes hacer" in message_lower or "qué podes hacer" in message_lower or
            "que puedes hacer por mi" in message_lower or ("haces" in message_lower and "qué" in message_lower)):
            return "Puedo ayudarte con varias cosas: responder preguntas básicas, recordar información, darte la hora y fecha. También puedes conversar conmigo sobre cualquier tema. Escribe 'ayuda' para ver todos mis comandos."
        
        # Detectar preguntas sobre el nombre
        if ("cómo te llamas" in message_lower or "como te llamas" in message_lower or
            "cuál es tu nombre" in message_lower or "cual es tu nombre" in message_lower or
            "quién eres" in message_lower or "quien eres" in message_lower):
            return "Soy Ecko, tu asistente virtual personal. 🤖 Estoy diseñado para ayudarte y aprender contigo. A medida que conversamos, voy mejorando mis respuestas."
        
        # Detectar preguntas sobre historial
        if ("guardas historial" in message_lower or "guardas conversación" in message_lower or
            "guardas los mensajes" in message_lower or ("memoria" in message_lower and "guardas" in message_lower)):
            return "Sí, guardo el historial de nuestra conversación en esta sesión. Esto me permite recordar lo que hemos hablado y mantener el contexto. Si cierras la sesión, el historial se borra (por ahora)."
        
        # Respuestas más conversacionales usando el historial
        if len(history) >= 2:
            # Si hay conversación previa, referirse a ella
            last_user_msg = ""
            for msg in reversed(history):
                if msg.get("role") == "user":
                    last_user_msg = msg.get("content", "").lower()
                    break
            
            # Respuestas contextuales
            if "sí" in message_lower or "si" in message_lower or "claro" in message_lower or "ok" in message_lower or "okay" in message_lower:
                return "¡Perfecto! 😊 ¿Hay algo más en lo que pueda ayudarte?"
            
            if "no" in message_lower and len(message_lower) < 5:
                return "Entendido. No te preocupes. ¿Hay otra cosa en lo que pueda ayudarte?"
        
        # Respuestas generales más conversacionales
        responses_conversational = [
            "Interesante, cuéntame más. 😊",
            "Entiendo. ¿Hay algo específico en lo que pueda ayudarte con eso?",
            "Eso suena bien. ¿Qué más puedo hacer por ti?",
            "Claro, estoy aquí para ayudarte. ¿Hay algo más?",
            "Gracias por compartir eso conmigo. Sigo aprendiendo contigo. ¿En qué más puedo ayudarte?",
            "Notado. A medida que aprendo, podré ayudarte mejor. ¿Hay algo específico que necesites ahora?",
            "Mmm, interesante. ¿Quieres que haga algo con esa información?",
            "¡Claro! Estoy escuchando. ¿Qué más te gustaría compartir?",
        ]
        
        # Usar el número de mensajes y longitud del mensaje para variar respuestas
        message_length = len(user_message)
        response_index = (len(history) + message_length) % len(responses_conversational)
        return responses_conversational[response_index]
    
    async def _generate_ai_response(self, user_message: str, history: List[Dict]) -> str:
        """
        Genera una respuesta usando Groq API (IA gratuita) - usando requests directamente
        """
        try:
            import aiohttp
            import json
            
            print(f"🔗 [IA] Conectando a Groq API...")
            
            # Preparar el contexto del sistema
            system_prompt = """Eres Ecko, un asistente virtual personal amigable y útil. 
Responde en español de manera conversacional, natural y concisa. 
Sé amigable pero profesional. Si no sabes algo, admítelo honestamente.
Mantén las respuestas cortas y relevantes (máximo 2-3 frases).
Cuando el usuario te diga su nombre, recuérdalo y úsalo en futuras conversaciones."""
            
            # Preparar mensajes para la API (formato conversacional)
            messages = [{"role": "system", "content": system_prompt}]
            
            # Añadir historial (últimos 8 mensajes para mantener contexto)
            recent_history = history[-8:] if len(history) > 8 else history
            for msg in recent_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ["user", "assistant"]:
                    messages.append({"role": role, "content": content})
            
            # Añadir el mensaje actual del usuario
            messages.append({"role": "user", "content": user_message})
            
            print(f"📤 [IA] Enviando request a Groq ({len(messages)} mensajes)...")
            
            # URL de la API de Groq
            url = "https://api.groq.com/openai/v1/chat/completions"
            
            # Headers
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            
            # Datos del request
            payload = {
                "messages": messages,
                "model": self.ai_model,
                "temperature": 0.7,
                "max_tokens": 300,
                "top_p": 0.9,
            }
            
            # Llamar a la API usando aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"API Error {response.status}: {error_text}")
                    
                    data = await response.json()
                    ai_response = data["choices"][0]["message"]["content"].strip()
                    print(f"📥 [IA] Respuesta recibida: {ai_response[:50]}...")
                    return ai_response
            
        except ImportError:
            raise Exception("La librería 'aiohttp' no está instalada. Instala con: pip install aiohttp")
        except Exception as e:
            error_msg = str(e)
            print(f"❌ [IA] Error en API: {type(e).__name__}: {error_msg}")
            raise Exception(f"Error comunicándose con la API de IA: {error_msg}")

