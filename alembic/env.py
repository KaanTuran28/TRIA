import asyncio
from logging.config import fileConfig

from geoalchemy2.alembic_helpers import include_object as ga2_include_object
from geoalchemy2.alembic_helpers import render_item as ga2_render_item
from geoalchemy2.alembic_helpers import writer as ga2_writer
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.core.database import Base, DATABASE_URL
from app.modules.c4i.models import PoliceUnit, PoliceUnitHistory  # noqa: F401
from app.modules.crime.models import CrimeEvent, RawNewsArchive  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

_KNOWN_TABLES = set(target_metadata.tables.keys())


def include_object(object_, name, type_, reflected, compare_to):
    """PostGIS/tiger-geocoder uzanti tablolarini (bizim modelimizde olmayan,
    yalnizca DB'de reflected goruntu) autogenerate'in 'DROP' onerilerinden haric tutar.
    """
    if reflected and compare_to is None:
        if type_ == "table" and name not in _KNOWN_TABLES:
            return False
        if type_ in ("index", "unique_constraint", "foreign_key_constraint"):
            table = getattr(object_, "table", None)
            if table is not None and table.name not in _KNOWN_TABLES:
                return False
    return ga2_include_object(object_, name, type_, reflected, compare_to)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        render_item=ga2_render_item,
        process_revision_directives=ga2_writer,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        render_item=ga2_render_item,
        process_revision_directives=ga2_writer,
    )
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
