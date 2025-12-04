# Dockerfile para Ecko - Asistente Virtual (Multi-Stage Optimizado)

# ============================================
# STAGE 1: Builder - Instalar dependencias
# ============================================
FROM python:3.12-slim as builder

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements.txt
COPY app/backend/requirements.txt ./requirements.txt

# Instalar dependencias en un directorio local
# Esto permite copiar solo las dependencias, no pip ni otras herramientas
RUN pip install --user --no-cache-dir -r requirements.txt

# ============================================
# STAGE 2: Runtime - Imagen final pequeña
# ============================================
FROM python:3.12-slim

# Establecer directorio de trabajo
WORKDIR /app

# Copiar SOLO las dependencias instaladas del stage anterior
# Esto copia solo los paquetes de Python, no pip ni herramientas de build
COPY --from=builder /root/.local /root/.local

# Asegurar que los scripts instalados estén en el PATH
ENV PATH=/root/.local/bin:$PATH

# Copiar el código de la aplicación
COPY app/backend/ ./app/backend/
COPY app/frontend/ ./app/frontend/

# Crear directorio para datos (base de datos SQLite)
RUN mkdir -p ./app/backend/data/chats

# Cambiar al directorio del backend
WORKDIR /app/app/backend

# Exponer el puerto 8000
EXPOSE 8000

# Comando para iniciar la aplicación
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]