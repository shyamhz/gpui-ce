# Public Surfaces

Catalog-level inventory of every boundary the outside world touches. The architecture map (`findings/architecture/architecture-map.md` §Public Surfaces) owns the summary; this file owns the enumerated detail. (`observed fact` unless noted; paths relative to repo root.)

## 2026-11-21 — architecture phase

### Rust library API (no binary, no RPC)

- The workspace publishes libraries only: `gpui-ce`, `gpui_ce_platform`, `gpui_ce_{macos,apple,linux,windows,web,wgpu,render,parley,elements,…}` (`observed fact`: `[lib]` sections, no `[[bin]]` except `tooling/perf`). Crate docs entry: `crates/gpui/src/gpui.rs` (`#![warn(missing_docs)]`).
- Boot: `gpui_platform::application() -> Application` (OS-selected `Rc<dyn Platform>`), `Application::run(launch: FnOnce(&mut App))`, `App::open_window::<V: Render>(WindowOptions, build_root_view) -> Result<WindowHandle<V>>` (`crates/gpui_platform/src/gpui_platform.rs:18-54`, `crates/gpui/src/app.rs:327,1558`). `WindowOptions` is a builder (`CHANGELOG #299/#301`).
- UI declaration: `div()` builder (`crates/gpui/src/elements/div.rs:2316`), `canvas`, `img`, `svg`, `uniform_list` (virtualized, `examples/learn/uniform_list.rs`), `list`, `deferred`, `surface` (custom shaders), `anchored`, `container_query`; traits `Element`, `IntoElement`, `ParentElement`, `InteractiveElement`, `StatefulInteractiveElement`, `Styled` (+ derive macros in `gpui_macros`: `derive_element_traits.rs`, `styles.rs`).
- Views: `Entity<T>` handle (slotmap `EntityId`, `app/entity_map.rs:32-60,469-478`), `Render::render(&mut self, &mut Window, &mut Context<Self>) -> impl IntoElement`, `RenderOnce`, `use_state` hook state, `Entity::cached` skip, `Context::notify/emit/observe/subscribe` (`app/context.rs:146-256,416,1145`).
- Actions/keys: `actions!` (zero-data) / `#[derive(Action)]` (data-carrying), `ActionRegistry`, `KeyBinding::new(keystrokes, action, context)`, `Keymap`, key-context dispatch tree (`key_dispatch.rs:140-327`), `App::bind_keys`, `on_action` handlers, global action listeners (`app.rs:855`).
- Async: `BackgroundExecutor::spawn/spawn_with_priority/spawn_realtime/spawn_dedicated`, `ForegroundExecutor::spawn/spawn_when_idle`, `Task<T>::detach`, `cx.spawn`, timers via `Scheduler`/`Timer` (`executor.rs`, `gpui_scheduler/src/executor.rs:72-385,555-636`).
- Painting: `Window::paint_quad/paint_path/paint_image/paint_drop_shadows/paint_inset_shadows/paint_backdrop_filter/paint_layer/with_filter_layer/defer/defer_draw`, `request_animation_frame/on_next_frame`, `Hitbox`/`HitTest` inspection (`window.rs:2682-2712,4439-4774,2807`).

### Platform trait (`dyn Platform`, `crates/gpui/src/platform.rs:151-411`)

Window/run-loop/appearance control; displays; menus (`app_menu.rs`, dock menu); clipboard (sync + async + primary + find pasteboard); credentials vault (read/write/delete → keychain/oo7); file/dir prompts; URL schemes + `on_open_urls`; notifications (+ response callbacks); thermal state; haptics; keyboard layout + mapper; screen capture (feature-gated; `windows_screen_capture.rs`, macOS `screen_capture.rs`); app identity/restart paths; cursor styles; drag (platform-owned); IME/input-handler plumbing (`PlatformInputHandler`, `set_input_handler`).

### Text (`crates/gpui/src/text_system/`, `crates/gpui_ce_parley/`)

`TextSystem { platform_text_system: Arc<dyn PlatformTextSystem>, font caches }`; `ShapedLine`, `LineLayout`, `TextRun`, `Font/FontId/FontMetrics`, `GlyphRasterizer` (in core since #399); Parley backend (`ParleyTextSystem::new` + `.with_system_fonts()/.add_fonts()/.with_fallback_families()`, `CHANGELOG #399/#400`); `SwashGlyphRasterizer` + `BitmapFallbackGlyphRasterizer` behind `gpui_render/swash` (`CHANGELOG #399`); fontconfig dlopen opt-in (`fontconfig-dlopen`).

### Accessibility (accesskit 0.24)

Per-frame `TreeUpdate` (`a11y_tree()`), node bounds, frame number, `perform_a11y_action`, forced generation (`with_accessibility_forced`, `set_a11y_forced`), opt-out (`new_inaccessible`, `aria_hidden`), aria attributes (disabled/modal/live/hidden) (`window.rs:7216-7268`, `window/a11y.rs`, `CHANGELOG #233/#234/#274/#279/#293`).

### Outbound I/O traits (no inbound network surface)

`HttpClient::get(url, follow_redirects)` + `NullHttpClient`; web backend supplies fetch client (`http_client.rs`, `gpui_web/src/http_client.rs`). `AssetSource` (deprecated path) → `AssetRegistry`/`AssetEntry` (preloaded + on-demand) (`assets.rs`, `CHANGELOG #259`).

### Formats & artifacts consumed

System fonts; raster images (`image` crate: `png/gif/webp` default, `image-default-formats` flag → default-formats); SVG (resvg/usvg via `svg_renderer.rs`); cursor themes (`XCURSOR_PATH`); locale (`LC_CTYPE`); keymap collections (format not verified — see blind spot in architecture map).
