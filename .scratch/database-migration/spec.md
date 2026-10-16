# Database Migration Management Specification

Status: resolved

## Problem Statement

Applications built on `core_kit` (FastAPI web backends and PySide6 desktop applications) currently only have `create_tables()` via SQLAlchemy metadata. As applications evolve and models change over time (adding or modifying columns, altering tables, adjusting indexes), `create_tables()` cannot update existing database schemas. 

Without migration management, developers and end-users face broken data schemas, risk of data loss during updates, manual SQL scripting, and an inability to reliably upgrade local SQLite databases distributed with desktop applications or remote databases deployed on servers.

## Solution

Integrate a database migration management layer into `core_kit` powered by Alembic. 

This layer provides:
1. **Programmatic Migration Runner**: A Python API (`apply_migrations`) and a convenient method on `DatabaseManager` (`db_manager.migrate()`) that automatically upgrades database schemas to `head` during application startup (crucial for zero-touch desktop app updates).
2. **SQLite Batch Mode Support**: Pre-configured support for SQLite batch operations (`render_as_batch=True`), enabling table alterations (drop/alter column, rename constraints) on SQLite without errors.
3. **Packaging / Frozen Environment Compatibility**: Automatic resolution of migration assets when running inside bundled executables (such as PyInstaller).
4. **Standard Migration Scaffolding**: Standardized templates (`alembic.ini` and `env.py`) connecting to the shared `Base` metadata, allowing developers to use standard Alembic CLI workflows for generating and reviewing revisions.
5. **Decoupled Architecture**: `core_kit` provides the migration engine and helpers, while each consumer application owns and version-controls its own migration scripts.

## User Stories

1. As a desktop application developer, I want my app to automatically run database migrations on startup, so that end-user local SQLite databases upgrade without requiring manual user intervention.
2. As a web backend developer, I want to execute database migrations programmatically or via CLI during deployment, so that the database schema is synchronized with application releases.
3. As an application developer, I want to generate new migration scripts automatically by comparing existing schemas with current SQLAlchemy models, so that I do not need to manually write DDL scripts.
4. As a desktop developer using SQLite, I want schema modifications (such as dropping or altering columns) to execute smoothly via SQLite batch mode, so that migrations do not fail due to SQLite's DDL constraints.
5. As an engineer packaging desktop applications with PyInstaller, I want the migration helper to correctly find migration script folders in frozen bundles, so that packaged executables do not crash on startup.
6. As a library consumer, I want to trigger migrations directly from `DatabaseManager.migrate()`, so that I can manage database connection and schema lifecycle through a single unified object.
7. As a developer, I want failed migrations to roll back cleanly, so that the database is not left in an inconsistent or partially migrated state.
8. As a system operator, I want migration versions to be tracked in a dedicated schema version table, so that I can inspect the exact migration version of any database instance.
9. As a developer working across multiple services, I want each service repository to own its own migration scripts and history, so that multiple applications do not share or conflict on migration revisions.
10. As a test author, I want to run migrations programmatically against temporary test databases, so that integration tests run against exact production-like schemas.

## Implementation Decisions

- **Engine Selection**: Alembic is chosen as the standard migration engine for SQLAlchemy 2.0.
- **Dependency Management**: `alembic>=1.13.0` is added to optional database dependencies (`db`) and the project requirements.
- **Programmatic API Surface**:
  - A standalone function `apply_migrations(db_url: str, script_location: str = "migrations")` programmatically invokes Alembic's upgrade command to target revision `head`.
  - A helper method `migrate(self, script_location: str = "migrations")` is added to `DatabaseManager`, allowing consumers to invoke migrations directly through their database manager instance.
- **SQLite Batch Mode**: The Alembic environment configuration template explicitly activates `render_as_batch=True` when connecting to SQLite dialects.
- **Frozen Environment Detection**: Path resolution checks for frozen execution attributes (`sys.frozen`, `sys._MEIPASS`, or executable directories) to resolve script folders reliably whether running from source or from a packaged binary.
- **Responsibility Split**: Downstream projects store their migration revisions in their own repositories (defaulting to `./migrations/versions`). The shared library provides the runner, environment templates, and integration hooks.

## Testing Decisions

- **Definition of Good Tests**: Tests must verify observable behavior against real SQLite database instances rather than mocking internal Alembic functions. Tests must prove that invoking the migration runner upgrades an existing database, alters columns, and allows data queries through updated models.
- **Tested Modules**: `DatabaseManager.migrate()`, standalone `apply_migrations()`, and path resolution helper.
- **Testing Seam**: Single highest seam at `DatabaseManager.migrate(script_location)`. A test harness creates a temporary SQLite database, executes an initial migration, inserts test records, applies a subsequent schema migration with column changes, and confirms data integrity and schema updates.
- **Prior Art**: Follows existing integration test patterns in the repository that use SQLite files and test record lifecycles.

## Out of Scope

- Remote database backup and restore orchestration prior to migration.
- Multi-tenant database routing across separate migration trees.
- Graphical progress dialogs or UI indicators for long-running migrations (handled at application UI layer if needed).
- Custom schema linter or drift detection beyond standard Alembic checks.

## Further Notes

- Standard Alembic CLI commands (`alembic revision --autogenerate -m "..."`, `alembic upgrade head`) remain fully compatible with the generated configuration files.
