# 02: CLI Driver, PCL Raster Pipeline & Socket Dispatch

**What to build:** Implement the complete end-to-end execution pipeline in `examples/print_test_label.py`. Wire the generated calibration image into `PCL5RasterBuilder` (Custom 102x148mm, Tray 1, Short-Edge feed, 90° rotation, 0.94 scale factor). Implement command-line handling using raw `sys.argv` (strictly avoiding `argparse`) supporting `--dry-run`, `--save-pcl <path>`, and custom printer IP overrides. Connect `PCLNetworkPrinter` with pre-flight status checking (`get_status()`) and graceful socket transmission to port 9100.

**Blocked by:** 01: Calibration Label Canvas & Layout Generator

**Status:** resolved

- [x] Connects calibration image to `PCL5RasterBuilder` with custom decal settings ($102 \times 148\text{ mm}$, Short-Edge feed, 90° CW rotation, 0.94 scale, auto-centering)
- [x] Parses `sys.argv` without `argparse`, supporting `--dry-run`, `--save-pcl <path>`, and target IP argument
- [x] In non-dry-run mode, interrogates printer status via `PCLNetworkPrinter.get_status()` before sending, aborting with a clear error if the printer reports not ready (jam or empty tray)
- [x] Sends PCL 5 raster payload over TCP socket port 9100 with graceful shutdown
- [x] Supports dumping the compiled PCL bytes to file when `--save-pcl` is provided
- [x] Verified to run cleanly with zero errors in `--dry-run` mode
