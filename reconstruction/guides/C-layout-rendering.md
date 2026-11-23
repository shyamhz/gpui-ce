# C. Layout & Rendering

This guide owns geometry, element traversal and the scene-to-renderer
contract. [B](B-runtime-interaction-state.md) owns when a frame is requested;
[D](D-text-platform-resources.md) owns shaping and resource providers.

## Style and measurement

**Reconstruction requirement.** Inputs are a styled tree, known
dimensions, per-axis available space, root/override rem size and device
scale. Distinguish `Definite(n)`, `MinContent` and `MaxContent` per axis.
Do not replace an indefinite constraint with zero. Resolve authored
logical direction and bidi before computing geometry; a direction-only
change can invalidate just the affected subtree. Default position is
relative. Map length as follows:

| Input | Value at the layout boundary |
|---|---|
| Pixel or rem length | Resolve to logical pixels with the active rem size, then snap to the device grid before mapping an absolute length. |
| Relative fraction `f` | Pass a percentage/fraction of the reference dimension; `0.5` means half, not one-half percent. |
| Auto | Retain the engine's automatic sizing semantics; do not substitute a definite length. |
| Measured leaf | Ask for intrinsic size with known dimensions and the available-space tags; use the returned size in that pass. |

For an auto-sized axis with two nonnegative absolute padding lengths
and a nonzero total, snap the total and divide it by the authored ratio.
Explicit axes, percent lengths, negative pairs and zero totals use normal
per-edge conversion.

Use measurements that can be repeated under the same inputs. Request and
compute nodes for the current frame; do not read stale cached geometry after
constraint, style or direction changes. Sum local positions up the tree
before snapping bounds: `snap(edge) = round_half_toward_zero(edge × scale) /
scale`. Snap both edges so shared edges close; keep text placement
parent-relative to preserve offsets. Return logical bounds. Failed internal
layout/tree construction is an invariant error, not a retry policy.

**Implementation choice — reference engine.** GPUI feeds Taffy 0.13.0 a
left-to-right engine direction after its own direction processing. Preserve
observable mappings (sizing/overflow/box edges, flex direction/wrap/basis,
alignment/gaps and grid placement). The grid repeat variants map to
`minmax(0, 1fr)`, `minmax(min-content, 1fr)` and `minmax(0, max-content)`.
Equivalent engines are fine; do not inherit browser defaults or assume
unspecified style combinations match without fixtures.

**Evidence:** [contracts C7–C12](../findings/behavioral-contracts.md#apisdk--layout-and-measurement-b2c);
`crates/gpui/Cargo.toml`, `crates/gpui/src/taffy.rs:106-200,426-470,630-696,749-935,955-1010`.

## Element phases, state and scroll

**Reconstruction requirement.** Traverse `request layout → compute →
prepaint → paint`. Reject repeated or out-of-order phase use; measuring a
root again may use the previous result for identical available space.
Prepaint builds hitboxes and geometry; paint emits records against those
bounds. Canvas exposes both passes with the same bounds. Use stable element
identity together with state kind to recover state across adjacent frames.
A call-site key alone aliases loop instances; use an explicit item key
for distinct state. Deferred work follows ordinary work, and each round
orders by priority so higher priority paints above lower priority.

Hit testing walks front to back. A point must be inside the mask and the
hitbox bounds (or one of its inline fragments). An ordinary match remains
eligible; a hover-only blocker cuts off lower hover while preserving lower
scroll candidates; full occlusion ends both lists. Keep entry metadata
separate from eligibility. [B](B-runtime-interaction-state.md#normalized-input-focus-and-shortcuts)
uses those lists during dispatch.

Uniform virtual lists measure to a visible range and report that range
rather than materializing all rows. For each scrollable axis compute
`max = max(0, padded_content − viewport)`, then clamp offset to `[−max, 0]`;
scroll-to-bottom uses the current vertical `−max`. Recompute on resize or
content change. A container query receives the computed container size.

**Implementation choice — reference caching.** View reuse requires a
matching key (bounds, clip, text style, direction and bidi), a non-dirty
view, no fresh element, and no force-refresh. Copy prepaint/paint ranges
from the published frame into the building frame; remap dispatch references
and store the new spans before rotating frames. Reuse must never change
ownership or ordering. A port may rebuild instead; the audit did not
establish a reachable stale-range fault on the traced path.

**Evidence:** [contracts C13–C20/C33](../findings/behavioral-contracts.md#apisdk--elements-and-composition-b2a)
and [protocols S3](../findings/protocols-and-state.md#s3-element-traversal-and-frame-index-ownership-mech-cf1);
`crates/gpui/src/element.rs:579-605,825-950`,
`crates/gpui/src/view.rs:539-557,595-607,644-660`,
`crates/gpui/src/window.rs:798-854,979-985,1263-1265,3650-3863,4222-4300`,
`crates/gpui/src/elements/uniform_list.rs`, `crates/gpui/src/elements/div.rs:3143-3204`.

## Scene and renderer

**Reconstruction requirement.**

1. **Record:** take typed paint primitives, bounds, masks and layers.
   Intersect ordinary primitives with the mask and skip empty intersections.
   Retain filter boundaries even when clipped out so pairing and order
   survive. Replay cached paint operations as records, not old GPU commands.
2. **Compile:** merge primitive streams in paint order. Batch only compatible
   instances, respecting kind, atlas/pipeline and intervening boundaries.
   Pair filter scopes with a stack and compute resource requirements for
   instances, paths and intermediate targets. An isolated scope composites
   into its parent. The reference compiles an unmatched opening inline;
   an unmatched closing marker asserts in debug and falls back inline
   without that assertion. Keep ranges bound to the originating scene.
3. **Consume:** draw the published scene in plan order; reserve capacity and
   required resources before encoding. Atlas bindings belong to the renderer;
   retain imported surfaces needed by the complete scene, not just a single
   batch. Preserve glyph lookup/raster failure from [D](D-text-platform-resources.md#shaping-caret-and-raster).

**Implementation choice — adapter example.** wgpu acquires a surface
texture, encodes and submits, then calls present. No configured target
returns failure; suboptimal/lost/outdated acquisitions trigger reconfigure,
timeout/occlusion request redraw, and validation records a fault and
requests redraw. A failed encode after acquisition releases the acquired
view/frame before reconfiguring. Metal and DirectX share plan inputs but
need not use that recovery policy. None of these calls proves display
completion; see [E](E-implementation-verification.md#unresolved-runtime-behavior).

**Implementation choice — native resources.** The reference wgpu atlas
can clear cached textures, pending uploads and glyph entries, recreating
them as needed; on device loss the atlas also replaces its device/queue.
An imported surface supplies typed-by-adapter content and device dimensions;
the surface element fits it to layout bounds and paints with its opacity.
Do not infer portable import of native texture handles across adapters.

**Evidence:** [protocols S6](../findings/protocols-and-state.md#s6-scene-construction-compilation-and-presentation);
`crates/gpui/src/scene.rs:136-177,242-313,509-650`, `crates/gpui/src/scene/plan.rs:34-163`,
`crates/gpui/src/window.rs:3395-3411`, `crates/gpui_apple/src/metal_renderer.rs:581`,
`crates/gpui_windows/src/directx_renderer.rs:491`,
`crates/gpui_wgpu/src/wgpu_renderer/frame.rs:16-42,244-289`,
`crates/gpui_wgpu/src/wgpu_renderer/platform.rs:124-182`,
`crates/gpui_wgpu/src/wgpu_atlas.rs:98-117,162-179`,
`crates/gpui/src/elements/surface.rs:13-42,166-184`.
