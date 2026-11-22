# Build and Deploy

Build-pipeline and packaging notes. The architecture map (`findings/architecture/architecture-map.md` §Build and Packaging) owns the summary; this file owns the recipe/job-level detail. (`observed fact` unless noted.)

## 2026-11-21 — architecture phase

### Toolchain

- Cargo workspace, `resolver = "3"`, `edition = "2024"`, `rust-version = "1.95"` workspace-wide; MSRV pinned as `msrv := "1.95.0"` in `justfile` and enforced by the `msrv` CI job (bump to 1.95 was needed for `Vec::push_mut`, `CHANGELOG #247`). Default workspace member: `crates/gpui` only (`Cargo.toml:29`).
- Clippy workspace lints deny `dbg_macro`, `todo`, `declare_interior_mutable_const`, `redundant_clone`, `disallowed_methods` (`Cargo.toml:326-341` + `clippy.toml`); `typos.toml`, `audit.toml`, `deny.toml` (license allow-list + `wgsl-rs` clarifications), `cargo-machete` for unused deps.
- `flake.nix`: Nix dev shell via fenix toolchain + crane builders.

### `justfile` recipes (task runner)

`check`/`build`/`test` (flag passthrough), `build-{linux,mac,windows}`, `build-examples`, `check-wasm`, `check-wasm-atomics`, `check-examples`, `test-doc`, `test-nextest`, `test-with-seed`, `fmt`/`fmt-check`, `clippy-fix`, `typos`, `machete`, `msrv-check`, `lint` (= fmt-check + clippy + typos + machete), `check-packages`, `ci`/`ci-tidy`/`ci-test`/`ci-wasm`, `clean`, `update`/`outdated`, `release-version`/`release-sync`/`release-prepare`/`release-check`/`publishable`/`release-tag`, `sync-upstream*` (+ `sync` alias), `sync-upstream-status`, `doc-open`.

### CI (`.github/workflows/`)

- `ci.yml`: change-aware `orchestrate` (docs-only changes skip tests) → `fmt`, `clippy`, `typos`, `lockfile`, `machete`, `msrv`, `check-wasm` → `test-linux`, `test-mac`, `test-windows`, `check-examples`.
- `release*.yml` / `prerelease.yml`: version PRs, tag builds, crates.io publish (`publish` + `verify-publish`), GitHub releases.
- `audit.yml`: dependency/security audit. `vouch-*.yml`: contributor vouch governance automation (matches `CONTRIBUTING.md` vouch system).
- `SETUP.md` OS deps: Xcode CLT (macOS/Metal), `libxkbcommon/wayland/X11/EGL/fontconfig` dev packages (Linux), MSVC + Windows SDK (Windows); Rust via rustup + rustfmt/clippy.

### Codegen / packaging quirks (port-relevant)

- `gpui_render` build.rs: `wgsl-rs` + `naga` compile Rust shader modules to WGSL into `OUT_DIR` (`BASE_WGSL`, `BASE_DOWNLEVEL_WGSL` for WebGL2/GLES downlevel path via `rgba32uint` data texture — `artifacts.rs`).
- macOS build-deps: `bindgen 0.72`; Windows: `embed-resource` app-manifest embedding (`windows-manifest` feature, target-specific build-deps).
- All crates versioned in lockstep at `0.4.0`, published as `gpui-ce` / `gpui_ce_*` (`cargo-shear` metadata present for dep hygiene).
- Upstream sync: `scripts/sync-upstream/sync_upstream.py` vendor-branch merge; `state.json` pins last Zed SHA (`b1a7ef0…`, 2026-09-03). `docs/releasing.md` + `MAINTENANCE.md` cover the human release/governance side.
