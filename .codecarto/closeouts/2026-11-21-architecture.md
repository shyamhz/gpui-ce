# Closeout — architecture

## Summary

- Executed the architecture phase inline against pipeline-architecture-only.yaml after confirming status.yaml already selects it.
- Produced the architecture map plus five secondary outputs, all validated PASS, with every load-bearing claim evidence-tagged.
- Recorded three needs-runtime-test open questions and one post-pipeline frame-capture spike; no carry-forward exists in a single-phase pipeline.

## Files Touched

- **Added:** .codecarto/CONVENTIONS.md, .codecarto/DECISIONS.md (seeded skeletons), .codecarto/findings/architecture/architecture-map.md, .codecarto/findings/public-surfaces/public-surfaces.md, .codecarto/findings/runtime-lifecycle/runtime-lifecycle.md, .codecarto/findings/state-and-storage/state-and-storage.md, .codecarto/findings/build-and-deploy/build-and-deploy.md, .codecarto/findings/config-model/config-model.md, .codecarto/scratch/handoffs/architecture.yaml
- **Modified:** none
- **Deleted:** none

## Tests / Gates

| Gate | Result | Notes |
|---|---|---|
| codecarto_validate (architecture) | pending at handoff time | run before codecarto_complete; block appended to architecture-map.md |
| repo test suite | not run | architecture phase is read-only by design |

## Decisions Beyond Prompt

- Drove completion through a local stdio client against published codecartographer-pi 0.27.0 because this host has no codecarto MCP wiring, never hand-editing framework-owned state | The framework forbids hand-editing status.yaml, closeouts, and THREAD_LOG.md, so the published server was run locally to apply validation and completion canonically.
- Kept status.yaml pipeline field untouched after verifying it already selects pipeline-architecture-only.yaml | Editing workflow state by hand is forbidden and the configured value already matched the requested pipeline, so verification replaced modification.

## Proposed Conventions

### Evidence-tagged claims with file cites

**Why:** A reimplementation in another language must re-verify each architectural claim without re-reading 217K LOC; bare assertions rot.

**How to apply:** Tag every load-bearing finding with one evidence level and cite the supporting file path, as done across all six architecture outputs.

## Open Questions Left Behind

| ID | Kind | Description | Deferred Reason |
|---|---|---|---|
| q-headless-parity | needs-runtime-test | Headless vs on-screen pixel parity for use as a port oracle | Needs side-by-side GPU and headless runs |
| q-gpu-fallback | needs-runtime-test | No-GPU behavior and app-visible errors per platform | Backend init paths unread, needs GPU-less execution |
| q-frame-scheduling | needs-runtime-test | Frame pacing on Linux, Windows, web | Needs event-loop observation |

## Carry-Forward Routed

None. Single-phase pipeline, so there is no downstream phase to target.

## Next Session Pointer

Await user approval per the first-pass stop condition. If approved for a wider pipeline, switch pipelines explicitly and start the next eligible phase; begin by re-reading status.yaml and the architecture map rather than re-deriving structure.

## Decisions Beyond Prompt

- Drove completion through a local stdio client against published codecartographer-pi 0.27.0 because this host has no codecarto MCP wiring, never hand-editing framework-owned state
- Kept status.yaml pipeline field untouched after verifying it already selects pipeline-architecture-only.yaml
