# 🐳 Docker - Guía de Uso para Ecko

Ecko está containerizado usando Docker para facilitar el despliegue y desarrollo.

## 📋 Requisitos

- Docker instalado ([Descargar Docker](https://www.docker.com/get-started))
- Docker Compose (incluido con Docker Desktop)

## 🚀 Uso Rápido

### Desarrollo Local con Docker Compose

1. **Construir y ejecutar**:
```bash
docker-compose up --build
```

2. **Ejecutar en segundo plano**:
```bash
docker-compose up -d
```

3. **Ver logs**:
```bash
docker-compose logs -f
```

4. **Detener**:
```bash
docker-compose down
```

5. **Acceder a la aplicación**:
   - Interfaz web: http://localhost:8000
   - API docs: http://localhost:8000/docs

### Configuración de IA

Para usar la IA, asegúrate de tener tu archivo `.env` en `app/backend/`:
```env
USE_AI=true
GROQ_API_KEY=tu_api_key_aqui
```

El archivo `.env` se monta automáticamente en el contenedor.

## 🔧 Comandos Útiles

### Docker Compose

```bash
# Reconstruir imágenes
docker-compose build

# Reiniciar servicios
docker-compose restart

# Ver estado
docker-compose ps

# Eliminar contenedores y volúmenes
docker-compose down -v

# Ejecutar comando en el contenedor
docker-compose exec ecko bash
```

### Docker (sin compose)

```bash
# Construir imagen
docker build -t ecko:latest .

# Ejecutar contenedor
docker run -p 8000:8000 \
  -v $(pwd)/app/backend/.env:/app/backend/.env:ro \
  ecko:latest

# Ver logs
docker logs ecko-asistente

# Detener contenedor
docker stop ecko-asistente
```

## 🏗️ Estructura del Dockerfile

El Dockerfile usa una estrategia **multi-stage**:

1. **Stage Builder**: Instala dependencias y compila paquetes
2. **Stage Runtime**: Imagen final ligera solo con lo necesario

Esto resulta en:
- ✅ Imagen más pequeña (~150MB vs ~500MB)
- ✅ Mayor seguridad (sin herramientas de build)
- ✅ Builds más rápidos (caché de capas)

## 🔒 Seguridad

- ✅ Usuario no-root (`ecko`)
- ✅ Solo puerto necesario expuesto (8000)
- ✅ Health checks configurados
- ✅ Variables sensibles no en imagen

## 📊 Monitoreo

### Health Check

El contenedor incluye un health check que verifica el endpoint `/health`:

```bash
# Ver estado del health check
docker ps
```

### Logs

```bash
# Logs en tiempo real
docker-compose logs -f ecko

# Últimas 100 líneas
docker-compose logs --tail=100 ecko
```

## 🚢 Producción

Para producción, usa `docker-compose.prod.yml`:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

Este archivo incluye:
- Límites de recursos (CPU/RAM)
- Restart policy: `always`
- Configuración optimizada para producción

## 🔍 Troubleshooting

### Error: "Cannot connect to Docker daemon"

Asegúrate de que Docker Desktop esté corriendo.

### Error: "Port 8000 already in use"

Cambia el puerto en `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"  # Puerto host:puerto contenedor
```

### Error: "Module not found" dentro del contenedor

Asegúrate de que todas las dependencias estén en `requirements.txt` y reconstruye:
```bash
docker-compose build --no-cache
```

### Ver archivos dentro del contenedor

```bash
docker-compose exec ecko ls -la /app
```

### Reiniciar desde cero

```bash
# Eliminar todo y empezar de nuevo
docker-compose down -v
docker system prune -a
docker-compose up --build
```

## 📝 Notas

- El código se monta como volumen en desarrollo (cambios se reflejan automáticamente)
- En producción, el código está copiado en la imagen (más seguro)
- El archivo `.env` debe estar presente para usar la IA
- Los logs se muestran en stdout/stderr (visibles con `docker-compose logs`)

## 🎯 Próximos Pasos

Una vez que Docker funcione localmente, podrás:
1. Subir la imagen a un registry (Docker Hub, ECR)
2. Desplegar en AWS ECS Fargate
3. Configurar CI/CD para builds automáticos

