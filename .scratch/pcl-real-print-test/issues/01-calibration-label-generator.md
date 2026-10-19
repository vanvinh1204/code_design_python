# 01: Calibration Label Canvas & Layout Generator

**What to build:** Implement the standalone test label canvas generator using Pillow that draws a high-contrast calibration label ($148 \times 102\text{ mm}$ at 300 DPI). The layout includes millimeter alignment ticks along all borders to measure unprintable margin clearance, diagnostic metadata, resolution test ladders (1px, 2px, 4px lines), a solid black toner density block, typography samples, and machine-readable 1D/2D test patterns. Provide an automatic PNG preview export function so users can inspect the label visually before printing.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] Canvas is created at exactly $148 \times 102\text{ mm}$ (300 DPI, monochrome/RGB)
- [x] Millimeter ruler ticks and margin border box are rendered at all four edges
- [x] System metadata (module name, DPI, orientation, target dimensions) is legibly printed
- [x] Resolution ladder lines (1px, 2px, 4px) and solid black fill block are drawn
- [x] High-contrast simulated 1D barcode and 2D matrix patterns are included
- [x] Generates and saves a visual preview PNG file to disk for visual verification
