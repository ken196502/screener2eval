# Multi-stage build for React frontend and Python backend

# Stage 1: Build frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app

# Copy package files for workspace
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY frontend/package.json ./frontend/

# Install pnpm and dependencies
RUN npm install -g pnpm@8.15.5
RUN pnpm install --frozen-lockfile

# Copy frontend source
COPY frontend/ ./frontend/

# Build frontend for production
WORKDIR /app/frontend
RUN pnpm run build

# Stage 2: Setup Python backend
FROM python:3.11-slim AS backend

WORKDIR /app

# Install uv for Python dependency management
RUN pip install uv

# Copy backend files
COPY backend/ ./backend/
COPY backend/pyproject.toml backend/uv.lock ./backend/

# Install Python dependencies
WORKDIR /app/backend
RUN uv sync --frozen

# Copy built frontend static files to backend static directory
COPY --from=frontend-builder /app/frontend/dist /app/backend/static

# Expose port
EXPOSE 2611

# Set environment variables
ENV PYTHONPATH=/app/backend
ENV HOST=0.0.0.0
ENV PORT=2611

# Start the application
WORKDIR /app/backend
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "2611"]