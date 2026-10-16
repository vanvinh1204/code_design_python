# 01: Dependencies and Migration Template Scaffolding

**What to build:** Add `alembic>=1.13.0` to the project's dependency manifest and provide a scaffolding generator that sets up a standardized Alembic environment for consumer applications. The generated environment must link directly with `Base.metadata` and automatically configure `render_as_batch=True` for SQLite databases so that subsequent migrations support table and column alterations without syntax errors.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] `alembic>=1.13.0` is declared in database optional dependencies and requirements
- [x] Scaffolding utility generates valid `alembic.ini` and `env.py` template files
- [x] The generated `env.py` binds to `core_kit.database.Base.metadata`
- [x] SQLite batch mode (`render_as_batch=True`) is enabled for SQLite connections in the template
