"""
Servicio de perfil de usuario - Sistema estilo Jarvis
Almacena información personal del usuario: nombre, cumpleaños, preferencias, etc.
Ahora con persistencia en base de datos
"""

import uuid
from datetime import datetime
from typing import Dict, Optional
import re

# Importar almacenamiento persistente si está disponible
try:
    from services.persistent_storage import get_storage
    PERSISTENT_STORAGE_AVAILABLE = True
except ImportError:
    PERSISTENT_STORAGE_AVAILABLE = False
    print("[WARN] Almacenamiento persistente no disponible")

class UserProfileService:
    """
    Gestiona perfiles de usuario con información personal
    Permite personalizar las respuestas como un asistente personal tipo Jarvis
    Ahora con persistencia en SQLite
    """
    
    def __init__(self, use_persistence: bool = True):
        # Almacenamiento en memoria (fallback si no hay persistencia)
        self.profiles: Dict[str, Dict] = {}
        self.use_persistence = use_persistence and PERSISTENT_STORAGE_AVAILABLE
        
        if self.use_persistence:
            try:
                self.storage = get_storage()
                print("[OK] UserProfileService inicializado - Sistema de perfiles activo (con persistencia)")
            except Exception as e:
                print(f"[WARN] Error inicializando persistencia, usando memoria: {e}")
                self.use_persistence = False
        else:
            print("[OK] UserProfileService inicializado - Sistema de perfiles activo (solo memoria)")
    
    def get_or_create_profile(self, session_id: str) -> Dict:
        """Obtener o crear perfil de usuario (con persistencia)"""
        # Intentar cargar desde almacenamiento persistente
        if self.use_persistence:
            try:
                profile = self.storage.get_user_profile(session_id)
                if profile:
                    # Cachear en memoria para acceso rápido
                    self.profiles[session_id] = profile
                    return profile
            except Exception as e:
                print(f"[WARN] Error cargando perfil desde storage: {e}")
        
        # Si no existe, crear nuevo perfil
        if session_id not in self.profiles:
            new_profile = {
                "session_id": session_id,
                "name": None,  # Nombre del usuario (ej: "Franco")
                "preferred_title": None,  # Cómo prefiere ser llamado (ej: "Señor", "Franco")
                "birthday": None,  # Fecha de cumpleaños (YYYY-MM-DD)
                "created_at": datetime.now().isoformat(),
                "preferences": {
                    "formality": "formal",  # "formal", "informal", "friendly"
                    "use_name_in_responses": True,
                },
                "learned_info": {}  # Información aprendida durante conversaciones
            }
            self.profiles[session_id] = new_profile
            
            # Guardar en almacenamiento persistente
            if self.use_persistence:
                try:
                    self.storage.save_user_profile(session_id, new_profile)
                except Exception as e:
                    print(f"[WARN] Error guardando perfil en storage: {e}")
        
        return self.profiles[session_id]
    
    def update_name(self, session_id: str, name: str):
        """Actualizar nombre del usuario"""
        profile = self.get_or_create_profile(session_id)
        profile["name"] = name.strip()
        # Si no tiene título preferido, usar el nombre
        if not profile.get("preferred_title"):
            profile["preferred_title"] = name.strip()
        
        # Guardar en almacenamiento persistente
        if self.use_persistence:
            try:
                self.storage.save_user_profile(session_id, profile)
            except Exception as e:
                print(f"[WARN] Error guardando perfil: {e}")
        
        print(f"[PERFIL] Nombre actualizado para sesión {session_id}: {name}")
    
    def update_birthday(self, session_id: str, birthday_str: str):
        """Actualizar cumpleaños del usuario (formato: YYYY-MM-DD o texto natural)"""
        profile = self.get_or_create_profile(session_id)
        
        # Intentar parsear fecha
        try:
            from dateparser import parse
            parsed_date = parse(birthday_str, languages=['es', 'en'])
            if parsed_date:
                profile["birthday"] = parsed_date.strftime("%Y-%m-%d")
                
                # Guardar en almacenamiento persistente
                if self.use_persistence:
                    try:
                        self.storage.save_user_profile(session_id, profile)
                    except Exception as e:
                        print(f"[WARN] Error guardando perfil: {e}")
                
                print(f"[PERFIL] Cumpleaños actualizado para sesión {session_id}: {profile['birthday']}")
                return True
        except Exception as e:
            print(f"[WARN] Error parseando cumpleaños: {e}")
        
        return False
    
    def update_preferred_title(self, session_id: str, title: str):
        """Actualizar cómo prefiere ser llamado el usuario"""
        profile = self.get_or_create_profile(session_id)
        profile["preferred_title"] = title.strip()
        
        # Guardar en almacenamiento persistente
        if self.use_persistence:
            try:
                self.storage.save_user_profile(session_id, profile)
            except Exception as e:
                print(f"[WARN] Error guardando perfil: {e}")
        
        print(f"[PERFIL] Título preferido actualizado para sesión {session_id}: {title}")
    
    def get_user_greeting(self, session_id: str) -> str:
        """Obtener saludo personalizado para el usuario"""
        profile = self.get_or_create_profile(session_id)
        
        name_or_title = profile.get("preferred_title") or profile.get("name") or "Señor"
        
        # Verificar si es su cumpleaños
        if profile.get("birthday"):
            today = datetime.now().date()
            try:
                birthday = datetime.strptime(profile["birthday"], "%Y-%m-%d").date()
                if today.month == birthday.month and today.day == birthday.day:
                    return f"¡Feliz cumpleaños, {name_or_title}! 🎉"
            except:
                pass
        
        return name_or_title
    
    def personalize_response(self, session_id: str, response: str) -> str:
        """Personalizar una respuesta usando el perfil del usuario"""
        profile = self.get_or_create_profile(session_id)
        
        name_or_title = profile.get("preferred_title") or profile.get("name")
        
        # Si el usuario tiene nombre y las respuestas deben personalizarse
        if name_or_title and profile["preferences"].get("use_name_in_responses", True):
            # Reemplazar saludos genéricos con nombre personalizado
            response = re.sub(r'\b(Hola|Hola!)\b', f'Hola, {name_or_title}', response, count=1)
            response = re.sub(r'\b(Señor|Señora)\b', name_or_title, response)
        
        return response
    
    def extract_user_info(self, session_id: str, message: str) -> Dict[str, str]:
        """
        Extraer información del usuario desde mensajes conversacionales
        Retorna dict con información extraída: {"name": "...", "birthday": "..."}
        """
        info = {}
        message_lower = message.lower()
        
        # IMPORTANTE: No extraer "ecko" o "eco" como nombre del usuario
        # Estas son referencias al asistente, no al usuario
        wake_words = ['ecko', 'eco']
        if any(word in message_lower for word in wake_words):
            # Si el mensaje contiene el nombre del asistente, no extraer nombres
            # a menos que sea explícito ("me llamo..." después del saludo)
            pass
        
        # Detectar nombre
        name_patterns = [
            r'me llamo\s+(\w+)',
            r'mi nombre\s+es\s+(\w+)',
            r'soy\s+(\w+)',
            r'me llaman\s+(\w+)',
        ]
        for pattern in name_patterns:
            match = re.search(pattern, message_lower)
            if match:
                extracted_name = match.group(1).lower().strip()
                # NO extraer si es "ecko" o "eco" (nombre del asistente)
                if extracted_name not in wake_words:
                    info["name"] = match.group(1).capitalize()
                    break
        
        # Detectar cumpleaños
        birthday_patterns = [
            r'cumplo años\s+(?:el\s+)?(\d{1,2})[/-](\d{1,2})',
            r'mi cumpleaños\s+es\s+(?:el\s+)?(\d{1,2})[/-](\d{1,2})',
            r'nací\s+(?:el\s+)?(\d{1,2})[/-](\d{1,2})[/-](\d{4})',
        ]
        for pattern in birthday_patterns:
            match = re.search(pattern, message_lower)
            if match:
                if len(match.groups()) == 3:
                    info["birthday"] = f"{match.group(3)}-{match.group(2)}-{match.group(1)}"
                else:
                    # Solo mes y día, usar año actual o próximo
                    today = datetime.now()
                    month, day = int(match.group(1)), int(match.group(2))
                    if (today.month, today.day) > (month, day):
                        year = today.year + 1
                    else:
                        year = today.year
                    info["birthday"] = f"{year}-{month:02d}-{day:02d}"
                break
        
        return info

