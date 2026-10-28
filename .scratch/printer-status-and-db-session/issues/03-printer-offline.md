# 03: Report Printer Offline correctly

**What to build:** When the status query cannot reach the printer, `get_status()` returns a Printer Offline status (`is_online=False`, `is_ready=False`, reason in `display`) instead of misreporting it as online. The transport signals failure with a typed `PrinterConnectionError`; the fake fails the same way as the TCP adapter. `send(verify_ready=True)` aborts without transmitting when offline. See spec: `.scratch/printer-status-and-db-session/spec.md` (Status Probe seam).

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] `PrinterConnectionError` defined and exported from `core_kit.devices`
- [ ] `TcpSocketAdapter.query` raises `PrinterConnectionError` (chained) instead of returning an error string
- [ ] `FakeSocketTransport(should_fail=True).query` raises `PrinterConnectionError`
- [ ] `PrinterStatus.offline(reason)` classmethod
- [ ] `get_status()` catches the error and returns the offline status
- [ ] Test: offline status from a failing fake
- [ ] Test: `send(verify_ready=True)` transmits nothing when offline
- [ ] Full test suite green
