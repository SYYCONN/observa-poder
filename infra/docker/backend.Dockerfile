FROM python:3.15-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY backend/requirements.lock ./requirements.lock
RUN pip install -r requirements.lock && useradd --create-home --uid 10001 appuser
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./alembic.ini
COPY infra/postgres/release_db.py infra/docker/serve_production.py ./
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers", "--no-server-header", "--no-access-log", "--log-level", "info", "--limit-concurrency", "100", "--timeout-keep-alive", "5"]
