# Architecture Map

## System Intent

GPUI-CE is a community-maintained fork of Zed's [GPUI](https://gpui.rs) GPU-accelerated UI framework
for Rust, extracted from the Zed editor monorepo into a standalone Cargo workspace so independent
applications can build on it (`observed fact`: `README.md:9`, `crates/gpui/README.md:1`). It is a
**hybrid immediate- and retained-mode, GPU-accelerated UI framework designed to support a wide
variety of applications** (`observed fact`: `crates/gpui/README.md:2-4`). It is pre-1.0 (current
version 0.4.0, `observed fact`: workspace `Cargo.toml:36`, `crates/gpui/Cargo.toml:3`) and breaking
changes between versions are expected (`observed fact`: `crates/gpui/README.md:6-8`). The fork
tracks upstream Zed GPUI via an automated vendor-branch sync (`observed fact`:
`scripts/sync-upstream/README.md`, `justfile:537-547`), while diverging deliberately: parley-based
text on all platforms, a unified WGSL renderer, Tailwind-style APIs, and a maintained changelog of
breaking changes (`observed fact`: `CHANGELOG.md:59-265`).

In language-independent terms: think "a retained scene-graph UI toolkit with a React-like
declarative layer, an Elm-like typed message/action system, and a retained GPU scene that is rebuilt
every frame" — the porting target is that architecture, not the Rust syntax.

## Layer Map

### Package Inventory

| Package / Module | Role | Public Entrypoints | Key Dependencies | Runtime Surface |
|---|---|---|---|---|
| `gpui` (`gpui-ce` 0.4.0, `crates/gpui/`) | `core semantics` | `gpui_platform::application()`, `Application::run`, `App::open_window`, `div()`, `Entity<T>`, `Context`, `Render`/`RenderOnce`, `actions!`, `KeyBinding`, `Task`, `BackgroundExecutor`/`ForegroundExecutor`, `Window::paint_*` | leaf utils (`collections`, `refineable`, `scheduler`, `sum_tree`, `gpui_util`, `gpui_shared_string`), `gpui_macros`, `taffy` (=0.13.0), `wgsl-rs` (build), accesskit | In-process UI runtime: windows, GPU scenes, async tasks |
| `gpui_platform` (`gpui_ce_platform`, `crates/gpui_platform/`) | `integration adapter` | `application()`, `application_with_web_backend()`, `current_platform(headless)`, `headless()`, `background_executor()`; re-exports `gpui::Platform` | `gpui`, plus per-OS crate selected by `cfg` (`gpui_macos`, `gpui_linux`, `gpui_windows`, `gpui_web`, `gpui_apple`) | Facade: picks windowing + text backends for the host OS |
| `gpui_macos` (`gpui_ce_macos`) | `integration adapter` | `MacPlatform` | `gpui`, `gpui_apple`, `gpui_parley` (system-fonts), `gpui_render` (swash), opt `gpui_wgpu` | NSApplication/NSWindow via objc2; Metal (default) or WGPU (opt-in `wgpu` feature) |
| `gpui_apple` (`crates/gpui_apple/`) | `integration adapter` | `MetalRenderer`, `MetalHeadlessRenderer` | `gpui`, `gpui_render` | Shared Apple GPU layer: CAMetalLayer, `metal_atlas` |
| `gpui_linux` (`gpui_ce_linux`) | `integration adapter` | `current_platform(headless)` | `gpui_wgpu`, calloop, wayland-*/x11 stack, ashpd, xkbcommon | Wayland backend (`linux/wayland/`), X11 backend (`linux/x11/`), headless; backend chosen by `wayland`/`x11` features |
| `gpui_windows` (`gpui_ce_windows`) | `integration adapter` | `WindowsPlatform` | `gpui`, `gpui_render` (swash), `gpui_parley`, `windows` crate, DirectX stack | Win32 message pump, DirectWrite text, DirectX renderer (`directx_renderer.rs`), DirectComposition toggle |
| `gpui_web` (`gpui_ce_web`) | `integration adapter` | `WebPlatform`, `WebBackendPreference`, `web_init()` | wasm-bindgen, web-sys, `scheduler/wasm-threads` (via `multithreaded` default feature) | Browser canvas; single-threaded or web-worker (`multithreaded`) modes |
| `gpui_render` (`gpui_ce_render`) | `protocol or normalization layer` | Shader contracts (`BASE_WGSL`, `BASE_DOWNLEVEL_WGSL`), `InstanceRange`, `SwashGlyphRasterizer`, `BitmapFallbackGlyphRasterizer` (behind `swash` feature) | `gpui` (path dep), `wgsl-rs` + `naga` (build-time WGSL codegen) | Shared typed rendering: instances, targets, per-primitive WGSL modules in `shaders/` |
| `gpui_wgpu` (`gpui_ce_wgpu`) | `integration adapter` | `WgpuRenderer`, `GpuContext`, `WgpuSurfaceConfig`, `FontRasterizationSettings` | `gpui`, `gpui_render`, `gpui_util`, wgpu 29.0.3 | wgpu-based backend (Linux/Windows; opt-in macOS `custom-gpu`/`wgpu-surfaces` paths) |
| `gpui_ce_parley` (`gpui_ce_parley`) | `protocol or normalization layer` | `ParleyTextSystem` | `gpui`, fontique 0.12, parley 0.12, skrifa | Text shaping/wrapping/hit-testing on every platform; `FontStore` |
| `gpui_ce_fonts` (`gpui-ce-fonts`) | `core semantics` | font catalog abstraction (optional dep of parley crate) | fontique/parley system backends | System-font loading (`system-fonts` default feature) |
| `gpui_scheduler` (`gpui_ce_scheduler`) | `core semantics` | `BackgroundExecutor`, `ForegroundExecutor`, `Task<T>`, `Priority`, `TestClock`, `TestScheduler` | `async-task`, flume, `web-time`; opt `wasm_thread` | Task/executor substrate for all async work |
| `gpui_sum_tree` (`gpui_ce_sum_tree`) | `core semantics` | `SumTree`, `Cursor`/`FilterCursor`/`Iter`, `TreeMap`/`TreeSet` | (leaf: proptest only in dev) | Persistent ordered tree; used by `elements/list.rs`, `tab_stop.rs` (`observed fact`: grep) |
| `gpui_collections` (`gpui_ce_collections`) | `core semantics` | `FxHashMap`/`FxHashSet` (rustc-hash re-export), `indexmap::Equivalent`, `vecmap` | `gpui_ce_util` | Hash-map vocabulary used in 24 files under `crates/gpui/src/` (`observed fact`: grep count) |
| `gpui_path` (`gpui_ce_path`) | `core semantics` | `AbsPath`/`RelPath` (`abs_path`, `rel_path`), `PathComponent`, windows-prefix handling | (leaf) | Typed absolute/relative path wrappers (ported from Zed) |
| `gpui_refineable` + `gpui_derive_refineable` | `core semantics` | `Refineable` trait, `#[derive(Refineable)]`, `StyleRefinement` | (leaf; proc-macro deps only) | Hierarchical partial-update pattern: base value + sparse refinement overlay (drives `Styled::refine_style`) |
| `gpui_macros` (`gpui_ce_macros`) | `core semantics` | `actions!` (re-exported), `#[derive(Action, Render, IntoElement, ParentElement, InteractiveElement, StatefulInteractiveElement, Styled, AppContext, VisualContext)]`, `register_action`, `test`/`bench`/`property_test` harnesses, `inspector` reflection | syn/quote/proc-macro2 | Compile-time codegen for the action/component/test vocabulary |
| `gpui_elements` (`gpui_ce_elements`) | `UI or rendering` | `editable_text`, `switch` (`BaseSwitch`) modules | `gpui` | Small unopinionated widget set on top of core (`observed fact`: `lib.rs:1-3`) |
| `gpui_media` (`gpui_ce_media`) | `integration adapter` | CoreMedia/CoreVideo bindings (`bindings.rs`, `media.rs`) | macOS system frameworks (build: cbindgen) | Native media bindings (macOS) |
| `gpui_tokio` (`gpui_ce_tokio`) | `integration adapter` | `gpui_tokio::init(cx)` / `init_from_handle` | `gpui`, tokio (2 worker threads) | Bridges a Tokio runtime in as a `Global` so entities can spawn Tokio work (`observed fact`: `gpui_tokio.rs:7-24`) |
| `gpui_shared_string` (`gpui_ce_shared_string`) | `core semantics` | `SharedString` (smol_str-backed, serde/schemars impls) | smol_str, serde, schemars | Cheap-clone immutable string used pervasively (element ids, labels) |
| `gpui_zed_util` (`gpui_ce_zed_util`) | `core semantics` | `fs`, `paths`, `shell`, `process`, `command`, `markdown`, `time`, `redact`, `size`, … | `gpui_ce_util`, `gpui_ce_path` | Vendored Zed utility belt for platform backends (`observed fact`: crate description "vendored from Zed's util") |
| `gpui_ce_util` (package `gpui_util`) | `core semantics` | `arc_cow::ArcCow`, `ResultExt`, `defer` | (leaf) | New small CE-owned utilities (split from the vendored Zed set) |
| `tooling/perf` | `product shell` | `tooling/perf` binary (`main.rs`, `implementation.rs`) | workspace | Perf-measurement harness for the framework itself |

Role notes: every `gpui_*` directory publishes under a `gpui_ce_*` package name (`observed fact`:
`[package] name` fields, e.g. `gpui_ce_platform`, `gpui-ce-fonts`) — the rename reserves the `gpui`
namespace and marks the fork. `gpui` itself publishes as `gpui-ce`.

### Dependency Direction

The stable base is the **leaf-utility layer**: `gpui_collections`, `gpui_path`, `gpui_refineable`
(+derive), `gpui_shared_string`, `gpui_ce_util`, `gpui_scheduler`, `gpui_sum_tree` depend on nothing
in the workspace (only external crates). `gpui_ce_zed_util` sits one step up (depends on
`gpui_ce_util` + `gpui_ce_path`).

**`gpui` (core) depends only on leaves + `gpui_macros`** (`observed fact`: `crates/gpui/Cargo.toml`
`[dependencies]` lists `gpui_macros`, `gpui_shared_string`, workspace leaves; no
`gpui_platform`/`gpui_render`/backend crates in normal deps). Platform and
GPU adapters use interfaces defined in core, including separate `Platform`,
`PlatformDisplay`, `PlatformWindow` and `PlatformTextSystem` traits
(`observed fact`: `crates/gpui/src/platform.rs:151,389,891,1206`).

The next ring — `gpui_platform`, `gpui_macos`, `gpui_apple`, `gpui_linux`, `gpui_windows`,
`gpui_web`, `gpui_render`, `gpui_wgpu`, `gpui_ce_parley`, `gpui_elements`, `gpui_media`,
`gpui_tokio` — **all depend on `gpui`** (`observed fact`: each crate's `Cargo.toml`; e.g.
`gpui_render` → `gpui` path dep, `gpui_platform` → `gpui`). `gpui_platform` is the facade that
re-exports `gpui::Platform` and selects the per-OS implementation with `#[cfg]` (`observed fact`:
`crates/gpui_platform/src/gpui_platform.rs:56-94`, `current_platform()`), so applications depend on
`gpui` + `gpui_platform` and never `cfg`-gate themselves (`observed fact`:
`crates/gpui/README.md:12-26`).

**Cycles:** there is exactly one, and it is dev-only and legal: `gpui`'s `[dev-dependencies]`
include `gpui_platform` (line 162) while `gpui_platform`'s `[dependencies]` include `gpui` — Cargo
permits cycles through dev-dependencies, and this one exists so core tests/examples exercise the
real platform (`strong inference`: placement of the dep under `[dev-dependencies]` plus per-OS
`test-support` dev-deps in `gpui_platform`). The `wayland = ["gpui_platform/wayland"]` feature
entries in `crates/gpui/Cargo.toml:37-38` likewise only take effect for test/example builds. No
production (`[dependencies]`) cycle was found (`observed fact`: grep over `crates/gpui/Cargo.toml`).

Feature flags carve the platform matrix without multiplying crates: `gpui/wayland`, `gpui/x11`
toggle the corresponding `gpui_platform` backends so Linux can target either or both
(`observed fact`: `CHANGELOG.md:19-20`, `crates/gpui_linux/Cargo.toml` feature split);
`gpui_macos/wgpu` swaps Metal for the shared WGPU renderer; `screen-capture`, `test-support`,
`bench-support`, `inspector`, `hot-patching`, `leak-detection` gate optional subsystems
(`observed fact`: feature tables in `crates/gpui/Cargo.toml:14-54` and per-crate manifests).

## Public Surfaces

Full catalog with per-item detail lives in `findings/public-surfaces/public-surfaces.md` (secondary
output). Summary of load-bearing surfaces:

- **Rust library API (`gpui` crate).** The whole framework is a library; there is no binary, no
  socket, no RPC of its own (`observed fact`: `crates/gpui/Cargo.toml` `[lib]`, no `[[bin]]`).
  Applications enter through `gpui_platform::application()` → `Application::run(launch_callback)` →
  `App::open_window(options, build_root_view)` (`observed fact`: `gpui_platform.rs:18-54`,
  `app.rs:327`, `app.rs:1558`).

- **Declarative element API.** `div()` + builder chain (`.flex()`, `.gap_2()`, `.bg()`,
  `.on_click()`, …), `canvas`, `img`/`svg`, `uniform_list`, `deferred`, `surface`, `list`
  (`observed fact`: `crates/gpui/src/elements/`, `README.md:15-116`). Views are `Entity<T: Render>`;
  stateless pieces are `RenderOnce`; element-scoped state via `use_state` (`observed fact`:
  `element.rs:385-466`, `examples/learn/creating_components.rs:1-40`).

- **Action/keybinding system.** `actions!` declares zero-data actions; `#[derive(Action)]` declares
  data-carrying ones; `KeyBinding::new(keystrokes, action, context)` maps keys;
  `InteractiveElement::on_action` handles them; focus + key-context tree drives dispatch
  (`observed fact`: `action.rs:15-110`, `crates/gpui/examples/learn/actions_and_keybinds.rs`).

- **Async/task API.** `cx.spawn` (foreground), `cx.background_executor().spawn` (Send futures),
  `Task<T>` with `.detach()`, `cx.notify()`/`emit()`/`observe()`/`subscribe()` for the observer
  graph (`observed fact`: `executor.rs:68-129,359-390`, `app.rs:1314`, `app.rs:1430`,
  `context.rs:146-256,416,1145`).

- **Platform trait surface (74 declarations).** This source count includes
  default bodies and target-gated methods, but not sibling traits. Window
  management, run loop, menus, clipboard (incl. async + primary/find
  pasteboards), credentials/keychain, file prompts, URL schemes,
  notifications, thermal state, haptics, keyboard layout, screen capture
  capability and app identity/restart are behind `dyn Platform`
  (`observed fact`: `crates/gpui/src/platform.rs:151-386`; `PlatformDisplay`
  begins at line 389).

- **GPU scene API.**
  `Window::paint_quad/paint_path/paint_image/paint_drop_shadows/paint_backdrop_filter/paint_layer…`,
  `Surface` API for custom shaders (`observed fact`: `window.rs:4439-4774`, `CHANGELOG.md` "Surface
  API for custom shaders" #237). Scenes compile to a `ScenePlan` (`scene/plan.rs`) consumed
  per-backend.

- **Text API.** `TextSystem` façade over `Arc<dyn PlatformTextSystem>`; `ShapedLine`/`LineLayout`;
  single Parley implementation (`ParleyTextSystem`) on all platforms since #267 (`observed fact`:
  `text_system.rs:14-34`, `CHANGELOG.md` breaking change #267).

- **Accessibility.** accesskit integration: per-frame `a11y_tree()`, node bounds, forced generation,
  programmatic actions, aria attributes on interactive elements (`observed fact`:
  `window.rs:7216-7268`, `CHANGELOG.md` #233/#234/#274/#279/#293).

- **Outbound-only I/O traits.** `HttpClient::get` (with `NullHttpClient` default; web backend
  supplies fetch) and `AssetSource`/`AssetRegistry` for bundled/on-demand assets — the framework
  makes no inbound network surface (`observed fact`: `http_client.rs:13-25`, `assets.rs:22-31`).

- **File/persistent artifacts owned by the framework:** none at the app level (it is a library). It
  *reads* system fonts, images (`png/gif/webp` by default; `image-default-formats` flag), SVG via
  resvg/usvg, cursor themes (`XCURSOR_PATH`), locale (`LC_CTYPE`).

## Runtime Lifecycle

Step-by-step trace with phase detail lives in `findings/runtime-lifecycle/runtime-lifecycle.md`
(secondary output). The short version:

1. **Boot.** `main()` → `gpui_platform::application()` builds an `Rc<dyn Platform>` for the host OS
   → `Application::with_platform` → `Application::run(|cx| …)` hands the closure to
   `platform.run(...)`, which starts the OS event loop and invokes the launch callback
   (`observed fact`: `gpui_platform.rs:18-36`, `app.rs:327-345`). `App` construction asserts it runs
   on the main thread (`observed fact`: `app.rs:945-949`).

2. **Window creation.** `App::open_window` inserts a `WindowId`, builds the root view via the caller
   closure, stores it as `window.root`, and forces one synchronous `draw` before returning (a
   Windows race fix — losing the race crashed on an empty dispatch tree, `observed fact`:
   `app.rs:1558-1592` comment).

3. **Frame (draw).** `Window::draw`: drain profiler state → enter per-`App` element arena →
   `invalidate_entities` → `draw_roots()` rebuilds the element tree by calling `Render::render` down
   the view hierarchy → `request_layout` (taffy nodes) → `prepaint` → `paint` emits `Primitive`s
   (Shadow/Quad/Path/Underline/sprites/Surface/BackdropFilter/FilterBoundary) into `Scene`
   (`observed fact`: `window.rs:3218-3260`, `scene.rs:392-437`) → `ScenePlan` compiled → backend
   `draw(scene)` presents (Metal `MetalRenderer::draw`, macOS `window.rs:2151`, wgpu `WgpuRenderer`)
   — then arenas clear and the plan's temporary allocations drop (`strong inference`: `draw()`
   epilogue + `layout_engine.clear()`, `text_system().finish_frame()`).

4. **Events.** OS event → `PlatformInput::{KeyDown,…,MouseMove,…,FileDrop,Touch}` (`observed fact`:
   `interactive.rs:771-800`) → `Window::dispatch_event` → hit-test against `bounds_tree` → element
   handlers; keystrokes additionally flow through the key-context dispatch tree and `Keymap` into
   typed `Action`s (`observed fact`: `window.rs:5871`, `key_dispatch.rs:140-327`).

5. **Scheduling inside a frame.** `pending_effects: VecDeque<Effect>`, dirty-view sets
   (`dirty_views`, `pending_notifications`), `on_next_frame`/`request_animation_frame` callbacks,
   deferred content-mask layers — all drained deterministically within `draw` (`observed fact`:
   `app.rs:857-899`, `window.rs:2682-2712`).

6. **Shutdown.** `quit_observers` / `QuitHandler`s run; `globals_by_type` drops last so entity tasks
   cancel before the Tokio runtime shuts down (a wrong order panics, `observed fact`:
   `app.rs:878-882` comment). Optional leak detection (`leak-detection` feature, `LEAK_BACKTRACE`
   env) reports leaked entities in test builds.

## Concurrency Model

- **Single-threaded core, enforced.** `ApplicationHandle::update` synchronously
  borrows its `Rc<AppCell>` and enters the app update; it does not send a
  message. `AsyncApp` holds a weak reference to the same app, upgrades and
  borrows it on update, and can be retained across await points.
  `AsyncWindowContext` wraps it. Neither is a worker-thread proxy, and
  re-entrant mutable borrowing is rejected. The platform scheduler hands
  foreground runnables to the main-thread dispatcher separately
  (`observed fact`: `crates/gpui/src/app.rs:186-215`,
  `crates/gpui/src/app/async_context.rs:57-69,238-250,448-452`,
  `crates/gpui/src/platform_scheduler.rs:109-122`).

- **Two executors, one scheduler interface.** `async-task` builds task
  handles and runnables; the platform dispatcher places foreground work on
  the UI thread and background `Send` work according to its own policy.
  The Linux background pool creates OS worker threads that consume queued
  runnables. Its weighted queue has high, medium and low lanes; this is not
  a universal dispatcher implementation. A dedicated session is a separate
  path, starting a fresh OS thread or a supported Wasm worker
  (`observed fact`: `crates/gpui_scheduler/src/executor.rs:229-251`,
  `crates/gpui/src/platform_scheduler.rs:109-122`,
  `crates/gpui_linux/src/linux/dispatcher.rs:30-52`,
  `crates/gpui/src/queue.rs:69-77`,
  `crates/gpui_scheduler/src/scheduler.rs:163-208`; protocols S8).

- **Threading matrix.** Production dispatchers are per-platform (`LinuxDispatcher`, macOS
  dispatch/GCD, Windows, web). `spawn_dedicated` spawns real OS threads — **on wasm it panics at
  runtime** unless the `wasm-threads` feature is on, which additionally requires shared-memory
  atomics build flags and swaps flume's mutex for a spinlock (browsers forbid `Atomics.wait` on the
  main thread) (`observed fact`: root `Cargo.toml` `wasm-threads` comment block).
  `portability hazard`: this whole threading story (GCD queues, Win32 threads, wasm workers vs
  shared memory) has no 1:1 translation; a port must re-derive it from the *contract* (main-thread
  UI + background `Send` pool + main-pump), not the mechanism.

- **Deterministic testing.** `TestClock` (virtual time from a fixed 2025-07-01 epoch),
  `TestDispatcher` (single-threaded) vs `ThreadedDispatcher` (production-like pool + timer thread +
  `run_until_idle`), `TestApp`/`test-support` harness, seeded runs (`SEED` env, `test-with-seed`
  recipe) (`observed fact`: `scheduler/clock.rs:14-30`, `threaded_dispatcher.rs:17-36`,
  `headless_app_context.rs:83`, `justfile` `test-with-seed`).

- **Shared-state primitives.** `parking_lot` locks + condvars in queues/dispatchers; `RefCell`
  arenas per frame (`element_arena`, `event_arena`); `FxHashMap`/`FxHashSet` (non-cryptographic
  FxHash — fast but unsalted, `observed fact`: `collections.rs` re-exports rustc-hash) for
  observer/subscriber tables; atomics only for ids and counters (`EntityId` via slotmap `KeyData`,
  `observed fact`: `entity_map.rs:32-60`).

## Build and Packaging

Detail lives in `findings/build-and-deploy/build-and-deploy.md` (secondary output). Essentials:

- **Cargo workspace**, resolver v3, workspace edition 2024. `gpui-ce` declares
  Rust 1.95 for `Vec::push_mut`; the workspace MSRV check uses 1.95.0
  (`observed fact`: root `Cargo.toml:29-33`, `crates/gpui/Cargo.toml:14`,
  `justfile:9,164-168`, `.github/workflows/ci.yml:132-148`).

- **Codegen at build time.** `gpui_render`'s build script compiles Rust-authored shader modules
  (`wgsl-rs`) to WGSL via `naga` and `include!`s them from `OUT_DIR` (`observed fact`:
  `gpui_render/Cargo.toml` build-deps + `artifacts.rs:1-10`); macOS links a bindgen step
  (`bindgen 0.72`); Windows embeds a manifest (`embed-resource`, `windows-manual` feature).

- **Task runner: `justfile`.** `check/build/test` (+`*flags` passthrough),
  `build-{linux,mac,windows}`, `check-wasm`, `check-wasm-atomics`, `check-examples`, `test-doc`,
  `test-nextest`, `lint` (= fmt + clippy with `deny` on `todo!`/`dbg!`/`redundant_clone` + typos +
  machete), `msrv-check`, `ci/ci-test/ci-tidy/ci-wasm`, `release-{version,sync,prepare,check}`,
  `publishable`, `sync-upstream*` (`observed fact`: `justfile` recipe list, `clippy.toml`, root
  `[workspace.lints.clippy]`).

- **CI (`.github/workflows/ci.yml`).** Change-aware orchestration (docs-only PRs skip tests), then
  `fmt`, `clippy`, `typos`, `lockfile`, `machete` (unused-dep check), `msrv`, `check-wasm`, per-OS
  `test-{linux,mac,windows}`, `check-examples`. Release trains (`release.yml`, `prerelease.yml`,
  `release-pr*.yml`, `release-tag.yml`) verify and publish all `gpui_ce_*` crates to crates.io plus
  GitHub releases; `audit.yml` runs cargo-deny/audit (`observed fact`: workflow job names,
  `deny.toml`, `audit.toml`).

- **Supply-chain posture.** `cargo-deny` bans unapproved licenses (allow-list
  MIT/Apache/BSD/ISC/Zlib/Unicode/0BSD/MPL/CC0/NCSA, with explicit clarifications for `wgsl-rs`),
  `cargo-audit`, `typos`, flake.nix Nix build (fenix toolchain + crane) (`observed fact`:
  `deny.toml`, `flake.nix:1-32`).

- **Upstream-sync machinery.** `scripts/sync-upstream/` implements a vendor-branch 3-way merge
  preserving upstream commit history, with LLM-driven conflict resolution and verify-fix loops;
  state in `state.json` (last synced Zed SHA `b1a7ef0…`, 2026-09-03) (`observed fact`:
  `sync_upstream.py` README, `state.json`). `portability hazard` for a port: none directly — but the
  port inherits drift risk; pinning to a synced SHA matters.

## Porting Priorities

| Component | Priority | Rationale |
|---|---|---|
| `App`/`Entity<T>`/`Context` observer graph + `Action`/keymap dispatch | core | Every app behavior routes through entities, notifications, and typed actions; without this nothing runs |
| `Element` 3-phase protocol (`request_layout`→`prepaint`→`paint`) + `Render`/`RenderOnce` + `Div`/style system | core | The entire declarative UI layer; layout/paint correctness is the framework's contract |
| taffy layout integration + `Style`/`Refineable` resolution | core | All geometry flows through it; `Relative`/`DefiniteLength` semantics are load-bearing (CHANGELOG #230/#255) |
| `Scene` primitives + `ScenePlan` + one software/headless raster path | core | The portable rendering contract; backends are interchangeable behind it |
| `Platform` trait + one full backend (headless or single OS) | core | Boot, windows, events, clipboard, timers — the OS seam every port must re-implement per target |
| `TextSystem` façade + Parley shaping/wrapping/hit-testing | important | Text correctness (bidi #263, font fallback, variable width #316) is user-visible; native rasterizers differ per OS |
| `BackgroundExecutor`/`ForegroundExecutor`/`Task` + main-thread pump | important | Async behavior (spawn ordering, priorities, timers) affects all apps; exact thread mapping is platform work |
| accesskit a11y tree generation | important | Required for parity on desktop workflows; tree is rebuilt per frame |
| `uniform_list`/`list` virtualization + `canvas`/`img`/`svg` elements | important | Needed for real-app parity (editors, image views) |
| `gpui_elements` (editable_text, switch), drag-drop, menus, notifications, screen capture | optional | Valuable but separable; several are platform-gated already |
| `inspector`, `debug_overlay`, `profiler`, hot-patching (`subsecond`), `tooling/perf` | optional | Developer tooling; not needed for first viable port |
| `gpui_tokio` bridge, `gpui_media`, layer-shell, keyring/credentials | optional | Narrow integrations; port on demand |
| `embed-resource` manifests, Nix flake, release trains, vouch governance | incidental | Source-repo ergonomics, not framework behavior |

## Durable State

GPUI is a library, not a service: it owns **no config files, no databases, no migration history**
(`strong inference`: no config-file readers found outside build tooling; all state is in-process
per-`App`). What persists or leaks across runs:

- **Environment variables read at runtime** (`observed fact`: grep): `WAYLAND_DISPLAY` / `DISPLAY`
  (backend selection, `platform.rs:117-122`), `ZED_HEADLESS` (force headless), `XCURSOR_PATH` +
  `LC_CTYPE` (Linux cursors/locale), `XDG_ACTIVATION_TOKEN` (Wayland activation),
  `XDG_CURRENT_DESKTOP` (character palette), `GPUI_X11_SCALE_FACTOR_ENV` (X11 DPI),
  `DISABLE_DIRECT_COMPOSITION` (Windows), `SEED` (deterministic test RNG), `LEAK_BACKTRACE` (leak
  reports), `GPUI_RUN_UNTIL_PARKED_LOG` (executor tracing). Compile-time: `TRACK_THREAD_BORROWS`
  (borrow logging).

- **Caches:** glyph atlas pages in GPU memory (`metal_atlas`, `wgpu_atlas`, `directx_atlas`); Swash
  font cache keyed by (source, collection face) after #406; font-metrics memo tables in
  `TextSystem`; `asset_cache`/`AssetRegistry` for bundled assets; per-frame arenas that must drain
  (`element_arena`, `event_arena`).

- **Generated artifacts:** `target/` (incl. `OUT_DIR` WGSL), embedded assets via `rust-embed`
  (`embedded-assets` feature), Windows manifest resources, macOS bindgen output.

- **Logs:** `env_logger` in tests, `gpui_web::init_logging` (browser console), tracing/profiling
  journals behind `profiler`.

## Agent Addressability

| Surface / concern | Headless | Inspectable state | Programmatic seam | Evidence | Notes (what an agent can and cannot do) |
|---|---|---|---|---|---|
| App boot + window creation | yes | yes | test | observed fact | `gpui_platform::headless()`, `TestApp`/`HeadlessApp` (`headless_app_context.rs`), `test-support` feature; no display needed |
| Frame rendering (element→scene) | yes | yes | test | observed fact | `Window::simulate_next_frame`, `painted_quads()`, `render_to_image` (macOS `window.rs:2418`); scene primitives are plain data an agent can assert on |
| GPU presentation (vsync, swapchain) | partial | no | none | strong inference | Requires a real compositor/GPU; headless renderers exist per-backend (`MetalHeadlessRenderer`, `WgpuHeadlessRenderer`) but pixel-parity with on-screen presentation is unverified — see `q-headless-parity` |
| Input dispatch (mouse/key/touch) | yes | yes | test | observed fact | `PlatformInput` enum is constructible; `dispatch_event` + `TestApp` keystroke simulation; `mouse_hit_test()` exposes hit results |
| Keymap/action dispatch | yes | yes | test | observed fact | Keymap + `ActionRegistry` are in-memory; `perform_a11y_action`, `on_action` handlers callable without OS keys |
| Async tasks/timers | yes | partial | test | observed fact | Virtual `TestClock` + `TestDispatcher`/`ThreadedDispatcher::run_until_idle`; wall-clock races still need real runs |
| Text shaping/wrapping | yes | yes | test | observed fact | Parley backend is pure computation; `LineLayout`/`ShapedLine` inspectable; needs fonts present (system or bundled) |
| a11y tree | yes | yes | test | observed fact | `a11y_tree()` returns the accesskit update; `set_a11y_forced(true)` builds it with no screen reader |
| Platform backends (Win32/objc2/Wayland/wasm) | no | partial | none | portability hazard | Behavior depends on OS APIs, GPU drivers, browsers; an agent can read the code but cannot observe it without the OS — this is a gap, not evidence of correctness |
| GPU fallback (no device) | no | no | none | open question | Error vs software-fallback behavior per platform not verified by reading — see `q-gpu-fallback` |
| Frame pacing (vsync/display-link) | partial | partial | none | open question | macOS `display_link.rs` observed; Linux/Windows pacing not verified — see `q-frame-scheduling` |

## Coverage and limits

- Inspected scope: repo root docs (`README`, `CONTRIBUTING`, `SETUP`, `CHANGELOG`, `MAINTENANCE`,
  `AI_POLICY`), workspace + all 24 crate manifests with feature tables, `justfile`, CI/release
  workflows, `deny/audit/typos/clippy` configs, `flake.nix`, `scripts/sync-upstream`,
  `crates/gpui/src/gpui.rs` (full module list + re-exports), `prelude.rs`, `app.rs` (Application/App
  structs, run/open_window/draw call sites), `window.rs` (draw/dispatch/paint/a11y entry points),
  `element.rs` (Element/Render/RenderOnce traits), `scene.rs` (Primitive enum), `platform.rs`
  (Platform trait), `interactive.rs` (PlatformInput), `entity_map.rs` (Entity/slotmap),
  `executor.rs` + `gpui_scheduler`, `text_system.rs` + parley crate shape, `gpui_render`
  shader-codegen path, backend crate file lists (macos/apple/linux/windows/web),
  `gpui_elements`/`gpui_macros`/`gpui_tokio`/util crates, `examples/learn` entry pattern, env-var
  grep across platform crates.

- Skipped scope: line-by-line reads of `window.rs` (9.7K LOC), platform backend internals (Win32
  proc, NSView delegates, Wayland/X11 protocol code, wasm bindings), full style/styled/taffy
  mapping, keymap file loading format, gesture/keystroke disambiguation details, profiler/journal
  internals, `tooling/perf` implementation, doc-site (`docs/`, typst).

- Evidence basis: source inspection only. No code was executed, no tests run, no runtime probed.

- Known blind spots: exact per-frame ordering guarantees beyond what `draw()` shows (e.g.
  effect-flush interleavings); Linux frame-pacing implementation; Windows/macOS GPU-recovery paths;
  keymap deserialization format; performance characteristics (no benchmarks run).

- Coverage disposition: PARTIAL

## Open Questions

| ID | Kind | Description | Deferred Reason |
|---|---|---|---|
| q-headless-parity | needs-runtime-test | Do headless/test renderers (`MetalHeadlessRenderer`, `WgpuHeadlessRenderer`, `TestApp` frames) produce pixel-identical scenes to on-screen presentation, so a port can use headless output as an oracle? | Requires running GPU and headless paths side by side; not answerable by reading. |
| q-gpu-fallback | needs-runtime-test | What happens on each platform when no GPU device/surface is available — error, software fallback, panic? Which error surfaces reach the app? | Failure paths live in backend init code not fully read; needs execution against GPU-less environments. |
| q-frame-scheduling | needs-runtime-test | What paces frames on Linux (Wayland/X11), Windows, and web (vsync callback, timer, display-link)? macOS `display_link.rs` seen; others not verified. | Requires platform event-loop observation; affects animation-timing port fidelity. |

## Carry-Forward

| ID  | Target Phase | Description | Deferred Reason |
| --- | ------------ | ----------- | --------------- |
|     |              |             |                 |

No carry-forward: the active pipeline (`pipeline-architecture-only.yaml`) contains only the
`architecture` phase, so there is no downstream phase to route items to. Genuinely unknown items are
recorded above as `open_questions`; a runtime frame-capture spike is proposed as post-pipeline work
in the handoff.

---

## Validation

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | The system intent is documented. | PASS | §System Intent (paragraph + fork-identity cites). |
| 2 | The layer map and dependency direction are documented. | PASS | §Layer Map: 24-crate inventory table with roles/entrypoints/deps; Dependency Direction with trait-seam, facade, and dev-only cycle analysis. |
| 3 | Public surfaces are identified. | PASS | §Public Surfaces summary + full catalog in secondary output `findings/public-surfaces/public-surfaces.md`. |
| 4 | Runtime lifecycle, concurrency model, and porting priorities are summarized. | PASS | §Runtime Lifecycle (6-stage trace), §Concurrency Model (single-thread core, executors, wasm matrix, test determinism), §Porting Priorities (table). |
| 5 | Findings are marked with evidence levels. | PASS | Every load-bearing claim tagged `observed fact` / `strong inference` / `portability hazard` / `open question` with file cites. |
| 6 | Coverage and limits name inspected scope, skipped scope, evidence basis, and blind spots. | PASS | §Coverage and limits; disposition PARTIAL, blind spots enumerated; unknowns tracked as `q-headless-parity`, `q-gpu-fallback`, `q-frame-scheduling`. |
| 7 | Agent addressability is assessed with evidence levels, and missing seams are recorded as hazards. | PASS | §Agent Addressability table (11 rows, all tagged); OS/GPU gaps recorded as hazards, not correctness claims. |

**Validated by:** 2026-11-21 (architecture phase, inline orchestrator+executor session)
**Overall:** PASS
