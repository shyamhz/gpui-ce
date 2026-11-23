# B7d — Final reconstruction verification

**Disposition: complete with limits.** The language-independent guides and
acceptance plan are ready for a scoped implementation. All seven framework
phases are complete. This is not independent implementation sign-off,
exhaustive parity verification, or a claim that all reference tests pass.
No GPUI source was changed.

## Exit checks against plan §10

| Check | Result | Evidence or limit |
|---|---|---|
| (a) Guide sections cite source paths | PASS | Every main section in [A–E](../README.md#reimplementation-guides) has an Evidence block; the sweep checked 77 local links and 59 distinct source paths. |
| (b) Mechanisms state inputs, outputs, ordering, invariants and failure behavior | PASS for the scoped core and named adapter boundaries | The source walk-through below checked the critical handoffs. Exact host internals and exhaustive error paths are not established. |
| (c) Acceptance scenarios trace to contracts, protocols or a cited audit disposition | PASS | All 36 scenarios in the [spec](../findings/reimplementation-spec.md#acceptance-scenarios) have a named trace; all are owned by the 10-slice graph, with a verification route. The slices are not executed acceptance tests. |
| (d) Every defect has a cited disposition | PASS | Five mechanical and six semantic IDs match the [porting bundle](../findings/reverse-engineering-bundle.md#defect-synthesis) and [spec design choices](../findings/reimplementation-spec.md#design-consequences-for-audited-defects). The range invariant is not asserted to be a reproduced fault. |
| (e) Unresolved work has concrete, funded verification | PARTIAL | The [three original spikes](runtime-spikes.md#question-ledger) and the font follow-up below have procedures and blocking verdicts. No funding or cross-platform test access was established in this block. |
| (f) Areas 2–11 can be independently implemented from the guides | PARTIAL | Cross-checked the guides against the relevant source and findings, including missing dependencies below. No independent engineer implemented or signed off on the whole surface; renderer/provider fidelity and host details are not exhaustive. |
| (g–i) Classification and unresolved accounting | PASS for the guide scope | Required behavior, port choices and unresolved findings are separated. Ledgers give all six fields. None of the open questions blocks the core; each limits a named parity claim. |

## Guide-to-source walk-through

This was a source cross-check, not a claim to have executed every path.
Limited runtime observations were checked against their measurement points.

| Area | Verified boundary | Qualification |
|---|---|---|
| 2. App/window lifetime | `crates/gpui/src/app.rs:1558-1592,2235-2285`: first draw precedes handle return; failed open rolls back; removal cleans associations before observers. | Published frame is not presented output. |
| 3. Elements/composition | `crates/gpui/src/element.rs:579-605,825-950`, `crates/gpui/src/window.rs:3650-3863,4222-4300`: ordered traversal, deferred work and state reuse by identity. | Frame-index checking is a defensive port choice; not a new defect reproduction. |
| 4. State/notifications | `crates/gpui/src/app.rs:1264-1283,1344-1369,2013-2075`, `crates/gpui/src/app/entity_map.rs:164-190`, `crates/gpui/src/view.rs:539-557`: outer effect drain and draw-scoped dependency tracking. | B now distinguishes resetting a trace from releasing identity or subscriptions. No panic recovery guarantee. |
| 5. Input/focus | `crates/gpui/src/window.rs:798-854,979-985,6088-6188,6577-6610`, `crates/gpui/src/key_dispatch.rs:480-560`: separate hover and scroll reachability; longest-prefix replay; taps emit mouse events. | B and C now cover prefix reprocessing and per-hitbox masks/fragments. No raw pinch recognition promise. |
| 6. Layout | `crates/gpui/src/taffy.rs:133-200,630-696,749-935`: tagged constraints, edge snapping and auto-axis paired padding. | C includes the padding exception; the complete style/backend combination matrix is not a verified portable oracle. |
| 7. Motion | `crates/gpui/src/motion.rs:647-738`, `crates/gpui/src/spring.rs:5-170`: elapsed-time passes, endpoint behavior, spring branches and tolerance. | Source tests exercise samples, not real display cadence. |
| 8. Rendering | `crates/gpui/src/scene/plan.rs:67-146`, `crates/gpui_wgpu/src/wgpu_atlas.rs:98-117,162-179`, `crates/gpui_wgpu/src/wgpu_renderer/platform.rs:124-182`: filter pairing, scene-scoped commands, atlas invalidation and surface reactions. | C distinguishes imported surface ownership and unmatched filter handling. Full shader/downlevel/driver and recovery behavior is not established. |
| 9. Text | `crates/gpui_ce_parley/src/text_system.rs:1503-1516,1634-1750,2059-2076,2780-2814`, `crates/gpui/src/input.rs:7-32`: catalog change, paragraph breaks, clamp and editing indices. | Hard breaks survive the soft clamp. See the font-catalog result below before using host metrics as an oracle. |
| 10. Host adapters | `crates/gpui/src/platform.rs:107-135`, `crates/gpui_linux/src/linux/wayland/client.rs:1644-1666,2043-2109`, `crates/gpui_web/src/events.rs:1108-1154`: selector, popup/IME handoffs. | Platform-specific sequencing and permission outcomes need matching native environments. |
| 11. Tasks | `crates/gpui/src/platform_scheduler.rs:109-170`, `crates/gpui_scheduler/src/scheduler.rs:139-208`, `crates/gpui/src/queue.rs:315-357`: affinity, dedicated session lifetime and lane dequeue. | Dequeue is not completion order; timer targets are not observed wake deadlines. |

## Reference tests executed

Built the locked `gpui-ce` library test harness with Rust 1.95.0,
`wayland,x11,test-support`, and forced headless execution (`ZED_HEADLESS=1`,
`SEED=0`, display selectors removed for the tests). These were selected
reference unit tests, not tests of a port:

| Filter | Passed | Failed |
|---|---:|---:|
| `motion::` | 20 | 0 |
| `spring::` | 11 | 0 |
| `gestures::` | 36 | 0 |
| `keymap::` | 33 | 0 |
| `key_dispatch::` | 7 | 0 |
| `scene::` | 8 | 0 |
| `taffy::` | 6 | 0 |
| `hit_test_preserves_inline_regions_occlusion_and_metadata` | 1 | 0 |
| **Selected core total** | **122** | **0** |

The `gpui_ce_parley` library suite with `test-support` and default
`system-fonts` ran separately: **41 passed, 1 failed** under the host font
catalog. An isolated rerun reproduced the failure. Running the same
binary with a temporary Fontconfig configuration pointing to an empty
font directory (`fc-list`: zero entries for that configuration) gave
**42 passed, 0 failed**. This is bounded evidence from two catalog
conditions, not a root-cause analysis or a claim of a fix.

## Font catalog follow-up

**Observed result.** The reference test
`text_system::tests::loading_system_fonts_preserves_registered_faces_and_invalidates_layouts`
passed its assertions for cache invalidation, canonical font ID, first
paint fragment font ID and width before failing ascent equality:
`18.449999px` before loading system fonts versus `19.241999px` afterward
(`crates/gpui_ce_parley/src/text_system.rs:2780-2814`, assertion at 2810).
Later assertions did not run in that failing attempt. The change affected
the metric under one catalog; a stable ID does not establish stable metrics.

| Accounting field | Follow-up (`b7d-font-catalog-metrics`, local audit ID) |
|---|---|
| What remains unknown | Which catalog entries, shaping choices or metric aggregation account for the ascent change, and on which hosts it occurs. |
| Why unresolved | The assertion reports the metric difference, not the selected face/variation for every run or the metric contribution of each fragment. |
| Available evidence and limits | Repeated on one Linux default catalog; not reproduced with the same binary and empty Fontconfig configuration. The catalog dependency is observed; its mechanism is not. |
| Reconstruction impact | Use fixed catalog fixtures for metric comparisons. Keep catalog invalidation and face identity separate from metric invariance after enrichment. |
| Blocking verdict | Non-blocking for core and fixed-catalog shaping; blocks generalizing stable metrics across system-font loading. |
| Verification method | Compare empty and populated pinned catalogs while recording all fragment face identities/variations and metrics before/after enrichment; reduce the populated set and repeat on supported targets. |

The original three framework runtime questions remain open. This follow-up
is tracked here, not added by editing framework state after completion.
No unresolved result was promoted to a port requirement or declared fixed.
