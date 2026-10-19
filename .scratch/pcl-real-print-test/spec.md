# PCL Real-World Print Verification & Calibration Tool Specification

Status: resolved

## Problem Statement

Now that the core PCL 5 raster and PJL network printing module has been implemented in the library, developers and operators need a reliable, self-contained verification tool to test printing physical labels on actual laser printers (such as the Fujifilm ApeosPort Print 4020SD over local network).

Without a dedicated real-world test tool:
1. Developers cannot immediately verify whether physical output on custom decal media ($102 \times 148\text{ mm}$) suffers from mechanical unprintable margin clipping (the 3.5mm laser dead zone).
2. Users cannot visually calibrate print scaling, alignment offsets, toner density, or 1D/2D barcode readability on actual paper without deploying a full-blown downstream web/desktop application.
3. Troubleshooting network connectivity, socket timeouts, and hardware faults (such as paper jams or open tray covers) requires manual debugging scripts, risking jammed printer queues.
4. Developers need a way to inspect the rendered label on a computer screen (preview image) before committing expensive decal label sheets to physical print.
5. In accordance with project rules, the tool must run cleanly without relying on the prohibited `argparse` library.

## Solution

Provide a standalone verification and calibration script in the examples suite that demonstrates the end-to-end printing pipeline:

1. **Self-Contained Calibration & Test Label Generator**:
   - Generates a high-contrast calibration label using Pillow on a standard $148 \times 102\text{ mm}$ canvas at 300 DPI.
   - Includes physical alignment border boxes, millimeter calibration ticks at all four corners, system diagnostic metadata, resolution test ladders (1px, 2px, 4px line widths), solid toner density blocks, and machine-readable test barcode patterns.

2. **Integration with Core Printing Classes**:
   - Feeds the generated image into `PCL5RasterBuilder` configured for custom paper dimensions ($102 \times 148\text{ mm}$), Tray 1, Short-Edge feed, 90° rotation, 0.94 scale factor, and automatic centering.
   - Leverages `PCLNetworkPrinter` to perform pre-flight hardware interrogation (`get_status()`) and dispatch the raw PCL 5 byte stream to the target printer IP over port 9100.

3. **Safe Execution, Previews, and Zero-Argparse CLI**:
   - Automatically exports a visual preview image to the local filesystem for immediate inspection without physical printing.
   - Supports dry-run execution (`--dry-run`), raw PCL binary dumping (`--save-pcl`), and direct IP override without utilizing `argparse`.
   - Enforces pre-flight status verification to prevent job dispatch when the printer LCD reports paper jams or empty trays.

## User Stories

1. As a field technician, I want to execute a single command to print a test label to the ApeosPort printer, so that I can immediately verify network reachability and hardware functionality.
2. As a quality engineer, I want the printed test page to contain millimeter ruler ticks at all corners, so that I can measure margin clearance and verify that the 3.5mm dead zone is not truncating text or borders.
3. As a developer, I want an automatic visual preview image generated on my machine, so that I can inspect label layout without wasting physical decal label stock.
4. As an operator, I want the script to check printer status prior to sending data, so that print jobs are aborted with clear warnings if the printer is jammed or out of paper.
5. As a system administrator, I want to supply a custom printer IP directly on the command line or via environment variables, so that I can test multiple printers across different subnets.
6. As a barcode scanner operator, I want the test label to feature high-contrast 1D and 2D barcode patterns, so that I can verify that handheld optical scanners can scan labels printed via PCL 5 raster.
7. As a maintenance engineer, I want the test label to include solid black fill blocks and variable-thickness line ladders, so that I can evaluate toner transfer uniformity and 300 DPI resolution sharpness.
8. As a developer troubleshooting printer communication, I want a dry-run mode that skips network calls, so that I can verify payload generation and file exports in offline development environments.
9. As a library maintainer, I want the test script to function strictly without the `argparse` module, so that the codebase remains fully compliant with project architectural rules.
10. As an integration engineer, I want an option to dump the raw PCL binary stream to disk, so that I can inspect escape sequence bytes in a hex editor or transmit them via third-party network tools.

## Implementation Decisions

- **Architectural Placement**: The script is placed in the examples directory alongside existing device verification tools, acting as both an end-to-end verification script and a canonical reference example for downstream application developers.
- **Dependency Isolation**: Label generation uses Pillow only, avoiding dependencies on external PDF rendering engines or specific business logic modules.
- **Command-Line Parsing Strategy**: Uses raw argument inspection on `sys.argv` (checking for flags like `--dry-run`, `--save-pcl`, or positional IP addresses) to strictly comply with the rule prohibiting `argparse`.
- **Pre-Flight Telemetry Hook**: Before attempting socket write operations, `PCLNetworkPrinter.get_status()` is called. If `is_ready` evaluates to `False`, the script halts with an explanatory message unless overridden.
- **Preview Artifact Generation**: Every invocation saves a PNG preview of the generated label canvas to facilitate rapid visual inspection.

## Testing Decisions

- **Definition of Good Tests**: The test script must prove external system behavior: successful socket handshake, accurate LCD status reporting, and byte-complete transmission confirmed by graceful socket closure.
- **Tested Modules**: `core_kit.devices.PCL5RasterBuilder` and `core_kit.devices.PCLNetworkPrinter`.
- **Testing Seam**: 
  - Primary Execution Seam: End-to-end execution of `examples/print_test_label.py` running in `--dry-run` mode to verify zero-error generation and PNG/PCL artifact creation.
  - Hardware Seam: Physical socket dispatch to port 9100 on the live printer network.
- **Prior Art**: Follows patterns established in `examples/test_devices.py` and `examples/test_printer_pcl.py`.

## Out of Scope

- Automated optical verification or scanning of the printed paper via camera.
- Spooling or queue management for multi-user concurrent print tests.
- Firmware updating or remote printer configuration changes via PJL.

## Further Notes

- The default IP address `10.45.1.191` corresponds to the workshop ApeosPort Print 4020SD unit currently designated for WHSX internal label printing.
