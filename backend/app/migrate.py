"""Apply Alembic migrations. Run on startup (AUTO_MIGRATE) or manually: `python -m app.migrate`.

Databases created by Week 2 (tables made with create_all, no alembic_version table) are detected and
stamped at revision 0001 first, so the Week 3 migration upgrades them in place without data loss."""
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, pool

from app.config import get_settings

log = logging.getLogger("app.migrate")
BACKEND_DIR = Path(__file__).resolve().parent.parent


def alembic_config(url: str) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.attributes["url"] = url  # passed via attributes, not the ini, so '%' in passwords needs no escaping
    return cfg


def run_migrations(url: str | None = None) -> None:
    url = url or get_settings().sqlalchemy_url
    cfg = alembic_config(url)
    engine = create_engine(url, poolclass=pool.NullPool)
    try:
        with engine.connect() as conn:
            tables = set(inspect(conn).get_table_names())
    finally:
        engine.dispose()
    if "users" in tables and "alembic_version" not in tables:
        log.info("existing Week 2 schema without migration history: stamping 0001")
        command.stamp(cfg, "0001")
    command.upgrade(cfg, "head")
    log.info("database schema is up to date")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migrations()
