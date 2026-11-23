# Protocols and State

**Block B3a — event catalog.** B3b–B3d and phase validation are pending.
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

Pending B3b–B3d. The gesture/popup and frame-reuse routes remain open.


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
- **Skipped:** exhaustive per-adapter event conversion, IME sequencing, state
  machine transitions, frame scheduling/recovery, and persisted schemas.
- **Evidence basis:** source inspection, with completed architecture and
  contracts outputs for context. No runtime tests or traces were run.
- **Known blind spots:** observed pacing, platform-specific emission
  differences, gesture arbitration, popup lifecycle, and frame-cache ownership.
- **Coverage disposition:** PARTIAL — B3a only.


## Open Questions

The existing `q-headless-parity` and `q-gpu-fallback` are unchanged. The static
trigger paths narrow `q-frame-scheduling`, but effective frame pacing remains
unverified. No question is closed here.


## Carry-Forward

`mech-CF1` (frame reuse) and `contracts-CF1` (gesture and Wayland popup
lifecycle) remain assigned to the protocols phase. B3a is not their closure.


## Validation

Phase validation pending B3b–B3d. B3a block check: all 14 normalized input
variants accounted for, boundary carriers identified, and static facts separated
from runtime claims.
