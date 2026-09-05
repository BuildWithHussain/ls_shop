# Commera dashboard — unfinished work audit

**Scope:** `dashboard/src` only. **Branch:** `feat/admin-dashboard`. **Date:** 2026-09-04.

The bug class: controls and screens that *look* done but aren't. They don't crash, so
click-through testing misses them. Everything below is evidence-backed with `file:line`.

**This is a decision list, not a work order. Nothing here has been fixed.**

---

## Completeness — what was enumerated, and how

| # | Category | Population checked | Method |
|---|---|---|---|
| 1 | Dead controls | **114** `<Button>` + **10** raw `<button>` + **54** `toast.success` sites + **10** `toast.info` sites | Python scan of every `.vue` for a `<Button`/`<button` open tag lacking `@click`/`:onClick`/`route=`/`link=`/`type="submit"` (20 + 1 hits, each then read in context to separate Dropdown triggers from genuinely dead); `grep -riE "toast\.(info\|warning)\|coming soon\|not supported\|isn't supported\|TODO\|FIXME\|XXX\|HACK\|ponytail:"`; `grep -E "onClick: \(\) => \{\}"`. **TODO/FIXME count: 0.** |
| 2 | Orphan routes | **23** route entries vs **15** nav destinations + **4** aliases | `router.js` × `ia/nav.js`, both directions |
| 3 | Unreachable pages | **21** page components | every `router.push(`, `:to=`, `to="`, `route=`, `back-to=` in the tree (48 sites) matched against the route table |
| 4 | Shell screens | **21** pages | per-file count of `useAdminRead\|useAdminAction\|useMethod*\|useCall\|createResource\|adminCall`; the 5 zero-count pages then read to see if they delegate to a store/editor child |
| 5 | Mock data | **5** importers of `data/mock.js` + `data/erpnext.js` + hardcoded arrays | `grep -rn "from '.*mock"`; manual read of `data/*.js` for literal fixtures |
| 6 | Placeholder assets | `Thumb.vue`, `ProductThumb.vue`, `integrations/logos.js`, `assets/commera.svg`; deleted `BrandMark.vue`/`StorefrontPreview.vue` | read each; `git log --all -S` for the deleted pair (no residual refs) |
| 7 | Backend↔frontend | **84** whitelisted/re-exported `ls_shop.api.admin.*` methods vs **47** called | backend: `grep @frappe.whitelist` + the by-reference re-export blocks in `footer.py`/`navigation.py`; frontend: static `useAdmin*(' … ')` + dynamic `call/attempt/mutate(' … ')` extraction. **18 backend methods have no UI. 0 UI calls hit a method that doesn't exist.** |

Also verified: **0 unimported components** (all 55 are reachable from some parent).

---

## Group A — obviously delete

| file:line | What it does today | Expected | Why unfinished | Options | Default |
|---|---|---|---|---|---|
| `ia/productActions.js:120` | `onConfirm: () => { toast.success('Deleted'); router.push('/products') }` — **lies**, then navigates away so you can't see the product still there | Delete the product | No delete endpoint; never wired | WIRE (medium — needs a guarded `catalog.delete_product` with order-line checks) / **DELETE** / HIDE | **Delete the menu item.** A false "Deleted" toast plus a redirect is the single most dangerous row in this file. |
| `ia/productActions.js:91` | `onClick: () => toast.success('Duplicated as a draft')` | Create a draft copy | No endpoint | WIRE (medium) / **DELETE** / HIDE | Delete. |
| `ia/productActions.js:92` | `onClick: () => toast.success('Export queued')` | CSV export | No endpoint | WIRE (small — Frappe already has data-export) / **DELETE** | Delete. |
| `ia/productActions.js:63` | ``onConfirm: ({values}) => toast.success(`Stock adjusted by ${values.qty}`)`` | Adjust stock with a reason | Backend is additive-only (`receive_stock`); no reason-coded adjustment exists (`Adjustments.vue:11` says so explicitly) | WIRE (large) / **DELETE** | Delete — `Inventory.vue` already has the honest additive version. |
| `ia/productActions.js:68` | `toast.success('You will be told below 5 units')` | Set a restock alert | No alert model | **DELETE** | Delete. |
| `ia/productActions.js:33` | `toast.success('Link copied')` — copies nothing | Copy the storefront URL | Never wired (URL *is* derivable, cf. `PageDetail.vue:49`) | WIRE (trivial) / DELETE | **Wire** — it's 3 lines. Listed here because it's the one cheap one. |
| `ia/productActions.js:32,34,41,42,44,66,67,76,83` | 9 × `toast.info('…')` describing what would happen | Preview, SEO, add option, bulk-edit variants, add to collection, transfer, barcodes, discount, sales report | No backend for any | DELETE / HIDE | Delete all 9. They inflate a dropdown to 18 rows of which 6 work. |
| `pages/OrderDetail.vue:56,57` | `toast.info('Duplicate is coming soon')`, `toast.info('Printing is coming soon')` | Duplicate order / print invoice | Print format exists in Frappe; duplicate does not | WIRE print (small) / **DELETE** duplicate | Delete Duplicate; see Group B for print. |
| `pages/Orders.vue:122` | `<Button label="Print packing slips" @click="() => toast.info('Printing is coming soon')" />` | Print packing slips | Never wired | WIRE (small) / DELETE | See Group B. |
| `pages/CustomerDetail.vue:47` | `toast.info("Emailing a customer isn't wired up yet")` | Email the customer | Frappe has an email dialog; never wired | WIRE (small) / DELETE | Delete — `mailto:` is one line if you want the affordance. |
| `components/import/steps/ImagesStep.vue:196` | `<Button variant="subtle" label="Upload instead" />` — no handler at all | Upload a replacement for a 404'd image URL | Whole step is inert (see C3) | DELETE with the step | Delete. |
| `components/import/steps/ImagesStep.vue:214` | `<Button variant="ghost" label="Skip the rest for now" />` — no handler | Skip remaining per-product uploads | Same | DELETE with the step | Delete. |
| `pages/Products.vue:145` | `<Button label="Add to collection" />` inside `BulkBar` — no handler; sits next to a working Archive | Add selected products to a collection | `catalog.create_collection` exists but there's no add-items method | WIRE (small — needs one endpoint) / **HIDE** | See C5. Delete the button as it stands. |

---

## Group B — obviously wire

| file:line | Today | Expected | Why unfinished | Cost | Default |
|---|---|---|---|---|---|
| `components/AppShell.vue:19` | `{ label: 'View storefront', … onClick: () => {} }` — empty | Open the storefront in a new tab | Just never wired; the URL is already available (`PageDetail.vue:48-50` does exactly this) | **trivial** | Wire it. |
| `components/AppShell.vue:20` | `{ label: 'Log out', … onClick: () => {} }` — empty | Log out | Just never wired; `/api/method/logout` exists | **trivial** | Wire it. A dead Log out in the workspace menu is the kind of thing a merchant discovers at the worst moment. |
| `pages/Orders.vue:122` + `pages/OrderDetail.vue:57` | Two "printing is coming soon" toasts | Print packing slip / invoice | Frappe print formats + `/api/method/frappe.utils.print_format.download_pdf` already exist | **small** | Wire both to the existing print endpoint. |
| `components/ReportHeader.vue:24` | `back-to="/analytics/revenue"` hardcoded | Back to the section | On `/analytics/revenue` the back button points at the page you're on | **trivial** | Fix to the previous route or drop the back button. (Not one of the seven categories — a bug hit while enumerating.) |
| `ia/productActions.js:33` | `toast.success('Link copied')` | Actually copy | Never wired | **trivial** | Wire. |

---

## Group C — needs a decision

### C1 · The Settings dialog was built, wired, and then replaced by a mock — 13 backend methods now orphaned

`486eb3f` ("replace the admin dashboard with the Commera frontend", 31 Aug) swapped a fully-wired
settings suite for the prototype dialog. Recoverable at `486eb3f^` (the commit message names `806e2c6`):

```
dashboard/src/components/settings/StoreSettings.vue        AdvancedSettings.vue
                                  ShippingSettings.vue     ProfileSettings.vue
                                  PaymentSettings.vue      AnalyticsSettings.vue
                                  FooterSettings.vue       useSettingsForm.ts
                                  DocFieldControl.vue      SettingsSecretField.vue …
```

The backend they called is **still live and still whitelisted** — `ls_shop/api/admin/settings.py`
has 13 whitelisted methods (`get/save_store_settings`, `get/save_shipping_settings`,
`get/save_payment_settings`, `get/save_footer_settings`, `get/save_advanced_settings`,
`get_link_options`, `get/save_profile`) and **zero** of them are called from `dashboard/src`.
`analytics.get_analytics_settings` / `save_analytics_settings` likewise. Payments and Shipping were
later re-wired through `IntegrationsPanel`; the rest were not.

What's mock in the current dialog:

| file:line | Today | Backend that exists |
|---|---|---|
| `components/settings/AppSettingsDialog.vue:166` General | `company` from `data/erpnext.js` — a hardcoded fake: `Kirana & Co`, GSTIN `29AABCU9603R1ZM`, `ERPNEXT_URL = 'https://erp.kirana.co'` | `settings.get_store_settings` / `save_store_settings` |
| `:210` Locations | `locations` from `data/mock.js:7` | single-warehouse, from Lifestyle Settings |
| `:222` Users | `const users = [['Aarti Mehta','aarti@kirana.co',…], …]` (`:76-80`) — three invented people | Frappe User/Role — none wired |
| `:243` | `<Button label="Permissions" variant="ghost" />` — no handler | — |
| `:94` | ``onConfirm: ({values}) => toast.success(`Invite sent to ${values.email}`)`` — **no email is sent** | — |
| `:302` Taxes | `taxInclusive`/`weightUnit` are bare `ref()`s (`:41-42`), never saved | `settings.get/save_advanced_settings` |
| `:328` Apps | `appIntegrations` from `data/mock.js:390` (GA4, Meta Pixel) | `analytics.get/save_analytics_settings` — and `AnalyticsSettings.vue` at `486eb3f^` already had the full GA4/Pixel form incl. secret handling |
| `:346` | `<Button :label="app.connected ? 'Manage' : 'Connect'" />` — no handler | as above |
| `:353` Notifications | three bare `ref()`s, never saved | none |

**Also leaking outside Settings:** `pages/OrderDetail.vue:43` and `pages/CustomerDetail.vue:38`
render a "View in ERP" button whose href is `https://erp.kirana.co/app/sales-order/…` — a domain
that isn't yours. That one is a live wrong link in a shipped screen, not just a mock.

- **WIRE IT** — medium. Restore `useSettingsForm.ts` + `DocFieldControl.vue` from `486eb3f^` and
  point General/Taxes/Apps at the endpoints that are already there. The generic `docfields.py`
  renderer is designed for exactly this. Users/Permissions/Notifications have no backend and stay out.
- **DELETE** — cut Users, Permissions, Invite, Notifications, and the Apps tab; keep
  General/Locations/Taxes as read-only.
- **HIDE** — ship Settings with only Appearance, Payments, Shipping (the three that work).

**Decision needed:** was replacing the wired settings with the prototype deliberate (new IA,
rewiring pending) or a merge loss? That changes this from "restore" to "rebuild". Separately: is the
invented company identity (Kirana & Co / erp.kirana.co) demo-seed dressing, or does it need to come
off before anyone outside the team sees it?

### C2 · Product types — a whole routed screen with no backend at all

`pages/ProductTypes.vue` — 0 API calls, the only page in the tree that is pure fixture.

- `:5` `import { productTypes, products } from '../data/mock'`
- `:17` ``onConfirm: ({values}) => toast.success(`"${values.name}" created`)`` — **claims success, creates nothing**
- `:57` `<Button label="Edit" variant="ghost" />` — no handler
- Reached from `SearchPalette.vue:78` and `productActions.js:43` ("Change product type"), not from the sidebar.
- `components/product/ProductOrganization.vue:4` and `ProductTypeFields.vue:5` also import
  `productTypes` from mock — so **mock product types leak onto the real, wired product detail form**.

There is **no Product Type doctype** anywhere in `ls_shop`
(`find . -ipath "*doctype*" -name "*.json"` → no match). The page's own copy at `:30-34` argues this
is the concept that "keeps the catalogue from being hard-wired to one kind of product" — i.e. a
stated product thesis with zero implementation.

- **WIRE IT** — large. New DocType + field-schema storage + per-type field rendering on the product form.
- **DELETE** — remove the route, the page, the two `productTypes` imports, and the two links into it.
- **HIDE** — keep the file, drop the route + links.

**Decision needed:** is "product type as a field schema" a real roadmap item or prototype residue?
Not inferable from the code, and it changes whether this is a large build or a five-file delete.
Note this one leaks: even if the page is deleted, `ProductOrganization.vue` and
`ProductTypeFields.vue` need a real source or removal.

### C3 · Import wizard, Images step — a fully simulated step inside an otherwise real flow

`components/import/steps/ImagesStep.vue`. The rest of the import is real
(`imports.validate_import` at `data/importFlow.js:91`, `imports.run_import`,
`download_product_template` linked at `UploadStep.vue:58`). This step is theatre:

- `:36-48` `upload()` — a `setTimeout` loop ticking a progress bar `+12` at a time, ending in
  `toast.success('356 of 372 images matched by file name')`. **Hardcoded numbers, unrelated to the file count.**
- `:29` `const UNMATCHED = ['IMG_4471.jpg','IMG_4472.jpg','shoot-final-v2.png','socks grey.jpeg']` — invented filenames
- `:52-56` fabricated URLs `https://cdn.kirana.co/catalog/${sku}-1.jpg`, with
  `ok: !(i === 3 || i === 8 || i === 12)` — the "404 not found" badges are **hardcoded row indices**
- `:196`, `:214` — the two handler-less buttons from Group A
- `:12-14` an honest comment says so and points at `docs/commera-open-questions.md`

A merchant runs the import, watches a progress bar, is told 356 images matched, and gets a catalogue
with no photos. The rest of the wizard did commit real products, so this is the worst kind of
invisible failure — the surrounding success is genuine.

- **WIRE IT** — medium/large. Two separate backends: zip-upload + filename→SKU matching, and
  server-side URL fetching. The per-variant photo write already exists (`catalog.add_product_images`),
  so it's the matching layer that's missing, not storage.
- **DELETE** — drop the step; import lands products without photos and the "fix them from the product
  page" CoachTip at `:203` is already the honest story.
- **HIDE** — keep the step but make it a single "Add photos later" panel with no fake progress.

**Decision needed:** photo import is usually *the* reason a merchant migrates rather than retypes.
In scope for launch? If not, HIDE is safer than DELETE — the step's position in the wizard is doing IA work.

### C4 · Navigation publish/cascade — backend built, no UI

Three whitelisted methods re-exported at `ls_shop/api/admin/navigation.py:23-25` with no caller
anywhere in `dashboard/src`:

- `get_cascade_products`
- `get_publish_preview`
- `set_published`

`git log --all -S` over `dashboard/` returns **nothing** for all three — this UI has never existed on
any branch, so it isn't a loss, it's a gap. The editor has `set_visibility` (show/hide a menu entry)
wired at `NavigationEditor.vue:154`, but not publish, which in the navbar manager is the heavier
operation that cascades to products.

- **WIRE IT** — small/medium. The editor already has the row-action dropdown and the
  preview-then-confirm pattern (`get_delete_preview` → confirm → `delete_node`,
  `NavigationEditor.vue:120-134`) to copy verbatim.
- **DELETE** the backend methods.
- **LEAVE** as an API-only capability.

**Decision needed:** what does "publish a menu entry" mean to a merchant, given they already have
"visible/hidden"? If the two are the same concept to a shop owner, exposing both is a UX regression,
and the answer is to pick one. Not inferable from the code which one the storefront actually reads.

### C5 · Collections — create works, add-to-collection doesn't

`pages/Collections.vue` is wired (`catalog.get_collections`, `create_collection`). But there is no
method to put a product *into* a collection, so:

- `pages/Products.vue:145` `<Button label="Add to collection" />` — no handler, in the bulk bar next to a working Archive
- `ia/productActions.js:44` `toast.info('Pick a collection')`
- `pages/Collections.vue:53` a note says collections are manual-only — ls_shop never re-evaluates a saved rule

So a merchant can create collections and can't fill them from the dashboard.

- **WIRE IT** — small. One `catalog.add_products_to_collection`; the bulk-selection UI, the combobox
  pattern, and the toast plumbing all already exist.
- **DELETE** both entry points.
- **HIDE** until the endpoint lands.

**Decision needed:** is collection membership meant to be managed from the dashboard at all, or does
it stay a Desk/item-group operation? If dashboard-managed, this is the cheapest high-value wire on
the list and belongs in Group B.

### C6 · Honest-but-inert controls — confirm these should stay visible

These are `disabled` with a comment naming the missing backend. They don't lie, but they're permanent
grey furniture:

| file:line | Control | Documented reason |
|---|---|---|
| `components/VariantEditor.vue:82` | "Add option" | `create_product` sets `option_attribute` once, at insert |
| `pages/Pricing.vue:125` | "Price rules" | no price-rule engine |
| `pages/Pricing.vue:126` | "Export prices" | no export endpoint |
| `pages/Inventory.vue:100` | "Transfer" | single-warehouse shop |
| `components/product/ProductBasics.vue:26` | "Add media" tile | `Item.image` has no admin write path |
| `components/import/steps/SourceStep.vue:16-21` | 5 import sources, `disabled` + "Coming soon" badge | only CSV exists |

**Decision needed:** keep as visible roadmap signposts, or remove? The SourceStep comment (`:6-8`)
argues the case for keeping — "a merchant coming from Shopify should see that we know about it."
That reasoning may or may not extend to a permanently-grey "Transfer" button in a shop that will only
ever have one warehouse.

---

## Clean

- **Orphan routes: none.** All 23 routes resolve to an existing component; all 15 nav destinations
  resolve to a route. `/pricing`, `/product-types`, `/inventory`, `/inventory/adjustments` have no
  sidebar entry *by design* — `ia/nav.js:53-58` aliases each to `/products` for active-state, and each
  is reachable from `SearchPalette` and/or an in-page button.
- **Unreachable pages: none.** All 21 have an inbound link, including the two most likely to fail:
  `VariantDetail` (`VariantDialog.vue:106`) and `Adjustments` (`Inventory.vue:72`).
- **UI calling methods that don't exist: none.** All 47 called endpoints resolve, including the
  by-reference re-exports in `footer.py`/`navigation.py` that a naive `grep @frappe.whitelist` misses.
- **Unimported components: none** (55/55).
- **Placeholder assets:** `integrations/logos.js` carries real artwork for all 6 providers + Meta;
  `letterPlate` (`data/integrations.js:26`) is a documented *fallback* for unregistered providers, not
  a stand-in. `ProductThumb.vue`'s gradient (`:12` "Stand-in for a real product photo") is confined to
  the import wizard, where no photo exists yet by definition. `Thumb.vue`'s `📦` default is never
  triggered — all 9 call sites pass `:image`. The deleted `BrandMark.vue` and `StorefrontPreview.vue`
  have zero residual references.
- **Real data confirmed** on all 21 pages except `ProductTypes.vue` (C2). The four zero-count
  storefront pages delegate to `data/pages.js` / `theme.js` / `navMenu.js` / `footerEditor.js`, all of
  which call the server.

---

## One unsolicited opinion

`ia/productActions.js:120` (the false "Deleted" toast + redirect) is the only row worth treating as
urgent regardless of what is decided about the rest.
