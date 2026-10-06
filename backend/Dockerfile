FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml README.md alembic.ini ./
COPY backend ./backend
COPY bot ./bot
COPY scripts ./scripts
COPY frontend/miniapp/public/assets/publications ./publication-assets
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
RUN --mount=type=cache,target=/root/.cache/pip python -m pip install .
COPY CHANGELOG.md DEVLOG.md ./

RUN addgroup --system app && adduser --system --ingroup app app \
    && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["uvicorn", "k_loto.main:app", "--host", "0.0.0.0", "--port", "8000"]
