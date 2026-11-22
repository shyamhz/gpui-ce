# Mechanical Defects Report — GPUI-CE

## Scan Context

- **Source:** `../` (repository root)
- **Architecture reference:** `findings/architecture/architecture-map.md`
- **Pipeline:** workflow/pipeline-full-with-deep-audit.yaml
- **Date:** 2026-11-22
- **Scope:** Mechanical passes only (1 logic, 2 error handling, 6 configuration). Semantic passes (3 concurrency, 4 security, 5 contract violations) deferred to `defect-scan-semantic` after protocols.
- **Execution:** block-by-block per `reconstruction/plan-blocks.md`. B1a (pass 1) complete in this revision; passes 2 (B1b) and 6 (B1c) pending — their sections are marked PENDING, not "no defects found".

---

## Pass 1: Logic and Correctness

| # | Location | Defect | Severity | Evidence Level | Action |
|---|---|---|---|---|---|
| 1.1 | `crates/gpui/src/app.rs:1607,1612` → `crates/gpui_windows/src/platform.rs:536,541` | Ungated public API `App::hide_other_apps` / `unhide_other_apps` panics on Windows (`unimplemented!()`) while Linux logs-and-ignores (`linux/platform.rs:351,355`) and macOS implements (`gpui_macos/.../platform.rs:623,631`); same-file Windows convention is graceful no-op (`activate`, `hide`). | Medium | observed fact | port differently |
| 1.2 | `crates/gpui/src/key_dispatch.rs:100-107` (`refresh_node_id`), `crates/gpui/src/window.rs:3795-3860` (`reuse_prepaint` slicing), `crates/gpui/src/key_dispatch.rs:235-244` (`pop_node`) | Frame-reuse index arithmetic enforced only by `debug_assert` / fail-fast panics with no release-mode guarantee: `refresh_node_id` subtracts without check (`node_id.0 - old_range.start` wraps in release → silent misdispatch), `reuse_prepaint`/`reuse_paint` slice `rendered_frame` vectors with internally recorded indices, `pop_node` unwraps + indexes. Safe only if cached ranges never outlive the frame they were recorded against. | Medium | strong inference | port differently |

**1.1 detail.** The `Platform` trait requires `hide_other_apps`/`unhide_other_apps` (`platform.rs:162-163`, no default body). `App` forwards unconditionally. A cross-platform app calling this public API crashes on Windows. The Windows file's own convention for unimplemented macOS-centric behavior is a silent no-op (`activate`, `hide`), so the two panicking methods violate local convention as well as cross-platform parity. Port should specify no-op-or-unsupported, never panic.

**1.2 detail.** The invariant (cached prepaint/paint ranges are valid only within the frame whose `rendered_frame` they index; `refresh_node_id` callers only pass ids inside `old_range`) is believed-held — single-threaded, single-frame scoping via `next_frame.finish(&mut rendered_frame)` — but no release-mode check enforces it, and slice/unwrap sites fail by panicking while the subtraction site fails silently in release. Port should use checked arithmetic and state the invariant explicitly. Protocols phase (B3 frame-lifecycle work) should confirm the invalidation coverage; routed accordingly (see checkpoint; handoff at phase completion).

---

## Pass 2: Error Handling and Resilience

PENDING — block B1b not yet executed. (Preliminary note, not a finding: duplicate action-name registration panics at app creation (`actions!` docs); `Keystroke::parse` error paths unexamined.)

EXECUTED 2026-11-22 — findings below; preliminary note resolved: duplicate action-name panic is intentional fail-fast (dismissed, not filed); `Keystroke::parse` returns `Result<Self, InvalidKeystrokeError>` (propagated to callers; reviewed, no finding).

| 2.1 | `crates/gpui_windows/src/platform.rs:525`, `crates/gpui_macos/src/platform.rs:604`, `crates/gpui_linux/src/linux/platform.rs:339` | Restart-script spawn failure is log-only on all three backends: success path quits/posts-quit, failure path logs and keeps the old instance running, with no retry and no signal to the caller or user. | Medium | observed fact | port differently |
| 2.2 | `crates/gpui/src/http_client.rs:13-19` | `HttpClient::get` has no timeout, cancellation, or retry in the API; a stalled fetch stalls the awaiting task indistinguishably from a slow one. Callers must wrap with `Timer` themselves. | Low | observed fact | port differently |

**2.1 detail.** All three `restart()` implementations share the shape `match spawn { Ok(_) => quit, Err(e) => log::error!(...) }` and return `()`. A user-initiated restart that fails to spawn does nothing observable except a log line — the app keeps running the old instance with no error surfaced. Port should retry-or-surface (dialog, error return, or status callback); spec must define observable restart-failure behavior.

**2.2 detail.** The trait is `get(url, follow_redirects) -> BoxFuture<Result<HttpResponse>>` — no deadline, no abort handle, no retry policy; the default web backend leans on browser fetch (no timeout by default). Transient stalls are therefore silent and unbounded at this layer. Port should specify timeout + cancellation semantics on the HTTP surface.

| # | Location | Defect | Severity | Evidence Level | Action |
|---|---|---|---|---|---|
| | | | | | |

---

## Pass 6: Configuration and Environment Hazards

PENDING — block B1c not yet executed.

| # | Location | Defect | Severity | Evidence Level | Action |
|---|---|---|---|---|---|
| | | | | | |

---

## Summary

### Findings by Severity

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 0 |
| Medium | 3 |
| Low | 1 |
| **Total** | **4 (passes 1–2; pass 6 pending B1c)** |

### Findings by Pass

| Pass | Critical | High | Medium | Low | Total |
|------|----------|------|--------|-----|-------|
| 1. Logic and correctness | 0 | 0 | 2 | 0 | 2 |
| 2. Error handling | 0 | 0 | 1 | 1 | 2 |
| 6. Config and environment | — | — | — | — | pending (B1c) |

### Top Findings

1. Pass 1, `app.rs:1607` → Windows `platform.rs:536`: public hide-other-apps API panics on Windows; specify no-op-or-unsupported in port. Medium, port differently.
2. Pass 1, `key_dispatch.rs:100` + `window.rs:3795-3860`: frame-reuse index arithmetic debug-only enforced; port with checked arithmetic after protocols confirms the lifecycle invariant. Medium, port differently.
3. Pass 2, restart spawn failure log-only on all backends (win:525, mac:604, linux:339); no retry, no caller/user signal. Medium, port differently.
4. Pass 2, `http_client.rs:13-19`: no timeout/cancellation/retry in the HTTP API; stalls indistinguishable from slow. Low, port differently.

### Routed To Semantic Phase

None from B1a. (A frame-lifecycle invariant confirmation is routed to **protocols**, not semantic — recorded in the checkpoint and to be carried in the phase handoff at phase completion.)

---

## Runtime probes

None run during B1a (read-only investigation; probes optional per template). No probe currently required: 1.1 is code-evident, 1.2's invariant confirmation is routed to protocols analysis, not runtime.

| Probe | Finding | What it did | What it showed | Script |
|---|---|---|---|---|
| | | | | |

---

## Open Questions

None arising from pass-1 findings (both findings carry settled pre-porting actions; no `open question` / `external-behavior claim` evidence used).

| ID | Kind | Question | Why source cannot settle it | Derived findings |
|---|---|---|---|---|
| | | | | |

---

## Coverage and limits

- Inspected scope (B1a): `unimplemented!`/`unreachable!` sites repo-wide; `Platform::hide*` implementations per backend + `App` forwarding; `as`-cast conversions in `geometry.rs`; `unwrap()` sites in `app.rs` tab control + entity/global/downcast paths (reviewed, invariants hold); `rotation_scale` indexing (fixed `[[f32; 2]; 2]`, safe); `Bounds::intersects`/`contains` boundary semantics (correct half-open); `uniform_list::visible_range` + its consumer (event data only, benign); list `splice` arithmetic (valid-range API contract); `bounds_tree` ordering overflow (unreachable magnitude); `to_bytes` overflow (no realistic trigger); `reuse_subtree`/`truncate`/`refresh_node_id`/`pop_node`/`reuse_prepaint` index logic.
- Inspected scope (B1b): action-registry duplicate-name panic (intentional fail-fast, not filed); `Keystroke::parse` `Result` propagation (reviewed, no finding); `async_context`/`context` `.ok()` shutdown-tolerance sites (documented, justified); detached-task loops (`.log_err()` discipline + `detach_and_log_err` combinator exist); `MainThreadMarker::unwrap()` ×10 (all main-thread paths incl. main-queue-dispatched quit — dismissed); downcast/`update`/`windows.get_mut` unwraps (type/lifecycle invariants); arena chunk-exhaustion panic (single alloc path boxes small element structs — no realistic trigger); `SmokeDispatcher` expects (test-only); `app.rs` broadcast/filter `.ok()` sites (justified); SVG `parse_svg`/`render` `Result` propagation (positive pattern); element phase-order panics (intentional contract enforcement — noted for contracts B2a); `restart()` failure paths all backends; `HttpClient` trait surface.
- Skipped scope: gesture recognizer internals (header-level only); full `key_dispatch` matching algorithm; `taffy.rs` mapping arithmetic; text-system layout arithmetic — candidates for deeper passes if phase time permits, otherwise explicitly out of B1a.
- Evidence basis: source inspection.
- Known blind spots: reachability of the F1.2 violation path (requires frame-lifecycle analysis → routed to protocols); `editable_text` id-requirement intentionally panics (contract enforcement, not a defect — id requirement noted for contracts B2a).
- Coverage disposition: PARTIAL (passes 1–2 covered to their exit tests; pass 6 pending B1c by plan).

## Validation

<!-- Phase incomplete: B1c pending. Validation runs at phase completion. Criterion 1 already satisfiable (passes 1–2 produced findings); criteria 2–8 assessed then. -->

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | At least two of the three mechanical passes (1, 2, 6) produced findings or documented "no defects found." | PENDING | Passes 1–2: 4 findings. Pass 6: block B1c not executed. |
| 2 | Each finding has location, severity, evidence level, and recommended action. | PENDING | Holds for the 4 pass-1/2 findings; phase-level check at completion. |
| 3 | Findings are organized by pass and sorted by severity. | PENDING | As above. |
| 4 | Summary tables are complete and counts match the detailed findings. | PENDING | As above. |
| 5 | Findings are marked with evidence levels. | PENDING | As above. |
| 6 | Coverage and limits name inspected scope, skipped scope, evidence basis, and blind spots. | PENDING | B1a scope recorded; full section at completion. |
| 7 | Unsettled findings carry an unsettled action and each appears in the Open Questions table. | PENDING | No unsettled pass-1 findings; checked at completion. |
| 8 | Every quantitative specific cites the file and line or command output it was read from, or is marked as an estimate. | PENDING | Pass-1 citations present; checked at completion. |

**Validated by:** — (pending phase completion)
**Overall:** PENDING
