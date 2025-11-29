"""
Servicio de Push Notifications
Envía notificaciones push a dispositivos usando Web Push API
Permite que Ecko te notifique aunque la web esté cerrada
"""

import json
import os
from typing import Dict, List, Optional
import base64

# Verificar disponibilidad de librerías opcionales
try:
    from pywebpush import webpush, WebPushException
    PYWEBPUSH_AVAILABLE = True
except ImportError:
    PYWEBPUSH_AVAILABLE = False
    print("[WARN] pywebpush no está instalado. El servicio de Push estará desactivado.")

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.backends import default_backend
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    print("[WARN] cryptography no está instalado. La generación de claves VAPID estará limitada.")

# Instancia global
_push_service_instance: Optional["PushService"] = None

def get_push_service() -> Optional["PushService"]:
    """Retorna la instancia singleton de PushService."""
    return _push_service_instance

class PushService:
    """
    Gestiona el envío de notificaciones push web
    Usa VAPID para autenticación con los servicios de push
    """
    
    def __init__(self):
        if not PYWEBPUSH_AVAILABLE:
            print("[WARN] pywebpush no disponible, PushService desactivado")
            self.vapid_private_key = None
            self.vapid_public_key_b64 = None
            self.vapid_email = "ecko@example.com"
            return
        
        # Configuración VAPID (claves públicas/privadas para autenticación)
        self.vapid_private_key = os.getenv("VAPID_PRIVATE_KEY")
        self.vapid_public_key = os.getenv("VAPID_PUBLIC_KEY")
        self.vapid_email = os.getenv("VAPID_EMAIL", "ecko@example.com")
        
        # Si hay clave pública de env, convertir a base64 si es necesario
        if self.vapid_public_key and len(self.vapid_public_key) < 100:
            # Probablemente viene en formato corto (base64), usar directamente
            self.vapid_public_key_b64 = self.vapid_public_key
        elif self.vapid_public_key:
            # Puede venir en formato PEM, necesitaríamos convertir
            self.vapid_public_key_b64 = self.vapid_public_key
        
        # Si no hay claves, generarlas automáticamente
        if not self.vapid_private_key or not self.vapid_public_key:
            print("[WARN] VAPID keys no configuradas, generando claves temporales...")
            try:
                from cryptography.hazmat.primitives import serialization
                from cryptography.hazmat.backends import default_backend
                self._generate_vapid_keys()
            except Exception as e:
                print(f"[ERROR] Error en generación de claves: {e}")
                self.vapid_private_key = None
                self.vapid_public_key_b64 = None
        
        # Configuración para webpush
        self.vapid_claims = {
            "sub": f"mailto:{self.vapid_email}"
        }
        
        if PYWEBPUSH_AVAILABLE and self.vapid_private_key:
            print(f"[OK] PushService inicializado - Sistema de notificaciones push activo")
            print(f"[INFO] VAPID Email: {self.vapid_email}")
        else:
            print("[WARN] PushService inicializado pero sin funcionalidad completa (falta pywebpush o claves VAPID)")
        
        # Guardar instancia global
        global _push_service_instance
        _push_service_instance = self
    
    def _generate_vapid_keys(self):
        """Generar claves VAPID automáticamente (para desarrollo)"""
        try:
            if not CRYPTOGRAPHY_AVAILABLE:
                print("[WARN] cryptography no disponible, no se pueden generar claves VAPID")
                self.vapid_private_key = None
                self.vapid_public_key_b64 = None
                return
            
            # Usar cryptography directamente (más confiable)
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend
            
            # Generar clave privada ECDSA P-256 (SECP256R1)
            private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
            
            # Convertir a PEM para pywebpush
            self.vapid_private_key = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode('utf-8')
            
            # Obtener clave pública y convertir a base64 URL-safe (formato VAPID)
            public_key = private_key.public_key()
            public_key_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.X962,
                format=serialization.PublicFormat.UncompressedPoint
            )
            # VAPID usa base64 URL-safe sin padding
            self.vapid_public_key_b64 = base64.urlsafe_b64encode(public_key_bytes).decode('utf-8').rstrip('=')
            
            print("[INFO] Claves VAPID generadas automáticamente con cryptography")
            print("[INFO] Para producción, genera claves con: python -m py_vapid --gen")
            
        except Exception as e:
            print(f"[ERROR] Error generando claves VAPID: {e}")
            import traceback
            traceback.print_exc()
            self.vapid_private_key = None
            self.vapid_public_key_b64 = None
    
    def get_vapid_public_key(self) -> Optional[str]:
        """Obtener clave pública VAPID en formato base64 (para el frontend)"""
        if hasattr(self, 'vapid_public_key_b64'):
            return self.vapid_public_key_b64
        elif self.vapid_public_key:
            # Si la clave viene de variable de entorno, convertirla
            import base64
            if isinstance(self.vapid_public_key, str):
                # Asumir que viene en formato PEM, necesitamos convertirla
                # Por ahora, si es string largo, asumir que es base64
                if len(self.vapid_public_key) > 100:
                    return self.vapid_public_key
            return self.vapid_public_key
        return None
    
    def send_notification(self, subscription: Dict, message: str, title: str = "Ecko", 
                         options: Optional[Dict] = None) -> bool:
        """
        Enviar notificación push a un dispositivo
        
        Args:
            subscription: Objeto de suscripción del cliente (del navegador)
            message: Mensaje a enviar
            title: Título de la notificación
            options: Opciones adicionales (icon, badge, etc.)
        
        Returns:
            True si se envió exitosamente, False en caso contrario
        """
        if not PYWEBPUSH_AVAILABLE:
            return False
        
        if not self.vapid_private_key:
            print("[WARN] VAPID keys no disponibles, no se puede enviar push")
            return False
        
        try:
            # Preparar payload de la notificación
            payload = {
                "title": title,
                "body": message,
                "icon": options.get("icon") if options else "/static/logo.svg",
                "badge": options.get("badge") if options else "/static/logo.svg",
                "tag": options.get("tag") if options else "ecko-notification",
                "requireInteraction": options.get("requireInteraction", False) if options else False,
                "data": options.get("data") if options else {}
            }
            
            # Enviar push notification
            webpush(
                subscription_info=subscription,
                data=json.dumps(payload),
                vapid_private_key=self.vapid_private_key,
                vapid_claims=self.vapid_claims
            )
            
            print(f"[OK] Notificación push enviada: {title} - {message[:50]}")
            return True
            
        except WebPushException as e:
            # Error común: suscripción expirada
            if e.response.status_code == 410:
                print(f"[WARN] Suscripción expirada, debe renovarse")
            else:
                print(f"[ERROR] Error enviando push: {e.response.status_code} - {e.response.reason}")
            return False
        except Exception as e:
            print(f"[ERROR] Error inesperado enviando push: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def send_notification_to_user(self, session_id: str, message: str, title: str = "Ecko",
                                  options: Optional[Dict] = None) -> bool:
        """
        Enviar notificación a un usuario específico (busca su suscripción)
        
        Args:
            session_id: ID de sesión del usuario
            message: Mensaje a enviar
            title: Título de la notificación
            options: Opciones adicionales
        
        Returns:
            True si se envió exitosamente
        """
        # Obtener suscripciones del usuario desde almacenamiento persistente
        try:
            from services.persistent_storage import get_storage
            storage = get_storage()
            
            # Obtener perfil del usuario (donde se guardan las suscripciones)
            profile = storage.get_user_profile(session_id)
            if not profile:
                return False
            
            # Las suscripciones se guardan en learned_info o preferences
            subscriptions = profile.get("learned_info", {}).get("push_subscriptions", [])
            
            if not subscriptions:
                print(f"[INFO] Usuario {session_id} no tiene suscripciones push registradas")
                return False
            
            # Enviar a todas las suscripciones del usuario (puede tener múltiples dispositivos)
            success_count = 0
            for subscription in subscriptions:
                if self.send_notification(subscription, message, title, options):
                    success_count += 1
            
            print(f"[OK] Notificación enviada a {success_count}/{len(subscriptions)} dispositivos de {session_id}")
            return success_count > 0
            
        except Exception as e:
            print(f"[ERROR] Error obteniendo suscripciones: {e}")
            return False

