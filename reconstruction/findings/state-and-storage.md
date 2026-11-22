# State and Storage

Durable-state inventory: what survives a frame, a run, or a reboot. The architecture map (`findings/architecture/architecture-map.md` §Durable State) owns the summary; this file owns the itemized layers. (`observed fact` unless noted.)

## 2026-11-21 — architecture phase

### In-process UI state (per `App`, dropped at shutdown)

- `entities: EntityMap` — slotmap-backed (`slotmap::SlotMap<EntityId, …>`) store of `Box<dyn Any>` keyed by `TypeId`; `Entity<T>` is a typed handle (`app/entity_map.rs:78-478`). Never reused ids (`EntityId` docs).
- Observer tables: `observers`, `event_listeners`, `global_observers`, `new_entity_observers`, `release_listeners`, keystroke observers + interceptors, thermal/wake/layout/quit/restart/window-closed observer sets (`app.rs:847-870`) — `SubscriberSet` keyed by `EntityId`/`TypeId`/unit.
- `globals_by_type: TypeIdHashMap<Box<dyn Any>>` + `global_entities: Vec<AnyEntity>` (retained until explicit removal).
- Windows: `SlotMap<WindowId, Option<Box<Window>>>`, `window_handles`, `focus_handles: Arc<FocusMap>`, `keymap: Rc<RefCell<Keymap>>`, `current_window_by_entity`, `tracked_entities`, per-entity `WindowInvalidator`s.
- Frame-ephemeral: `element_arena` / `event_arena` (bump arenas drained per frame), `layout_id_buffer` (recycled `Vec<LayoutId>`), `pending_effects`, dirty sets, `window_update_stack`, `propagate_event` flag.

### GPU / raster caches (per window/renderer, VRAM + RAM)

- Texture atlases: `metal_atlas` (Apple), `wgpu_atlas`, `directx_atlas` (Windows) — glyph/sprite pages.
- `TextSystem` memo tables: `font_ids_by_font`, `font_metrics` (`RwLock<FxHashMap…>`).
- Swash font cache keyed by (source, collection face) — stale-reuse bug fixed in #406 (`CHANGELOG`).
- `asset_cache` / `AssetRegistry`: preloaded + on-demand blobs (images, SVGs, fonts).

### Environment (read, never written)

`WAYLAND_DISPLAY`, `DISPLAY`, `ZED_HEADLESS`, `XCURSOR_PATH`, `LC_CTYPE`, `XDG_ACTIVATION_TOKEN`, `XDG_CURRENT_DESKTOP`, `GPUI_X11_SCALE_FACTOR_ENV`, `DISABLE_DIRECT_COMPOSITION`, `SEED`, `LEAK_BACKTRACE`, `GPUI_RUN_UNTIL_PARKED_LOG`; compile-time `TRACK_THREAD_BORROWS`. No config-file or env-var *writes* found.

### Filesystem (artifacts, not state)

- Read: system fonts, image/SVG assets, cursor themes; Linux portal settings/credentials via ashpd/oo7 (credential store is OS-owned, accessed through the keychain APIs).
- Written: nothing durable at runtime by the framework itself (screenshots/tests write into `target/` or temp dirs only). No database, no migrations, no log files (logging goes to stderr/console via `env_logger`/tracing).
