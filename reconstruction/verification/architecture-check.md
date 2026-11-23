# Architecture Check — verification of the architecture-phase findings

Scope: targeted read-only spot-checks of the six architecture outputs against source.
No workflow action taken; no findings modified; no phase executed.

## 1. Overall accuracy assessment

The architecture picture is **trustworthy as a structural map and unreliable on counted details**.
Subsystem inventory, dependency direction, boot/frame/event flow, and state ownership all
re-verified against source. Four claims need correction (two wrong numbers, two wrong
mechanisms — all inexact phrasing, none load-bearing for the layer map). Coverage is
thinnest on the animation/motion core, which is user-visible behavior, not plumbing.

## 2. Claim verification by area

| Area (source file) | Verdict | Evidence |
|---|---|---|
| Subsystems + responsibilities (architecture-map §Layer Map) | VERIFIED | 24 crate dirs confirmed by listing; every role re-checked against manifests and lib.rs entry points (`gpui_platform.rs`, `editable_text`/`switch`, `MetalRenderer`, `WgpuRenderer`, `ParleyTextSystem`). Normal-dependency grep on `crates/gpui/Cargo.toml` shows only leaf workspace deps + `gpui_macros` — no backend crates. |
| Dependency direction + cycle analysis (architecture-map §Dependency Direction) | VERIFIED | `gpui → gpui_platform` exists only under `[dev-dependencies]` (`crates/gpui/Cargo.toml:162`); `gpui_platform → gpui` is a normal dep. Dev-only cycles are legal in Cargo; no production cycle found. Facade `current_platform` cfg-mapping re-read and accurate. |
| Boot / window / frame lifecycle (runtime-lifecycle.md) | VERIFIED | `Application::run → platform.run` (`app.rs:327`), forced first `draw` in `open_window` with Windows-race comment (`app.rs:1558-1592`), `Window::draw` phase order (`window.rs:3218+`), `dispatch_event`/`handle_input` entry points all re-read verbatim. |
| State + resource management (state-and-storage.md) | VERIFIED | `EntityMap`/slotmap, observer `SubscriberSet` tables, per-frame arenas, atlas + `TextSystem` memo caches, env-var list — all re-grepped; no config files or durable stores found beyond what is listed. |
| Execution + rendering flow (architecture-map §§Runtime, Concurrency) | PARTIAL | Frame → `Scene` primitives → `ScenePlan` → backend `draw` re-verified (`scene.rs:392-437`, `metal_renderer.rs:661`, `window.rs:2151`). Backend internals (command encoding, atlas eviction, vsync) were never read — correctly recorded as blind spots, not findings. Two mechanism sentences are wrong (see §3). |
| Overlooked boundaries (§6) | PARTIAL | No missed load-bearing seam. Three real omissions, all below the incorrectness threshold: animation/motion core, layer-shell surface roles, gesture-recognizer design. |

## 3. Incorrect or misleading findings (correct here; source files untouched)

1. **INCORRECT — `PlatformInput` variant count.** `runtime-lifecycle.md` says 17 variants;
   the enum has **14** (`interactive.rs:771-800`, counted).

2. **INCORRECT — `Platform` trait method count.** The architecture map says "~90 methods";
   brace-matched count is **74** (`platform.rs:151-386`). The methods past line 386
   (`id`, `uuid`, `bounds`, …) belong to sibling traits such as `PlatformDisplay`.

3. **MISLEADING — "channel-based `update()`".** Architecture map §Concurrency Model implies
   cross-thread hops go through a channel-based `update()`. `ApplicationHandle::update`
   (`crates/gpui/src/app.rs:193-215`) borrows the main-thread `Rc<AppCell>`.
   `AsyncApp` likewise borrows that app on the same thread via a weak reference
   (`crates/gpui/src/app/async_context.rs:57-69,238-250`). The scheduler, not either
   update method, dispatches foreground runnables to the UI thread
   (`crates/gpui/src/platform_scheduler.rs:109-122`).

4. **MISLEADING — "worker pool via smol-like async-task".** The Linux dispatcher
   spawns the background workers (`crates/gpui_linux/src/linux/dispatcher.rs:30-52`);
   `async-task` supplies runnables and task handles
   (`crates/gpui_scheduler/src/executor.rs:229-251`). The OS-thread/Wasm-worker
   code in `crates/gpui_scheduler/src/scheduler.rs:163-208` is the distinct
   dedicated-session path, not the pool constructor.

5. Minor: the MSRV cite `root Cargo.toml:29,95` conflates the workspace file with
   `crates/gpui/Cargo.toml:14` (`rust-version = "1.95"`). The workspace check pins
   1.95.0 (`justfile:9,164-168`, `.github/workflows/ci.yml:132-148`).

**B7b disposition:** Items 1–5 were folded into the architecture map,
public surfaces, runtime lifecycle and build notes. Both counts were
rechecked at the declaration boundary. No GPUI source or framework state changed.

## 4. Critical gaps (not resolved here, by instruction)

1. **Animation/motion core — investigate first when approved.** `motion.rs` (damped
   harmonic oscillator vocabulary, `Motion`/`secs`/`millis`), `spring.rs` (stiffness /
   damping / mass parameters), `animated.rs`, `style_transitions.rs` (~4.4K LOC combined)
   plus the `synced_animation_epoch` phase-lock. The findings name the transitions API
   from the changelog but never the spring-physics timing model. Timing curves are
   user-visible behavior any port must reproduce; the code is pure computation, no
   runtime needed.

2. **Layer-shell + popup surface roles — can wait.** `platform/layer_shell.rs`
   (`Layer::{Background,Bottom,Top,Overlay}`) and `platform/popup.rs` were never
   mentioned. Needed only if the port targets Linux desktop overlays/menus; defer
   until a Linux windowing investigation.

3. **Gesture-recognizer design — can wait.** `gestures.rs` documents a portable
   core arena (recognizers compete, winner claims, losers cancel; tap→click,
   pan→scroll, pinch→pinch). Findings list the event names but not the design.
   Matters for touch parity; defer until touch behavior is in scope.

4. Already tracked, no action: keymap file format (blind spot), backend draw
   internals and frame pacing (open questions `q-frame-scheduling`, `q-gpu-fallback`,
   headless parity `q-headless-parity`).

## 5. Recommended next investigation

Read the animation/motion subsystem end to end (`motion.rs`, `spring.rs`,
`animated.rs`, `style_transitions.rs`, `Window::use_transition` /
`use_keyed_transition`, `synced_animation_epoch` scheduling in `window.rs`):
it is the largest block of user-visible behavioral semantics with no dedicated
coverage, it composes directly with the already-mapped frame loop, and it is
fully verifiable by reading — no runtime, no pipeline change required.
