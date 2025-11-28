"""
Router para endpoints de Push Notifications
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict

router = APIRouter()

# Instancia del servicio de push (se inicializa en main.py)
push_service = None

class PushSubscription(BaseModel):
    session_id: str
    subscription: Dict  # Objeto de suscripción del navegador

@router.get("/vapid-public-key")
async def get_vapid_public_key():
    """
    Obtener clave pública VAPID para suscribirse a push notifications
    """
    if not push_service:
        raise HTTPException(status_code=503, detail="Servicio de push no disponible")
    
    public_key = push_service.get_vapid_public_key()
    if not public_key:
        raise HTTPException(status_code=500, detail="Clave pública VAPID no disponible")
    
    return {"publicKey": public_key}

@router.post("/subscribe")
async def subscribe_to_push(subscription_data: PushSubscription):
    """
    Registrar suscripción push de un usuario
    Guarda la suscripción para enviar notificaciones cuando sea necesario
    """
    if not push_service:
        raise HTTPException(status_code=503, detail="Servicio de push no disponible")
    
    try:
        # Guardar suscripción en el perfil del usuario
        from services.persistent_storage import get_storage
        storage = get_storage()
        
        # Obtener o crear perfil
        profile = storage.get_user_profile(subscription_data.session_id)
        if not profile:
            # Crear perfil básico
            profile = {
                "session_id": subscription_data.session_id,
                "learned_info": {}
            }
        
        # Guardar suscripciones en learned_info
        if "push_subscriptions" not in profile.get("learned_info", {}):
            profile["learned_info"]["push_subscriptions"] = []
        
        # Convertir subscription a dict si es necesario
        sub_dict = subscription_data.subscription
        if hasattr(sub_dict, 'keys'):
            sub_dict = dict(sub_dict)
        
        # Verificar si ya existe esta suscripción (por endpoint)
        existing_subs = profile["learned_info"]["push_subscriptions"]
        endpoint = sub_dict.get("endpoint")
        
        # Actualizar o agregar suscripción
        found = False
        for i, existing_sub in enumerate(existing_subs):
            if existing_sub.get("endpoint") == endpoint:
                existing_subs[i] = sub_dict
                found = True
                break
        
        if not found:
            existing_subs.append(sub_dict)
        
        profile["learned_info"]["push_subscriptions"] = existing_subs
        storage.save_user_profile(subscription_data.session_id, profile)
        
        return {
            "message": "Suscripción registrada exitosamente",
            "session_id": subscription_data.session_id,
            "subscriptions_count": len(existing_subs)
        }
    except Exception as e:
        print(f"[ERROR] Error registrando suscripción: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error registrando suscripción: {str(e)}")

@router.delete("/unsubscribe/{session_id}")
async def unsubscribe_from_push(session_id: str):
    """
    Eliminar todas las suscripciones push de un usuario
    """
    try:
        from services.persistent_storage import get_storage
        storage = get_storage()
        
        profile = storage.get_user_profile(session_id)
        if profile:
            profile["learned_info"]["push_subscriptions"] = []
            storage.save_user_profile(session_id, profile)
        
        return {"message": "Suscripciones eliminadas", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error eliminando suscripciones: {str(e)}")

