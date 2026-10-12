# One image for the API, the ingestion worker and migrations (different commands).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# Tesseract with English + Malay language packs, poppler for scanned-PDF rendering.
RUN apt-get update \
 && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng tesseract-ocr-msa poppler-utils \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY pyproject.toml ./
COPY app ./app
ARG EXTRAS="gcp"
RUN pip install ".[${EXTRAS}]" && python -m spacy download en_core_web_sm

COPY alembic.ini ./
COPY migrations ./migrations
COPY data ./data
COPY scripts ./scripts

RUN useradd --create-home --uid 10001 appuser \
 && mkdir -p /srv/var/uploads && chown -R appuser /srv/var
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
