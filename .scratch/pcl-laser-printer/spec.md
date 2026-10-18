# PCL 5 Raster & PJL Network Printing Specification

Status: resolved

## Problem Statement

Applications built on `core_kit` (FastAPI web backends and PySide6 desktop applications) often need to print internal labels, carton tags, shipping documents, or reports directly to network laser printers (such as Fujifilm ApeosPort Print 4020SD, HP LaserJet, Ricoh, Canon) across local area networks (LAN).

Previously, developers attempting direct socket printing on port 9100 faced critical hurdles:
1. Sending raw PostScript directly causes many enterprise laser printers (including ApeosPort 4020SD) to eject blank pages due to missing built-in PostScript fonts or device firmware constraints.
2. Operating system print drivers and spoolers (Windows GDI / CUPS) require manual setup on every terminal and cannot be used in headless Docker containers or lightweight client deployments.
3. Custom label stock (such as $102.4 \times 148\text{ mm}$ decal media loaded in Short-Edge Feed orientation) requires hardware-specific PJL variables; without them, printers default to standard Legal or A4 sizes, jamming or clipping the output.
4. Physical laser printers have an unprintable margin (~3.5 – 4 mm) on all edges. Without automatic scaling and centering, barcodes and text near the label edges are sliced off.

## Solution

Provide a generalized, driverless PCL 5 Raster and PJL network printing module within `core_kit.devices`:

1. **`PCL5RasterBuilder` (Pure-Logic Document Rasterizer)**:
   - Configures PJL headers for both standard paper sizes (A4, Letter) and custom millimeter dimensions (e.g. 102 mm x 148 mm), specifying paper source (Tray 1, MP Feeder) and feed direction (Short-Edge vs Long-Edge).
   - Ingests monochrome or color images, converting them to 1-bit monochrome bitmaps.
   - Automatically handles image rotation (0°, 90°, 180°, 270°) to match hardware tray orientation.
   - Automatically scales (defaulting to 0.94 to avoid mechanical margins) and centers the image on the physical canvas, while allowing fine-grained millimeter offset tuning (`shift_x_mm`, `shift_y_mm`).
   - Compiles pixel rows into standard PCL 5 raster escape sequences (`\x1b*t300R`, `\x1b*r1A`, `\x1b*b...W`, `\x1b*rB`) with inverted bit ordering, producing a self-contained, print-ready byte payload.

2. **`PCLNetworkPrinter` (Raw Socket Transport & Hardware Telemetry)**:
   - Connects directly to the printer's TCP port 9100 with configurable timeout and graceful socket teardown.
   - Interrogates printer status via `@PJL INFO STATUS` and parses the response into a structured `PrinterStatus` object (`is_online`, `is_ready`, `display`), enabling callers to detect paper jams, open doors, or empty paper trays before dispatching jobs.
   - Dispatches byte payloads cleanly over the network.

3. **Decoupled Architecture & Lightweight Dependencies**:
   - `core_kit` processes pre-rendered images (`PIL.Image`) using Pillow, keeping heavy PDF-rendering engines (like `pypdfium2`) in downstream applications.

## User Stories

1. As a warehouse software developer, I want to send label print jobs directly to an ApeosPort 4020SD laser printer over RAW TCP socket (port 9100), so that users do not need to install local OS printer drivers on every workstation.
2. As an application developer, I want to print using PCL 5 raster graphics instead of PostScript, so that laser printers without built-in PostScript interpreters print crisp labels without outputting blank pages.
3. As a label operator, I want custom decal paper ($102 \times 148\text{ mm}$) to feed via Tray 1 in Short-Edge orientation, so that the printer feeds the stock smoothly without size mismatch paper errors.
4. As a developer, I want images to rotate 90°, 180°, or 270° within the builder, so that labels designed horizontally print properly on vertically fed paper rolls or sheets.
5. As a quality engineer, I want the builder to apply a default 0.94 scale factor and center the artwork, so that barcodes and border frames are not truncated by the printer's 3.5mm mechanical unprintable margin.
6. As a system administrator, I want to adjust millimeter offsets (`shift_x_mm`, `shift_y_mm`), so that I can compensate for mechanical tray alignment tolerances across different printer units.
7. As a client developer, I want to query the printer's LCD display status before printing, so that I can warn the user if the printer is reporting "Paper Jam" or "Load Tray 1" instead of sending jobs into a failing queue.
8. As a backend developer, I want `PCL5RasterBuilder` to be a pure-logic class with zero network calls, so that I can generate print payloads and run fast, automated unit tests in CI/CD without physical printer hardware.
9. As a library maintainer, I want Pillow to be optional under `core_kit[devices]`, so that developers who only use database or auth features do not have to install image manipulation dependencies.
10. As a desktop developer, I want `PCLNetworkPrinter.send()` to gracefully shut down the write channel before closing the socket, so that the final raster byte packets are never dropped mid-transmission.
11. As a web developer, I want the print module to support standard paper sizes (like A4 and Letter) alongside Custom sizes, so that the same library can print warehouse pick lists and reports on regular office printers.
12. As a software tester, I want to test PCL raster conversion using simulated 1-bit test patterns, so that test assertions can deterministically verify byte-for-byte fidelity of PCL escape sequences.

## Implementation Decisions

- **Architectural Scope**: The module is placed under the devices namespace as a general-purpose PCL 5 / PJL raster engine, rather than locked to a specific printer brand or model.
- **Two-Class Separation**:
  - `PCL5RasterBuilder` strictly handles document layout, coordinate math, image rasterization, and PCL/PJL byte serialization.
  - `PCLNetworkPrinter` strictly handles TCP socket transmission and PJL status interrogation.
- **Structured Status Model**: Status queries return a typed dataclass encapsulating `is_online`, `is_ready`, `display` message, and the full `raw` response string.
- **Dependency Boundary**: `pillow>=10.0.0` is declared as an optional dependency for the devices extra. Heavy PDF rendering engines remain strictly in downstream applications.
- **Command-Line Interface Constraint**: In strict adherence to project rules, no command-line parsing libraries (such as `argparse`) are used in any module or test script.
- **Bit Inversion Handling**: Standard 1-bit image representations (where 0 is black and 1 is white) are bitwise inverted during PCL raster encoding to match PCL 5 conventions (where 1 represents a deposited toner dot).

## Testing Decisions

- **Definition of Good Tests**: Tests must verify observable external behavior (correctness of PJL headers, presence of resolution commands, valid raster line markers, form feed termination) rather than mocking internal image loops.
- **Tested Modules**: `PCL5RasterBuilder` serialization logic, custom dimension header formatting, coordinate shifting, scale clamping, and `PrinterStatus` text parser.
- **Testing Seam**: 
  - Primary Seam: `PCL5RasterBuilder.build()` called with test images to inspect the generated `bytes`.
  - Secondary Seam: `PrinterStatus.from_raw(status_text)` tested against sample responses ("Ready", "Paper Jam", "Load Tray 1").
- **Prior Art**: Follows the pattern established in existing device tests (`test_devices.py`), generating standalone verification scripts in the examples suite.

## Out of Scope

- Rendering PDF documents or PostScript files directly inside `core_kit` (delegated to application layer).
- Vector PCL drawing primitives (lines, text fonts, curves); all graphical content is unified through 300 DPI rasterization.
- Bidirectional SNMP printer management or MIB walking.
- USB and parallel port communication (raw TCP socket only).

## Further Notes

- The 0.94 scale factor was experimentally verified on firmware MSLBD.230.441 of ApeosPort Print 4020SD as the ideal ratio preventing both margin clipping and excessive white space padding.
