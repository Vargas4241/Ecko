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
        # Usar override=True para asegurar que las variables del .env sobrescriban las del sistema
        load_dotenv(dotenv_path=env_path, encoding='utf-8', override=True)
        print(f"[OK] Archivo .env cargado desde: {env_path}")
    except Exception as e:
        print(f"[WARN] No se pudo cargar .env: {e}")

# Configuración de IA
USE_AI = os.getenv("USE_AI", "false").lower() == "true"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
# Opciones de IA más potentes (opcionales)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")  # Para GPT-4
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")  # Para Claude
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")  # Para Google Gemini (recomendado)
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai").lower()  # "groq", "openai", "anthropic", "gemini" (openai recomendado)

# Configuración de Búsqueda Web
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY", "")  # API key de Tavily (opcional)
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "duckduckgo")  # "tavily" o "duckduckgo"
ENABLE_SEARCH = os.getenv("ENABLE_SEARCH", "true").lower() == "true"  # Habilitar búsqueda

