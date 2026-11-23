# D. Text, Platform & Resources

This guide owns text and editor interchange, host selection and native roles,
and host/resource capabilities. [B](B-runtime-interaction-state.md) owns
normalized dispatch; [C](C-layout-rendering.md) owns geometry and rendering.

## Shaping, caret and raster

**Reconstruction requirement.** Accept UTF-8 text, font size and ordered
style runs whose byte lengths cover the source at scalar boundaries.
Shape by paragraph with direction and bidi scopes, and rebase local runs,
inline objects and fragments into document indices. Keep hard breaks and
trailing empty rows. Wrap width controls soft breaks; alignment width
positions output independently. With clamp budget `n`, take at most
`max(n−1, 0)` width-limited breaks in the paragraph, then emit the remaining
content without a width limit. Charge produced visual rows to later
paragraphs without deleting hard breaks. Clamp is neither a total row cap
nor an ellipsis rule. Inline atomic boxes use baseline alignment by default;
the measured text-truncation path in `Div` bypasses its text truncation
when such boxes are present.

Return visual rows, paint fragments and logical source ranges. A cluster
hit identifies the cluster start, including whitespace; closest caret
uses edges and affinity (RTL visual left maps to logical end). Past-source
indices yield no position; off-row points report their appropriate edge
with the outside indication. Resolve the descriptor family, then its
ordered fallbacks, then configured fallback families; try generic system UI
before its named substitute. No resolved family is an error. Keep selected
face, variation and glyph identity across raster and atlas insertion;
surface raster/atlas failures rather than assuming successful insertion.

**Implementation choice — provider boundaries.** Share shaping cache entries
only across identical relevant inputs; catalog changes invalidate dependent
data. Parley, platform font discovery and raster libraries may be replaced.
Use fixed font fixtures; installed fonts and final pixels are not portable
oracles. For the malformed-input policy see [E](E-implementation-verification.md#defect-dispositions).

**UNRESOLVED — host font metrics after catalog enrichment.** The final
audit observed a changed ascent after system fonts loaded, despite the
registered face ID remaining stable in the checked fixture. An isolated,
empty Fontconfig catalog did not reproduce the failure. Do not require
metric stability under arbitrary catalog changes. This does not block
fixed-font shaping; see the [font audit ledger](../verification/final-verification.md#font-catalog-follow-up)
for scope and the next comparison.

**Evidence:** [contracts C28–C31](../findings/behavioral-contracts.md#apisdk--text-behavior-b2e)
and [protocols S9](../findings/protocols-and-state.md#s9-document-shaping-and-inline-measurement);
`crates/gpui/src/text_system/line_layout.rs:710-813,1123-1194`,
`crates/gpui_ce_parley/src/text_system.rs:1469-1599,1601-1750,2059-2148,2431-2448`,
`crates/gpui/src/elements/div/inline.rs:72-127`, `crates/gpui/src/window.rs:4892-4901`.

## Editor and IME boundary

**Reconstruction requirement.** The current paint-registered input
handler receives marked and committed edits independently of shortcuts.
Ranges use UTF-16 code units, not shaping byte offsets. Snap an interior
scalar offset to its end and clamp beyond source length; that is not
grapheme snapping. Keep selection and optional replacement ranges
distinct, and route composition only within the applicable focus boundary.
Do not infer a universal composition ordering from one host.

**Implementation choice — reference adapter routes.**

| Host | Observed carrier and mapping |
|---|---|
| macOS | AppKit window / `NSTextInputClient`: extract text from attributed input; insert, mark and unmark with optional range arguments. |
| Windows | Native message loop / `WM_IME_COMPOSITION`: process result before composition, convert text and optional caret range. |
| Wayland | Text-input-v3: stage preedit and handle at `Done`; commit clears composing. The one-byte commit path synthesizes a keydown; other commits go through insertion. |
| X11 | Optional XIM context stages preedit, commit and forwarded-key events; not every XIM feedback field is passed through. |
| Web | Browser composition events mark on update; commit on end only if marked text remains, then unmark and reconcile the input mirror. |

**Evidence:** [protocols S10](../findings/protocols-and-state.md#s10-platform-to-editor-text-input);
`crates/gpui/src/input.rs:7-98`, `crates/gpui/src/window.rs:3270-3295`,
`crates/gpui_macos/src/window.rs:447-477,3482-3528`,
`crates/gpui_windows/src/events.rs:156-157,737-779`,
`crates/gpui_linux/src/linux/wayland/client.rs:2043-2109`,
`crates/gpui_linux/src/linux/x11/xim_handler.rs:32-140`,
`crates/gpui_web/src/events.rs:1108-1154`.

## Host selection and native roles

**Reconstruction requirement (Linux/FreeBSD adapters).** Select explicit
headless first, then headless if `ZED_HEADLESS` is present. Otherwise try
the first compiled-in backend with its nonempty selector — Wayland via
`WAYLAND_DISPLAY`, then X11 via `DISPLAY` — or select headless. Selection
does not probe connectivity or promise fallback after failed construction.
X11 scale distinguishes auto (unset/empty), `randr`, and a positive normal
numeric value. Malformed input panics on the reached reference path;
[E](E-implementation-verification.md#defect-dispositions) owns the departure.

**Reconstruction requirement.** An anchored native popup uses an existing
parent and does not degrade into an ordinary window. On the inspected
Wayland path, a nonzero press serial enables requesting a configured
grab; it does not prove a grant. Stage positive popup configure size,
apply at surface configure and acknowledge its serial. Do not treat
reposition completion alone as geometry. Dismiss through normal close.
Layer surfaces use distinct compositor capability, output, role,
size/anchor and keyboard settings; missing capability is unsupported.

**Implementation choice — frame sources.** Reference paths include
macOS display link, X11 refresh timer, Wayland frame callbacks, Windows
`WM_PAINT` and web `requestAnimationFrame`. These are trigger mechanisms,
not a guarantee of matching request, draw or display intervals. See
[E](E-implementation-verification.md#unresolved-runtime-behavior) for measured
evidence and remaining questions.

**Evidence:** [contracts C37–C38](../findings/behavioral-contracts.md#c37-anchored-platform-popups)
and [protocols S5/S11](../findings/protocols-and-state.md#s5-wayland-anchored-popup-configure-and-dismissal-contracts-cf1);
`crates/gpui/src/platform.rs:107-135`, `crates/gpui_linux/src/linux.rs:27-55`,
`crates/gpui_linux/src/linux/x11/client.rs:1983-2017,2535-2579`,
`crates/gpui_linux/src/linux/wayland/window.rs:162-205,1128-1179,1396-1420`,
`crates/gpui_linux/src/linux/wayland/client.rs:1074-1098,1481-1497,1644-1666`,
`crates/gpui_macos/src/display_link.rs`, `crates/gpui_windows/src/events.rs:109,335`,
`crates/gpui_web/src/window.rs:350-359,415-423`.

## Assets, accessibility and host-owned data

**Reconstruction requirement.**

| Boundary | Inputs, state and observable failure |
|---|---|
| Image | Asset bytes or loader result → pending, ready or failed. Loading/error builders are optional. For retained state, pending may show loading UI after 200 ms; its timer invalidates rather than retries. A configured fallback replaces failed content. |
| Accessibility | Per-frame semantic tree with stable node identities and optional bounds; forcing requests a tree-producing frame even without a client where supported. Missing snapshot is not an empty successful tree. On the inspected native action path, run a node listener before built-in click/focus/blur. |
| Clipboard | Host-owned typed strings, image data or paths. Metadata and a matching text hash are not proof of writer identity. Web synchronous reads return no item; async reads expose supported results or rejection. Writes have no framework acknowledgement; a discarded web promise does not prove success. |
| Credentials | Caller-supplied lookup key, username and secret bytes; host store decides capability and permissions. Web read returns no item, write/delete unsupported. The URL-like key is not authorization. Apply the secret-handling choices in [E](E-implementation-verification.md#defect-dispositions). |
| State and formats | Action names accept typed/JSON params; key bindings and UI state are in memory. Asset bytes and host clipboard/keychain formats do not imply a GPUI-owned keymap file, database, migration or replay schema. |

**Evidence:** [contracts C32–C36](../findings/behavioral-contracts.md#c32-image-loading-and-fallback),
[protocol storage notes](../findings/protocols-and-state.md#persistent-schema-notes);
`crates/gpui/src/elements/img.rs:31-38,382-423,537-552`,
`crates/gpui/src/window.rs:7203-7286`, `crates/gpui/src/app.rs:1740-1850`,
`crates/gpui/src/platform.rs:3446-3461,3846-3862`,
`crates/gpui_web/src/platform.rs:556-645`,
`crates/gpui/src/action.rs:405-430`, `crates/gpui/src/keymap/binding.rs:30-101`.
