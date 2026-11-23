# Semantic Defects Report — GPUI-CE

## Scan Context

- **Source:** repository root; source references below are relative to it.
- **Architecture:** `findings/architecture/architecture-map.md`, Concurrency Model.
- **Contracts:** `findings/contracts/behavioral-contracts.md`, notably C20,
  C27–C28, C35–C36 and Security and Authorization.
- **Protocols:** `findings/protocols/protocols-and-state.md`, S3 and S6–S8.
- **Mechanical baseline:** `findings/defect-scan-mechanical/mechanical-defects.md`.
- **Pipeline:** `workflow/pipeline-full-with-deep-audit.yaml`.
- **Date:** 2026-11-23.
- **Scope:** B4a–B4c / passes 3, 4 and 5.

## Pass 3: Concurrency and Resource Management

| # | Location | Defect | Severity | Evidence Level | Action |
|---|---|---|---|---|---|
| 3.1 | `crates/gpui/src/queue.rs:80-92,156-161`; worker consumers in `crates/gpui_linux/src/linux/dispatcher.rs:31-52,90-98` and `crates/gpui_web/src/dispatcher.rs:184-205` | Closing the shared priority queue can strand already-idle workers. Sender drop decrements the sender count without waking blocked receivers; blocking receive only checks disconnection before its wait loop. This is a teardown gap at the worker handoff in protocols S8, not a change to lane ordering or the dedicated-session contract. | Medium | strong inference | port differently |

**3.1 — queue closure is not a wakeable state transition.** The receive
path already treats empty plus no senders as terminal, and the web worker
explicitly exits on that result. But if a worker enters the wait with an
empty queue while the sender is still alive, the sender's drop supplies no
wakeup. A wake without new items would not help: the loop tests only
emptiness (`crates/gpui/src/queue.rs:80-92,156-161`). The Linux worker
iterator also relies on the blocking receive returning an error to exit
(`crates/gpui/src/queue.rs:368-375`).

The source establishes the missing exit path, not a process-exit hang,
measured resource growth, or the behavior of every dispatcher. A port
should synchronize the queue's closed predicate with its wait, wake all
blocked workers on final close, and drain queued work before returning the
terminal result. This is a port recommendation, not a source change.

### Checked paths not promoted to findings

- **Executor shutdown (S8):** Linux and Windows deliberately retain an
  undeliverable foreground runnable on the failure branch rather than
  risking destruction of a thread-affine future on the wrong thread
  (`crates/gpui_linux/src/linux/dispatcher.rs:113-126`;
  `crates/gpui_windows/src/dispatcher.rs:118-143`). Linux's delayed-dispatch
  send failure also explicitly retains work as shutdown policy
  (`crates/gpui_linux/src/linux/dispatcher.rs:129-135`). These are observed
  source branches, not evidence of accumulating leaks during normal operation.

- **Render ownership (S3/S6, C20):** wgpu prunes imported-surface bindings
  against the full scene before encoding, not between batches. On a failed
  render after swapchain acquisition, the adapter drops the view/frame
  before reconfiguring. These are source-observed ownership steps, not
  proof of when the driver releases its resources
  (`crates/gpui_wgpu/src/wgpu_renderer/frame.rs:19-42`;
  `crates/gpui_wgpu/src/wgpu_renderer/surfaces/texture.rs:16-31`;
  `crates/gpui_wgpu/src/wgpu_renderer/platform.rs:136-170`). The frame-cache
  invariant is already addressed in protocols S3 and is not counted again.

## Pass 4: Security and Trust Boundaries

### Credential confidentiality

| # | Location | Defect | Severity | Evidence Level | Action |
|---|---|---|---|---|---|
| 4.1 | `crates/gpui_windows/src/platform.rs:833-842`; contract C36 | An oversized credential returns an error containing the full caller-supplied lookup key. This places potentially sensitive URL data in a diagnostic that only needs to explain the size rejection. | Low | observed fact | port differently |
| 4.2 | `crates/gpui_linux/src/linux/platform.rs:679-704`; `crates/gpui/src/app.rs:1842-1845`; contract C36 | Linux copies the recovered secret into an ordinary byte vector at the public API boundary, explicitly losing the store-side zeroization described in the adapter. | Low | observed fact | port differently |

**4.1 — separate lookup identifiers from diagnostics.** The rejection occurs
before the host write. It returns an error to the caller, not a GPUI log entry,
and does not include password bytes. A port can retain the actionable size
error without embedding the lookup key. The caller should use a stable,
non-secret identifier even when that identifier resembles a URL.

**4.2 — separate persistent storage from memory ownership.** A port can use
a secret buffer with explicit ownership and cleanup, minimizing intermediate
copies. This is a defense-in-depth improvement, not evidence of secret
recovery from process memory. Document the caller's responsibility once the
secret leaves the adapter.

### Trust-boundary assessment

- **Credential store (C36):** GPUI takes an identifier, username and password
  from application code and delegates authorization and persistence to the
  host. Windows constructs a prefixed target name, macOS queries for an
  Internet-password item by server, and Linux searches by URL and filters
  reads and deletes by the configured label. These are request shapes, not
  proof of equivalent isolation, replacement, or permission semantics across
  stores. Web does not implement storage
  (`crates/gpui_windows/src/util.rs:85-87`;
  `crates/gpui_macos/src/platform.rs:1140-1242`;
  `crates/gpui_linux/src/linux/platform.rs:657-731`;
  `crates/gpui_web/src/platform.rs:631-645`). The API has no framework role
  or session model; a lookup key is not an authorization decision.

- **Clipboard (C35):** Treat host text, images, paths and metadata as external
  data. The macOS and Windows text checks associate metadata with matching
  text; the hash is for change detection, not writer authentication. The
  typed JSON helper can reject malformed data but does not establish source
  trust or validate application-specific semantics
  (`crates/gpui_macos/src/pasteboard.rs:108-134`;
  `crates/gpui_windows/src/clipboard.rs:229-246`;
  `crates/gpui/src/platform.rs:3846-3862`). No privileged consumer of this
  metadata was established in the inspected paths.

- **Clipboard permissions and formats (C35):** Web checks clipboard API
  availability, initiates the read synchronously, and handles rejection in
  its asynchronous result. It accepts plain text and recognized image types,
  not arbitrary HTML/custom formats in that path. No browser permission
  grant is inferred. On Linux, the Wayland path delegates to its clipboard
  reader; X11 checks current ownership before using the cached item and
  otherwise reads the external selection
  (`crates/gpui_web/src/platform.rs:556-627`;
  `crates/gpui_linux/src/linux/wayland/client.rs:1296-1298`;
  `crates/gpui_linux/src/linux/x11/client.rs:1781-1795`).

## Pass 5: API Contract Violations

| # | Location | Defect | Severity | Evidence Level | Action | Spec reference |
|---|---|---|---|---|---|---|
| 5.1 | `crates/gpui/src/gestures.rs:479-489,751-765`; `crates/gpui/src/window.rs:6127-6140`; `crates/gpui/src/elements/div.rs:3883-3897` | Raw-touch tap recognition dispatches synthetic mouse down/up. The ordinary `Div` click path constructs `ClickEvent::Mouse` when its click guards pass, not the documented `ClickEvent::Touch`. The traced recognizer also does not recognize pinch from raw contacts. | Medium | observed fact | port differently | C27; `crates/gpui/src/gestures.rs:3-11`; protocols S4 records the implemented touch path. |
| 5.2 | `crates/gpui/src/text_system/window_text_system.rs:37-56` | `shape_line` documents an unconditional panic for newlines, but its explicit newline check is a debug assertion. The wrapper does not enforce that promise in builds with debug assertions disabled. | Low | observed fact | port differently | C28 and public `shape_line` documentation at `window_text_system.rs:37-42`. |
| 5.3 | `crates/gpui/src/app.rs:1750-1760`; `crates/gpui/src/platform.rs:339-348`; `crates/gpui_windows/src/platform.rs:829-831`; `crates/gpui_windows/src/clipboard.rs:92-94` | The public awaitable clipboard read says read failures resolve to errors. The default adapter implementation wraps the synchronous `Option` in `Ok`; the Windows reader's clipboard-open failure becomes `Ok(None)` via this path, not a typed error. | Low | observed fact | port differently | C35 and public `App::read_from_clipboard_async` documentation at `app.rs:1750-1755`. |

- **5.1:** Preserve synthesized pointer compatibility, including the existing
  dispatch guards, when reproducing the current raw-touch path. Distinguish
  the public touch-click variant from what this route emits, and do not
  infer raw-touch pinch recognition from the separate `PlatformInput::Pinch`
  carrier (`crates/gpui/src/interactive.rs:771-800`).
- **5.2:** Specify the single-line precondition and choose consistent
  validation independently of build mode. This is not a claim that
  multiline input succeeds in optimized builds: subsequent shaping is
  outside the assertion comparison.
- **5.3:** Model success-with-no-item and host-read failure separately where
  the backend can distinguish them, or document the lossy fallback. The
  finding concerns the adapter's return mapping, not conditions under which
  the Windows API fails or web permissions are granted.

**Cross-check not counted twice:** protocols S9 already qualifies C28's
clamp wording. GPUI's Parley adapter reduces the soft-break budget across
paragraphs, without suppressing hard paragraph breaks. This is a clarification
to the reconstruction contract, not evidence of an unconditional document
row cap being violated (`crates/gpui_ce_parley/src/text_system.rs:1634,1712-1721,2059-2076`).

## Summary

Counts cover all three semantic passes.

### Findings by Severity

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 0 |
| Medium | 2 |
| Low | 4 |
| **Total** | **6** |

### Findings by Pass

| Pass | Critical | High | Medium | Low | Total |
|---|---:|---:|---:|---:|---:|
| 3. Concurrency and resources | 0 | 0 | 1 | 0 | 1 |
| 4. Security and trust | 0 | 0 | 0 | 2 | 2 |
| 5. API contract violations | 0 | 0 | 1 | 2 | 3 |

### Top Findings

1. Pass 3, `crates/gpui/src/queue.rs:80-92,156-161`: shared queue
   closure does not wake idle workers. Medium; port differently.
2. Pass 5, `crates/gpui/src/window.rs:6134-6140`: recognized taps enter
   mouse dispatch rather than producing the documented touch-click variant.
   Medium; port differently.
3. Pass 4, `crates/gpui_windows/src/platform.rs:833-842`: size rejection
   echoes the credential lookup key. Low; port differently.
4. Pass 4, `crates/gpui_linux/src/linux/platform.rs:679-704`: ordinary
   output bytes lose store-side zeroization. Low; port differently.

### Carry-Forward Closure

None routed to this phase at entry. The mechanical carry-forward `mech-CF1`
was closed in protocols, where S3 records the frame-range invariant
without claiming a reachable defect. `contracts-CF1` also closed there.
Neither is reopened here.

## Runtime probes

None run. The queue disposition is based on the receive and sender-drop paths.

## Open Questions

No new framework questions. The inherited questions on headless
pixel parity, GPU-less behavior, and delivered frame pacing still need
runtime evidence; this pass does not propose an answer to any of them.

## Coverage and limits

- **Inspected scope:** worker enqueue/dequeue, disconnection and worker
  exit branches; foreground and delayed dispatch failure ownership;
  representative wgpu acquire/encode/cache/reconfigure paths.
- **Inspected scope (B4b):** credential lookup inputs, host delegation,
  diagnostics and secret output ownership; clipboard ownership, format
  handling, metadata provenance and web permission handoff.
- **Inspected scope (B4c):** raw touch through window/element dispatch,
  single-line shaping guards, paragraph clamp qualification, and the
  default async clipboard return mapping through the Windows reader.
- **Skipped scope:** full adapter shutdown matrix, native and driver
  allocation internals, lock-order proof across dependencies, dependency
  vulnerability scanning, host authorization tests, downstream clipboard
  consumers, and exhaustive contract testing across platforms.
- **Evidence basis:** source inspection and upstream findings.
- **Known blind spots:** worker lifetime in a live host, driver-side
  reclamation, quantitative effects of repeated dispatcher teardown, and
  native store/browser policy outcomes.
- **Coverage disposition:** COMPLETE for the planned, source-based semantic
  passes; not exhaustive across host APIs.

## Validation

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | All three passes documented | PASS | Passes 3, 4 and 5 contain findings. |
| 2 | Location, severity, evidence level and action present | PASS | All numbered rows include these fields. |
| 3 | Pass 5 cites the diverging contract | PASS | C27, C28 and C35 plus public source docs. |
| 4 | Organized by pass and severity; totals reconcile | PASS | Six findings: two medium and four low. |
| 5 | Carry-forwards addressed | PASS | None targeted this phase; previous closures accounted for. |
| 6 | Evidence levels present | PASS | Source observations distinguished from queue-lifecycle inference. |
| 7 | Unsettled findings correctly routed | PASS | No new external-behavior or open-question findings; three inherited questions remain unresolved. |
| 8 | Quantitative specifics supported | PASS | No uncited numeric limits asserted; severity totals follow the rows. |
| 9 | Coverage and limits stated | PASS | Inspected and skipped scope, evidence basis, and blind spots documented. |

**Validated by:** 2026-11-23 (semantic defects phase)

**Overall:** PASS
