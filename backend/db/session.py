from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.core.config import PROJECT_ROOT, settings


def prepare_database_url(database_url: str) -> str:
    """Normaliza URLs SQLite e garante que o diretório do banco exista."""
    if not database_url.startswith("sqlite:///"):
        return database_url

    database_path = database_url.removeprefix("sqlite:///")
    if database_path in ("", ":memory:"):
        return database_url

    path = Path(database_path).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path

    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path}"


DATABASE_URL = prepare_database_url(settings.DATABASE_URL)
CONNECT_ARGS = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL, connect_args=CONNECT_ARGS
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
