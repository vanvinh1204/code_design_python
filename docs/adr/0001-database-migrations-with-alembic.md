# Database Migrations with Alembic

Status: accepted

## Context & Decision

Core applications built with `core_kit` span both web backends (FastAPI) and desktop applications (PySide6). Previously, the database layer relied solely on SQLAlchemy's `create_tables()`, which cannot alter or migrate existing tables without schema recreation.

We decided to adopt **Alembic** as the official database migration engine, providing both standard CLI configuration templates and a programmatic execution API (`apply_migrations` and `DatabaseManager.migrate()`). The environment configuration explicitly enables SQLite batch mode (`render_as_batch=True`) and dynamically resolves asset locations for packaged desktop executables (`sys.frozen`).

## Considered Options

- **SQLAlchemy `create_tables` only**: Simple and zero extra dependencies, but impossible to evolve schemas or add/alter columns without data loss.
- **Custom SQL migration script runner**: Lightweight, but requires manual tracking of revision graphs, fails to autogenerate schema diffs from ORM models, and reinvents transaction rollbacks.
- **Alembic CLI only**: Industry standard, but unusable inside packaged desktop applications (PySide6 executables) where end-users cannot and should not run terminal commands.

## Consequences

- Applications can automatically upgrade their schema to `head` during startup with a single call to `db_manager.migrate()`.
- Desktop SQLite databases can safely alter, add, and drop columns through Alembic's batch mode.
- Each downstream application maintains its own version history under its own repository, avoiding shared-library migration conflicts.
