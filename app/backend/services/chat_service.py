"""
Servicio de procesamiento de mensajes y generación de respuestas
"""

import re
import os
from datetime import datetime
from typing import List, Dict, Optional

# Importar configuración
try:
    from config import USE_AI, GROQ_API_KEY, ENABLE_SEARCH
except ImportError:
    # Fallback si config.py no existe
    USE_AI = os.getenv("USE_AI", "false").lower() == "true"
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    ENABLE_SEARCH = os.getenv("ENABLE_SEARCH", "true").lower() == "true"

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

class ChatService:
    """
    Servicio principal para procesar mensajes y generar respuestas
    Ahora soporta IA usando Groq API (gratuita)
    """
    
    def __init__(self, reminder_service=None, user_profile_service=None):
        self.commands = {
            "hora": self._get_time,
            "fecha": self._get_date,
            "ayuda": self._get_help,
            "recordatorios": self._list_reminders,
            "mis recordatorios": self._list_reminders,
        }
        # Configurar API de IA (Groq - gratis)
        self.use_ai = USE_AI
        self.groq_api_key = GROQ_API_KEY
        self.ai_model = "llama-3.1-8b-instant"  # Modelo rápido y gratis de Groq
        
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
        
        # Log de configuración (solo al iniciar)
        if self.use_ai and self.groq_api_key:
            print("[OK] IA activada - Usando Groq API")
        else:
            print("[INFO] Modo basico - IA desactivada o API key no configurada")
    
    async def process_message(self, user_message: str, session_id: str, history: List[Dict]) -> str:
        """
        Procesa el mensaje del usuario y genera una respuesta
        """
        message_lower = user_message.lower().strip()
        
        # Extraer información del usuario si está disponible (para perfil personal)
        if self.user_profile_service:
            user_info = self.user_profile_service.extract_user_info(session_id, user_message)
            if user_info.get("name"):
                self.user_profile_service.update_name(session_id, user_info["name"])
            if user_info.get("birthday"):
                self.user_profile_service.update_birthday(session_id, user_info["birthday"])
        
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
            "recuérdame", "recordarme", "recordar", "recuerda", 
            "recuerdame", "recuardame", "quiero que me recuerdes",
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
        has_time_reference = bool(re.search(r'\d{1,2}:\d{2}|a las \d+|en \d+ (minutos?|horas?)', message_lower))
        
        # Si tiene palabra clave de recordatorio O menciona tiempo específico con "recordatorio"
        if has_reminder_keyword or (has_time_reference and "recordatorio" in message_lower):
            # Verificar que NO sea solo una pregunta sobre recordatorios
            list_reminder_patterns = ["tengo recordatorios", "mis recordatorios", "qué recordatorios tengo"]
            is_listing = any(pattern in message_lower for pattern in list_reminder_patterns)
            if not is_listing:
                print(f"[DEBUG] Detectado comando de recordatorio: '{user_message}'")
                return await self._handle_remember(user_message, session_id)
        
        # PRIORIDAD 3: Eliminar recordatorios
        if message_lower.startswith("eliminar recordatorio") or message_lower.startswith("borrar recordatorio"):
            return await self._handle_delete_reminder(user_message, session_id)
        
        # PRIORIDAD 4: Verificar comandos de búsqueda
        search_commands = ["buscar", "busca", "qué es", "que es", "quien es", "quién es", "noticias"]
        if self.search_service and any(message_lower.startswith(cmd) for cmd in search_commands):
            return await self._handle_search(user_message, message_lower)
        
        # PRIORIDAD 5: Si la IA está habilitada y hay API key, usar IA (ÚLTIMO)
        # Solo usar respuestas básicas si la IA falla o está desactivada
        if self.use_ai and self.groq_api_key:
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
            r'(?:un\s+)?recordatorio\s+(?:ahora\s+)?(?:a las\s+)?(?:\d{1,2}:\d{2}\s+)?(?:que diga|que|de)\s+(.+)',  # "un recordatorio a las 15:10 que diga..."
            r'(?:un\s+)?recordatorio\s+(?:hoy|mañana|ahora)\s+(?:a las\s+)?(?:\d{1,2}:\d{2}\s+)?(?:que diga|que|de)\s+(.+)',  # "un recordatorio hoy a las 15:10 que diga..."
            r'm[áa]ndame\s+(?:un\s+)?(?:mensaje|recordatorio|notificaci[oó]n)\s+(?:a las\s+)?(?:\d{1,2}:\d{2}\s+)?(?:que diga|que|de)\s+(.+)',  # "mándame un recordatorio a las 15:10 que diga..."
            r'(?:no\s+)?(?:solo\s+)?m[áa]ndame\s+(?:a las\s+)?(?:\d{1,2}:\d{2}\s+)?(?:un\s+)?(?:mensaje|recordatorio|notificaci[oó]n)\s+(?:que diga|que|de)\s+(.+)',  # "no solo mándame a las 15:10 un recordatorio que diga..."
            r'rec(?:u|o)rd(?:a|e)(?:r|me|rme)?\s+(?:ahora\s+)?(?:en\s+\d+\s+(?:minutos?|horas?)\s+)?(?:que\s+)?(.+)',  # "recordame ahora en 2 minutos que..."
            r'(?:quiero\s+)?(?:que\s+)?me\s+recuerdes?\s+(?:que\s+)?(.+)',  # "quiero que me recuerdes que ..."
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
        
        # Verificar saludos (debe ser al inicio del mensaje o como palabra completa)
        for greeting in greetings:
            if message_lower == greeting or message_lower.startswith(greeting + " ") or message_lower.endswith(" " + greeting):
                if len(history) > 0:
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
        Genera una respuesta usando Groq API (IA gratuita) - usando requests directamente
        Puede incluir resultados de búsqueda web para información actualizada
        """
        try:
            import aiohttp
            import json
            
            print(f"🔗 [IA] Conectando a Groq API...")
            
            # Personalizar system prompt con información del usuario (estilo Jarvis)
            user_name = None
            user_title = "Señor"
            if self.user_profile_service:
                profile = self.user_profile_service.get_or_create_profile(session_id)
                user_name = profile.get("name")
                user_title = profile.get("preferred_title") or user_name or "Señor"
            
            system_prompt = f"""Eres Ecko, un asistente virtual personal estilo Jarvis de Iron Man. 
Responde en español de manera conversacional, natural y profesional pero amigable.
Trata al usuario como "{user_title}" o usa su nombre si lo conoces. 
Sé preciso, útil y proactivo como Jarvis.

REGLAS IMPORTANTES:
- NUNCA inventes información que no tengas. Si no sabes algo o no tienes datos, dilo claramente.
- Si te preguntan por tareas, calendario, eventos o recordatorios, SOLO menciona los que realmente existan.
- Si no hay recordatorios/tareas, di claramente "No tienes recordatorios/tareas pendientes" en lugar de inventar.
- NO inventes eventos, reuniones, vuelos o citas que no existan.
- Mantén las respuestas cortas y relevantes (máximo 2-3 frases).
- Cuando el usuario te diga su nombre o información personal, guárdala para futuras conversaciones.
- Si se te proporciona información de búsqueda web, úsala para responder con datos actualizados y precisos.
- Actúa como un verdadero asistente personal: recuerda información del usuario, sus preferencias y contexto."""
            
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
            print(f"[ERROR] [IA] Error en API: {type(e).__name__}: {error_msg}")
            raise Exception(f"Error comunicándose con la API de IA: {error_msg}")

