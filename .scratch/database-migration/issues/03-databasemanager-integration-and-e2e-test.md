# 03: DatabaseManager Integration and E2E Testing

**What to build:** Integrate the migration execution capability directly into the core `DatabaseManager` class via a `migrate(self, script_location)` method and export all migration helpers through the `core_kit.database` module. Validate the entire migration workflow with an end-to-end integration test (testing seam) that spins up an SQLite database, migrates an initial schema, inserts sample records, migrates to an altered schema using SQLite batch mode, and verifies schema updates and data preservation.

**Blocked by:** 02: Programmatic Migration Runner and Frozen Path Support

**Status:** resolved

- [x] `DatabaseManager.migrate()` is available on database manager instances and defaults to the standard migration directory
- [x] Top-level `core_kit.database` exports the migration helper methods
- [x] Integration tests exercise the highest seam (`db_manager.migrate()`) against a real SQLite database file
- [x] Tests verify schema updates, column alterations in SQLite batch mode, and existing record retention across revisions
