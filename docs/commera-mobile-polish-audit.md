# Commera dashboard — mobile & component polish audit

Read-only pass over all 71 `.vue` files in `dashboard/src`, run 2026-09-04 by five parallel
reviewers (shell/nav, dialogs+import, catalog, orders/analytics, storefront/media).

Scope was deliberately narrow: **no layout rewrites, no new dependencies** — surgical fixes only,
measured against Gameplan and the frappe-ui recipes.

## Ground truth used

| Reference | Location |
|---|---|
| frappe-ui `MobileShell` / `DesktopShell` / recipe sources | `apps/frappe-ui/src/components/`, `apps/frappe-ui/docs/components/recipes` (= ui.frappe.io/recipes) |
| Gameplan implementation | `apps/gameplan/frontend/src` — `MobileLayout.vue`, `AppSidebar.vue`, `MobileMoreMenu.vue`, `MobileListRow.vue`, `utils/useIsMobile.ts` |
| House skill | `~/.claude/skills/frappe-ui/` (SKILL / COMPONENTS / DESIGN / TOKENS) |
| Live comparison site | Gameplan on `polish.localhost` |

### Version skew — read before copying anything

| Where | frappe-ui version |
|---|---|
| `dashboard/node_modules/frappe-ui` — **what actually builds** | **1.0.0-beta.56** |
| bench `apps/frappe-ui` | 1.0.0-beta.55 |
| `gameplan/frontend` — the look reference | **1.0.0-beta.51** |

Gameplan is five versions behind what we compile against. Its *patterns* are the reference; its
API calls are not safe to copy verbatim. Every recommendation below was verified against beta.56's
own exports.

---

## P0 — broken on touch, not merely ugly

### 1. There is no mobile shell at all — `components/AppShell.vue:30`
`DesktopShell` + a 14rem `Sidebar` is the only rendering path, at every viewport.

What actually happens on a phone: frappe-ui's `Sidebar.vue:41` auto-collapses itself below `sm`
via its own internal `useBreakpoints`, so you get a **permanent 3rem icon-only rail** eating
horizontal width on every page, with no way to expand it (no `v-model:collapsed` is wired) and no
bottom tab bar. That is the concrete shape of "the sidebars look very bad on mobile", and it is
the multiplier on every other finding here — the rail eats ~224px of a 375px screen before any
content gets its remainder.

`DesktopShell.md` is explicit that this is not a breakpoint problem:

> Its mobile counterpart is a separate family — `MobileShell` — because the two are different
> navigation models, not one responsive component.

**Fix:** adopt `MobileShell` + `MobileNav`/`MobileNavItem` (all exported in beta.56,
`node_modules/frappe-ui/src/index.ts:96`) and branch the shell the way Gameplan's `App.vue:43`
does — an async swap between `MobileLayout`/`DesktopLayout` driven by `useIsMobile()`. Copy
`gameplan/frontend/src/utils/useIsMobile.ts` verbatim; it is `useMediaQuery('(max-width: 639.98px)')`
from `@vueuse/core`, which already resolves transitively through frappe-ui — **no new dependency**,
though it should be declared in `package.json` for honesty.

Per `DESIGN.md:144`, the mapping is **Sidebar → BottomSheet, persistent nav → MobileNav tabs**: put
Overview / Orders / Products / Customers in `MobileNav`, everything else behind a "More" tab opening
a `BottomSheet`, as Gameplan's `MobileMoreMenu.vue` does.

**Effort:** medium — but every piece is a straight lift from an open reference. Do this first.

### 2. Product photos cannot be deleted on a phone — `components/VariantMedia.vue:68`
The remove (×) control is `opacity-0 group-hover:opacity-100` with no touch or `focus-within`
fallback. Touch has no hover, so a photo can be added and **never removed**.

**Fix:** `opacity-100 sm:opacity-0 sm:group-hover:opacity-100`. **Effort:** trivial.

> Gameplan's own `CoverImage.vue:28` has the identical bug. Do not copy it here — this is one place
> the reference repo is wrong.

### 3. Menu reordering is dead on touch — `components/storefront/NavigationEditor.vue:213`
`Tree`'s `draggable` is native HTML5 drag-and-drop, which does not fire on touch at all (no
pointer/touch handling anywhere in `frappe-ui/src/components/Tree`). The menu tree is read-only for
ordering on mobile.

**Fix:** already solved two files over — `FooterEditor.vue:141` gives every move a `Dropdown`
fallback beside the drag handle. Add Move up/down entries to `rowActions()` (`NavigationEditor.vue:155`),
calling `mutate('move_node', …)` exactly as `onDragEnd` does. **Effort:** small.

### 4. Order detail loses the customer entirely below 1024px — `pages/OrderDetail.vue:152`
`<aside class="hidden w-[19rem] … lg:flex">` hides customer, shipping address, tags and note with
**no fallback rendering anywhere else in the template** — on phone *and* tablet. The order screen
has no way to see who placed the order or where it ships.

**Fix:** restructure the outer flex to `flex-col lg:flex-row` so the aside stacks, or render the
same content into the main `ScrollArea` under `lg:hidden`. Gameplan's two-pane pages stack via
`flex-col md:flex-row`; they never use `hidden … lg:flex` with no substitute. **Effort:** small–medium.

---

## P1 — mobile breakage, mechanical fixes

### 5. Five data tables never collapse on mobile
`Products.vue:157` (`min-w-[54rem]`), `Pricing.vue:153` (`50rem`), `Inventory.vue:105` (`56rem`),
`Collections.vue:59` (`34rem`), `VariantEditor.vue:119` (`30rem`) — each wraps a fixed `min-w` in
`overflow-x-auto`, so a 375px screen renders a 480–900px table you must scroll sideways to read.
`VariantEditor`'s sits inside `PageBody width="narrow"`, so it has even less room.

**Fix:** the recipe ships with the library we already build against —
`node_modules/frappe-ui/src/molecules/list/list.md`:

```
<List class="max-sm:[--list-columns:auto_minmax(0,1fr)_auto]" :columns="[...]">
  <ListHeader class="max-sm:hidden">…</ListHeader>
  <ListCell class="max-sm:hidden">…</ListCell>   <!-- secondary cells -->
```

Keep the name plus the one number that matters. Once it lands, the `overflow-x-auto` wrapper is
unnecessary on mobile. **Effort:** small per page, identical five times.

### 6. `pages/Customers.vue:56` — `List` with fixed-rem columns (≈32rem) has **no** `overflow-x-auto`
wrapper, unlike every sibling (`Dashboard.vue:142`, `Revenue.vue:95`, `Inventory.vue:93`). frappe-ui's
`List` root is a bare CSS grid with no built-in scroll handling, so the whole page overflows
horizontally rather than the table scrolling in place. **Fix:** one wrapper div. **Trivial.**

### 7. `components/import/steps/MapStep.vue:52` — the column-mapping grid has no `overflow-x-auto`,
unlike `ReviewStep.vue:60` and `UploadStep.vue:103`. At 375px it crushes a filename, a `Select` and
a confidence `Badge` into ~340px with no escape — the two most important controls of the import
flow. **Fix:** same wrapper, or `min-w-[28rem]` on the grid. **Small.**

### 8. `components/import/ImportDialog.vue:74` — the footer packs Back, an unshrinkable helper
sentence and up to two action buttons into one flex row; it overflows the dialog's own `px-4` at
375px. **Fix:** `hidden sm:inline` on the helper text. **Small.**

### 9. `components/import/steps/ImagesStep.vue:68` — `TabButtons` is `shrink-0` with three long
labels next to a `min-w-0 flex-1` title, starving the title on a phone. **Fix:**
`flex-col items-start gap-3 sm:flex-row`. **Small.**

### 10. `pages/CustomerDetail.vue:67` — `grid-cols-3 divide-x` stat row with no breakpoint, squeezing
values into ~110px columns. Both equivalents in the same codebase (`Dashboard.vue:87`,
`ReportStats.vue:9`) already use `grid-cols-2 … sm:grid-cols-4`. **Fix:** match them, or better,
extract — three copies of this grid are already drifting. **Trivial.**

### 11. `components/StorefrontPreview.vue:16` — the mobile-device mock is a hardcoded `w-[22rem]`
(352px) that itself forces horizontal scroll on a 320–360px Android screen. Self-inflicted overflow
from the preview widget. **Fix:** add `max-w-full`. **Trivial.**

### 12. Both storefront editors auto-open a 1440px preview iframe — `FooterEditor.vue:14`,
`NavigationEditor.vue:26` default `previewCollapsed = false`, so `ChromePreview.vue:15` loads a
1440px iframe scaled to ~26% on a phone: illegible, and real data weight. **Fix:** default collapsed
below `sm` via the same `useIsMobile()` from finding #1. **Small.**

### 13. `components/AppPageHeader.vue` — header actions never wrap. It renders inside `PageHeader`'s
`flex items-center justify-between`, and `OrderDetail.vue:63` puts three full label+icon buttons
there alongside breadcrumbs (`Customers.vue`, `Orders.vue` put two). No page has any responsive
treatment for header actions — zero hits across the whole tree. **Fix:** fold secondary actions into
the existing "More actions" `Dropdown` below `sm`. **Medium** (shared component + 4 call sites), but
the highest-leverage single fix outside the shell.

### 14. Settings controls hardcode `w-72` — `AppSettingsDialog.vue:184,287`,
`IntegrationConfig.vue:120,126`. `SettingsRow` is a plain `flex items-center gap-8` with no mobile
stacking, so on the full-screen mobile `SettingsDialog` a 288px control plus 32px gap leaves ~55px
for the row label. `SettingsRow` isn't ours to change — narrow at the call site: `w-40 sm:w-72`.
**Trivial.**

---

## P2 — polish and cleanup

15. **`components/AppPageHeader.vue:4` — `backTo` is a dead prop.** Declared, passed by four pages
    (`CustomerDetail.vue:31`, `VariantDetail.vue:89`, `Adjustments.vue:25`, `Pricing.vue:119`), never
    read by the template. `Adjustments.vue` passes only `back-to` and no breadcrumbs, so it renders
    **no back affordance at all**. This is a plain bug, and it becomes load-bearing the moment the
    sidebar stops being permanently on screen. frappe-ui already ships `PageHeaderBackButton`.
    **Trivial.**
16. `components/OrderProgress.vue:60` — the horizontal step ladder crushes labels to a few characters
    at 375px, at the top of every order page. Surgical option: `flex-wrap` below `sm`. **Small.**
17. `components/ListPagination.vue:33` — `Select` + two labelled buttons wrap mid-control at ~360px.
    Icon-only buttons below `sm`. **Trivial.**
18. `components/VariantDialog.vue:102` — actions inline in the default slot instead of Dialog's
    `#actions` slot, which `AddProductDialog.vue:251` already uses for the same job. One dialog,
    two shapes. **Trivial.**
19. The `overflow-x-auto` + `min-w-[Nrem]` wrapper is duplicated verbatim five times (see #5). Once
    #5 lands, extract the remainder rather than retyping it. **Trivial.**
20. `components/import/ImportStepNav.vue:17` — three unguarded items in one baseline row. Survives
    today's strings; no guard if a hint grows. **Nit.**

---

## Deliberately not fixed

- **`VariantImageImport.vue` — hide on mobile, don't adapt it.** Its only interaction is a zip
  drag-drop; the "Choose a zip file" button (line 76) has no `<input type=file>` behind it at all and
  is already a known stub (`VariantEditor.vue:193`). Folder-zip drag-drop has no sane mobile
  equivalent. Hide the trigger under `hidden sm:inline-flex` once the feature is real.
- **Do not route `VariantMedia`'s upload through frappe-ui's `FileUploader`.** It takes a single file
  (`FileUploader.vue:110`) and has no native drag-drop, so it is a worse fit than the current
  `useFileUpload` composable for a multi-file thumbnail grid.
- **No `BottomSheet` inspector for `NavInspector`.** It already stacks correctly below `lg`. A
  sheet-driven inspector would read better but is an interaction change, not a polish fix.

## Verified already correct

- **Tokens: no violations anywhere in 71 files.** `bg-surface-*`, `text-ink-*`, `border-outline-*`
  used consistently; zero raw Tailwind grays, zero hex, zero inline `style=`.
- On the right side of every beta.56 API split: `RichTextField.vue` uses `frappe-ui/editor` (not the
  parked `experimental` TextEditor); all four chart pages import `frappe-ui/charts` (not the parked
  v1 family); `SearchPalette.vue` uses the modern `CommandPalette`.
- `components/product/*` (all 7), `EditableValue.vue`, `AttributeMultiSelect.vue`, `ReportStats.vue`,
  `PageBody.vue`, `ProductDetail.vue`/`VariantDetail.vue` — already mobile-first, nothing to do.
- `UploadStep.vue` correctly uses `useFileUpload` rather than raw fetch, and wraps its table properly.
- `OptionSizeGrid.vue`'s hand-rolled `<table>` is the right call — a colour×size checkbox matrix has
  no `List` equivalent.

## Suggested order

1. **#1 mobile shell** — root cause; everything else is measured against a viewport it is stealing.
2. **#2, #3, #4** — the three things that are genuinely broken rather than ugly. All small.
3. **#5 + #6** — the table collapse, one mechanical recipe applied six times.
4. **#7–#9** — the import/upload flow the owner called out by name.
5. Everything else as budget allows.
