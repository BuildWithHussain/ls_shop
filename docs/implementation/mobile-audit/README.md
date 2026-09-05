# Mobile polish audit — ls_shop dashboard

Six parallel read-only passes over all 71 `.vue` files in `dashboard/src`, measured against the
ui.frappe.io recipe sources vendored at `apps/frappe-ui/docs/components/recipes/` (10 matched
Desktop/Mobile pairs) and against gameplan as a production reference.

Reference viewport **375 × 667**. `PageBody` is `px-3`, so usable width is **351px**; inside a
`Dialog` it is **311px**.

No files were edited. Per-group detail:

| File | Group |
|---|---|
| `00-skill-freshness.md` | frappe-ui version + house skill staleness |
| `01-shell-nav.md` | App shell, sidebar, page header, pagination, bulk bar |
| `02-dialogs.md` | Dialogs, the import wizard, settings panels |
| `03-lists.md` | 9 list pages, dashboard, 3 analytics pages |
| `04-detail-editor.md` | Detail pages, product/variant editor |
| `05-storefront.md` | Storefront editors + preview |

## Verdict

The codebase is **well built and consistently styled** — the problem is narrow and mechanical.

Verified clean across all six groups: zero raw `bg-gray-*`/`text-gray-*`/hex colours, zero
inline `style=`, zero legacy APIs (`ListView`, `TextEditor`, `Autocomplete`, `createResource`),
semantic tokens throughout, `v-model:open` on overlays, `useCall`-family data fetching.

The responsive layer was simply never written. **49 of 71 files have no `sm:`/`md:`/`lg:` class
at all**; the whole app contains ~33 responsive utilities, fewer than gameplan's single
`CommentsArea.vue` (55).

## Root cause

`AppShell.vue:30` mounts `DesktopShell` unconditionally. There is no `MobileShell`, `MobileNav`,
`BottomSheet` or `Rail` anywhere in the app.

Correcting a common assumption: the sidebar **does** collapse below `sm` on its own —
`Sidebar.vue:41-47` auto-collapses when `v-model:collapsed` is unset, which is our case. The bug
is that it collapses to a **48px icon rail with no toggle to escape it**, and `SidebarItem`
tooltips are hover-only so labels are unreachable on touch. The fix is a mobile shell branch,
not "make the sidebar responsive".

There is **no official breakpoint composable** — frappe-ui deliberately removed
`useIsMobile`/`useScreenSize` in 1.0.0 (`changelog.md:1842-1846`); apps own the media query.
Gameplan's `frontend/src/utils/useIsMobile.ts` is a 19-line `useMediaQuery` wrapper and is the
copy target. `@vueuse/core` is already a transitive frappe-ui dependency but is **not** declared
in `dashboard/package.json` — declare it.

## Blockers — data or tasks unreachable on a phone

1. **Order + product context panes render nowhere below 1024px.**
   `OrderDetail.vue:152` and `ProductDetail.vue:150` are `hidden w-[19rem] … lg:flex`. Customer
   name, phone, email and shipping address are not on the page at all. `ProductSummaryPanel` is
   already a component — fixing that one is a single line.
2. **Ten list pages are horizontal scrollers**, `min-w-[34rem]`–`min-w-[56rem]` in 351px, with
   `ListHeader` inside the scroller so dragged-right columns are unlabelled.
   `Customers.vue:56` is worse: the only list with **no** `overflow-x-auto` and no `min-w`, so
   32rem of fixed tracks drags the page and sidebar sideways.
3. **Every gateway credential field is unusable**, so payments setup cannot be completed on a
   phone. Partly upstream: `SettingsBody.vue:6` and `SettingsHeader.vue:3` hardcode
   `px-[4.4rem]` with no breakpoint (confirmed in installed beta.56), leaving 235px; ls_shop
   then stacks `w-72`/`w-64` on top. **File the padding bug upstream**; fix ours with
   `w-full sm:w-72`.
4. **Import wizard is unadvanceable.** `ImportDialog.vue:51` `max-h-[calc(100vh-8rem)]` puts the
   footer holding the only Continue button under the mobile URL bar.
   `SettingsDialog.vue:14` already solves this exact problem with `h-[100dvh] … sm:…`.
   `MapStep.vue:54` gives each mapping column ~79px, and its step nav is six 4px tap targets.

## Themes

- **Hover-only affordances die on touch** — exactly two, both load-bearing:
  `EditableValue.vue:52` (the only inline-edit hint in the variant matrix) and
  `VariantMedia.vue:69` (variant photos cannot be removed at all on a phone).
- **Drag-only interactions die on touch** — `NavigationEditor.vue:213` uses frappe-ui `Tree`
  with native HTML5 DnD, which never fires from touch, so the storefront menu is read-only on a
  phone. The sibling `FooterEditor.vue:171-210` already ships menu-based moves; copy that.
  `NavInspector.vue:115` tells the user to drag — false on touch.
- **Tap targets** — `!size-5` (20px) overrides in 4 places, 28px sidebar rows, 4px step nav,
  13px checkboxes. Note: **no touch-target rule exists upstream to cite**; we'd author it.
- **Action clusters overflow the header** — `AppPageHeader.vue:15` has no wrap/shrink and its
  `h1` no `min-w-0 truncate`; `ReportHeader.vue:27` puts ~500px of controls in a 351px header.
- **Dead prop:** `AppPageHeader.vue:6` declares `backTo` and never renders it. **Seven** call
  sites pass it. `Adjustments.vue:25` has no breadcrumbs either — no way back at any width.

## Sequenced plan

**Phase 0 — unblock (do first).** Update the house skill; declare `@vueuse/core`; copy
gameplan's `useIsMobile`; add `viewport-fit=cover` to both `index.html` and `www/dashboard.html`
(without it iOS resolves `env(safe-area-inset-*)` to `0px`, silently disabling every safe-area
fix below).

**Phase 1 — the two systemic fixes.** These are most of the win.
- Mobile shell branch in `AppShell.vue` beside the untouched `DesktopShell` block.
- Collapse the ten lists via `max-sm:[--list-columns:…]` + `max-sm:hidden`. This is the
  **officially documented** mechanism (`list.md:80-100` publishes `--list-columns` as a public
  styling hook), not a workaround — two classes per list, no custom CSS.

**Phase 2 — surgical.** The `lg:hidden` context panes; `w-full sm:w-*` on settings and dialog
fields; `100vh` → `100dvh`; `AppPageHeader` truncate/shrink + render `backTo`; hover-only →
always-visible under `sm`; drop the `!size-5` overrides; menu-based moves in `NavigationEditor`.

**Phase 3 — cleanup.** Dedupe the KPI strip (`Dashboard.vue:87` clones `ReportStats.vue:9` and
already computes the right shape); one row-height helper instead of three idioms; `virtual` on
the three 200–500 row lists; collapse `ChromePreview` under `sm`.

## Skill action — do this before writing any code

Our `~/.claude/skills/frappe-ui/` is **byte-identical** to the copy vendored in this frappe-ui
checkout (all five files, `diff` clean) — a frozen upstream snapshot, not a house artifact.
Upstream has since restructured it (`SKILL.md` + `CORE.md` + `DATA.md` + `SETUP.md` + `evals/`).

Verified directly against our installed source, our skill documents APIs that do not exist:

| Skill teaches | Reality |
|---|---|
| `dialog.alert({...})` (`COMPONENTS.md:50`) | no `alert`; only `confirm`/`prompt`/`danger` (`utils/dialog.ts:322`) |
| Popover `#target` / `#body` (`:57`) | `#trigger` / `#default` (`Popover.vue:145`) |
| `Tabs v-model:tab` (`:120`) | plain `v-model` |
| Button `theme` incl. `orange` (`SKILL.md` rule 4) | `'gray' \| 'blue' \| 'green' \| 'red'` (`Button/types.ts:4`) |

`npx skills add https://github.com/frappe/frappe-ui/tree/main/skills/frappe-ui` — zero merge
cost, our copy has no local edits.

Also note `SKILL.md` rule 2 ("scroll regions → `ScrollArea`") is **wrong on mobile**:
`MobileShell` deliberately uses native scroll for platform inertia (`MobileShell.vue:12-16`).

## Version

frappe-ui beta.55 → **beta.56 contains nothing mobile-related**; take the bump as its own commit,
not inside this pass. `^1.0.0-beta.55` already resolves to 56 — pin exactly. Gameplan is on
beta.51, four betas behind us: good for *patterns*, unreliable for *API shapes*.

## Not yet done

Every finding here is static analysis. No 375px screenshots were captured — the built dashboard
in `ls_shop/public/dashboard/` is from Aug 31 and stale, so a browser pass needs a rebuild first.
One item explicitly needs a screenshot before prescribing: analytics x-axis tick crowding
(12 months in a 343px plot).
