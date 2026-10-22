FROM python:3.12-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

ENV PATH="/app/.venv/bin:$PATH" \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

COPY pyproject.toml uv.lock README.md alembic.ini ./
COPY backend ./backend
COPY bot ./bot
COPY scripts ./scripts
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
RUN uv sync --locked --no-dev --no-editable --python /usr/local/bin/python \
    && uv cache clean
COPY CHANGELOG.md DEVLOG.md ./

RUN python -m scripts.verify_runtime_lock --write runtime-manifest.json

RUN addgroup --system app && adduser --system --ingroup app app \
    && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["uvicorn", "k_loto.main:app", "--host", "0.0.0.0", "--port", "8000"]
