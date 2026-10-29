# PCL XL Raster with CustomMediaSize

Status: accepted (supersedes ADR-0002)

## Context & Decision

ADR-0002 chose PCL 5 raster over RAW socket printing. PCL 5 has no command that carries custom page dimensions: `ESC&l101A` only says "custom", and the real size (e.g. a 102 x 148 mm label) travels in vendor-specific PJL variables. That only works when the printer's firmware understands those variables.

Two printer families behave differently with the same PCL 5 job:

- **Lexmark-family firmware** (Fujifilm ApeosPort Print 4020SD, 10.45.1.191): exposes `LCUSTOMPAPERWIDTH/HEIGHT/UNITS` and `PAPER=CUSTOM`, and its cassette is set to `INTRAY1SIZE=CUSTOM`. It honours the job's custom size, so labels print correctly.
- **Brother-family firmware** (Fujifilm ApeosPrint 4620 SDW, 10.45.1.193, `@PJL INFO ID` = `84U-LB4`): exposes none of the `LCUSTOMPAPER*` / `PAPERWIDTH` variables and has no `PAPER=CUSTOM`. It silently falls back to the size configured for the cassette (`INTRAY2SIZE=EXECUTIVE`), so the label prints shifted ~62 mm off the paper. Its panel offers no "Universal" size.

Hardware probes on the 4620 SDW, with the tray left at Executive:

| Probe | Payload | Result |
|---|---|---|
| PA1 | PCL 5 + `ESC&l74A` + `@PJL SET PAPER = P4X6` | shifted (wrong) |
| PA2 | PCL XL, `BeginPage` with `CustomMediaSize` 102 x 148 mm | **correct** |
| PA3 | PostScript `setpagedevice /PageSize [289 420]` | shifted (wrong) |

PA2 was then sent unchanged to the 4020SD and also printed correctly.

We decided to add `PCLXLRasterBuilder`, which produces a PJL-wrapped PCL XL raster job whose page size is **always** declared via the `CustomMediaSize` attribute of `BeginPage` in millimetres (`CustomMediaSizeUnits = eMillimeter`), including for standard paper names (resolved to mm first). The PJL envelope carries only the job name, an optional `MEDIASOURCE` (passed through verbatim as per-printer configuration) and `ENTER LANGUAGE = PCLXL`; it emits no paper-size or feed-direction variables. Defaults are scale 1.0 and shift 0 mm. `PCLNetworkPrinter` and the PJL Status Probe are unchanged.

## Considered Options

- **PA1: PCL 5 with a standard size code + PJL `PAPER`**: rejected. The Brother-family firmware still used the cassette size; there is no PCL 5 / PJL path that declares a custom size on it.
- **PA3: PostScript `setpagedevice /PageSize`**: rejected. Also shifted on the 4620 SDW, and ADR-0002 already found PostScript unreliable (blank pages) on the 4020SD.
- **Reconfigure the printer tray** (set cassette to the label size or Universal): rejected. The 4620 SDW has no Universal option, and correctness should not depend on panel settings per machine.
- **PCL XL `MediaSize` enum for standard papers**: not used. There is no hardware evidence for it; one proven path (`CustomMediaSize`) for every size avoids an untested branch.
- **Keep PCL 5 with hand-tuned scale/shift**: rejected. The old defaults (scale 0.89/0.94, shift_x -5 mm) were calibrated against the 4020SD and masked the layout mismatch instead of fixing it.

## Consequences

- One payload shape prints edge-accurate on both printer families with no tray reconfiguration and no scale/shift compensation. Optional scale/shift remain only for fine-tuning a 1-2 mm mechanical offset.
- Tray names differ between families (4620 SDW cassette = `TRAY2`, 4020SD cassette = `TRAY1`) and are caller configuration, not a hard-coded mapping. `tray=None` sends no tray selection.
- Payloads are uncompressed in this iteration (about 260 KB per 102 x 148 mm page at 300 dpi). RLE compression is a possible later improvement.
- `PCL5RasterBuilder` stays for backward compatibility but is deprecated; it cannot declare custom sizes on Brother-family firmware. Do not revert to PCL 5 custom sizing.
- A golden-byte test locks the hardware-verified PCL XL payload so refactors cannot silently change what the printers accept.

## Evidence

In `.scratch/pclxl-raster-builder/evidence/`:

- `pjl-info-4620sdw.txt`, `pjl-info-4020sd.txt`: raw `@PJL INFO ID/CONFIG/VARIABLES` from both printers.
- `paper_probe.py`: generator for PA1/PA2/PA3, including the working PCL XL encoder (`job_pclxl`).
- `PA2.prn`: the exact payload that printed correctly on both printers.
