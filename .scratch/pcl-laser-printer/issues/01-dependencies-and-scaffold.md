# 01: Dependencies Configuration and Module Exports

**What to build:** Update project configuration files (`pyproject.toml` and `requirements.txt`) to declare `pillow>=10.0.0` within optional dependencies under `devices` and `all`. Prepare package exports in `src/core_kit/devices/__init__.py` for the upcoming classes (`PCL5RasterBuilder`, `PCLNetworkPrinter`, `PrinterStatus`).

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] Declare `pillow>=10.0.0` in `[project.optional-dependencies]` under `devices` and `all` in `pyproject.toml`
- [x] Add `pillow>=10.0.0` to `requirements.txt` under devices group
- [x] Update `src/core_kit/devices/__init__.py` to export `PCL5RasterBuilder`, `PCLNetworkPrinter`, and `PrinterStatus`
