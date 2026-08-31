FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml README.md CHANGELOG.md DEVLOG.md alembic.ini ./
COPY backend ./backend
COPY bot ./bot
COPY scripts ./scripts
RUN python -m pip install --no-cache-dir .

RUN addgroup --system app && adduser --system --ingroup app app \
    && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["uvicorn", "k_loto.main:app", "--host", "0.0.0.0", "--port", "8000"]
