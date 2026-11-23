# Runtime spikes — B7a

## Scope and evidence

GPUI-CE source at `ee17377ebe174a76e7495c2bb80ffe1e0e0ce288`.
Linux x86-64 only, in the same session with a working X11 display and Wayland
compositor. `vulkaninfo --summary` reported an NVIDIA GeForce RTX 4070 with
driver 610.43.03; `glxinfo -B` independently reported the hardware renderer
on X11. `wayland-info` enumerated a live compositor and `xdg_wm_base`.
These are environment checks, not GPUI results.

The default Rust 1.91.1 could not build the locked checkout, which requires
1.95. The installed Rust 1.95.0 built the `hello_world` example and linked
the standalone [Rust fixture](b7a-linux-probe.rs). The
[runner](run-b7a-linux.py) drives it with per-process settings; it does not
change the display configuration, kernel drivers, or GPUI source. The
fixture uses a 256×192 logical-pixel view with two opaque colors and no
text, to isolate the initial capture from fonts and animation. Limits
below apply even when a run exits successfully.

## Reproduction

With Rust 1.95.0, the workspace's Linux native build dependencies, and a
fresh `CARGO_TARGET_DIR`, build the pinned example and feature-enabled
libraries:

```sh
rustup run 1.95.0 cargo build --locked -p gpui-ce -p gpui_ce_wgpu \
  --example hello_world \
  --features gpui-ce/wayland,gpui-ce/x11,gpui-ce/test-support,gpui_ce_wgpu/test-support
```

Link the fixture with Rust 1.95.0, edition 2024, and
`-L dependency=<target>/debug/deps`. Supply `--extern` paths for
`gpui=libgpui-*.rlib`, `gpui_platform=libgpui_ce_platform-*.rlib`,
`gpui_wgpu=libgpui_ce_wgpu-*.rlib` and `env_logger=libenv_logger-*.rlib`
from that build. Then run `python3 reconstruction/verification/run-b7a-linux.py
<probe-binary> <evidence-directory>` with Pillow, ImageMagick `import`,
`xdotool`, Bubblewrap and GNU `timeout`. The runner filters by fixture PID
and title for X11 capture and records raw process output and timestamp
samples. Environment/driver availability and package paths can differ on
other hosts; record the actual conditions rather than assuming equivalent
fault injection.

## Q1 — Headless pixel parity

**Predeclared comparison:** byte-exact RGB for equal dimensions, using the
same fixture and target size. The X11 capture is the fixture's drawable,
not an independently timed physical display capture; alpha is not compared.

The initial normal-window attempt was rejected before comparison: the
offscreen test window used scale 2 and captured 512×384, while the X11
window used scale 1 and was tiled to a 953×1032 drawable. A differently
sized capture is not evidence of parity or divergence.

In the retry, the live fixture used an X11 popup to avoid tiling and a
process-local scale override of 2. Both images were **512×384**. The
comparison found **0 differing RGB pixels out of 196,608**, with a maximum
channel delta of 0. A point in the foreground matched `(234, 173, 39)` and
a point in the background matched `(40, 79, 125)`. This verifies one opaque
two-color fixture against the X11 drawable, not normal-window parity,
compositor output, filters, font rasterization, or other backends.

## Q2 — GPU/surface availability

**Fault conditions:** for the restricted processes, Bubblewrap mounts a
minimal `/dev` (no `/dev/dri` or `/dev/nvidia0` observed) and Vulkan/EGL
loader overrides prevent the normal drivers from loading. In the separate
software run the Mesa EGL vendor is restored and software GL requested
while Vulkan and device access stay disabled. These are process-local
conditions, not a GPU-less physical host or a proof of every driver path.

| Linux attempt | Observed result |
|---|---|
| Unrestricted GPU offscreen control | Returned a 64×64 image; process exit 0. |
| Device nodes and both loader paths blocked; offscreen | Renderer returned an error to the fixture: no suitable adapter from either Vulkan or GL. Fixture exit 1. |
| Same restrictions; X11 and Wayland native window | Both reached the named backend and returned a GPU-context error to `open_window`; Vulkan and GL both reported failure to create a surface. After reporting the error, the fixture's quit call did not end either process before the 7 s timeout (exit 124). This is not a diagnosis of the shutdown cause. |
| Same restrictions; explicit Linux headless window | Reported `HOST headless` and `OPEN_OK`; process exit 0. No GPU-backed image requested in this case. |
| No device nodes or Vulkan; Mesa EGL with software requested | Offscreen returned a 64×64 image; process exit 0. This controlled offscreen success does not establish native-window software fallback. |

The restricted outcome matrix repeated successfully. These attempts did
not exercise browser WebGL2 or establish a downlevel texture path.

## Q3 — Frame pacing

**Measurement point:** `Window::on_next_frame` callback entry, with the
fixture requeuing demand and refreshing on active runs. The loaded run adds
an 8 ms sleep in root rendering, a controlled UI-thread delay rather than a
GPU benchmark. The idle run requests no recurring callbacks and counts
root render invocations, not platform wakeups or display deliveries.
Statistics use inter-callback intervals, with an inclusive p95.

| Backend | Mode | Callbacks | Min ms | Median ms | p95 ms | Max ms |
|---|---|---:|---:|---:|---:|---:|
| X11 | Active | 60 | 0.933 | 10.009 | 10.039 | 10.062 |
| X11 | Active with rendering delay | 60 | 9.490 | 10.010 | 20.063 | 42.579 |
| Wayland | Active | 60 | 5.214 | 9.961 | 10.265 | 20.525 |
| Wayland | Active with rendering delay | 60 | 9.711 | 10.064 | 20.266 | 47.497 |

These are the first complete run's samples. In the idle window lifetime
(approximately four seconds), the fixture saw 10 root draws on X11 and
11 on Wayland, including startup activity; the repeat saw 6 on each.
The repeat produced another 60 callbacks per active case. Its p95 was
10.051 ms active and 20.040 ms loaded on X11, and 10.179 ms active and
20.036 ms loaded on Wayland. The added render delay increased tail
intervals in both runs. Compare the static trigger paths in protocols
S7/S11 (`crates/gpui_linux/src/linux/x11/client.rs:1983-2017` and
`crates/gpui_linux/src/linux/wayland/client.rs:1481-1497`). Neither the
distribution nor the draw counts measures display completion or proves
which invocation source delivered each application callback.

## Question ledger

The rows record the six required fields. None of the three cross-platform
questions is sufficient to close on this Linux-only scope.

| ID / unknown | Why unresolved | Evidence and limits | Reconstruction impact | Blocking? | Next verification |
|---|---|---|---|---|---|
| `q-headless-parity` — when may headless pixels stand in for display output? | No matched Metal capture or multi-scene display comparison. | One exact match against an X11 drawable; not a display/color pipeline test. | Keep independent scene assertions; do not certify headless as a general pixel oracle. | No for the core; yes for claiming pixel equivalence. | Capture the same scenes on Metal and on the Linux on-screen display path, including text, alpha and filters; control scale/color and compare with a stated threshold. |
| `q-gpu-fallback` — per-host no-device/no-surface outcomes and application visibility | No controlled Windows/macOS/browser device condition; Linux overrides constrain only the tested driver routes. | Process-isolated Linux cases plus an explicit software attempt, not a platform matrix. | Preserve the adapter failure seam; do not promise automatic fallback across hosts. | No for the core; yes for claiming GPU-less parity. | Repeat on GPU-less VMs and with known software rasterizers; record returned errors, exits and rendered frames independently of backend selection. |
| `q-frame-scheduling` — delivered pacing across hosts and load states | Callback samples do not measure displayed frames; Windows, macOS and web are unmeasured. | Linux root-render counts and active callback intervals, tied to source trigger paths rather than presentation feedback. | Tests can pin demand and sampling semantics but not native cadence. | No for the core; yes for claiming delivered timing parity. | Collect native request/draw/present-feedback traces and visible delivery across idle, active, loaded and occluded states; compare X11, Wayland, Windows, macOS and browser. |

Framework question and backlog IDs remain open. No workflow amendment or
changes to the specification are made in this block.
