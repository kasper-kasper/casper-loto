"""Shared test environment setup."""

import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/k_loto_test",
)
