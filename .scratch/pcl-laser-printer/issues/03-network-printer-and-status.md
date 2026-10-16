# 03: PCL Network Printer & Telemetry Implementation

**What to build:** Implement `PrinterStatus` and `PCLNetworkPrinter` inside `src/core_kit/devices/printer_pcl.py`. `PCLNetworkPrinter` connects to the printer via RAW TCP socket (port 9100) with configurable timeout and graceful socket shutdown. It queries hardware status using `@PJL INFO STATUS` and returns a structured `PrinterStatus` object (`is_online`, `is_ready`, `display`, `raw`).

**Blocked by:** 02-pcl5-raster-builder

**Status:** ready-for-agent

- [ ] Implement `PrinterStatus` dataclass with `from_raw` parser detecting "ONLINE", "DISPLAY", and readiness states
- [ ] Implement `PCLNetworkPrinter.__init__(host, port=9100, timeout=5.0)`
- [ ] Implement `PCLNetworkPrinter.get_status() -> PrinterStatus` querying `@PJL INFO STATUS`
- [ ] Implement `PCLNetworkPrinter.send(payload: bytes, verify_ready: bool = False) -> bool` with graceful socket shutdown
