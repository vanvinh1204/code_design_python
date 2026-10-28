# 01: `get_db()` works with FastAPI `Depends()`

**What to build:** `Depends(db_manager.get_db)` injects a real `Session` that commits on success, rolls back on error and is always closed. `with db.session()` and `with db.session_scope()` keep working. Commit/rollback/close logic lives in one internal generator. Docstrings show the correct usage. See spec: `.scratch/printer-status-and-db-session/spec.md` (Database session seam).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `get_db()` returns a plain generator yielding a `Session`
- [ ] `session()` / `session_scope()` share the same internal generator via `contextmanager`
- [ ] Test: drive `get_db()` with `next()` + `close()` — row committed
- [ ] Test: drive `get_db()` with `throw()` — row rolled back, exception propagates
- [ ] Docstring recommends `Depends(db.get_db)` for FastAPI
- [ ] Full test suite green
