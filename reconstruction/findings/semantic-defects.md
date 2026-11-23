# Semantic Defects Report — GPUI-CE

## Scan Context

- **Source:** repository root; source references below are relative to it.
- **Architecture:** `findings/architecture/architecture-map.md`, Concurrency Model.
- **Contracts:** `findings/contracts/behavioral-contracts.md`, notably C20.
- **Protocols:** `findings/protocols/protocols-and-state.md`, S3 and S6–S8.
- **Mechanical baseline:** `findings/defect-scan-mechanical/mechanical-defects.md`.
- **Pipeline:** `workflow/pipeline-full-with-deep-audit.yaml`.
- **Date:** 2026-11-23.
- **Scope:** B4a / pass 3 only. Passes 4 and 5 are pending.

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

Pending B4b.

## Pass 5: API Contract Violations

Pending B4c.

## Summary

Counts cover executed passes only.

### Findings by Severity

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 0 |
| Medium | 1 |
| Low | 0 |
| **Total** | **1** |

### Findings by Pass

| Pass | Critical | High | Medium | Low | Total |
|---|---:|---:|---:|---:|---:|
| 3. Concurrency and resources | 0 | 0 | 1 | 0 | 1 |
| 4. Security and trust | — | — | — | — | Pending |
| 5. API contract violations | — | — | — | — | Pending |

### Top Findings

1. Pass 3, `crates/gpui/src/queue.rs:80-92,156-161`: shared queue
   closure does not wake idle workers. Medium; port differently.

### Carry-Forward Closure

None routed to this phase at entry. B4a does not close runtime questions.

## Runtime probes

None run. The queue disposition is based on the receive and sender-drop paths.

## Open Questions

No new framework questions from B4a. The inherited questions on headless
pixel parity, GPU-less behavior, and delivered frame pacing still need
runtime evidence; this pass does not propose an answer to any of them.

## Coverage and limits

- **Inspected scope:** worker enqueue/dequeue, disconnection and worker
  exit branches; foreground and delayed dispatch failure ownership;
  representative wgpu acquire/encode/cache/reconfigure paths.
- **Skipped scope:** full adapter shutdown matrix, native and driver
  allocation internals, lock-order proof across dependencies, B4b and B4c.
- **Evidence basis:** source inspection and upstream findings.
- **Known blind spots:** worker lifetime in a live host, driver-side
  reclamation, and quantitative effects of repeated dispatcher teardown.
- **Coverage disposition:** PARTIAL — B4a only.

## Validation

Phase validation pending B4c. Block check: the numbered finding cites its
protocol boundary and both sides of the queue lifecycle; summary counts match
the executed pass.
