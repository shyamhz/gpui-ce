# Closeout — defect-scan-mechanical

## Summary

- Executed the mechanical defect scan block-by-block (B1a logic/correctness, B1b error handling, B1c config/environment) with entry validation per block.
- Produced 5 findings (3 medium, 2 low): Windows-only hide_other_apps panic (F1.1); debug-only frame-reuse index enforcement (F1.2); log-only restart failure on all backends (F2.1); HttpClient without timeout/cancellation (F2.2); GPUI_X11_SCALE_FACTOR invalid-value panic (F6.1).
- Filed one carry-forward (mech-CF1) to protocols to confirm the frame-reuse invariant. No open questions from this phase; prior architecture questions untouched.

## Files Touched

- **Added:** .codecarto/findings/defect-scan-mechanical/mechanical-defects.md, .codecarto/scratch/checkpoints/defect-scan-mechanical.md, .codecarto/scratch/handoffs/defect-scan-mechanical.yaml
- **Modified:** none
- **Deleted:** none

## Tests / Gates

| Gate | Result | Notes |
|---|---|---|
| codecarto_validate (defect-scan-mechanical) | PASS | Framework parse of the appended validation block |
| repo test suite | not run | read-only investigation; no code modified |

## Decisions Beyond Prompt

None. Severity and action assignments follow the pass rubrics; no spec or prompt divergence.

## Proposed Conventions

None new. Evidence-tag discipline from architecture still stands as the single staged proposal.

## Open Questions Left Behind

None from this phase. (Architecture-phase questions q-headless-parity, q-gpu-fallback, q-frame-scheduling remain open in status.yaml.)

## Carry-Forward Routed

| ID | Target Phase | Description | Deferred Reason |
|---|---|---|---|
| mech-CF1 | protocols | Confirm frame-reuse cache-invalidation invariant behind F1.2 | Frame-lifecycle state machine is protocols rubric |

## Next Session Pointer

Begin the contracts phase: run entry validation, then B2d (animation/timing contracts) first per the agreed B2 order. The phase handoff for contracts must collect mech-CF1 only if protocols is active — note mech-CF1 targets protocols, not contracts, so it stays parked until then. If the MCP client is missing from /tmp (machine-local, wiped between sessions), rebuild it from the published codecartographer-pi package before running codecarto_validate.
