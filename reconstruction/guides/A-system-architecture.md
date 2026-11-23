# A. System Architecture

**Start here.** [B](B-runtime-interaction-state.md) owns runtime semantics,
[C](C-layout-rendering.md) geometry and scenes,
[D](D-text-platform-resources.md) host, text and resources, and
[E](E-implementation-verification.md) the implementation and proof plan.
Source paths are repository-relative.

## Ownership and dependency direction

**Reconstruction requirement.** This is an embedded UI library, not an app
server. Application code supplies the model, root view and launch callback.
The core owns identities, updates, interaction and ordered scenes; it defines
the host, window and text interfaces. Adapters implement those interfaces and
return host events or capability results. A caller must be able to use the
core with a test host without making normal UI state depend on native handles.

**Implementation choice — reference arrangement.**

| Layer | Reference ownership | Replaceable detail |
|---|---|---|
| Substrate | Scheduler; collection, tree, path and style-refinement helpers | Thread primitives, container types, IDs and allocator |
| Core | `gpui`: app/window/entity graph, elements, layout/dispatch/scene interfaces | Crate and type hierarchy; use explicit invariants instead |
| Shared providers | Parley/font catalog, shader and raster support | Layout/shaping/raster implementation, subject to observable behavior |
| Host and presentation | Platform facade; macOS/Apple, Linux, Windows, web and GPU adapters | First target and backend technology |
| Optional integration | Widgets, media/Tokio bridges, inspector, profiler and tooling | Keep out of the initial core |

The normal dependency edges lead from adapters to core and from core to
utilities. The reverse edge from core to platform exists for development and
examples; it is not a production cycle. The platform trait declares **74
methods** in source including default and target-gated declarations; display
and window traits are separate. The count is not a port requirement.

**Evidence:** [architecture map](../findings/architecture-map.md) and
[surface inventory](../findings/public-surfaces.md);
`crates/gpui/Cargo.toml`, `crates/gpui_platform/Cargo.toml`,
`crates/gpui_platform/src/gpui_platform.rs:18-94`,
`crates/gpui/src/platform.rs:151-386,389,891,1206`.

## Build and configuration boundaries

**Implementation choice — reference build.** Cargo resolver 3 and workspace
edition 2024 are declared at the root. `gpui-ce` declares Rust 1.95 and CI
checks the workspace with 1.95.0. The build generates shader source and can
embed native resources. Build switches select providers or optional tooling;
do not copy Cargo packaging, Rust code generation or release machinery to
match a runtime contract.

**Reconstruction requirement.** Keep three controls distinct: compiled
capabilities, explicit embedding/window options, and runtime environment.
Do not apply a single universal precedence rule across them. The backend
selection algorithm and invalid-setting behavior are owned by [D](D-text-platform-resources.md#host-selection-and-native-roles).
The core does not need a framework settings database to interpret those
controls.

**Evidence:** [build notes](../findings/build-and-deploy.md) and
[configuration inventory](../findings/config-model.md);
`Cargo.toml:29-33`, `crates/gpui/Cargo.toml:14-54`, `justfile:9,164-168`,
`.github/workflows/ci.yml:132-148`, `crates/gpui_render/build.rs`,
`crates/gpui/src/platform.rs:107-135`.
