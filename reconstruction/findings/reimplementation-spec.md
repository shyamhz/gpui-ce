---
spec_variant: language-agnostic
selection: approved-roadmap
---

# GPUI-CE Reimplementation Spec

## System Summary

Build an embeddable UI runtime: application code owns the model; the runtime
owns UI identity, updates, layout, dispatch and scene production. Hosts supply
clocks, window events, presentation and system services. An implementation
need not reproduce Rust APIs, package boundaries or backend technology.

**Evidence key.** B is the porting bundle and its Source Index
(`reconstruction/findings/reverse-engineering-bundle.md` in the committed
review tree); C1–C38 and P S1–S11 refer to its canonical contracts
and protocols. M/D are the mechanical/semantic findings there. Requirements
below are source-backed unless explicitly labeled as implementation choices
or unresolved. Observed code and checked-in assertions are not runtime results.
The minimum-viable tier is an implementation target, not a claim that it
already achieves native parity.

## Conceptual Module Model

Each row defines a responsibility, its public boundary and its owned state.
Names are implementation choices; the stated invariants are requirements.

| Module | Responsibility | Public inputs → outputs | Owned state and invariant | Collaborators |
|---|---|---|---|---|
| UI runtime | Serialize UI mutation and manage lifetimes. | Launch/update/open/close → handles, callbacks, errors | Entity/window identities and effects; outermost update drains work | Host, Scheduler, Interaction, Frame |
| Scheduler | Deliver work, time and wakeups. | Spawn/cancel/wake/timer → result or completion | Ready work, timers and session lifetime; UI affinity preserved | UI runtime, Host |
| Layout and elements | Reconcile element state and resolve geometry. | Tree, style, constraints, measurement → bounds, hitboxes, paint work | Identity-based state and frame-local traversal; layout precedes prepaint and paint | Frame, Text, Resources |
| Frame | Publish an ordered scene and interaction snapshot. | Frame request, dirty state, paint → frame and presentation request | Current/building snapshots, callbacks and ranges; no cross-generation range misuse | UI runtime, Layout and elements, Interaction, Presenter |
| Interaction | Route input, focus and actions. | Normalized input, focus, bindings → listener effects and dispatch flags | Focus path, pending prefixes, pointer and gesture state | UI runtime, Frame, Text, Scheduler |
| Text | Shape documents and expose editor exchange. | Text, runs, fonts, constraints or IME edit → rows, carets, glyphs or edit result | Layout/face caches and editor-facing marked state; units explicit | Layout and elements, Interaction, Host, Presenter |
| Motion | Evaluate time-dependent properties. | Clock sample, goal, timing/physics → sample and redraw demand | Start time, goal, velocity/state; continuous retargeting by default | Scheduler, Frame, Layout and elements |
| Resources and accessibility | Resolve display inputs and publish accessibility observations. | Asset request or semantics → resource state, tree or action result | Cache and latest tree; tree absent is not an empty success | Layout and elements, Text, Frame, Host |
| Presenter | Consume a finished scene and submit an output. | Scene, target, raster requests → submission or failure | Target resources; submitted is not displayed | Frame, Text, Host |
| Host | Translate host traffic and mediate system capabilities. | Native messages/service requests → normalized events, replies or unsupported | Host handles and capability state; no ownership of the app model | UI runtime, Presenter, Scheduler, Interaction |
| Embedding entry point | Assemble modules for one host or test harness. | Configuration and launch callback → initialized runtime | Process-local host selection; selection is not connectivity | UI runtime, Host |

## Layer Split

| Module | Layer | Notes |
|---|---|---|
| UI runtime, Layout and elements, Frame, Interaction, Motion | core semantics | Preserve observable rules, not source organization. |
| Scheduler, Text, Resources and accessibility | core semantics with adapter ports | Dispatchers, font/raster providers, I/O and accessibility transports plug in. |
| Host, Presenter | adapters | Map native lifecycle, device, input and service behavior at explicit boundaries. |
| Embedding entry point | delivery surfaces | Library and test harness; no required service, network listener or CLI. |

## Required Behaviors

The following are **reconstruction requirements**. Conditional features apply
when their tier or host is in scope. See Acceptance Scenarios for observables.

- **App and frames (B; P S1–S3/S7):** reserve a window identity, build its
  root, draw once before returning a live handle; unwind the reservation on
  construction error. No second mutable borrow of a window currently in an
  update. Deliver close notification at most once, separately from the
  synchronous decision. Drain queued effects on normal outermost-update
  exit, not at an arbitrary paint boundary: release dropped entities/focus
  handles before the next effect, dequeue FIFO, coalesce pending notifications
  by entity or global type but not ordinary emits, and allow callbacks to
  enqueue more. Reconcile frame state, finish the scene, publish, then
  compare rendered focus paths. Presentation is separate.

- **Elements and geometry (C7–C20; P S3):** request layout → prepaint →
  paint; reject invalid order. Reconcile state by stable tree identity and
  state kind; call-site state alone does not distinguish loop iterations.
  Prepaint builds hitboxes and scoped geometry used by paint and dispatch.
  Resolve rem lengths using the active root/override, relative lengths as
  fractions of the available parent base, and auto by layout policy; keep
  definite, min-content and max-content constraints distinct. Default layout
  position is relative. Resolve direction/bidi before layout; the port must
  not blindly substitute native CSS direction or sizing defaults. Snap
  both absolute edges to the device grid (half ties toward zero for bounds),
  so shared edges close; keep text offsets parent-relative. Recompute current
  bounds after changes. Baseline is the default inline alignment. Deferred
  work follows normal work, with higher priority above lower in the relevant
  round. Scrolling clamps each offset to `[−max, 0]`, where max is nonnegative
  padded content minus viewport; shrink, resize and scroll-to-bottom use the
  current extent (C33).

- **Scene and demand (P S3/S6–S7):** retain ordered typed records, clipping
  masks, layers and filter boundaries even when a boundary clips empty.
  Group only compatible instances without changing composite order; pair
  filter scopes and plan intermediate resources before drawing. Reuse may
  replay records, but all ranges must belong to the matching frame. Consume
  a snapshot of next-frame callbacks before deciding to redraw; callbacks
  added during the drain wait for another turn. Dirty or forced requests can
  rebuild; clean presentation requests can reuse the scene. Avoid nested
  draws and preserve deferred forced demand; presentation-required work is
  not subject to the ordinary interval throttle. No cadence guarantee.

- **Input and focus (C21–C27/C33; P S2/S4):** start each dispatch with
  propagation enabled and default not prevented. Pointer capture runs in
  registration order; if propagation continues, bubble runs in reverse.
  Occlusion hides lower hitboxes, and keyboard modality can suppress passive
  pointer hover. Separate binding identity from typed characters; when a
  distinct typed character is eligible, consider it before the key/modifier
  pair (see C21 for platform-specific modifier handling). Interceptors run
  before matching. Prefer deeper context, treat context-free bindings as
  deepest, break ties by later insertion, and apply null disabling only at
  equal or weaker precedence. Favor matching actions unless character input
  takes priority. Prefixes stay pending until resolved; retry/replay input
  under the key and text rules on mismatch or eligible timeout (one second,
  C23), but clear pending state on focus change or blur. Released weak focus
  handles do not restore focus; tab order respects eligibility.

- **Motion and scheduling (C1–C6; P S7–S8):** sample by elapsed time,
  returning phase, local time, direction, iteration, eased progress and active
  status. Delay holds the start; finite runs settle to their final sample;
  zero-duration and empty runs are handled without a panic; infinite runs
  do not complete. Easing may overshoot. Spring position/velocity obey the
  damped oscillator with analytic steps for fixed or linearly moving targets
  and the under/critical/overdamped regimes; settling checks both position
  and velocity; undamped motion has no finite settle time (C2). Default
  retargeting starts at the current presentation and preserves spring
  velocity; restart, jump and reset are distinct. Animation repetition
  applies to the motion, synchronized motion uses the app epoch, and active
  work requests another frame. An animation cap limits its own requests,
  not global throughput. Reduced motion jumps to the target/resting value
  and completes affected animations. Preserve task affinity and lifecycle,
  awaiting vs cancellation-on-drop vs detach, and per-lane FIFO dequeue
  where weighted queues are reproduced. No global priority completion order.

- **Text (C28–C31; P S9–S10):** consume UTF-8 source with ordered runs
  covering it on scalar boundaries; respect hard breaks and trailing empty
  rows. Shape per paragraph with bidi scope, distinguish wrap width from
  alignment width, and return source-indexed rows, fragments and cluster
  geometry. Clamp limits soft wrapping, not total document rows or ellipsis:
  for a clamped paragraph use up to budget-minus-one width-limited breaks,
  then emit the remainder unbounded; later paragraphs consume remaining
  budget but retain hard breaks. Inline boxes are atomic. Caret/cluster
  queries use byte indices, respect RTL affinity/edges, and reject indices
  past the source; distinguish off-line edge results from an in-row hit.
  Resolve face by requested family, descriptor fallback, then configured
  fallback; system-UI generic precedes its configured substitute. Keep
  face/raster identity and propagate raster or atlas failure. For editor
  interchange use UTF-16 code units and mark/commit separately; conversion
  clamps beyond end and snaps inside a scalar to its end, not the enclosing
  grapheme. Do not infer native composition ordering from simulated keys.

- **Components and host services (C17–C20/C32–C38; P S5/S11):** virtualize
  uniform rows by visible range; expose canvas prepaint and paint bounds and
  resize-dependent container output. Resource loading distinguishes pending,
  ready, and failed with optional loading/error UI; delayed loading UI is
  not a fetch retry. Accessibility exposes optional last-frame tree, stable
  node identities/bounds, forced build where supported, and action routing.
  Host clipboard and credential stores retain ownership; no app auth is
  implied. Web clipboard synchronous read is empty by design; async is the
  permission-capable path. Web credentials read as no item and writes/deletes
  report unsupported. Unsupported native roles must not silently degrade to
  ordinary windows. Linux/FreeBSD selection respects explicit headless,
  presence of the headless override, then nonempty Wayland and X11 display
  values among compiled backends, then headless (C38). X11 scale handling
  distinguishes auto, a positive normal scale and RandR.

### Design consequences for audited defects

These are **implementation choices adopted for the port**, not descriptions
of existing source behavior. Every entry preserves B's `port differently`
disposition. M1.2 and D3.1 are **strong inferences** in B; the other findings
are source observations.

| Defect | Disposition | Port choice and proof |
|---|---|---|
| M1.1 | port differently | Return unsupported for an unavailable hide/unhide-other-apps operation, rather than panic (S-34). |
| M1.2 | port differently | Validate provenance/membership when reusing frame ranges; rebuild instead of using a mismatched generation (S-08). No reachable stale-range claim. |
| M2.1 | port differently | Surface restart launch failure and keep the original app running (S-34). |
| M2.2 | port differently | Expose caller-controlled resource deadlines and cancellation; do not retry implicitly (S-35). |
| M6.1 | port differently | Warn and fall back to auto scale for malformed X11 overrides (S-33). |
| D3.1 | port differently | Wake blocked workers on close, drain accepted work and let receivers exit (S-27). |
| D4.1, D4.2 | port differently | Redact credential identifiers from diagnostics; give secret buffers explicit clearing ownership and avoid incidental copies (S-32). |
| D5.1 | port differently | Specify synthetic mouse dispatch for raw taps; do not invent direct touch clicks or in-core raw pinch detection (S-12). |
| D5.2 | port differently | Reject multiline input at the single-line boundary consistently; use document shaping for multiline (S-25). |
| D5.3 | port differently | Propagate a distinguishable clipboard failure; label a lossy adapter rather than imply that no item proves no error (S-31). |

## Protocols and Persisted State

**Reconstruction requirements** below follow P's catalog and state machines.
Tag names convey meaning; the port need not serialize these records.

| Input tag | Payload (position in logical window pixels) |
|---|---|
| KeyDown / KeyUp | Keystroke with modifiers, binding key, optional typed character; Down adds held and prefer-character-input flags. |
| ModifiersChanged | Modifiers and Caps Lock state. |
| MouseDown / MouseUp | Button, position, modifiers, click count; Down adds first-mouse flag. |
| MousePressure | Pressure, stage, position and modifiers. |
| MouseMove / MouseExited | Position, modifiers and optional pressed button. |
| ScrollWheel | Position, modifiers, touch phase and tagged pixels-or-lines delta. |
| Pinch | Center, signed zoom delta, modifiers and phase. |
| LongPress / TouchDrag | Phase, start position and current position. |
| FileDrop | Entered with position and paths; Pending/Submit with position; Exited/Ended without payload. |
| Touch | Contact identity, phase, position, optional prediction and optional force. |

- **Window and effects (P catalog/S1–S2):** callbacks are window-scoped.
  Frame requests distinguish force-render and require-presentation. Resize
  carries size and scale; active and hover changes carry flags; move,
  appearance, button layout and close are notifications. A should-close
  callback returns a decision; hit-test returns an optional control area.
  Input returns propagate/default-prevented. Effects carry entity/global
  identity, typed emit payload, refresh, deferred callback or creation
  notification. Neither envelope has a durable replay protocol.
- **Raw contacts (P S4):** Started/Moved/Ended/Cancelled; pending contacts
  can claim drag or long press via default prevention, move into axis-locked
  pan after slop, or end as a synthetic down/up tap. Cancel is not release
  and never starts momentum; ended pans can start a decaying scroll stream,
  which a new contact can catch. Keep prediction distinct from contact
  position. File-drop enter/pending/submit can normalize to pointer events;
  exit and end are distinct cleanup paths (P catalog).
- **Role and storage boundaries (P S5/S11/Persistent Schema Notes):** Wayland
  popup configure stages positive size, surface configure applies it and is
  acknowledged, dismissal closes. A layer surface is a separate capability.
  Typed bindings and JSON action parameters do not define a GPUI keymap
  file. Scene, entity, layout and focus state are in memory. No framework
  database, migrations or restart replay are required by these paths.
  Assets are external bytes; clipboard and credentials use host formats.

## External Dependencies

These stances are **implementation choices**. Equivalent providers are
acceptable only when their slice's observable acceptance checks pass.

| Dependency | Stance (replace/wrap/emulate/postpone) | Rationale |
|---|---|---|
| Flex/grid engine and styles | replace | Reproduce measured constraints, direction, defaults and snapping, not the source library. |
| Paragraph shaping, font discovery and rasterization | wrap | Keep interchangeable services behind source index, face, glyph and error contracts. |
| Clock, event loop and executor | wrap | Use target primitives with deterministic test time and explicit affinity. |
| Scene/GPU stack | emulate | First use an inspectable scene consumer; add native presentation at the adapter boundary. |
| Native windows, IME, clipboard, keychain and accessibility | wrap | Keep permission and capability decisions with host SDKs. |
| Assets, HTTP and codecs | wrap | Keep decoding/transport separate from resource lifecycle. |
| Media, runtime bridges and source-specific tooling | postpone | Not required for the minimum runtime or the named major workflows. |

## Portability Hazards

**Portability hazards**, not claimed failures (B Hazards, P S3/S6/S8–S11):
test affinity and release boundaries in a runtime with different ownership;
do not inherit browser layout defaults by accident; preserve source indices
across bidi, inline objects and UTF-16 conversion; avoid reordered compositing
and frame-range reuse; treat clipboard metadata and credential lookup keys
as data, not identity proofs. Headless scene inspection is not evidence
about actual pixels or pacing. Never silently replace a native role with an
overlay or treat selected configuration as a connectivity result.

## Implementation Sequence

1. Establish controllable time, a test host, app lifecycle and frame barriers.
2. Build identity, layout and scene composition; add input and focus against
   the same published frame. Accept the minimum-viable scenarios.
3. Add motion, document text and IME exchange, concurrent execution,
   resource/virtualization flows and accessibility. Test core behavior with
   fixtures and explicit adapter seams before wiring native services.
4. Extend host coverage only as capabilities are verified; keep the B7a
   questions separate from implementation acceptance.

### Scope Tiers

- **Minimum viable port:** one testable embedding, app/window lifecycle,
  element and frame pipeline, basic geometry, pointer and key/focus behavior.
- **Major-workflow parity:** motion, text/editor integration, executor
  semantics, scrolling, resources and accessibility; host event translation
  is tested at its boundary and native fidelity is not implied.
- **Full parity:** target-specific adapters, native roles, services and
  configuration; criteria here are representative entry checks, not an
  exhaustive assurance of every original host behavior.

## Acceptance Scenarios

Planned **verification obligations**, not test results. `test` routes use
controlled clocks, event injection, fixture fonts and fake host results so
they can observe the stated condition without relying on OS permission,
screen pixels or timing. Real host comparisons are separately unresolved.

| Scenario ID | Tier | Scenario | Input | Expected Output / Side Effect |
|---|---|---|---|---|
| S-01 | minimum-viable | Window lifetime (P S1) | Open a recording root and a host-rejected second window; veto first close then allow it | First draw precedes handle return; failed open yields no live handle; only allowed close yields a single close notification. |
| S-02 | minimum-viable | Effect drain (P S2) | Nested update queues duplicate notify and distinct emits; observer enqueues another effect | No delivery before outer return boundary; coalesced notify, ordered emits and callback work drain in queue order. |
| S-03 | minimum-viable | State identity and phase guards (B2a-1–3) | Update state under a stable ID and redraw; repeat a call site in a loop with and without explicit keys; attempt paint first | State persists; unkeyed uses alias while explicit keys isolate; invalid phase use is rejected. |
| S-04 | minimum-viable | Relative, rem and intrinsic geometry (B2c-1–4) | 200-unit parent, half-width child, then roots of 10 and 20 units per rem; measure an unconstrained leaf twice with a deterministic intrinsic-size callback | Child width 100; rem geometry doubles; intrinsic size uses content and identical constraints yield the same bounds. |
| S-05 | minimum-viable | Shared edges and freshness (B2c-5/6/8) | Adjacent boxes meet at a fractional coordinate; flip one directional subtree, then change width and redraw | Shared snapped edge has no seam; unaffected subtree stays fixed; bounds reflect the new style. |
| S-06 | minimum-viable | Canvas and deferred order (B2a-6/7) | Recording canvas and two deferred children with different priorities | Canvas prepaint precedes paint with same bounds; deferred paint follows ordinary paint; higher priority composites above lower. |
| S-07 | minimum-viable | Demand and publication (P S1/S6/S7) | Callback A queues B; request a clean presentation then a forced draw | B waits for the next eligible request; clean present uses the published scene; forced draw publishes rebuilt state. |
| S-08 | minimum-viable | Frame range ownership (P S3/S6; M1.2) | Reuse a cached view with a nested deferred draw; then change mask and alter earlier frame records | Correct target, hitbox and paint order after reuse; invalidated view rebuilds without referencing the old range. |
| S-09 | minimum-viable | Occlusion and modality (B2a-4; B2b-7/8) | Overlap foreground occluder and hoverable item; begin keyboard navigation with pointer stationary | Rear item is not hovered through occluder; passive pointer hover is suppressed in keyboard modality. |
| S-10 | minimum-viable | Binding precedence (B2b-1/2/6) | Install nested-context bindings, a later same-context user binding, and a lower-precedence disable | Deep context wins when applicable; within context later wins; lower disable cannot suppress stronger binding. |
| S-11 | minimum-viable | Prefix and focus (B2b-3–5) | Prefix of two-key shortcut in editable field; finish, time out, then repeat with intervening focus change | No initial action; completion fires once; timeout replays eligible text; focus change prevents old prefix completion. |
| S-12 | major-workflow | Raw touch recognition (C27/C33; P S4; D5.1) | Tap a hoverable listener, move a separate contact past horizontal slop then cancel; end another qualifying pan | Tap follows mouse path; horizontal scroll is locked and cancel yields no new fling; eligible ended pan can continue in momentum. |
| S-13 | major-workflow | Gesture claims and input units (P catalog/S4) | Accept drag by preventing default; send moved and cancelled; inject one pixel and one line delta | Claimed stream receives move/cancel without tap; scroll unit and phase remain distinguishable at intake. |
| S-14 | major-workflow | Duration endpoints (B2d-1/2/8/9) | Sample zero-duration, delayed, finite repeated, and infinite motions before and after boundaries | Zero completes, delay holds start, finite reports final iteration, infinite never reports completion. |
| S-15 | major-workflow | Retarget and reduce motion (B2d-3/4) | Retarget a running transition at value V; compare restart opt-out; toggle reduced motion while active | Continuous target starts at V; restart uses initial value; next reduced-motion frame settles and stops requesting for that animation. |
| S-16 | major-workflow | Sync and demand cap (B2d-5/10) | Two synchronized animations started in different frames; drive clock with one positive capped animation | Equal phases at equal time; at most one pending cap timer per animation state; timer requests a later update, not a global cap. |
| S-17 | major-workflow | Spring settling (B2d-6/7) | Step a damped and an undamped spring from the same displaced initial state | Damped settles to target within position/velocity tolerance; undamped does not settle in finite time. |
| S-18 | major-workflow | Inline baseline and document rows (B2c-7; B2e-1) | Inline atomic box with default alignment; shape empty text and `one` followed by a hard newline with wide wrap | Baselines align; empty has an empty row and no paint; trailing break adds an empty row. |
| S-19 | major-workflow | Soft clamp (B2e-2; P S9) | Fixture font and one paragraph wrapping to at least three rows; clamp to two; then shape three hard-separated paragraphs with same clamp | Single paragraph has two visual rows; hard paragraph breaks survive and can exceed two rows. |
| S-20 | major-workflow | Caret edges and RTL (B2e-3/4) | Query off the left/right of an LTR row and both edges of a multibyte RTL cluster | Off-line results identify corresponding edge; RTL left maps to logical end, right to start; no interior byte. |
| S-21 | major-workflow | Font precedence and failure (B2e-5/6) | Missing family with configured A and descriptor B present; fail rasterization on a known atlas miss | A without descriptor fallback, B with it; raster failure is exposed, not a successful insertion. |
| S-22 | major-workflow | IME units and composition (P S10) | Editor text `A😀B`; query UTF-16 offset inside the surrogate pair; send marked update followed by commit | Offset snaps after the scalar, not to an interior byte; marked edit becomes committed once on the tested adapter seam. |
| S-23 | major-workflow | Uniform list, scroll and resize (B2a-5/8; B2f-2) | Scroll a 10,000-row uniform list to the middle, shrink contents to fit and resize containing view | Only visible subset renders; matching range is reported; offset clamps to zero and container receives new size. |
| S-24 | major-workflow | Image states (B2f-1; C32) | Controlled loader goes pending, crosses configured loading delay, then fails with fallback supplied | Delayed loading placeholder gives way to fallback; no implicit fetch retry. |
| S-25 | major-workflow | Single-line guard (D5.2) | Pass `a` followed by newline then `b` to single-line and document entry points | Single-line rejection is consistent across configurations; document route preserves two rows. |
| S-26 | major-workflow | Forced accessibility (B2f-3) | No assistive client; enable forcing on accessible test window and draw | Fresh tree, node bounds and incremented tree counter are observable. |
| S-27 | major-workflow | Task and queue lifecycle (P S8; D3.1) | Await a result; separately cancel pending work, detach work and close a queue with idle waiters and accepted work | Await returns result; detach may finish; cancellation does not roll back earlier effects; closure drains accepted items and waiters terminate. |
| S-28 | major-workflow | Thread affinity and timer (P S8) | Schedule foreground and background callbacks, start a delayed completion under controlled time | Foreground runs in UI domain; delayed result is not ready before its deadline in the fixture; no cross-domain completion order asserted. |
| S-29 | full-parity | Clipboard/credential capability (B2f-4) | Web adapter boundary: sync clipboard read, async failure, credential read/write/delete | Sync no item; async failure observable; credential read no item and write/delete unsupported. |
| S-30 | full-parity | Native window-role decision (B2f-5; P S5/S11) | Simulate X11 popup request with valid parent, then Wayland staged configure followed by surface configure and dismissal | X11 returns unsupported; Wayland applies staged size at surface configure, acknowledges it and closes on dismissal. |
| S-31 | full-parity | Clipboard read status (D5.3) | Adapter fixture distinguishes empty from open failure | Empty and failed reads remain distinguishable; a lossy adapter advertises its limitation. |
| S-32 | full-parity | Credential diagnostics and ownership (D4.1/4.2) | Simulate size rejection with a sentinel identifier; release an owned secret through an instrumented buffer provider | Diagnostic omits sentinel and secret; ownership invokes clearing before releasing supported storage. |
| S-33 | full-parity | Backend and scale configuration (B2f-6; M6.1) | Both display values present, then add headless override; select X11 and supply invalid scale | Select Wayland then headless; invalid X11 override produces warning/auto fallback, not panic. |
| S-34 | full-parity | Unavailable desktop actions (M1.1/M2.1) | Host fixture cannot hide other apps and rejects restart launch | Hide/unhide report unsupported; restart exposes failure while original app stays live. |
| S-35 | full-parity | Resource transport controls (M2.2) | Fetch fixture never completes; expire caller deadline, then repeat with explicit cancellation | Both terminate as defined, with no implicit retry and no claimed successful result. |
| S-36 | minimum-viable | Scene order through filter boundaries (P S6) | Record back/front primitives of the same kind around a nested filter group; give the inner boundary an empty clip | Inspectable scene preserves the back/group/front order, keeps matched scope markers even when clipped, and uses only range indices belonging to that scene. |

## Slices

Routes are planned, not executed, and require the named fixtures in the
chosen port. None asserts native display or device parity.

| Slice ID | Deliverable | Modules | Proves scenarios | Depends on | Tier | Verification route |
|---|---|---|---|---|---|---|
| SL-01 | Test embedding and update/window lifecycle | UI runtime, Host, Embedding entry point | S-01, S-02 | none | minimum-viable | test |
| SL-02 | Identity, traversal and geometric layout | Layout and elements, Frame | S-03, S-04, S-05 | SL-01 | minimum-viable | test |
| SL-03 | Ordered scene, publication and demand | Frame, Layout and elements, Presenter | S-06, S-07, S-08, S-36 | SL-02 | minimum-viable | test |
| SL-04 | Dispatch, focus and bindings | Interaction, Scheduler, Frame | S-09, S-10, S-11 | SL-03 | minimum-viable | test |
| SL-05 | Touch recognition and scroll events | Interaction, Scheduler | S-12, S-13 | SL-04 | major-workflow | test |
| SL-06 | Motion sampling and scheduling | Motion, Scheduler, Frame | S-14, S-15, S-16, S-17 | SL-03 | major-workflow | test |
| SL-07 | Document text and editor interchange | Text, Layout and elements, Interaction | S-18, S-19, S-20, S-21, S-22, S-25 | SL-04 | major-workflow | test |
| SL-08 | Virtualization, loading and accessibility | Layout and elements, Resources and accessibility | S-23, S-24, S-26 | SL-03, SL-04 | major-workflow | test |
| SL-09 | Executor lifecycle and affinity | Scheduler, UI runtime | S-27, S-28 | SL-01 | major-workflow | test |
| SL-10 | Host services and fault semantics | Host, Embedding entry point, Resources and accessibility | S-29, S-30, S-31, S-32, S-33, S-34, S-35 | SL-04, SL-08, SL-09 | full-parity | test |

## Deliberate Non-Goals

**Implementation choices:** no required Rust/Cargo compatibility, crate
layout, profiler, inspector, distribution machinery or source-specific
bridge APIs. Initially stub unsupported native capabilities explicitly.
Exhaustive renderer, font/IME, permission and platform-role equivalence is
not inferred from fake hosts. Pixel-identical output, delivered cadence
and automatic software fallback are not minimum-viable requirements.

## Coverage and limits

- **Inspected scope:** B's module and ownership map, contracts, protocols,
  agent seams, defect dispositions and inherited question IDs.
- **Targeted deep reads:** C §Black-Box Acceptance List for concrete fixtures;
  C1–C6/C15/C23 for motion, identity and prefix conditions; P catalog for
  normalized fields. S4/S9 qualifications and defect dispositions follow B;
  underlying scans were not re-audited.
- **Skipped scope:** exhaustive style/primitive/native message and shader
  matrices, host capability probes, benchmarks and implementation execution.
- **Evidence basis:** upstream source-based findings and indexed scenarios.
  Acceptance routes specify future observations, not results.
- **Known blind spots:** three runtime questions below and host policy
  differences outside the inspected scenarios.
- **Coverage disposition:** COMPLETE for the scoped language-agnostic
  implementation plan; live-host parity is unverified.

## Known Unknowns

All three are **UNRESOLVED**, remain `needs-runtime-test`, and have the
disposition `verify at runtime`. B and its cited source mechanisms do not
settle them; no duplicate framework open questions are registered.

| ID | Kind | Description | Deferred Reason / available evidence | Impact and blocking verdict | Verification |
|---|---|---|---|---|---|
| `q-headless-parity` | needs-runtime-test | Can offscreen frames serve as an on-screen pixel oracle? | P S6 and B identify scene and capture seams, not paired comparisons. | Non-blocking for core; blocks using offscreen output as a pixel oracle. | Capture matched scene/frame, scale and fonts on both paths; compare with a declared threshold (B7a Q1). |
| `q-gpu-fallback` | needs-runtime-test | What happens when no usable device or surface is available? | P S6/S11 show selected paths, not actual device/driver outcomes. | Non-blocking for core; no cross-host fallback guarantee. | Observe startup/failure by host with hardware hidden and distinguish software rasterizer availability (B7a Q2). |
| `q-frame-scheduling` | needs-runtime-test | What paces actual delivered frames on Linux, Windows and web? | P S7/S11 identify trigger mechanisms only. | Non-blocking for clock-driven state; blocks a native cadence parity claim. | Timestamp request, redraw and presentation observations by backend and visibility/idle state (B7a Q3). |

## Carry-Forward

No downstream framework phase. B7a is separate work; B7b–B7d integrate
corrections, consolidate the guide and perform final verification.

## Spike List

- Q1: reuse existing `post-frame-capture` — collect matched captures on
  accessible Metal/wgpu hosts; no comparison, no parity finding.
- Q2: `post-gpu-fallback` — collect observed initialization results per
  host; never conflate software-rendering and no-device environments.
- Q3: `post-frame-scheduling` — observe request versus delivered cadence
  across X11, Wayland, Windows and web using the B7a plan. Do not infer
  display completion from callback delivery.

## Validation

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Concept-level modules defined | PASS | Module model names ports, owners, collaborators and invariants. |
| 2 | Required behaviors stated | PASS | UI, geometry, frame, input, motion, text and host contracts. |
| 3 | Protocol and persisted-state expectations stated | PASS | Normalized envelope, lifecycle and storage boundaries. |
| 4 | Acceptance and unknowns included | PASS | Concrete scenarios and six-field unresolved accounting. |
| 5 | Both defect scans dispositioned | PASS | All eleven IDs carry explicit design consequences. |
| 6 | Evidence levels marked | PASS | Requirements, choices, strong inferences and unresolved claims distinguished. |
| 7 | Coverage and limits named | PASS | Scope, evidence and known blind spots explicit. |
| 8 | Lower-level reads tied to the bundle | PASS | Coverage records targeted fixture and carrier reads. |
| 9 | Each slice proves existing scenarios | PASS | Slice table lists stable Scenario IDs. |
| 10 | Minimum-viable scenarios owned | PASS | SL-01–SL-04 cover S-01–S-11 and S-36. |
| 11 | Observable verification route per slice | PASS | All slices use planned fixture tests; no runtime verification implied. |
| 12 | Strategic variant recorded | PASS | Language-agnostic, selected by the approved roadmap; no stack-specific proof commands. |

**Validated by:** 2026-11-23 (B6, language-agnostic)

**Overall:** PASS
