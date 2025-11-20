# 🚀 Cómo Activar la IA en Ecko - Guía Rápida

## 📝 Pasos Rápidos

### Paso 1: Obtener API Key de Groq (GRATIS)

1. Ve a **https://console.groq.com/**
2. Clic en **"Sign Up"** o **"Log In"** (si ya tienes cuenta)
3. Una vez dentro, ve a **"API Keys"** en el menú lateral
4. Clic en **"Create API Key"**
5. Dale un nombre (ej: "Ecko-Asistente")
6. **COPIA LA API KEY** (solo se muestra una vez)

### Paso 2: Crear archivo .env

1. Abre tu terminal/PowerShell en la carpeta del proyecto
2. Ve a la carpeta backend:
```powershell
cd app\backend
```

3. Crea el archivo `.env`:
```powershell
# Opción 1: Con notepad
notepad .env

# Opción 2: Con PowerShell
echo USE_AI=true > .env
echo GROQ_API_KEY=tu_api_key_aqui >> .env
```

4. **Edita el archivo .env** y pega tu API key:
```
USE_AI=true
GROQ_API_KEY=gsk_tu_api_key_real_aqui
```

**⚠️ IMPORTANTE**: Reemplaza `tu_api_key_aqui` con la API key real que copiaste de Groq.

### Paso 3: Instalar dependencias

Si aún no instalaste las dependencias actualizadas:
```powershell
pip install -r requirements.txt
```

Esto instalará `groq` y `python-dotenv`.

### Paso 4: Reiniciar el servidor

1. Si el servidor está corriendo, deténlo (Ctrl+C)
2. Inícialo de nuevo:
```powershell
cd C:\Users\franc\Desktop\Ecko
python start.py
```

### Paso 5: ¡Probar!

Abre http://localhost:8000 y prueba con:
- "Hola"
- "¿Qué puedes hacer?"
- "Cuéntame un chiste"
- "¿Cómo funciona la IA?"

## ✅ Verificar que la IA está activa

Si la IA está activa, las respuestas serán:
- ✨ Más naturales y conversacionales
- ✨ Mantienen contexto de la conversación
- ✨ Pueden responder preguntas complejas
- ✨ Más coherentes e inteligentes

Si ves respuestas tipo "Interesante, cuéntame más" o genéricas, la IA no está activa. Revisa:
1. ✅ `USE_AI=true` en `.env`
2. ✅ API key correcta en `.env`
3. ✅ Dependencias instaladas (`pip install groq`)
4. ✅ Servidor reiniciado después de configurar

## 🔍 Ver logs en la consola

Si hay errores con la IA, verás mensajes en la terminal del servidor:
- ❌ "Error comunicándose con la API de IA" = Problema con la API key o conexión
- ❌ "La librería 'groq' no está instalada" = Falta instalar dependencias

## 💡 Ejemplo de Configuración Correcta

Tu archivo `.env` debería verse así:
```
USE_AI=true
GROQ_API_KEY=gsk_abc123xyz456789...
```

**NO debe tener** espacios extras, comillas, o caracteres especiales.

## 🎯 ¿Listo?

Una vez configurado, la IA responderá de forma inteligente a tus preguntas y mantendrá conversaciones naturales. ¡Pruébala!

