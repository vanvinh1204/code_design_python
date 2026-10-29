# 04: Deprecate PCL5RasterBuilder; migrate README and remaining examples

**What to build:** Constructing `PCL5RasterBuilder` emits a `DeprecationWarning` pointing to `PCLXLRasterBuilder`; its docstring states it cannot declare custom sizes on Brother-family firmware. Behaviour otherwise unchanged. README printing usage and the remaining printer example move to `PCLXLRasterBuilder`.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Test: constructing `PCL5RasterBuilder` warns `DeprecationWarning`
- [ ] Existing `PCL5RasterBuilder` tests still pass (warnings handled, not suppressed globally)
- [ ] README and remaining example use `PCLXLRasterBuilder` with no `feed_direction`
