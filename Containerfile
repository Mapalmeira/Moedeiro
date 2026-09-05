FROM node:24-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build:production


FROM python:3.14-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    REGISTRY_DB_PATH=/data/registry/registry.sqlite \
    LEDGER_DBS_DIR=/data/ledgers \
    FRONTEND_DIST_PATH=/app/frontend

WORKDIR /app

COPY backend/ /app/backend/
RUN pip install --no-cache-dir /app/backend && rm -rf /app/backend

COPY --from=frontend-build /app/frontend/dist/moedeiro/browser/ /app/frontend/

EXPOSE 8000

CMD ["moedeiro", "start", "--host", "0.0.0.0", "--port", "8000"]
