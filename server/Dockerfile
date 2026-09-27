# Build context is the repo root (see docker-compose.yml), because this
# image needs both server/ and ui/web/.

FROM node:22-slim AS ui-build
WORKDIR /ui
COPY ui/web/package.json ui/web/package-lock.json* ./
RUN npm install
COPY ui/web/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

COPY server/requirements.txt ./server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt

COPY server/ ./server/
COPY --from=ui-build /ui/dist ./ui/web/dist

ENV SOUND_ASSISTANT_DB=/data/sound_assistant.db
VOLUME ["/data"]

EXPOSE 8000
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
