# 02: Programmatic Migration Runner and Frozen Path Support

**What to build:** A standalone programmatic migration runner `apply_migrations(db_url, script_location)` that allows applications (especially PySide6 desktop apps) to trigger migrations to `head` directly in Python code during application startup. The runner must include dynamic resource path resolution so that migrations continue to locate their revision directories correctly when bundled into standalone binary executables (such as via PyInstaller).

**Blocked by:** 01: Dependencies and Migration Template Scaffolding

**Status:** resolved

- [x] `apply_migrations` programmatically loads Alembic configuration and executes `upgrade head` without calling shell/CLI subprocesses
- [x] Path resolution logic correctly handles both standard Python execution and packaged environments (`sys.frozen` / `sys._MEIPASS`)
- [x] Database connection URLs are dynamically applied to the migration context
- [x] Errors during migration roll back transactions cleanly and raise informative exceptions
