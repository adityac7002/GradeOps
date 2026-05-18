# ── Stage 1: Python dependency builder ───────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools only in the builder stage
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# ── Stage 2: Runtime image ─────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Security: run as non-root user
RUN groupadd --gid 1001 gradeops && \
    useradd --uid 1001 --gid gradeops --no-create-home gradeops

WORKDIR /app

# Copy only installed packages from builder
COPY --from=builder /root/.local /root/.local

# System deps for PDF processing and image handling
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY .env.example .

# Create storage directory with correct ownership
RUN mkdir -p storage && chown -R gradeops:gradeops /app/storage

# Copy built frontend if available
COPY --chown=gradeops:gradeops frontend/dist/ ./frontend/dist/ 2>/dev/null || true

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

USER gradeops

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
