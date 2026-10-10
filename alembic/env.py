"""
alembic/env.py
--------------
Alembic environment configuration.

* Reads DATABASE_URL from the application Settings (which reads from .env).
* Imports all models through app.models so every table is discovered.
* Supports both online (live DB) and offline (SQL script) migration modes.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Load application settings ─────────────────────────────────────────────────
# This import also triggers discovery of all SQLAlchemy models via
# app.models.__init__, which re-exports Base and all mapped classes.
from app.core.config import get_settings
import app.models  # noqa: F401  — ensures all models are registered with Base
from app.db.session import Base

settings_obj = get_settings()

# ── Alembic Config ────────────────────────────────────────────────────────────
config = context.config

# Override the sqlalchemy.url from alembic.ini with the value from Settings
config.set_main_option("sqlalchemy.url", settings_obj.DATABASE_URL)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ── Migration runners ─────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode, generating SQL without a live DB connection.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode against a live database connection.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
