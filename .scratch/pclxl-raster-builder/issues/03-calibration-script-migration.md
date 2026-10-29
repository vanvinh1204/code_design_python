# 03: Calibration example on PCLXLRasterBuilder + hardware acceptance

**What to build:** `print_test_label.py` builds its job with `PCLXLRasterBuilder`, with defaults scale 1.0, shift 0, tray none, rotate 90; the `PRINT_SCALE_X/Y` and `PRINT_SHIFT_X/Y` environment defaults are removed; `--tray`, `--scale`, `--scale-x/-y`, `--shift-x/-y`, `--rotate`, host IP, `--dry-run`, `--save-pcl` still work via `sys.argv` (no argparse). On-label and console texts that name PCL 5 / the old builder / old scale defaults are updated.

**Blocked by:** 01

**Status:** ready-for-agent (operator confirms the prints)

- [x] `--dry-run` produces the preview and a PCL XL payload
- [x] No environment-based compensation defaults remain
- [ ] Operator confirmed: `10.45.1.193 --tray TRAY2` border within ±2 mm of paper edge
- [ ] Operator confirmed: `10.45.1.191 --tray TRAY1` border within ±2 mm of paper edge
