# Matches the local dev interpreter (Python 3.13) for dev/prod parity.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first (better layer caching), then the spaCy model.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m spacy download en_core_web_sm

COPY app ./app
COPY data ./data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
