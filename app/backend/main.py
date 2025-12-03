"""
Ecko - Asistente Virtual
Backend principal con FastAPI
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import sys
from pathlib import Path

# Añadir el directorio actual al path para importaciones
sys.path.insert(0, str(Path(__file__).parent))

from routes import chat_router
from routes import push_router

# Importar servicios
try:
    from services.reminder_service import ReminderService
    REMINDER_SERVICE_AVAILABLE = True
except ImportError:
    REMINDER_SERVICE_AVAILABLE = False
    print("[WARN] ReminderService no disponible (dependencias faltantes)")

try:
    from services.user_profile_service import UserProfileService
    USER_PROFILE_SERVICE_AVAILABLE = True
except ImportError:
    USER_PROFILE_SERVICE_AVAILABLE = False
    print("[WARN] UserProfileService no disponible")

try:
    from services.notes_service import NotesService
    NOTES_SERVICE_AVAILABLE = True
except ImportError:
    NOTES_SERVICE_AVAILABLE = False
    print("[WARN] NotesService no disponible")

try:
    from services.onboarding_service import OnboardingService
    ONBOARDING_SERVICE_AVAILABLE = True
except ImportError:
    ONBOARDING_SERVICE_AVAILABLE = False
    print("[WARN] OnboardingService no disponible")

try:
    from services.push_service import PushService
    PUSH_SERVICE_AVAILABLE = True
except ImportError:
    PUSH_SERVICE_AVAILABLE = False
    print("[WARN] PushService no disponible")

try:
    from services.summary_service import SummaryService
    SUMMARY_SERVICE_AVAILABLE = True
except ImportError:
    SUMMARY_SERVICE_AVAILABLE = False
    print("[WARN] SummaryService no disponible")

# Crear aplicación FastAPI
app = FastAPI(
    title="Ecko - Asistente Virtual",
    description="Asistente virtual tipo Jarvis - Backend API",
    version="0.1.0"
)

# Instancias globales de servicios
reminder_service = None
user_profile_service = None
push_service = None
notes_service = None
onboarding_service = None
summary_service = None

@app.on_event("startup")
async def startup_event():
    """Inicializar servicios al iniciar la aplicación"""
    global reminder_service, user_profile_service, push_service, notes_service, onboarding_service, summary_service
    
    # Inicializar servicio de push notifications
    if PUSH_SERVICE_AVAILABLE:
        try:
            push_service = PushService()
            push_router.push_service = push_service
            # Guardar referencia global para acceso desde otros servicios
            import services.push_service as push_module
            push_module._push_service_instance = push_service
            print("[OK] PushService inicializado")
        except Exception as e:
            print(f"[WARN] Error inicializando PushService: {e}")
            import traceback
            traceback.print_exc()
            push_service = None
    
    # Inicializar servicio de perfil de usuario (Jarvis-like)
    if USER_PROFILE_SERVICE_AVAILABLE:
        try:
            user_profile_service = UserProfileService()
        except Exception as e:
            print(f"[WARN] Error inicializando UserProfileService: {e}")
            user_profile_service = None
    
    # Inicializar servicio de notas
    if NOTES_SERVICE_AVAILABLE:
        try:
            notes_service = NotesService()
            print("[OK] NotesService inicializado")
        except Exception as e:
            print(f"[WARN] Error inicializando NotesService: {e}")
            notes_service = None
    
    # Inicializar servicio de resúmenes
    if SUMMARY_SERVICE_AVAILABLE:
        try:
            from services.memory_service import MemoryService
            memory_service = MemoryService()
            summary_service = SummaryService(memory_service=memory_service)
            chat_router.summary_service = summary_service
            print("[OK] SummaryService inicializado")
        except Exception as e:
            print(f"[WARN] Error inicializando SummaryService: {e}")
            summary_service = None
    
    # Inicializar servicio de recordatorios
    if REMINDER_SERVICE_AVAILABLE:
        try:
            reminder_service = ReminderService()
            # Pasar el servicio de recordatorios al router
            chat_router.reminder_service = reminder_service
            # Actualizar chat_service con todos los servicios
            from services.chat_service import ChatService
            chat_router.chat_service = ChatService(
                reminder_service=reminder_service,
                user_profile_service=user_profile_service,
                notes_service=notes_service,
                onboarding_service=onboarding_service,
                summary_service=summary_service
            )
            print("[OK] Servicios inicializados correctamente")
        except Exception as e:
            print(f"[WARN] Error inicializando servicios: {e}")
            import traceback
            traceback.print_exc()
            # Continuar sin recordatorios si hay error
            from services.chat_service import ChatService
            chat_router.chat_service = ChatService(
                user_profile_service=user_profile_service,
                notes_service=notes_service,
                onboarding_service=onboarding_service,
                summary_service=summary_service
            )
    else:
        # Inicializar solo ChatService con perfil de usuario y notas
        from services.chat_service import ChatService
        chat_router.chat_service = ChatService(
            user_profile_service=user_profile_service,
            notes_service=notes_service,
            summary_service=summary_service
        )

@app.on_event("shutdown")
async def shutdown_event():
    """Limpiar recursos al cerrar la aplicación"""
    global reminder_service
    if reminder_service:
        try:
            reminder_service.shutdown()
        except:
            pass

# Configurar CORS para permitir requests desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En desarrollo, en producción restringir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(chat_router.router, prefix="/api", tags=["chat"])
app.include_router(push_router.router, prefix="/api/push", tags=["push"])

# Servir archivos estáticos del frontend (para desarrollo)
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
    
    # Servir Service Worker con el tipo MIME correcto (importante para PWA)
    @app.get("/static/sw.js")
    async def service_worker():
        """Servir Service Worker con tipo MIME correcto"""
        sw_path = os.path.join(frontend_path, "sw.js")
        if os.path.exists(sw_path):
            from fastapi.responses import Response
            with open(sw_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return Response(content=content, media_type="application/javascript")
        raise HTTPException(status_code=404, detail="Service Worker no encontrado")

@app.get("/")
async def root():
    """Redirigir a la interfaz web"""
    frontend_index = os.path.join(frontend_path, "index.html")
    if os.path.exists(frontend_index):
        return FileResponse(frontend_index)
    return {"message": "Ecko API está funcionando. Usa /api/chat para interactuar."}

@app.get("/health")
async def health_check():
    """Endpoint de salud para monitoreo"""
    return {"status": "healthy", "service": "ecko"}

if __name__ == "__main__":
    import uvicorn
    # Obtener puerto de variable de entorno o usar 8000 por defecto
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

