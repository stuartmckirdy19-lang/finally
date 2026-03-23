# Stage 1: Build Next.js frontend
FROM node:20-slim AS frontend-builder
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend + serve everything
FROM python:3.12-slim AS app
WORKDIR /app

# Install uv
RUN pip install uv

# Copy backend project files and install deps (source copied AFTER sync for layer caching)
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
RUN uv sync --frozen --no-dev

# Copy backend source
COPY backend/app/ ./app/

# Copy frontend static export
COPY --from=frontend-builder /build/frontend/out/ ./static/

# Create db directory
RUN mkdir -p /app/db

EXPOSE 8000
CMD [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
