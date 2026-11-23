# Protocols and State

**Blocks B3a–B3c — events, state machines, rendering and scheduling.**
B3d and phase validation are pending.
Code locations below are relative to the repository root.


## Boundaries Identified

- **Host → window:** adapters translate native or browser input into a tagged
  `PlatformInput` value. A separate callback family carries window lifecycle
  signals. Neither boundary uses a serialized GPUI wire format.

- **Window → application:** dispatch routes normalized input to registered
  listeners, key bindings, and the touch recognizer. Delivered clicks are
  a separate semantic event, not another `PlatformInput` case.

- **Application → observers:** the application queues typed effects for delivery
  within its update lifecycle.

**Evidence — observed fact:** `crates/gpui/src/platform.rs:939-948`,
`crates/gpui/src/window.rs:1971,5871,6004-6010`, and
`crates/gpui/src/app.rs:3528-3551`.


## Event Catalog

### Normalized input envelope

| Field | Contract |
|---|---|
| Producer | Platform adapter, or code that explicitly dispatches a normalized input value. Representative adapters: AppKit (`crates/gpui_macos/src/events.rs:130-135,192,243,271`), Win32 (`crates/gpui_windows/src/events.rs:394,442,594`), Wayland and X11 (`crates/gpui_linux/src/linux/wayland/client.rs:1965,2180` and `crates/gpui_linux/src/linux/x11/client.rs:1120,1193`), browser (`crates/gpui_web/src/events.rs:245,594,656,733`). |
| Consumer and carrier | Window-scoped `on_input` callback receives `PlatformInput` and returns `DispatchEventResult`; native message formats stay on the adapter side. |
| Ordering | A dispatch initializes propagation and default-prevention flags before routing. Mouse listeners run capture in stored order, then bubble in reverse order if propagation continues. This does not impose a total order across windows or platforms. |
| Required and optional data | See all variants below. Positions are window-relative logical pixels where present. |
| Identity and time | Window is implicit in callback registration. `TouchId` identifies a contact; no common sequence number or timestamp appears in the envelope. |
| Failure and resume | The synchronous reply exposes `propagate` and `default_prevented`, not an error or delivery acknowledgement. No durable replay or resume mechanism is defined by this carrier. Key-prefix replay is separate (contracts C23). |

**Evidence — observed fact:** `crates/gpui/src/platform.rs:940`,
`crates/gpui/src/window.rs:2153-2159,5871-5900,6213-6260`,
`crates/gpui/src/interactive.rs:771-800`.

### All 14 `PlatformInput` variants

The table is exhaustive for the enum, not for each adapter's emitted subset.
Payloads are **observed facts** from the listed source definitions.

| Variant | Required payload | Optional payload |
|---|---|---|
| `KeyDown` | Keystroke, held flag, prefer-character-input flag | Typed character within the keystroke |
| `KeyUp` | Keystroke | Typed character within the keystroke |
| `ModifiersChanged` | Modifiers, Caps Lock state | — |
| `MouseDown` | Button, position, modifiers, click count, first-mouse flag | — |
| `MouseUp` | Button, position, modifiers, click count | — |
| `MousePressure` | Pressure, stage, position, modifiers | — |
| `MouseMove` | Position, modifiers | Pressed button |
| `MouseExited` | Position, modifiers | Pressed button |
| `ScrollWheel` | Position, modifiers, touch phase, tagged delta: pixels or lines | — |
| `Pinch` | Center, signed zoom delta, modifiers, phase | — |
| `LongPress` | Phase, starting position, current position | — |
| `TouchDrag` | Phase, starting position, current position | — |
| `FileDrop` | Nested phase: `Entered(position, paths)`, `Pending(position)`, `Submit(position)`, `Exited`, or `Ended` | — |
| `Touch` | Contact ID, phase, position | Predicted position and contact force |

**Source:** `crates/gpui/src/interactive.rs:25-259,493-586,665-800`,
`crates/gpui/src/platform/keystroke.rs:18-33`, and
`crates/gpui/src/gestures.rs:383-420`.

**Normalization notes — observed facts:**

- `TouchPhase` distinguishes `Started`, `Moved`, `Ended`, and `Cancelled`.
  The identity and prediction rules in `interactive.rs:88-135` describe the
  interface. Its start-target delivery comment is explicitly marked pending;
  actual routing and cancellation must be traced in B3b.

- `ClickEvent` has mouse, keyboard, and recognized-touch forms, none of which
  is a member of the normalized enum (`interactive.rs:290-299,771-800`).

- A native file-drop update can become ordinary pointer input before routing:
  `Pending` becomes a left-button-held move; `Submit` becomes a left-button
  release. `Exited` and `Ended` follow distinct cleanup paths
  (`window.rs:5955-5984`). Full state transitions are not inferred here.

### Window lifecycle callbacks

**Evidence — observed fact:** `crates/gpui/src/platform.rs:812-819,939-948`.
These are in-memory adapter-to-window callbacks; the registered window is the
implicit identity and there is no standard timestamp, serialized transport,
or replay contract.

| Signal | Payload | Return / interpretation |
|---|---|---|
| Frame request | `require_presentation`, `force_render` | No return; flags separate presentation from forced redraw. Not a presentation-completion event. |
| Active or hover status | One boolean | Notification; not a veto. |
| Resize | Logical size and scale factor | Notification carrying both values. |
| Move, appearance, button-layout change | None | Notification; button-layout registration has a default no-op. |
| Should close | None | Synchronous boolean decision. |
| Close | None | One-shot callback, distinct from the decision callback. |
| Window-control hit test | None | Synchronous optional window-control area. |

**Source-level frame clues, not measurements:** X11 registers a `calloop`
timer in `crates/gpui_linux/src/linux/x11/client.rs:1983-2012`; Wayland forwards
a frame callback at `crates/gpui_linux/src/linux/wayland/client.rs:1494`;
the browser schedules `requestAnimationFrame` and has a separate resize-triggered
frame path (`crates/gpui_web/src/window.rs:350-359,415-423`). These establish
candidate trigger paths, not observed cadence, visibility behavior, or present
timing. Windows trigger coverage remains for B3c/B3d.

### Application effect envelope

**Evidence — observed fact:** `crates/gpui/src/app.rs:3528-3551` declares
effects processed at the end of the application update cycle.

- `Notify`: emitter identity. `Emit`: emitter identity, event type identity,
  and a typed payload held through the arena.
- `RefreshWindows`: no payload. `NotifyGlobalObservers`: global type identity.
- `Defer`: a one-shot callback. `EntityCreated`: entity, type identity, and
  optional window identity.

The carrier is in memory; the enum supplies no timestamp, wire encoding or
restart data. Ordering within an update, coalescing, listener removal, and
reentrancy are B3b work, not guarantees implied by this catalog.


## State Machine


### S1. Window lifetime and frame publication

**Observed fact.** `crates/gpui/src/app.rs:1558-1590,2235-2285` and
`crates/gpui/src/window.rs:1710-1729,3218-3369`. See contracts C13–C16 and C25
for element-facing behavior; the catalog above distinguishes close request from
close notification.

| State → state | Trigger and guard | Side effects / barrier |
|---|---|---|
| Absent → reserved → live | `open_window`; backend construction succeeds | Build and install root, draw synchronously, clear its arena token, store window, then return handle. Drawing is not presentation. |
| Reserved → absent | Backend construction returns an error | Remove reserved slot and return error. |
| Live → borrowed → live | Successful window lookup and take, then normal update return | The registry slot is temporarily empty during the callback. Restore it before the enclosing update flush. An unavailable slot does not supply a second mutable window. |
| Borrowed → removed | Update marks window removed; native close callback can request removal | Remove handles and entity/window links, notify close observers, then consider quitting under `QuitMode`. |
| Last rendered + building → published | Finish the new frame | Reconcile accessed state and finish the scene, snapshot old focus data, swap `rendered_frame` and `next_frame`, then clear the recycled frame. Focus notifications observe the newly published frame. Presentation is a separate operation. |

### S2. Focus and queued application effects

**Observed fact.** `crates/gpui/src/window.rs:2372-2404,3301-3354,6350-6420`
and `crates/gpui/src/app.rs:1264-1283,2013-2075,2146-2179`. See contracts
C15, C23 and C25.

- Focus requests are ignored when disabled or already on that ID. An accepted
  change updates the logical focus, bumps its generation, clears pending keys
  and requests refresh. Blur clears pending input and removes focus when
  enabled. The rendered dispatch path is a separate snapshot: after the frame
  swap, compare old/new paths and active state to notify listeners. A focus
  change made by those listeners can request another draw.

- An update increments nesting depth. On normal exit, the outermost update
  starts the drain unless a drain is already active. Each iteration releases
  dropped entities and focus handles, then pops the oldest queued effect.
  Callbacks can enqueue more work for the same drain. `Notify` deduplicates
  pending entries by entity, and global notifications by type; `Emit` is not
  deduplicated by that queue insertion logic. Notify removes its pending mark
  before delivery, so a new notification during delivery is not suppressed
  merely because an earlier one ran. This is not a panic-recovery guarantee.

### S3. Element traversal and frame-index ownership (`mech-CF1`)

**Observed fact.** `crates/gpui/src/element.rs:579-605,670-700,825-950`;
`crates/gpui/src/view.rs:539-557,595-607,644-660`;
`crates/gpui/src/window.rs:1273-1284,3235-3252,3296-3309,3650-3774,3793-3863`;
`crates/gpui/src/key_dispatch.rs:100-107,264-307`. See contracts C13–C15 and C19.

1. An element starts unmeasured, requests layout, may compute/recompute
   its root layout, then prepaints and paints. Guards reject repeated or
   out-of-order calls; repeated root measurement can reuse a result under
   the same available space.

2. A cached view can reuse prepaint when there is no fresh element, its
   cache key matches (bounds, mask, text style, direction and bidi), the view
   is not dirty, and refresh is not forcing a rebuild. Reuse reads ranges
   from `rendered_frame`, appends to `next_frame`, and replaces stored ranges
   with their new destinations. Paint similarly records its new span on
   both fresh and reuse paths.

3. Deferred prepaint keeps its vector in place while running nested rounds;
   snapshots use that vector's indices. Deferred entries copied from the old
   frame remap `parent_node` into the copied dispatch subtree and rewrite
   their own prepaint/paint spans as processed. Input-handler transfer uses
   an empty slot rather than removing an indexed entry. Unused old records
   are cleared at frame rotation.

**Strong inference — disposition for F1.2:** On the traced normal path,
source ranges belong to the currently rendered frame and destination ranges
are rebased before publication. The unguarded subtraction does not itself
prove reachable stale inputs. Preserve frame ownership and node membership
as reconstruction invariants; checked conversions remain a defensive port
choice, not a confirmed defect fix. No exhaustive proof of every producer
or invalidation branch, and no execution evidence is claimed.

### S4. Touch claiming, cancellation, and momentum (`contracts-CF1`)

**Observed fact.** `crates/gpui/src/gestures.rs:513-551,591-704,728-880,891-1004`
and `crates/gpui/src/window.rs:6088-6188`. See contracts C27 and C33.

| State → state | Input and guard | Output |
|---|---|---|
| Idle → pending | Start a contact without a fling to catch | Keep contact ID, start point, deadline, and offer flags. |
| Pending → touch-drag or long-press | Matching contact offered once and the routed `Started` event prevents default | Claim interaction; subsequent movement/end/cancel follows that kind. Declined offer leaves it pending. Drag is offered at contact start; long press is offered by a timer while still eligible. |
| Pending → panning | Matching movement exceeds slop | Choose dominant axis, include accumulated movement in the initial scroll, and use prediction only for presentation correction. |
| Pending → idle | Matching release / cancel | Release synthesizes a pointer down/up pair; cancel emits no tap. |
| Panning → idle, with optional momentum | Matching release | Emit `Ended` scroll at the starting position; momentum requires sufficient recent speed and nonzero fling duration. |
| Claimed → idle | Matching release | Emit `Ended` for the claimed gesture rather than synthesizing a tap. |
| Panning / claimed → idle | Matching cancel | Emit that stream's `Cancelled` event; no tap or new fling. Other contact IDs do not finish the active state. |
| Momentum → momentum / finished | Tick evaluates curve against elapsed time | Emit nonnegative distance increments along the stored direction, with `Moved` until the terminal `Ended`. A new contact catches momentum: finish the old stream and start a pan immediately rather than a tap candidate. |

This is the window's recognizer path, not a guarantee that every host emits raw
touch or that all raw touches target a fixed element. The contact state and
optional momentum are separate fields.

### S5. Wayland anchored popup configure and dismissal (`contracts-CF1`)

**Observed fact.** `crates/gpui_linux/src/linux/wayland/client.rs:1074-1098,1644-1666`
and `crates/gpui_linux/src/linux/wayland/window.rs:1128-1179,1396-1420`.
See contract C37 for parent resolution, press serial selection, and other
adapters' unsupported result.

- Open against an existing parent or return an error. A configured grab is
  supplied only when the adapter has a nonzero press serial; that is a request,
  not evidence that a compositor granted it.
- `xdg_popup.configure` stages a size if positive on both axes; it does not
  apply the event's position. `xdg_surface.configure(serial)` consumes staged
  state, applies applicable size changes and acknowledges the configure.
  `Repositioned` does not apply geometry by itself.
- `PopupDone` causes the adapter to call `window.close()` and enter the normal
  close path. An event with no matching registered window is ignored.
  These are callback reactions, not an assertion of compositor event timing.


### S6. Scene construction, compilation, and presentation

**Observed fact.** The render boundary carries a finished scene and a
backend-neutral command sequence whose ranges index that scene's primitive
arrays. It is not a serialized graphics protocol.

1. **Record.** The scene receives paint primitives with geometry and a mask.
   Insert intersects the bounds with the mask and skips empty non-boundary
   primitives. It retains filter markers to keep pairing intact. Order is
   assigned through the bounds-ordering structure or the active layer.
   Frame-cache replay reinserts paint operations through the same scene API;
   it does not replay an old GPU command buffer. See S3 and
   `crates/gpui/src/scene.rs:136-177,242-250`.

2. **Compile.** `Scene::finish` sorts the typed arrays and compiles the plan.
   The batch iterator merges live primitive streams by order and kind,
   preserving filter markers as boundaries; compatible instances are grouped
   with their ranges, atlas IDs or pipeline variants as applicable. The
   plan matches filter markers with a stack, allocates isolated target indices
   by nesting depth, and emits begin/end commands plus ordinary batches.
   An unmatched opening marker uses the inline target. An orphan closing
   marker triggers a debug assertion; the non-asserting path emits an inline
   end command. Requirements include path geometry counts and intermediate
   target needs. See `crates/gpui/src/scene.rs:252-313,509-650` and
   `crates/gpui/src/scene/plan.rs:34-163,237-290`.

3. **Consume.** `Window::present` passes `rendered_frame.scene` to the
   platform draw method. Metal, DirectX, and wgpu read shared plan
   requirements; the wgpu encoder turns commands into draws after preparing
   targets and capacity. Paths can require intermediate rasterization;
   layer and filter ordering may not be discarded by a port's batching.
   See `crates/gpui/src/window.rs:3395-3411`,
   `crates/gpui_apple/src/metal_renderer.rs:581`,
   `crates/gpui_windows/src/directx_renderer.rs:491`, and
   `crates/gpui_wgpu/src/wgpu_renderer/frame.rs:16-42,244-289,457`.

4. **Submit / present (wgpu trace).** An unconfigured target returns false.
   On surface acquisition, suboptimal/lost/outdated branches reconfigure;
   timeout/occlusion request a redraw; validation records a fault and also
   requests redraw. Successful encoding submits to the queue, then the
   successful draw path calls `present`; if encoding fails after acquisition,
   it drops the view/frame and reconfigures. These are adapter reactions,
   not measured recovery or display completion. See
   `crates/gpui_wgpu/src/wgpu_renderer/platform.rs:124-172` and
   `crates/gpui_wgpu/src/wgpu_renderer/frame.rs:16-42`.

**Portability hazard.** A plan's ranges are meaningful only with the finished
scene that produced them. The debug checks do not make them portable handles.
`request_animation_frame`, renderer submission, and pixels actually appearing
on a display are different observations.

### S7. Window frame demand and callback drain

**Observed fact.** `crates/gpui/src/window.rs:1758-1897,2682-2713`;
see animation contracts C3/C5 and frame publication S1.

| Trigger / guard | Core behavior |
|---|---|
| Register a next-frame callback | Append it, call platform `schedule_frame`, and wake the platform source; registration need not immediately dirty the window. |
| Request an animation frame | Register a callback that notifies the captured current view. |
| Frame request while another draw is on the same thread's stack | Return without a nested draw; accumulate its forced-render bit for a later request. |
| Eligible request hits the interval throttle | Preserve forced-render demand; schedule/wake to retry, without draining callbacks in this turn. Presentation-required requests bypass the throttle. |
| Request accepted | Take the queued callback snapshot and invoke it in order before deciding whether to redraw. Callbacks appended while this snapshot runs stay queued. |
| Dirty or forced render | Draw and present; forcing refresh bypasses cached view reuse in this path. |
| Not dirty; presentation is needed | Present the existing rendered scene without rebuilding it. Dirty work or remaining callbacks cause renewed scheduling/wake requests. |

The interval policy is conditional, not a universal FPS guarantee. Scheduler
and backend source signals do not settle `q-frame-scheduling`.

### S8. Task scheduling, ordering, and lifetime

**Observed fact.** `crates/gpui/src/platform_scheduler.rs:109-170`,
`crates/gpui/src/queue.rs:69-77,315-357`,
`crates/gpui_scheduler/src/scheduler.rs:25-46,135-211`, and
`crates/gpui_scheduler/src/executor.rs:221-253,380-403,554-563`.

| Boundary / operation | Carrier and guarantee |
|---|---|
| Foreground scheduling | `PlatformScheduler` hands a runnable to the main-thread dispatcher with default priority. This is thread placement, not synchronous execution at the call site. |
| Background scheduling | Spawning schedules a runnable; subsequent scheduling uses the requested priority through the dispatcher while the scheduler is alive. No cross-backend completion order is specified. |
| Shared weighted queue when the adapter uses it | Enqueue at the back of each priority lane. Select a lane probabilistically from nonempty lanes, then pop its front. This gives FIFO **dequeue** within one lane, not strict priority across lanes, or FIFO completion across workers / task polls. Realtime audio is not accepted by this queue. |
| Timer | The platform delayed-dispatch path runs a runnable which sends a one-shot completion signal. A requested delay is not an observed wake deadline. |
| Task handle | Await obtains output; documented cancellation on drop and detach-without-output are distinct. No rollback of already executed side effects is implied. |
| Dedicated session | Spawn a thread (worker for the supported Wasm build), return an asynchronous handle rendezvous, and run session-local runnables on that thread. The loop exits when runnable senders are gone; detached children may keep it alive after the root finishes. Cancelling the root is not a session-wide join. |

**Portability hazard.** The shared priority queue does not define all
dispatchers' policy. Its users include the Linux background dispatcher and
the Windows main queue (`crates/gpui_linux/src/linux/dispatcher.rs:32-38`,
`crates/gpui_windows/src/platform.rs:130`). Keep affinity, readiness, dequeue
and completion separate when specifying ordering.


## Persistent Schema Notes

Pending. The event envelopes cataloged here are in-memory values; that does not
establish the absence of other persisted formats.


## Compatibility Hazards

| Hazard | Evidence level | Port implication |
|---|---|---|
| Scroll units are tagged | Portability hazard | Preserve pixels vs lines and phase before policy-level conversion (`interactive.rs:522-564`). |
| Contact prediction is optional | Portability hazard | Do not conflate a predicted coordinate with the actual contact position (`interactive.rs:119-135`). |
| Close decision is distinct from notification | Portability hazard | An asynchronous notification cannot substitute for the synchronous boolean decision (`platform.rs:945-947`). |


## Coverage and limits

- **Inspected:** complete normalized input enum and nested file-drop payloads;
  representative adapter producers; callback signatures, mouse dispatch order,
  and application effect types.
- **Inspected (B3b):** window registry lifetime, redraw publication, focus and
  effect flushing, element/frame reuse, touch claims and momentum, and Wayland
  popup event handling.
- **Inspected (B3c):** record/replay and render-plan compilation; wgpu
  acquire/submit/present; frame demand and callback drain; executor handoff,
  priority queue selection, timers and dedicated sessions.
- **Skipped:** exhaustive per-adapter event conversion and IME sequencing,
  complete GPU recovery and renderer parity, and persisted schemas.
- **Evidence basis:** source inspection, with completed architecture and
  contracts outputs for context. No runtime tests or traces were run.
- **Known blind spots:** observed pacing, platform-specific emission, and
  exhaustive frame-cache invalidation across all producers and rollback paths.
- **Coverage disposition:** PARTIAL — B3a through B3c recorded; B3d pending.


## Open Questions

The existing `q-headless-parity` and `q-gpu-fallback` are unchanged. The static
trigger paths narrow `q-frame-scheduling`, but effective frame pacing remains
unverified. No question is closed here.


## Carry-Forward

Responses recorded in S3–S5. These do not close the independent runtime
questions. Framework carry-forward closure awaits the protocols phase handoff.


## Validation

Phase validation pending B3d. B3a checked all 14 input variants against
source. B3b recorded guarded transitions and distinguished frame publication,
effect draining, and native configuration acknowledgements. B3c traced the
render-plan and scheduling paths without asserting measured timing.
