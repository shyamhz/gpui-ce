# Behavioral Contracts

## Surfaces Covered

GPUI-CE is a Rust library (API/SDK surface). No CLI, TUI, or bot surfaces exist.
Contracts below are written against the public Rust API so a reimplementation
in another language can honor the observable behavior without reading Rust.

B2d + B2c + B2a + B2b scope (this revision): animation/timing, layout/measurement,
elements/composition, and input/focus/keys contracts. Contracts for
text (B2e) and supporting systems (B2f) follow in later blocks; their
sections are marked PENDING, not absent.

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
| **Defaults** | Unsynced (elapsed measured from playlist start); `repeat` restarts the playlist; `repeat_synced` anchors elapsed time to the shared App epoch so animations on different elements advance in lockstep |
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
| **Trigger or input** | Elements insert hitboxes during paint with bounds + `HitboxBehavior` |
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
| **Observable output** | Bindings match on `key` (+ modifiers); text input consumes `key_char` |
| **Side effects** | None |
| **Persisted state** | None |
| **Error behavior** | `Keystroke::parse` returns `Result<_, InvalidKeystrokeError>` (markdown-renderable error); invalid keymap strings fail at parse, not silently |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`platform/keystroke.rs:18-60`) |
| **Evidence** | Observed fact: struct docs + `InvalidKeystrokeError` |

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

#### C24 Dispatch order: interceptors → handlers → keymap → IME

| Field | Value |
|---|---|
| **Feature** | `Window::dispatch_event` / `dispatch_keystroke` pipeline |
| **Trigger or input** | Any `PlatformInput` (17-type enum family incl. key/mouse/touch/file-drop) |
| **Defaults** | `propagate_event = true`, `default_prevented = false` per event; input modality tracked (Keyboard/Mouse/Touch) with hover suppression during keyboard modality |
| **Observable output** | Handlers run first (can `stop_propagation`); keystrokes then go through keymap matching; unmatched `key_char` input falls through to the focused text input handler; unhandled returns false |
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
| **Feature** | Capture → target → bubble dispatch with hit-test occlusion |
| **Trigger or input** | Mouse events resolved against hitboxes |
| **Defaults** | Occluding hitboxes (`InteractiveElement::occlude`) suppress mouse/hover/scroll/tooltip for everything behind (equivalent to a capture-phase handler calling `stop_propagation` when hovered) |
| **Observable output** | Handlers per phase; `DispatchEventResult { propagate }`; `default_prevented` flag |
| **Side effects** | None beyond handler effects |
| **Persisted state** | Per-frame hitbox lists |
| **Error behavior** | None |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`HitboxBehavior` docs `window.rs:1021-1040`; `dispatch_event`) |
| **Evidence** | Observed fact: behavior docs; propagate/prevent flags |

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

## High-Value Behaviors

B2d-relevant notes only; other blocks pending.

- **Frame pumping (follow-up behavior):** active transitions/animations re-request frames until settled/completed (`Transition::evaluate`, animation `done` flag). A port must implement demand-driven frame scheduling, not fixed-rate ticks, or idle apps will burn CPU and settled animations may overrun.
- **Wall-clock caution:** sampling uses read-time clocks (`Instant::now`, executor `now()`). Animation progress is a pure function of timestamps, but the timestamps themselves come from platform frame delivery — pacing guarantees stay with open question `q-frame-scheduling` (verify at runtime). No B2d finding asserts settled wall-clock behavior.
- Cancellation/abort, streaming/partial output, persistence/resume: not applicable to B2d scope (no persisted animation state across runs).

## Security and Authorization

Deferred to B2f with rationale: the framework is a library with no auth model (no users, sessions, or permissions). Credential storage (OS keychain via platform backends) is platform integration, covered under B2f supporting systems if its behavior proves contract-relevant. No auth contracts asserted in B2d.

## Configuration Model

Pointer to `findings/config-model/config-model.md` (architecture phase) for sources/precedence. B2d additions: `reduce_motion` flag (App-level, setter refreshes all windows). Remaining env/feature-flag behavior belongs to B2f. Animation-relevant config is exhausted by the flag above.

## Doc/Test Conflicts

None found in B2d scope. (Docs-vs-code comparison for animation: doc comments on `step`/`step_ramp`/`is_settled` match the implemented math; no test suite was executed — tests are read as contracts only where cited, none cited here beyond code-level doc examples.)

## Black-Box Acceptance List

B2d scenarios only; other blocks append theirs at phase completion.

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
| B2d-10 | max_fps throttle | Animation with `max_fps = N` | Observe frame callbacks | At most N evaluations per second |
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

## Coverage and limits

- Inspected scope (B2d): `motion.rs` (Motion/MotionSample/phase/dir/iteration, `sample`/`sample_at`, `checked_extent`, `resting_progress`); `spring.rs` (`step`/`step_ramp`/`propagator`/`is_settled`/`settle_time`); `animated.rs` (`set`/`restart`/`jump_to`/`adopt_completed_target`/`reset`/`sample`); `transition.rs` (`evaluate` frame pumping, `continuous`); `window.rs` `use_transition`/`use_keyed_transition`; `elements/animation.rs` (playlist, synced/unsynced elapsed, max_fps, reduce_motion); `app.rs` reduce-motion flag + epoch init; `style_transitions.rs` evaluate path + reduce branch.
- Inspected scope (B2c): `TaffyLayoutEngine` (`request_layout`, `request_measured_layout`, `compute_layout`, `layout_bounds`, `parent_relative_layout_bounds`); `ToTaffy` style mapping incl. hardcoded taffy-`Ltr` + grid templates; length resolution (`DefiniteLength`/`AbsoluteLength` impls) + `rem_size` override stack; `AvailableSpace` semantics; direction metadata + `resolve_directions`/targeted recompute; `VerticalAlign` default + accessor; `EXPECT_MESSAGE` panic sites (internal invariant, not filed).
- Inspected scope (B2a): element phase machine (`element.rs:670-955` guards + `compute_layout_as_root`); `ParentElement`/`IntoElement` composition + id-path scoping docs; `use_state`/`use_keyed_state`/`with_element_state` (`window.rs:4222-4300+`); `Hitbox`/`HitboxBehavior` (`window.rs:962-1041`); `uniform_list` ctor + `ListScrollEvent`; `canvas` callbacks; `deferred` priority; `Surface`/`ImageSource`/anchored/container-query builders.
- Inspected scope (B2b): `Keystroke` identity rules + `InvalidKeystrokeError` (`platform/keystroke.rs`); binding precedence docs + `match_keystrokes` + null-disable scoping (`keymap.rs:140-200`, `binding.rs:89-117`); `dispatch_key` pending/match/replay + `flush_dispatch` + 1s timeout task (`key_dispatch.rs:480-560`, `window.rs:6357-6420`); `dispatch_keystroke` fallthrough chain + modality tracking (`window.rs:5829-5920`); focus model (`window.rs:550-640`, `2372-2400`); mouse phases + occlusion docs; gesture module docs + event types.
- Skipped scope (later B2 blocks): input/focus/keys (B2b), text shaping (B2e), supporting systems incl. keyring/clipboard trust (B2f); per-`Styled`-method styling catalog (presentation details, not composition).
- Skipped scope (later B2 blocks): elements/composition (B2a), input/focus/keys (B2b), text shaping (B2e), supporting systems incl. keyring/clipboard trust (B2f); full `Styled` method catalog and grid edge cases (behavioral spot-checks only).
- Skipped scope (later B2 blocks): elements/composition (B2a), input/focus/keys (B2b), full style/taffy mapping (B2c), text shaping (B2e), supporting systems incl. keyring/clipboard trust (B2f).
- Evidence basis: source inspection (code + doc comments as specified behavior).
- Known blind spots: wall-clock pacing of frame timestamps (stays with `q-frame-scheduling`, needs runtime); exact `now` source in style-transition path (frame time vs read time — read as evaluate-time `now`, confirm in B2c/protocols if it matters); gesture/keyboard timing (B2b/B2e).
- Coverage disposition: PARTIAL (B2d block complete to its exit test; B2a–B2f pending by plan).

## Open Questions

None new from B2d. Wall-clock pacing inherits the standing `q-frame-scheduling` (needs-runtime-test); no B2d finding asserts settled wall-clock behavior, so no new entry is required.

| ID | Kind | Description | Deferred Reason |
|---|---|---|---|
| | | | |

## Carry-Forward

None from B2d (no downstream phase is active yet for routing; mech-CF1 to protocols stands from the mechanical phase and is unaffected).

| ID | Target Phase | Description | Deferred Reason |
|---|---|---|---|
| | | | |

---

## Validation

<!-- Phase incomplete: B2a–B2f pending. Validation runs at phase completion. -->

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | User-facing surfaces are split by surface type. | PENDING | API/SDK surface identified; full surface split at completion. |
| 2 | Feature contracts record trigger, defaults, outputs, side effects, persisted state, error behavior, and recovery behavior. | PENDING | B2d contracts complete per template fields; remaining blocks pending. |
| 3 | Security and authorization model is documented (if applicable). | PENDING | Deferred to B2f with rationale; skip-or-document decided at completion. |
| 4 | Contract ownership is mapped back to a layer or package. | PENDING | B2d ownership mapped; full map at completion. |
| 5 | A black-box acceptance list is included. | PENDING | B2d scenarios B2d-1–B2d-10 recorded; full list at completion. |
| 6 | Findings are marked with evidence levels. | PENDING | B2d claims tagged (all observed fact); phase-wide check at completion. |
| 7 | Coverage and limits name inspected scope, skipped scope, evidence basis, and blind spots. | PENDING | B2d scope recorded; full section at completion. |

**Validated by:** — (pending phase completion)
**Overall:** PENDING
