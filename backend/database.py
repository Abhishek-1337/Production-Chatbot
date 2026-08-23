from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv
import os

load_dotenv()

_DATABASE_URL = os.getenv("DATABASE_URL")
if not _DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set — check backend/.env or docker-compose environment")

_ssl_mode = os.getenv("DATABASE_SSL", "").lower().strip()
if _ssl_mode in ("require", "true", "1"):
    _connect_args = {"ssl": "require"}
elif _ssl_mode in ("disable", "false", "0"):
    _connect_args = {}
else:
    _is_local = any(
        h in _DATABASE_URL for h in ["@db:", "@db/", "@localhost", "@127.0.0.1", "localhost:", "127.0.0.1:"]
    )
    _needs_ssl = any(
        h in _DATABASE_URL for h in ["neon.tech", "supabase.co", "rds.amazonaws.com", "sslmode=require"]
    )
    if _needs_ssl or not _is_local:
        _connect_args = {} if _is_local else {"ssl": "require"}
    else:
        _connect_args = {}

engine = create_async_engine(
    _DATABASE_URL,
    connect_args=_connect_args,
    echo=False,
)

SessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with SessionLocal() as session:
        yield session