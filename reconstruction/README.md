# GPUI-CE Reconstruction Workspace

Human-readable, committable record of the GPUI-CE reverse-engineering project.
The machine workspace lives in `.codecarto/` (framework-owned state, phase
gates, handoffs); this folder is the record a person reviews and git tracks.

## Layout

- `plan-reconstruction.md` — the 11-section end-to-end plan (authoritative).

- `plan-blocks.md` — block decomposition B0–B7d, exit tests, B7a spike plans,
  execution protocol (authoritative for how blocks run).

- `findings/` — mirror of the completed architecture findings (map + 5
  secondary outputs). The framework reads the originals under
  `.codecarto/findings/`; this folder is the committed copy.

- `verification/` — verification reports on completed work.

## Authority and mirror policy

- Plans (`plan-*.md`) live here only. The framework never reads them.

- Findings originate in `.codecarto/findings/` (phase outputs the framework
  validates and later phases consume as required reading). At each block exit,
  new findings are mirrored here, so this folder tracks the latest block
  output. Mirrors of incomplete phases carry explicit PENDING markers — they
  are work-in-progress snapshots, not validated results; only a phase with a
  PASS validation block counts as complete.

- Framework state (`status.yaml`, closeouts, `THREAD_LOG.md`, `CONVENTIONS.md`,
  `DECISIONS.md`) stays in `.codecarto/` and is committed alongside this
  folder at each block exit. Machine-local paths (`scratch/`, `dashboard.html`,
  usage logs, `broadside/` runs) are intentionally never committed — see
  `.codecarto/.gitignore`.
