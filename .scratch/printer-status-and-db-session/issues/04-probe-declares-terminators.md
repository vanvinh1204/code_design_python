# 04: Status Probe declares response terminators

**What to build:** `PJLStatusProbe` declares `terminators` (form feed and UEL). `RawSocketPrinter.get_status()` passes them to `transport.query(..., terminators=...)`, and the TCP adapter reads until any terminator, connection close, or timeout. The transport no longer contains PJL bytes. See spec: `.scratch/printer-status-and-db-session/spec.md` (Status Probe seam).

**Blocked by:** 02, 03 (03 also edits `SocketTransport.query`)

**Status:** ready-for-agent

- [ ] `StatusProbe` protocol includes `terminators: tuple[bytes, ...]`
- [ ] `PJLStatusProbe.terminators` set; no PJL bytes remain in the transport adapters
- [ ] `SocketTransport.query` accepts `terminators`; TCP adapter stops on any of them
- [ ] `FakeSocketTransport` records the terminators it received
- [ ] Test: probe terminators reach the transport via `get_status()`
- [ ] Full test suite green
