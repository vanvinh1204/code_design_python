# 01: `get_db()` works with FastAPI `Depends()`

**What to build:** `Depends(db_manager.get_db)` injects a real `Session` that commits on success, rolls back on error and is always closed. `with db.session()` and `with db.session_scope()` keep working. Commit/rollback/close logic lives in one internal generator. Docstrings show the correct usage. See spec: `.scratch/printer-status-and-db-session/spec.md` (Database session seam).

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] `get_db()` returns a plain generator yielding a `Session`
- [x] `session()` / `session_scope()` share the same internal generator via `contextmanager`
- [x] Test: drive `get_db()` with `next()` + a second `next()` (StopIteration, as FastAPI does) — row committed (note: `close()` raises GeneratorExit at the yield and would skip the commit)
- [x] Test: drive `get_db()` with `throw()` — row rolled back, exception propagates
- [x] Docstring recommends `Depends(db.get_db)` for FastAPI
- [x] Full test suite green
