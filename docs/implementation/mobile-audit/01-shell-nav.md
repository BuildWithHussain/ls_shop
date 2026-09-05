# Mobile polish audit — 01 · Shell & navigation

Read-only audit. Files: `App.vue`, `components/AppShell.vue`, `NavSection.vue`,
`AppPageHeader.vue`, `PageBody.vue`, `SearchPalette.vue`, `ListPagination.vue`,
`BulkBar.vue`, `ia/nav.js`, `router.js`, `main.js`. Viewport judged at 375 x 667.

All paths absolute. Reference repos:
`/Users/deathstarconsole/company_projects/frappe/develop/apps/frappe-ui/`,
`/Users/deathstarconsole/company_projects/frappe/develop/apps/gameplan/frontend/src/`.

## Correction to the brief

The brief says "fixed 14rem Sidebar with no mobile collapse". That is not what
happens. `Sidebar.vue:41-47` computes
`isMobile = breakpoints.smaller('sm')` and `shouldCollapse = (isCollapsed ?? isMobile)`.
`AppShell.vue:32` passes neither `v-model:collapsed` nor `disableCollapse`, so at
375px frappe-ui **already** collapses the sidebar to `collapsedWidth` = `3rem` (48px).

That changes the diagnosis and the fix. The bug is not "224px of nav eats the
screen" — it is "the app is permanently stuck in a 48px icon rail it cannot leave,
and the app's own markup inside the sidebar was never written for collapsed mode."
There is no `SidebarCollapseToggle` anywhere in the tree (grep: zero hits outside
the two storefront preview panes).

---

## S1 — [blocker] Sidebar collapses to a 48px rail on mobile with no way out, and no MobileNav

`components/AppShell.vue:30-47`

At 375px: `Sidebar` auto-collapses (Sidebar.vue:41-47), so the whole IA — Overview,
Orders, Customers, Analytics, Catalog, Storefront — becomes an unlabelled 48px icon
strip. No `SidebarCollapseToggle` is rendered, so the labels are unreachable.
`SidebarItem` gives a hover Tooltip (SidebarItem.vue:30-34), which never fires on
touch. Nav rows are `h-7` = 28px tall (SidebarItem.vue:5) — well under a 44px
tap target; `MobileNavItem` uses `min-h-14` = 56px (MobileNavItem.vue:18).

The library's answer is a shell swap, not CSS. Precedent, in order of authority:

- `frappe-ui/src/components/DesktopShell/DesktopShell.vue:60` — the `#sidebar` slot
  is documented "Render it conditionally to hide it on routes that don't need it."
- `gameplan/frontend/src/App.vue:43-51` — `MobileLayout` / `DesktopLayout` as two
  `defineAsyncComponent`s picked by a `computed` off `useIsMobile()`.
- `gameplan/frontend/src/utils/useIsMobile.ts:16-18` — `useMediaQuery('(max-width: 639.98px)')`,
  with the comment explaining why a media query beats a resize listener.
- `gameplan/frontend/src/components/MobileLayout.vue:1-45` — the whole mobile shell
  is 45 lines: `MobileShell` + `#nav` with four `MobileNavItem`s.
- `frappe-ui/docs/components/recipes/TasksMobile.vue:309, 549-580` — same shape.
- `~/.claude/skills/frappe-ui/DESIGN.md:147-148` — "Sidebar → `BottomSheet`;
  persistent nav → `MobileNav` tabs".

**Minimal fix** (additive, no layout rewrite): add `dashboard/src/utils/useIsMobile.js`
copied from gameplan, then in `AppShell.vue` render `MobileShell` + `MobileNav` when
mobile and keep the existing `DesktopShell` block untouched otherwise. Four tabs off
`ia/nav.js`: Overview, Orders, Products, and a "More" that opens the remaining
`sections` in a `BottomSheet` (`BottomSheet` takes `v-model:open` + `title`,
BottomSheet.api.md). The existing `sections` array drives both, so the IA is not forked.

Ranked #1: nothing else on this list matters if the user cannot navigate.

## S2 — [blocker] `back-to` is a dead prop — 7 call sites pass it, the template drops it

`components/AppPageHeader.vue:6` declares `backTo`, and the template (lines 11-18)
never reads it. Seven call sites pass it:

- `pages/OrderDetail.vue:60`, `pages/ProductDetail.vue:115`, `pages/CustomerDetail.vue:31`,
  `pages/VariantDetail.vue:89`, `pages/Pricing.vue:119`, `pages/Adjustments.vue:25`,
  `components/ReportHeader.vue:24`.

On desktop the `breadcrumbs` branch hides the loss. `pages/Adjustments.vue:25` passes
`back-to` with **no** breadcrumbs — that screen has no way back at any width. On mobile,
with S1 fixed, there is no sidebar either, so every detail route is a dead end.

frappe-ui ships the component and the logic: `PageHeader/PageHeaderBackButton.vue:1-9`
(`variant="ghost" size="md" icon="lucide-chevron-left"`) driving
`PageHeader/useHeaderBack.ts:24-33` `hasAppHistory()`, which falls back to the `to`
target when `history.state.back` is null (cold load on a deep link).

**Fix:** render `<PageHeaderBackButton v-if="backTo" :to="backTo" />` as the leading
element of the header. Recipe precedent: `TasksMobile.vue:411-420` puts the back
control in `PageHeaderMobile`'s `#prefix`.

## S3 — [major] Page header overflows horizontally: untruncated title + unshrinkable action cluster

`components/AppPageHeader.vue:14-17`

`<h1 class="text-lg-semibold">` has no `min-w-0 truncate`, and the actions wrapper
`<div class="flex items-center gap-2">` has no `shrink-0`. `PageHeader` renders them
into `flex items-center justify-between` (PageHeader.vue:5) with no wrap and no
overflow guard.

At 375px, `pages/OrderDetail.vue:63-72` puts three controls in `#actions` — "View in
ERP" + `…` + "Fulfil items" ≈ 250px — beside a breadcrumb trail. `ReportHeader.vue:27-38`
puts three more (range dropdown, "Compare", "Export"). Both overflow the ~351px of
usable header width, and the buttons squash before anything truncates.

Note `Breadcrumbs` defends itself (`Breadcrumbs.vue:1-3` `min-w-0` plus an
overflow-to-`…`-Dropdown at line 2). The `v-else` `h1` does not — so the pages that
pass `title` only (Products, Orders, Customers, Collections, Attributes, Inventory,
storefront/*) are the ones that break.

**Fix, two classes:** `min-w-0 truncate` on the `h1`, `shrink-0` on the actions div.
Then apply `DESIGN.md:149` ("Action clusters → one `…` `Dropdown`") on the detail
pages — that is a note for the pages reviewer, not this file.

## S4 — [major] `h-screen` wrapper fights the mobile viewport

`components/AppShell.vue:29` — `<div class="h-screen w-full …">`.

`100vh` on mobile Safari/Chrome is the *large* viewport: it includes the collapsing
URL bar, so the shell is taller than what you can see and the bottom of every page
(including any future `MobileNav`) sits under browser chrome until you scroll.

`~/.claude/skills/frappe-ui/DESIGN.md:60` is explicit: `<MobileShell>` "owns height;
no h-screen wrapper". `MobileShell.vue:2-5` uses `fixed inset-0` for exactly this
reason; `DesktopShell.vue:2` is `h-full` and expects the host to size it.
`ls_shop/www/dashboard.html` already sets `class="h-full"` on `<html>`, `<body>` and
`#app`, so the height chain exists.

**Fix:** `h-full` on the wrapper (or `h-dvh` if you want it independent of the host
page). With S1, the mobile branch is `MobileShell` and needs no wrapper at all.

## S5 — [major] `viewport-fit=cover` is missing, so every safe-area inset in frappe-ui is a no-op

`dashboard/index.html:5` and `ls_shop/www/dashboard.html:5` both ship
`<meta name="viewport" content="width=device-width, initial-scale=1.0" />`.

Without `viewport-fit=cover`, iOS resolves `env(safe-area-inset-*)` to `0px`. That
silently disables:

- `MobileShell.vue:9` — `[@media(display-mode:standalone)]:pt-[env(safe-area-inset-top)]` (notch)
- `MobileNav.vue:4` — `[@media(display-mode:standalone)]:pb-4` plus the home-indicator gap
- `DESIGN.md:155-156` — the pinned-footer recipe this audit recommends in S8

**Fix:** one attribute — `content="width=device-width, initial-scale=1.0, viewport-fit=cover"`
in both files. `ls_shop/www/dashboard.html` is the served copy (see the
"Dashboard stale build" memory), so patch its source template too, not just the build output.

## S6 — [major] `scrollBehavior` is a no-op — the window never scrolls in this app

`router.js:34` — `scrollBehavior: () => ({ top: 0 })`.

Neither shell scrolls the document. `DesktopShell.vue:18` scrolls a `ScrollArea`
viewport; `MobileShell.vue:17-21` scrolls its own `div`. `scrollBehavior` only ever
touches `window`, so navigating from a scrolled Products list into a product detail
keeps the previous scroll offset — the detail page opens mid-way down. Most visible
on mobile, where lists are long and every drill-in is a full-screen change.

frappe-ui registers the real container for you (`DesktopShell.vue:72-85`,
`MobileShell.vue:46`) and exports the handle: `frappe-ui/src/index.ts:138-141` exports
`shellScrollContainer` (note: `scrollShellToTop` is *not* exported, only
`shellScrollContainer` and `useShellScrolled`).

**Fix:** drop `scrollBehavior` and add
`router.afterEach(() => shellScrollContainer.value?.scrollTo({ top: 0 }))` in `router.js`.

## S7 — [major] Nested nav children are clipped in the collapsed rail (and break under RTL)

`components/NavSection.vue:41` — `<div v-show="isOpen(item)" class="space-y-0.5 pl-5">`

Arithmetic at 375px: `Sidebar` 48px, minus `AppShell.vue:33`'s `p-2` (16px) = 32px of
content. `SidebarItem`'s own `pl-2` is 8px and its icon is `size-4` (16px) = 24px, which
just fits. Add this hand-written `pl-5` (20px) and the three Analytics report icons need
44px in a 32px box — `Sidebar.vue:5` is `overflow-x-hidden`, so they are simply cut off.

`SidebarItem` and `SidebarLabel` both collapse their own text (`SidebarItem.vue:45-51`,
`SidebarLabel.vue:4-7`); this indent is app markup that does not participate.

Second defect, same lines: `pl-5` here and `mr-1` at lines 35 and 65 are physical
directions. `data/boot.js:20` sets `document.documentElement.dir = 'rtl'` for Arabic
(and `ls_shop/translations/ar.csv` is in the working tree), and there are **zero**
logical-direction utilities (`ms-`/`me-`/`ps-`/`pe-`) in the entire dashboard. The
nested reports indent from the wrong edge in Arabic.

**Fix:** `ps-5` and `me-1`, and gate the indent on collapsed state — or drop the nested
disclosure on mobile entirely, since S1 moves Analytics into the `BottomSheet`.

## S8 — [major] `BulkBar` scrolls away; it is the one bar that must stay put

`components/BulkBar.vue:15` — `class="mt-3 flex flex-wrap …"`, static, rendered at the
top of the list by `pages/Products.vue`, `Orders.vue`, `Inventory.vue`, `Pricing.vue`.

Selection mode on a 375px screen means scrolling down a long list tapping rows. The
action bar is 600px above by the time you have picked three items, so you scroll back
up to act, losing your place. `PageBody.vue:14`'s `pb-32` makes the trip longer.

`DESIGN.md:155-156` gives the pinned-footer pattern verbatim:
`[@media(display-mode:standalone)]:pb-[env(safe-area-inset-bottom)]` (which needs S5
to actually resolve).

**Fix:** `sticky bottom-0 z-10` + the safe-area padding on line 15. It lives inside the
shell's scroll region, so `sticky` works with no other change.

Also on line 19: `"Rows pick instead of opening while this is on."` — a second
explanatory sentence that wraps the bar to three lines at 375px. Team memory says keep
UI minimal; drop it or make it `hidden sm:inline`.

## S9 — [minor] `ListPagination` is three controls competing for 351px

`components/ListPagination.vue:32-56`

The `ml-auto` group is `flex items-center gap-2` with no wrap of its own: `Select`
`class="w-32"` (128px, fixed) + "Previous" (~100px) + "Next" (~85px) + gaps ≈ 330px.
The parent wraps (line 29), so it survives — as a second full-width row that pushes
the page down on every list screen.

The per-page Select is the least useful of the three on a phone (team memory: keep UI
minimal — no unnecessary fields).

**Fix:** `class="w-32 hidden sm:block"` on the `Select` (line 35), leaving the
count and the two page buttons. Mobile-first, per DESIGN.md's "Section cards go flush:
border/rounding/padding only at `sm:`+" principle applied to controls.

Secondary: `Button` defaults to `size: 'sm'` = `h-7` = 28px (`Button/types.ts:22`).
Previous/Next are navigation controls; frappe-ui's own navigation control,
`PageHeaderBackButton.vue:4`, explicitly overrides to `size="md"`. Worth `size="md"`
here on mobile.

## S10 — [minor] The search palette is a desktop dialog with desktop chrome

`components/SearchPalette.vue:136-147, 231-241`

- Line 147: `CommandPaletteList class="max-h-[21rem]"` (336px) on top of
  `CommandPalette.vue:14`'s own `max-h-[60vh]` (400px at 667px tall). With the software
  keyboard up the visual viewport is ~340px, so `vh` — which tracks the *layout*
  viewport — leaves the footer and the last rows under the keyboard.
- Lines 231-241: the footer is three keyboard hints — ArrowUp/ArrowDown "Navigate",
  Enter "Open", Esc "Close". None of them exist on a touch device, and at
  `gap-4` + `px-4.5` they are the widest row in the palette.
- `CommandPalette.vue:2-8` is a `Dialog size="xl" position="top"`; `Dialog.vue:205-217`
  maps `xl` to `max-w-xl` with `my-8` — a centred card, not the full-height sheet a
  phone wants.

`DESIGN.md:147` and `MailMobile.vue` (imports `BottomSheet` at line 7) both say mobile
overlays are `BottomSheet`.

**Fix, minimal, no rewrite:** `class="hidden sm:flex"` on `CommandPaletteFooter`, and
swap the hardcoded `max-h-[21rem]` for a `max-h-[50svh] sm:max-h-[21rem]` so the list
tracks the *small* viewport when the keyboard is up. The `BottomSheet` variant is the
right end state but is out of scope here.

## S11 — [minor] Two dead menu entries and a hardcoded store name in the workspace header

`components/AppShell.vue:20-25` — "View storefront" and "Log out" are both
`onClick: () => {}`. Tapping either does nothing. On mobile this dropdown is the only
route to Settings once the sidebar is a rail, so a dead "Log out" is the most visible
broken control in the shell.

`components/AppShell.vue:34` — `subtitle="Kirana & Co"` is hardcoded, which contradicts
`ia/nav.js:72-73`'s own comment: "the store it manages is named in Settings."

**Fix:** wire both handlers or remove the rows; read the subtitle from the settings
resource.

## S12 — [minor] `ia/nav.js` imports mock data to compute a nav badge

`ia/nav.js:1-4` — `import { products } from '../data/mock'` and
`const activeProducts = products.filter(...).length`, rendered as the Products count at
line 27. `data/mock.js:1-2` says "Static mock data for the prototype. No backend."

The count is fake, computed once at module load, and never reflects the API the rest of
the app talks to (`useAdminRead('catalog.get_products', …)`, SearchPalette.vue:39).
It also pulls the whole mock module into the shell's initial chunk.

**Fix:** drop the badge, or source it from the same admin API the Products page uses.

## S13 — [minor] `meta.split` disables page scrolling at every width

`components/AppShell.vue:30` — `:scroll="!route.meta.split"`, set by `router.js:6` and
`router.js:10` for OrderDetail and ProductDetail.

`scroll=false` makes the content area fixed-height so inner panes own their overflow
(`DesktopShell.vue:22-31`). Those pages do degrade the right pane
(`pages/ProductDetail.vue:148` — `hidden w-[19rem] … lg:flex`), so nothing overlaps at
375px. But the consequence is that on mobile the page body scrolls inside a nested reka
`ScrollArea` (`ProductDetail.vue:128`, `OrderDetail.vue:82`) rather than natively —
and `MobileShell.vue:12-16` states the reason that is wrong in its own comment:
"a mobile surface wants the platform's own overscroll + inertia". No rubber-band, no
iOS status-bar tap-to-top.

Separately: everything in that `lg:`-hidden aside (the order's customer summary, the
product's sidebar) is unreachable below 1024px. That is a pages-group finding; flagging
it here because the shell flag is what enables the layout.

**Fix at this file:** `:scroll="!route.meta.split || is_mobile"` once S1 lands
`useIsMobile`.

---

## Legacy-API / token sweep (clean)

Grepped all eleven files for `ListView`, `TextEditor`, `Autocomplete`,
`createResource` / `createListResource` / `createDocumentResource`, raw
`bg-gray-*` / `text-gray-*` / `border-gray-*` / `bg-white`, and inline `style="…"`.
**Zero hits.** The shell uses semantic tokens throughout, `useCall`-family data
fetching (`useAdminRead`), `v-model:open` on overlays (SearchPalette.vue:137), and
lucide string-class icons. This half of the codebase is on the modern API.

One cross-cutting gap, not mobile-specific: **zero `__()` calls** in the entire
dashboard, while `ls_shop/translations/ar.csv` ships and `data/boot.js:20` sets
`dir="rtl"`. Every string in `AppShell.vue:21-24`, `ia/nav.js:8-33`, `BulkBar.vue:17-19`
and `ListPagination.vue:37-41` is hardcoded English. Worth its own ticket.

---

## Ranked by user-visible pain

| # | Severity | Finding |
|---|---|---|
| S1 | blocker | 48px unlabelled rail, no MobileNav, no way to expand |
| S2 | blocker | `back-to` dead prop — 7 call sites, no back button anywhere |
| S3 | major | Header overflows: untruncated `h1`, unshrinkable actions |
| S4 | major | `h-screen` vs. the mobile URL bar |
| S5 | major | Missing `viewport-fit=cover` kills every safe-area inset |
| S6 | major | `scrollBehavior` no-op — detail pages open mid-scroll |
| S7 | major | `pl-5` clipped in the rail; physical direction breaks RTL |
| S8 | major | `BulkBar` scrolls away from the selection it describes |
| S9 | minor | Pagination row overflows to a second row |
| S10 | minor | Palette: `vh` cap under the keyboard, desktop-only footer |
| S11 | minor | Dead "Log out" / "View storefront", hardcoded store name |
| S12 | minor | Mock data imported into the shipped nav |
| S13 | minor | `meta.split` forces nested `ScrollArea` on mobile |
