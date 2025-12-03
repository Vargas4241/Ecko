# 🤖 Ecko - Asistente Virtual Personal

Asistente virtual tipo "Jarvis" desarrollado con Python (FastAPI) y JavaScript vanilla.

## 📋 Características

- **Chat conversacional inteligente**: Con soporte para IA usando OpenAI GPT-4o-mini
- **Comandos básicos**: 
  - `hora` - Mostrar hora actual
  - `fecha` - Mostrar fecha actual
  - `recordar [texto]` - Guardar notas
  - `resumen de hoy` - Generar resumen de la conversación del día
  - `ayuda` - Mostrar comandos disponibles
- **Sesiones persistentes**: Mantiene el contexto de conversación
- **Interfaz móvil**: Funciona perfectamente desde tu celular
- **Reconocimiento de voz**: Actívale con "Hey Ecko" o "Eco"
- **Síntesis de voz**: Ecko te responde hablando

## 🚀 Inicio Rápido

### Prerrequisitos

- Python 3.9 o superior
- pip (gestor de paquetes de Python)

### Instalación

1. **Navegar al proyecto**:
```bash
cd Ecko
```

2. **Crear entorno virtual** (recomendado):
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Instalar dependencias**:
```bash
cd app/backend
pip install -r requirements.txt
```

4. **Ejecutar la aplicación**:

Desde la raíz del proyecto:
```bash
python start.py
```

O desde el directorio backend:
```bash
cd app/backend
python main.py
```

5. **Abrir en el navegador**:
   - Abre tu navegador en `http://localhost:8000`
   - También puedes acceder a la API directamente en `http://localhost:8000/docs` para ver la documentación Swagger

## 📁 Estructura del Proyecto

```
Ecko/
├── app/
│   ├── backend/              # API FastAPI
│   │   ├── main.py          # Punto de entrada
│   │   ├── routes/          # Routers de la API
│   │   ├── services/        # Lógica de negocio
│   │   ├── models/          # Modelos de datos
│   │   ├── data/            # Base de datos SQLite
│   │   └── requirements.txt
│   └── frontend/            # Interfaz web
│       ├── index.html
│       ├── styles.css
│       ├── styles-jarvis.css
│       └── app.js
├── start.py                 # Script de inicio rápido
└── README.md
```

## 🔌 API Endpoints Principales

### POST `/api/chat`
Enviar un mensaje al asistente

**Request:**
```json
{
  "message": "Hola Ecko",
  "session_id": "uuid-opcional"
}
```

**Response:**
```json
{
  "response": "¡Hola! Soy Ecko...",
  "session_id": "uuid-de-sesion",
  "timestamp": "2024-01-01T12:00:00"
}
```

### POST `/api/sessions`
Crear una nueva sesión de conversación

### GET `/api/history/{session_id}`
Obtener historial de una sesión

### POST `/api/summaries/{session_id}`
Generar resumen de la conversación

## 🤖 Configuración de IA (Opcional pero Recomendado)

Para que Ecko tenga conversaciones más inteligentes usando OpenAI:

1. Obtén una API key en [OpenAI Platform](https://platform.openai.com/api-keys)
2. Crea un archivo `.env` en `app/backend/`:
```env
USE_AI=true
AI_PROVIDER=openai
OPENAI_API_KEY=tu_api_key_aqui
```

3. Reinicia el servidor

Sin configurar IA, Ecko usará respuestas básicas predefinidas.

## 🛠️ Tecnologías

- **Backend**: Python 3.9+, FastAPI
- **Frontend**: HTML5, CSS3, JavaScript (vanilla)
- **Base de datos**: SQLite
- **IA**: OpenAI GPT-4o-mini (opcional)

## 📝 Notas

- La aplicación guarda el historial de conversaciones en SQLite
- Los datos se persisten en `app/backend/data/ecko.db`
- Funciona completamente offline (sin IA) o con IA para respuestas más inteligentes

---

**Versión**: 1.0.0
