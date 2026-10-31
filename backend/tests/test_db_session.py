import pytest

from backend import main
from backend.db.session import prepare_database_url


def test_prepare_database_url_creates_sqlite_parent_directory(tmp_path):
    database_path = tmp_path / "nested" / "data" / "app.db"

    normalized_url = prepare_database_url(f"sqlite:///{database_path}")

    assert database_path.parent.is_dir()
    assert normalized_url == f"sqlite:///{database_path}"


def test_prepare_database_url_keeps_memory_database_unchanged():
    assert prepare_database_url("sqlite:///:memory:") == "sqlite:///:memory:"


@pytest.mark.asyncio
async def test_lifespan_aborts_when_database_initialization_fails(monkeypatch):
    def fail_database_initialization():
        raise RuntimeError("falha de banco simulada")

    monkeypatch.setattr(main, "init_db", fail_database_initialization)

    with pytest.raises(RuntimeError, match="falha de banco simulada"):
        async with main.lifespan(main.app):
            pass
