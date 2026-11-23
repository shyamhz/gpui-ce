# B. Runtime, Interaction & State

This guide owns app and window lifetime, request scheduling, input and motion.
[C](C-layout-rendering.md) owns the contents of a frame and
[D](D-text-platform-resources.md) owns host/IME translation.

## App, entities and windows

**Reconstruction requirement.** Boot the host and invoke the launch callback
with serialized UI access. Reserve a window ID, construct the backend
window, install the root, perform an initial draw, then register the live
window and return its handle. If construction fails, remove the reservation
and return the error. A live window is temporarily unavailable for a second
mutable update; restore it before effects flush on normal return. Treat
should-close as a synchronous decision and close as a one-shot notification;
on removal detach window/entity associations before close observers and
apply quit policy independently.

**Reconstruction requirement.** Updates nest. The normal outermost return
drains effects unless already draining. Before each dequeue release dropped
entities/focus handles. Deliver effects in queue order, coalescing pending
entity/global notifications but not emits. Clear a notification's pending
mark before its callback so it can enqueue again. A callback may add work
to the same drain; this is not a panic-recovery guarantee. Teardown must
keep integrations alive while their dependent work is cancelled.

**Reconstruction requirement.** A draw starts a new entity-access trace.
Entity reads contribute dependencies; reused views also restore their
recorded accesses. After publication replace the window's tracked
dependencies, so future entity invalidations reach the views that used
them. Resetting access tracking does not delete an entity or its observers.

**Implementation choice — reference ownership.** The embedding handle
borrows the UI app synchronously; its weak async counterpart can survive an
await, but is not a message channel or worker-thread proxy. GPUI uses a
single-thread borrow cell and rejects re-entrant mutable borrowing. The
required property is serialized UI mutation and explicit ownership, not
that particular borrowing mechanism.

**Evidence:** [protocols S1–S2](../findings/protocols-and-state.md#state-machine),
[architecture concurrency](../findings/architecture-map.md#concurrency-model);
`crates/gpui/src/app.rs:193-215,327-345,878-882,1264-1283,1344-1369,1558-1592,2013-2075,2235-2285`,
`crates/gpui/src/app/async_context.rs:57-69,238-250`,
`crates/gpui/src/app/entity_map.rs:164-190`, `crates/gpui/src/view.rs:539-557`,
`crates/gpui/src/window.rs:3227-3233,3341-3389`.

## Frame demand and task lifetime

**Reconstruction requirement.** Frame requests distinguish redraw demand
from required presentation. Registering a next-frame callback schedules
work without necessarily dirtying the view. On an accepted request take a
snapshot of callbacks, run them before the redraw decision, and leave new
registrations for a later turn. Dirty/forced work rebuilds; a clean request
can present the existing scene. Suppress nested drawing and preserve deferred
force demand. Presentation-required requests bypass the ordinary throttle.
Publish the completed frame before comparing rendered focus paths. No
request, redraw or submission is proof that pixels reached the display.

**Reconstruction requirement.** Foreground work runs in the UI domain.
Background readiness, priority, dequeue and completion are different
orders. Await returns output; dropping an attached task cancels it without
rolling back completed work; detach allows continuation without an output
handle. Dedicated sessions may outlive the root if children still own
their runnable sender; dropping the root is not a session join. A timer
provides delayed completion, not a measured wake deadline.

**Implementation choice — reference scheduling.** `async-task` creates
runnables, while the dispatcher places work. The Linux worker pool dequeues
FIFO within a selected weighted lane, not in global FIFO or strict priority
order. Dedicated OS threads/Wasm workers are separate from that pool. For
queue closure adopt the audited port policy in [E](E-implementation-verification.md#defect-dispositions).

**Evidence:** [protocols S7–S8](../findings/protocols-and-state.md#s7-window-frame-demand-and-callback-drain);
`crates/gpui/src/window.rs:1758-1897,2682-2713,3301-3354`,
`crates/gpui/src/platform_scheduler.rs:109-170`, `crates/gpui/src/queue.rs:315-357`,
`crates/gpui_linux/src/linux/dispatcher.rs:30-52`,
`crates/gpui_scheduler/src/executor.rs:229-251,380-403`,
`crates/gpui_scheduler/src/scheduler.rs:139-208`.

## Normalized input, focus and shortcuts

**Reconstruction requirement.** The window-scoped, in-memory event envelope
carries no general timestamp, durable replay or delivery acknowledgement.
Use the [14-variant payload table](../findings/protocols-and-state.md#all-14-platforminput-variants);
`ClickEvent` is separate. Preserve scroll pixel/line units, logical window
coordinates and optional contact prediction. Reset propagation and default
prevention before dispatch; return both flags synchronously. Pointer
capture uses stored order and bubble uses reverse order if propagation
continues, with no third target pass. Occluding hitboxes block lower hover;
keyboard modality can suppress passive pointer hover. File-drop enter and
pending can normalize to pointer movement and submit to release; end and
exit remain distinct cleanup paths.

**Reconstruction requirement.** Change logical focus only when enabled
and the target differs; bump its generation, clear pending keystrokes and
refresh. Blur clears the pending prefix. Focus containment and notifications
use the rendered dispatch path after publication; weak released handles
cannot restore focus. Tab eligibility is explicit.

**Reconstruction requirement — matching sequence.**

1. Let interceptors stop the event before matching. Separate binding key
   from typed character: try an eligible distinct typed character first
   (Control/Platform only outside Windows; an unmodified binding on
   Windows), then the binding key with modifiers.
2. Rank complete matches by descending context depth and then insertion
   index; a context-free binding is treated as deepest. A null rule only
   suppresses candidates it outranks from equal or weaker sources.
3. If a longer match remains eligible, retain the prefix with its focus.
   Start/reset the one-second timeout when a pending binding or an accepting
   input handler needs it. Finish a full match through action dispatch
   unless character input takes priority. On mismatch or eligible timeout,
   resolve replay through actions, ordinary key listeners, then any eligible
   typed character; cancellation or consumption can stop delivery. Ignore
   a stale focus prefix. Invalid binding strings are parse errors.

On mismatch, remove the new key temporarily. Replay the longest complete
binding prefix of the old pending keys, or one old key if no prefix
matches. Reprocess the new key against the remaining suffix. Timeout
repeatedly replays prefixes until none remain. Replay resolves at the
focus path in effect for that dispatch; it is not guaranteed text insertion.

**Evidence:** [contracts C21–C26](../findings/behavioral-contracts.md#apisdk--input-focus-and-keys-b2b)
and [protocol catalog](../findings/protocols-and-state.md#event-catalog);
`crates/gpui/src/interactive.rs:771-800`,
`crates/gpui/src/platform/keystroke.rs:18-60,82-113`, `crates/gpui/src/keymap.rs:140-210`,
`crates/gpui/src/key_dispatch.rs:480-560`,
`crates/gpui/src/window.rs:2372-2404,5871-6010,6213-6260,6352-6420,6577-6610`.

## Raw touch

**Reconstruction requirement.** Track a pending contact by identity and
start point. Offer drag on start and long press on the eligibility timer;
claim only if the event prevents default. Otherwise, crossing slop begins
axis-locked pan. Release of a pending contact synthesizes pointer
down/up; the usual click guards still apply. A claimed release ends its
gesture. Cancellation ends the matching stream without a tap or new
fling. A pan release can start momentum; emit incremental deltas until
end, or finish that stream when a new contact catches it. Prediction may
correct presentation, not replace contact position. Do not promise direct
touch-click dispatch, raw pinch recognition or fixed start-target routing
from this recognizer.

**Evidence:** [protocols S4](../findings/protocols-and-state.md#s4-touch-claiming-cancellation-and-momentum-contracts-cf1),
[semantic 5.1](../findings/semantic-defects.md#pass-5-api-contract-violations);
`crates/gpui/src/gestures.rs:479-489,513-1004`,
`crates/gpui/src/window.rs:6088-6188`, `crates/gpui/src/elements/div.rs:3883-3897`.

## Motion and transition time

**Reconstruction requirement.** Duration motion takes elapsed time and
returns progress, local time, iteration, direction, phase and active state.
Before delay, return start and remain active. After subtracting delay,
select passes and iteration parity in integer time; check finite extent
before active passes. A finite run reports the last iteration at completion.
At an internal exact restart boundary, forward/reverse repetition presents
the preceding endpoint while remaining active. Empty cycles have an
inactive/complete path, not a divide by zero; infinite runs do not complete.
Apply easing to the local fraction without clamping away permitted overshoot.

**Reconstruction requirement.** For spring state `(x,v)` and constant
target `g`, propagate displacement `y=x−g` by the damped oscillator:

```text
ω = sqrt(stiffness / mass)
ζ = damping / (2 sqrt(stiffness * mass))
A = [[0, 1], [−ω², −2ζω]]
[y', v'] = exp(A Δt) [y, v]
x' = g + y'
```

The reference uses the underdamped branch below `ζ = 1 − 10⁻⁴`,
overdamped above `ζ = 1 + 10⁻⁴`, and critical in between. For a target
ramp of velocity `u`, remove lag `−2ζu/ω` from displacement and subtract
`u` from velocity before the step; restore both relative to the advanced
target afterward. Settling requires both displacement within `ε` and
velocity within `εω`; the default `ε` is `0.001`. Zero damping has no
finite settling time. Default retargeting preserves current
presentation and spring velocity; explicit restart/jump is different.
Active evaluated transitions request another frame until settled. Synced
animations use an app epoch, repeat loops the individual motion, cap
timers limit per-animation demand, and reduced motion settles affected
animations immediately. Wall-clock delivery remains in [E's runtime ledger](E-implementation-verification.md#unresolved-runtime-behavior).

**Implementation choice.** The propagator can be evaluated by an
equivalent stable method; frame-count stepping is not a substitute.

**Evidence:** [contracts C1–C6](../findings/behavioral-contracts.md#apisdk--animation-and-timing-b2d);
`crates/gpui/src/motion.rs:647-738`, `crates/gpui/src/spring.rs:5-170`,
`crates/gpui/src/animated.rs:82-144`, `crates/gpui/src/transition.rs:108-144`,
`crates/gpui/src/elements/animation.rs:380-440`, `crates/gpui/src/app.rs:1240-1257`.
