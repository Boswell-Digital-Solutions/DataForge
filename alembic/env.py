from logging.config import fileConfig
import os
import sys
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

import alembic  # type: ignore
from alembic import context as _context  # type: ignore
from dotenv import load_dotenv

# Add parent directory to Python path to import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load environment variables
load_dotenv()

# Import our database and models
from app.database import Base
# Import ALL model modules to register them with Base.metadata
from app.models import models  # noqa: F401 - core models
from app.models import authorforge_models  # noqa: F401
from app.models import authorforge_v2_models  # noqa: F401
from app.models import vibeforge_models  # noqa: F401
from app.models import runs_models  # noqa: F401
from app.models import planning_models  # noqa: F401
from app.models import team_models  # noqa: F401
from app.models import diligence_models  # noqa: F401
from app.models import bugcheck_models  # noqa: F401
from app.models import buildguard_models  # noqa: F401
from app.models import smithy_portfolio_models  # noqa: F401
from app.models import smithy_planning_models  # noqa: F401
from app.models import neuroforge_models  # noqa: F401
from app.models import tarcie_models  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = _context.config

# Set the database URL from environment variable
db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/dataforge")
config.set_main_option("sqlalchemy.url", db_url.replace("%", "%%"))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    _context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with _context.begin_transaction():
        _context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with _context.begin_transaction():
            _context.run_migrations()


if _context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
