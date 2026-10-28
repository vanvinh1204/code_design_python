# Printer Status Probe Seam & Database Session Seam Specification

Status: ready-for-agent
Labels: ready-for-agent

## Problem Statement

After the `cb954fb` deepening refactor, two seams in `core_kit` still cause real failures:

1. **Database session seam is broken for FastAPI.** `DatabaseManager.get_db()` now returns the `@contextmanager` object produced by `session()` rather than a plain generator. Using `Depends(db.get_db)` or `Depends(db.session)` (as the docstring recommends) injects a `_GeneratorContextManager` into the endpoint instead of a `Session`. Three names (`session`, `session_scope`, `get_db`) exist, yet only the `with` usage works.
2. **Printer status is misreported and PJL knowledge is scattered.** When the network query fails, the TCP transport returns the string `"Connection Error: ..."`, which is fed to the PJL parser as if it were a printer response; the parser yields `is_online=True, is_ready=False`, so an unreachable printer is reported as *online with an error*. The fake transport returns `"Simulated Failure"`, a different shape from the real adapter. PJL knowledge is spread across the `PrinterStatus` dataclass (parsing), the TCP transport (PJL response terminators), and a dead 90-line duplicate of `PrinterStatus` in the PCL module. The real parse cases live only in an `examples/` script, outside pytest.

## Solution

1. Give `DatabaseManager` one internal session generator holding commit / rollback / close. `session()` and `session_scope()` wrap it as a context manager for `with` blocks; `get_db()` returns the generator itself for FastAPI dependency injection.
2. Concentrate the status protocol inside the **Status Probe**: query bytes, response terminators and parsing all live in `PJLStatusProbe`. The socket transport only moves bytes and signals failure with a typed `PrinterConnectionError`. `RawSocketPrinter.get_status()` turns that error into a **Printer Offline** status, so callers still always receive a `PrinterStatus`.

## User Stories

1. As a FastAPI developer, I want `Depends(db_manager.get_db)` to inject a real `Session`, so that my endpoints can query the database.
2. As a FastAPI developer, I want the injected session to commit when my endpoint succeeds, so that writes persist without boilerplate.
3. As a FastAPI developer, I want the injected session to roll back when my endpoint raises, so that partial writes never persist.
4. As a FastAPI developer, I want the injected session to be closed after the request, so that connections are not leaked.
5. As a PySide6 desktop developer, I want `with db_manager.session() as s:` to keep working unchanged, so that my worker threads need no migration.
6. As a maintainer of existing apps, I want `with db_manager.session_scope() as s:` to keep working, so that upgrading `core_kit` does not break me.
7. As a maintainer of `core_kit`, I want commit/rollback/close logic in exactly one place, so that a fix to transaction handling applies to every usage style.
8. As a developer reading the docstring, I want it to show the correct FastAPI usage, so that I do not copy a broken pattern.
9. As a warehouse app developer, I want `get_status()` to report an unreachable printer as offline, so that my UI does not tell operators the printer is online.
10. As a warehouse app developer, I want the offline status to carry the connection failure reason, so that I can show "timeout" vs "connection refused" to operators.
11. As a warehouse app developer, I want `get_status()` to never raise on connection failure, so that my existing status-polling code keeps working.
12. As a warehouse app developer, I want `send(verify_ready=True)` to abort without transmitting when the printer is offline, so that jobs are not silently lost.
13. As a software tester, I want `FakeSocketTransport` to fail the same way the TCP adapter fails, so that tests with the fake reflect production behaviour.
14. As a maintainer, I want all PJL status knowledge (query bytes, terminators, parsing) in `PJLStatusProbe`, so that a PJL change happens in one module.
15. As a future contributor adding another printer language, I want the transport to read until probe-declared terminators, so that I can add a new probe without editing the transport.
16. As a maintainer, I want the duplicate `PrinterStatus` in the PCL module deleted, so that there is only one definition to keep correct.
17. As an existing caller of `PrinterStatus.from_raw`, I want it to keep working with a `DeprecationWarning`, so that I have time to migrate to `PJLStatusProbe`.
18. As a maintainer, I want the known PJL parse cases (Ready, Paper Jam, Load Tray, Door Open) in pytest, so that regressions are caught in CI.
19. As a user importing `PrinterStatus` from the PCL module, I want that import to keep resolving, so that my code does not break.

## Implementation Decisions

### Database session seam
- `DatabaseManager` holds one private generator method yielding a `Session`: commit after the yield returns normally, rollback and re-raise on exception, always close.
- `session()` is that generator wrapped with `contextlib.contextmanager`; `session_scope()` remains an alias returning `session()`.
- `get_db()` returns the plain generator (not wrapped), suitable for FastAPI `Depends()`.
- Docstrings document: `with db.session()` for desktop/workers, `Depends(db.get_db)` for FastAPI.
- No FastAPI dependency is added.

### Status Probe seam
- `StatusProbe` protocol: `query_bytes: bytes`, `terminators: tuple[bytes, ...]`, `parse_response(raw: str) -> PrinterStatus`.
- `PJLStatusProbe` owns the full PJL parse logic (CODE, DISPLAY, ONLINE/STA, unready keywords), moved verbatim from `PrinterStatus.from_raw`; terminators are form-feed and the UEL sequence.
- `PrinterStatus` becomes a plain dataclass plus a classmethod `offline(reason: str)` returning `is_online=False, is_ready=False, display=reason`.
- `PrinterStatus.from_raw` stays as a deprecated alias: emits `DeprecationWarning` and delegates to `PJLStatusProbe().parse_response`.
- New exception `PrinterConnectionError` exported from `core_kit.devices`.
- `SocketTransport.query(host, port, query_payload, timeout, terminators)` returns the decoded response or raises `PrinterConnectionError`; it reads until any terminator appears, the connection closes, or the read times out. It holds no PJL bytes.
- `TcpSocketAdapter.query` wraps socket failures in `PrinterConnectionError` (chained). `send()` keeps returning `bool`.
- `FakeSocketTransport(should_fail=True).query` raises `PrinterConnectionError`; the fake records the terminators it received.
- `RawSocketPrinter.get_status()` catches `PrinterConnectionError` and returns `PrinterStatus.offline(reason)`. Per-call `probe` parameter with PJL default is unchanged.
- The duplicate `PrinterStatus` class and unused `socket` imports are removed from the PCL and TSPL modules; the PCL module keeps re-exporting `PrinterStatus` from the raw printer module.

## Testing Decisions

- Tests exercise public interfaces only; never assert on private attributes or socket internals.
- **Database**: against in-memory SQLite. `with session()` / `session_scope()` commit and rollback; `get_db()` driven directly as a generator (`next()` to obtain the session, a second `next()` raising `StopIteration` to commit — as FastAPI does; `close()` raises `GeneratorExit` and skips the commit — `throw()` to roll back) with no FastAPI install. Prior art: existing database manager tests.
- **Printer**: `RawSocketPrinter` with `FakeSocketTransport` — status for ready / jam / door open / load tray / offline; `send(verify_ready=True)` does not transmit when offline; probe terminators reach the transport. Prior art: existing raw printer tests.
- **Probe**: `PJLStatusProbe.parse_response` with raw PJL strings ported from the PCL example script.
- **Deprecation**: `PrinterStatus.from_raw` emits `DeprecationWarning` and returns the same result as the probe.
- `TcpSocketAdapter` is not unit tested (needs a real socket); it is covered by the hardware example scripts.

## Out of Scope

- A TSPL status probe (`ESC !?`) — deferred until a real app needs it and hardware is available.
- Moving the default probe into the `RawSocketPrinter` constructor.
- Changing `send()` return type.
- PCL raster builder changes (ADR-0002).
- Other review candidates (crypto/vault, migration path resolver, logging, api_client/serial seams).

## Further Notes

- Originated from the architecture review of 2026-10-28 (candidates #1 and #2).
- Glossary terms **Status Probe** and **Printer Offline** were added to `GLOSSARY.md`.
- Follow `.agents/rules/python.md`; keep Vietnamese comments/docstrings style.
