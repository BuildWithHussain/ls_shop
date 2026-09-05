# Mobile polish audit — 05 Storefront editors & preview

Read-only audit. Viewport under test: 375 x 667. No files were edited.

Files in scope:
- `dashboard/src/pages/storefront/Navigation.vue`
- `dashboard/src/pages/storefront/Pages.vue`
- `dashboard/src/pages/storefront/Theme.vue`
- `dashboard/src/components/storefront/NavigationEditor.vue`
- `dashboard/src/components/storefront/NavInspector.vue`
- `dashboard/src/components/storefront/FooterEditor.vue`
- `dashboard/src/components/storefront/ChromePreview.vue`
- `dashboard/src/components/StorefrontPreview.vue`

## Headline

The editor-beside-preview layouts are actually the *least* broken thing here — `NavigationEditor.vue:211`
(`lg:flex`), `NavInspector` `aside` (`lg:w-[24rem]`) and `Theme.vue:53` (`lg:flex`) all already stack at
`< lg`. The real damage is elsewhere:

1. **Nav reordering is impossible on touch** — `Tree` drag is native HTML5 DnD, which no mobile browser fires.
2. **Every row action is a 20 px tap target** (`!size-5` overrides on the frappe-ui `Button`).
3. **`ChromePreview` renders a 1440 px frame at ~0.23 scale** — a 325 x 131 postage stamp that eats 420 px of a 667 px screen.

Ranked by user-visible pain below.

---

## P1 — blocker — nav tree cannot be reordered on a phone at all

`components/storefront/NavigationEditor.vue:213` — `<Tree draggable :move="canDrop" @drag-end="onDragEnd">`
is the **only** way to reorder or re-nest a menu entry. `rowActions()` (`:155-170`) offers add-inside /
hide / delete but no move.

frappe-ui's `Tree` implements drag with the native HTML5 API:
`frappe-ui/src/components/Tree/TreeItem.vue:27-32` — `:draggable="…"`, `@dragstart`, `@dragover`,
`@dragend`. Mobile Safari and Chrome Android do not synthesise `dragstart` from touch. There is also no
keyboard reorder — `useTreeKeyboard.ts` only navigates and expands. So on a phone the menu is **read-only**.

The in-house precedent for the fix already exists one file over:
`components/storefront/FooterEditor.vue:171-210`, `linkActions()` gives Move up / Move down / Move to
previous column / Move to next column as `Dropdown` items and calls the same server mutations. FooterEditor
is fully usable by thumb because of it.

**Minimal fix** (no layout change): extend `rowActions(node)` in `NavigationEditor.vue:155` with three
entries that reuse the existing `mutate('move_node', …)` call already in `onDragEnd` (`:51-61`):
`Move up` / `Move down` (same parent, `target_index ± 1`) and `Move out one level` (`to_parent` = the
grandparent). No new endpoint, no new component — the same shape as `FooterEditor.moveLinkWithinColumn`
(`:19-28`) and `moveSection` (`:42-50`).

Also `NavInspector.vue:115-116` tells the user *"Drag entries to reorder them, or drop one onto another to
nest it."* On touch that sentence is a lie. Once the menu actions exist, the copy should name them.

## P2 — blocker — 20 px tap targets on every row action

- `NavigationEditor.vue:235` — `<Button variant="ghost" class="!size-5" aria-label="Entry actions">`
- `FooterEditor.vue:256` — add-a-link button, `class="!size-5"`
- `FooterEditor.vue:268` — column actions, `class="!size-5"`
- `FooterEditor.vue:299` — link actions, `class="!size-5"`

`!size-5` is 20 x 20 px. Given P1, the ellipsis dropdown is the *entire* interaction surface for a menu
entry or footer link on mobile; at 20 px it is under half the 44 px touch minimum and sits 4-8 px from its
neighbours (`FooterEditor.vue:296` `gap-1`).

frappe-ui already sizes icon buttons correctly — `Button.vue:206-212`: `sm` 28 px, `md` 32 px, `lg` 40 px.
The `!size-5` override is fighting the component, which is exactly what PHILOSOPHY P10 (no class-injection
to restyle a component) warns against.

**Minimal fix**: delete the four `class="!size-5"` overrides and pass `size="md"` (32 px, plus the ghost
button's own hit padding). If the desktop row rhythm must stay tight, `class="size-5 sm:size-5"` is not the
answer — use `size="md" class="sm:size-7"` or leave desktop at the 28 px default; 28 -> 32 is a 4 px shift
that will not disturb the tree row.

Related: `frappe-ui/src/components/Tree/Tree.vue:302` sets `--tree-row-height: 32px`. Tree.md is explicit
that this is the supported override path — *"Row height and indentation are CSS variables — override them in
CSS rather than through props"*. A one-line scoped rule on the `Tree` in `NavigationEditor.vue:213`
(`--tree-row-height: 44px` under `@media (max-width: 639px)`) brings the label button (`:215-226`) and the
expand chevron to a thumb-sized row without touching the markup.

## P3 — major — ChromePreview is an illegible 0.23x postage stamp that still costs 420 px

`components/storefront/ChromePreview.vue:15` — `const FRAME_WIDTH = 1440`, hard-coded, with
`scale = min(1, stageWidth / FRAME_WIDTH)` (`:44`).

At 375 px: `PageBody` `px-3` (`components/PageBody.vue:14`) leaves 351, ChromePreview's own `px-3` (`:83`)
leaves 327, minus the stage border ≈ **325 px** -> `scale ≈ 0.226`. Storefront body text at 16 px renders at
**3.6 px**. For the header preview `frameHeight = contentHeight + DROPDOWN_HEADROOM (460)` (`:50`), so the
stage is roughly 325 x 130 — a grey smear. And it is expanded by default (`NavigationEditor.vue:26`,
`FooterEditor.vue:14` both `ref(false)`), so it costs real estate up to `MAX_STAGE_HEIGHT = 420` (`:17`) on a
667 px screen for zero information.

**Minimal fix, two lines, no layout change:**
1. Start collapsed on narrow viewports — `const previewCollapsed = ref(window.innerWidth < 640)` in both
   editors, or better, drive it from a shared `useIsMobile()` (see P6). The collapse affordance already
   exists (`ChromePreview.vue:71-76`) and reads *"Show navigation preview"*, so nothing is hidden from the
   user — they opt in.
2. Make `FRAME_WIDTH` a prop with a mobile default, e.g. `420`. The storefront chrome is responsive, so a
   420 px frame at `scale ≈ 0.77` is legible **and** is the more honest preview on a phone: it shows the
   customer's mobile navbar, which is what a shop owner editing from a phone wants to see. This is a
   `computed` swap of one constant, not a rewrite.

Note `DROPDOWN_HEADROOM = 460` (`:20`) is tuned for a desktop mega-menu that does not exist in the mobile
chrome — with a mobile `FRAME_WIDTH` the headroom should drop too, or the stage is mostly blank.

## P4 — major — NavInspector selection is invisible on mobile (BottomSheet is the precedent)

`NavigationEditor.vue:247-251` — the inspector is an `aside` that goes `w-full` below `lg`. Structurally
fine, but behaviourally broken: tapping a tree row (`:223` `@click.stop="selectedName = node.name"`) fills a
form that is *below the fold* — under the whole tree, and above `ChromePreview`. Nothing on screen changes.
The user taps, sees nothing, taps again.

The canonical answer is the recipe pair. `docs/components/recipes/FilesMobile.vue:696` surfaces the desktop
row's detail/overflow panel as a `BottomSheet` rather than as a stacked pane, and `FilesMobile.vue:664` does
the same for the desktop sidebar. `BottomSheet.md` states the rule outright: *"Use `Dialog` on desktop and
`BottomSheet` on mobile. They are separate components rather than one responsive component."* Gameplan uses
exactly this split — `gameplan/frontend/src/components/RevisionsDialog.vue:2` (`<Dialog v-if="!isMobile">`)
with `:141` `useMediaQuery('(max-width: 1024px)')`.

**Two options, cheapest first:**
- **(a) 3 lines, no new dependency** — keep the stacked `aside`, add `id="nav-inspector"` and, in the tree
  row click handler, `document.getElementById(...)?.scrollIntoView({ behavior: 'smooth', block: 'start' })`
  when `window.innerWidth < 1024`. Honest, ugly, works.
- **(b) ~12 lines, recommended** — wrap `<NavInspector>` in a `BottomSheet` when mobile:
  `<BottomSheet v-if="is_mobile" :open="Boolean(selectedName)" :title="selected?.label" @update:open="v => !v && (selectedName = null)"><NavInspector … /></BottomSheet>`, and keep the `aside` under `v-else`.
  `NavInspector` needs no change — it is already a self-contained scrolling column (`:132` `overflow-y-auto`)
  with its own sticky save footer (`:212-214`), which is precisely the content rhythm a sheet wants.

Option (b) needs a `useIsMobile()`; see P6.

## P5 — major — `StorefrontPreview` mobile frame overflows the 375 px viewport

`components/StorefrontPreview.vue:16` — `:class="device === 'mobile' ? 'w-[22rem]' : 'w-full'"`.

`22rem` = 352 px, fixed. At 375 px: `PageBody px-3` -> 351, minus `StorefrontPreview`'s own `p-4` (`:13`)
-> **319 px available**. The 352 px child overflows by 33 px, and because the ancestor chain has no
`overflow-x` clamp, the whole page gets a horizontal scrollbar the moment `device` is switched to Mobile on
`Theme.vue:119-126`. Ironic failure mode: the *mobile* preview is the one that breaks mobile.

**Minimal fix**: `'w-[22rem] max-w-full'`. One class.

Secondary, same file: `StorefrontPreview.vue:23` hides the nav strip with `hidden sm:flex`, which keys the
mock nav off the **dashboard** viewport rather than off the `device` prop. On a phone, the Desktop preview
also loses its nav — so the desktop/mobile toggle shows two near-identical mocks. Should be
`:class="device === 'mobile' ? 'hidden' : 'flex'"` to follow the prop, not the browser.

## P6 — major — no `useIsMobile` in the codebase, and no `@vueuse/core`

`grep` across `dashboard/src/` finds zero `useIsMobile` / `useMediaQuery` / `BottomSheet` / `MobileShell`;
`AppShell.vue:30` mounts `DesktopShell` unconditionally. `dashboard/package.json` has no `@vueuse/core`.

Every fix above that is conditional on viewport (P3.1, P4b) needs one. frappe-ui stopped exporting
`useIsMobile`/`useScreenSize` in 1.0.0, so gameplan keeps a 3-line local:
`gameplan/frontend/src/utils/useIsMobile.ts:16` — `useMediaQuery('(max-width: 639.98px)')`, with the reason
documented in the docstring (a media query fires only on breakpoint crossings; a resize listener wakes every
consumer per frame).

**Minimal fix**: add `@vueuse/core` and copy that file to `dashboard/src/data/useIsMobile.js` (house naming:
`use_is_mobile` return value, `useIsMobile` composable name per the `useX` rule). This is the enabling change
for the whole group, not just this file set.

## P7 — minor — FooterEditor kanban scrolls horizontally inside a vertically scrolling page

`FooterEditor.vue:237` — `flex items-start gap-3 overflow-x-auto` with `w-72` (288 px) columns at `:241`.
At 375 px exactly one column is visible with ~63 px of the next peeking, so the affordance *is* there and
the columns themselves are fully usable by thumb (all moves are `Dropdown` items — see P1). This is the
normal kanban trade-off and I would not rewrite it.

Worth noting only that the nested horizontal scroller sits inside the `DesktopShell` vertical scroller;
diagonal flicks will feel sticky on iOS. If it becomes a complaint, `snap-x snap-mandatory` on the row and
`snap-start` on the column is a two-class fix that makes the paging deliberate.

## P8 — minor — `Pages.vue` horizontal table is fine, but it is mock data

`pages/storefront/Pages.vue:33-56` already does the right thing: `overflow-x-auto` wrapper +
`min-w-[38rem]` on the `List`, five columns with explicit widths, `row-height` floored at 44
(`:36` `Math.max(ia.density, 44)`) — the only place in this file group that respects a touch minimum.

Two notes: the data comes from `data/mock` (`:9`), and `Add page` (`:24`) is inert. Not a mobile issue, but
this screen will need a re-audit once it is wired.

## P9 — minor — `Theme.vue` dead colour constants and hardcoded hex

`pages/storefront/Theme.vue:14-19` — `ACCENTS` maps four names to hex values, but only
`Object.keys(ACCENTS)` is ever read (`:29`). The hex values are never rendered — there is no swatch grid,
just a `Select` of capitalised keys. So this is dead data *and* hardcoded colour literals in one constant.
Either render the swatches (a `Select` with `#prefix` colour dots) or drop the values and keep a plain array.

Everything else in `Theme.vue` is clean: `Select`/`Slider`/`Switch`/`TabButtons` are all frappe-ui, tokens
are all semantic (`bg-surface-gray-2`, `text-ink-gray-5`, `rounded-4/5`), no raw `gray-*`, no inline styles.
The `lg:flex` -> stacked control column at `:53-54` is the correct degradation and needs no change.

## P10 — minor — house-law drift, systemic across the group

Flagged once rather than per line, because fixing it is a mass rename, not mobile polish:

- **snake_case (project CLAUDE.md + team memory).** These files are camelCase throughout —
  `previewCollapsed`, `itemGroupOptions`, `moveLinkWithinColumn`, `linkDialogSection`, `onDragEnd`,
  `groupCount`, `countEntries`. Should be `preview_collapsed`, `item_group_options`, etc.
- **Single-letter parameters** violate the no-abbreviation rule: `Theme.vue:29` `(k)`, `:30` `(f)`,
  `:36` `(w)`, `:39` `(t)`; `StorefrontPreview.vue:8` `ring(part, highlight)` is fine but `n`/`m` at
  `:39`/`:53` are loop counters in `v-for` — acceptable there, but `k`/`f`/`w`/`t` are not.
- **`__()` is absent everywhere.** Every user-facing string in these eight files is a bare English literal —
  including the toasts (`NavigationEditor.vue:74,116,132,146`) and the dialog copy (`:126-134`). Notable
  because `ChromePreview.vue:22-25` offers an Arabic *storefront* preview while the editor chrome around it
  cannot be translated, and `ls_shop/translations/ar.csv` exists.
- `ChromePreview.vue:36-42` hand-rolls a `ResizeObserver` where `useElementSize` from `@vueuse/core` does
  the same job — worth folding in if P6 lands and the dependency is already there.

Nothing here is a raw-`gray-*` or `bg-white` violation — token discipline in this group is genuinely good.

---

## Recommendation: reachable-but-degraded, not desktop-only

Do **not** put a "please use a desktop" wall on these screens. Reasoning:

- **Navigation and Footer are 90 % there.** Every mutation is already a `Dropdown`/`dialog.prompt` flow that
  works perfectly by thumb: add, rename, hide, delete, edit link, and (in FooterEditor) move. The panes
  already stack. The only genuinely touch-hostile mechanism is `Tree` drag (P1), and the fix is menu items
  we already ship in the sibling component — a couple of dozen lines, not a rewrite.
- **The realistic mobile job is small and urgent, not structural.** A shop owner on a phone is hiding a
  broken menu link, fixing a typo in a footer label, or unhiding a column before a sale. Those are exactly
  the operations that work today. Blocking the screen to protect them from a reorder they may not need is a
  worse trade than letting them in.
- **Theme already degrades correctly** and has no drag or fixed-width dependency once `StorefrontPreview`
  gets `max-w-full` (P5). A desktop-only gate there would be pure loss.
- **`Pages` is a plain list** and needs nothing.

What *should* be explicitly degraded is the **preview**, not the editor: `ChromePreview` collapsed by
default under `sm` (P3), with the existing "Show navigation preview" button as the opt-in. That is the one
surface that genuinely cannot be made useful at 375 px, and it already has a first-class collapse
affordance. Degrade the thing that can't work; keep the things that can.

### Cheapest honest patch set, in order
1. P2 — drop the four `!size-5` overrides, pass `size="md"`. *(4 lines, no risk)*
2. P5 — `max-w-full` on `StorefrontPreview.vue:16`; drive `:23` off the `device` prop. *(2 lines)*
3. P1 — Move up / Move down / Move out one level in `rowActions`, reusing `mutate('move_node')`; fix the
   `NavInspector.vue:115` copy. *(~25 lines, mirrors FooterEditor)*
4. P6 + P3.1 — add `@vueuse/core` + `useIsMobile`, start `ChromePreview` collapsed under `sm`. *(1 dep, ~6 lines)*
5. P2b — `--tree-row-height: 44px` under `sm` on the `Tree`. *(1 CSS rule)*
6. P4b — `BottomSheet` around `NavInspector` on mobile. *(~12 lines; do last, it is the only one that
   touches structure)*

Items 1-3 are worth doing regardless of the mobile question — they are correctness bugs on desktop touch
laptops too.
