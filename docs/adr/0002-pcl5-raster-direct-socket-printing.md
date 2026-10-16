# PCL 5 Raster Direct Socket Printing

Status: accepted

## Context & Decision

Downstream applications using `core_kit` (e.g. `whsx-scan-web`, warehouse scan apps) need direct network printing to office and enterprise laser printers (such as Fujifilm ApeosPort Print 4020SD) without operating system print drivers or spoolers.

During diagnostics, sending PostScript directly to devices like the ApeosPort 4020SD yielded blank pages due to missing resident PostScript fonts or device firmware constraints. Conversely, PCL 5 raster streaming (`@PJL ENTER LANGUAGE = PCL`, `\x1b*t300R`, `\x1b*r1A`) rendered reliably with exact dimensional accuracy.

We decided to implement a generalized PCL 5 Raster and PJL network printing module under `core_kit.devices.printer_pcl`, cleanly split into two classes:
1. `PCL5RasterBuilder`: A pure-logic builder that handles physical page configuration (Standard and Custom paper dimensions in mm, Tray selection, Short/Long edge feed, DPI), rasterizes 1-bit monochrome image data with rotation/scaling/offset adjustments, and generates valid PCL 5 raster escape sequences with PJL job headers.
2. `PCLNetworkPrinter`: A lightweight network transport over raw TCP socket (port 9100) providing job dispatch and hardware status interrogation (`@PJL INFO STATUS`).

To preserve minimal core dependencies, `core_kit` handles image processing via Pillow (`PIL.Image`) as an optional extra under `core_kit[devices]`. Heavy document rendering engines (such as PDF-to-image rasterizers like `pypdfium2`) remain strictly inside downstream application layers.

## Considered Options

- **PostScript Level 2/3 via PJL**: Cleaner vector rendering on paper, but causes blank page outputs on models lacking built-in PostScript interpreter licenses or resident font tables.
- **Operating System Spooler / CUPS / Windows GDI**: Requires system-level driver installation and manual configuration on every client machine; unfeasible for headless Docker containers and cross-platform desktop deployments.
- **Monolithic Printer Class**: Blending canvas rasterization and network socket handling in a single class prevents isolated unit testing without physical printer hardware.

## Consequences

- Full independent unit test coverage can verify PCL raster byte output and PJL headers in CI/CD without network access.
- Laser printer hardware margins (~3.5mm dead zone) and custom paper orientations (Short-Edge feed) are safely compensated via scale and offset options.
- The module is reusable across any PCL 5-compatible network laser printer (HP, Fujifilm, Canon, Xerox, Ricoh, Brother).
