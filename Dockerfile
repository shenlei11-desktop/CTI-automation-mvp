# Matches the local dev interpreter (Python 3.13) for dev/prod parity.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first (better layer caching), then warm the model caches so
# the first real request doesn't pay a multi-hundred-MB download (or fail outright if
# the container has no outbound network at runtime).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m spacy download en_core_web_sm \
    && python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-base-en-v1.5')" \
    && python -c "from fastembed.rerank.cross_encoder import TextCrossEncoder; TextCrossEncoder(model_name='Xenova/ms-marco-MiniLM-L-6-v2')"

COPY app ./app
COPY data ./data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
