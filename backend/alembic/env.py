import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

import os
import sys
sys.path.append(os.getcwd())  # so `app` package is importable

# Load env BEFORE importing database (database.py creates engine at import)
from dotenv import load_dotenv
load_dotenv()

config = context.config

# Normalize: alembic offline (sync) needs psycopg2, online (async) needs asyncpg
def _alembic_url(url: str | None) -> str | None:
    if not url:
        return url
    return url

_db_url = os.getenv("DATABASE_URL")
if _db_url:
    # keep asyncpg for online; offline will convert below
    config.set_main_option("sqlalchemy.url", _db_url)

from database import Base
from models.user import User
from models.document import Document
from models.chat_message import ChatMessage
from models.conversation import Conversation
from models.token_usage import TokenUsage

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _sync_url(url: str | None) -> str | None:
    if not url:
        return url
    # offline (sync) must use psycopg2, not asyncpg
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        # default sync driver is psycopg2, keep as is
        return url
    return url

def run_migrations_offline() -> None:
    url = _sync_url(config.get_main_option("sqlalchemy.url"))
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())