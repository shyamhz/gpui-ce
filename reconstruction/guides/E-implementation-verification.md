# E. Implementation Spec & Verification

Use the [language-independent specification](../findings/reimplementation-spec.md)
as the build contract and the [porting bundle](../findings/reverse-engineering-bundle.md)
as the source index. This guide owns scope and evidence routing, not a second
copy of the implementation or test tables.

## Build order and acceptance

**Implementation choice.** Start with a test embedding and controlled time.
Follow the [slice dependency table](../findings/reimplementation-spec.md#slices):

| Tier | Deliverable | Evidence expected |
|---|---|---|
| Minimum viable | Window/update lifecycle, layout and frame publication, focus/input | SL-01–SL-04: deterministic host and scene fixtures. |
| Major workflows | Gestures, motion, text/IME exchange, resources, accessibility, executor lifecycle | SL-05–SL-09: injected events, clock, fixed font/raster/error fixtures and task ownership tests. |
| Full-parity track | Target-specific role/service and fault semantics | SL-10: controlled adapter results first. Host comparisons remain separate; this slice is not proof of full native parity. |

**Reconstruction requirement — acceptance gate.** Each slice must show its
named observable outcomes in the [acceptance table](../findings/reimplementation-spec.md#acceptance-scenarios).
Do not accept a slice from a build, an API shape, or a callback count alone.
The 36 scenario IDs and 10 slice IDs are the plan, not a claim that a port or
test suite has been implemented. Use [B](B-runtime-interaction-state.md) for
ordering and [C](C-layout-rendering.md) and [D](D-text-platform-resources.md)
for content and boundary expectations.

**Evidence:** specification and [bundle addressability](../findings/reverse-engineering-bundle.md#agent-addressability);
the reference programmatic seams include
`crates/gpui/src/app/test_app.rs:221-301,597-795` and
`crates/gpui/src/window.rs:2712-2719,2785-2807,7203-7286`.

## Defect dispositions

**Implementation choice.** Use the spec's
[defect-to-proof table](../findings/reimplementation-spec.md#design-consequences-for-audited-defects)
for all 11 dispositions. These are intentional port departures or defensive
choices, not implemented GPUI fixes. Use this index to locate the relevant
failure boundary:

| Boundary | Audit coverage | Verification route |
|---|---|---|
| Frame ranges and gesture carrier | M1.2, D5.1 | S-08, S-12; [B](B-runtime-interaction-state.md#raw-touch) / [C](C-layout-rendering.md#element-phases-state-and-scroll). |
| Task closure | D3.1 | S-27; [B](B-runtime-interaction-state.md#frame-demand-and-task-lifetime). |
| Text precondition | D5.2 | S-25; [D](D-text-platform-resources.md#shaping-caret-and-raster). |
| Host/transport failure, configuration and secret ownership | M1.1, M2.1, M2.2, M6.1, D4.1, D4.2, D5.3 | S-31–S-35; [D](D-text-platform-resources.md#assets-accessibility-and-host-owned-data). |

**Evidence:** [mechanical scan](../findings/mechanical-defects.md),
[semantic scan](../findings/semantic-defects.md) and [bundle dispositions](../findings/reverse-engineering-bundle.md#defect-synthesis);
example source boundaries are `crates/gpui/src/window.rs:3795-3860`,
`crates/gpui/src/queue.rs:80-92,156-161`,
`crates/gpui/src/text_system/window_text_system.rs:37-56`,
and `crates/gpui/src/platform.rs:339-348`.

## Unresolved runtime behavior

Each item below is **UNRESOLVED**. The
[B7a question ledger](../verification/runtime-spikes.md#question-ledger) is
the six-field record (unknown, reason, bounded evidence, impact, blocking
verdict and verification method). The three spikes are tracked in CodeCartographer
and use the [approved procedures](../plan-blocks.md#b7a--runtime-spike-plans-executable).
Completion of the framework phases does not close these questions.

| ID | Decision not yet supported |
|---|---|
| `q-headless-parity` | One matched Linux X11 drawable fixture is not a general offscreen pixel oracle. |
| `q-gpu-fallback` | Linux fault injection and software offscreen success do not establish portable fallback behavior. |
| `q-frame-scheduling` | Application callback timings do not establish delivered cadence. |

**Evidence:** [runtime observations and fixture](../verification/runtime-spikes.md);
`crates/gpui_wgpu/src/wgpu_renderer/headless.rs:147-230`,
`crates/gpui_wgpu/src/wgpu_renderer/platform.rs:124-182`,
`crates/gpui/src/window.rs:1758-1897,2682-2713`. None blocks the core build;
each blocks its corresponding parity claim.
