# Behavioral Contracts

## Surfaces Covered

GPUI-CE is a Rust library (API/SDK surface). No CLI, TUI, or bot surfaces exist.
Contracts below are written against the public Rust API so a reimplementation
in another language can honor the observable behavior without reading Rust.

B2d scope (this revision): animation and timing contracts only. Contracts for
elements/composition (B2a), input/focus/keys (B2b), layout/measurement (B2c),
text (B2e), and supporting systems (B2f) follow in later blocks; their
sections are marked PENDING, not absent.

## Feature Contracts

### API/SDK — animation and timing (B2d)

#### C1 Duration motion evaluation

| Field | Value |
|---|---|
| **Feature** | `Motion` (duration-based) evaluation |
| **Trigger or input** | `Motion::sample(elapsed)` / `sample_at(started_at, now)` with elapsed wall/framework time |
| **Defaults** | `Motion::default()` is a zero-duration motion; `Easing::default()` is linear; delay defaults to zero |
| **Observable output** | `MotionSample { progress (eased, may overshoot 0..1), local_time, iteration (u128), direction, phase (Delayed/Playing/Completed/Inactive), is_active }` |
| **Side effects** | None — evaluation is a pure function of elapsed time (`observed fact`: `motion.rs:652-743`) |
| **Persisted state** | None at this layer (callers hold `started_at`) |
| **Error behavior** | No errors; zero-duration passes and empty cycles resolve to `Inactive`/`Completed`, never panic |
| **Retry or recovery behavior** | N/A (pure computation) |
| **Owner (layer/package)** | `gpui` core (`motion.rs`) |
| **Evidence** | Observed fact: `MotionSample` fields and lifecycle (`motion.rs:227-300`); `sample_at` = `sample(now - started_at)` (`motion.rs:724-729`); `checked_extent` overflow-safe (`motion.rs:541-553`) |

#### C2 Spring motion evaluation

| Field | Value |
|---|---|
| **Feature** | Damped-harmonic-oscillator spring integration |
| **Trigger or input** | `SpringConfig::step` (fixed target) / `step_ramp` (constant-velocity target) per frame with `delta_time`; or `Motion::spring(config)` sampled like C1 |
| **Defaults** | Settle epsilon default (`DEFAULT_SPRING_EPSILON`); `is_settled` tests position within epsilon AND velocity within `epsilon * natural_frequency` |
| **Observable output** | New `(position, velocity)`; analytic propagator exact for the step (under/critical/over-damped branches selected by damping ratio vs 1.0 ± 1e-4) |
| **Side effects** | None — pure function of `(state, target, dt)`; retargeting preserves velocity without restarting |
| **Persisted state** | Caller-held `SpringState`; settling springs report iteration zero and nominal forward direction |
| **Error behavior** | No errors; an undamped spring has no finite settling time (`settle_time` returns `Duration::MAX`) |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`spring.rs`) |
| **Evidence** | Observed fact: `step`/`step_ramp`/`propagator`/`is_settled`/`settle_time` (`spring.rs:27-170`) |

#### C3 Transition handle (`use_transition` / `use_keyed_transition`)

| Field | Value |
|---|---|
| **Feature** | Element-scoped animated value with per-frame evaluation |
| **Trigger or input** | `window.use_transition(cx, motion, init)` (caller-location state) or `use_keyed_transition(key, …)` (keyed state); `Transition::evaluate(window, cx)` read during render |
| **Defaults** | Continuous retargeting (continue from current value); per-frame result cached |
| **Observable output** | Interpolated value; while active, evaluation requests the next animation frame (frame pumping until settle/complete) |
| **Side effects** | Frame scheduling (`request_animation_frame` while `is_active`); state keyed by caller location or explicit key |
| **Persisted state** | `TransitionState` entity (survives across frames while the call site/key is stable) |
| **Error behavior** | Sampling uses wall-clock `Instant::now()` at read time; a sample always contains a value (internal invariant) |
| **Retry or recovery behavior** | N/A (frames re-requested automatically while active) |
| **Owner (layer/package)** | `gpui` core (`transition.rs`, `window.rs:4381-4425`) |
| **Evidence** | Observed fact: `evaluate` samples + pumps frames (`transition.rs:108-144`); state hooks (`window.rs:4381-4425`) |

#### C4 Retarget continuity

| Field | Value |
|---|---|
| **Feature** | Mid-flight goal changes |
| **Trigger or input** | Goal update with a new target value (and/or new motion) |
| **Defaults** | Continuous: sample current presentation, restart the run from it (no visual jump; spring velocity preserved) |
| **Observable output** | `restart` variant restarts from the initial value instead (`Animated::restart`); `jump_to` snaps immediately and clears run state; `adopt_completed_target` aligns END presentation with the logical target so a later retarget does not jump |
| **Side effects** | Run restart (new `started_at`); `reset` restores initial value |
| **Persisted state** | `last_value`, `settled_progress`, `started_at` in `Animated` |
| **Error behavior** | None (goal equality short-circuits: no new run when value unchanged) |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`animated.rs:82-144`) |
| **Evidence** | Observed fact: `set`/`restart`/`jump_to`/`adopt_completed_target` (`animated.rs:82-144`) |

#### C5 Animation element playlist

| Field | Value |
|---|---|
| **Feature** | Declarative `Animation` element (sequential motion playlist) |
| **Trigger or input** | `Animation::new(motion)` + `.repeat()` / `.repeat_synced()` / `.with_easing()` / `.with_max_fps()`; playlist advances when the current motion's sample goes inactive |
| **Defaults** | Unsynced (elapsed measured from playlist start); `repeat` restarts the playlist; `repeat_synced` anchors elapsed time to the shared App epoch so animations on different elements advance in lockstep |
| **Observable output** | Animator closure receives `(element, animation_ix, delta)` per frame; `max_fps` throttles via timer + delayed frame |
| **Side effects** | Frame scheduling while any playlist item is active; `reduce_motion` jumps to the resting progress of the LAST animation and marks done |
| **Persisted state** | `AnimationState { start, animation_ix }` per element |
| **Error behavior** | `debug_assert` on finite delta (non-finite values are a bug, caught in debug) |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`elements/animation.rs`) |
| **Evidence** | Observed fact: playlist advance, synced/unsynced elapsed, max_fps throttle, reduce_motion jump (`elements/animation.rs:380-440`); epoch init (`app.rs:919,952`) |

#### C6 Global reduce-motion

| Field | Value |
|---|---|
| **Feature** | `App::reduce_motion` / `set_reduce_motion` accessibility override |
| **Trigger or input** | App-level setter; honored by transitions (jump to endpoint) and `Animation` elements (jump to resting progress, done) |
| **Defaults** | Off (`false` at App creation) |
| **Observable output** | State changes render statically at targets; setter refreshes all windows once |
| **Side effects** | Full-window refresh on change; animations needed to show state (e.g. progress bars) are the documented exception and keep running |
| **Persisted state** | App-level bool |
| **Error behavior** | None |
| **Retry or recovery behavior** | N/A |
| **Owner (layer/package)** | `gpui` core (`app.rs:1240-1257`; honored in `style_transitions.rs`, `elements/animation.rs`) |
| **Evidence** | Observed fact: flag, setter with refresh (`app.rs:1240-1257`); `jump_to` on reduce (`style_transitions.rs:269`; `animation.rs` reduce branch) |

## High-Value Behaviors

B2d-relevant notes only; other blocks pending.

- **Frame pumping (follow-up behavior):** active transitions/animations re-request frames until settled/completed (`Transition::evaluate`, animation `done` flag). A port must implement demand-driven frame scheduling, not fixed-rate ticks, or idle apps will burn CPU and settled animations may overrun.
- **Wall-clock caution:** sampling uses read-time clocks (`Instant::now`, executor `now()`). Animation progress is a pure function of timestamps, but the timestamps themselves come from platform frame delivery — pacing guarantees stay with open question `q-frame-scheduling` (verify at runtime). No B2d finding asserts settled wall-clock behavior.
- Cancellation/abort, streaming/partial output, persistence/resume: not applicable to B2d scope (no persisted animation state across runs).

## Security and Authorization

Deferred to B2f with rationale: the framework is a library with no auth model (no users, sessions, or permissions). Credential storage (OS keychain via platform backends) is platform integration, covered under B2f supporting systems if its behavior proves contract-relevant. No auth contracts asserted in B2d.

## Configuration Model

Pointer to `findings/config-model/config-model.md` (architecture phase) for sources/precedence. B2d additions: `reduce_motion` flag (App-level, setter refreshes all windows). Remaining env/feature-flag behavior belongs to B2f. Animation-relevant config is exhausted by the flag above.

## Doc/Test Conflicts

None found in B2d scope. (Docs-vs-code comparison for animation: doc comments on `step`/`step_ramp`/`is_settled` match the implemented math; no test suite was executed — tests are read as contracts only where cited, none cited here beyond code-level doc examples.)

## Black-Box Acceptance List

B2d scenarios only; other blocks append theirs at phase completion.

| # | Scenario | Precondition | Action | Expected Outcome |
|---|---|---|---|---|
| B2d-1 | Zero-duration motion completes immediately | `Motion` with zero duration, just started | Sample at any `elapsed >= 0` | Phase `Completed`, progress END, `is_active` false |
| B2d-2 | Delay gate | Motion with delay D | Sample at `elapsed < D` | Phase `Delayed`, progress at start value, `is_active` true |
| B2d-3 | Retarget continuity | Transition mid-flight at value V | Set new goal | Presentation continues from V with no jump (default); restarts from initial only if `continuous(false)` |
| B2d-4 | Reduce motion | `reduce_motion` true, transition/animation active | Next frame renders | Target/resting value presented immediately; animation marked done |
| B2d-5 | Synced lockstep | Two `repeat_synced` animations on different elements | Advance wall clock | Both report identical progress at identical times |
| B2d-6 | Spring settle | Underdamped spring toward fixed target | Sample past `settle_time` | Value stays within epsilon of target; `is_active` false |
| B2d-7 | Undamped spring never settles | Zero-damping spring | Sample at any time | `is_active` remains true (settling time is infinite) |
| B2d-8 | Infinite iterations never complete | Motion with `Iterations::Forever` | Sample at any time | Phase never `Completed` |
| B2d-9 | Completed run reports final iteration | Finite motion, elapsed past total duration | Sample | Phase `Completed`, iteration equals final index |
| B2d-10 | max_fps throttle | Animation with `max_fps = N` | Observe frame callbacks | At most N evaluations per second |

## Coverage and limits

- Inspected scope (B2d): `motion.rs` (Motion/MotionSample/phase/dir/iteration, `sample`/`sample_at`, `checked_extent`, `resting_progress`); `spring.rs` (`step`/`step_ramp`/`propagator`/`is_settled`/`settle_time`); `animated.rs` (`set`/`restart`/`jump_to`/`adopt_completed_target`/`reset`/`sample`); `transition.rs` (`evaluate` frame pumping, `continuous`); `window.rs` `use_transition`/`use_keyed_transition`; `elements/animation.rs` (playlist, synced/unsynced elapsed, max_fps, reduce_motion); `app.rs` reduce-motion flag + epoch init; `style_transitions.rs` evaluate path + reduce branch.
- Skipped scope (later B2 blocks): elements/composition (B2a), input/focus/keys (B2b), full style/taffy mapping (B2c), text shaping (B2e), supporting systems incl. keyring/clipboard trust (B2f).
- Evidence basis: source inspection (code + doc comments as specified behavior).
- Known blind spots: wall-clock pacing of frame timestamps (stays with `q-frame-scheduling`, needs runtime); exact `now` source in style-transition path (frame time vs read time — read as evaluate-time `now`, confirm in B2c/protocols if it matters); gesture/keyboard timing (B2b/B2e).
- Coverage disposition: PARTIAL (B2d block complete to its exit test; B2a–B2f pending by plan).

## Open Questions

None new from B2d. Wall-clock pacing inherits the standing `q-frame-scheduling` (needs-runtime-test); no B2d finding asserts settled wall-clock behavior, so no new entry is required.

| ID | Kind | Description | Deferred Reason |
|---|---|---|---|
| | | | |

## Carry-Forward

None from B2d (no downstream phase is active yet for routing; mech-CF1 to protocols stands from the mechanical phase and is unaffected).

| ID | Target Phase | Description | Deferred Reason |
|---|---|---|---|
| | | | |

---

## Validation

<!-- Phase incomplete: B2a–B2f pending. Validation runs at phase completion. -->

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | User-facing surfaces are split by surface type. | PENDING | API/SDK surface identified; full surface split at completion. |
| 2 | Feature contracts record trigger, defaults, outputs, side effects, persisted state, error behavior, and recovery behavior. | PENDING | B2d contracts complete per template fields; remaining blocks pending. |
| 3 | Security and authorization model is documented (if applicable). | PENDING | Deferred to B2f with rationale; skip-or-document decided at completion. |
| 4 | Contract ownership is mapped back to a layer or package. | PENDING | B2d ownership mapped; full map at completion. |
| 5 | A black-box acceptance list is included. | PENDING | B2d scenarios B2d-1–B2d-10 recorded; full list at completion. |
| 6 | Findings are marked with evidence levels. | PENDING | B2d claims tagged (all observed fact); phase-wide check at completion. |
| 7 | Coverage and limits name inspected scope, skipped scope, evidence basis, and blind spots. | PENDING | B2d scope recorded; full section at completion. |

**Validated by:** — (pending phase completion)
**Overall:** PENDING
