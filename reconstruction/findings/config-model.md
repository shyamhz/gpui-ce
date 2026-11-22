# Configuration Model

How the framework is configured: features, options structs, and environment. The architecture map (`findings/architecture/architecture-map.md` §Durable State) owns the summary; this file owns the configuration surface. (`observed fact` unless noted.)

## 2026-11-21 — architecture phase

### Cargo features (compile-time configuration; per-crate tables in manifests)

- `gpui`: `default = [font-kit, wayland, x11, windows-manifest, image-default-formats]`; backends `wayland`/`x11` (forward to `gpui_platform`); renderer opts `custom-gpu`, `wgpu-surfaces`; app opts `screen-capture`, `image-default-formats`, `embedded-assets`, `windows-manifest`, `hot-patching` (subsecond/dioxus-devtools), `profiler`, `stacker`, `inspector`, `test-support` (+`leak-detection`, `bench-support`→criterion).
- `gpui_linux`: `default = [wayland, x11]`; either backend alone is supported (`CHANGELOG #373/#379`).
- `gpui_macos`: `font-kit`, `screen-capture`, `wgpu` (swap Metal→WGPU), `bench-support`/`test-support`.
- `gpui_windows`: `default = [gpui/default]`, `test-support`, `screen-capture`.
- `gpui_web`: `default = [multithreaded]` (= `scheduler/wasm-threads` + `flume/spin`).
- `gpui_ce_parley`: `default = [system-fonts]`, `fontconfig-dlopen`, `test-support`.
- `gpui_render`: `swash` (glyph rasterizer), default empty.
- `gpui_scheduler`: `test-support`, `wasm-threads` (panics without shared-memory atomics build flags).
- Inheritance rule: features are additive and backend-selecting; no feature changes public Rust API shape except `test-support` (exposes `TestApp`, test dispatchers) and `inspector`/`profiler` (extra draw paths).

### Runtime options structs

`WindowOptions` (builder: bounds, title, traffic lights, transparency, `kind`, fullscreen… — `CHANGELOG #299/#301`), `WindowParams` (platform-level), `WgpuSurfaceConfig`, `FontRasterizationSettings`, `SubpixelOrder`, `AssetRegistry` wiring (`with_assets`), `PromptBuilder`/`prompt_builder`, appearance override (`set_window_appearance`, macOS-only), `TextRenderingMode`, `CursorHideMode`, `GpuiMode` (incl. headless/skip-drawing), `QuitMode`, `MacActivationPolicy`.

### Environment variables (no config files)

Backend/display: `WAYLAND_DISPLAY`, `DISPLAY`, `ZED_HEADLESS`. Linux desktop: `XCURSOR_PATH`, `LC_CTYPE`, `XDG_ACTIVATION_TOKEN`, `XDG_CURRENT_DESKTOP`, `GPUI_X11_SCALE_FACTOR_ENV`. Windows: `DISABLE_DIRECT_COMPOSITION`. Diagnostics/tests: `SEED`, `LEAK_BACKTRACE`, `GPUI_RUN_UNTIL_PARKED_LOG`, `RUST_BACKTRACE`/`RUST_LOG` (ambient). Compile-time: `TRACK_THREAD_BORROWS`, `OUT_DIR` (shader codegen).

### Precedence (strong inference)

Explicit API arguments (`WindowOptions`, `with_*` builders) > platform-detected defaults (compositor name, displays, system appearance) > ambient environment (display vars, desktop hints) > Cargo features (which backends/code paths even exist). There is no layered config-file system to merge — a port needs option structs + env probing, not a settings cascade.
