# 02: PCL 5 Raster Builder Implementation

**What to build:** Implement `PCL5RasterBuilder` inside `src/core_kit/devices/printer_pcl.py`. The builder must configure PJL headers for Standard and Custom page dimensions, handle image ingestion (converting to 1-bit monochrome), support image rotation (0°, 90°, 180°, 270°), apply automatic scaling (default 0.94) and centering, apply millimeter offsets (`shift_x_mm`, `shift_y_mm`), invert bitmap bits, and serialize pixel rows into standard PCL 5 raster commands (`\x1b*t300R`, `\x1b*r1A`, `\x1b*b...W`, `\x1b*rB`, `\x0c`).

**Blocked by:** 01-dependencies-and-scaffold

**Status:** resolved

- [x] Implement `PCL5RasterBuilder.__init__` supporting custom width/height (mm), standard paper sizes, tray, feed direction, and DPI
- [x] Implement `add_page(image, rotate=0, scale=0.94, shift_x_mm=0.0, shift_y_mm=0.0, auto_center=True)` with Pillow integration
- [x] Implement bitwise inversion and PCL 5 raster row packing (`\x1b*b{len}W` + row bytes)
- [x] Implement `build() -> bytes` returning PJL header, PCL raster body, and PJL footer
