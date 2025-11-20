# 🤖 Configuración de IA para Ecko

Ecko ahora puede usar IA real para conversaciones más inteligentes usando **Groq API**, que es completamente gratuita.

## 🚀 Configuración Rápida

### 1. Obtener API Key de Groq (Gratuita)

1. Ve a [https://console.groq.com/](https://console.groq.com/)
2. Crea una cuenta (es gratis, no requiere tarjeta de crédito)
3. Ve a "API Keys" y crea una nueva API key
4. Copia tu API key

### 2. Configurar en Ecko

1. En `app/backend/`, crea un archivo `.env`:

```bash
cd app/backend
copy .env.example .env  # Windows
# o
cp .env.example .env    # Linux/Mac
```

2. Edita el archivo `.env` y añade tu API key:

```env
USE_AI=true
GROQ_API_KEY=tu_api_key_aqui
```

### 3. Instalar dependencias

```bash
cd app/backend
pip install -r requirements.txt
```

### 4. Reiniciar el servidor

Reinicia tu servidor de Ecko y ya estará usando IA real.

## 📋 Opciones Disponibles

### Modo IA (Recomendado)

Con `USE_AI=true` y `GROQ_API_KEY` configurado:
- ✅ Conversaciones naturales e inteligentes
- ✅ Contexto de conversación mantenido
- ✅ Respuestas coherentes y útiles
- ✅ Gratis (límites generosos de Groq)

### Modo Básico (Sin IA)

Con `USE_AI=false` o sin `GROQ_API_KEY`:
- ✅ Respuestas predefinidas
- ✅ Comandos básicos funcionando
- ✅ No requiere API key
- ✅ Útil para desarrollo/testing

## 🎯 Modelos Disponibles

Por defecto usa `llama-3.1-8b-instant` (rápido y gratis). Puedes cambiar el modelo editando `app/backend/services/chat_service.py`:

```python
self.ai_model = "llama-3.1-8b-instant"  # Rápido, gratis
# Otros modelos disponibles:
# - "llama-3.1-70b-versatile"  # Más potente pero más lento
# - "mixtral-8x7b-32768"       # Buen balance
```

## 💡 Ventajas de Groq

- **Completamente gratis** para uso personal
- **Muy rápido** (inferencia en milisegundos)
- **No requiere instalación** local de modelos
- **Fácil de usar** - solo necesitas una API key
- **Límites generosos** - suficiente para desarrollo y uso personal

## 🔒 Seguridad

- **NUNCA** subas tu archivo `.env` a Git (está en .gitignore)
- **NUNCA** compartas tu API key públicamente
- Si comprometes tu key, puedes generar una nueva en Groq Console

## ❓ Troubleshooting

### Error: "La librería 'groq' no está instalada"

```bash
pip install groq
```

### Error: "Error comunicándose con la API de IA"

- Verifica que tu API key sea correcta
- Verifica tu conexión a internet
- Revisa los límites de tu cuenta en Groq Console

### La IA no está respondiendo

- Verifica que `USE_AI=true` en `.env`
- Verifica que `GROQ_API_KEY` esté configurada
- Revisa los logs del servidor para ver errores

