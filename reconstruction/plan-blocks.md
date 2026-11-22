# Block-by-Block Compatibility Check

Persisted copy of the compatibility assessment delivered in chat.
Verdict: the reconstruction plan is compatible with incremental block-by-block
execution, with the three adjustments in §4 (no pipeline or config change required).

State reference: `workflow/status.yaml` (`architecture → complete`, six phases pending).

Revision (refinement pass 1): B1a–B1c boundaries made explicit with a within-phase
routing rule; B2 rows reordered into execution order B2d→B2c→B2a→B2b→B2e→B2f
(IDs and dependencies unchanged); B7a expanded into executable spike plans;
block boundary protocol and §5 extended with early-failure-detection safeguards.
No pipeline, phase, or execution-state change.

---

## 1. What already supports block-by-block (evidence)

- **Hard gates per block:** completion refuses FAIL/MISSING validation (`VALIDATE.md`); a phase
  cannot close with unaddressed criteria. Every phase is therefore a closable block by construction.

- **Ordered dependencies:** `depends_on` chains (mechanical→…→semantic→porting→spec) mean a later
  block only consumes completed, validated outputs via `required_reads`. You cannot build on an
  unverified block.

- **Per-block state tracking:** `status.yaml` carries per-phase status, owner notes, outputs, open
  questions, and carry-forwards — the gap register lives in state, not in anyone's memory.

- **Gap-routing mechanism:** anything uncloseable in-block must become an `open_question` (terminal
  unknown) or `carry_forward` (named target block) or the phase cannot complete honestly. Silent
  deferral fails the gate.

- **Checkpoint convention:** `templates/phase-checkpoint.md` + `scratch/checkpoints/` exist for
  mid-block resumable state.

## 2. Where the plan was not yet block-ready

1. **Coarse blocks.** The roadmap assigned up to six subsystem areas to a single phase (e.g.
   contracts ← areas 3, 5, 6, 7, 9, 13) with no per-area done-criteria. A phase could validate PASS
   while an area stays thin — the "gap found after major work" scenario.

2. **contracts ∥ protocols parallelism.** Sharing an interface (protocols' state machines cite
   contracts' behavior) while running in parallel risks drift between the two; a gap would surface
   at semantic/porting time — late.

3. **Homeless corrections.** The 4 verified corrections had no owning block; they floated until
   post-pipeline consolidation. If consolidation is never explicitly scheduled, they stay stranded
   in the verification report.

4. **Unscheduled spikes.** The 3 open questions + 1 spike had no trigger point; "post-pipeline" is a
   parking lot, not a plan.

## 3. Pre-enumerated block list (everything planned from start)

Each block has fixed scope and an exit test. A gap can thereafter only mean
"a block failed its exit test" — caught at block exit, never at spec time.

| Block | Scope (gap-analysis areas) | Exit test |
|---|---|---|
| B0 architecture baseline | done | Validation PASS ✓, verification filed ✓, corrections logged ✓ |
| B1a mechanical: logic/correctness (defect pass 1) | pass 1 | IN: logic/correctness findings only. Exit: every finding has location/severity/evidence/action; coverage table complete; no error-handling/config findings investigated beyond recording + routing (see boundary rule) |
| B1b mechanical: error handling (defect pass 2) | 12 + pass 2 | IN: error paths, failure behavior, recovery. Exit: error taxonomy enumerated; every recovery path stated or UNRESOLVED-with-spike; checkpoint items assigned to B1b collected or explicitly deferred with destination |
| B1c mechanical: config/env (defect pass 6) | 10, 13 + pass 6 | IN: env vars, feature flags, config-dependent behavior. Exit: env/feature matrix complete; semantic sightings routed via phase-level `carry_forward` to defect-scan-semantic, none stranded; checkpoint clean |
B2 rows below are listed in execution order (highest risk/value first). IDs and dependencies are
unchanged. All B2 blocks complete before B3 begins (enforced: contracts phase gate + sequential
contracts→protocols).

| B2d contracts: animation/timing | 7 | Spring/easing evaluation + scheduling rules (highest value, least coverage) |
| B2c contracts: layout/measurement | 6 | Style→taffy mapping + measurement loop with acceptance cases |
| B2a contracts: elements/composition | 3 | Per-element trigger/defaults/outputs/side-effects + acceptance checks |
| B2b contracts: input/focus/keys | 5 | Dispatch-matching rules + focus model stated as testable contracts |
| B2e contracts: text behavior | 9 | Shaping/wrapping/hit-test observables + fallback rules |
| B2f contracts: supporting systems | 13 | Per-surface contracts (a11y, clipboard, images, gestures, popups, scroll, config) |
| B3a protocols: event catalog | 5, 10 | Complete event catalog, no unnamed variants (the 14-not-17 lesson) |
| B3b protocols: state machines | 2, 4, 5 | Window, focus, element-lifecycle, gesture machines; transitions cited to B2 contracts |
| B3c protocols: render + schedule pipelines | 8, 11 | Plan compilation stages, executor ordering guarantees |
| B3d protocols: text + backend flows | 9, 10 | Layout loop, per-OS event/window/IME flows, layer-shell roles |
| B4a semantic: concurrency/resources | 8, 11 | Each finding cites the protocol/contract ref it violates |
| B4b semantic: trust boundaries | 10, 13 | Boundaries + credential/clipboard flows assessed |
| B4c semantic: contract violations + carry-forward closure | all | All B1 carry-forwards resolved or explicitly re-routed |
| B5 porting synthesis | all | Every defect dispositioned (fix/port-differently/leave-behind/verify-at-runtime); Source Index complete with deep-read triggers |
| B6 reimplementation spec | all | Template criteria met; every slice proves a scenario; every scenario has a verification route |
| B7a runtime spikes (3 questions) | 2, 8 | Each question answered with observed evidence or formally UNRESOLVED with full 6-field accounting — see spike plans below |
| B7b corrections fold-in | verification §3 items 1–5 | The 4 corrections merged into the record they belong to |
| B7c guide consolidation (A–E) | all | One mechanism explained once; cross-references, no repeats |
| B7d final verification pass | all | Plan §10 completion criteria (a)–(f) checked off |

### B1 block boundary rule (within-phase routing)

All three B1 blocks write to the single phase output `mechanical-defects.md`
(pass-organized sections). A finding discovered outside the executing block's
scope is recorded under its owning pass section and logged in
`scratch/checkpoints/defect-scan-mechanical.md` with its owning block — it is
not investigated further in the current block, and no completed block is
reopened unless its exit test is invalidated (a stop-condition trigger, not
mere adjacent discovery). Framework `carry_forward` is reserved for
cross-phase routing: completion refuses same-phase (equal or earlier) targets,
so within-phase routing uses the checkpoint log. Each block's entry checklist
begins by collecting checkpoint items assigned to it.

### B7a — runtime spike plans (executable)

Scheduled after B3 (spikes consume B3c/B3d findings + B2 contracts as the
definition of correct behavior). Results feed B7c consolidation and B7d
verification. No spike may invent a conclusion: an unobservable question stays
UNRESOLVED with the 6-field accounting (see reconstruction plan §10).

**Q1 — headless-vs-screen pixel parity** (`q-headless-parity`).

1. Behavior to establish: whether headless/test renderer output is
   pixel-identical to on-screen presentation of the same app frame (oracle suitability).

2. Required evidence: same app + same frame driven in both modes; pixel diff of
   headless image output (`render_to_image`, `MetalHeadlessRenderer`,
   `WgpuHeadlessRenderer` — all in the existing record) vs captured screen frame,
   under deterministic input (seeded `TestApp`, fixed fonts).

3. Environments: macOS with GPU (Metal on-screen vs `MetalHeadlessRenderer`);
   Linux with GPU (wgpu on-screen vs `WgpuHeadlessRenderer`). Same machine, same build.

4. Procedure: drive a fixed frame of an existing sample app via
   `TestApp`/`simulate_next_frame`; capture the headless image; run on-screen
   and capture the screen frame; compare bytes with a pre-stated match threshold.

5. Success: byte-identical (or under-threshold) across N frames → headless usable
   as oracle. Failure: systematic divergence → headless is NOT an oracle; record
   divergence classes as INFERRED-at-best, never as parity.

6. Dependencies: B3c (render-plan/backend present understanding), B2 contracts
   (definition of a correct frame).

7. If unavailable (no GPU Mac/Linux box): remain UNRESOLVED — unknown: parity;
   why: no side-by-side run possible; evidence: headless paths exist in code but
   uncompared; impact: port cannot trust headless output as ground truth, so
   acceptance must use on-screen capture or spec-level assertions; blocking: no
   (spec records the limitation); future plan: run on GPU CI runners or hosted Mac.

**Q2 — GPU-less fallback behavior** (`q-gpu-fallback`).

1. Behavior to establish: per-platform outcome when no GPU device/surface exists
   (error, panic, software fallback) and what reaches the app.

2. Required evidence: observed launch outcome per OS — exit code, panic message,
   error value, or successful software-rendered frame.

3. Environments: Linux VM without GPU passthrough, Windows VM without GPU,
   macOS VM without Metal where obtainable; GPU-less CI runners. Note whether a
   software rasterizer (e.g. llvmpipe/SwiftShader) is present — that is a
   different condition from no-GPU-at-all and must be recorded, not conflated.

4. Procedure: run the minimal sample app (and the headless init path) with the
   GPU hidden; record outcome; repeat per platform; record whether the downlevel
   (WebGL2/GLES `rgba32uint`) path engages.

5. Success: a per-platform outcome table with observed evidence per cell.
   No observation → no conclusion.

6. Dependencies: B3d (backend init paths), B1b (error taxonomy gives candidate
   error values to look for).

7. If unavailable: remain UNRESOLVED with the same 6-field shape; impact: port
   init-failure handling stays implementation-defined with a verification hook;
   blocking: no; future plan: GPU-less cloud CI matrix.

**Q3 — per-platform frame pacing** (`q-frame-scheduling`).

1. Behavior to establish: what paces frames per platform (vsync/display-link
   callback, compositor frame event, timer) and the resulting timing guarantees.

2. Required evidence: observed frame-callback source + measured inter-frame
   interval distribution, idle and loaded, per platform.

3. Environments: macOS (display link), Linux Wayland + X11 under a compositor,
   Windows with DWM, web browser `requestAnimationFrame`. Real displays/GPUs.

4. Procedure: instrument a sample app frame counter with timestamps (tracing /
   profiler journals exist behind the `profiler` feature); record interval
   distributions idle + loaded; attribute the pacing source using B3d's platform
   findings (macOS `display_link` already established; others from B3d, confirmed
   behaviorally here — never asserted from code alone).

5. Success: per-platform pacing source + interval stats; B2d timing contracts
   validated or corrected.

6. Dependencies: B3d (platform loop knowledge), B2d (timing contracts under test).

7. If unavailable: remain UNRESOLVED; impact: animation timing specifiable only
   in frame counts, wall-clock behavior implementation-defined; blocking: no;
   future plan: on-device measurement pass.

## 4. The three adjustments (adopted into the plan)

1. **Sequentialize contracts → protocols.** Drop the parallel proposal. B3 blocks cite B2 contracts;
   executing B2 first makes interface drift impossible. No config change needed — the pipeline
   permits sequential execution; protocols simply is not started until contracts completes.

2. **Make B7b and B7a first-class blocks** with the exit tests above, instead of "post-pipeline"
   vagueness. Trigger: B7a spikes may run any time after B3 (their inputs are render-plan + sample
   app); B7b–B7d run after B6.

3. **Block boundary protocol (entry + exit).** Entry — before significant effort:
   confirm prerequisites are complete and sufficient; scope, inputs, and expected
   outputs understood; assumptions that could invalidate the block listed;
   existing findings to build on judged reliable (fix the unreliability first if
   not); tools and environment access confirmed; evidence standard for "done"
   defined; risk gate asked — invalidation risk? dependency risk? rework cost?
   verification cost? — with high-rework-cost, low-verification-cost checks
   first. Exit — the existing ritual (re-triage open-question labels, sweep new
   findings against earlier blocks for contradictions, confirm routed items
   landed) plus: stop-condition scan; every carry-forward has an explicit
   destination and completion condition; downstream inputs verified sufficient;
   execution order re-confirmed still appropriate. A block never passes a known
   critical issue downstream without an explicit, justified disposition. At each
   block exit (and on every phase completion): mirror new findings into
   `reconstruction/findings/` (and new reports into `reconstruction/`), then
   commit `reconstruction/` together with the framework record (`status.yaml`,
   closeouts, `THREAD_LOG.md`, `CONVENTIONS.md`, `DECISIONS.md`) incrementally
   with a message naming the block and its outcome; never push —
   pushing publishes the workspace and requires explicit user approval.

## 5. How late-gap discovery is prevented

- Pre-enumeration (§3 table) converts unknown-unknowns into block-exit failures.

- Risk is front-loaded: B1b/B1c (failure/config) run before any behavior work; B2d/B2c
  (animation/layout — thinnest coverage, highest user visibility) run first within contracts.

- Dependency direction is downward only: no block reads from an uncompleted block.

- The phase gates + carry-forward discipline make silent deferral a completion failure, not a
  judgment call.

- Progressive validation inside every block: state the question + expected
  evidence → investigate a limited representative slice → validate the
  interpretation against callers, tests, and invariants → check contradictions
  and missing dependencies → expand only then. Intermediate state lives in the
  phase checkpoint, not in new documents.

- Stop conditions (stop and reassess immediately, never continue merely to
  satisfy schedule): a foundational assumption is disproved; a required
  dependency or contract is missing; source behavior contradicts an earlier
  finding; the method cannot produce the required evidence; scope is expanding
  beyond the block; downstream would inherit unresolved ambiguity; continuing
  risks substantial rework.

- Completion standard: a block is complete when its exit test is demonstrated
  by evidence, not when its activities were performed. Insufficient evidence →
  stop or formally carry forward. No unverified assumption enters the record
  disguised as established fact.
