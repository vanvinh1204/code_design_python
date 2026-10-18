# 04: Standalone Verification Test and Documentation

**What to build:** Create an automated verification script `examples/test_printer_pcl.py` that generates simulated 1-bit test images, configures both custom and standard pages, produces PCL raster streams, verifies PJL headers and raster byte integrity, and tests status string parsing. Update `README.md` with usage instructions and code examples for `core_kit.devices.printer_pcl`.

**Blocked by:** 03-network-printer-and-status

**Status:** resolved

- [x] Create `examples/test_printer_pcl.py` verifying PCL raster serialization, headers, and status parsing without requiring argparse
- [x] Verify test execution passes cleanly with zero errors
- [x] Update `README.md` Section 2.3 with developer documentation and code examples for PCL laser printing
