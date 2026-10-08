FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY repair_schema.py .
COPY docker-entrypoint.sh .
COPY docker_healthcheck.py .
COPY wait_for_db.py .
COPY dedupe_alembic_version.py .
RUN sed -i 's/\r$//' docker-entrypoint.sh && chmod +x docker-entrypoint.sh

EXPOSE 8000

# Перед запуском API схема доводится до последней ревизии.
CMD ["sh", "docker-entrypoint.sh"]
