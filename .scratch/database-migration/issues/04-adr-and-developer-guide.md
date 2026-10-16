# 04: ADR and Developer Usage Guide

**What to build:** Record the architectural decision for database migrations with Alembic in the repository's ADR directory and provide concrete usage examples in `examples/` demonstrating how both FastAPI web applications and PySide6 desktop applications integrate migration execution into their startup lifecycles.

**Blocked by:** 03: DatabaseManager Integration and E2E Testing

**Status:** resolved

- [x] ADR `docs/adr/0001-database-migrations-with-alembic.md` is created following standard ADR format
- [x] Example script demonstrates `DatabaseManager.migrate()` usage in standalone / desktop environments
- [x] Documentation outlines how to run standard Alembic CLI commands (`revision --autogenerate`, `upgrade head`)
