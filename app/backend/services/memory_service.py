"""
Servicio de memoria y gestión de sesiones
Ahora con persistencia en base de datos SQLite
"""

import uuid
from datetime import datetime
from typing import List, Dict, Optional

# Importar almacenamiento persistente si está disponible
try:
    from services.persistent_storage import get_storage
    PERSISTENT_STORAGE_AVAILABLE = True
except ImportError:
    PERSISTENT_STORAGE_AVAILABLE = False
    print("[WARN] Almacenamiento persistente no disponible para MemoryService")

class MemoryService:
    """
    Gestiona las sesiones de conversación y el historial
    Ahora con persistencia en SQLite
    """
    
    def __init__(self, use_persistence: bool = True):
        # Cache en memoria para acceso rápido
        self.sessions_cache: Dict[str, List[Dict]] = {}
        
        # Almacenamiento persistente
        self.use_persistence = use_persistence and PERSISTENT_STORAGE_AVAILABLE
        if self.use_persistence:
            try:
                self.storage = get_storage()
                print("[OK] MemoryService usando almacenamiento persistente")
            except Exception as e:
                print(f"[WARN] Error inicializando persistencia, usando solo memoria: {e}")
                self.use_persistence = False
        else:
            print("[OK] MemoryService usando solo almacenamiento en memoria")
    
    def create_session(self, user_agent: str = None) -> str:
        """
        Crear una nueva sesión de conversación
        """
        if self.use_persistence:
            try:
                session_id = self.storage.create_session(None, user_agent)
                # Inicializar cache vacío
                self.sessions_cache[session_id] = []
                return session_id
            except Exception as e:
                print(f"[WARN] Error creando sesión en storage: {e}")
        
        # Fallback a memoria
        session_id = str(uuid.uuid4())
        self.sessions_cache[session_id] = []
        return session_id
    
    def get_session_history(self, session_id: str) -> List[Dict]:
        """
        Obtener el historial de una sesión (desde persistencia si está disponible)
        """
        # Si hay persistencia, cargar desde ahí
        if self.use_persistence:
            try:
                history = self.storage.get_conversation_history(session_id)
                # Actualizar cache
                self.sessions_cache[session_id] = history
                return history
            except Exception as e:
                print(f"[WARN] Error cargando historial desde storage: {e}")
        
        # Fallback a memoria
        return self.sessions_cache.get(session_id, [])
    
    def add_message(self, session_id: str, role: str, content: str):
        """
        Agregar un mensaje al historial de una sesión
        """
        # Agregar a memoria (cache)
        if session_id not in self.sessions_cache:
            self.sessions_cache[session_id] = []
        
        message = {
            "role": role,  # "user" o "assistant"
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        self.sessions_cache[session_id].append(message)
        
        # Guardar en almacenamiento persistente
        if self.use_persistence:
            try:
                self.storage.add_conversation_message(session_id, role, content)
            except Exception as e:
                print(f"[WARN] Error guardando mensaje en storage: {e}")
    
    def clear_session(self, session_id: str):
        """
        Limpiar el historial de una sesión
        """
        # Limpiar cache
        if session_id in self.sessions_cache:
            self.sessions_cache[session_id] = []
        
        # Limpiar en almacenamiento persistente
        if self.use_persistence:
            try:
                self.storage.clear_conversation(session_id)
            except Exception as e:
                print(f"[WARN] Error limpiando conversación en storage: {e}")
    
    def delete_session(self, session_id: str):
        """
        Eliminar una sesión completamente
        """
        # Eliminar de cache
        if session_id in self.sessions_cache:
            del self.sessions_cache[session_id]
        
        # Eliminar de almacenamiento persistente (si hay método para eso)
        # Por ahora solo limpiamos la conversación
    
    def get_all_sessions(self) -> List[str]:
        """
        Obtener lista de todas las sesiones activas
        """
        # Si hay persistencia, cargar desde BD
        # Por ahora retornar cache
        return list(self.sessions_cache.keys())
    
    def session_exists(self, session_id: str) -> bool:
        """Verificar si una sesión existe"""
        if self.use_persistence:
            try:
                return self.storage.session_exists(session_id)
            except Exception as e:
                print(f"[WARN] Error verificando sesión: {e}")
        
        # Fallback a memoria
        return session_id in self.sessions_cache

