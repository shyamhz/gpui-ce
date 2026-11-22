# Conventions

<!--
  Project-level skeleton. Copy this to `.codecarto/CONVENTIONS.md` (one level up from templates/)
  the first time the orchestrator promotes a convention. Then add entries as they accumulate.

  This file holds cross-cutting patterns that have been promoted to project-wide invariants.
  Every new session reads this file and either honors these conventions or documents why it
  diverges.

  This file is **orchestrator-maintained**. Phase executors propose additions in their session
  closeout; the orchestrator promotes them at the phase boundary. In an inline run the same chat
  does both — the rule is about *when* (between phases, deliberately), not about which thread.
-->

Cross-cutting patterns promoted to project-wide invariants. Every session reads this file at start
and either honors these conventions or documents why it diverges.

This file is **orchestrator-maintained**. Phase executors propose additions in their closeout's
"Proposed Conventions" section; the orchestrator promotes them here at the phase boundary — in an
inline run, the same chat changing hats between phases.

## How conventions get added

A new entry lands here when ONE of the following holds:

1. **Three independent sessions** reach for the same pattern (the "lift if it generalizes" rule
   applied to conventions themselves), OR
2. **One session** explicitly promotes a pattern in its closeout report and the orchestrator
   confirms it generalizes, OR
3. **The spec or framework feedback corpus** identifies a project-wide invariant that future
   implementing sessions need to know about.

The orchestrator owns this file. Implementing sessions propose; orchestrator promotes.

## Entry shape

Each convention is a numbered section (`## C<NN>. <Title>`) with three required parts:

- **Body** — the rule itself, in prose. May include a code block for shape contracts.
- **Why:** — the reason the rule exists. Often a past incident or a defect class the rule
  prevents. Future maintainers judging edge cases need to know *why* to judge whether the rule
  applies.
- **How to apply:** — when and where the rule kicks in. Should answer "is this case in scope?"

Optional:
- **Current implementers:** — files/modules that already follow the rule. Useful as worked examples.
- **Source:** — the closeout entry where the orchestrator promoted this convention.

---

## C01. Evidence-tagged claims with file cites

Every load-bearing finding carries one evidence tag — `observed fact`,
`strong inference`, `external-behavior claim`, `portability hazard`, or
`open question` — plus the file path (and line where it matters) that
supports it. Unverifiable-by-reading claims stay unsettled: no settled
action is asserted from an `open question` or `external-behavior claim`
without runtime evidence.

**Why:** A reimplementation in another language must re-verify each
architectural claim without re-reading 217K LOC of Rust. Bare assertions
rot; tagged claims with cites let a later session check exactly the
supporting source. A four-phase failure in this framework's history came
from a mislabeled question suppressing verification for every later phase.

**How to apply:** Tag every load-bearing claim in every findings document.
`observed fact` = direct statement from docs, tests, schemas, types, or
code. `strong inference` = architectural conclusion from multiple facts.
`external-behavior claim` = behavior of a system outside this source tree
(OS, GPU, driver); stays unsettled until a runtime probe or that system's
own source confirms it. `portability hazard` = assumption tied to Rust,
runtime, OS, or third-party SDKs. `open question` = missing or conflicting
behavior still needing evidence. The pairing rule is mechanical: unsettled
evidence never carries a settled action.

**Current implementers:** All six architecture findings
(`findings/architecture/architecture-map.md` + 5 secondary outputs);
defect-scan-mechanical findings (evidence tags on every finding row).

**Source:** Architecture closeout `2026-11-21-architecture` (proposed
convention); mechanical findings applied it; orchestrator confirmed it
generalizes to all future phases at the contracts boundary, 2026-11-22.

---

<!-- Repeat the C<NN> block for each convention. Number sequentially. -->
