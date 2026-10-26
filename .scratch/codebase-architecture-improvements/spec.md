# Codebase Architecture Improvements Specification

Status: ready-for-agent
Labels: ready-for-agent

## Problem Statement

The `core_kit` shared foundation library powers both FastAPI web backends and PySide6 desktop applications across warehouse scanning, barcode printing, and operational workflows. As the codebase evolved, several foundational modules became shallow, tightly coupled, or architecturally fragmented:

1. **Fragmented RAW Socket Printing**: Laser printing (PCL 5) and label printing (TSPL) each implement their own separate network printer classes (`PCLNetworkPrinter` and `TSPLNetworkPrinter`). Both open raw TCP sockets to port 9100 with inconsistent method signatures (`send(bytes)` vs `send_raw(str)`), neither provides a clean test seam, and unit tests cannot verify print dispatch without real printer hardware or brittle monkeypatching.
2. **Leaky Authentication & Token Interface**: The `auth` module exposes loose functions (`create_access_token`, `decode_access_token`, `hash_password`, `verify_password`). Callers across routes and UI controllers are forced to manually pass `secret_key`, algorithm, and expiration times repeatedly, creating boilerplate, risking security drift, and complicating unit testing.
3. **Duplicated Database Session Management & Schema Divergence**: `DatabaseManager` maintains two completely duplicated methods (`get_db` and `session_scope`) with identical generator implementations. Furthermore, `create_tables()` exists alongside Alembic migrations, risking schema desynchronization when tables are created outside the revision graph, and `TimestampMixin` relies on deprecated `datetime.utcnow`, throwing warnings on Python 3.12+.
4. **Scattered Configuration Encryption & CLI Rule Violation**: Encryption of sensitive connection strings and passwords in `.env` files is split between low-level cryptographic functions and ad-hoc recursive dictionary traversal in settings. In addition, the developer CLI tool `encrypt_env.py` relies on `argparse`, which directly violates the repository rule prohibiting `argparse`, and lacks a programmatic interface for applications to safely update `.env` files.

## Solution

Deepen the four core modules to provide leverage for callers, locality for maintainers, and clean test seams across both web and desktop environments:

1. **Deep RAW Socket Printing Transport**:
   - Establish a unified, deep `RawSocketPrinter` transport module operating on port 9100.
   - Accept polymorphic print payloads (`bytes` or `str`, automatically encoding text formats like TSPL into bytes).
   - Encapsulate connection timeouts, retries, error logging, and graceful write-channel shutdown (`shutdown(SHUT_WR)`).
   - Separate hardware status interrogation into pluggable probes (such as `PJLStatusProbe` for laser engines).
   - Introduce an in-memory `FakeSocketTransport` test seam, allowing end-to-end print simulation in CI/CD without network access.
   - Preserve existing printer classes as thin deprecated adapters to ensure zero disruption for downstream applications.

2. **Deep AuthManager Module**:
   - Create a cohesive `AuthManager` that accepts cryptographic configuration (`secret_key`, `algorithm`, `default_expire_minutes`) once at initialization or via `AuthManager.from_settings(settings)`.
   - Expose an uncluttered, high-leverage interface: `issue_token()`, `verify_token()`, `hash_password()`, and `verify_password()`.
   - Keep low-level hashing helpers available at the module level for standalone use.
   - Eliminate repetitive secret passing across application endpoints and desktop controllers.

3. **Unified Database Session Seam & Schema Governance**:
   - Consolidate `get_db()` and `session_scope()` into a single standard `@contextmanager` method `session()`, directly usable with both FastAPI `Depends()` and PySide6 context blocks (`with db.session() as s:`).
   - Retain `session_scope()` as a non-breaking alias.
   - Automate schema alignment by integrating migration verification into `DatabaseManager`, promoting Alembic migrations over raw table creation.
   - Upgrade `TimestampMixin` to use timezone-aware UTC timestamps (`now_utc`), eliminating Python 3.12+ deprecation warnings.

4. **Encapsulated ConfigVault Module**:
   - Unify configuration encryption, token detection (`enc:`), and decryption into a deep `ConfigVault` module.
   - Provide programmatic methods: `encrypt()`, `decrypt()`, `decrypt_mapping()`, and `update_env_file()` for safe in-place `.env` modification preserving comments.
   - Refactor the CLI tool to use `sys.argv` argument handling, strictly eliminating all `argparse` dependencies.
   - Maintain 100% backward compatibility for all utility functions in `core_kit.utils.crypto`.

## User Stories

1. As a warehouse application developer, I want to send print payloads through a single `RawSocketPrinter` interface, so that I don't have to manage different socket implementations for PCL laser printers and TSPL barcode printers.
2. As a software tester, I want an in-memory `FakeSocketTransport` seam, so that CI/CD pipelines can verify print payload dispatch and error recovery without physical printer hardware.
3. As a developer using a PCL laser printer, I want to query PJL hardware status via a dedicated probe, so that I know if the printer has a paper jam or open door before transmitting large jobs.
4. As a developer using a TSPL label printer, I want text commands to be automatically encoded to bytes when sent, so that I do not need manual encoding conversions at call sites.
5. As a maintainer of existing downstream apps (such as `whsx-scan-web`), I want existing imports of `PCLNetworkPrinter` and `TSPLNetworkPrinter` to continue functioning with deprecation notices, so that my production deployment does not break upon upgrading `core_kit`.
6. As a backend API developer, I want to issue JWT access tokens via `auth_manager.issue_token()`, so that I don't have to repeatedly look up and inject the application's `secret_key` and algorithm in every endpoint.
7. As a security engineer, I want token decoding and claim verification centralized in `AuthManager`, so that expiration checks and token validation rules are enforced uniformly across the entire system.
8. As a desktop application developer, I want to verify user passwords using `auth_manager.verify_password()`, so that password validation is consistent between desktop authentication screens and backend services.
9. As a developer writing tests for protected routes, I want to initialize `AuthManager` with test keys or substitute it easily, so that I don't need complex monkeypatching of third-party JWT libraries.
10. As a FastAPI backend developer, I want to inject database sessions using `db: Session = Depends(db_manager.session)`, so that my endpoints receive a transactional session that auto-commits on success and rolls back on failure.
11. As a PySide6 desktop developer, I want to manage database transactions using `with db_manager.session() as session:`, so that worker threads handle transactions cleanly without manual commit/rollback boilerplate.
12. As a database maintainer, I want schema creation to go through Alembic migrations by default, so that production databases do not diverge from version control schemas.
13. As a Python 3.12 developer, I want `TimestampMixin` models to create UTC timestamps without triggering `datetime.utcnow` deprecation warnings, so that test logs remain clean and future-proof.
14. As a DevOps engineer, I want a single `ConfigVault` module to handle `.env` decryption and encryption, so that secret token parsing logic is not scattered across settings and utilities.
15. As a developer running the environment encryption CLI, I want `encrypt_env` to run without `argparse`, so that the codebase strictly adheres to the project's dependency and architectural rules.
16. As a desktop installer author, I want `ConfigVault.update_env_file()` to write encrypted database passwords directly into `.env`, so that automated setup scripts do not require manual text editing or external tools.
17. As an open-source contributor, I want automated unit tests in `tests/` covering printers, authentication, database sessions, and configuration, so that regressions are caught before release.

## Implementation Decisions

### 1. RAW Socket Printing Module
- **Module Structure**: Place `RawSocketPrinter` and `PJLStatusProbe` under the devices namespace.
- **Interface Contract**:
  - `RawSocketPrinter(host: str, port: int = 9100, timeout: float = 5.0, transport_adapter: Optional[SocketTransport] = None)`
  - `send(payload: Union[bytes, str], verify_ready: bool = False, probe: Optional[StatusProbe] = None) -> bool`
  - `get_status(probe: Optional[StatusProbe] = None) -> PrinterStatus`
- **Socket Adapter Seam**: Define an internal transport protocol with two concrete adapters:
  - `TcpSocketAdapter`: Standard TCP network connection with `socket.SHUT_WR` graceful teardown.
  - `FakeSocketTransport`: In-memory recording adapter holding sent bytes buffer and simulated status.
- **Backward Compatibility**: `PCLNetworkPrinter` and `TSPLNetworkPrinter` subclasses/wrappers inherit from or delegate to `RawSocketPrinter`, pre-configuring the default probe and issuing `DeprecationWarning`.

### 2. Auth Module
- **Module Structure**: Introduce `AuthManager` under the auth namespace.
- **Interface Contract**:
  - `AuthManager(secret_key: str, algorithm: str = "HS256", default_expire_minutes: int = 1440)`
  - `@classmethod from_settings(cls, settings: Any) -> AuthManager`
  - `issue_token(subject: Union[str, int], claims: Optional[dict] = None, expires_delta: Optional[timedelta] = None) -> str`
  - `verify_token(token: str) -> Optional[dict]`
  - `hash_password(plain_password: str) -> str`
  - `verify_password(plain_password: str, hashed_password: str) -> bool`
- **Standalone Functions**: Keep `hash_password()` and `verify_password()` as standalone module functions for lightweight use.

### 3. Database Lifecycle & Session Seam
- **Module Structure**: Update `DatabaseManager` in the database session namespace.
- **Interface Contract**:
  - Single `@contextmanager` method: `session() -> Generator[Session, None, None]`.
  - `session_scope()` retained as an alias calling `session()`.
  - Deprecate or soft-deprecate raw `create_tables()` in favor of `auto_migrate: bool = False` or `migrate()` to ensure alignment with ADR-0001.
- **Model Datetime Upgrade**: Update `TimestampMixin` in `base_model` to supply `default=now_utc` and `onupdate=now_utc` utilizing `datetime.now(timezone.utc)`.

### 4. ConfigVault Module
- **Module Structure**: Introduce `ConfigVault` under the config/crypto namespace.
- **Interface Contract**:
  - `encrypt(text: str, key: Optional[Union[str, bytes]] = None) -> str`
  - `decrypt(val: Optional[str], key: Optional[Union[str, bytes]] = None) -> str`
  - `decrypt_mapping(data: Any) -> Any`
  - `update_env_file(env_path: Union[str, Path], key: str, value: str, encrypt: bool = True) -> bool`
- **CLI Implementation**: Rewrite `tools/encrypt_env.py` to parse positional arguments and flags directly from `sys.argv`, removing all imports of `argparse`.

## Testing Decisions

- **Good Test Philosophy**: Tests must exercise external behavior through the public interfaces of modules across their highest seams, never asserting on private attributes or internal socket state.
- **Unit Test Coverage for Devices**:
  - Test `RawSocketPrinter.send()` using `FakeSocketTransport` with byte payloads, string payloads, timeout handling, and connection error handling.
  - Test `PJLStatusProbe` response parsing with known raw PJL strings ("00 READY", "DOOR OPEN", "PAPER JAM").
  - Test that deprecated `PCLNetworkPrinter` and `TSPLNetworkPrinter` correctly emit `DeprecationWarning` while successfully dispatching payloads.
- **Unit Test Coverage for Auth**:
  - Test `AuthManager.issue_token()` and `verify_token()` with valid tokens, expired tokens, tampered signatures, and custom claims.
  - Test password hashing and verification matches across repeated operations.
- **Unit Test Coverage for Database**:
  - Test `db_manager.session()` context manager in a transactional workflow against in-memory SQLite (`sqlite:///:memory:`).
  - Verify that exceptions inside a session block trigger automatic rollback.
  - Verify that `TimestampMixin` stores timezone-aware timestamps without deprecation warnings.
- **Unit Test Coverage for ConfigVault**:
  - Test round-trip encryption/decryption of connection URLs and plain passwords.
  - Test `update_env_file()` with existing `.env` content, verifying that comments and surrounding variables are preserved intact.
  - Test `encrypt_env.py` execution via `sys.argv` emulation without `argparse`.
- **Prior Art**: Existing tests in `tests/test_crypto_env.py` and diagnostic scripts in `examples/test_printer_pcl.py` provide reference behaviors and test fixtures.

## Out of Scope

- Introducing new third-party dependencies outside the currently approved packages.
- Redesigning `PCL5RasterBuilder` page layout math or PJL escape generation (which is already proven and verified on physical hardware per ADR-0002).
- Rewriting downstream business logic inside `whsx-scan-web` or desktop UI applications during this library refactoring.
- Modifying Alembic migration history or table definitions.

## Further Notes

- The implementation will proceed sequentially: Devices (RAW Socket Printing) &rarr; Auth &rarr; Database &rarr; ConfigVault.
- All code changes must strictly follow `.agents/rules/python.md` and preserve existing Vietnamese comments and docstrings.
