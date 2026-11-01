"""Migrations must produce exactly the schema the models describe, and upgrade a Week 2 database in place."""
import tempfile

from alembic import command
from sqlalchemy import create_engine, inspect, text

from app.db import Base
from app.migrate import alembic_config, run_migrations


def _url():
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    return f"sqlite:///{f.name}"


def _assert_matches_models(url):
    insp = inspect(create_engine(url))
    for table in Base.metadata.sorted_tables:
        cols = {c["name"]: c for c in insp.get_columns(table.name)}
        assert set(cols) == {c.name for c in table.columns}, table.name
        for c in table.columns:
            assert cols[c.name]["nullable"] == c.nullable, f"{table.name}.{c.name} nullable"
        model_indexes = {i.name for i in table.indexes}
        db_indexes = {i["name"] for i in insp.get_indexes(table.name)}
        assert model_indexes <= db_indexes, f"{table.name} indexes {model_indexes - db_indexes}"


def test_fresh_database_matches_models():
    url = _url()
    run_migrations(url)
    _assert_matches_models(url)


def test_week2_database_is_stamped_and_upgraded_without_data_loss():
    url = _url()
    command.upgrade(alembic_config(url), "0001")          # what Week 2's create_all produced
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE alembic_version"))  # Week 2 had no migration history
        conn.execute(text("INSERT INTO users (email, password_hash, created_at) "
                          "VALUES ('a@b.com', 'x', '2026-10-16 00:00:00')"))
    run_migrations(url)
    _assert_matches_models(url)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT email FROM users")).scalar() == "a@b.com"
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0003"


def test_downgrade_round_trip():
    url = _url()
    run_migrations(url)
    command.downgrade(alembic_config(url), "base")
    assert set(inspect(create_engine(url)).get_table_names()) <= {"alembic_version"}
