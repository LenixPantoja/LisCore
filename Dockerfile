# ============================================================
# Etapa 1: Builder — compila dependencias Python
# ============================================================
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Dependencias de compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf-2.0-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python en /install para copiarlas a la imagen final
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install -r requirements.txt

# ============================================================
# Etapa 2: Imagen final de producción
# ============================================================
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=America/Bogota

# Dependencias de runtime necesarias:
# - libpq5       → psycopg2 (PostgreSQL)
# - libcairo2, libpango-1.0-0, libgdk-pixbuf-2.0-0, libpangocairo-1.0-0 → WeasyPrint (PDFs)
# - libgomp1     → soporte OpenMP para algunas librerías científicas
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libcairo2 \
    libpango-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libgomp1 \
    shared-mime-info \
    fonts-dejavu-core \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copiar dependencias Python desde el builder
COPY --from=builder /install /usr/local

# Copiar código de la aplicación
COPY . .

# Usuario no-root por seguridad
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser /app
USER appuser

EXPOSE 8000

# # Healthcheck: verifica que el endpoint raíz responda
# HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
#     CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health', timeout=5)" || exit 1

# Workers = 2 * CPU cores + 1 (para 4 cores ≈ 9, usamos 4 conservador)
# --proxy-headers para respetar X-Forwarded-* detrás de reverse proxy
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers", "--log-level", "info"]
