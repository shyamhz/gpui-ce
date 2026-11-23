# Protocols and State

**Blocks B3a–B3b — event catalog and state machines.** B3c–B3d and phase
validation are pending.
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
- **Skipped:** exhaustive per-adapter event conversion, IME sequencing, full
  renderer/executor flows, frame scheduling/recovery, and persisted schemas.
- **Evidence basis:** source inspection, with completed architecture and
  contracts outputs for context. No runtime tests or traces were run.
- **Known blind spots:** observed pacing, platform-specific emission, and
  exhaustive frame-cache invalidation across all producers and rollback paths.
- **Coverage disposition:** PARTIAL — B3a and B3b recorded.


## Open Questions

The existing `q-headless-parity` and `q-gpu-fallback` are unchanged. The static
trigger paths narrow `q-frame-scheduling`, but effective frame pacing remains
unverified. No question is closed here.


## Carry-Forward

Responses recorded in S3–S5. These do not close the independent runtime
questions. Framework carry-forward closure awaits the protocols phase handoff.


## Validation

Phase validation pending B3c–B3d. B3a checked all 14 input variants against
source. B3b recorded guarded transitions and distinguished frame publication,
effect draining, and native configuration acknowledgements.
