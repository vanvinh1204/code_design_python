# 02: Move PJL status parsing into the Status Probe (prefactor)

**What to build:** `PJLStatusProbe.parse_response` owns all PJL parse logic; `PrinterStatus` is a plain dataclass. `PrinterStatus.from_raw` becomes a deprecated alias delegating to the probe. The dead duplicate `PrinterStatus` in the PCL module and unused `socket` imports in PCL/TSPL modules are removed. `get_status()` behaviour is unchanged. See spec: `.scratch/printer-status-and-db-session/spec.md` (Status Probe seam).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Parse logic moved verbatim into `PJLStatusProbe.parse_response`
- [ ] `PrinterStatus.from_raw` emits `DeprecationWarning` and returns the probe's result
- [ ] Duplicate `PrinterStatus` removed from the PCL module; `from core_kit.devices.printer_pcl import PrinterStatus` still resolves
- [ ] Unused `socket` imports removed from PCL and TSPL modules
- [ ] Pytest cases ported from the PCL example script: Ready, Paper Jam, Load Tray, Door Open (via `parse_response`)
- [ ] Full test suite green
