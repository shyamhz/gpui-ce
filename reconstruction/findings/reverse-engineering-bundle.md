# Reverse-Engineering Bundle

## System Summary

GPUI-CE is an embedded UI library. Application code owns the model and creates
windows with root views. The main-thread runtime owns entity identity, updates,
focus and dispatch. A frame rebuilds or reuses parts of the view tree, computes
geometry, prepares hit-testing and input state, and paints into a typed scene.
The core publishes that scene separately from submitting it for presentation.
Native and browser adapters translate host events and provide windowing, graphics
and services; they do not own the core UI state (A, C13–C26, P S1–S8).

**Porting recommendation:** build a testable core with one host adapter first.
Keep its rules independent of a particular graphics API, layout library, task
runtime or Rust crate boundary. Reference behavior and recommended departures
are intentionally separate below. This bundle does not establish native pixel
parity, delivered frame cadence, or unavailability behavior on live hosts.

## Source Index

Paths below are relative to `.codecarto/findings/`. IDs are stable pointers to
upstream sections, which in turn cite repository source. Use the bundle for the
initial specification; follow a trigger only for the affected slice.

| Area | Canonical upstream section | Summary carried forward | Deep-read trigger |
|---|---|---|---|
| A — architecture | `architecture/architecture-map.md`, Layer Map, Runtime Lifecycle, Concurrency Model, Agent Addressability | Main-thread core, adapter dependencies, test and host seams | Choosing a platform/build target, resolving a package edge, or verifying startup/shutdown ownership. Use P S1/S2/S7 over the coarse architecture sequence for frame/effect ordering. |
| C — motion | `contracts/behavioral-contracts.md`, C1–C6; Black-Box Acceptance B2d-1–10 | Timestamp samples, continuity, repeat/sync, demand, reduced motion | Pin easing/spring math, completion boundaries, or callback timing; pull B2d fixtures before making timing conformance claims. |
| C — geometry and elements | Same, C7–C20 and C32–C33; B2c-1–8, B2a-1–8, B2f-1–2 | Constraints, snapping, identity, phases, hitboxes, deferred ordering, resource states | Need exact mappings, cache invalidation or component behavior; use P S3/S6 for cache and scene ownership. |
| C — input and focus | Same, C21–C27; B2b-1–8 | Key identity, precedence and replay, focus invalidation, pointer routing | Writing exact ties, timeout/replay or modality rules; take raw touch behavior from P S4 and semantic 5.1 where C27 differs. |
| C — text | Same, C28–C31; B2e-1–6; P S9–S10 | Paragraphs, byte-index carets, fallback/raster boundary, editor composition | Pin whitespace, RTL, source indices, clamping, or malformed run behavior. Restrict B2e-2's exact row expectation to its single-paragraph fixture. |
| C — host services | Same, C34–C38; B2f-3–6 and Security and Authorization | Accessibility, clipboard/credential capability, popup roles, backend precedence | Need error/status shapes, action routing, unsupported cases, or exact environment rules. Host permissions are not decided here. |
| P — protocols | `protocols/protocols-and-state.md`, Event Catalog, S1–S11, Persistent Schema Notes | Normalized messages, state machines, render and executor handoffs, format ownership | Extracting exact variant fields or adapter lifecycle branches; use S6/S7/S11 and B7a for presentation or timing, not source as a runtime oracle. |
| M — mechanical defects | `defect-scan-mechanical/mechanical-defects.md`, passes 1/2/6 | Five dispositions below | Designing an affected failure path. For 1.2 read P S3 before treating reachability as established. |
| D — semantic defects | `defect-scan-semantic/semantic-defects.md`, passes 3/4/5 | Six dispositions below | Specifying closure, secret ownership, tap delivery, text guards or clipboard failure; read evidence/limits before claiming impact. |

Acceptance scenario ranges above refer to planned checks, not test runs. Include
all referenced scenario families in the spec or explicitly scope them out with a
reason. For exact setup and expected observations use C §Black-Box Acceptance
List; the B2e-2 clarification in P S9 supersedes broader wording.

## Layer Map With Ownership

**Observed fact** at the current source boundaries (A §Layer Map; P S6, S8–S10).

| Layer / Module | Role | Owns |
|---|---|---|
| Scheduler and data helpers | Reusable substrate below the UI core | Tasks, clocks, priority model; value and ordered-tree utilities |
| `gpui` application and window core | Update and interaction runtime | Entity lifetimes, effect drain, focus/key/observer graphs, window and frame state, adapter interfaces |
| `gpui` elements, layout and scene | Retained identity with frame traversal | Style resolution, constraints and geometry, hitboxes, paint records, frame-owned scene plan |
| Parley, font catalog, raster interfaces | Text and font subsystem | Document/inline shaping, source/visual mappings, face lookup; rasterizer/atlas handoff is separate |
| Shared render support and GPU backends | Scene consumers | GPU resources, intermediates, submission and host presentation; Metal, DirectX and wgpu implementations |
| Platform facade and host adapters | Integration | Boot, native/canvas windows, input/IME, frame triggers, clipboard and other host services |
| Widgets, bridges and tooling | Optional consumers | Controls, Tokio/media hooks, tests, profiling and packaging; not required to reproduce core dispatch |

## Feature Contract Table

Priorities are **porting recommendations**, not feature flags. Behavioral
summaries inherit the indexed source evidence; exceptions are called out.

| Feature | Surface | Priority | Key contracts | Notes / acceptance route |
|---|---|---|---|---|
| App, entities and windows | Library | core | A lifecycle; P S1–S2 | Main-thread update; initial draw before open returns; effects drain at outer update boundary; synchronous close veto distinct from close notification. |
| Element identity and traversal | Library | core | C13–C16, C19; P S3 | Layout → prepaint → paint; preserve stable ID state, occlusion and deferred ordering. B2a-1–4/7; M1.2. |
| Geometry and inline layout | Library | core | C7–C12 | Retain definite/min/max-content distinctions, rem and relative units, shared-edge snapping, direction before layout, and baseline alignment. B2c-1–8. |
| Scene compilation | Renderer seam | core | P S3/S6 | Record/replay, preserve primitive/layer order, pair filter markers, derive resource requirements, and bind ranges to their scene. No GPU-buffer replay requirement. M1.2. |
| Input, shortcuts and focus | Host/library | core | C21–C27, C33; P catalog/S2/S4 | Match key identity separately from typed text; honor context and insertion precedence, scoped disable, prefix timeout/replay and focus cancel; capture then bubble. B2b-1–8, B2f-2; D5.1. |
| Motion and frame demand | Library/host | important | C1–C6; P S7 | Preserve delay, iteration/final samples, easing overshoot, analytic spring branches, continuous retarget including spring velocity, shared sync epoch and reduce-motion snap. B2d-1–10. |
| Text and IME | Library/host | important | C28–C31; P S9–S10 | Document paragraphs, optional wrap and soft clamp, source byte/cluster geometry, ordered face fallback, raster errors, UTF-16 editing ranges and marked composition. B2e-1–6; D5.2. |
| Executors and timers | Library/host | important | A Concurrency Model; P S8 | Foreground affinity, background scheduling, wait/cancel/detach, dedicated session lifetime; no cross-worker completion order. D3.1. |
| Virtualization, canvas and resources | Library | important | C17–C18, C20, C32–C33 | Visible subset/range, canvas phase order, container resize, image pending/ready/error and scroll reclamping. B2a-5/6/8, B2f-1/2; M2.2 at fetch seam. |
| Accessibility | Library/host | important | C34 | Optional last-frame tree, stable node IDs, forcing and action handling independent of a live assistive client where supported. B2f-3. |
| Native roles and configuration | Host | optional beyond first host | C37–C38; P S5/S11 | Preserve capability gates and typed unsupported paths; distinguish environment selection from a successful connection. B2f-5/6; M1.1, M2.1, M6.1. |
| Clipboard and credentials | Host | optional | C35–C36; P Persistent Schema Notes | Host-owned typed payloads, explicit capability/error distinctions, no framework authorization. B2f-4; D4.1/4.2/5.3. |
| Repository tooling | Build/test | incidental | A Build and Packaging | No requirement for Rust-specific codegen, CI, release or governance machinery. |

## Protocol and State Notes

**Observed facts**, except the frame-ownership interpretation called out below.

- **Carrier and dispatch (P catalog, S2/S4/S10):** Window-scoped in-memory
  tagged input covers key down/up, modifiers, mouse down/up/pressure/move/exit,
  scroll, pinch, long press, touch drag, file drop and raw touch. No common
  timestamp, delivery acknowledgement or replay format. Dispatch returns
  propagation and default-prevention flags synchronously. Scroll retains
  pixels vs lines and phase; contact prediction is optional; file-drop
  phases can normalize into pointer work. Raw touch has pending, pan and
  claimed gesture states; cancellation differs from release, momentum can
  continue after release, and a tap can produce a mouse click through the
  normal guards. IME marked/committed updates are a separate editor channel.

- **Update and frame barriers (P S1–S3/S7):** Reserve/open, build root, initial
  draw, register live window; a borrowed window slot is temporarily unavailable.
  Drain effects FIFO at the outer update boundary, with pending notify dedup
  and lifecycle cleanup, not once per draw. Publish the completed frame before
  comparing rendered focus paths. Accepted frame requests drain a snapshot of
  next-frame callbacks before the draw decision; callbacks queued during that
  drain remain pending. Dirty or forced work rebuilds; presentation need can
  reuse the last scene. Native requests, core redraw, GPU submission and
  displayed output are separate observations.

- **Plan lifetime (P S3/S6):** Paint records are clipped/ordered and compiled
  into scene-owned batches and filter commands. **Strong inference:** the
  traced reuse path reads the rendered frame and rebases cached ranges and
  dispatch references into the building frame before rotation. Preserve that
  ownership invariant; a reachable stale range is not established.

- **Tasks (P S8):** Lane FIFO applies to dequeue where the weighted queue is
  used; readiness, thread affinity and completion are distinct. Dedicated
  session teardown tracks runnable senders, not just root completion. A timer
  has a completion handoff, not a guaranteed real-time deadline.

- **Host roles and formats (P S5/S9–S11, Persistent Schema Notes; C35–C38):**
  Popup role is distinct from layer or toplevel. Wayland stages popup size,
  applies it at surface configure/ack, and routes dismissal through close.
  Keymap bindings and action payloads are in-process; JSON action params,
  files/assets, clipboard and credential host formats do not imply a GPUI
  state database, keymap file schema, migration or restart replay contract.
  On text input, do not substitute UTF-8 byte indices for UTF-16 code units
  or equate scalar snapping with grapheme/cluster snapping.

## Portability Hazards

These are **portability hazards** and proposed mitigations, not findings of
failure in an untested port.

| Hazard | Source phase | Impact | Mitigation |
|---|---|---|---|
| Reentrant UI access in a different memory model | A, P S1–S2 | Affinity and release order can change | Serialize UI mutation; pin effect, borrow and release boundaries. |
| Generic CSS, geometry or text engine substitution | C7–C12, C28–C31 | Different defaults, shared edges, direction, clusters or glyphs | Use behavior fixtures, fixed fonts, source indices and explicit conversions. |
| Backend batching or cache shortcuts | P S3/S6; M1.2 | Changed compositing order or cross-frame references | Bound cache reads by ownership; check ordering and filter invariants before pixel comparisons. |
| Host clocks, surfaces and inaccessible presentation state | A addressability; P S6–S8/S11 | Simulated frames cannot establish visible cadence, GPU recovery or pixel parity | Verify at runtime using B7a; keep logic traces and pixel/host oracles separate. |
| Clipboard/credential metadata interpreted as authority | C35–C36; D pass 4 | Trust and error semantics differ by host | Treat payloads as data; preserve capability boundaries and use explicit secret ownership. |
| Host SDKs and build gates | A Build and Packaging; C37–C38 | A compiled feature does not imply runtime capability | Test supported and unsupported roles separately; do not treat selected backend as a connectivity result. |

## Defect Synthesis

M and D refer to the reports in the Source Index. Their Runtime probes sections
contain no execution evidence. “Required design consequence” below is a
porting recommendation, not a claim of a source fix.

| Defect ID | Source Report | One-line Description | Severity / evidence | Disposition | Required design consequence |
|---|---|---|---|---|---|
| M1.1 | M pass 1 | Ungated hide/unhide-other-apps panics on Windows. | Medium / observed fact | port differently | Return unsupported or define a harmless no-op; do not copy the panic. |
| M1.2 | M pass 1; P S3 | Frame reuse relies on valid scene/dispatch references; a reachable stale path is unproven. | Medium / strong inference | port differently | Define frame ownership and membership checks; no runtime defect claim. |
| M2.1 | M pass 2 | Restart spawn failure is log-only on the inspected desktop paths. | Medium / observed fact | port differently | Expose failure; do not request quit after failed launch. |
| D3.1 | D pass 3 | Shared queue close can strand waiting workers. | Medium / strong inference | port differently | Make closure a state visible to waiters; drain queued work and wake all blocked workers on close. |
| D5.1 | D pass 5; P S4 | Documented touch click/pinch differs from raw-touch implementation. | Medium / observed fact | port differently | Specify the actual synthetic pointer path and keep separate native pinch input capability; do not invent direct touch delivery. |
| M2.2 | M pass 2 | Fetch interface lacks timeout, cancellation and retry controls. | Low / observed fact | port differently | Define caller policy for deadlines and cancellation; do not assume unconditional retries. |
| M6.1 | M pass 6 | Invalid X11 scale override panics on the reached backend. | Low / observed fact | port differently | Validate and specify an observable rejection or warning/fallback. |
| D4.1, D4.2 | D pass 4 | Credential key in size error; ordinary output buffer loses zeroization. | Low / observed fact | port differently | Redact the key and use explicit secret-buffer ownership/cleanup. |
| D5.2 | D pass 5 | Newline precondition checked only with debug assertions. | Low / observed fact | port differently | Specify consistent validation or explicitly define the precondition; do not assume release success. |
| D5.3 | D pass 5 | Async clipboard fallback collapses a native open failure into no item. | Low / observed fact | port differently | Preserve error and absence separately when observable; document lossy fallbacks. |

## Observed Facts vs. Inferred Structure

### Observed Facts

- Core interfaces are implemented by adapters; published scene commands and
  dispatch values are in-memory data with explicit producers/consumers (A
  Dependency Direction; P catalog/S6). Runtime source entry points and test
  seams are not proof of execution or platform parity.
- Touch delivery, text clamp and clipboard error behavior use the implementing
  paths in P S4/S9 and D5.1/D5.3 over broader contract prose.

### Inferred Structure

- **Strong inference:** the natural independent implementation boundary is
  “UI state and ordered scene” versus “host event delivery and presentation.”
  It follows from P S1–S8, not from a requirement to preserve source packages.
- **Strong inference:** inspected framework paths do not require a framework
  app-state persistence service (A Durable State; P Persistent Schema Notes).
  This does not rule out downstream application files or host store formats.

## Domain Glossary

| Term | Definition | Where Used |
|---|---|---|
| Entity / element identity | Managed application object / stable key for element-scoped state | C14–C15, P S1–S3 |
| Prepaint | Prepare paint geometry, hitboxes and later interaction work after layout | C13, C16, P S3 |
| Published frame | Completed scene and dispatch snapshot, not a displayed image | P S1/S6–S7 |
| Scene plan | Ordered commands indexing the finished scene and declaring resource needs | P S6 |
| Dispatch context / pending input | Focus-derived binding scope / buffered key prefix awaiting resolution | C21–C25 |
| Visual row / caret affinity | Shaped display row / attachment at an index with multiple visual placements | C28–C29, P S9 |
| Marked text | Provisional composition associated with editor ranges before commitment | P S10 |

## Agent Addressability

“Headless” refers to the scoped operation, not to a GPU-less or pixel-identical
runtime. Programmatic entry points below are source-observed, not run here.

| Surface / concern | Headless | Inspectable state | Programmatic seam | Evidence | Notes |
|---|---|---|---|---|---|
| App, entities and windows | yes | yes | test | observed fact | `TestApp::open_window` and app updates; A Agent Addressability. |
| Element identity and traversal | yes | partial | test | observed fact | Test view can retain/observe state and record phase callbacks (C13–C16). |
| Geometry and inline layout | yes | yes | library/test | observed fact | Bounds/measurement queries and text fixtures (C7–C12). |
| Scene compilation | yes | partial | library/test | observed fact | Scene plan and `Window::painted_quads` (`crates/gpui/src/window.rs:2807`); not native output. |
| Input, shortcuts and focus | yes | yes | test | observed fact | `TestApp` window helpers simulate inputs (`crates/gpui/src/app/test_app.rs:597-760`); not OS emission. |
| Motion and frame demand | partial | partial | library/test | observed fact | Sample motion and drive test frames; host cadence is a missing seam (C1–C6, P S7). |
| Text and IME | partial | yes | library/test | observed fact | Fixed-font shaping is inspectable; OS composition sequencing is not reproduced by synthetic keys (C28–C31, P S10). |
| Executors and timers | yes | partial | test | observed fact | Virtual clock and executor drain; not real worker lifetime (A Concurrency Model). |
| Virtualization, canvas and resources | partial | partial | library/test | observed fact | Synthetic bounds, callbacks and controlled loaders; native/GPU resource behavior needs host support (C17–C20, C32). |
| Accessibility | yes | yes | library/test | observed fact | Forced tree and node bounds; not actual assistive-client behavior (C34). |
| Native roles and configuration | partial | partial | library | observed fact | Selection can be inspected; real role negotiation needs the host (C37–C38, P S5/S11). |
| Clipboard and credentials | partial | partial | library/test | observed fact | Test clipboard can be driven; host permission and persistence are not inferred (C35–C36). |
| Repository tooling | partial | partial | CLI | observed fact | Build/test commands are available by configuration (A Build and Packaging); not a runtime RPC. |
| GPU presentation, fallback and cadence | partial | no | none for portable display oracle | open question | Offscreen capture exists on some paths, but no verified equivalence or cross-host timing/availability oracle. See B7a. |

## Coverage and limits

- **Inspected scope:** architecture and ownership, C1–C38 and acceptance
  families, P catalog/S1–S11, both defect scans and runtime-probe sections.
- **Secondary outputs retained:** `public-surfaces/public-surfaces.md`,
  `runtime-lifecycle/runtime-lifecycle.md`, `state-and-storage/state-and-storage.md`,
  `build-and-deploy/build-and-deploy.md` and `config-model/config-model.md` remain
  upstream references. Ordering and behavioral qualifications are in this
  bundle and P; no new secondary evidence requires duplicating them.
- **Skipped scope:** exhaustive platform internals, runtime probes, fixture
  execution, benchmark results, exact style/shader/IME variants; use the index
  to retrieve details only when a slice needs them.
- **Evidence basis:** upstream source-based findings and targeted source/index
  checks. Checked-in test assertions are not reported as test executions.
- **Known blind spots:** live presentation, GPU-less behavior, headless parity,
  and browser/native permission policy. Source identifies trigger mechanisms,
  not observed cadence. Missing portable seams are noted above.
- **Coverage disposition:** COMPLETE for the scoped synthesis and defect
  accounting; runtime questions remain explicitly unresolved.

## Open Questions

Re-triaged at B5 entry against A and P S6/S7/S11. The original IDs stay in
framework status; no duplicate registrations or closures. All three require
**verify at runtime** under `reconstruction/plan-blocks.md` B7a.

| ID | Kind | Description | Deferred reason |
|---|---|---|---|
| `q-headless-parity` | needs-runtime-test | Do comparable offscreen and on-screen outputs match for the same scene? | Requires paired captures, not matching command types. |
| `q-gpu-fallback` | needs-runtime-test | What happens without a usable GPU device/surface, and what reaches the application? | Selected branches do not establish host/driver outcomes. |
| `q-frame-scheduling` | needs-runtime-test | What paces delivered frames on Linux, Windows and web? | Trigger paths are known in part; delivered cadence needs observation. |

## Carry-Forward

No new framework carry-forward. B6 should use the Source Index and keep the
three existing questions out of baseline parity guarantees; B7a owns the
runtime work. M1.2's prior investigation route was closed in protocols, not
reopened here.

## Validation

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Summary, layers, contracts, protocols and findings synthesized | PASS | System Summary through Defect Synthesis. |
| 2 | Hazards and open questions separated from facts | PASS | Distinct sections and runtime dispositions. |
| 3 | Features sorted for porting | PASS | Core through incidental priorities. |
| 4 | Both defect reports consolidated with dispositions | PASS | All five mechanical and six semantic IDs represented. |
| 5 | Findings marked with evidence levels | PASS | Facts, inference, hazards, defect and addressability tags. |
| 6 | Coverage and limits documented | PASS | Scope, evidence, blind spots and five retained outputs. |
| 7 | Source Index supports targeted deep reads | PASS | Canonical sections and explicit trigger for each area. |
| 8 | Agent addressability and missing seams assessed | PASS | Feature-aligned rows, separate host display gap. |

**Validated by:** 2026-11-23 (porting phase)

**Overall:** PASS
