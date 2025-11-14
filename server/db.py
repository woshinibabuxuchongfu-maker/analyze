import os
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, declarative_base

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None  # type: ignore


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_env() -> None:
    # Always try project root .env first to be stable regardless of CWD
    root_env = os.path.join(_project_root(), ".env")
    if os.path.exists(root_env) and load_dotenv is not None:
        load_dotenv(dotenv_path=root_env, override=False)
    # Allow local override by current working directory .env if present
    if load_dotenv is not None:
        load_dotenv(override=False)


def _build_url_from_env() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        if url.startswith("mysql://"):
            url = url.replace("mysql://", "mysql+pymysql://", 1)
        return url

    host = os.getenv("DB_HOST")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    database = os.getenv("DB_DATABASE")
    port = os.getenv("DB_PORT", "3306")

    missing = [k for k, v in {
        "DB_HOST": host,
        "DB_USER": user,
        "DB_PASSWORD": password,
        "DB_DATABASE": database,
    }.items() if not v]

    if missing:
        raise RuntimeError(
            f"Missing env for MySQL: {', '.join(missing)}. "
            "Please set DATABASE_URL or DB_HOST/DB_USER/DB_PASSWORD/DB_DATABASE."
        )

    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"


def _ensure_database_exists(url: str) -> None:
    # connect without database to create it if needed
    from urllib.parse import urlparse

    parsed = urlparse(url)
    db_name = parsed.path.lstrip("/")
    if not db_name:
        return

    admin_url = url.replace(f"/{db_name}", "/mysql", 1)
    admin_engine = create_engine(admin_url, pool_pre_ping=True)
    with admin_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
        conn.commit()
    admin_engine.dispose()


_load_env()
DATABASE_URL = _build_url_from_env()
_ensure_database_exists(DATABASE_URL)

engine: Engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()