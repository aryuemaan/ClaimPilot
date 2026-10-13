# ClaimPilot - one container: React build served by FastAPI, ADK agents inside.
# Build & deploy:  ./deploy/deploy.sh   (or: gcloud run deploy claimpilot --source .)

# ---- 1. Build the web app ---------------------------------------------------
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- 2. Python runtime ------------------------------------------------------
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    TZ=IST-5:30
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt
COPY backend/app backend/app
COPY sample-data sample-data
COPY --from=web /web/dist frontend/dist
WORKDIR /app/backend
EXPOSE 8080
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips="*" --timeout-keep-alive 75
