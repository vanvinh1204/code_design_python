# 05: Comprehensive Test Suite & Examples Migration

**What to build:**
Consolidate and migrate informal testing scripts in `examples/` (`test_devices.py`, `test_printer_pcl.py`, `test_database.py`, `test_auth.py`, `test_migration.py`, `test_utils.py`) into formal, automated `pytest` suites under `tests/`. Verify that all tests pass cleanly with 100% green status and zero deprecation warnings on Python 3.12+.

**Blocked by:** 01-raw-socket-printer, 02-auth-manager, 03-database-session-lifecycle, 04-config-vault

**Status:** ready-for-agent

- [ ] Add `tests/test_devices_raw_printer.py` testing `RawSocketPrinter`, `PJLStatusProbe`, and backward compatibility
- [ ] Add `tests/test_auth_manager.py` testing `AuthManager` token lifecycle and password verification
- [ ] Add `tests/test_database_manager.py` testing `db_manager.session()` and model timestamp behavior
- [ ] Add `tests/test_config_vault.py` testing `ConfigVault` and `update_env_file()`
- [ ] Run full `pytest` suite ensuring all tests pass cleanly with zero warnings
