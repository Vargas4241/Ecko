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
# El ReminderService se inicializa en main.py y se pasa aquí
memory_service = MemoryService()
reminder_service = None  # Se inicializará en startup event de main.py
chat_service = ChatService()  # Inicialización básica, se actualizará en startup

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
        
        # Registrar callback de notificaciones si hay reminder_service
        if reminder_service and session_id:
            # Esto permite que las notificaciones lleguen al frontend
            # Por ahora solo registramos, las notificaciones se manejan vía polling
            pass
        
        # Guardar mensaje del usuario PRIMERO para tener historial completo
        memory_service.add_message(session_id, "user", message.message)
        
        # Obtener historial de la sesión (ahora incluye el mensaje recién guardado)
        history = memory_service.get_session_history(session_id)
        
        # Usar chat_service global o crear uno nuevo si no existe
        service = chat_service if chat_service else ChatService(reminder_service=reminder_service)
        
        # Procesar mensaje y generar respuesta
        response = await service.process_message(
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
    # Obtener user-agent del request si está disponible
    from fastapi import Request
    user_agent = None
    try:
        request = Request
        # Nota: En FastAPI, necesitamos obtener el request del contexto
        # Por ahora, crear sesión sin user_agent
    except:
        pass
    
    session_id = memory_service.create_session(user_agent=user_agent)
    return {"session_id": session_id, "message": "Nueva sesión creada"}

@router.get("/sessions/{session_id}/exists")
async def check_session_exists(session_id: str):
    """
    Verificar si una sesión existe (para validar sessionId guardado)
    """
    exists = memory_service.session_exists(session_id)
    return {"session_id": session_id, "exists": exists}

@router.get("/reminders/{session_id}")
async def get_reminders(session_id: str):
    """
    Obtener recordatorios activos de una sesión y notificaciones pendientes
    """
    if not reminder_service:
        raise HTTPException(status_code=503, detail="Servicio de recordatorios no disponible")
    
    reminders = reminder_service.get_reminders(session_id, active_only=True)
    notifications = reminder_service.get_pending_notifications(session_id, clear_after=True)
    
    return {
        "session_id": session_id, 
        "reminders": reminders, 
        "count": len(reminders),
        "notifications": notifications,
        "notifications_count": len(notifications)
    }

@router.delete("/reminders/{session_id}/{reminder_id}")
async def delete_reminder(session_id: str, reminder_id: str):
    """
    Eliminar un recordatorio
    """
    if not reminder_service:
        raise HTTPException(status_code=503, detail="Servicio de recordatorios no disponible")
    
    success = reminder_service.delete_reminder(session_id, reminder_id)
    if success:
        return {"message": "Recordatorio eliminado", "reminder_id": reminder_id}
    else:
        raise HTTPException(status_code=404, detail="Recordatorio no encontrado")

