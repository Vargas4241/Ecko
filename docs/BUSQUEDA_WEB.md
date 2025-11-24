# 🔍 Sistema de Búsqueda Web Inteligente

Ecko ahora puede buscar información en internet para responderte con datos actualizados del mundo real.

## 🎯 Características

- ✅ Búsqueda web en tiempo real
- ✅ Respuestas basadas en información actualizada
- ✅ Múltiples proveedores de búsqueda
- ✅ Integración automática con la IA

## 📋 Comandos Disponibles

### Comandos Explícitos

```
buscar [tema]
busca [tema]
qué es [concepto]
que es [concepto]
noticias [tema]
```

### Búsqueda Automática

La IA detecta automáticamente cuándo necesitas información actualizada y busca por ti. Por ejemplo:

- "¿Qué pasó con Python últimamente?"
- "Noticias de tecnología"
- "Información sobre Docker"
- "¿Cuándo salió la nueva versión de FastAPI?"

## 🔧 Configuración

### ✅ ¡Por Defecto ya Funciona!

**La búsqueda está ACTIVADA por defecto usando DuckDuckGo** - **¡NO necesitas configurar NADA!**

Solo ejecuta la aplicación y la búsqueda funcionará inmediatamente.

### Opción 1: DuckDuckGo (Por Defecto - Sin Configuración)

**✅ Ya está configurado y funcionando** - No necesitas hacer nada.

DuckDuckGo funciona sin API key y es completamente gratuito. Perfecto para empezar.

### Opción 2: Tavily API (Opcional - Mejor Calidad)

Si quieres mejor calidad de búsqueda (recomendado para producción):

1. **Obtener API Key gratuita:**
   - Ve a [Tavily.com](https://tavily.com)
   - Crea una cuenta (gratis)
   - Obtén tu API key

2. **Crear archivo `.env` en `app/backend/`** (solo si quieres usar Tavily):
   ```env
   ENABLE_SEARCH=true
   SEARCH_PROVIDER=tavily
   SEARCH_API_KEY=tu_api_key_aqui
   ```

**Nota:** Si no creas el archivo `.env`, funcionará con DuckDuckGo automáticamente.

### Desactivar Búsqueda (Opcional)

Si por alguna razón quieres desactivar la búsqueda, crea `.env`:

```env
ENABLE_SEARCH=false
```

## 📊 Proveedores Disponibles

| Proveedor | API Key | Calidad | Límite |
|-----------|---------|---------|--------|
| **Tavily** | ✅ Requerida | ⭐⭐⭐⭐⭐ Excelente | Gratis con límites |
| **DuckDuckGo** | ❌ No requiere | ⭐⭐⭐ Buena | Sin límite conocido |

## 🚀 Ejemplos de Uso

### Búsqueda Explícita

```
Usuario: buscar Python 3.12 nuevas características
Ecko: 🔍 Encontré información sobre 'Python 3.12 nuevas características':

**Fuentes encontradas:**
1. Python 3.12 Release Notes
   Python 3.12 incluye mejoras de rendimiento...
```

### Búsqueda Automática

```
Usuario: ¿Qué son las últimas noticias de tecnología?
Ecko: [Busca automáticamente y responde con IA usando los resultados]
```

### Preguntas Específicas

```
Usuario: qué es Docker
Ecko: 🔍 Docker es una plataforma de contenedores que permite...
```

## 🔍 Cómo Funciona

1. **Detección**: Ecko detecta si tu pregunta necesita información actualizada
2. **Búsqueda**: Busca en internet usando el proveedor configurado
3. **Procesamiento**: La IA procesa los resultados y genera una respuesta natural
4. **Respuesta**: Te da una respuesta informada y actualizada

## ⚙️ Variables de Entorno

Añade estas variables a tu archivo `app/backend/.env`:

```env
# Activar/desactivar búsqueda
ENABLE_SEARCH=true

# Proveedor: "tavily" o "duckduckgo"
SEARCH_PROVIDER=tavily

# API Key (solo necesario para Tavily)
SEARCH_API_KEY=tu_api_key_aqui
```

## 🐛 Troubleshooting

### La búsqueda no funciona

1. Verifica que `ENABLE_SEARCH=true` en tu `.env`
2. Si usas Tavily, verifica que tu API key sea correcta
3. Revisa los logs del servidor para ver errores

### Errores de conexión

- DuckDuckGo puede tener límites de rate
- Tavily tiene límites según tu plan
- Verifica tu conexión a internet

### Respuestas genéricas

- La búsqueda funciona mejor con preguntas específicas
- Usa comandos explícitos como "buscar [tema]" para mejores resultados

## 📝 Notas

- La búsqueda automática solo se activa cuando Ecko detecta que necesitas información actualizada
- Los resultados se integran automáticamente con las respuestas de la IA
- Puedes desactivar la búsqueda en cualquier momento desde `.env`

## 🔗 Enlaces Útiles

- [Tavily API](https://tavily.com)
- [Documentación de Tavily](https://docs.tavily.com)
- [DuckDuckGo](https://duckduckgo.com)

