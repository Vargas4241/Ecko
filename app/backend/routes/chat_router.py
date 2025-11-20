"""
Router para endpoints de chat
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from services.chat_service import ChatService
from services.memory_service import MemoryService

router = APIRouter()

# Instancias de servicios (singleton para desarrollo simple)
chat_service = ChatService()
memory_service = MemoryService()

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str

class SessionHistory(BaseModel):
    session_id: str
    messages: List[dict]

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(message: ChatMessage):
    """
    Endpoint principal para conversar con el asistente
    """
    try:
        # Obtener o crear sesión
        session_id = message.session_id
        if not session_id:
            session_id = memory_service.create_session()
        
        # Guardar mensaje del usuario PRIMERO para tener historial completo
        memory_service.add_message(session_id, "user", message.message)
        
        # Obtener historial de la sesión (ahora incluye el mensaje recién guardado)
        history = memory_service.get_session_history(session_id)
        
        # Procesar mensaje y generar respuesta
        response = await chat_service.process_message(
            user_message=message.message,
            session_id=session_id,
            history=history
        )
        
        # Guardar respuesta del asistente
        memory_service.add_message(session_id, "assistant", response)
        
        return ChatResponse(
            response=response,
            session_id=session_id,
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando mensaje: {str(e)}")

@router.get("/history/{session_id}", response_model=SessionHistory)
async def get_history(session_id: str):
    """
    Obtener historial de conversación de una sesión
    """
    try:
        history = memory_service.get_session_history(session_id)
        if not history:
            raise HTTPException(status_code=404, detail="Sesión no encontrada")
        
        return SessionHistory(
            session_id=session_id,
            messages=history
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo historial: {str(e)}")

@router.delete("/history/{session_id}")
async def clear_history(session_id: str):
    """
    Limpiar historial de una sesión
    """
    try:
        memory_service.clear_session(session_id)
        return {"message": "Historial limpiado", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error limpiando historial: {str(e)}")

@router.post("/sessions")
async def create_session():
    """
    Crear una nueva sesión de conversación
    """
    session_id = memory_service.create_session()
    return {"session_id": session_id, "message": "Nueva sesión creada"}

