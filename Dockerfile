# All-in-one image: builds the React frontend, then serves it from FastAPI
# (./static) alongside the API + SQLite. Used by Hugging Face Spaces (free tier).
# HF Spaces listens on port 7860 by default.
FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
ENV VITE_API_BASE=""
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=web /web/dist ./static
ENV DATABASE_URL="sqlite:///./foodmate.db" PORT="7860" AI_PROVIDER="rule" DEMO_MODE="true"
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
