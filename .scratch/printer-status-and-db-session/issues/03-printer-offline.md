# 03: Report Printer Offline correctly

**What to build:** When the status query cannot reach the printer, `get_status()` returns a Printer Offline status (`is_online=False`, `is_ready=False`, reason in `display`) instead of misreporting it as online. The transport signals failure with a typed `PrinterConnectionError`; the fake fails the same way as the TCP adapter. `send(verify_ready=True)` aborts without transmitting when offline. See spec: `.scratch/printer-status-and-db-session/spec.md` (Status Probe seam).

**Blocked by:** 02

**Status:** resolved

- [x] `PrinterConnectionError` defined and exported from `core_kit.devices`
- [x] `TcpSocketAdapter.query` raises `PrinterConnectionError` (chained) instead of returning an error string
- [x] `FakeSocketTransport(should_fail=True).query` raises `PrinterConnectionError`
- [x] `PrinterStatus.offline(reason)` classmethod
- [x] `get_status()` catches the error and returns the offline status
- [x] Test: offline status from a failing fake
- [x] Test: `send(verify_ready=True)` transmits nothing when offline
- [x] Full test suite green
