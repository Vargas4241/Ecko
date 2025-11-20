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

# Crear aplicación FastAPI
app = FastAPI(
    title="Ecko - Asistente Virtual",
    description="Asistente virtual tipo Jarvis - Backend API",
    version="0.1.0"
)

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

# Servir archivos estáticos del frontend (para desarrollo)
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

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

