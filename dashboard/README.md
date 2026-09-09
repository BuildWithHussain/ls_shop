# Commera — merchant dashboard IA prototype

Frontend-only prototype of **Commera**, a merchant e-commerce dashboard
(Shopify / Medusa shaped), built with Vue 3 + [frappe-ui]. No backend: every
screen reads from `src/data/mock.js`, and writes only raise a toast.

Commera is the product; *Kirana & Co* is the sample store it manages, so the
sidebar header names both and the storefront previews stay in the store's
brand.

The point of the prototype is the **information hierarchy**, so the IA is a
runtime setting rather than a decision baked into the components. The toolbar
pinned to the bottom of every screen flips it.

```bash
npm install
npm run dev
```

## The confirmed IA

```json
{
  "navModel": "medusa",        // grouped sidebar: Overview, Orders, Customers,
  "sidebarGrouping": "collapsible", //   Search, then Catalog and Storefront
  "productDetail": "meta",     // form left, standing summary panel right
  "productActions": "panel",   // frequent actions listed in that panel
  "variantUI": "matrix",       // one editable row per permutation
  "inventoryHome": "product",  // no Inventory section; stock sits on the product
  "storefrontHome": "sidebar",
  "density": 60,
  "viewport": "desktop",
  "theme": "dark"
}
```

These are the defaults in `src/ia/store.js` and the "Commera" preset. The
toolbar stays so the alternatives remain walkable, and `Reset` returns here.
The product page also carries its own layout switcher in the header — the same
three axes (layout, actions, variants), reachable without opening the toolbar,
because that screen is the one worth comparing in place.

## IA axes (the toolbar)

| Axis | Options | What it changes |
|---|---|---|
| Nav model | Shopify flat · Medusa grouped · Rail workspaces | Sidebar grouping and depth |
| Group behaviour | Collapsible · Always open | Whether sidebar groups fold |
| Product detail | Single page · Tabbed · Content + summary panel · Summary first · Two-pane variants | Layout of `/products/:id` |
| Product actions | Header + overflow · Listed in the panel · Sticky save bar | Where the action set is parked |
| Variant UI | Flat matrix · Grouped by first option · Drill-in rows | How permutations are edited |
| Inventory lives in | Own section · Inside the product | Whether `/inventory` exists |
| Storefront lives in | Sidebar section · Own rail workspace | Where theme/nav/pages sit |
| Row density | 40 · 48 · 60 px | List row height everywhere |
| Viewport | Desktop · Mobile | `DesktopShell` vs `MobileShell` in a phone frame |
| Theme | Light · Dark | `data-theme` on `<html>` |

Four presets combine them: **Shopify-like**, **Medusa-like**, **Lean
merchant**, **Two workspaces**. State lives in `src/ia/store.js` and persists to
`localStorage`; "Copy config" puts the current object on the clipboard.

## The product page

The screen the prototype spends most of its effort on. Five layouts, all
reading the same sections, so they can be compared without re-reading content:

| Layout | Shape | Suits |
|---|---|---|
| Single long page | Everything stacked | Small catalogues; nothing to learn |
| Tabbed | Details / Variants / Inventory / Storefront | Deep products; one concern at a time |
| Content + summary panel | Form left, standing summary right (the Helpdesk shape) | Wide screens; "how is this doing" always answered |
| Summary first | Figures strip, then the form | Same answer, no side panel — survives narrow widths |
| Two-pane variants | Variant list left, selected variant edits right | Catalogues where the variant is the unit of work |

The **summary panel** is the piece worth arguing about. It carries, in order:
status and visibility · price range, available, committed, variant count ·
30-day sold / orders / revenue · stock per location as meters · anything
needing attention (out of stock, running low) · top variants by stock with
price · organisation (type, vendor, SKU, collections). It answers the questions
a merchant opens a product to ask, without making them scroll into the form.

### Actions available from a product page

One set, defined in `src/ia/productActions.js`; the `productActions` axis only
moves it. Grouped by intent:

- **Storefront** — publish / unpublish, preview on the storefront, copy the
  product link, edit the SEO listing.
- **Catalogue** — add an option (or split a single item into variants), bulk
  edit variants, change product type, add to a collection.
- **Inventory** — adjust stock (opens a reason-coded prompt), transfer between
  locations, print barcode labels, set a restock alert.
- **Pricing** — edit prices, apply a discount.
- **Reporting** — view the sales report, jump to orders containing this product.
- **Manage** — duplicate, export as CSV, archive / restore, delete.

Five of these — publish, adjust stock, edit prices, add an option, duplicate —
are the ones the panel surfaces without a menu. Bulk work still belongs to the
list view; this page is about one product.

## Order progress

The order page opens with a horizontal tracker — **Placed → Paid → Fulfilled →
Delivered** — with the reached steps filled and the connector drawn only as far
as the order has got. It replaced the vertical timeline: same information, read
in one glance instead of scrolled to.

State is derived from `payment` and `fulfillment` rather than stored, and each
step depends on the one before it, so the line can only fill left to right
however the two combine. A cancelled order ends the run in red. The status
badges above it now appear only for what the tracker cannot say — payment
pending, refunded, partly refunded, cancelled. On a phone the steps stack.

## It sits on ERPNext

Company, tax and accounting records are owned by the books; Commera reads them
and never asks the merchant to learn ERPNext:

- Settings → General is **read-only** — store name (the company name), address,
  contact, currency, financial year — with one "Open company record" handoff.
  Only Commera's own fields (weight unit, notifications, gateways) are editable
  there. The GSTIN under Taxes reads the same way.
- The **customer record** is theirs too: the customer page shows it read-only
  and offers "View in ERP" for the full contact and billing detail. Its Recent
  orders rows stay in Commera — orders have a page here — and the order page
  carries its own "View in ERP" for the document behind it.
- `src/data/erpnext.js` holds the company record and `erpnextLink()`; swap it
  for a real fetch and nothing else changes.

## Search

`Search` is a nav row, not a page — the same shape hive uses. It opens
frappe-ui's experimental `CommandPalette` family (`CommandPaletteInput` /
`List` / `Group` / `Item` / `Empty` / `Footer`), bound to `Mod+K` through
`useKeyboardShortcut`. `:filterable="false"`, so ranking is app code: records
(products, orders, customers, collections) appear once you type, commands
(Go to / Create / Settings) show even on an empty query and filter on their own
keywords. State lives in `src/ia/search.js`.

## Settings

Settings is a **dialog**, not a route — opened from the workspace menu in the
sidebar header, the sidebar footer, and the rail. It is frappe-ui's
`SettingsDialog` family (`SettingsSidebar` / `SettingsNavItem` /
`SettingsPanel` / `SettingsHeader` / `SettingsBody` / `SettingsRow`), with tab
state in `src/ia/settings.js` so any caller can deep-link a panel:
`openSettings('payments')`.

Panels: General · Locations · Staff · **Payments** · Shipping · Taxes ·
Apps and channels · Notifications. The workspace dropdown carries one
"Settings" entry — panels are reached inside the dialog, not duplicated in the
menu.

**Payments** is the one built out. Gateways are not mutually exclusive: each row
has its own Enable switch, its own Test/Live environment, and its own key
fields, and any number can be on and expanded at once. The only exclusive
choice is which one checkout preselects — a `Select` at the top, also settable
from a gateway's own "Make default at checkout". Shipping Stripe, Razorpay,
PayPal, PayU, Cashfree, Paytm and cash on delivery, each with its real fee and
region so the trade-off between them is visible.

Vendor brand colour is used for the logo tiles (`BrandMark.vue`) — the one
place in the app where non-semantic colour is right, because recognition *is*
the job. Everything around them stays on the gray ink ladder.

## Entity model

```
Product ──┬── ProductType   field schema (Book: author/ISBN · Apparel: fabric/fit)
          ├── Option[]      0..n, drawn from the global Attribute registry
          └── Variant[]     cartesian product; own SKU, price, stock, image
Collection    manual or smart (rule re-evaluated on save)
InventoryItem Variant × Location
Order ────┬── LineItem[] · Payment[] · Fulfillment[]
Customer ──── Address[], Order[]
Storefront ── Theme tokens · Navigation menus · Pages
```

Two things keep the catalogue from being hard-wired to one kind of product:

- **Product types** (`/product-types`) carry the extra field schema. A bookshop
  and a clothing label share every core field and differ only here.
- **Attributes** (`/attributes`) are ordinary records. Size and Color ship out of
  the box; a bookshop deletes them and adds Format and Binding.

## Layout

```
src/
  ia/store.js      axes, presets, persisted state, the `narrow` flag
  ia/nav.js        the three nav models, derived from the axes
  data/mock.js     catalogue, orders, customers, inventory, storefront
  data/format.js   currency, dates, one status→theme lookup
  components/      AppShell, IAToolbar, VariantEditor, shared bits
  components/product/  the product-detail sections, arranged per layout
  ia/productActions.js the action set, grouped by intent
  data/product.js      per-product stats the summary panel reads
  pages/           one file per route
```

Notes for anyone picking this up:

- Every list uses the `frappe-ui/list` family; columned tables sit in an
  `overflow-x-auto` wrapper with a `min-w-*` so they scroll rather than crush.
- `SidebarItem` infers active state from an exact route match only, so
  `activeNavTarget()` in `ia/nav.js` resolves it instead: the longest
  destination the current path sits under wins. That lights Products on
  `/products/p-2` without lighting Stock on `/inventory/adjustments`.
- `selectable` on a `List` is a **mode**, not decoration: while it is on, a row
  click toggles selection instead of following the row's `to`. So the four
  selectable lists (products, orders, stock, pricing) enter it through a
  "Select" button and leave it through the bulk bar's "Done" — rows open by
  default.
- Colour appears only where it encodes state (status badges, stock levels,
  financial sign). Everything else is `ink-gray-*` on `surface-*`.
- The mobile preview is a real `MobileShell` inside a `translateZ(0)` frame, so
  its `fixed inset-0` is contained. CSS media queries still see the desktop
  viewport, which is why layout switches key off `narrow` from the IA store
  rather than `sm:` / `lg:` prefixes.

## frappe-ui version

Pinned to `1.0.0-beta.55`. Things that moved since beta.21, in case you are
porting other code across:

- `TabButtons` dropped `buttons` — pass `options`.
- `Tabs` items are keyed by `value`; `modelValue` is that value, not an index.
  `icon` on a tab means icon-only, `iconLeft` keeps the label.
- `SidebarHeader`'s logo slot is now `#prefix`.
- `PageHeaderMobile`'s edge slots are `#prefix` / `#suffix`, not `#left` / `#right`.
- `Button` now falls back to a passed `aria-label` when it has no `label`, so
  icon-only buttons can be named either way.
- `Dropdown` groups take `{ group, options }`; the old `{ group, items }` shape
  renders **nothing** (it warns in dev only).
- `Dropdown`'s `placement` prop is gone — use `align`.

## Why pricing is not a section

Price belongs to the product — it is on the product form, and per variant in the
variant matrix. A sidebar entry for it duplicated that, so it is gone. What is
left is a bulk tool: select rows in Products and choose "Edit prices", or reach
it from a product's action menu or the palette. It opens as **Products › Edit
prices**, not as a destination of its own.

A pricing *section* would only earn its place once there is something a single
product cannot express — several price lists (retail, wholesale, B2B), or price
rules with their own schedule and conditions. Those are records in their own
right; repricing a table of variants is not.
