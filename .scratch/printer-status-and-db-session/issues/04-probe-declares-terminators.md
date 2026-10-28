# 04: Status Probe declares response terminators

**What to build:** `PJLStatusProbe` declares `terminators` (form feed and UEL). `RawSocketPrinter.get_status()` passes them to `transport.query(..., terminators=...)`, and the TCP adapter reads until any terminator, connection close, or timeout. The transport no longer contains PJL bytes. See spec: `.scratch/printer-status-and-db-session/spec.md` (Status Probe seam).

**Blocked by:** 02, 03 (03 also edits `SocketTransport.query`)

**Status:** resolved

- [x] `StatusProbe` protocol includes `terminators: tuple[bytes, ...]`
- [x] `PJLStatusProbe.terminators` set; no PJL bytes remain in the transport adapters
- [x] `SocketTransport.query` accepts `terminators`; TCP adapter stops on any of them
- [x] `FakeSocketTransport` records the terminators it received
- [x] Test: probe terminators reach the transport via `get_status()`
- [x] `FakeSocketTransport(query_fails=True)` fails only `query`; test "send(verify_ready=True) transmits nothing when offline" uses it so it fails if `send()` ignores `verify_ready` (coordinator addendum, closes the ticket 03 gap)
- [x] Full test suite green
