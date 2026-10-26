# 03: Unified DatabaseManager Session Seam & Timezone-Aware Models

**What to build:**
Unify session management in `DatabaseManager` into a single `@contextmanager` generator method `session()`, directly usable for both FastAPI dependency injection (`Depends(db.session)`) and PySide6 context blocks (`with db.session() as s:`), eliminating duplicated generator code. Keep `session_scope()` as an alias. Ensure schema management respects Alembic migrations per ADR-0001, providing warnings or deprecation notices on raw `create_tables()` calls. Upgrade `TimestampMixin` in `core_kit.database.base_model` from deprecated `datetime.utcnow` to `now_utc` (`datetime.now(timezone.utc)`), eliminating Python 3.12+ warnings.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] Implement `DatabaseManager.session()` as the unified transactional context manager
- [x] Retain `session_scope()` and `get_db()` as backward-compatible aliases pointing to `session()`
- [x] Align `DatabaseManager` with Alembic migration lifecycle and deprecate bare `create_tables`
- [x] Upgrade `TimestampMixin` fields to `now_utc` timezone-aware timestamps
- [x] Write unit tests for `session()` transaction commit, exception rollback, and timezone-aware model storage
