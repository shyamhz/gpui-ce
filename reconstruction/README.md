# GPUI-CE Reconstruction Workspace

Human-readable record of the GPUI-CE reverse-engineering project.
[GPUI-CE's `reconstruction/` directory](https://github.com/shyamhz/gpui-ce/tree/main/reconstruction)
is the source of truth. If you're reading this in the standalone mirror,
submit changes to GPUI-CE, not to the mirror.

The mirror contains the guides, specification, and verification records.
Source citations are relative to the GPUI-CE checkout, and the
[Linux probes](verification/runtime-spikes.md#reproduction) are run there.
The `.codecarto/` workspace and GPUI source are not part of the mirror.

## Reimplementation guides

Read these in order; use the phase findings for evidence and exact fixtures.
See the [final verification report](verification/final-verification.md)
for what was checked, what failed, and what remains unresolved.

1. [A. System Architecture](guides/A-system-architecture.md) — layer and build boundaries.
2. [B. Runtime, Interaction & State](guides/B-runtime-interaction-state.md) — lifecycle, input, motion and scheduling.
3. [C. Layout & Rendering](guides/C-layout-rendering.md) — geometry, traversal, scenes and consumption.
4. [D. Text, Platform & Resources](guides/D-text-platform-resources.md) — shaping, IME, native roles and services.
5. [E. Implementation Spec & Verification](guides/E-implementation-verification.md) — build slices, defect dispositions and unresolved runtime questions.

## Layout

- `plan-reconstruction.md` — the 11-section end-to-end plan (authoritative).

- `plan-blocks.md` — block decomposition B0–B7d, exit tests, B7a spike plans,
  execution protocol (authoritative for how blocks run).

- `findings/` — committed mirrors of the phase findings, including the porting
  bundle and language-independent specification. The framework reads the originals under
  `.codecarto/findings/`; this folder is the committed copy.

- `verification/` — source spot-checks and bounded runtime observations.

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

## Mirror setup for maintainers

1. Create an **empty** GitHub repository for the mirror. Do not initialize it
   with a README, license, or `.gitignore`. Review the reconstruction history
   and choose the visibility before publishing.
2. Create a fine-grained GitHub token with access to **only the destination
   repo** and **Contents: Read and write**. Store it in GPUI-CE under
   **Settings → Secrets and variables → Actions → Secrets** as
   `RECONSTRUCTION_MIRROR_TOKEN`.
3. In the same settings under **Variables**, set `RECONSTRUCTION_MIRROR_REPO`
   to the destination's `owner/repo`, for example `shyamhz/gpui-reconstruction`.
4. Once the workflow is on GPUI-CE `main`, run **Publish reconstruction
   mirror** manually from the Actions tab for the initial sync. Subsequent
   pushes to `main` that touch `reconstruction/` publish automatically.

The workflow exports the folder and its history with `git subtree split`.
It only fast-forwards the destination's `main`. If someone commits directly
to the mirror, the workflow fails rather than overwriting their work.
