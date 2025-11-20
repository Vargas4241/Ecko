# Dockerfile multi-stage para Ecko - Asistente Virtual
# Optimizado para producción con imágenes pequeñas y rápidas

# Stage 1: Builder - Instalar dependencias
FROM python:3.12-slim AS builder

WORKDIR /app

# Instalar dependencias del sistema necesarias para compilar algunos paquetes Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y instalar dependencias Python
COPY app/backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime - Imagen final optimizada
FROM python:3.12-slim

WORKDIR /app

# Crear usuario no-root para seguridad
RUN useradd -m -u 1000 ecko && \
    mkdir -p /app && \
    chown -R ecko:ecko /app

# Copiar dependencias instaladas desde el builder
COPY --from=builder /root/.local /home/ecko/.local

# Copiar código de la aplicación
COPY --chown=ecko:ecko app/backend/ ./backend/
COPY --chown=ecko:ecko app/frontend/ ./frontend/

# Añadir .local/bin al PATH para el usuario
ENV PATH=/home/ecko/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Cambiar a usuario no-root
USER ecko

# Exponer puerto 8000
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Comando para iniciar la aplicación
CMD ["python", "backend/main.py"]

