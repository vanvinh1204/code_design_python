# 01: RAW Socket Printing Transport and In-Memory Test Seam

**What to build:**
Create a unified, deep `RawSocketPrinter` transport class in `core_kit.devices` that transmits binary or text print payloads (`bytes` or `str`) across TCP port 9100 with configurable timeouts, retries, and graceful write-channel shutdown (`shutdown(SHUT_WR)`). Decouple hardware telemetry into `PJLStatusProbe` (interrogating `@PJL INFO STATUS`), and introduce `FakeSocketTransport` at the internal socket adapter seam to enable deterministic unit testing without a physical printer. Retain `PCLNetworkPrinter` and `TSPLNetworkPrinter` as backward-compatible subclasses/wrappers emitting `DeprecationWarning`.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] Implement `SocketTransport` protocol with `TcpSocketAdapter` and `FakeSocketTransport`
- [x] Implement `RawSocketPrinter` with `send(payload: bytes | str, verify_ready=False, probe=None)` and `get_status(probe=None)`
- [x] Implement `PJLStatusProbe` to parse status codes, display strings, and online flags from PJL responses
- [x] Refactor `PCLNetworkPrinter` and `TSPLNetworkPrinter` to delegate to `RawSocketPrinter` with `DeprecationWarning`
- [x] Write unit tests verifying payload transmission, error handling, and timeout behavior using `FakeSocketTransport`
