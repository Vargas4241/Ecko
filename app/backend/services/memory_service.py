"""
Servicio de memoria y gestión de sesiones
Por ahora usa almacenamiento en memoria, después se migrará a base de datos
"""

import uuid
from datetime import datetime
from typing import List, Dict, Optional

class MemoryService:
    """
    Gestiona las sesiones de conversación y el historial
    """
    
    def __init__(self):
        # Almacenamiento en memoria (en producción usar DB)
        self.sessions: Dict[str, List[Dict]] = {}
    
    def create_session(self) -> str:
        """
        Crear una nueva sesión de conversación
        """
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = []
        return session_id
    
    def get_session_history(self, session_id: str) -> List[Dict]:
        """
        Obtener el historial de una sesión
        """
        return self.sessions.get(session_id, [])
    
    def add_message(self, session_id: str, role: str, content: str):
        """
        Agregar un mensaje al historial de una sesión
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        
        message = {
            "role": role,  # "user" o "assistant"
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        self.sessions[session_id].append(message)
    
    def clear_session(self, session_id: str):
        """
        Limpiar el historial de una sesión
        """
        if session_id in self.sessions:
            self.sessions[session_id] = []
    
    def delete_session(self, session_id: str):
        """
        Eliminar una sesión completamente
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def get_all_sessions(self) -> List[str]:
        """
        Obtener lista de todas las sesiones activas
        """
        return list(self.sessions.keys())

