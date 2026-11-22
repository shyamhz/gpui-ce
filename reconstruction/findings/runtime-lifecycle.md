# Runtime Lifecycle

Frame-by-frame account of boot → event loop → frame → shutdown. The architecture map (`findings/architecture/architecture-map.md` §Runtime Lifecycle) owns the summary; this file owns the step-level trace. (`observed fact` unless noted.)

## 2026-11-21 — architecture phase

### Boot sequence

1. `fn main` (downstream app) calls `gpui_platform::application()`. Non-wasm: `Application::with_platform(current_platform(false))`; wasm: `WebPlatform::new_with_backend(Auto)` + fetch HTTP client; `web_init()` installs panic hook + logging first (`gpui_platform.rs:18-54`).
2. `Application::run(on_finish_launching)` clones `Rc<AppCell>`, calls `platform.run(Box::new(|| on_finish_launching(&mut app)))` (`app.rs:327-345`). The OS backend owns the event loop from here (NSApplication run, Win32 pump, calloop, browser rAF — backend files).
3. `App::new_app` (called during `with_platform`) asserts main-thread construction (`app.rs:945-949`), wires executors from the platform, builds `TextSystem` over `platform.text_system()`, creates `EntityMap`, keyboard layout/mapper, `AssetRegistry`, `SvgRenderer` (`app.rs:937-990 approx`).
4. Launch callback typically calls `App::open_window(options, |window, cx| Entity<V>)`.

### Window creation (`App::open_window`, `app.rs:1558-1592`)

Insert `WindowId` → `Window::new(handle, options, cx)` (creates `PlatformWindow` via `platform.open_window`) → push `window_update_stack` → build root view → `window.root.replace(view.into())` → schedule appearance check → **forced synchronous first `draw`** (Windows race fix; empty dispatch tree crashed `DispatchTree::root_node_id`) → store window. Returns `WindowHandle<V>`.

### Frame (`Window::draw`, `window.rs:3218-…`)

1. Profiler drain (feature-gated) → `ElementArenaScope::enter(&cx.element_arena)` (per-App arena isolates test Apps).
2. `invalidate_entities()`; `cx.entities.clear_accessed()`; reset `invalidator`, `requested_autoscroll`.
3. Restore previously-taken input handler into `rendered_frame.input_handlers` (slot-preserving `take()` dance for `reuse_paint` index stability).
4. Unless `cx.mode.skip_drawing()`: `draw_roots(cx)` — walks root views, calls `Render::render`, recursively `into_element()` → builds fresh element tree each frame (`strong inference`: `Render` docs "elements are consumed by the frame and dropped").
5. Layout: elements call `Window::request_layout(Style, children)` → taffy `LayoutId`s; engine cleared at frame end (`layout_engine.clear()`), buffer recycled (`layout_id_buffer`).
6. `prepaint` then `paint` per element → `Scene` accumulates `Primitive::{Shadow, Quad, Path, Underline, MonochromeSprite, SubpixelSprite, PolychromeSprite, Surface, BackdropFilter}` + `StartLayer/EndLayer` (`scene.rs:385-437`).
7. `text_system().finish_frame()`; `next_frame.finish(&mut rendered_frame)` → `ScenePlan` (`scene/plan.rs`, `MAX_FILTER_GROUP_DEPTH = 2` for isolated filter groups) → backend `draw(&scene)` presents; `present_if_needed` (`window.rs:3418`).
8. Input-handler registration for focused text input (`set_input_handler`, `text_input_state_changed FocusGained/FocusLost`); `dirty_views.clear()`; arena contents drop with the scope.

### Event dispatch (`Window::dispatch_event`, `window.rs:5871`; `handle_input`, `:5643`)

OS event → `PlatformInput` (17 variants: keys, modifiers, mouse ×5, pressure, scroll, pinch, long-press, touch-drag, file-drop, touch — `interactive.rs:771-800`) → `dispatch_event` → bounds-tree hit test → element mouse handlers / focus dispatch; keystrokes → focus-id + key-context resolution (`key_dispatch.rs` dispatch tree, `set_key_context/set_focus_id/set_view_id`, node reuse via `reuse_subtree`) → `Keymap` lookup → typed `Action` → `on_action` handlers (bubbling controlled by `propagate_event`, `app.rs:900`). `DispatchEventResult` returned to the platform (handled vs ignored).

### In-frame scheduling

`pending_effects: VecDeque<Effect>` + `flushing_effects` guard; `dirty_views` / `pending_notifications` / `pending_global_notifications`; `window_invalidators_by_entity`; `on_next_frame` / `request_animation_frame`; `Deferred` layers with auto-incrementing priority (`DeferredPriority`, `CHANGELOG #245`); synced-animation epoch clock (`synced_animation_epoch`) phase-locks repeating animations.

### Shutdown

`on_quit` callbacks (vetoable: `Box<dyn FnMut() -> bool>`); `quit_observers`/`restart_observers` (restart carries `restart_path` + args); drop order: entity tasks cancelled first, `globals_by_type` last (protects the Tokio runtime: spawning blocking tasks during teardown panics — `app.rs:878-882`); leak detector (`leak-detection`, `LEAK_BACKTRACE`) reports after everything else.
