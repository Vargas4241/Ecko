"""
Script de inicio rápido para Ecko
Ejecutar desde la raíz del proyecto: python start.py
"""

import sys
import os
from pathlib import Path

# Añadir el directorio backend al path
backend_path = Path(__file__).parent / "app" / "backend"
sys.path.insert(0, str(backend_path))
os.chdir(backend_path)

if __name__ == "__main__":
    try:
        import uvicorn
        from main import app
        
        import sys
        import io
        # Configurar encoding UTF-8 para Windows
        if sys.platform == 'win32':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        
        print("=" * 50)
        print("Iniciando Ecko - Asistente Virtual")
        print("=" * 50)
        print("\nServidor iniciandose en http://localhost:8000")
        print("Documentacion API: http://localhost:8000/docs")
        print("Interfaz web: http://localhost:8000")
        print("\nPresiona Ctrl+C para detener el servidor\n")
        
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    except ImportError as e:
        print("ERROR: No se encontraron las dependencias necesarias.")
        print("\nPor favor instala las dependencias:")
        print("   cd app/backend")
        print("   pip install -r requirements.txt")
        print(f"\nDetalle del error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR al iniciar el servidor: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

