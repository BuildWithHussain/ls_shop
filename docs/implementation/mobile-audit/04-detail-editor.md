# Mobile polish audit — group 4: detail pages & the product/variant editor

Read-only audit at 375px. 19 files. No edits made.

Usable widths assumed: `PageBody` is `px-3` → **351px**; `PageHeader` is `px-3` → **351px**;
a `Dialog` is outer `px-4` + inner `px-4` → **311px**.

Clean across the whole group, worth saying up front: no raw `gray-*`/hex colours, no inline
`style`, no `TextEditor`/`Autocomplete`/`ListView`/`createResource`. `RichTextField` already uses
`Editor` from `frappe-ui/editor`; `ProductOrganization` already uses `MultiSelect`.

Context/dependency: there is no `MobileShell`, `PageHeaderMobile`, `BottomSheet` or breakpoint
composable anywhere in `dashboard/src` — `AppShell.vue:30` mounts `DesktopShell` unconditionally.
Every fix below is a Tailwind `sm:`/`lg:` change that works under the desktop shell today. The
"panes → separate routes" translation (DESIGN.md:148) that F1/F2 really want is blocked on the
shell group; the fallbacks proposed here do not need it.
`@vueuse/core` is **not** in `dashboard/package.json` (only transitive via frappe-ui) — prefer CSS
breakpoints; F9's computed-columns variant is the only fix that would need it added.

---

## F1 — blocker — `pages/OrderDetail.vue:152-190`

The whole right pane is `hidden w-[19rem] … lg:flex`. Below 1024px the customer, phone, email,
shipping address, tags and note **do not render anywhere on the page**. A phone user cannot see who
ordered or where it ships — the two facts you open an order for.

- DESIGN.md:156 "Same data on both — trim fields, don't fork the model." Hiding the pane forks it.
- DESIGN.md:148 "panes → separate routes"; :150 "meta panel → chip row".
- `frappe-ui/docs/components/recipes/TasksMobile.vue:429-431`: "Gameplan's mobile task detail lays
  the same controls out as a wrapping row instead of a side panel."

Fix: the aside body is already four self-contained `<section>`s (lines 155-187). Extract them to
`dashboard/src/components/order/OrderContextPanel.vue`, leave the `<aside>` exactly as-is, and add
`<OrderContextPanel class="mt-6 lg:hidden" :order="order" />` at the end of the left `PageBody`.
One new file, desktop byte-identical.

## F2 — blocker — `pages/ProductDetail.vue:150-155`

Same `hidden … lg:flex` aside. `ProductSummaryPanel` is already its own component, so this is one
line: render it a second time inside `PageBody` with `class="mt-8 lg:hidden"`. The "Needs attention
/ running low" block (`ProductSummaryPanel.vue:63-77`) is the reason the screen gets opened, and on
a phone it is unreachable. Same citations as F1.

## F3 — blocker — `pages/OrderDetail.vue:112-125`

The item row loses the product name. Fixed widths consume `px-4` (32) + Thumb `size-10` (40) +
3 × `gap-3` (36) + `w-28` (112) + `w-24` (96) = **316px of 351**, leaving ~35px for the
`min-w-0 flex-1` title/SKU column — one or two characters plus an ellipsis.

Precedent: `recipes/AccountingMobile.vue:70-92` — two tracks, description + date stacked on the
left, amount right-aligned.

Fix: `w-28` → `hidden sm:block sm:w-28`; `w-24` → `w-auto sm:w-24`; append
`· {{ money(item.rate) }} × {{ item.qty }}` to the existing `mt-1` meta line (line 116-118). Same
data, unchanged desktop row.

## F4 — major — `components/OrderProgress.vue:60-91`

`<ol class="flex">` with `flex-1` steps and no minimum width. Six non-terminal states (`ICONS`,
lines 11-16) in 351 − 40 (`px-5`) = 311px → **52px per step**, of which the dot alone is `size-8`
plus `mx-2` = 48px. Connectors collapse to ~2px and `truncate` (line 89) cuts "Delivery note
drafted" to roughly five characters, the caption to four. The ladder is the point of the screen.

Precedent for an inherently-wide horizontal strip: `recipes/MailMobile.vue:512-514`
(`sticky … flex items-center overflow-x-auto`), `recipes/ComposeMobile.vue:185-187`.

Fix: card `px-5` → `px-0 sm:px-5`, wrap the `<ol>` in `<div class="overflow-x-auto px-5">`, give
each `<li>` `min-w-[5.5rem] sm:min-w-0`. IA untouched; it scrolls.

## F5 — major — `pages/CustomerDetail.vue:67-82`

`grid gap-y-4 grid-cols-3 divide-x` with **zero** responsive fallback. 351 ÷ 3 = 117px per column,
minus `pr-5`/`px-5` leaves 77-97px for a `text-2xl` (24px) currency figure. "₹1,24,500" needs
~110px, so Lifetime spend and Average order wrap mid-number under a `divide-x` rule.

Precedent: `recipes/AccountingMobile.vue:41` — stat grid is `grid-cols-2 gap-3` on mobile.

Fix: `grid-cols-1 divide-y sm:grid-cols-3 sm:divide-x sm:divide-y-0`; gutters `pr-5` → `sm:pr-5`,
`px-5` → `py-3 sm:py-0 sm:px-5`.

## F6 — major — `pages/CustomerDetail.vue:89-111`

The recent-orders `List` passes no `:columns`, so three equal ~117px tracks. Cell 3 (lines 103-108)
holds two `StatusBadge`s plus a chevron in a `gap-3` row — ~180px of content in a 117px track. Cell
2's title ("3 items · ₹4,200") needs ~130px.

Precedent: `recipes/AccountingMobile.vue:70` — `:columns="['minmax(0,1fr)', 'auto']"`.

Fix: add `:columns="['minmax(0,1fr)','auto']"`, fold the order id (cell 1) into the meta line under
the title, wrap the payment-state badge in `hidden sm:flex` (DESIGN.md:150, "multi-value fields
collapse").

## F7 — major — `components/EditableValue.vue:44-55`

The only inline-edit affordance in the variant matrix is hover-only and 24px tall. The pencil is
`opacity-0 group-hover:opacity-100` (line 52) — there is no hover on touch, so on a phone **nothing
marks the price as editable**. The trigger is `px-1.5 py-0.5` around one `text-base` line, ~24px,
well under a 44px touch target.

Fix, two classes: line 45 add `min-h-8 sm:min-h-0`; line 52 →
`opacity-100 sm:opacity-0 sm:group-hover:opacity-100`.

## F8 — major — `components/VariantMedia.vue:68-73`

The per-photo Remove `Button` is `opacity-0 transition-opacity group-hover:opacity-100`. On a phone
a variant photo cannot be removed at all. Same fix shape as F7:
`opacity-100 sm:opacity-0 sm:group-hover:opacity-100`.

Adjacent, not a mobile bug: the cover is defined as `variant.images[0]` (line 67) and there is no
reorder control on any viewport, so cover choice is unreachable everywhere. Product gap — flag,
don't fix here.

## F9 — major — `components/VariantEditor.vue:119-188`

The matrix is 480px wide in a 351px viewport — `min-w-[30rem]` (line 122) plus `columns` (line 68)
totalling 7+5+6.5+5+4.5 = 28rem, plus the `selectable` checkbox track. It scrolls, which is a fair
escape hatch, except the identity column is **not sticky**: scroll right to reach Price/Stock/Photos
and the variant name (lines 136-141) is gone, so you are editing a row you can no longer identify.

`components/OptionSizeGrid.vue:46,60-61` in this same codebase already solves exactly this
(`sticky start-0 z-10 bg-surface-base` on the label column) — copy it onto the first `ListCell`.

Also lines 102-117: `Set price` / `Clear` / `Import photos` are labelled buttons in a header that
already carries an `h2`. DESIGN.md:149 — "Action clusters → one `…` Dropdown" on mobile.

## F10 — major — `components/product/ProductStock.vue:26-59`

Same shape: `min-w-[28rem]` (448px) four-column list in 351px, first column not sticky (line 48).
Same fix as F9.

Line 26: `flex items-center justify-between` with a two-line heading block and a labelled
`Button label="Open in Inventory"`, no `flex-wrap` — the button squeezes the heading at 375px. Add
`flex-wrap gap-2`.

## F11 — minor — `components/OptionSizeGrid.vue:67-71`

13×13px tap targets. `Checkbox` with no `size` renders `w-[13px] h-[13px]`
(`frappe-ui/src/components/Checkbox/Checkbox.vue:166-172`); the `<td class="px-3 py-2">` gives a
~37×29px cell. This grid only ever appears inside `AddProductDialog` (`size="xl"` → 311px usable at
375px), so the owner is ticking a colour × size matrix with a 13px target.

Fix: `<Checkbox size="md" padded …>` — `padded` is frappe-ui's own `h-8 px-3` hit surface for this
case (Checkbox.vue:132-142) — and `py-2` → `py-1 sm:py-2` to hold the row height. Credit where due:
the sticky first column here is the only correctly-degrading wide grid in the group.

## F12 — minor — `components/AppPageHeader.vue:15` (+ its three callers)

`<div class="flex items-center gap-2">` — no wrap, no shrink. `OrderDetail.vue:63-76` asks it for
three labelled buttons: "View in ERP" (~115px) + `…` (~36px) + "Fulfil items" (~120px) = ~271px,
beside Breadcrumbs ("Orders / SAL-ORD-2026-00042", ~200px), in 351px.
`CustomerDetail.vue:35-48` and `ProductDetail.vue:118-123` are the same shape with two.

`frappe-ui/src/components/PageHeader/PageHeaderMobile.vue:26-32` caps `#suffix` at `max-w-[35%]`,
and every mobile recipe puts exactly one action there — `recipes/ComposeMobile.vue:184-190`
("Publish"), `recipes/TasksMobile.vue:411-420` (back only). DESIGN.md:149.

Fix per page: keep the primary solid button; give the secondary `class="hidden sm:inline-flex"` and
add the matching entry to the existing `moreActions` / `actions.groups` Dropdown.

## F13 — minor — `components/RichTextField.vue:22-29`

The toolbar is clipped, not scrollable. `EditorFixedMenu` renders `flex items-center gap-1` with no
wrap and no overflow (`frappe-ui/src/molecules/editor/EditorFixedMenu.vue:18`), inside a wrapper
carrying `overflow-hidden` (line 23). `commentToolbar` is 6 controls + a separator
(`frappe-ui/src/molecules/editor/menu.ts:365-373`), ~200px, so it *does* fit at 351px today — but
anything richer, or this field inside a 311px Dialog, silently loses its right-hand tools with no
scroll to recover them.

One-line fix, exactly the recipe: `recipes/ComposeMobile.vue:185-187` —
`<div class="overflow-x-auto px-2 py-1"><EditorFixedMenu … /></div>`.

## F14 — minor — `pages/VariantDetail.vue:161-172`

`flex items-center justify-between … px-4 py-3` with "On hand: 12 · Committed: 3" (~190px at
`text-base`) beside a `w-28` TextInput (112px) in 351 − 32 = 319px. No `flex-wrap`, no `min-w-0` —
the text overflows the rounded border instead of wrapping. Add `flex-wrap gap-2` and `min-w-0`.

Same block: the `TextInput` uses `placeholder="Receive qty"` as its only label. Placeholder-as-label
is a P5 violation — give it `label="Receive"`.

The rest of this page is the best-behaved file in the group: `grid-cols-1 sm:grid-cols-2` at lines
143 and 154, Save docked in the header.

## F15 — minor — `components/product/ProductBasics.vue:26-32`, `components/VariantMedia.vue:76-86`

Hand-rolled `<button class="grid size-20 …">`. These are legitimate 80px drop tiles rather than
Buttons, so component-first is a nit here. But `ProductBasics`' tile is permanently `disabled` with
`opacity-50` and no user-visible reason — on a phone it sits directly under the only visible product
image and reads as broken. Either explain it or drop it (house rule: keep UI minimal).

## F16 — minor — `components/OptionSizeGrid.vue:46,52,61`

Raw type utilities instead of the composite scale: `text-xs font-medium` → `text-xs-medium`;
`text-sm font-normal` → `text-sm`. TOKENS.md.

---

## No finding

- `components/VariantImageImport.vue` — `sm:grid-cols-3` (line 102) is already responsive and
  `Dialog` is `w-full` + `max-w-*`, so it fits. Its drag-a-zip flow has no touch path, but the
  "Choose a zip file" button covers it. (Whole flow is simulated — no backend — so it is not worth
  polishing yet.)
- `components/AttributeMultiSelect.vue` — thin `MultiSelect` wrapper, correct slots
  (`#summary`, `#search-suffix`), `v-model:open`. Nothing width-bound.
- `components/product/ProductTypeFields.vue`, `ProductPricing.vue`, `ProductOrganization.vue` —
  already `grid-cols-1 … sm:grid-cols-*`. `ProductTypeFields` renders nothing on real data anyway.
- `components/product/ProductSummaryPanel.vue:47` — `grid-cols-3` with `text-lg` values fits at
  351px full-width. Recheck once F2 renders it on mobile, but no change expected.
- `ProductStorefront.vue` — `space-y-4`, single column throughout.
