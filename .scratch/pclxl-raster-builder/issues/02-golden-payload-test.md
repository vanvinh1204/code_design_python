# 02: Golden test locking the hardware-verified PCL XL payload

**What to build:** A font-free, purely geometric 102 x 148 mm test image (outer border, 5 mm inner border, mm ticks on top/left edges, centre cross) generated deterministically in the test, a fixture payload built from it with `PCLXLRasterBuilder` (paper CUSTOM 102 x 148, tray `TRAY2`, fixed job name, defaults otherwise), and a test asserting `build()` reproduces the fixture byte-for-byte. The fixture is printed once on the 4620 SDW and confirmed aligned by the operator before it is considered frozen.

**Blocked by:** 01

**Status:** ready-for-agent (operator confirms the print)

- [x] Deterministic geometric image helper (no fonts) used by the test and by the fixture generator
- [x] A small regeneration script/function for the fixture, documented in the test module docstring
- [x] Fixture committed; golden test passes
- [ ] Operator confirmed the fixture prints aligned (±2 mm) on 10.45.1.193
