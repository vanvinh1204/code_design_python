# PCL XL Raster Builder (Custom Media Size Across Printer Families) Specification

Status: ready-for-agent

## Problem Statement

Operators print 102 x 148 mm calibration/decal labels through `core_kit` by streaming **PCL 5 Raster** over **RAW Socket Printing** (port 9100). On the Fujifilm ApeosPort Print 4020SD (10.45.1.191) the label prints correctly, but on the Fujifilm ApeosPrint 4620 SDW (10.45.1.193) the same job prints shifted ~62 mm off the paper, as if the printer were laying out a standard sheet instead of the custom label.

Root cause, confirmed on hardware (evidence in `evidence/`):

- PCL 5 has no command that carries custom page dimensions. `ESC&l101A` only says "custom"; the actual 102 x 148 mm size travels in vendor-specific **PJL** variables.
- The 4020SD runs a Lexmark-family firmware that understands `LCUSTOMPAPERWIDTH/HEIGHT`, and its cassette is set to `CUSTOM` (Universal), so it honours the job's size.
- The 4620 SDW runs a Brother-family firmware (`84U-LB4`) that exposes none of the `LCUSTOMPAPER*` / `PAPERWIDTH` variables and has no `PAPER=CUSTOM`. It silently falls back to the size configured for the cassette (`INTRAY2SIZE=EXECUTIVE`), and offers no "Universal" option on its panel.
- The current hand-tuned defaults (scale 0.89/0.94, shift_x -5 mm) were calibrated against the 4020SD and mask layout mismatches rather than fixing them.

Test prints on the 4620 SDW with the tray left at Executive:

| Probe | Payload | Result |
|---|---|---|
| PA1 | PCL 5 + `ESC&l74A` + `@PJL SET PAPER = P4X6` | shifted (wrong) |
| PA2 | PCL XL, `BeginPage` with `CustomMediaSize` 102 x 148 mm | **correct** |
| PA3 | PostScript `setpagedevice /PageSize [289 420]` | shifted (wrong) |

PA2 was then sent unchanged to the 4020SD and also printed **correctly**. PCL XL `CustomMediaSize` is therefore the one page-size mechanism proven on both printer families, without any printer reconfiguration and without scale/shift compensation.

## Solution

Add a new pure-logic builder, `PCLXLRasterBuilder`, that produces a PJL-wrapped **PCL XL** raster job whose page size is always declared via `CustomMediaSize` in millimetres. It keeps the familiar builder shape (`add_page`, `build`, `reset`) so callers migrate by swapping the class and dropping obsolete arguments. Labels print edge-accurate on both the 4020SD and the 4620 SDW with default settings (no scale, no shift).

`PCL5RasterBuilder` stays for backward compatibility (released in 0.2.0) but is marked deprecated. The calibration example, README and other examples move to the new builder. ADR-0003 records the switch and supersedes ADR-0002.

## User Stories

1. As an operator, I want a 102 x 148 mm label to print aligned on the ApeosPrint 4620 SDW, so that labels are usable without manual re-feeding or reprinting.
2. As an operator, I want the same job to keep printing aligned on the ApeosPort Print 4020SD, so that switching builders does not regress the printer that already works.
3. As an operator, I want correct output without changing the tray paper-size setting on the printer, so that I do not depend on panel configuration that some models (4620 SDW) cannot express.
4. As a backend developer, I want a `PCLXLRasterBuilder` with the same `add_page` / `build` / `reset` shape as `PCL5RasterBuilder`, so that migrating is a class swap, not a rewrite.
5. As a backend developer, I want to declare paper as `CUSTOM` with width/height in mm, so that I can print any label stock.
6. As a backend developer, I want to name standard sizes (A4, A5, A6, Letter, ...) and have them resolved to millimetres, so that I do not memorise dimensions.
7. As a backend developer, I want every page size, standard or custom, to be sent through the one hardware-proven `CustomMediaSize` path, so that there is no untested branch.
8. As a backend developer, I want defaults of scale 1.0, shift 0 mm and auto-centre on, so that a correctly sized image prints edge-accurate with no tuning.
9. As a backend developer, I want to keep optional `scale` (uniform or per-axis), `shift_x_mm`, `shift_y_mm` and `rotate`, so that I can fine-tune a 1-2 mm mechanical offset on a specific machine.
10. As a backend developer, I want rotation in 90-degree steps, so that landscape-designed content fits a short-edge-fed label.
11. As a backend developer, I want to pass the tray as the printer's own PJL `MEDIASOURCE` name (e.g. `TRAY2` on the 4620 SDW, `TRAY1` on the 4020SD), so that tray naming differences between printer families are handled by per-printer configuration, not hard-coded mapping.
12. As a backend developer, I want `tray=None` (default) to send no tray selection at all, so that the printer uses its own default source.
13. As a backend developer, I want the builder to emit no PJL paper-size or feed-direction variables, so that vendor-specific variables cannot conflict with the PCL XL page size.
14. As a backend developer, I want the builder to accept any Pillow image and convert it to 1-bit, so that I can render labels in whatever mode is convenient.
15. As a backend developer, I want multiple pages per job, so that a batch of labels goes out as one print job.
16. As a backend developer, I want a job name in the PJL header, so that jobs are identifiable on the printer panel and logs.
17. As a backend developer, I want `build()` to be pure (no network, no filesystem), so that payloads can be unit-tested in CI without hardware.
18. As a backend developer, I want clear `ValueError`s for invalid inputs (non-positive scale, unsupported rotation, unknown paper name, missing custom dimensions, building with no pages), so that misuse fails fast.
19. As a backend developer, I want `PCL5RasterBuilder` to keep working but warn that it is deprecated and cannot declare custom sizes on Brother-family firmware, so that existing callers are not broken but are steered to the new builder.
20. As an operator, I want `print_test_label.py` to use the new builder with no compensation by default, so that the calibration sheet shows the true alignment of the printer.
21. As an operator, I want `print_test_label.py` to accept `--tray`, `--scale`, `--scale-x/-y`, `--shift-x/-y`, `--rotate` and a host IP, so that I can calibrate any printer from the command line.
22. As an operator, I want `print_test_label.py` to stop reading the old `PRINT_SCALE_*` / `PRINT_SHIFT_*` environment defaults, so that stale 4020SD compensation does not silently distort other printers.
23. As an operator, I want `print_test_label.py` to default to no tray selection, so that it does not pick the wrong tray on printers with different tray numbering.
24. As a maintainer, I want ADR-0003 to explain why PCL XL replaced PCL 5 (with the PJL `INFO` evidence and the PA1/PA2/PA3 results), so that nobody reverts to PCL 5 custom sizing.
25. As a maintainer, I want the glossary to define **PCL XL**, **CustomMediaSize** and **Printer Family**, so that future specs use consistent vocabulary.
26. As a maintainer, I want the CHANGELOG `Unreleased` section to list the new builder and the deprecation, so that the next release notes are accurate.
27. As a maintainer, I want a golden-byte test locking the hardware-verified PCL XL payload, so that refactors cannot silently change what the printers accept.

## Implementation Decisions

- **New module class `PCLXLRasterBuilder`** in the existing `core_kit.devices` printer module, exported from `core_kit.devices`. `PCLNetworkPrinter`, `PrinterStatus` and the PJL **Status Probe** are unchanged; PCL XL payloads are sent through the same transport.
- **Constructor**: `paper_size` (`"CUSTOM"` or a standard name), `width_mm`, `height_mm` (required for `CUSTOM`), `tray: str | None = None`, `dpi: int = 300`, `job_name: str`. There is **no `feed_direction`** parameter.
- **`add_page(image, rotate=0, scale=1.0, shift_x_mm=0.0, shift_y_mm=0.0, auto_center=True)`**: same layout pipeline as today: rotate, then scale (uniform float or `(x, y)` tuple), then paste onto a white page canvas sized from the paper dimensions at `dpi`, centred if `auto_center`, then offset by the shift. Returns `self` for chaining. `reset()` clears pages.
- **Paper size**: always declared with `CustomMediaSize` (real32_xy, millimetres) plus `CustomMediaSizeUnits = eMillimeter`. Standard names resolve to mm via the existing standard-size table. The `MediaSize` enum is **not** used (no hardware evidence for it; A4 test prints are explicitly not part of acceptance).
- **PJL envelope**: UEL + `@PJL JOB NAME`, then `@PJL SET MEDIASOURCE = <tray>` only when `tray` is given, then `@PJL ENTER LANGUAGE = PCLXL`. Footer: UEL + `@PJL EOJ` + UEL. No `PAPER`, `PAPERWIDTH/LENGTH`, `LCUSTOMPAPER*`, `SHORTEDGEFEED`, `FEEDDIR` or `DUPLEX` variables.
- **PCL XL stream**, little-endian binding, as proven by probe PA2 (`evidence/paper_probe.py`, function `job_pclxl`):
  - Stream header `) HP-PCL XL;2;0;...` + LF.
  - `BeginSession`: `UnitsPerMeasure = (dpi, dpi)`, `Measure = eInch`, `ErrorReport = eErrorPage`.
  - `OpenDataSource`: `SourceType = eDefaultDataSource`, `DataOrg = eBinaryLowByteFirst`.
  - Per page: `BeginPage` (`Orientation = ePortrait`, `MediaSource = eDefaultSource`, `CustomMediaSize`, `CustomMediaSizeUnits`), `SetColorSpace eGray`, `SetCursor (0,0)`, `BeginImage` (`eDirectPixel`, `e1Bit`, source width/height = page canvas in pixels, destination size = same), `ReadImage` (`StartLine 0`, `BlockHeight = height`, `eNoCompression`, uint32 data length), `EndImage`, `EndPage (PageCopies 1)`.
  - `CloseDataSource`, `EndSession`.
  - The full page canvas is sent as one image (white = 1, black = 0, matching Pillow mode `1`), each row padded with white to a 4-byte boundary.
- **Tray**: always `MediaSource = eDefaultSource` inside PCL XL; tray choice lives only in PJL `MEDIASOURCE`, passed through verbatim. Tray names are per-printer configuration owned by the caller (4620 SDW cassette = `TRAY2`, 4020SD cassette = `TRAY1`).
- **No compression** in this iteration (about 260 KB per 102 x 148 mm page at 300 dpi). RLE (`eRLECompression`) is a possible later improvement.
- **Deprecation**: `PCL5RasterBuilder` emits a `DeprecationWarning` on construction and its docstring states it cannot declare custom sizes on Brother-family firmware. Behaviour is otherwise untouched.
- **Calibration example**: switches to `PCLXLRasterBuilder`; defaults become scale 1.0, shift 0, tray none, rotate 90; removes the `PRINT_SCALE_X/Y` and `PRINT_SHIFT_X/Y` environment defaults; keeps the `sys.argv` parser (no argparse, per project rule). Texts that name the builder or "PCL 5" are updated.
- **Docs**: ADR-0003 "PCL XL raster with CustomMediaSize" supersedes ADR-0002 (ADR-0002 status becomes "superseded by ADR-0003"). The glossary gains **PCL XL**, **CustomMediaSize** and **Printer Family** (Lexmark-family vs Brother-family firmware, identified via `@PJL INFO ID` / variable naming). README usage and the other examples move to the new builder. CHANGELOG gets an `Unreleased` entry. No version bump.

## Testing Decisions

- **Seam**: `PCLXLRasterBuilder.build()` returning `bytes`. It is the highest seam, the same seam the existing builder tests use, and needs no network or new seam. Tests assert only on the public output bytes and raised errors, never on private helpers.
- **Behaviour tests** (TDD, red-green):
  - The PJL header contains the job name and `ENTER LANGUAGE = PCLXL`, and contains no paper-size or feed variables.
  - `MEDIASOURCE` appears verbatim when `tray` is given and is absent when `tray=None`.
  - The PCL XL stream header is present after the PJL header.
  - `CustomMediaSize` encodes the requested mm (e.g. 102.0, 148.0) followed by `eMillimeter`. A standard name (e.g. `A4`) encodes its mm dimensions through the same path.
  - Image source width/height equal the page canvas in pixels at the given dpi. Data length equals `height * padded_stride` (4-byte aligned).
  - With scale 1 / shift 0 / auto-centre, a black pixel at the image origin lands at the page origin. Shift moves it by the expected pixel count. Rotation swaps dimensions.
  - Multiple `add_page` calls produce multiple `BeginPage`/`EndPage` pairs in one session. `reset()` empties the job.
  - Invalid inputs raise `ValueError`: no pages, non-positive scale, bad scale tuple, unsupported rotation, unknown paper name, `CUSTOM` without dimensions.
  - `PCL5RasterBuilder` construction emits `DeprecationWarning`, and its existing tests keep passing.
- **Golden test**: a fixture payload generated from a font-free, purely geometric 102 x 148 mm test image (border, mm ticks, centre cross) with tray `TRAY2`, job name fixed, defaults otherwise. Before the fixture is frozen, it is printed once on hardware to confirm alignment. The test asserts `build()` reproduces it byte-for-byte.
- **Prior art**: the existing builder tests in the tests folder (byte-level assertions on `PCL5RasterBuilder.build()`), and the printer status tests for the transport.
- **Run note**: in a git worktree, run tests with `PYTHONPATH=src` because the package is an editable install of the main checkout.
- **Hardware acceptance** (manual, operator-confirmed): `print_test_label.py 10.45.1.193 --tray TRAY2` and `print_test_label.py 10.45.1.191 --tray TRAY1`, with no scale and no shift. The outer border must sit within ±2 mm of the paper edge on both printers. The full test suite must be green. No A4 test prints.

## Out of Scope

- Reconfiguring printer trays (setting `INTRAY2SIZE`, Universal, user-defined sizes) or changing printer panel settings.
- Auto-detecting printer family or tray names via `@PJL INFO`. Tray naming stays caller configuration.
- PCL XL `MediaSize` enum for standard papers, and A4 hardware testing.
- RLE or other raster compression.
- Removing `PCL5RasterBuilder` (deprecation only), and fixing its custom-size handling.
- PostScript output, vector/text PCL XL operators, duplex, multiple copies, colour.
- Version bump / release.

## Further Notes

- Evidence in this folder: `evidence/pjl-info-4620sdw.txt` and `evidence/pjl-info-4020sd.txt` (raw `@PJL INFO ID/CONFIG/VARIABLES`), `evidence/paper_probe.py` (the PA1/PA2/PA3 generator, including the working PCL XL encoder) and `evidence/PA2.prn` (the exact payload that printed correctly on both printers).
- The 4620 SDW reports trays as `INTRAY1 = MP` (bypass) and `INTRAY2 = PC` (cassette). The 4020SD names its cassette `TRAY1`.
- Laser printers have a ~3-4 mm non-printable band at the edges. Label designs should keep content inside it rather than rely on scale.
- PCL XL attribute/operator byte values used by the probe: BeginSession 0x41, EndSession 0x42, BeginPage 0x43, EndPage 0x44, OpenDataSource 0x48, CloseDataSource 0x49, SetColorSpace 0x6A, SetCursor 0x6B, BeginImage 0xB0, ReadImage 0xB1, EndImage 0xB2. Attribute ids: ColorSpace 0x03, MediaSource 0x26, Orientation 0x28, CustomMediaSize 0x2F, CustomMediaSizeUnits 0x30, PageCopies 0x31, Point 0x4C, ColorDepth 0x62, BlockHeight 0x63, CompressMode 0x65, ColorMapping 0x64, DestinationSize 0x67, SourceHeight 0x6B, SourceWidth 0x6C, StartLine 0x6D, DataOrg 0x82, Measure 0x86, SourceType 0x88, UnitsPerMeasure 0x89, ErrorReport 0x8F.
