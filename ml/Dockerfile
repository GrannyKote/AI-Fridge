FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Индекс CPU: в контейнере нет CUDA, а PyPI по умолчанию ставит сборку под видеокарту.
# Повтор всего шага: оборванное соединение pip не всегда докачивает сам.
RUN pip install --no-cache-dir --upgrade pip \
    && ok=0 \
    && for _ in 1 2 3 4 5; do \
        if pip install --no-cache-dir --default-timeout=300 --retries 8 \
            torch torchvision --index-url https://download.pytorch.org/whl/cpu; then \
            ok=1; \
            break; \
        fi; \
        sleep 15; \
    done \
    && test "$ok" = 1

RUN ok=0 \
    && for _ in 1 2 3 4 5; do \
        if pip install --no-cache-dir --default-timeout=300 --retries 8 \
            --upgrade-strategy only-if-needed -r requirements.txt; then \
            ok=1; \
            break; \
        fi; \
        sleep 15; \
    done \
    && test "$ok" = 1

# Уже скачанные на хосте веса кладём в образ. Чего нет — докачивает ensure_models.py.
COPY .model-cache/easyocr/ /root/.EasyOCR/model/
COPY ensure_models.py .
RUN ok=0 \
    && for _ in 1 2 3 4 5; do \
        if python ensure_models.py; then \
            ok=1; \
            break; \
        fi; \
        sleep 15; \
    done \
    && test "$ok" = 1

# CPU-колесо: сборка llama.cpp из исходников на этом шаге не нужна.
RUN ok=0 \
    && for _ in 1 2 3 4 5; do \
        if pip install --no-cache-dir --default-timeout=300 --retries 8 \
            llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu; then \
            ok=1; \
            break; \
        fi; \
        sleep 15; \
    done \
    && test "$ok" = 1

COPY .model-cache/llm/ /opt/llm/
ENV LLM_MODEL=/opt/llm/qwen2.5-1.5b-instruct-q4_k_m.gguf

COPY receipts ./receipts
COPY schema.sql ./schema.sql

EXPOSE 8001

CMD ["uvicorn", "receipts.api:app", "--host", "0.0.0.0", "--port", "8001"]
