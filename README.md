# 🤖 Ecko - Asistente Virtual Personal

Asistente virtual tipo "Jarvis" desarrollado con Python (FastAPI), diseñado para funcionar 24/7 en AWS. Este proyecto es una plataforma de aprendizaje para Docker, AWS ECS Fargate, Terraform y CI/CD.

## 📋 Características

- **Chat conversacional inteligente**: Con soporte para IA real usando Groq API (gratuita)
- **Comandos básicos**: 
  - `hora` - Mostrar hora actual
  - `fecha` - Mostrar fecha actual
  - `recordar [texto]` - Guardar notas
  - `ayuda` - Mostrar comandos disponibles
- **Sesiones persistentes**: Mantiene el contexto de conversación
- **Interfaz móvil**: Funciona perfectamente desde tu celular
- **IA opcional**: Puede usar respuestas básicas o IA real (configurable)

## 🚀 Inicio Rápido (Desarrollo Local)

### Prerrequisitos

- Python 3.9 o superior
- pip (gestor de paquetes de Python)

### Instalación

1. **Clonar o navegar al proyecto**:
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
│   │   └── requirements.txt
│   └── frontend/            # Interfaz web
│       ├── index.html
│       ├── styles.css
│       └── app.js
├── README.md
└── .gitignore
```

## 🔌 API Endpoints

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

### DELETE `/api/history/{session_id}`
Limpiar historial de una sesión

## 🛠️ Tecnologías

- **Backend**: Python 3.9+, FastAPI
- **Frontend**: HTML5, CSS3, JavaScript (vanilla)
- **Containers**: Docker ✅
- **Infraestructura**: AWS ECS Fargate ✅
- **IaC**: Terraform ✅
- **CI/CD**: GitHub Actions (próximamente)

## 🎯 Objetivos de Aprendizaje

Este proyecto está diseñado para aprender:

1. ✅ Desarrollo de APIs con FastAPI
2. ✅ Docker y containerización
3. ✅ Infraestructura en AWS (ECS Fargate)
4. ✅ Terraform (Infraestructura como Código)
5. 🔄 CI/CD con GitHub Actions

## 🐳 Docker

Ecko está containerizado y listo para desplegar. Ver [docs/DOCKER.md](docs/DOCKER.md) para más detalles.

### Inicio Rápido con Docker

```bash
# Construir y ejecutar
docker-compose up --build

# Acceder en http://localhost:8000
```

## ☁️ AWS Deployment con Terraform

Ecko está listo para desplegarse en AWS usando Terraform. Ver [docs/TERRAFORM.md](docs/TERRAFORM.md) para la guía completa.

### Inicio Rápido con Terraform

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

Después, pushea tu imagen Docker a ECR y despliega.

## 🤖 Configuración de IA (Opcional pero Recomendado)

Para que Ecko tenga conversaciones más inteligentes usando IA real (GRATIS):

1. Obtén una API key gratuita en [Groq Console](https://console.groq.com/)
2. Crea un archivo `.env` en `app/backend/`:
```env
USE_AI=true
GROQ_API_KEY=tu_api_key_aqui
```
3. Instala dependencias: `pip install -r requirements.txt`
4. Reinicia el servidor

**Ver guía completa en**: [docs/IA_SETUP.md](docs/IA_SETUP.md)

## 📝 Notas

- El asistente puede usar respuestas básicas o IA real (configurable)
- El sistema de memoria es en memoria (no persistente por ahora)
- Se migrará a base de datos para persistencia en futuras versiones

## 🤝 Contribuir

Este es un proyecto personal de aprendizaje, pero las sugerencias son bienvenidas.

## 📄 Licencia

Proyecto personal - Uso educativo

---

**Versión**: 0.1.0 (Fase 1 - Asistente Básico Local)

