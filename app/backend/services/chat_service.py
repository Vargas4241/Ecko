"""
Servicio de procesamiento de mensajes y generación de respuestas
"""

import re
import os
from datetime import datetime
from typing import List, Dict, Optional

# Importar configuración
try:
    from config import USE_AI, GROQ_API_KEY, ENABLE_SEARCH, AI_PROVIDER, ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY
except ImportError:
    # Fallback si config.py no existe
    USE_AI = os.getenv("USE_AI", "false").lower() == "true"
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    ENABLE_SEARCH = os.getenv("ENABLE_SEARCH", "true").lower() == "true"
    AI_PROVIDER = os.getenv("AI_PROVIDER", "groq").lower()
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Importar servicio de búsqueda
try:
    from services.search_service import SearchService
except ImportError:
    SearchService = None
    print("[WARN] [Busqueda] SearchService no disponible")

# Importar servicio de recordatorios
try:
    from services.reminder_service import ReminderService
except ImportError:
    ReminderService = None
    print("[WARN] [Recordatorios] ReminderService no disponible")

# Importar servicio de perfil de usuario
try:
    from services.user_profile_service import UserProfileService
except ImportError:
    UserProfileService = None
    print("[WARN] [Perfil] UserProfileService no disponible")

# Importar servicio de notas
try:
    from services.notes_service import NotesService
except ImportError:
    NotesService = None
    print("[WARN] [Notas] NotesService no disponible")

class ChatService:
    """
    Servicio principal para procesar mensajes y generar respuestas
    Ahora soporta IA usando Groq API (gratuita)
    """
    
    def __init__(self, reminder_service=None, user_profile_service=None, notes_service=None, onboarding_service=None, summary_service=None):
        self.commands = {
            "hora": self._get_time,
            "fecha": self._get_date,
            "ayuda": self._get_help,
            "recordatorios": self._list_reminders,
            "mis recordatorios": self._list_reminders,
        }
        self.summary_service = summary_service
        # Configurar API de IA (soporta Groq, Anthropic Claude, OpenAI, Google Gemini)
        self.use_ai = USE_AI
        self.groq_api_key = GROQ_API_KEY
        self.anthropic_api_key = ANTHROPIC_API_KEY
        self.openai_api_key = OPENAI_API_KEY
        self.gemini_api_key = GEMINI_API_KEY
        self.ai_provider = AI_PROVIDER  # "groq", "anthropic", "openai", "gemini"
        self.ai_model = "llama-3.1-8b-instant"  # Modelo por defecto (Groq)
        
        # Configurar servicio de búsqueda
        self.enable_search = ENABLE_SEARCH
        self.search_service = None
        if self.enable_search and SearchService:
            try:
                self.search_service = SearchService()
                print("[OK] Busqueda web activada")
            except Exception as e:
                print(f"[WARN] [Busqueda] Error inicializando: {e}")
                self.search_service = None
        
        # Configurar servicio de recordatorios
        self.reminder_service = reminder_service
        if self.reminder_service:
            print("[OK] Sistema de recordatorios activado")
        
        # Configurar servicio de perfil de usuario (Jarvis-like)
        self.user_profile_service = user_profile_service
        if self.user_profile_service:
            print("[OK] Sistema de perfil personal activado")
        elif UserProfileService:
            # Si no se pasó pero está disponible, crearlo
            try:
                self.user_profile_service = UserProfileService()
                print("[OK] Sistema de perfil personal inicializado")
            except Exception as e:
                print(f"[WARN] [Perfil] Error inicializando: {e}")
                self.user_profile_service = None
        
        # Configurar servicio de notas
        self.notes_service = notes_service
        if self.notes_service:
            print("[OK] Sistema de notas activado")
        elif NotesService:
            try:
                self.notes_service = NotesService()
                print("[OK] Sistema de notas inicializado")
            except Exception as e:
                print(f"[WARN] [Notas] Error inicializando: {e}")
                self.notes_service = None
        
        # Configurar servicio de onboarding
        try:
            from services.onboarding_service import OnboardingService
            self.onboarding_service = onboarding_service
            if not self.onboarding_service and self.user_profile_service:
                self.onboarding_service = OnboardingService(self.user_profile_service)
                print("[OK] Sistema de onboarding inicializado")
            elif self.onboarding_service:
                print("[OK] Sistema de onboarding activado")
            else:
                self.onboarding_service = None
        except ImportError:
            self.onboarding_service = None
            print("[WARN] OnboardingService no disponible")
        
        # Log de configuración (solo al iniciar)
        if self.use_ai:
            if self.ai_provider == "gemini" and self.gemini_api_key:
                print("[OK] IA activada - Usando Google Gemini API (recomendado, gratis)")
                # El SDK de Google Gemini - usar modelo estable y disponible
                # Usar modelo Gemini estable - sin prefijo "models/" 
                # El SDK de google-generativeai usa nombres simples como "gemini-pro"
                self.ai_model = "gemini-pro"  # Modelo estable
            elif self.ai_provider == "anthropic" and self.anthropic_api_key:
                print("[OK] IA activada - Usando Anthropic Claude API (Cursor Premium)")
                self.ai_model = "claude-3-5-sonnet-20241022"  # Modelo más potente de Claude
            elif self.ai_provider == "openai" and self.openai_api_key:
                print("[OK] IA activada - Usando OpenAI GPT API (gpt-4o-mini - recomendado)")
                self.ai_model = "gpt-4o-mini"  # Modelo económico y potente
            elif self.groq_api_key:
                print("[OK] IA activada - Usando Groq API (gratis)")
            else:
                print("[WARN] IA activada pero no hay API key configurada")
                self.use_ai = False
        else:
            print("[INFO] Modo basico - IA desactivada")
    
    async def process_message(self, user_message: str, session_id: str, history: List[Dict]) -> str:
        """
        Procesa el mensaje del usuario y genera una respuesta
        """
        # CRÍTICO: Filtrar wake word "eco" o "ecko" al INICIO antes de cualquier procesamiento
        # Esto evita que se confunda con el nombre del usuario
        original_message = user_message
        message_lower = user_message.lower().strip()
        
        # Filtrar "eco" o "ecko" al inicio del mensaje (viene del wake word)
        # Patrón: "eco algo" o "ecko algo" -> "algo"
        if message_lower.startswith("eco ") or message_lower.startswith("ecko "):
            user_message = re.sub(r'^(eco|ecko)\s+', '', user_message, flags=re.IGNORECASE).strip()
            message_lower = user_message.lower().strip()
            print(f"[DEBUG] ✅ Wake word filtrado. Original: '{original_message}' -> Limpio: '{user_message}'")
        
        # También filtrar si hay "eco" o "ecko" seguido de un saludo (ej: "eco buen día")
        wake_word_with_greeting = r'^(eco|ecko)\s+(hola|buen|buenos|buenas|hey|hi)'
        if re.match(wake_word_with_greeting, message_lower):
            user_message = re.sub(wake_word_with_greeting, r'\2', user_message, flags=re.IGNORECASE).strip()
            message_lower = user_message.lower().strip()
            print(f"[DEBUG] ✅ Wake word + saludo filtrado. Original: '{original_message}' -> Limpio: '{user_message}'")
        
        # PRIORIDAD MÁXIMA: Verificar si está en proceso de onboarding
        if self.onboarding_service and not self.onboarding_service.is_onboarding_complete(session_id):
            # Está en onboarding - procesar respuesta
            onboarding_result = self.onboarding_service.process_onboarding_response(session_id, user_message)
            
            if onboarding_result["completed"]:
                # Onboarding completado
                return onboarding_result["response"]
            else:
                # Siguiente pregunta o respuesta intermedia
                response = onboarding_result["response"] or onboarding_result.get("next_question")
                if response:
                    return response
        
        # PRIORIDAD 0.5: Si el onboarding no está completo (sin importar historial), iniciar onboarding
        if (self.onboarding_service and 
            not self.onboarding_service.is_onboarding_complete(session_id)):
            # Verificar si ya se inició el onboarding en este mensaje
            # Si no, iniciar ahora
            first_question = self.onboarding_service.get_onboarding_question(session_id)
            if first_question:
                return first_question
        
        # Extraer información del usuario si está disponible (para perfil personal)
        # PERO: NO extraer si el mensaje contiene "ecko" o "eco" como saludo (es el nombre del asistente)
        if self.user_profile_service:
            # Solo extraer info si NO es un saludo directo a Ecko
            greetings_with_ecko = ("ecko" in message_lower or "eco" in message_lower) and any(g in message_lower for g in ["hola", "hi", "hey", "buenos días", "buenas tardes", "buenas noches", "buen día"])
            if not greetings_with_ecko:
                user_info = self.user_profile_service.extract_user_info(session_id, user_message)
                if user_info.get("name"):
                    # Verificar que el nombre no sea "ecko" o "eco"
                    extracted_name = user_info.get("name").lower().strip()
                    if extracted_name not in ["ecko", "eco"]:
                        self.user_profile_service.update_name(session_id, user_info["name"])
                if user_info.get("birthday"):
                    self.user_profile_service.update_birthday(session_id, user_info["birthday"])
        
        # PRIORIDAD 0.3: Detectar comandos de resumen
        summary_keywords = [
            "resumen de hoy", "resumen hoy", "resumen del día",
            "resumen de la semana", "resumen semanal",
            "resumen de todo", "resumen completo",
            "resumen", "dame un resumen", "quiero un resumen"
        ]
        
        if any(keyword in message_lower for keyword in summary_keywords):
            if not self.summary_service:
                return "⚠️ El servicio de resúmenes no está disponible en este momento."
            
            # Detectar período
            period = "today"
            if "semana" in message_lower or "semanal" in message_lower:
                period = "week"
            elif "todo" in message_lower or "completo" in message_lower or "toda" in message_lower:
                period = "all"
            
            try:
                summary = await self.summary_service.generate_summary(
                    session_id=session_id,
                    history=history,
                    period=period
                )
                return summary
            except Exception as e:
                return f"⚠️ Error generando resumen: {str(e)}"
        
        # Procesar comandos especiales
        for command, handler in self.commands.items():
            if message_lower.startswith(command):
                # Algunos comandos necesitan session_id
                if command in ["recordatorios", "mis recordatorios"]:
                    return await handler(session_id)
                return handler()
        
        # PRIORIDAD 0: Detectar preguntas sobre tareas/calendario/eventos y verificar datos reales
        # Esto previene que la IA invente información
        calendar_keywords = ["tareas", "calendario", "eventos", "reuniones", "compromisos", "citas", "agenda", "qué tengo", "que tengo", "tengo algún"]
        has_calendar_keyword = any(keyword in message_lower for keyword in calendar_keywords)
        
        # Solo interceptar si pregunta por datos, NO si quiere crear algo
        is_asking_about = (
            has_calendar_keyword and 
            not any(cmd in message_lower for cmd in ["recordar", "recordatorio", "crear", "agregar", "añadir", "nuevo", "hacer"])
        )
        
        if is_asking_about:
            # Verificar datos reales antes de responder
            reminders = []
            if self.reminder_service:
                reminders = self.reminder_service.get_reminders(session_id, active_only=True)
            
            if not reminders:
                # NO hay recordatorios/tareas reales - responder directamente sin IA
                user_title = "Señor"
                if self.user_profile_service:
                    profile = self.user_profile_service.get_or_create_profile(session_id)
                    user_title = profile.get("preferred_title") or profile.get("name") or "Señor"
                
                if "recordatorio" in message_lower or "pendiente" in message_lower:
                    return f"Señor, no tienes recordatorios pendientes en este momento. Puedes decirme 'recuérdame...' si quieres crear alguno."
                elif "tareas" in message_lower or "tarea" in message_lower:
                    return f"Señor, no tienes tareas pendientes registradas. Puedo ayudarte a crear recordatorios si lo necesitas."
                elif "calendario" in message_lower or "eventos" in message_lower or "reuniones" in message_lower:
                    return f"Señor, no tengo eventos o reuniones registrados en tu calendario. Puedes usar recordatorios para organizarte."
                else:
                    return f"Señor, no tengo información sobre eso registrada. ¿Hay algo específico en lo que pueda ayudarte?"
            else:
                # Hay recordatorios - listarlos
                return await self._list_reminders(session_id)
        
        # PRIORIDAD 1: Verificar comandos para LISTAR recordatorios (antes que crear)
        list_patterns = [
            "tengo recordatorios", "mis recordatorios", "muéstrame recordatorios",
            "listar recordatorios", "qué recordatorios", "que recordatorios",
            "decime vos que tengo en la lista", "dime que tengo en la lista",
            "cuáles son mis recordatorios", "cuales son mis recordatorios",
            "muéstrame mis recordatorios", "muestrame mis recordatorios",
            "qué recordatorios tengo", "que recordatorios tengo"
        ]
        for pattern in list_patterns:
            if pattern in message_lower:
                return await self._list_reminders(session_id)
        
        # Verificar comando directo "recordatorios"
        if message_lower.startswith("recordatorios") or message_lower == "recordatorios":
            return await self._list_reminders(session_id)
        
        # PRIORIDAD 2: Verificar comandos de recordatorios (ANTES que la IA)
        # Ignorar comandos negativos ("no quiero", "no hagas", etc.)
        negative_patterns = ["no quiero", "no hagas", "no necesito", "no quiero que", "no me hagas"]
        is_negative = any(pattern in message_lower for pattern in negative_patterns)
        if is_negative and ("recordatorio" in message_lower or "recordar" in message_lower):
            # Ignorar comandos negativos de recordatorios
            return "Entendido, no crearé ningún recordatorio."
        
        # Buscar patrones que indiquen crear un recordatorio
        reminder_keywords = [
            "recuérdame", "recordarme", "recordar", "recuerda", "recuerdes",
            "recuerdame", "recuardame", "quiero que me recuerdes", "que me recuerdes",
            "lo que quiero hacer es que me recuerdes", "quiero que recuerdes",
            "puedes recordarme", "puedes recordar", "necesito que recuerdes",
            "hacemos un recordatorio", "hacemos recordatorio", "haceme un recordatorio", "hazme un recordatorio",
            "crea un recordatorio", "crear un recordatorio", "añade un recordatorio",
            "agregar recordatorio", "agrega recordatorio",
            "un recordatorio", "mándame un recordatorio", "mandame un recordatorio",
            "envíame un recordatorio", "envíame recordatorio",
            "mándame recordatorio", "mandame recordatorio"
        ]
        
        # Detectar si es un comando de crear recordatorio
        has_reminder_keyword = any(keyword in message_lower for keyword in reminder_keywords)
        
        # También verificar si menciona hora/fecha específica (indicador fuerte de recordatorio)
        # Incluir "dentro de X minutos/horas" que es muy común
        has_time_reference = bool(re.search(r'\d{1,2}:\d{2}|a las \d+|en \d+ (minutos?|horas?)|dentro de \d+ (minutos?|horas?)', message_lower))
        
        # Si tiene palabra clave de recordatorio O menciona tiempo específico con contexto de recordar
        if has_reminder_keyword or (has_time_reference and ("recordatorio" in message_lower or "recuerd" in message_lower)):
            # Verificar que NO sea solo una pregunta sobre recordatorios
            list_reminder_patterns = ["tengo recordatorios", "mis recordatorios", "qué recordatorios tengo"]
            is_listing = any(pattern in message_lower for pattern in list_reminder_patterns)
            if not is_listing:
                print(f"[DEBUG] Detectado comando de recordatorio: '{user_message}'")
                return await self._handle_remember(user_message, session_id)
        
        # PRIORIDAD 3: Eliminar recordatorios
        if message_lower.startswith("eliminar recordatorio") or message_lower.startswith("borrar recordatorio"):
            return await self._handle_delete_reminder(user_message, session_id)
        
        # PRIORIDAD 3.5: Verificar comandos de notas (ANTES de búsqueda e IA)
        # Usar IA para entender mejor las intenciones si los patrones fallan
        if self.notes_service:
            note_command = self.notes_service.parse_note_command(user_message)
            if note_command.get("action"):
                return await self._handle_note_command(note_command, session_id)
            
            # Si no detectó comando pero hay palabras clave de notas, usar IA para interpretar
            note_keywords = ["nota", "notas", "crear nota", "agregar a nota", "leer nota", "eliminar nota"]
            if any(keyword in message_lower for keyword in note_keywords):
                # Usar IA para entender la intención
                intent = await self._interpret_note_intent(user_message, session_id)
                if intent and intent.get("action"):
                    return await self._handle_note_command(intent, session_id)
        
        # PRIORIDAD 4: Interceptar saludos con "Ecko" o "eco" ANTES de llegar a la IA
        # IMPORTANTE: Filtrar "eco" o "ecko" del mensaje antes de procesar, ya que es el nombre del asistente
        # NO debe interpretarse como nombre del usuario
        greetings_list = ["hola", "hi", "hey", "buenos días", "buenas tardes", "buenas noches", "buen día", "buen dia"]
        has_greeting = any(g in message_lower for g in greetings_list)
        has_ecko_mention = "ecko" in message_lower or "eco" in message_lower
        
        # Si el mensaje tiene un saludo Y menciona "ecko" o "eco", es un saludo a Ecko
        # También interceptar si el mensaje empieza con "eco" seguido de algo (del wake word)
        if (has_greeting and has_ecko_mention) or (message_lower.startswith("eco ") and len(message_lower) > 5):
            # Filtrar "eco" o "ecko" del mensaje para evitar confusión
            cleaned_message = message_lower
            
            # Filtrar TODAS las ocurrencias de "eco" o "ecko" como palabra completa
            # Esto maneja casos como "buen día eco como estás" -> "buen día como estás"
            cleaned_message = re.sub(r'\b(eco|ecko)\b', '', cleaned_message, flags=re.IGNORECASE)
            cleaned_message = re.sub(r'\s+', ' ', cleaned_message).strip()  # Limpiar espacios múltiples
            
            # Si después del filtrado solo queda un saludo o está vacío, es un saludo simple
            is_simple_greeting = cleaned_message in greetings_list or len(cleaned_message) < 10 or cleaned_message == ""
            
            # El usuario saluda a Ecko directamente
            if self.user_profile_service:
                profile = self.user_profile_service.get_or_create_profile(session_id)
                name_or_title = profile.get("preferred_title") or profile.get("name") or "Señor"
                user_messages_count = len([msg for msg in history if msg.get("role") == "user"])
                
                if is_simple_greeting:
                    if user_messages_count > 1:
                        return f"Buen día, {name_or_title}. Estoy funcionando perfectamente, gracias por preguntar. ¿En qué puedo ayudarte?"
                    else:
                        return f"Buen día, {name_or_title}. Soy Ecko, tu asistente virtual personal. Es un placer conocerte. ¿En qué puedo ayudarte hoy?"
                else:
                    # Hay más contenido después del saludo, procesar normalmente pero sin "eco"
                    # Reemplazar el mensaje original con el limpiado para que la IA lo procese
                    user_message = cleaned_message
                    message_lower = cleaned_message.lower()
                    print(f"[DEBUG] ✅ Saludo con 'eco' filtrado. Nuevo mensaje: '{user_message}'")
            else:
                user_messages_count = len([msg for msg in history if msg.get("role") == "user"])
                if is_simple_greeting:
                    if user_messages_count > 1:
                        return "Buen día. Estoy funcionando perfectamente, gracias por preguntar. ¿En qué puedo ayudarte?"
                    else:
                        return "Buen día. Soy Ecko, tu asistente virtual personal. Es un placer conocerte. ¿En qué puedo ayudarte hoy?"
                else:
                    # Hay más contenido, procesar sin "eco"
                    user_message = cleaned_message
                    message_lower = cleaned_message.lower()
                    print(f"[DEBUG] ✅ Saludo con 'eco' filtrado. Nuevo mensaje: '{user_message}'")
        
        # PRIORIDAD 4.5: Verificar comandos de búsqueda
        search_commands = ["buscar", "busca", "qué es", "que es", "quien es", "quién es", "noticias"]
        if self.search_service and any(message_lower.startswith(cmd) for cmd in search_commands):
            return await self._handle_search(user_message, message_lower)
        
        # PRIORIDAD 5: Si la IA está habilitada y hay API key, usar IA (ÚLTIMO)
        # Solo usar respuestas básicas si la IA falla o está desactivada
        if self.use_ai and (self.groq_api_key or self.anthropic_api_key or self.openai_api_key or self.gemini_api_key):
            try:
                print(f"🤖 [IA] Procesando: '{user_message}' (historial: {len(history)} mensajes)")
                
                # Verificar si necesita búsqueda (preguntas sobre temas actuales)
                search_result = None
                if self.search_service and self._should_search(message_lower):
                    print(f"🔍 [Búsqueda] Detectada necesidad de búsqueda web")
                    search_result = await self.search_service.search(user_message, max_results=3)
                
                ai_response = await self._generate_ai_response(user_message, history, session_id, search_result)
                # Verificar que la respuesta de IA no esté vacía
                if ai_response and ai_response.strip():
                    print(f"[OK] [IA] Respuesta generada correctamente")
                    # Personalizar respuesta con perfil de usuario (estilo Jarvis)
                    if self.user_profile_service:
                        ai_response = self.user_profile_service.personalize_response(session_id, ai_response)
                    return ai_response
                else:
                    print(f"[WARN] [IA] Respuesta vacia, usando fallback")
            except Exception as e:
                print(f"[ERROR] [IA] Error usando IA: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                # Fallback a respuestas básicas si falla la IA
        else:
            print(f"[INFO] [Basico] Modo basico (IA: {self.use_ai}, API Key: {bool(self.groq_api_key)})")
        
        # Respuesta conversacional básica (fallback)
        response = await self._generate_response(user_message, history, session_id)
        # Personalizar respuesta con perfil de usuario (estilo Jarvis)
        if self.user_profile_service:
            response = self.user_profile_service.personalize_response(session_id, response)
        return response
    
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
• recordar [texto] - Crear un recordatorio (ej: "recuérdame estudiar Docker mañana a las 9am")
• recordatorios - Ver tus recordatorios activos
• eliminar recordatorio [número] - Eliminar un recordatorio
• buscar [tema] - Buscar información en la web
• qué es [concepto] - Buscar definición o información
• noticias [tema] - Buscar noticias recientes
• ayuda - Mostrar esta ayuda

💡 Ejemplos de recordatorios:
  - "recuérdame estudiar Docker mañana a las 9am"
  - "recuérdame hacer ejercicio cada lunes a las 7am"
  - "recuérdame llamar a mamá en 2 horas"

También puedes conversar conmigo normalmente. Puedo buscar información en internet para responderte mejor!
        """
        return help_text.strip()
    
    async def _handle_remember(self, message: str, session_id: str) -> str:
        """Manejar comando recordar - ahora con sistema de alarmas"""
        if not self.reminder_service:
            return "⚠️ El sistema de recordatorios no está disponible."
        
        message_lower = message.lower()
        
        # Extraer el texto después de "recordar" o "recuérdame" - más flexible
        # Busca patrones como: "recordame", "recuérdame", "hacemos un recordatorio", etc.
        patterns = [
            r'lo\s+que\s+quiero\s+hacer\s+es\s+que\s+me\s+recuerdes?\s+(?:ahora\s+)?(?:dentro\s+de\s+\d+\s+(?:minutos?|horas?)\s+)?(?:que\s+)?(.+)',  # "lo que quiero hacer es que me recuerdes ahora dentro de 2 minutos que..."
            r'(?:un\s+)?recordatorio\s+(?:ahora\s+)?(?:a las\s+)?(?:\d{1,2}:\d{2}\s+)?(?:que diga|que|de)\s+(.+)',  # "un recordatorio a las 15:10 que diga..."
            r'(?:un\s+)?recordatorio\s+(?:hoy|mañana|ahora)\s+(?:a las\s+)?(?:\d{1,2}:\d{2}\s+)?(?:que diga|que|de)\s+(.+)',  # "un recordatorio hoy a las 15:10 que diga..."
            r'm[áa]ndame\s+(?:un\s+)?(?:mensaje|recordatorio|notificaci[oó]n)\s+(?:a las\s+)?(?:\d{1,2}:\d{2}\s+)?(?:que diga|que|de)\s+(.+)',  # "mándame un recordatorio a las 15:10 que diga..."
            r'(?:no\s+)?(?:solo\s+)?m[áa]ndame\s+(?:a las\s+)?(?:\d{1,2}:\d{2}\s+)?(?:un\s+)?(?:mensaje|recordatorio|notificaci[oó]n)\s+(?:que diga|que|de)\s+(.+)',  # "no solo mándame a las 15:10 un recordatorio que diga..."
            r'rec(?:u|o)rd(?:a|e)(?:r|me|rme)?\s+(?:ahora\s+)?(?:en\s+\d+\s+(?:minutos?|horas?)\s+|dentro\s+de\s+\d+\s+(?:minutos?|horas?)\s+)?(?:que\s+)?(.+)',  # "recordame ahora en 2 minutos que..." o "dentro de 2 minutos"
            r'(?:quiero\s+)?(?:que\s+)?me\s+recuerdes?\s+(?:ahora\s+)?(?:dentro\s+de\s+\d+\s+(?:minutos?|horas?)\s+)?(?:que\s+)?(.+)',  # "quiero que me recuerdes que ..." o "que me recuerdes ahora dentro de 2 minutos"
            r'puedes?\s+recuerd(?:a|arme)?\s+(?:que\s+)?(.+)',  # "puedes recordarme que ..."
            r'(?:hacemos|haceme|hazme)\s+un\s+recordatorio\s+(?:que\s+)?(.+)',  # "hacemos un recordatorio que ..."
            r'cre(?:a|ar|amos)?\s+(?:un\s+)?recordatorio\s+(?:que\s+)?(.+)',  # "crea un recordatorio que ..."
            r'(?:añade|agrega|agregar)\s+(?:un\s+)?recordatorio\s+(?:que\s+)?(.+)',  # "añade un recordatorio que ..."
        ]
        
        reminder_text = None
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                reminder_text = match.group(1).strip()
                break
        
        # Si no se encontró con regex, intentar extraer todo después de palabras clave
        if not reminder_text:
            keywords = [
                "no solo mándame", "mándame un recordatorio", "mandame un recordatorio",
                "un recordatorio hoy a las", "un recordatorio a las",
                "un recordatorio ahora", "un recordatorio",
                "recuérdame", "recordarme", "recordame", "recuerda", "recordar",
                "hacemos un recordatorio", "haceme un recordatorio", "hazme un recordatorio",
                "crea un recordatorio", "añade un recordatorio",
                "mándame a las", "mandame a las"
            ]
            # Buscar la keyword más larga primero
            keywords.sort(key=len, reverse=True)
            for keyword in keywords:
                if keyword in message_lower:
                    idx = message_lower.find(keyword)
                    reminder_text = message[idx + len(keyword):].strip()
                    # Remover palabras comunes al inicio
                    for prefix in ["que diga", "que", "de", "un mensaje", "una notificación"]:
                        if reminder_text.lower().startswith(prefix + " "):
                            reminder_text = reminder_text[len(prefix):].strip()
                            break
                    break
        
        if reminder_text:
            print(f"[DEBUG] Texto extraído del recordatorio: '{reminder_text}'")
            # Crear recordatorio usando el servicio
            try:
                reminder = self.reminder_service.create_reminder(session_id, message, reminder_text)
                
                # Formatear respuesta
                response = f"✅ Recordatorio creado: '{reminder['message']}'\n"
                
                if reminder.get("recurrence"):
                    rec_type = reminder["recurrence"]["type"]
                    time_str = reminder.get("time_str", "sin hora específica")
                    if rec_type == "daily":
                        response += f"⏰ Se repetirá todos los días a las {time_str}"
                    elif rec_type == "weekly":
                        days = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
                        day = days[reminder["recurrence"].get("day_of_week", 0)]
                        response += f"⏰ Se repetirá todos los {day} a las {time_str}"
                elif reminder.get("target_datetime"):
                    from datetime import datetime
                    target_dt = datetime.fromisoformat(reminder["target_datetime"])
                    response += f"⏰ Alarma programada para {target_dt.strftime('%d/%m/%Y a las %H:%M')}"
                else:
                    response += "ℹ️ Recordatorio guardado (sin fecha/hora específica)"
                
                return response
            except Exception as e:
                print(f"[ERROR] Error creando recordatorio: {e}")
                return f"⚠️ Hubo un error al crear el recordatorio: {str(e)}"
        else:
            return "¿Qué te gustaría que recuerde? Ejemplo: 'recuérdame estudiar Docker mañana a las 9am'"
    
    async def _list_reminders(self, session_id: str = None) -> str:
        """Listar recordatorios activos"""
        if not self.reminder_service:
            return "⚠️ El sistema de recordatorios no está disponible."
        
        if not session_id:
            return "⚠️ Necesito tu sesión para mostrar tus recordatorios."
        
        reminders = self.reminder_service.get_reminders(session_id, active_only=True)
        
        if not reminders:
            return "📋 No tienes recordatorios activos. Usa 'recuérdame...' para crear uno."
        
        response = f"📋 Tienes {len(reminders)} recordatorio(s) activo(s):\n\n"
        
        for i, reminder in enumerate(reminders, 1):
            response += f"{i}. **{reminder['message']}**\n"
            
            if reminder.get("recurrence"):
                rec_type = reminder["recurrence"]["type"]
                time_str = reminder.get("time_str", "sin hora")
                if rec_type == "daily":
                    response += f"   ⏰ Recurrente: Todos los días a las {time_str}\n"
                elif rec_type == "weekly":
                    days = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
                    day = days[reminder["recurrence"].get("day_of_week", 0)]
                    response += f"   ⏰ Recurrente: Todos los {day} a las {time_str}\n"
            elif reminder.get("target_datetime"):
                from datetime import datetime
                target_dt = datetime.fromisoformat(reminder["target_datetime"])
                response += f"   ⏰ Fecha: {target_dt.strftime('%d/%m/%Y a las %H:%M')}\n"
            else:
                response += f"   ℹ️ Sin fecha/hora específica\n"
            
            response += "\n"
        
        response += "💡 Usa 'eliminar recordatorio [número]' para eliminar uno."
        return response
    
    async def _handle_delete_reminder(self, message: str, session_id: str) -> str:
        """Eliminar un recordatorio"""
        if not self.reminder_service:
            return "⚠️ El sistema de recordatorios no está disponible."
        
        # Extraer número del recordatorio
        match = re.search(r'\d+', message)
        if match:
            try:
                index = int(match.group()) - 1  # Convertir a índice (1-based a 0-based)
                reminders = self.reminder_service.get_reminders(session_id, active_only=True)
                
                if 0 <= index < len(reminders):
                    reminder_id = reminders[index]["id"]
                    if self.reminder_service.delete_reminder(session_id, reminder_id):
                        return f"✅ Recordatorio eliminado: '{reminders[index]['message']}'"
                    else:
                        return "⚠️ Error al eliminar el recordatorio."
                else:
                    return f"⚠️ Recordatorio #{index + 1} no encontrado. Usa 'recordatorios' para ver la lista."
            except Exception as e:
                return f"⚠️ Error: {str(e)}"
        else:
            return "⚠️ Por favor especifica el número del recordatorio. Ejemplo: 'eliminar recordatorio 1'"
    
    async def _handle_note_command(self, command: Dict, session_id: str) -> str:
        """Manejar comandos de notas"""
        if not self.notes_service:
            return "⚠️ El sistema de notas no está disponible."
        
        action = command.get("action")
        
        if action == "create":
            title = command.get("title", "").strip()
            content = command.get("content", "").strip()
            
            if not title:
                return "⚠️ Por favor especifica un nombre para la nota. Ejemplo: 'abre una nota nombre compras'"
            
            note = self.notes_service.create_note(session_id, title, content)
            response = f"✅ Nota '{title}' creada"
            if content:
                response += f" con el contenido: {content}"
            return response
        
        elif action == "read":
            title = command.get("title", "").strip()
            if not title:
                return "⚠️ Por favor especifica el nombre de la nota. Ejemplo: 'dime la nota compras'"
            
            note = self.notes_service.get_note_by_title(session_id, title)
            if not note:
                return f"⚠️ No encontré una nota llamada '{title}'. ¿Quieres crearla?"
            
            content = note.get("content", "")
            if not content:
                return f"📝 La nota '{title}' está vacía. Puedes agregarle contenido diciendo 'agrega a la nota {title} que...'"
            
            return f"📝 Nota '{title}':\n\n{content}"
        
        elif action == "append":
            title = command.get("title", "").strip()
            content = command.get("content", "").strip()
            
            if not title:
                return "⚠️ Por favor especifica el nombre de la nota."
            if not content:
                return "⚠️ Por favor especifica qué quieres agregar a la nota."
            
            note = self.notes_service.get_note_by_title(session_id, title)
            if not note:
                return f"⚠️ No encontré una nota llamada '{title}'. ¿Quieres crearla primero?"
            
            updated_note = self.notes_service.append_to_note(session_id, note["id"], content)
            if updated_note:
                return f"✅ Agregado a la nota '{title}': {content}"
            else:
                return "⚠️ Error al agregar contenido a la nota."
        
        elif action == "overwrite":
            title = command.get("title", "").strip()
            content = command.get("content", "").strip()
            
            if not title:
                return "⚠️ Por favor especifica el nombre de la nota."
            if not content:
                return "⚠️ Por favor especifica el nuevo contenido de la nota."
            
            note = self.notes_service.get_note_by_title(session_id, title)
            if not note:
                return f"⚠️ No encontré una nota llamada '{title}'. ¿Quieres crearla primero?"
            
            updated_note = self.notes_service.overwrite_note(session_id, note["id"], content)
            if updated_note:
                return f"✅ Nota '{title}' actualizada con: {content}"
            else:
                return "⚠️ Error al actualizar la nota."
        
        elif action == "delete":
            title = command.get("title", "").strip()
            if not title:
                return "⚠️ Por favor especifica el nombre de la nota a eliminar."
            
            note = self.notes_service.get_note_by_title(session_id, title)
            if not note:
                return f"⚠️ No encontré una nota llamada '{title}'."
            
            if self.notes_service.delete_note(session_id, note["id"]):
                return f"✅ Nota '{title}' eliminada."
            else:
                return "⚠️ Error al eliminar la nota."
        
        elif action == "list":
            notes = self.notes_service.list_notes(session_id)
            if not notes:
                return "📝 No tienes notas guardadas. Puedes crear una diciendo 'abre una nota nombre [nombre]'"
            
            response = f"📝 Tienes {len(notes)} nota(s):\n\n"
            for i, note in enumerate(notes, 1):
                content_preview = note.get("content", "")[:50]
                if len(note.get("content", "")) > 50:
                    content_preview += "..."
                response += f"{i}. **{note['title']}**"
                if content_preview:
                    response += f" - {content_preview}"
                response += "\n"
            
            return response
        
        return "⚠️ Comando de nota no reconocido."
    
    async def _handle_search(self, user_message: str, message_lower: str) -> str:
        """Manejar comandos de búsqueda web"""
        if not self.search_service:
            return "Lo siento, el servicio de búsqueda no está disponible en este momento."
        
        # Extraer el término de búsqueda
        query = user_message
        
        # Limpiar comandos comunes del inicio
        search_prefixes = ["buscar", "busca", "qué es", "que es", "quien es", "quién es", "noticias"]
        for prefix in search_prefixes:
            if message_lower.startswith(prefix):
                query = user_message[len(prefix):].strip()
                break
        
        if not query or len(query) < 2:
            return "¿Qué te gustaría buscar? Ejemplo: 'buscar Python' o 'qué es Docker'"
        
        try:
            # Realizar búsqueda
            search_result = await self.search_service.search(query, max_results=5)
            
            if search_result.get("error"):
                return f"❌ Error en la búsqueda: {search_result['error']}"
            
            # Formatear respuesta
            if search_result.get("answer"):
                response = f"🔍 {search_result['answer']}\n\n"
            else:
                response = f"🔍 Encontré información sobre '{query}':\n\n"
            
            if search_result.get("results") and len(search_result["results"]) > 0:
                response += "**Fuentes encontradas:**\n"
                for i, result in enumerate(search_result["results"][:3], 1):
                    response += f"{i}. **{result.get('title', 'Sin título')}**\n"
                    if result.get("content"):
                        content = result["content"][:150]
                        response += f"   {content}...\n"
                response += "\n¿Quieres más información sobre algún resultado específico?"
            else:
                response += "No encontré resultados específicos. ¿Puedes reformular tu búsqueda?"
            
            return response
            
        except Exception as e:
            print(f"[ERROR] [Busqueda] Error: {e}")
            return f"Lo siento, hubo un error al buscar. Por favor intenta de nuevo."
    
    def _should_search(self, message_lower: str) -> bool:
        """
        Determina si un mensaje requiere búsqueda web
        Busca indicadores de preguntas sobre información actual o externa
        """
        # Indicadores de que necesita búsqueda
        search_indicators = [
            "últimas noticias", "noticias de", "qué pasó", "que pasó",
            "cuándo fue", "cuando fue", "dónde está", "donde esta",
            "información sobre", "datos de", "estadísticas de"
        ]
        
        # Preguntas sobre temas técnicos o actuales
        technical_terms = [
            "python", "docker", "aws", "terraform", "javascript", "react",
            "versión", "version", "actualización", "actualizacion"
        ]
        
        # Si contiene indicadores de búsqueda
        if any(indicator in message_lower for indicator in search_indicators):
            return True
        
        # Si pregunta "qué es" o "quién es" algo
        if re.search(r'qu[ée] es|qui[ée]n es', message_lower):
            return True
        
        # Si menciona términos técnicos + pregunta
        if any(term in message_lower for term in technical_terms) and any(q in message_lower for q in ["qué", "que", "cómo", "como"]):
            return True
        
        return False
    
    async def _generate_response(self, user_message: str, history: List[Dict], session_id: str = None) -> str:
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
        
        # PRIORIDAD ALTA: Interceptar saludos con "Ecko" o "eco" ANTES de llegar a la IA
        if ("ecko" in message_lower or "eco" in message_lower) and any(g in message_lower for g in greetings):
            # El usuario saluda a Ecko directamente (ej: "buen día Ecko", "hola Ecko", "buen día eco")
            # Interceptar ANTES de llegar a la IA para evitar que responda "Hola Ecko" o "Buen día, Eco"
            if self.user_profile_service:
                profile = self.user_profile_service.get_or_create_profile(session_id)
                name_or_title = profile.get("preferred_title") or profile.get("name") or "Señor"
                # Verificar si hay mucho historial (más de 2 mensajes del usuario)
                user_messages_count = len([msg for msg in history if msg.get("role") == "user"])
                if user_messages_count > 1:
                    return f"Buen día, {name_or_title}. Estoy funcionando perfectamente, gracias por preguntar. ¿En qué puedo ayudarte?"
                else:
                    return f"Buen día, {name_or_title}. Soy Ecko, tu asistente virtual personal. Es un placer conocerte. ¿En qué puedo ayudarte hoy?"
            else:
                user_messages_count = len([msg for msg in history if msg.get("role") == "user"])
                if user_messages_count > 1:
                    return "Buen día. Estoy funcionando perfectamente, gracias por preguntar. ¿En qué puedo ayudarte?"
                else:
                    return "Buen día. Soy Ecko, tu asistente virtual personal. Es un placer conocerte. ¿En qué puedo ayudarte hoy?"
        
        # Verificar saludos (debe ser al inicio del mensaje o como palabra completa)
        for greeting in greetings:
            if message_lower == greeting or message_lower.startswith(greeting + " ") or message_lower.endswith(" " + greeting):
                if len(history) > 1:
                    # Si hay perfil de usuario, personalizar saludo
                    if self.user_profile_service:
                        name_or_title = self.user_profile_service.get_user_greeting(session_id)
                        return f"¡Hola de nuevo, {name_or_title}! ¿Qué tal? ¿En qué más puedo ayudarte?"
                    return "¡Hola de nuevo! ¿Qué tal? ¿En qué más puedo ayudarte?"
                # Saludo inicial - intentar obtener nombre del usuario
                if self.user_profile_service:
                    profile = self.user_profile_service.get_or_create_profile(session_id)
                    name_or_title = profile.get("preferred_title") or profile.get("name") or "Señor"
                    return f"¡Hola, {name_or_title}! 👋 Soy Ecko, tu asistente virtual personal. Es un placer conocerte. ¿En qué puedo ayudarte hoy?"
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
    
    async def _generate_ai_response(self, user_message: str, history: List[Dict], session_id: str, search_result: Optional[Dict] = None) -> str:
        """
        Genera una respuesta usando IA - soporta Groq, Anthropic Claude, y OpenAI
        Puede incluir resultados de búsqueda web para información actualizada
        """
        try:
            import aiohttp
            import json
            
            # Personalizar system prompt con información del usuario (estilo Jarvis)
            user_name = None
            user_title = "Señor"
            if self.user_profile_service:
                profile = self.user_profile_service.get_or_create_profile(session_id)
                user_name = profile.get("name")
                user_title = profile.get("preferred_title") or user_name or "Señor"
            
            system_prompt = f"""Eres Ecko, un asistente virtual personal estilo Jarvis de Iron Man. Eres inteligente, preciso y siempre útil.

TU IDENTIDAD (CRÍTICO):
- Tu nombre ES "Ecko" (con K). NUNCA eres "Eco", "eco" ni "ECKO". 
- Cuando el usuario dice "buen día Ecko" o menciona "Ecko"/"eco", está saludándote A TI.
- NUNCA respondas "Hola Ecko" de vuelta. Responde como Ecko saludando al usuario.
- Ejemplo CORRECTO: Usuario: "buen día Ecko" → Tú: "Buen día, {user_title}. ¿En qué puedo ayudarte?"
- Ejemplo INCORRECTO (NUNCA): "Hola Ecko" / "Buen día, Eco" / "Hola, soy Ecko"

PERSONALIDAD Y ESTILO (tipo Jarvis):
- Profesional, preciso y eficiente como un verdadero asistente personal.
- Responde en español de forma natural, conversacional y amigable.
- Trata al usuario como "{user_title}" o usa su nombre si lo conoces.
- Mantén respuestas CONCISAS (máximo 2-3 frases, excepto si pide detalles).
- Sé PROACTIVO: anticipa necesidades, ofrece sugerencias útiles cuando sea apropiado.
- Actúa como asistente personal real: recuerda contexto, preferencias y detalles del usuario.

INTELIGENCIA Y PRECISIÓN:
- NUNCA inventes información que no tengas. Si no sabes algo, dilo claramente: "No tengo esa información" o "No estoy seguro de eso".
- Si preguntan por tareas/recordatorios, SOLO menciona los que REALMENTE existan.
- Si no hay datos, di: "No tienes recordatorios pendientes" (NO inventes).
- NO inventes eventos, reuniones, vuelos, citas o cualquier dato que no exista.
- Cuando el usuario comparte información personal (nombre, preferencias), úsala en futuras conversaciones.
- Si hay información de búsqueda web, úsala para responder con datos actualizados y precisos.

CALIDAD DE RESPUESTAS:
- Prioriza RELEVANCIA sobre cantidad de palabras.
- Responde directamente a lo que preguntan, sin divagar.
- Si no entiendes algo, pregunta de forma breve y clara.
- Sé útil y práctico: ofrece soluciones concretas, no solo información.
- Evita respuestas genéricas o obvias que no aporten valor."""
            
            # Si hay resultados de búsqueda, incluirlos en el contexto
            user_message_with_context = user_message
            if search_result and search_result.get("results"):
                search_info = self.search_service.format_results_for_ai(search_result)
                user_message_with_context = f"""Información de búsqueda web disponible:
{search_info}

Pregunta del usuario: {user_message}

Usa la información de búsqueda para responder de manera precisa y actualizada."""
            
            # Preparar mensajes para la API (formato conversacional)
            messages = [{"role": "system", "content": system_prompt}]
            
            # Añadir historial (últimos 8 mensajes para mantener contexto)
            recent_history = history[-8:] if len(history) > 8 else history
            for msg in recent_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ["user", "assistant"]:
                    messages.append({"role": role, "content": content})
            
            # Añadir el mensaje actual del usuario (con contexto de búsqueda si existe)
            messages.append({"role": "user", "content": user_message_with_context})
            
            # Seleccionar provider y llamar a la API correspondiente
            if self.ai_provider == "gemini" and self.gemini_api_key:
                print(f"🔗 [IA] Conectando a Google Gemini API...")
                return await self._call_gemini_api(messages, user_message_with_context)
            elif self.ai_provider == "anthropic" and self.anthropic_api_key:
                print(f"🔗 [IA] Conectando a Anthropic Claude API...")
                return await self._call_anthropic_api(messages, user_message_with_context)
            elif self.ai_provider == "openai" and self.openai_api_key:
                print(f"🔗 [IA] Conectando a OpenAI API...")
                return await self._call_openai_api(messages)
            else:
                # Default: Groq
                print(f"🔗 [IA] Conectando a Groq API...")
                return await self._call_groq_api(messages)
            
        except ImportError:
            raise Exception("La librería 'aiohttp' no está instalada. Instala con: pip install aiohttp")
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] [IA] Error en API: {type(e).__name__}: {error_msg}")
            raise Exception(f"Error comunicándose con la API de IA: {error_msg}")
    
    async def _call_groq_api(self, messages: List[Dict]) -> str:
        """Llamar a Groq API"""
        import aiohttp
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "messages": messages,
            "model": self.ai_model,
            "temperature": 0.7,
            "max_tokens": 300,
            "top_p": 0.9,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API Error {response.status}: {error_text}")
                
                data = await response.json()
                ai_response = data["choices"][0]["message"]["content"].strip()
                print(f"📥 [IA] Respuesta recibida: {ai_response[:50]}...")
                return ai_response
    
    async def _call_anthropic_api(self, messages: List[Dict], user_message: str) -> str:
        """Llamar a Anthropic Claude API (Cursor Premium)"""
        import aiohttp
        
        url = "https://api.anthropic.com/v1/messages"
        
        # Convertir mensajes de OpenAI format a Anthropic format
        system_prompt = messages[0]["content"] if messages and messages[0]["role"] == "system" else ""
        conversation_messages = [msg for msg in messages if msg["role"] != "system"]
        
        headers = {
            "x-api-key": self.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.ai_model,
            "max_tokens": 300,
            "temperature": 0.7,
            "messages": conversation_messages
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API Error {response.status}: {error_text}")
                
                data = await response.json()
                # Anthropic devuelve el contenido en data["content"][0]["text"]
                ai_response = data["content"][0]["text"].strip()
                print(f"📥 [IA] Respuesta recibida: {ai_response[:50]}...")
                return ai_response
    
    async def _call_openai_api(self, messages: List[Dict]) -> str:
        """Llamar a OpenAI API"""
        import aiohttp
        
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "messages": messages,
            "model": self.ai_model,
            "temperature": 0.6,  # Más bajo para respuestas más precisas y menos "tontas"
            "max_tokens": 400,    # Aumentado para respuestas más completas cuando sea necesario
            "top_p": 0.9,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API Error {response.status}: {error_text}")
                
                data = await response.json()
                ai_response = data["choices"][0]["message"]["content"].strip()
                print(f"📥 [IA] Respuesta recibida: {ai_response[:50]}...")
                return ai_response
    
    async def _call_gemini_api(self, messages: List[Dict], user_message: str) -> str:
        """Llamar a Google Gemini API usando el SDK oficial"""
        try:
            import google.generativeai as genai
            import asyncio
        except ImportError:
            raise Exception("google-generativeai no está instalado. Ejecuta: pip install google-generativeai")
        
        # Configurar la API key
        genai.configure(api_key=self.gemini_api_key)
        
        # Extraer system prompt si existe
        system_prompt = ""
        conversation_history = []
        
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            
            if role == "system":
                system_prompt = content
            elif role == "user":
                conversation_history.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                conversation_history.append({"role": "model", "parts": [{"text": content}]})
        
        # Si no hay historial, crear uno con el mensaje del usuario
        if not conversation_history:
            conversation_history = [{"role": "user", "parts": [{"text": user_message}]}]
        
        # Obtener el modelo - intentar varios modelos hasta encontrar uno que funcione
        model_name = getattr(self, 'ai_model', "gemini-pro")
        
        # Lista de modelos a intentar en orden de preferencia (nombres sin prefijo)
        models_to_try = [
            "gemini-1.5-flash",  # Más rápido y disponible
            "gemini-1.5-pro",    # Más potente  
            "gemini-pro"         # Fallback
        ]
        
        if model_name not in models_to_try:
            models_to_try.insert(0, model_name)
        
        model = None
        last_error = None
        
        for attempt_model in models_to_try:
            try:
                print(f"[IA] Intentando modelo Gemini: {attempt_model}")
                model = genai.GenerativeModel(attempt_model)
                print(f"[OK] Modelo {attempt_model} cargado correctamente")
                self.ai_model = attempt_model  # Guardar el que funcionó
                break
            except Exception as e:
                last_error = e
                print(f"[WARN] Modelo {attempt_model} no disponible: {e}")
                continue
        
        if model is None:
            error_msg = f"Error: Ningún modelo de Gemini está disponible. Último error: {last_error}. Verifica tu API key de Gemini."
            print(f"[ERROR] {error_msg}")
            raise Exception(error_msg)
        
        # Configurar el sistema de generación
        generation_config = {
            "temperature": 0.7,
            "top_k": 40,
            "top_p": 0.95,
            "max_output_tokens": 1024,
        }
        
        # Preparar el contenido para el chat
        # Si hay system prompt, añadirlo al primer mensaje
        if system_prompt:
            if conversation_history and conversation_history[0]["role"] == "user":
                original_text = conversation_history[0]["parts"][0]["text"]
                conversation_history[0]["parts"][0]["text"] = f"{system_prompt}\n\n{original_text}"
        
        # Construir el historial en formato del SDK de Gemini
        # El SDK necesita una lista de dicts con "role" y "parts"
        history_for_chat = []
        for msg in conversation_history:
            role = msg["role"]
            text = msg["parts"][0]["text"]
            history_for_chat.append({
                "role": role,
                "parts": [{"text": text}]
            })
        
        # Si tenemos historial, usar start_chat con el historial completo menos el último mensaje
        # y luego enviar el último mensaje
        if len(history_for_chat) > 1:
            # Crear el chat con el historial (todos menos el último)
            chat = model.start_chat(history=history_for_chat[:-1])
            # Enviar el último mensaje
            last_message = history_for_chat[-1]["parts"][0]["text"]
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: chat.send_message(last_message, generation_config=generation_config)
            )
        else:
            # Solo hay un mensaje, generar directamente
            single_message = history_for_chat[0]["parts"][0]["text"]
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: model.generate_content(single_message, generation_config=generation_config)
            )
        
        ai_response = response.text.strip()
        print(f"📥 [IA] Respuesta recibida: {ai_response[:50]}...")
        return ai_response
    
    async def _interpret_note_intent(self, message: str, session_id: str) -> Optional[Dict]:
        """Usar IA para interpretar la intención de comandos de notas de forma más fluida"""
        if not self.use_ai or not (self.groq_api_key or self.anthropic_api_key or self.openai_api_key or self.gemini_api_key):
            return None
        
        try:
            import aiohttp
            import json
            
            # Crear un prompt específico para interpretar intenciones de notas
            system_prompt = """Eres un asistente que analiza mensajes sobre notas y extrae la acción.
Responde SOLO con JSON válido, sin texto adicional.

Estructura:
{
    "action": "create|read|append|overwrite|delete|list|null",
    "title": "nombre de la nota si aplica",
    "content": "contenido si aplica"
}"""

            user_prompt = f"""Analiza este mensaje sobre notas:

"{message}"

Ejemplos:
- "crea una nota supermercado y agrega comprar pan" -> {{"action": "create", "title": "supermercado", "content": "comprar pan"}}
- "agrega champú a la nota supermercado" -> {{"action": "append", "title": "supermercado", "content": "champú"}}
- "qué notas tengo" -> {{"action": "list"}}
- "dime la nota supermercado" -> {{"action": "read", "title": "supermercado"}}

Si no es un comando de notas, retorna {{"action": null}}."""

            # Llamar directamente a la API sin pasar por el sistema de historial
            if self.ai_provider == "gemini" and self.gemini_api_key:
                try:
                    import google.generativeai as genai
                    import asyncio
                    
                    # Configurar la API key
                    genai.configure(api_key=self.gemini_api_key)
                    
                    # Obtener el modelo
                    model_name = getattr(self, 'ai_model', "gemini-pro")
                    try:
                        model = genai.GenerativeModel(model_name)
                    except Exception as e:
                        print(f"[WARN] Modelo {model_name} no disponible, usando gemini-pro: {e}")
                        model = genai.GenerativeModel("gemini-pro")
                    
                    # Generar respuesta
                    full_prompt = f"{system_prompt}\n\n{user_prompt}"
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda: model.generate_content(
                            full_prompt,
                            generation_config={
                                "temperature": 0.1,
                                "max_output_tokens": 150,
                            }
                        )
                    )
                    
                    ai_response = response.text.strip()
                except Exception as e:
                    print(f"[WARN] Error usando SDK de Gemini: {e}")
                    return None
            elif self.ai_provider == "anthropic" and self.anthropic_api_key:
                url = "https://api.anthropic.com/v1/messages"
                headers = {
                    "x-api-key": self.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": self.ai_model,
                    "max_tokens": 150,
                    "temperature": 0.1,  # Baja temperatura para respuestas más deterministas
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}]
                }
            elif self.ai_provider == "openai" and self.openai_api_key:
                url = "https://api.openai.com/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "model": self.ai_model,
                    "temperature": 0.1,
                    "max_tokens": 150
                }
            else:
                # Groq
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "model": self.ai_model,
                    "temperature": 0.1,
                    "max_tokens": 150
                }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        return None
                    
                    data = await response.json()
                    
                    # Extraer respuesta según el provider
                    if self.ai_provider == "gemini":
                        # Gemini devuelve: data["candidates"][0]["content"]["parts"][0]["text"]
                        if "candidates" in data and len(data["candidates"]) > 0:
                            candidate = data["candidates"][0]
                            if "content" in candidate and "parts" in candidate["content"]:
                                parts = candidate["content"]["parts"]
                                if parts and len(parts) > 0 and "text" in parts[0]:
                                    ai_response = parts[0]["text"].strip()
                                else:
                                    return None
                            else:
                                return None
                        else:
                            return None
                    elif self.ai_provider == "anthropic":
                        ai_response = data["content"][0]["text"].strip()
                    else:
                        ai_response = data["choices"][0]["message"]["content"].strip()
                    
                    # Parsear JSON
                    ai_response = ai_response.strip()
                    # Limpiar si tiene markdown
                    if ai_response.startswith("```"):
                        parts = ai_response.split("```")
                        if len(parts) >= 2:
                            ai_response = parts[1]
                            if ai_response.startswith("json"):
                                ai_response = ai_response[4:]
                            ai_response = ai_response.strip()
                    
                    intent = json.loads(ai_response)
                    return intent if intent.get("action") and intent.get("action") != "null" else None
            
        except json.JSONDecodeError as e:
            print(f"[WARN] Error parseando JSON de intención: {e}")
            return None
        except Exception as e:
            print(f"[WARN] Error interpretando intención con IA: {e}")
            return None

