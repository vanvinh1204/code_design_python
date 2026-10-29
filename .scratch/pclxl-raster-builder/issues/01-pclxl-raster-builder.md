# 01: PCLXLRasterBuilder: PCL XL raster job with CustomMediaSize

**What to build:** A pure-logic `PCLXLRasterBuilder`, exported from `core_kit.devices`, whose `build()` returns a PJL-wrapped PCL XL raster job that declares the page size via `CustomMediaSize` (mm) for every paper (CUSTOM and standard names resolved to mm). Same builder shape as `PCL5RasterBuilder` (`add_page` / `build` / `reset`, chaining), with no `feed_direction`. See spec "Implementation Decisions" and the working encoder in `evidence/paper_probe.py` (`job_pclxl`).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] PJL header: job name, `@PJL SET MEDIASOURCE = <tray>` only when `tray` is given (verbatim), `@PJL ENTER LANGUAGE = PCLXL`; no paper-size/feed/duplex variables; UEL/EOJ footer
- [ ] PCL XL stream: `) HP-PCL XL;2;0` header, BeginSession/OpenDataSource/.../CloseDataSource/EndSession as in the spec
- [ ] `BeginPage` carries `CustomMediaSize` (real32_xy mm) + `eMillimeter`, `MediaSource = eDefaultSource`, portrait
- [ ] Full page canvas sent as one 1-bit gray image, rows padded with white to 4-byte boundary, uncompressed
- [ ] `add_page(image, rotate=0, scale=1.0, shift_x_mm=0.0, shift_y_mm=0.0, auto_center=True)`: rotate → scale (float or (x, y)) → place on page canvas, centred, shifted
- [ ] Multiple pages in one session; `reset()` clears pages
- [ ] `ValueError` for: no pages, non-positive scale, bad scale tuple, unsupported rotation, unknown paper name, CUSTOM without dimensions
- [ ] Byte-level unit tests for all of the above; full test suite green
