# GPUI-CE Reconstruction — Complete Project Plan

Persisted copy of the plan delivered in chat and approved for verification.
Source: planning session; pipeline configured but no phase executed.
Status reference: `workflow/status.yaml` (`architecture → complete`, six phases pending).

Revision (refinement pass 1): §6 corrected to sequential contracts→protocols with
B2 execution order B2d→B2c→B2a→B2b→B2e→B2f; §10 extended with the
requirement/choice/unresolved classification standard and UNRESOLVED accounting;
§11 points to the execution protocol in `plan-blocks.md`. Block detail
(B1 boundaries, B2 order, B7a spike plans) lives authoritatively in
`plan-blocks.md` and is referenced, not duplicated, here.

---

## 1. Existing work and verified baseline

| Artifact | State |
|---|---|
| `findings/architecture/architecture-map.md` (+ validation PASS) | Complete; 24-crate layer map, dependency direction, lifecycle, concurrency, porting priorities |
| 5 secondary outputs (public-surfaces, runtime-lifecycle, state-and-storage, build-and-deploy, config-model) | Complete; catalog-level detail |
| `findings/verification/architecture-check.md` | Complete; overall verdict: trustworthy structure, 4 corrections filed |
| `status.yaml` | `architecture: complete`; 3 open questions (`q-headless-parity`, `q-gpu-fallback`, `q-frame-scheduling`), 1 post-pipeline spike (`post-frame-capture`) |
| `DECISIONS.md` | D001 (local stdio client for framework ops), D002 (pipeline field verified-not-edited) |

**Corrections verified against report + source:** PlatformInput = 14 variants (`interactive.rs:771-800`); Platform trait = 74 methods (`platform.rs:151-386`, remainder belong to `PlatformDisplay` et al.); `ApplicationHandle::update` is a main-thread `Rc` borrow, cross-thread path is `AsyncApp` (`app.rs:204-215`); executor pool spawns plain OS threads (`scheduler.rs:200`, `wasm_thread` on wasm). The findings files themselves were intentionally left unedited per planning boundaries, so the corrections live in the verification report until a consolidation step folds them in.

## 2. Pipelines evaluated

| Pipeline | Phases | Verdict |
|---|---|---|
| `architecture-only` (was active) | 1 | Complete; insufficient — no behavior/spec coverage |
| `lite` | arch→contracts→protocols | Rejected — no porting bundle, no spec, no failure analysis |
| `defect-scan` | arch→defect | Rejected — maintenance audit, no reconstruction chain |
| `full` | arch→contracts→protocols→porting→spec | Rejected — no defect/failure-behavior mechanism, which the scope explicitly requires |
| `full-with-audit` | full + single defect-scan after arch | Rejected — one combined scan judges concurrency/API-contract issues without contracts/protocols context; saves one phase at the cost of the findings that most change a port |
| **`full-with-deep-audit`** | arch→mech-defects→contracts→protocols→semantic-defects→porting→spec | **Selected** — mechanical pass feeds contracts; semantic pass (concurrency, resources, API violations) runs with full protocol context; both synthesize into porting + spec |
| `scout-first` | deep-audit + broadside-scout brief | Rejected — no Broad-Side run exists (costs real OpenRouter money), and the completed architecture map already steers phases; without a run it degrades to deep-audit anyway |
| `synthesis` | vision→propose→merge→finalize | Rejected — forward-plans new products; explicitly not for repo analysis |

## 3. Selected pipeline and justification

**`workflow/pipeline-full-with-deep-audit.yaml`** (the framework default). It is the only variant covering all eight required capabilities: subsystem analysis (architecture ✓ done), mechanism investigation + call-path tracing (contracts acceptance checks + protocols state machines), state/lifecycle/concurrency (protocols + semantic pass 3), interfaces/contracts (contracts + semantic pass 5), runtime/platform behavior (protocols + mechanical pass 6 config/env), evidence collection (validation gates per phase), and final documentation (porting bundle → reimplementation-spec). Overlap is minimal: each phase has distinct completion criteria and consumes the prior phase's output as required reading.

## 4. YAML configuration changes and validation result

- **Change (sole permitted modification, applied via framework tool, not hand-edit):** `codecarto_switch_pipeline` with `pipeline: workflow/pipeline-full-with-deep-audit.yaml`.
- **Tool result:** `Switched pipeline: full-with-deep-audit. Phases preserved (completed): architecture. New phases: defect-scan-mechanical, contracts, protocols, defect-scan-semantic, porting, reimplementation-spec. Current phase: defect-scan-mechanical.`
- **Validation:** `codecarto_status` confirms `Pipeline: full-with-deep-audit, Progress: 1/7 complete`, 3 open questions carried, 1 post-pipeline item carried. Status block verified: `architecture → complete`, all six new phases → `pending`. No unfinished phase marked complete; completed work and all findings preserved on disk; no source touched.

## 5. Gap analysis (against the 13 subsystem areas)

| # | Area | Status | What's missing |
|---|---|---|---|
| 1 | Architecture & dependencies | VERIFIED | — (reuse map; fold 4 corrections at consolidation) |
| 2 | App/window/runtime lifecycle | VERIFIED core | Frame pacing per platform, GPU-fallback behavior (open questions; runtime spikes) |
| 3 | Elements, composition, component model | INCOMPLETE | Layout negotiation order, deferred-layer content masks, hit-test algorithm, focus scopes, `use_state` identity rules, `Entity::cached` invalidation |
| 4 | State, identity, notifications | PARTIAL | Observer dispatch order, effect-flush interleavings, release-listener edge cases, `clear_accessed` tracking semantics |
| 5 | Input, dispatch, focus, keybindings | PARTIAL | Keystroke-resolution algorithm, key-context tree matching, focus model, gesture recognizers (tap/pan/pinch mapping) |
| 6 | Layout & measurement | INCOMPLETE | `Style`→taffy mapping, `AvailableSpace` semantics, inline layout, text-measurement fallback loop |
| 7 | Animation, interpolation, springs | INCOMPLETE | Oscillator integration, `Motion`/easing evaluation, transition scheduling vs frame clock (verification gap #1 — highest behavioral value) |
| 8 | Scene & GPU rendering | PARTIAL | Render-plan compilation, atlas management/eviction, `Surface`/custom-GPU path, downlevel (WebGL2) path, per-backend present logic |
| 9 | Text shaping & glyphs | PARTIAL | Shaping/wrapping/hit-test algorithms, font-fallback chains, native-vs-Swash routing per platform |
| 10 | Platform backends | PARTIAL | Per-OS event loops, window management, IME, clipboard/credential flows, layer-shell roles |
| 11 | Executors & concurrency | PARTIAL | Scheduling order guarantees, `spawn_dedicated` semantics, wasm-threading constraints, timer precision |
| 12 | Ownership, cleanup, failure recovery | INCOMPLETE | Per-subsystem drop order, GPU-recovery paths, error taxonomy (mechanical pass 2 feeds this) |
| 13 | Supporting systems (a11y, clipboard, images, gestures, popups, scroll, config) | PARTIAL inventory | Behavioral contracts for each (covered as contracts-phase surface types) |

## 6. Ordered investigation roadmap and dependencies

Respects pipeline order. Contracts runs first, protocols second (sequential:
B3 blocks cite B2 contracts, so parallel execution would risk interface drift;
the pipeline permits sequential execution and the block plan mandates it):

1. **defect-scan-mechanical** (next eligible; do not start until approved): passes 1 (logic/correctness), 2 (error handling → feeds area 12), 6 (config/env → feeds areas 10, 13). Route semantic sightings forward to `defect-scan-semantic` via `carry_forward`. Internal execution blocks B1a→B1b→B1c with explicit boundaries (see `plan-blocks.md` §3).
2. **contracts**: takes areas 3, 5, 6, 7, 9, 13 as feature contracts with defaults/side effects/acceptance checks. Internal execution order (risk/value first): B2d animation/timing → B2c layout/measurement → B2a elements/composition → B2b input/focus/keys → B2e text behavior → B2f supporting systems. All B2 blocks finish before protocols begins.
3. **protocols** (after contracts completes): takes areas 2, 4, 5, 8, 10, 11 as event catalogs and state machines (element lifecycle, focus machine, render-plan pipeline, executor scheduling, text layout loop).
3. **defect-scan-semantic**: pass 3 (concurrency/resources → areas 8, 11), pass 4 (trust boundaries), pass 5 (API-contract violations, citing contracts/protocols refs). Resolves mechanical carry-forwards.
4. **porting**: synthesize all findings into the bundle; defect dispositions (`fix before porting / port differently / leave behind / verify at runtime`); Source Index as the compression boundary for the guides step.
5. **reimplementation-spec**: language-agnostic default (matches the language-independent goal; confirm at the Strategic Alignment Hook rather than assuming). Designs around or leaves behind every defect finding with citation.

## 7. Mapping of phases to investigations and final guides

B2 internal execution order: B2d→B2c→B2a→B2b→B2e→B2f (see `plan-blocks.md` §3);
all B2 blocks finish before protocols begins.

| Phase | Investigations (§5 areas) | Primary consumer guide |
|---|---|---|
| defect-scan-mechanical | 12 (error paths), 10/13 (env/config), logic hazards everywhere | Guide E (failure behavior), Guide D (config) |
| contracts | 3, 5, 6, 7, 9, 13 | Guides B (interaction/state), C (layout/render), D (text/resources) |
| protocols | 2, 4, 5, 8, 10, 11 | Guides B, C, D |
| defect-scan-semantic | 8, 11 (concurrency/resources), trust + contract violations | Guides C, D, E |
| porting | synthesis + dispositions + Source Index | Scaffolds all guides; index for deep-read triggers |
| reimplementation-spec | acceptance scenarios, slices, verification routes | Guide E + acceptance backbone for all guides |

## 8. Supplementary work not covered by the pipeline

- **Guide consolidation** (post-pipeline): fold the 6 architecture outputs + verification corrections + 6 phase outputs into the 5-guide structure; resolve the 4 corrected claims into the text (they currently live only in the verification report).
- **Runtime spikes** (post-pipeline `spike` entries, not phases): `post-frame-capture` (headless-vs-screen parity), GPU-less fallback probe, per-platform frame-pacing observation — required to close `q-headless-parity`, `q-gpu-fallback`, `q-frame-scheduling`. These need OS/GPU matrix access, not just reading.
- **Strategic Alignment Hook**: confirm language-agnostic spec at the `reimplementation-spec` boundary (the brief already implies it; record explicitly so an auto-run never has to guess).

## 9. Final guide structure

- **A. System Architecture** — layers, dependency direction, crate responsibilities, build/packaging, configuration model. (Mostly written; needs corrections folded in.)
- **B. Runtime, Interaction & State** — boot, frame, events, focus/key dispatch, entity/observer model, animation timing, executor scheduling, cleanup order.
- **C. Layout & Rendering** — style resolution, taffy mapping, measurement loop, scene primitives, render-plan compilation, atlas/surface management, backend present paths.
- **D. Text, Platform & Resources** — shaping/wrapping/hit-testing, font fallback + raster routing, per-OS backends, a11y, clipboard/credentials, images, config/env.
- **E. Implementation Spec & Verification** — porting dispositions, module build order, acceptance scenarios with verification routes, invariant/failure catalog, unresolved questions with spike plans.
- Rules: one mechanism explained once (cross-reference, don't repeat); pseudocode/equations where precision demands (spring integration, layout negotiation, dispatch matching); no source dumps, no per-file documents.

## 10. Verification strategy and completion criteria

- Classify every load-bearing statement **VERIFIED** (source-cited or behavior-reproduced) / **INFERRED** (strong support, indirect) / **UNRESOLVED** (insufficient evidence, carries a spike plan) / **NOT APPLICABLE** (target-irrelevant). Mapping from framework tags: `observed fact`→VERIFIED, `strong inference`→INFERRED, `open question`/`external-behavior claim`→UNRESOLVED.
- Phase gates remain the framework's (validation PASS required; PARTIAL rows name tracking IDs).
- **Measurable completion criteria:** (a) every guide section cites source paths; (b) every mechanism states inputs, outputs, ordering, invariants, and failure behavior; (c) every reimplementation-spec scenario traces to a contract/protocol finding; (d) every defect finding is dispositioned with citation; (e) UNRESOLVED list is empty or each item has a funded spike; (f) an independent engineer can implement areas 2–11 without reading Rust — tested by having each guide reviewed against its source area for contradictions and missing dependencies.

### Classification standard (refined)

Every load-bearing statement in the final guides carries exactly one label:

- **Reconstruction requirement** — behavior an independent implementation must
  reproduce (observable semantics, ordering, invariants, failure behavior).
- **Implementation choice** — detail that may legitimately differ in another
  language or architecture (e.g. thread-pool sizing, hash function, arena
  strategy, GPU backend selection), provided the observable contract holds.
- **UNRESOLVED** — detail available evidence cannot establish. Permitted only
  with all six fields: (1) what is unknown; (2) why it remains unknown;
  (3) available evidence and its limitations; (4) impact on reconstruction;
  (5) whether it blocks implementation (blocking/non-blocking verdict);
  (6) concrete verification method or future investigation plan.

Mapping: VERIFIED findings are sorted into requirements vs choices at B7c
consolidation; INFERRED findings are either promoted with evidence or
downgraded to UNRESOLVED — never left ambiguous. Measurable checks:
(g) zero unlabeled load-bearing statements; (h) every UNRESOLVED item carries
all six fields plus its blocking verdict; (i) zero blocking UNRESOLVED without
an approved spike plan. This strengthens, not weakens, the evidence bar:
uncertainty must be fully documented to be acceptable.

## 11. Token/effort optimization and major risks

- **Optimization:** reuse all required-read findings (pipeline enforces this); trace call paths instead of reading whole files (e.g. `draw()`→roots→layout→paint rather than all 9.7K lines of `window.rs`); run contracts+protocols in parallel; delegate bulk extraction (file inventories, enum catalogs) to subagents and cite their scratch notes; checkpoint long phases; no re-read of mapped areas; optional systems (media, tokio bridge, inspector, perf tooling) stay deferred. *(Parallel-contracts note superseded by `plan-blocks.md` adjustment 1: sequential contracts→protocols.)*
- **Risks:** (1) Subagent delegation failed last run (provider usage limits) — plan assumes inline execution with targeted reads; if limits persist, phases take more sessions. (2) 217K LOC context budget — mitigated by the porting bundle as compression boundary; spec phase must not reload all upstream reports. (3) Runtime spikes need a multi-OS/GPU matrix we may not have — worst case, affected behaviors stay UNRESOLVED with explicit spike plans rather than blocking the spec. (4) Scope creep into per-backend internals — contained by porting priorities (one full backend + headless path is core; the rest is important/optional).
- **Execution protocol:** the operative early-failure-detection rules (validate-before-investing entry checks, progressive validation loop, stop conditions, boundary anti-propagation, risk gate, completion standard) live authoritatively in `plan-blocks.md` §§4–5 and apply to every block; they are referenced here, not duplicated.
