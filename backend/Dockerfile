FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ffmpeg espeak-ng tesseract-ocr tesseract-ocr-eng tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml requirements.lock README.md alembic.ini ./
COPY alembic ./alembic
COPY src ./src
RUN python -m pip install --no-cache-dir --upgrade pip==26.2.1 setuptools==84.0.0
RUN pip install --no-cache-dir -c requirements.lock -e ".[dev,media]" \
    && pip check

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/.runtime \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "ccg_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
