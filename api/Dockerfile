# ============================================
# MIGANCORE API — Multi-Stage Optimized Build
# Target: <400MB (from 752MB)
# ============================================

# -------- Stage 1: Builder --------
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build deps only (not needed at runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps into a virtual environment
# (makes it easy to copy to runtime stage)
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -------- Stage 2: Runtime --------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install ONLY runtime system deps (no build tools, no chromium, no nodejs)
# Weasyprint needs: libcairo2, libpango, libgdk-pixbuf, libffi
# PostgreSQL needs: libpq5 (runtime, not dev)
# Fonts needed for PDF generation
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi8 \
    shared-mime-info \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN groupadd -r ado && useradd -r -g ado ado

# Create writable directories for the app (needed for read-only rootfs)
RUN mkdir -p /app/workspace /tmp /var/tmp && chown -R ado:ado /app /tmp /var/tmp

# Copy application code
COPY . .
RUN chown -R ado:ado /app

# Switch to non-root user
USER ado

# Run FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
