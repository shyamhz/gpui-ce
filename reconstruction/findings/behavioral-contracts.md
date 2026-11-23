# Behavioral Contracts

## Surfaces Covered

GPUI-CE is a Rust library (API/SDK surface). No CLI, TUI, or bot surfaces exist.
Contracts below are written against the public Rust API so a reimplementation
in another language can honor the observable behavior without reading Rust.

The contracts cover two surfaces: the in-process component API (animation,
layout, composition, input, and text) and platform-facing SDK services
(accessibility, clipboard, credentials, popup windows, and desktop configuration).

## Feature Contracts

### API/SDK — animation and timing (B2d)

#### C1 Duration motion evaluation

| Field | Value |
|---|---|
| **Feature** | `Motion` (duration-based) evaluation |
| **Trigger or input** | `Motion::sample(elapsed)` / `sample_at(started_at, now)` with elapsed wall/framework time |
| **Defaults** | `Motion::default()` is a zero-duration motion; `Easing::default()` is linear; delay defaults to zero |
| **Observable output** | `MotionSample { progress (eased, may overshoot 0..1), local_time, iteration (u128), direction, phase (Delayed/Playing/Completed/Inactive), is_active }` |
| **Side effects** | None — evaluation is a pure function of elapsed time (`observed fact`: `motion.rs:652-743`) |
| **Persisted state** | None at this layer (callers hold `started_at`) |
| **Error behavior** | No errors; zero-duration passes and empty cycles resolve to `Inactive`/`Completed`, never panic |
| **Retry or recovery behavior** | N/A (pure computation) |
| **Owner (layer/package)** | `gpui` core (`motion.rs`) |
| **Evidence** | Observed fact: `MotionSample` fields and lifecycle (`motion.rs:227-300`); `sample_at` = `sample(now - started_at)` (`motion.rs:724-729`); `checked_extent` overflow-safe (`motion.rs:541-553`) |

#### C2 Spring motion evaluation

| Field | Value |
|---|---|
| **Feature** | Damped-harmonic-oscillator spring integration |
| **Trigger or input** | `SpringConfig::step` (fixed target) / `step_ramp` (constant-velocity target) per frame with `delta_time`; or `Motion::spring(config)` sampled like C1 |
| **Defaults** | Settle epsilon default (`DEFAULT_SPRING_EPSILON`); `is_settled` tests position within epsilon AND velocity within `epsilon * natural_frequency` |
| **Observable output** | New `(position, velocity)`; analytic propagator exact for the step (under/critical/over-damped branches selected by damping ratio vs 1.0 ± 1e-4) |
| **Side effects** | None — pure function of `(state, target, dt)`; retargeting preserves velocity without restarting |
| **Persisted state** | Caller-held `SpringState`; settling springs report iteration zero and nominal forward direction |
| **Error behavior** | No errors; an undamped spring has no finite settling time (`settle_time` returns `Duration::MAX`) |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`spring.rs`) |
| **Evidence** | Observed fact: `step`/`step_ramp`/`propagator`/`is_settled`/`settle_time` (`spring.rs:27-170`) |

#### C3 Transition handle (`use_transition` / `use_keyed_transition`)

| Field | Value |
|---|---|
| **Feature** | Element-scoped animated value with per-frame evaluation |
| **Trigger or input** | `window.use_transition(cx, motion, init)` (caller-location state) or `use_keyed_transition(key, …)` (keyed state); `Transition::evaluate(window, cx)` read during render |
| **Defaults** | Continuous retargeting (continue from current value); per-frame result cached |
| **Observable output** | Interpolated value; while active, evaluation requests the next animation frame (frame pumping until settle/complete) |
| **Side effects** | Frame scheduling (`request_animation_frame` while `is_active`); state keyed by caller location or explicit key |
| **Persisted state** | `TransitionState` entity (survives across frames while the call site/key is stable) |
| **Error behavior** | Sampling uses wall-clock `Instant::now()` at read time; a sample always contains a value (internal invariant) |
| **Retry or recovery behavior** | N/A (frames re-requested automatically while active) |
| **Owner (layer/package)** | `gpui` core (`transition.rs`, `window.rs:4381-4425`) |
| **Evidence** | Observed fact: `evaluate` samples + pumps frames (`transition.rs:108-144`); state hooks (`window.rs:4381-4425`) |

#### C4 Retarget continuity

| Field | Value |
|---|---|
| **Feature** | Mid-flight goal changes |
| **Trigger or input** | Goal update with a new target value (and/or new motion) |
| **Defaults** | Continuous: sample current presentation, restart the run from it (no visual jump; spring velocity preserved) |
| **Observable output** | `restart` variant restarts from the initial value instead (`Animated::restart`); `jump_to` snaps immediately and clears run state; `adopt_completed_target` aligns END presentation with the logical target so a later retarget does not jump |
| **Side effects** | Run restart (new `started_at`); `reset` restores initial value |
| **Persisted state** | `last_value`, `settled_progress`, `started_at` in `Animated` |
| **Error behavior** | None (goal equality short-circuits: no new run when value unchanged) |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`animated.rs:82-144`) |
| **Evidence** | Observed fact: `set`/`restart`/`jump_to`/`adopt_completed_target` (`animated.rs:82-144`) |

#### C5 Animation element playlist

| Field | Value |
|---|---|
| **Feature** | Declarative `Animation` element (sequential motion playlist) |
| **Trigger or input** | `Animation::new(motion)` + `.repeat()` / `.repeat_synced()` / `.with_easing()` / `.with_max_fps()`; playlist advances when the current motion's sample goes inactive |
| **Defaults** | Unsynced (elapsed measured from the current item's start). `repeat` loops the configured motion, not the playlist; `repeat_synced` also uses the shared app epoch. |
| **Observable output** | Animator closure receives `(element, animation_ix, delta)` per frame; `max_fps` throttles via timer + delayed frame |
| **Side effects** | Frame scheduling while any playlist item is active; `reduce_motion` jumps to the resting progress of the LAST animation and marks done |
| **Persisted state** | `AnimationState { start, animation_ix }` per element |
| **Error behavior** | `debug_assert` on finite delta (non-finite values are a bug, caught in debug) |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`elements/animation.rs`) |
| **Evidence** | Observed fact: playlist advance, synced/unsynced elapsed, max_fps throttle, reduce_motion jump (`elements/animation.rs:380-440`); epoch init (`app.rs:919,952`) |

#### C6 Global reduce-motion

| Field | Value |
|---|---|
| **Feature** | `App::reduce_motion` / `set_reduce_motion` accessibility override |
| **Trigger or input** | App-level setter; honored by transitions (jump to endpoint) and `Animation` elements (jump to resting progress, done) |
| **Defaults** | Off (`false` at App creation) |
| **Observable output** | State changes render statically at targets; setter refreshes all windows once |
| **Side effects** | Full-window refresh on change; animations needed to show state (e.g. progress bars) are the documented exception and keep running |
| **Persisted state** | App-level bool |
| **Error behavior** | None |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`app.rs:1240-1257`; honored in `style_transitions.rs`, `elements/animation.rs`) |
| **Evidence** | Observed fact: flag, setter with refresh (`app.rs:1240-1257`); `jump_to` on reduce (`style_transitions.rs:269`; `animation.rs` reduce branch) |

### API/SDK — layout and measurement (B2c)

#### C7 Flex/grid layout via version-pinned taffy

| Field | Value |
|---|---|
| **Feature** | Element tree layout through taffy 0.13.0 (=0.13.0 pin) |
| **Trigger or input** | `Window::request_layout(style, children)` / `TaffyLayoutEngine::request_layout` (container) or `request_measured_layout` (measured leaf); then `compute_layout(id, available_space, direction, …)` per frame |
| **Defaults** | `Position::Relative` (unlike CSS); `AvailableSpace::MinContent` is the enum default; engine rebuilt every frame (`layout_engine.clear()` in `draw()`) |
| **Observable output** | `LayoutId` → `layout_bounds(id, scale_factor)` in `Pixels`; per-node cached available spaces drive targeted recompute on direction change |
| **Side effects** | Taffy node allocation per frame; direction resolution pass precedes layout |
| **Persisted state** | None across frames (nodes re-requested every frame); within a frame: node metadata (display/position, direction, vertical-align) |
| **Error behavior** | Taffy construction errors panic via `expect(EXPECT_MESSAGE)` ("avoid by construction") — internal invariant, not a user path |
| **Retry or recovery behavior** | N/A (deterministic recompute) |
| **Owner (layer/package)** | `gpui` core (`taffy.rs`); exact flex/grid semantics delegated to taffy 0.13.0 — a port must match that version's behavior, not just any flexbox |
| **Evidence** | Observed fact: `request_layout`/`request_measured_layout`/`compute_layout`/`record_style` (`taffy.rs:106-200, 426-470`); full flex+grid mapping (`taffy.rs:837-935`); pin (`Cargo.toml`) |

#### C8 Length resolution (absolute, relative, auto)

| Field | Value |
|---|---|
| **Feature** | `Length`/`DefiniteLength` → device pixels |
| **Trigger or input** | Style construction with `Absolute` / `Relative(f32)` / `Auto` lengths |
| **Defaults** | `Absolute` resolves through `rem_size` (override stack, else window root) and is pre-snapped via `round_to_device_pixel` before reaching taffy |
| **Observable output** | `Relative(x)` becomes exactly `x` fraction of the parent (`Dimension::percent`); `Auto` is content-driven (measured leaves) or absorbs free space |
| **Side effects** | None |
| **Persisted state** | None |
| **Error behavior** | None (total mapping; `..Default::default()` for unmapped taffy fields) |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`taffy.rs:955-1010`) |
| **Evidence** | Observed fact: `ToTaffy` impls for `DefiniteLength`/`AbsoluteLength`/`Length` |

#### C9 Available space and measured leaves

| Field | Value |
|---|---|
| **Feature** | Measure protocol for text/content leaves |
| **Trigger or input** | Taffy invokes the `measure(known_dimensions, available_space, window, cx) -> Size<Pixels>` closure supplied at `request_measured_layout` time |
| **Defaults** | Unconstrained axes arrive as `MinContent`/`MaxContent`, never as silently-zero definite space |
| **Observable output** | Returned `Size<Pixels>` becomes the leaf's size for that layout pass |
| **Side effects** | Bidi metadata (`effective_unicode_bidi`) recorded per node at request time |
| **Persisted state** | Per-node direction metadata (`authored`, `resolved`, logical children) |
| **Error behavior** | None at this layer (measure runs user/text code; its errors are the caller's) |
| **Retry or recovery behavior** | Taffy may invoke measure repeatedly during one layout (constraint refinement) — closures must be idempotent and side-effect free |
| **Owner (layer/package)** | `gpui` core (`taffy.rs:133-200`); text implementation in `text_system` (B2e owns shaping specifics) |
| **Evidence** | Observed fact: `request_measured_layout` signature + `NodeContext`; strong inference on repeat invocation (taffy measure protocol, version-pinned) |

#### C10 Bounds snapping and caching

| Field | Value |
|---|---|
| **Feature** | Layout → pixel bounds with device-grid snapping |
| **Trigger or input** | `layout_bounds(id, scale_factor)` after `compute_layout` |
| **Defaults** | Absolute edge snapping (`round_half_toward_zero` on both corners) so coincident edges close; text uses parent-relative placement so intra-element offsets stay stable across the pixel grid |
| **Observable output** | `Bounds<Pixels>` = snapped device bounds ÷ scale factor; results cached per node (`absolute_layout_bounds`) |
| **Side effects** | Recursive parent-origin accumulation on first query per frame |
| **Persisted state** | Per-frame caches, cleared with the layout engine |
| **Error behavior** | Missing parent origin panics (`expect`, internal invariant) |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`taffy.rs:630-696`) |
| **Evidence** | Observed fact: `layout_bounds` + `parent_relative_layout_bounds` with stability comment |

#### C11 Direction resolution precedes layout

| Field | Value |
|---|---|
| **Feature** | Bidi/direction handling outside taffy |
| **Trigger or input** | `compute_layout` resolves directions for the subtree first (`resolve_directions`), then lays out; changed subtrees are recomputed with cached bounds cleared |
| **Defaults** | Taffy itself is always fed `Direction::Ltr`; GPUI's own layer owns `LayoutDirection`/`UnicodeBidi` semantics |
| **Observable output** | Resolved direction per node; direction-only changes recompute just the affected subtree |
| **Side effects** | Targeted cache invalidation (`clear_cached_bounds`) |
| **Persisted state** | Per-node direction metadata |
| **Error behavior** | None |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`taffy.rs` direction metadata + `compute_layout`) |
| **Evidence** | Observed fact: hardcoded `Direction::Ltr` in mapping (`taffy.rs:837-935`); `resolve_directions` + `clear_cached_bounds` in `compute_layout` |

#### C12 Inline layout and vertical alignment

| Field | Value |
|---|---|
| **Feature** | `Display::Inline`/`InlineFlex` with `VerticalAlign` |
| **Trigger or input** | `Styled::inline()` / `inline_flex()` + `vertical_align(...)` / `align_baseline|top|middle|bottom()` |
| **Defaults** | `VerticalAlign::Baseline` (only non-default values are recorded per node) |
| **Observable output** | Inline fragments laid out in text order with the requested alignment |
| **Side effects** | Per-node vertical-alignment + display/position metadata |
| **Persisted state** | `vertical_alignments` / `display_and_position` maps, per frame |
| **Error behavior** | None |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`taffy.rs` metadata, `vertical_align()` accessor) |
| **Evidence** | Observed fact: `record_style` non-default recording; `vertical_align()` default (`taffy.rs:169-177, 327-331`) |

### API/SDK — elements and composition (B2a)

#### C13 Element three-phase protocol

| Field | Value |
|---|---|
| **Feature** | `Element::request_layout` → `prepaint` → `paint` state machine |
| **Trigger or input** | Framework drives phases per frame; custom elements implement the three methods |
| **Defaults** | Phase order enforced by panic (`must call request_layout only once`, `…before prepaint`, `prepaint before paint`, `cannot measure after painting`); re-measure with unchanged available space reuses cached layout |
| **Observable output** | LayoutId → bounds → paint primitives; violations abort with the documented message |
| **Side effects** | Taffy node allocation; element-id stack push/pop for state scoping |
| **Persisted state** | Per-frame `ElementDrawPhase`; nothing persists across frames except via ids |
| **Error behavior** | Out-of-order or duplicate phase calls panic (fail-fast contract enforcement, same policy as 1.1-style id panics) |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`element.rs:670-955`) |
| **Evidence** | Observed fact: phase enum + guard panics; `compute_layout_as_root` space caching |

#### C14 Composition and identity

| Field | Value |
|---|---|
| **Feature** | `ParentElement::child/children` builders; `IntoElement` conversion; id paths |
| **Trigger or input** | Builder chains (`div().child(…)`); `id()` on stateful elements |
| **Defaults** | Typeless `ParentElement` accepts any `IntoElement`; `ParentElementTyped` constrains row types |
| **Observable output** | Element tree rebuilt every frame; an element's state is found again by its id path from the window root — the path includes every ancestor that has an id, so two same-id elements under different id-less parents collide |
| **Side effects** | None beyond tree construction |
| **Persisted state** | State keyed by `(GlobalElementId, TypeId)` across frames |
| **Error behavior** | Type mismatch on state reuse panics in debug with requested-vs-actual types |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`element.rs:179-520`) |
| **Evidence** | Observed fact: trait docs on id paths; `with_element_state` keying + debug type check (`window.rs`); call-site collision documented for `use_state` |

#### C15 Element-scoped state

| Field | Value |
|---|---|
| **Feature** | `use_state` / `use_keyed_state` / `with_element_state` |
| **Trigger or input** | Called during render/draw with an init closure; `use_state` keys by caller source location (`#[track_caller]`), `use_keyed_state` by explicit key |
| **Defaults** | Reused if the same id existed in the rendered frame; a change observer is auto-attached that notifies the current view |
| **Observable output** | `Entity<S>` handle; state lives while the element renders in consecutive frames |
| **Side effects** | Observer registration (auto-notify on change) |
| **Persisted state** | Element states map keyed `(GlobalElementId, TypeId)`, transferred rendered→next frame |
| **Error behavior** | Called outside render/draw fails debug assertions; list items sharing a call site share state (documented: use keyed state there) |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`window.rs:4222-4300+`) |
| **Evidence** | Observed fact: `use_state`/`use_keyed_state`/`with_element_state` docs + bodies |

#### C16 Hit-testing

| Field | Value |
|---|---|
| **Feature** | `Hitbox` registration + `mouse_hit_test` |
| **Trigger or input** | Elements insert hitboxes during prepaint with bounds and `HitboxBehavior` (`window.rs:5530-5555`). |
| **Defaults** | `Normal` (no effect on others); occluding behavior blocks mouse events, hover styles, and tooltips for hitboxes behind |
| **Observable output** | `HitTest` inspectable via `mouse_hit_test()`; `hitbox.is_hovered()` reflects occlusion |
| **Side effects** | None beyond registration |
| **Persisted state** | Per-frame hitbox lists |
| **Error behavior** | None |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`window.rs:962-1040`, hit-test query) |
| **Evidence** | Observed fact: `Hitbox` struct + `HitboxBehavior` docs |

#### C17 Virtualized uniform list

| Field | Value |
|---|---|
| **Feature** | `uniform_list(id, item_count, render_range)` |
| **Trigger or input** | Item count + `Fn(Range<usize>, …) -> Vec<R>` invoked with the visible range |
| **Defaults** | Vertical scroll overflow; only the visible subset renders per frame |
| **Observable output** | Rows for `visible_range`; `ListScrollEvent { visible_range, count, … }` on scroll |
| **Side effects** | Scroll handling; pending-scroll anchoring across remeasure |
| **Persisted state** | `ListState` (scroll offset, pending scroll, follow state) |
| **Error behavior** | None at this layer (range arithmetic reviewed in B1a, benign) |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`elements/list.rs`, `uniform_list.rs`) |
| **Evidence** | Observed fact: constructor signature + overflow default (`uniform_list.rs:22-35`); event emission (`list.rs:943-957`) |

#### C18 Canvas custom drawing

| Field | Value |
|---|---|
| **Feature** | `canvas(prepaint, paint)` escape hatch |
| **Trigger or input** | Two `FnOnce` callbacks: prepaint receives bounds, returns state; paint receives bounds + state |
| **Defaults** | No retained state between frames beyond what the callbacks close over |
| **Observable output** | Direct `Window` paint calls (quads, paths, text) inside paint |
| **Side effects** | Caller-defined |
| **Persisted state** | None (framework holds no canvas state) |
| **Error behavior** | None |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`elements/canvas.rs:8-22`) |
| **Evidence** | Observed fact: constructor docs + signature |

#### C19 Deferred paint layers

| Field | Value |
|---|---|
| **Feature** | `deferred(child)` out-of-order painting |
| **Trigger or input** | Wrapped child + priority (`priority_auto` = 1 + previous deferred priority) + optional content mask |
| **Defaults** | Painted after all non-deferred content in priority order |
| **Observable output** | Deferred draws composited per `paint_range` bookkeeping |
| **Side effects** | Deferred-draw queue per frame |
| **Persisted state** | Per-frame queue only |
| **Error behavior** | None |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`elements/deferred.rs:95-106`) |
| **Evidence** | Observed fact: `priority_auto` docs + `DeferredPriority` |

#### C20 Images, SVG, surfaces, overlays

| Field | Value |
|---|---|
| **Feature** | `img`, `svg`, `surface`, `anchored`, `container_query` elements |
| **Trigger or input** | `img(ImageSource::{Resource, Render, Image, Custom(loader fn)})`; `svg()` builder; `surface(SurfaceSource)` custom-shader content; `anchored()` overflow-avoiding overlay at an anchor corner; `container_query(render_fn)` receiving container `Size` |
| **Defaults** | Custom image loader returns `Option<Result<…>>` (absence tolerated); anchored avoids window overflow by default |
| **Observable output** | Rasterized images / SVG scenes / GPU surfaces / positioned overlays / size-dependent content |
| **Side effects** | Image-cache loading; surface registration |
| **Persisted state** | Image cache; surface handles |
| **Error behavior** | SVG parse/render errors propagate as `Result` (B1b-verified); custom loader `None` = no image |
| **Retry or recovery behavior** | None specified at this layer |
| **Owner (layer/package)** | `gpui` core (`elements/img.rs:42-51`, `svg.rs`, `surface.rs:13-109`, `anchored.rs`, `container_query.rs:33-39`) |
| **Evidence** | Observed fact: source-variant enums + builder signatures |

### API/SDK — input, focus, and keys (B2b)

#### C21 Keystroke identity

| Field | Value |
|---|---|
| **Feature** | `Keystroke { modifiers, key, key_char }` produced by the platform |
| **Trigger or input** | Physical key press on the host layout |
| **Defaults** | `key` = printed character, or ASCII-equivalent on non-ASCII layouts (Thai `ๆ` → `q`); `key_char` = typed character (`s` → `s`, `option-s` → `ß`, `cmd-s` → `None`) |
| **Observable output** | Binding matching also tries a distinct `key_char` before the `key`/modifier pair. That character match retains only Control and Platform modifiers outside Windows; on Windows it requires an unmodified binding. Text input consumes `key_char`. |
| **Side effects** | None |
| **Persisted state** | None |
| **Error behavior** | `Keystroke::parse` returns `Result<_, InvalidKeystrokeError>` (markdown-renderable error); invalid keymap strings fail at parse, not silently |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`platform/keystroke.rs:18-60`) |
| **Evidence** | Observed fact: `platform/keystroke.rs:18-60,82-113` |

#### C22 Binding precedence

| Field | Value |
|---|---|
| **Feature** | `Keymap::bindings_for_input` / `possible_bindings_for_input` ordering |
| **Trigger or input** | Keystroke sequence + key-context stack along the focus dispatch path |
| **Defaults** | Deeper context wins (Editor > Pane > Workspace); context-less bindings rank as deepest; ties broken by reverse insertion order (user bindings added after built-ins win) |
| **Observable output** | Matching bindings in precedence order; boolean whether longer input could still match |
| **Side effects** | None |
| **Persisted state** | Keymap registry |
| **Error behavior** | Disabled (`null`) bindings never returned; a null suppresses only equal-or-weaker precedence (base null hides defaults, user bindings still apply) |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`keymap.rs:140-200` incl. precedence docs) |
| **Evidence** | Observed fact: `all_bindings_for_input` / `bindings_for_input` docs + `match_keystrokes` (`binding.rs:89-101`) |

#### C23 Multi-keystroke dispatch with pending input

| Field | Value |
|---|---|
| **Feature** | Prefix accumulation, timeout flush, replay-as-text |
| **Trigger or input** | Keystroke sequence that is a strict prefix of some binding |
| **Defaults** | Pending keystrokes stored per focus; 1s timeout (`Duration::from_secs(1)`, hardcoded) flushes via `flush_dispatch` |
| **Observable output** | While pending: nothing dispatched, `pending_input_changed` notified; on full match: bindings fire; on mismatch/timeout: unmatched suffix replayed as text input |
| **Side effects** | Timer spawned only when needed (`pending_has_binding` or text input requires timeout); focus change or blur clears pending state |
| **Persisted state** | `pending_input { keystrokes, focus, timer }` per window |
| **Error behavior** | Unmatched input is never swallowed — it is replayed as text or dropped only after replay resolution |
| **Retry or recovery behavior** | Suffix retried against the tree after prefix replay (`dispatch_key` recursion) |
| **Owner (layer/package)** | `gpui` core (`key_dispatch.rs:480-560`; `window.rs:6357-6420`) |
| **Evidence** | Observed fact: `dispatch_key` pending/match/replay logic; timeout task; `flush_dispatch` |

#### C24 Keyboard dispatch and character input

| Field | Value |
|---|---|
| **Feature** | `Window::dispatch_event` / `dispatch_keystroke` pipeline |
| **Trigger or input** | Any `PlatformInput`, including keyboard, mouse, touch, and file-drop events (`interactive.rs:771-800`) |
| **Defaults** | `propagate_event = true`, `default_prevented = false` per event; input modality tracked (Keyboard/Mouse/Touch) with hover suppression during keyboard modality |
| **Observable output** | Interceptors precede keymap matching. Matching actions are tried before ordinary key-event dispatch unless character input takes priority. The `dispatch_keystroke` helper sends `key_char` to the input handler if its synthetic keydown still propagates. |
| **Side effects** | Mouse position/modifier caching on the window; modality-change refresh |
| **Persisted state** | `pending_input`, modality, mouse position |
| **Error behavior** | Interceptors can stop propagation before matching; `prevent_default` flag recorded |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`window.rs:5829-5920`, `6340-6420`) |
| **Evidence** | Observed fact: `dispatch_keystroke` fallthrough chain; modality tracking (`dispatch_event` head) |

#### C25 Focus model

| Field | Value |
|---|---|
| **Feature** | `FocusHandle` / `Window::focus` / `blur` / tab order |
| **Trigger or input** | `handle.focus()` / `window.blur()` / tab navigation (`tab_index`, `tab_stop`) |
| **Defaults** | Handles are ref-counted with weak downgrade; `tab_stop(false)` excludes from tab order |
| **Observable output** | `is_focused` / `contains_focused`; focus change bumps `focus_generation` (wrapping) and refreshes; pending keystrokes cleared on focus change and blur |
| **Side effects** | Refresh on change; `disable_focus` blocks all future focusing |
| **Persisted state** | `FocusMap`, current `focus: Option<FocusId>` per window |
| **Error behavior** | Focus on a released handle is a no-op via weak upgrade (`for_id` returns `None`) |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`window.rs:550-640`, `2372-2400`) |
| **Evidence** | Observed fact: handle struct + focus/blur bodies |

#### C26 Mouse dispatch phases

| Field | Value |
|---|---|
| **Feature** | Capture and bubble dispatch with hit-test occlusion; no separate target phase in this loop. |
| **Trigger or input** | Mouse events resolved against hitboxes |
| **Defaults** | Occluding hitboxes (`InteractiveElement::occlude`) suppress mouse/hover/scroll/tooltip for everything behind (equivalent to a capture-phase handler calling `stop_propagation` when hovered) |
| **Observable output** | Handlers per phase; `DispatchEventResult { propagate }`; `default_prevented` flag |
| **Side effects** | None beyond handler effects |
| **Persisted state** | Per-frame hitbox lists |
| **Error behavior** | None |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`HitboxBehavior` docs `window.rs:1021-1040`; `dispatch_event`) |
| **Evidence** | Observed fact: `window.rs:6213-6260` invokes listeners in stored order for capture and reverse order for bubble, stopping each pass when propagation is disabled. |

#### C27 Touch, gesture, scroll, file-drop

| Field | Value |
|---|---|
| **Feature** | Portable gesture recognition + raw input events |
| **Trigger or input** | Raw touch streams, scroll wheels, OS file drops |
| **Defaults** | Single in-core recognizer arena: recognizers compete for in-flight touches, winners claim them, losers are cancelled |
| **Observable output** | Recognized gestures surface as semantic events where possible: tap → `ClickEvent::Touch`, pan → `ScrollWheelEvent` with `TouchPhase`, pinch → `PinchEvent`; `FileDrop(FileDropEvent)` for OS drops; `OngoingScroll` filtering with iOS/Android physics tuning |
| **Side effects** | None beyond event delivery |
| **Persisted state** | In-flight touch state per gesture |
| **Error behavior** | None specified |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`gestures.rs` module docs + event types; `interactive.rs` `PlatformInput`) |
| **Evidence** | Observed fact: module design docs; `ScrollPhysics::ios/android`; `TouchDragEvent`/`LongPressEvent` types |

### API/SDK — text behavior (B2e)

Paths in this section are relative to the repository root. Source assertions below were
inspected, not executed.

#### C28. Shaping and visual rows

| Field | Value |
|---|---|
| **Trigger or input** | Shape UTF-8 text with a font size and ordered style runs. Run lengths count bytes, cover the whole string, and end at character boundaries. |
| **Defaults** | Wrap width and row clamp are optional; paragraph base direction defaults to automatic. Alignment width is independent of wrap width. |
| **Observable output** | One document layout accounts for explicit line breaks, trailing empty rows, soft wrapping, and the visual row clamp. A font/style run describes a source span, not a row or a glyph. |
| **Side effects and state** | In-memory layout reuse; no persistent write. |
| **Error and recovery** | Use the document API for multiline input: the single-line wrapper only *debug-asserts* against `\n`, despite its unconditional panic wording. The document wrapper returns `Result` but wraps the layout in `Ok`; the Parley adapter uses `expect` if its internal layout fails. Do not assume malformed run input returns a recoverable error. |
| **Owner and evidence** | Observed fact: `crates/gpui/src/text_system/window_text_system.rs:38-104`, `crates/gpui/src/text_system/text_layout.rs:6-41`, and `crates/gpui_ce_parley/src/text_system.rs:4218-4251,4312-4354` (document fixtures and assertions), `:2500-2506` (adapter). |

#### C29. Hit testing and caret geometry

| Field | Value |
|---|---|
| **Trigger or input** | Query a shaped document with a pixel point and line height, or with a UTF-8 byte index and optional caret affinity. |
| **Defaults** | Position lookup by bare byte index attaches the caret to the next cluster; at a shared wrap boundary this selects the following row. |
| **Observable output** | A cluster hit gives its logical start, including whitespace. The closest-caret query selects cluster boundaries; for an RTL cluster the visual left edge corresponds to its logical end. Position lookup snaps interior indices to the start of an atomic cluster. Visual caret movement is separate from finding a logical neighbor. |
| **Side effects and state** | Read-only against a shaped layout; no persistent write. |
| **Error and recovery** | Off-line points return the appropriate edge result in the error branch, not an empty hit. Index-to-position returns `None` past the source length. Affinity-aware lookup can distinguish caret placements that a byte index alone cannot. |
| **Owner and evidence** | Observed fact: `crates/gpui/src/text_system/line_layout.rs:710-813`; off-line caret results also asserted in `crates/gpui_ce_parley/src/text_system.rs:4768-4772`. |

#### C30. Font selection and fallback

| Field | Value |
|---|---|
| **Trigger or input** | Resolve a font descriptor against the adapter's catalog, or shape text with descriptor-specific fallbacks. |
| **Defaults** | A newly constructed Parley adapter has an empty catalog. Bootstrap may add system fonts or register explicit font bytes. |
| **Observable output** | Canonical face lookup tries the descriptor family, its ordered fallbacks, then configured adapter fallbacks. For `.SystemUIFont`, the generic system UI family is tried before its configured named substitute. Face lookup order is not an exhaustive claim about Fontique's per-character substitution. |
| **Side effects and state** | Font registration changes the in-memory catalog and advances its generation, clearing Parley's paragraph caches. No writes to host font storage are required by these APIs. |
| **Error and recovery** | Canonical lookup returns an error when no family resolves. Adding a suitable font or configuring a fallback can make a later lookup succeed. Installed font sets and resulting glyph choices are not portable fixtures. |
| **Owner and evidence** | Observed fact: `crates/gpui_ce_parley/src/text_system.rs:1469-1538,1542-1599,2708-2757`. The fallback test uses explicit font fixtures and tests generic, named, and descriptor fallback precedence. |

#### C31. Rasterization boundary

| Field | Value |
|---|---|
| **Trigger or input** | Paint a shaped glyph at its resolved placement and request a raster for its selected font instance, glyph, and draw parameters. |
| **Defaults** | Parley provides layout; the platform selects the injected rasterizer. There is no promise of identical system font metrics or pixels across hosts. |
| **Observable output** | The rasterizer receives the face and variations identified by the shaped font instance. The window looks up or inserts glyph data in its atlas before painting; shaping alone does not produce the final pixels. |
| **Side effects and state** | Raster and atlas data are held in memory; no persistent write is specified. |
| **Error and recovery** | Unknown font IDs and raster failures return errors at the adapter boundary; atlas lookup/insertion errors propagate from the window glyph-paint path. Do not infer a universal retry or replacement-glyph policy. |
| **Owner and evidence** | Observed fact: `crates/gpui_ce_parley/src/text_system.rs:2431-2448`, `crates/gpui/src/window.rs:4892-4901`. Adapter examples: `crates/gpui_linux/src/linux/platform.rs:139`, `crates/gpui_web/src/platform.rs:163`, `crates/gpui_macos/src/text_system.rs:20`, `crates/gpui_windows/src/direct_write.rs:87`. |

### Supporting services — component API (B2f)

#### C32. Image loading and fallback

| Field | Contract |
|---|---|
| **Trigger and defaults** | An image source is evaluated during layout. Loading and error replacement builders are both absent by default. The loader result distinguishes pending (`None`), ready, and failed. |
| **Output and state** | Ready data supplies the image. With retained element state, pending data can display the loading view after the 200 ms delay; a timer notifies the view so layout can re-evaluate it. On error, a configured fallback becomes the replacement element. Loading state and cache entries are in memory, not a persistence contract. |
| **Failure and recovery** | Error clears the pending indicator state. The loading timer is a redraw request, not an automatic fetch retry. Resource locations use the asset or image-cache path; custom loaders supply their own results. |
| **Owner and evidence** | Observed fact: `crates/gpui/src/elements/img.rs:31-38,130-145,382-423,537-552`. |

#### C33. Gesture recognition and scroll bounds

| Field | Contract |
|---|---|
| **Trigger and defaults** | Raw touch enters the recognizer (C27); scrolling changes a container's in-memory offset. The default recognizer locks a sufficiently horizontal pan to the horizontal axis in the checked-in test. |
| **Output and state** | Pan publishes scroll events. During layout the scrollable container clamps each offset to `[-maximum, 0]`, with a nonnegative maximum from padded content minus viewport. A pending scroll-to-bottom request sets the vertical offset to `-maximum`. |
| **Failure and recovery** | If content shrinks or the viewport grows, the old offset is clamped to the new extent rather than retained out of bounds. No durable state or retry is involved. Recognition thresholds and momentum mechanics belong to the protocols investigation. |
| **Owner and evidence** | Observed fact: `crates/gpui/src/gestures.rs:1370-1386` (axis-lock assertion), `crates/gpui/src/elements/div.rs:3143-3204` (rounding, clamping, and request consumption). |

### Supporting services — platform-facing SDK (B2f)

#### C34. Accessibility inspection and actions

| Field | Contract |
|---|---|
| **Trigger and defaults** | Build the tree when accessibility is active; forcing it requests redraw and builds without an assistive client. Explicitly inaccessible application creation overrides forcing. |
| **Output and state** | Last-frame tree is optional, with a build counter starting at zero and optional logical-pixel node bounds. IDs remain stable with element identity. These are in-memory observations. |
| **Failure and recovery** | An absent tree is not an empty successful snapshot. On non-Wasm targets the programmatic action API tries the registered node listener before built-in click, focus, or blur. For a fresh observation, wait for a tree-producing frame after forcing. |
| **Owner and evidence** | Observed fact: `crates/gpui/src/window.rs:7203-7286`; external assistive-client behavior is not established by these entry points. |

#### C35. Clipboard

| Field | Contract |
|---|---|
| **Trigger and defaults** | Read or replace the host clipboard. Synchronous read returns an optional item and is always `None` in the web adapter. Awaitable read reports an optional item or a typed read error. |
| **Output and state** | Contents are host-owned. Primary-selection access is target-gated to Linux/FreeBSD; the Find pasteboard API is gated to macOS. Writing returns no acknowledgement; the web text-write path drops the browser promise. |
| **Failure and recovery** | Do not use a web synchronous `None` as evidence that the host clipboard is empty. Use the async path to observe rejection or unavailability; no automatic retry is promised. |
| **Owner and evidence** | Observed fact: `crates/gpui/src/app.rs:1740-1823`; `crates/gpui_web/src/platform.rs:556-630,691-703`. Actual browser permission grants are outside this contract. |

#### C36. Credential-store adapter

| Field | Contract |
|---|---|
| **Trigger and defaults** | Await storage, retrieval, or deletion of a username and password bytes keyed by a caller-supplied URL string. |
| **Output and state** | Storage is delegated to the platform keychain where supported. `Ok(None)` means no item is reported; it does not prove a store is available. |
| **Failure and recovery** | On web, read completes with `Ok(None)` and write/delete complete with an unsupported error. Failures are returned to callers; no retry or account lifecycle is provided. |
| **Owner and evidence** | Observed fact: `crates/gpui/src/app.rs:1826-1850`; `crates/gpui_web/src/platform.rs:631-647`. |

#### C37. Anchored platform popups

| Field | Contract |
|---|---|
| **Trigger and defaults** | Open an `AnchoredPopup` using a parent handle and a rectangle in the parent's coordinate space. Defaults are centered placement, zero offset, no constraint adjustments, and no grab. This is not the in-window `anchored()` element from C20. |
| **Output and state** | The Wayland adapter resolves the parent among its current windows. For an explicit grab it uses a recorded press serial if available; it supplies no grab if no such serial exists. Popup state is window-scoped, not durable. |
| **Failure and recovery** | Missing Wayland parent returns an error. macOS, Windows, X11, and web reject this window kind with `PopupNotSupportedError`. The caller can choose an in-window overlay; no automatic fallback is promised. Actual compositor grant or dismissal is not asserted. |
| **Owner and evidence** | Observed fact: `crates/gpui/src/platform/popup.rs:34-88`; `crates/gpui_linux/src/linux/wayland/client.rs:1074-1098`; rejection branches in `crates/gpui_macos/src/platform.rs:686`, `crates/gpui_windows/src/window.rs:424`, `crates/gpui_linux/src/linux/x11/window.rs:469`, and `crates/gpui_web/src/platform.rs:360`. |

#### C38. Linux/FreeBSD backend and X11 scale overrides

| Field | Contract |
|---|---|
| **Trigger and defaults** | `current_platform(true)` explicitly selects headless. Otherwise the selection checks for `ZED_HEADLESS` by presence, then nonempty `WAYLAND_DISPLAY` and `DISPLAY` for compiled-in backends, in that order. If none match, it chooses headless. |
| **Output and state** | A process-local backend is constructed. In the X11 scale path, a positive normal numeric `GPUI_X11_SCALE_FACTOR` overrides detection; `randr` selects RandR lookup; unset or empty uses automatic detection. |
| **Failure and recovery** | Selection is not a connectivity probe; the constructor does not try another backend after the chosen X11 initialization errors. Invalid scale values panic on the reached X11 path (mechanical F6.1), not warn-and-fallback. No persistent configuration write or retry is specified. |
| **Owner and evidence** | Observed fact: `crates/gpui/src/platform.rs:107-135`; `crates/gpui_linux/src/linux.rs:27-55`; `crates/gpui_linux/src/linux/x11/client.rs:2535-2579,2775-2777`. |

## High-Value Behaviors

- **Frame pumping (follow-up behavior):** active transitions/animations re-request frames until settled/completed (`Transition::evaluate`, animation `done` flag). A port must implement demand-driven frame scheduling, not fixed-rate ticks, or idle apps will burn CPU and settled animations may overrun.
- **Wall-clock caution:** sampling uses read-time clocks (`Instant::now`, executor `now()`). Animation progress is a pure function of timestamps, but the timestamps themselves come from platform frame delivery — pacing guarantees stay with open question `q-frame-scheduling` (verify at runtime). No B2d finding asserts settled wall-clock behavior.
- Cancellation/abort, streaming/partial output, persistence/resume: not applicable to B2d scope (no persisted animation state across runs).

## Security and Authorization

No framework account, session, or role model is specified. The reviewed APIs
delegate clipboard access and credential storage to the host (C35–C36);
the URL string is a lookup key, not an authorization decision.

## Configuration Model

See `findings/config-model/config-model.md` for the architecture inventory.
C38 records precedence and malformed-input behavior for the inspected backend
settings. C6 covers the app-level reduce-motion flag. These are mechanism-specific
controls, not one universal settings precedence rule.

## Doc/Test Conflicts

The single-line text API documents a panic on newlines; the guard is debug-only
(C28). Checked-in assertions were read where cited, not executed.

## Black-Box Acceptance List

Scenarios below are planned acceptance checks, not reported test runs.

| # | Scenario | Precondition | Action | Expected Outcome |
|---|---|---|---|---|
| B2d-1 | Zero-duration motion completes immediately | `Motion` with zero duration, just started | Sample at any `elapsed >= 0` | Phase `Completed`, progress END, `is_active` false |
| B2d-2 | Delay gate | Motion with delay D | Sample at `elapsed < D` | Phase `Delayed`, progress at start value, `is_active` true |
| B2d-3 | Retarget continuity | Transition mid-flight at value V | Set new goal | Presentation continues from V with no jump (default); restarts from initial only if `continuous(false)` |
| B2d-4 | Reduce motion | `reduce_motion` true, transition/animation active | Next frame renders | Target/resting value presented immediately; animation marked done |
| B2d-5 | Synced lockstep | Two `repeat_synced` animations on different elements | Advance wall clock | Both report identical progress at identical times |
| B2d-6 | Spring settle | Underdamped spring toward fixed target | Sample past `settle_time` | Value stays within epsilon of target; `is_active` false |
| B2d-7 | Undamped spring never settles | Zero-damping spring | Sample at any time | `is_active` remains true (settling time is infinite) |
| B2d-8 | Infinite iterations never complete | Motion with `Iterations::Forever` | Sample at any time | Phase never `Completed` |
| B2d-9 | Completed run reports final iteration | Finite motion, elapsed past total duration | Sample | Phase `Completed`, iteration equals final index |
| B2d-10 | Animation-driven timer throttle | Active animation with an ordinary positive finite cap and no external redraws | Inspect requests with a controlled clock | One pending timer per animation state at a time; its callback requests another update after the configured interval, not a global frame cap |
| B2c-1 | Relative sizing | Child with `Relative(0.5)` width in a fixed-width parent | Lay out and read bounds | Child width equals half the parent width |
| B2c-2 | Rem scaling | Same tree rendered under two `rem_size` roots | Compare absolute-positioned bounds | Bounds scale with the root rem size |
| B2c-3 | Min-content default | Unconstrained leaf (e.g. text) with no definite size | Lay out with indefinite space | Leaf sizes to its min content, never to zero-or-unbounded |
| B2c-4 | Measured leaf stability | Text leaf under identical constraints, two frames | Compare returned sizes | Identical `Size<Pixels>` (measure is pure for identical inputs) |
| B2c-5 | Edge closing | Two adjacent boxes sharing an edge coordinate | Read both bounds | No gap and no overlap between the coincident edges |
| B2c-6 | Direction change isolation | Subtree direction flipped, rest of tree untouched | Recompute and read bounds | Only the affected subtree's bounds change |
| B2c-7 | Inline baseline default | Inline children with no explicit alignment | Lay out | Children align on the text baseline |
| B2c-8 | Engine freshness | Layout queried, then a new frame draws with changed styles | Read bounds after the new frame | Bounds reflect the new styles (no stale per-frame state) |
| B2a-1 | Phase-order enforcement | Custom element calling paint before prepaint | Draw the frame | Panic with the documented phase message |
| B2a-2 | State persistence by id | Stateful element with stable id, state mutated | Draw next frame unchanged | State value retained |
| B2a-3 | Call-site collision | Two `use_state` calls at the same call site in a loop | Draw | Both share one state (documented: use keyed state) |
| B2a-4 | Occlusion | Occluding hitbox in front of a hoverable element | Move mouse over the overlap | Behind element reports not-hovered; no hover style |
| B2a-5 | Virtualization window | 10k-row uniform_list scrolled to the middle | Count rendered rows | Only the visible subset renders; scroll event reports the matching range |
| B2a-6 | Canvas order | Canvas with recording prepaint + paint | Draw one frame | Prepaint runs before paint with the same bounds |
| B2a-7 | Deferred ordering | Deferred child with higher priority inside normal content | Draw | Deferred content paints after non-deferred, higher priority on top |
| B2a-8 | Container query resize | `container_query` element under a resized parent | Draw after resize | Render fn receives the updated container size |
| B2b-1 | Precedence depth | Same keystroke bound in Editor and Workspace contexts, focus in Editor | Press the key | Editor binding fires, Workspace does not |
| B2b-2 | User-over-default | User binding added after a default for the same keystrokes | Press the key | User binding fires |
| B2b-3 | Pending then match | Two-key binding, first key typed | Observe | Nothing dispatched yet; typing the second key fires the binding |
| B2b-4 | Pending timeout replay | Two-key binding prefix typed, then pause > 1s with a text field focused | Wait | Prefix text appears in the field (replayed), no binding fires |
| B2b-5 | Focus change clears pending | Prefix typed, then focus moves to another element | Type the second key | Treated as a fresh single keystroke, not a sequence completion |
| B2b-6 | Null disable scoping | Base keymap nulls a binding that user keymap also defines | Press the key | User binding still fires |
| B2b-7 | Occlusion | Occluding element in front of a hoverable element | Hover the overlap | Behind element is not hovered; no hover style |
| B2b-8 | Modality hover suppression | Mouse resting over an item, then keyboard navigation begins | Press an arrow key | Hover highlight on the mouse-resting item is suppressed |
| B2e-1 | Empty and trailing rows (C28) | Fixed font; no clamp; wide enough to avoid wrapping | Shape `""` and `"one\n"` separately | Empty text yields one empty row, width zero, no paint fragments; trailing break yields a second row |
| B2e-2 | Visual-row clamp (C28) | Fixed font and width for which the unclamped input wraps to at least three rows | Shape with clamp set to two | Exactly two visual rows |
| B2e-3 | Line-edge hit (C29) | A shaped LTR line and y-coordinate inside that row | Query the closest caret strictly left and strictly right of the row | Both results signal an outside hit and report the respective row edge; indices are source byte boundaries |
| B2e-4 | RTL cluster (C29) | A visible multi-byte RTL cluster with nonzero advance | Hit just inside each visual edge using the closest-caret query | Left maps to logical end, right to logical start; neither returns an interior byte |
| B2e-5 | Explicit font precedence (C30) | Register two distinct fixture families A and B; adapter fallback starts with A; requested family unavailable | Resolve it first without and then with descriptor fallback B | First lookup returns A; second returns B |
| B2e-6 | Raster error propagation (C31) | Controlled rasterizer returns an error for a known glyph on an atlas miss | Paint that glyph through the window glyph API | Call reports a failure; it does not claim a successful atlas insertion |
| B2f-1 | Image fallback (C32) | Custom loader reports an error; fallback supplied | Lay out the image | Fallback appears rather than the loading view |
| B2f-2 | Scroll after content shrinks (C33) | Existing negative offset lies outside the new extent | Remove content and lay out again | Offset stays inside the new range; it is zero if content now fits |
| B2f-3 | Forced accessibility (C34) | Accessible window, no assistive client, visible accessible element | Enable forcing and draw | A fresh tree and node bounds are available; tree counter advances |
| B2f-4 | Clipboard and credential capability (C35–C36) | Web backend | Call synchronous clipboard read and await credential read/write | Clipboard read is `None`; credential read reports no entry; credential write reports unsupported |
| B2f-5 | Unsupported popup (C37) | X11 backend and a valid parent | Request an anchored platform popup | Typed unsupported error, not an implicit replacement window |
| B2f-6 | Backend precedence (C38) | Build with both backends; both display variables nonempty | Evaluate compositor selection with and without `ZED_HEADLESS` present | Headless with the override, Wayland without it; this tests selection, not connection |

## Coverage and limits

- Inspected scope (B2d): `motion.rs` (Motion/MotionSample/phase/dir/iteration, `sample`/`sample_at`, `checked_extent`, `resting_progress`); `spring.rs` (`step`/`step_ramp`/`propagator`/`is_settled`/`settle_time`); `animated.rs` (`set`/`restart`/`jump_to`/`adopt_completed_target`/`reset`/`sample`); `transition.rs` (`evaluate` frame pumping, `continuous`); `window.rs` `use_transition`/`use_keyed_transition`; `elements/animation.rs` (playlist, synced/unsynced elapsed, max_fps, reduce_motion); `app.rs` reduce-motion flag + epoch init; `style_transitions.rs` evaluate path + reduce branch.
- Inspected scope (B2c): `TaffyLayoutEngine` (`request_layout`, `request_measured_layout`, `compute_layout`, `layout_bounds`, `parent_relative_layout_bounds`); `ToTaffy` style mapping incl. hardcoded taffy-`Ltr` + grid templates; length resolution (`DefiniteLength`/`AbsoluteLength` impls) + `rem_size` override stack; `AvailableSpace` semantics; direction metadata + `resolve_directions`/targeted recompute; `VerticalAlign` default + accessor; `EXPECT_MESSAGE` panic sites (internal invariant, not filed).
- Inspected scope (B2a): element phase machine (`element.rs:670-955` guards + `compute_layout_as_root`); `ParentElement`/`IntoElement` composition + id-path scoping docs; `use_state`/`use_keyed_state`/`with_element_state` (`window.rs:4222-4300+`); `Hitbox`/`HitboxBehavior` (`window.rs:962-1041`); `uniform_list` ctor + `ListScrollEvent`; `canvas` callbacks; `deferred` priority; `Surface`/`ImageSource`/anchored/container-query builders.
- Inspected scope (B2b): `Keystroke` identity rules + `InvalidKeystrokeError` (`platform/keystroke.rs`); binding precedence docs + `match_keystrokes` + null-disable scoping (`keymap.rs:140-200`, `binding.rs:89-117`); `dispatch_key` pending/match/replay + `flush_dispatch` + 1s timeout task (`key_dispatch.rs:480-560`, `window.rs:6357-6420`); `dispatch_keystroke` fallthrough chain + modality tracking (`window.rs:5829-5920`); focus model (`window.rs:550-640`, `2372-2400`); mouse phases + occlusion docs; gesture module docs + event types.
- Inspected scope (B2e): document layout API and fixture assertions, caret query semantics,
  canonical font fallback, glyph dispatch, and atlas error propagation (C28–C31).
- Inspected scope (B2f): C32–C38, including controlled source and test paths for
  loading, gestures, scroll, accessibility, platform I/O, popups, and configuration.
- Skipped scope: full style/grid matrix; shaping engine internals,
  per-character fallback, rasterizer internals, and platform-dependent pixel comparison.
- Evidence basis: source inspection, API docs, and checked-in test assertions. No runtime tests run.
- Known blind spots: wall-clock pacing of frame timestamps (stays with `q-frame-scheduling`, needs runtime); exact `now` source in style-transition path (frame time vs read time — read as evaluate-time `now`, confirm in B2c/protocols if it matters); gesture/keyboard timing (B2b/B2e).
- Secondary outputs: no additions needed to public surfaces, runtime lifecycle,
  state and storage, or configuration model. Their architecture catalogs are
  retained; the added observable contracts live here.
- Coverage disposition: COMPLETE for the scheduled contracts blocks, not an
  exhaustive API catalog or a runtime verification claim.

## Open Questions

No new terminal questions registered. The existing headless parity, GPU
fallback, and frame-pacing questions remain unresolved; no runtime closure
is proposed by this phase.

## Carry-Forward

The prior `mech-CF1` route to protocols remains unchanged.

| ID | Target Phase | Description | Deferred Reason |
|---|---|---|---|
| contracts-CF1 | protocols | Trace gesture claim/cancel/momentum transitions and the Wayland anchored-popup configure/dismiss lifecycle. | C33 and C37 establish surface observations, not event order or state-machine completeness. |

---

## Validation

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | User-facing surfaces are split by surface type. | PASS | Surfaces Covered and Feature Contracts distinguish component and platform SDKs. |
| 2 | Feature contracts record trigger, defaults, outputs, side effects, persisted state, error behavior, and recovery behavior. | PASS | C1–C38 cover the scheduled features; related fields are combined in supporting-service rows. |
| 3 | Security and authorization model is documented (if applicable). | PASS | Security and Authorization; C35–C36 describe the inspected host services. |
| 4 | Contract ownership is mapped back to a layer or package. | PASS | Owner and evidence fields in Feature Contracts. |
| 5 | A black-box acceptance list is included. | PASS | Black-Box Acceptance List covers all six blocks; scenarios are not test results. |
| 6 | Findings are marked with evidence levels. | PASS | Evidence fields distinguish source assertions and inference; runtime questions remain open. |
| 7 | Coverage and limits name inspected scope, skipped scope, evidence basis, and blind spots. | PASS | Coverage and limits and the explicit protocol handoff. |

**Validated by:** 2026-11-23 (contracts phase)
**Overall:** PASS
