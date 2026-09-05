# Mobile polish audit — Group 03: list pages, dashboard & analytics

Read-only audit. Viewport reference: **375 x 667**. `PageBody` gutters are `px-3` (12px each
side), so the usable content width is **351px**.

Canonical references used:
- `frappe-ui/src/molecules/list/list.md:83-100` — "Styling hooks", the documented mobile collapse
- `frappe-ui/docs/components/recipes/TasksMobile.vue:330-405`, `TicketsMobile.vue` (template
  lines 25-99), `FilesMobile.vue` (template lines 52-90) — how a dense desktop table becomes a
  mobile row
- `frappe-ui/src/components/PageHeader/PageHeaderMobile.vue`, `PageHeader.vue:1-9`
- `~/.claude/skills/frappe-ui/DESIGN.md:80` (archetypes), `:104-113` (type/row heights),
  `:144-155` ("Desktop → mobile")

---

## What is already clean

No raw Tailwind palette colours (`bg-gray-*`, `text-gray-*`, `bg-white`), no `surface-white`, no
inline `style="…"`, no hardcoded hex anywhere in the 18 files. No legacy APIs — every list is the
modern `frappe-ui/list` family, no `ListView`, `ItemListRow`, `TextEditor`, `Autocomplete`, and no
`createResource`/`createListResource`. Status colour goes through one lookup
(`data/format.js:102 statusTheme`) exactly as `DESIGN.md:128` prescribes. That part of the house
style is not the problem; the responsive layer is simply absent.

---

## F1 — SYSTEMIC (blocker): every column-mode list becomes a horizontal scroller

**Files / lines**

| File | Line | `min-w` | px at 375 | overflow |
|---|---|---|---|---|
| `pages/Inventory.vue` | 108 | `min-w-[56rem]` | 896 | 2.55x |
| `pages/Products.vue` | 161 | `min-w-[54rem]` | 864 | 2.46x |
| `pages/Orders.vue` | 145 | `min-w-[54rem]` | 864 | 2.46x |
| `pages/Adjustments.vue` | 33 | `min-w-[52rem]` | 832 | 2.37x |
| `pages/Pricing.vue` | 156 | `min-w-[50rem]` | 800 | 2.28x |
| `pages/analytics/Revenue.vue` | 97 | `min-w-[46rem]` | 736 | 2.10x |
| `pages/analytics/Inventory.vue` | 95 | `min-w-[46rem]` | 736 | 2.10x |
| `pages/Collections.vue` | 61 | `min-w-[34rem]` | 544 | 1.55x |
| `pages/Dashboard.vue` | 145 | `min-w-[34rem]` | 544 | 1.55x |

**What breaks at 375px.** Each is wrapped in a bare `<div class="mt-3 overflow-x-auto">`
(`Products.vue:157`, `Orders.vue:142`, `Inventory.vue:105`, `Pricing.vue:153`,
`Adjustments.vue:32`, `Dashboard.vue:142`, `Revenue.vue:95`, `analytics/Inventory.vue:93`,
`Collections.vue:59`). Consequences on a phone:

1. A merchant sees **one column and a bit** of a six-column table. Reading a single order means
   two horizontal drags.
2. `ListHeader` sits inside the same scroller, so once you drag right the column labels are gone —
   you are reading unlabelled numbers. On `Adjustments.vue` that means a bare `+12` with no
   "Change" header in view.
3. A horizontal scroller nested inside the page's vertical scroller is the classic touch
   gesture-conflict: a slightly diagonal swipe does neither.
4. `Products.vue` / `Orders.vue` / `Inventory.vue` / `Pricing.vue` also render a checkbox column
   when `selecting` is on, pushing the row past 900px.

**Recipe precedent.** No mobile recipe horizontally scrolls a table. `TicketsMobile.vue`
(template 25-99) takes the desktop ticket table — subject, id, customer, first-response SLA,
resolution SLA, last activity, status — and renders it as **three cells**: avatar / stacked
title+meta+SLA line / right-aligned date+badge, with **no `ListHeader` and no `:columns`**.
`TasksMobile.vue:330-405` does the same for tasks (status glyph / title + priority-label-due meta
row / assignee avatar). `FilesMobile.vue` (template 52-85) collapses Modified + Size into one
`{date} · {size}` meta line. `DESIGN.md:153` states the rule: *"Same data on both — trim fields,
don't fork the model."*

**Minimal fix (no layout rewrite).** `frappe-ui/src/molecules/list/list.md:86-94` documents this
exact collapse as the supported API — no new component, no custom CSS, two classes per list:

```vue
<List
  :columns="['1fr', '7rem', '8rem', '8rem', '7rem', '6rem']"
  class="max-sm:[--list-columns:auto_minmax(0,1fr)_auto] sm:min-w-[54rem]"
>
  <ListHeader class="max-sm:hidden">…</ListHeader>
  …
  <ListCell class="max-sm:hidden">…</ListCell>   <!-- the trimmed columns -->
```

and move `min-w-[…]` behind `sm:` so the `overflow-x-auto` wrapper only ever engages on desktop.
Per page, the three cells to keep (everything else `max-sm:hidden`, folded into the existing
`text-sm text-ink-gray-5` meta line that each row already has):

- **Products** (`Products.vue:184-209`): keep `Thumb` + title/subtitle cell, keep `StatusBadge`;
  fold Collection + `{{ item.stock }} in stock` + price into the existing subtitle line at 189-192.
- **Orders** (`Orders.vue:167-189`): keep the customer/order-id cell, keep one `StatusBadge`
  (fulfilment), keep the total; fold date + item count into the `item.name` line at 170.
- **Inventory** (`Inventory.vue:122-143`): keep `Thumb` + product/option cell, keep Available;
  fold SKU + committed into the meta line at 127. The disabled `TextInput` at 142 is a read-only
  number wearing an input — on mobile it costs a full column for nothing; render it as text under
  `max-sm:`.
- **Pricing** (`Pricing.vue:170-200`): keep `Thumb` + item cell and the `EditableValue`; SKU,
  compare-at and the permanently-`—` Margin cell (194-199) all `max-sm:hidden`.
- **Adjustments** (`Adjustments.vue:43-54`): keep product, the signed `delta`, and fold
  date · SKU · reason · by into one meta line.
- **Collections / Dashboard recent orders / Revenue by month / Dead stock**: same treatment,
  each already fits three cells naturally.

---

## F2 — blocker: `Customers.vue` overflows the whole page, with no scroller at all

`pages/Customers.vue:56-61`

```vue
<List v-else class="mt-3 -mx-3 list-row-px-3"
      :row-height="Math.max(ia.density, 44)"
      :columns="['1fr', '9rem', '6rem', '8rem', '9rem']">
```

**What breaks at 375px.** It is the only list in the group with **no `overflow-x-auto` wrapper and
no `min-w`**. The fixed tracks total 9+6+8+9 = 32rem = 512px, plus four `--list-gap` gaps (8px) =
**544px**, against 351px available. The `1fr` Customer track collapses toward zero (killing the
avatar + name + email cell — the only reason to read the row) and the grid still overflows by
~190px. With nothing to contain it, the overflow escapes to the shell's scroll container, so the
**page header and sidebar drag sideways with the table**. This is strictly worse than F1's
contained scrollers.

**Fix.** Same `max-sm:[--list-columns:…]` collapse as F1 — keep the Avatar cell (71-79) and the
spend (82), `max-sm:hidden` on city / orders / customer-since, and fold city into the existing
email line at 76. Note the `-mx-3 list-row-px-3` gutter bleed here is the right pattern
(`DESIGN.md:139`) and is used by no other page in the group — worth propagating, not removing.

---

## F3 — major: page headers put 2-3 nowrap buttons next to the title in a `justify-between` row

`components/ReportHeader.vue:27-38` (worst), plus every `#actions` block:
`Products.vue:119-122` · `Orders.vue:101-113` · `Customers.vue:34-47` · `Inventory.vue:71-79` ·
`Pricing.vue:122-127` · `Collections.vue:46-48` · `Attributes.vue:58-60` ·
`ProductTypes.vue:24-26` · `Dashboard.vue:78-80`

**What breaks at 375px.** `PageHeader.vue:5` is `<div class="flex items-center justify-between">`
with no wrap and no shrink policy, and `AppPageHeader.vue:14-17` gives the `<h1>` no `min-w-0
truncate` and the actions `<div>` no `shrink-0`. Measured worst case, `ReportHeader`:
`Breadcrumbs` ("Analytics / Revenue", ~150px) + range `Dropdown` whose label is the live string
`"Last 12 months"` (~150px) + "Compare" (~105px) + "Export" (~95px) = **~500px in a 351px header**.
The buttons are `whitespace-nowrap`, so the breadcrumbs are crushed first and then the action
cluster runs off the right edge — "Export" is unreachable, and the range dropdown, the one control
the report exists to change, is half-clipped. Products/Orders/Customers are milder (~300px of
actions) but still leave ~50px for the title.

**Recipe precedent.** `PageHeaderMobile.vue` is built for exactly this: a centred single-line
truncating title with a **`#prefix` and a `#suffix` capped at `max-w-[35%]` each** (lines 12, 29),
i.e. *one* control per side. `FilesMobile.vue` (template 22-26) collapses a whole "New…" action
cluster into a single `Dropdown` behind one ghost icon Button; `TasksMobile.vue:313-315` and
`TicketsMobile.vue` (template 4-10) each carry exactly one `#suffix` button.
`DESIGN.md:149` states it: *"Action clusters → one `…` Dropdown."*

**Minimal fix.** Two surgical steps, no new shell:
1. In `AppPageHeader.vue` (shared, one edit): `min-w-0 truncate` on the `<h1>` and
   `shrink-0` on the actions `<div>` — stops the clipping everywhere at once.
2. In each page's `#actions`, keep only the primary action visible and put the secondaries
   behind one `Dropdown` at `max-sm:` — e.g. `Products.vue:120` "Import" and `Orders.vue:104`
   "Export" are secondary; `ReportHeader.vue:34-37` "Compare" + "Export" are both secondary to the
   range picker. Several of these buttons are already inert (`Orders.vue:104,107`,
   `Customers.vue:37,41`, `Pricing.vue:125-126` are `disabled` or toast "coming soon") — on a
   375px header they are pure cost.

---

## F4 — major: filter toolbars wrap into ragged rows, and `ml-auto` misaligns each one

`Products.vue:126-142` · `Orders.vue:118-132` · `Inventory.vue:84-93` · `Pricing.vue:131-143`

All four are `flex flex-wrap items-center gap-2|3` with a `w-56` search input carrying `ml-auto`.

**What breaks at 375px.**
- `Orders.vue:119` — `TabButtons` renders `inline-flex shrink-0` when not `fluid`
  (`TabButtons.vue:101`), so its five options (All · Unfulfilled · Unpaid · Open · Closed) measure
  ~340px and **cannot shrink**; it either fills the row edge to edge or pushes past it.
- `TextInput class="ml-auto w-56"` (`Products.vue:132`, `Orders.vue:122`, `Inventory.vue:86`) is a
  fixed 224px. It wraps onto its own line, and `ml-auto` then shoves it to the **right** of that
  line, leaving a 100px dead gutter on the left — the search field looks misplaced rather than
  full-width. `Pricing.vue:137` has the same `ml-auto` on the Select button.
- Products stacks three ragged rows (tabs / collection `Select` / search + "Select" button).
- `Pricing.vue:133-135` puts a full sentence ("N sellable units · one row per variant, priced
  individually on its product") inside the toolbar flex; it wraps to three lines on a phone.

**Recipe precedent.** `TasksMobile.vue:319-328` and `TicketsMobile.vue` (template 14-23) both wrap
`TabButtons` in `<div class="mb-3 px-4">` and pass **`fluid`**, reducing to two options.
`FilesMobile.vue` (template 30-47) makes the toolbar a `sticky top-0 … flex items-center gap-2` row
with `class="flex-1"` on the search input — never a fixed width, never `ml-auto`.

**Fix.** Per toolbar: `class="w-full sm:ml-auto sm:w-56"` on each `TextInput`; `fluid` on
`TabButtons` at mobile (or move the 5-option Orders set behind a `Select`, which is what
`FilesMobile` does for its type filter); `max-sm:hidden` on the `Pricing.vue:133` sentence.

---

## F5 — major: `Dashboard.vue` rows reserve fixed widths that leave no room for the title

**Top products** — `Dashboard.vue:190-206`

```vue
<span class="w-20 text-right …">{{ product.units }} sold</span>
<span class="w-24 text-right …">{{ compactMoney(product.revenue) }}</span>
```

At 375px: `px-4`×2 (32) + `Thumb size-8` (32) + three `gap-3` (36) + `w-20` (80) + `w-24` (96) =
**276px of chrome, leaving ~75px** for the product title and its "N in stock" line. Every product
name truncates after roughly eight characters.

**Needs attention** — `Dashboard.vue:105-114`. `size-8` glyph (32) + `gap-3`×2 (24) + `px-4`×2 (32)
+ a `Button` whose label is "Open catalogue" (~130px) = ~218px, leaving ~130px for
`"3 products need attention"` — it truncates to `"3 products ne…"`, destroying the number that is
the point of the row.

**Recipe precedent.** `TicketsMobile.vue` (template 85-96) puts the trailing date + badge in a
right-aligned cell with **no fixed width**, sized by `whitespace-nowrap` content, and the title
cell carries `min-w-0 flex-1`. `TasksMobile.vue:397-403` reduces the trailing cell to a single
`Avatar`.

**Fix.** Drop `w-20` / `w-24` to `max-sm:hidden` and fold "N sold · ₹X" into the existing
`mt-1 text-sm text-ink-gray-5` line at `Dashboard.vue:199`; on the attention rows, replace the
labelled `Button` at 113 with `variant="ghost" icon="lucide-chevron-right"` under `max-sm:` (the
whole row is already a link target by intent).

---

## F6 — major: KPI strips have no separators on mobile, and the markup is duplicated

`components/ReportStats.vue:9` and `pages/Dashboard.vue:87` are the **same nine lines twice**:

```
grid grid-cols-2 rounded-5 border border-outline-gray-1 sm:grid-cols-4 sm:divide-x sm:divide-outline-gray-2
```

**What breaks at 375px.** `divide-x` is gated behind `sm:` and there is no `divide-y` at all, so on
a phone the four tiles form a 2x2 block inside one rounded border with **zero internal
separation** — four numbers floating in a box, no visual grouping of label to value. This is the
one `sm:` class in each file and it removes the dividers rather than adapting them.

Secondary: `ReportStats.vue:20` renders `<p class="mt-1 text-sm">&nbsp;</p>` as a spacer whenever
`compare` is off — on `analytics/Inventory.vue`, where `stats` is built with `delta: null` for all
four tiles by design (lines 33-41), that is a permanently blank line in every tile, on the screen
with the least vertical room. `Storefront.vue` and `Revenue.vue` default `compare = true`, so the
spacer only bites the Inventory report.

**Precedent.** `DESIGN.md:80` (Dashboard archetype): *"KPI strip as `divide-x divide-outline-gray-2`"*
— not "divide-x on desktop only". `DESIGN.md:151`: *"Section cards go flush: border/rounding/padding
only at `sm:`+."*

**Fix.** (a) `divide-x divide-y divide-outline-gray-2 sm:divide-y-0` on the grid, and consider
`max-sm:rounded-none max-sm:border-x-0` per `DESIGN.md:151`. (b) **House code law, reuse rule** —
`Dashboard.vue:87-99` is a semantic clone of `ReportStats.vue:9-21` down to the `text-2xl
tabular-nums` value and the delta colouring; `Dashboard.vue` already computes `kpiTiles` in the
shape `ReportStats` wants (`label`/`value`/`delta`). Delete the inline copy and render
`<ReportStats :stats="kpiTiles" compare />`. One grid, fixed once. (c) drop the `&nbsp;` spacer to
`v-if` nothing.

---

## F7 — major: 500 unvirtualised rows on a phone

`pages/Inventory.vue:31` `page_length: 500` · `pages/Pricing.vue:32` `page_length: 500` ·
`pages/Adjustments.vue:18` `page_length: 200`

All three render `<ListRows :items="rows">` with **no `virtual`**. Inventory and Pricing each also
mount a `Thumb` per row (`Inventory.vue:124`, `Pricing.vue:172`), i.e. up to 500 `<img>` elements
with no `loading="lazy"` (`components/Thumb.vue:12-18`). On a mid-range phone that is a multi-second
first paint and a scroll that stutters — and neither page has pagination to escape into (the
comment at `Inventory.vue:24-26` says so outright).

**Fix.** `ListRows` supports it natively (`frappe-ui/src/molecules/list/ListRows.vue:41`,
documented at `list.md:69-79`): add `virtual` — `itemHeight` falls back to the List's `rowHeight`,
which all three already set. Independently, add `loading="lazy" decoding="async"` to
`components/Thumb.vue:12`; it benefits every list in the app.

---

## F8 — minor: `Attributes.vue` nests a `100vh`-capped scroller inside the page scroller

`pages/Attributes.vue:73` — `<ScrollArea class="mt-6 max-h-[calc(100vh-15rem)] …">`

On mobile `100vh` excludes the collapsing browser chrome, so the region is taller than the visible
viewport and the last attribute row hides behind the URL bar; and an inner scroller inside the
page's own scroller is the same gesture trap as F1. The stated reason (comment at 71-72, keeping
the header pinned) does not apply on a phone, where the header is 52px and there is nothing to
pin. **Fix:** `max-sm:max-h-none` (and `100dvh` in place of `100vh` for the desktop cap).

---

## F9 — minor: pagination and bulk bars fit, but only just

`components/ListPagination.vue:29-56` — `Select w-32` (128) + "Previous" (~110) + "Next" (~90) +
gaps ≈ 344px against 351. It survives at 375px and breaks on anything narrower (320px devices, or
any future gutter change). The "1–20 of 137" count then wraps above. **Fix:**
`max-sm:w-full max-sm:justify-between` on the trailing group, and drop the per-page `Select` to
`max-sm:hidden` — page size is a desktop concern.

`components/BulkBar.vue:15-24` — `flex-wrap` saves it, but `Products.vue:145-153` ("Add to
collection" + "Archive" + "Done" ≈ 325px) leaves nothing for the "N products selected" text, and
the secondary hint at `BulkBar.vue:19` ("Rows pick instead of opening while this is on.") wraps to
two more lines. **Fix:** `max-sm:hidden` on that hint line, per the team's "keep UI minimal" rule.

---

## F10 — minor: `EmptyState` burns 128px of vertical space

`components/EmptyState.vue:10` — `py-16` (64px top + bottom). Not oversized *art* (the glyph is a
tidy `size-6` in a `p-3` circle, correct per `DESIGN.md:113`), but on a 667px screen a "No orders
here" state occupies a fifth of the viewport in padding alone. **Fix:** `py-10 sm:py-16`.

---

## F11 — minor: two different row-height idioms across the same group

`ia.density` raw: `Products.vue:162`, `Orders.vue:147`, `Collections.vue:62`,
`Adjustments.vue:33`.
`Math.max(ia.density, 44)`: `Customers.vue:59`, `Inventory.vue:110`, `Pricing.vue:158`,
`Revenue.vue:99`, `analytics/Inventory.vue:97`, `Storefront.vue:122,150`.
`Math.max(ia.density, 48)`: `Dashboard.vue:146`.

`ia.density` is `60` and has no settings control anywhere (`ia/store.js:8`; nothing in
`pages/storefront/Theme.vue` writes it), so nothing currently drops below 44px — this is a latent
inconsistency, not a live tap-target break. It still means the floor is enforced on six lists and
not on four. **Fix:** one exported helper (e.g. `row_height()` in `ia/store.js`) rather than three
inline formulas — house code law, reuse rule. `DESIGN.md:111` gives the ladder:
`40` dense → `44-60` medium → `h-15`/`h-17` feed, *"one mechanism per list"*.

---

## F12 — observation: charts are height-fixed, not width-fixed (no finding)

`Dashboard.vue:132` `h-72`, `Revenue.vue:73` `h-72` / `81,87` `h-56`, `analytics/Inventory.vue:64`
`h-72` / `73,79` `h-64`, `Storefront.vue:96` `h-72` / `104,110` `h-64`. No pixel widths anywhere;
the `lg:grid-cols-2` pairs stack correctly on a phone. The residual risk is **x-axis tick
crowding** — twelve month labels, or `x="product"` product names (`analytics/Inventory.vue:74,80`),
in a 343px plot. That needs a screenshot at 375px before prescribing anything; do not guess a fix.

---

## Out of scope for this audit, flagged once

- **House code law — `snake_case` in JS.** Every file in this group is camelCase:
  `endSelecting`, `toggleSort`, `directionFor`, `pageSize`, `lowOnly`, `compareAt`, `deltaLabel`,
  `countDeltaLabel`, `kpiTiles`, `stockValueByMonth`, `deadStock`, `recentOrders`,
  `bulkRaisePrice`, `bulkSetCompareAt`, `addCollection`, `editAttribute`, `countFor`. This is the
  whole dashboard's established idiom, so it is a codebase-wide decision, not a mobile fix — but it
  contradicts the project CLAUDE.md and should be settled deliberately rather than by drift.
- **Native conversions instead of the global helpers.** `Number(values.value)`
  (`Inventory.vue:53`, `Pricing.vue:76,103`), `String(item.stock)` (`Inventory.vue:142`),
  `Number(stat.value).toLocaleString` (`Dashboard.vue:30`) — house rule wants `cint`/`cstr`/`flt`.
  Note the dashboard exposes no such helpers today (`data/format.js` has only `money`,
  `compactMoney`, `shortDate`, `longDate`, `label`, `statusTheme`, `priceRange`, `stockTone`), so
  this needs a decision, not a patch.
- **`pages/ProductTypes.vue:5`** still imports `productTypes, products` from `../data/mock`, and
  `addType` (9-19) only toasts. Not a mobile issue; noting it because the page is in this group.

---

## Suggested order of work

1. **F1 + F2** — the `max-sm:[--list-columns:…]` + `max-sm:hidden` collapse on all ten lists.
   One documented mechanism, mechanical to apply, and it is the difference between usable and not.
2. **F3** — two lines in `AppPageHeader.vue`, then collapse the secondary actions per page.
3. **F4 + F5** — toolbar widths and the two `Dashboard.vue` fixed-width rows.
4. **F6** — dividers, plus deleting the duplicated KPI grid.
5. **F7** — `virtual` on the three big lists, `loading="lazy"` on `Thumb`.
6. **F8-F11** — cleanup.
