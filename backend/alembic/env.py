from alembic import context
from sqlalchemy import create_engine, pool

from app import models  # noqa: F401  (registers tables on Base.metadata)
from app.config import get_settings
from app.db import Base

config = context.config
target_metadata = Base.metadata


def _url() -> str:
    # tests pass a URL explicitly; normal runs use DATABASE_URL
    return config.attributes.get("url") or get_settings().sqlalchemy_url


def _configure(**kwargs) -> None:
    context.configure(target_metadata=target_metadata, compare_type=True, **kwargs)


if context.is_offline_mode():
    _configure(url=_url(), literal_binds=True, render_as_batch=_url().startswith("sqlite"))
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        # batch mode lets ALTER-style migrations work on SQLite (local dev/tests)
        _configure(connection=connection, render_as_batch=connection.dialect.name == "sqlite")
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
