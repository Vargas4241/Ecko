"""
Configuración de la aplicación
Carga variables de entorno de forma segura
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    try:
        load_dotenv(dotenv_path=env_path, encoding='utf-8')
    except Exception as e:
        print(f"Advertencia: No se pudo cargar .env: {e}")

# Configuración de IA
USE_AI = os.getenv("USE_AI", "false").lower() == "true"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

