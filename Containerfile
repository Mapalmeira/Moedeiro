FROM node:24-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build:production


FROM python:3.14-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    REGISTRY_SCHEMA_PATH=/app/backend/app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql \
    LEDGER_SCHEMA_PATH=/app/backend/app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql \
    REGISTRY_DB_PATH=/data/registry/registry.sqlite \
    LEDGER_DBS_DIR=/data/ledgers \
    PYTHONPATH=/app/backend \
    FRONTEND_DIST_PATH=/app/frontend

WORKDIR /app

COPY backend/app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/app/ /app/backend/app/
COPY --chmod=755 backend/bin/moedeiro-cli /usr/local/bin/moedeiro-cli

COPY --from=frontend-build /app/frontend/dist/moedeiro/browser/ /app/frontend/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]