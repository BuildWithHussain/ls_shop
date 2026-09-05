# Mobile polish audit — group 02: dialogs, modals and overlays

Read-only audit. Target width 375px (iPhone SE/13 mini). Nothing in this group was edited.

Verified against the installed `frappe-ui@1.0.0-beta.56` in `dashboard/node_modules`, the
frappe-ui source checkout, the `docs/components/recipes/*Mobile.vue` pairs, and
`gameplan/frontend/src`.

## Summary

The shell primitives are fine. `Dialog` is `w-full max-w-*` inside a `px-4` scroll container
(`frappe-ui/src/components/Dialog/Dialog.vue:25,32`), so **no dialog in this group overflows
because of its `size` prop**. Every finding below is *content* inside the dialog: fixed
`w-64`/`w-72`/`min-w-[44rem]` widths, non-wrapping flex footers, `shrink-0` on trailing
clusters, `100vh` maths, and one 4px-tall tap target.

Colour tokens are clean across all 18 files (one legitimate brand-colour escape hatch, one
placeholder gradient). The data layer is clean — `useAdminRead`/`useAdminAction` wrap
`useCall` correctly, no legacy `createResource`.

Ranked by user-visible pain:

| # | Severity | Surface |
|---|----------|---------|
| 1 | blocker | `SettingsBody`/`SettingsHeader` 70px gutters (upstream) + `w-72` controls on top |
| 2 | blocker | `MapStep` 3-column grid — Selects collapse to ~79px |
| 3 | blocker | `ImagesStep` `TabButtons shrink-0` + `w-64` Select |
| 4 | major | `ImportDialog` `100vh` + non-wrapping header/footer |
| 5 | major | `ImportStepNav` 4px-tall tap targets |
| 6 | major | `AddProductDialog` / `VariantDialog` — CTA scrolls off screen |
| 7 | major | `ReviewStep` 704px table inside a 327px viewport |
| 8 | major | `UploadStep` drop zone is a gesture that does not exist on touch |
| 9 | minor | `IntegrationCard` badge/action squeeze; row duplication |

---

## 1. [blocker] Settings panels get 234px of content width

`components/settings/IntegrationConfig.vue:120`, `:126`
`components/settings/AppSettingsDialog.vue:184`, `:287`

**Root cause is upstream.** `SettingsBody` and `SettingsHeader` hardcode a 70.4px gutter with
no breakpoint:

- `node_modules/frappe-ui/src/components/SettingsDialog/SettingsBody.vue:6` — `viewport-class="px-[4.4rem] pb-16"`
- `node_modules/frappe-ui/src/components/SettingsDialog/SettingsHeader.vue:3` — `class="shrink-0 px-[4.4rem] pt-10"`

At 375px that is `375 − 140 = 235px` of usable width for **every one of the nine panels**.
The shell around it is correct — `SettingsDialog.vue:14` is properly responsive
(`h-[100dvh] w-screen flex-col … sm:h-[min(860px,calc(100vh-8rem))] sm:w-auto sm:flex-row`)
and `SettingsSidebar.vue:5` degrades to a `max-h-[38vh]` scrolling strip. Only the padding
was missed. **File this against frappe-ui** (`px-4 sm:px-[4.4rem]`); it cannot be fixed inside
ls_shop.

**What ls_shop must fix regardless** — the app stacks fixed widths on top of that 235px, inside
a `SettingsRow` whose `gap-8` (32px) and `shrink-0` control column are themselves not
responsive (`SettingsDialog/SettingsRow.vue:2,14`):

```
IntegrationConfig.vue:120   <Select    class="w-72" …>   288px
IntegrationConfig.vue:126   <TextInput class="w-72" …>   288px
AppSettingsDialog.vue:184   <Select    class="w-64" …>   256px
AppSettingsDialog.vue:287   <Select    class="w-64" …>   256px
```

`235 − 32 (gap) − 288 = −85px`. The label column gets negative space. Every gateway credential
field — Razorpay key id, key secret, webhook secret — is unusable at 375px, which means the
payments and shipping setup flow is not completable on a phone at all.

**Minimal fix:** `class="w-full sm:w-72"` (and `sm:w-64`) on all four. One class each, no layout
change on desktop.

## 2. [blocker] MapStep collapses every column Select to ~79px

`components/import/steps/MapStep.vue:54`, `:65`

```
grid-cols-[minmax(0,1fr)_minmax(0,1fr)_6rem] gap-4 … px-5
```

At 375px inside the import dialog body (`px-6`): `375 − 48 (body) − 40 (px-5) − 96 (6rem badge
col) − 32 (2 × gap-4) = 159px`, split across two `1fr` columns → **~79px each**. The source
column name truncates to three characters and the `Select` at `:73` is a chevron with no room
for its value. The header strip at `:56-58` wraps "Column in your file" onto three lines.

Column mapping is the step you cannot skip, so this blocks the whole import on mobile.

**Precedent:** the sibling step already does this correctly —
`components/import/steps/SourceStep.vue:34` uses `grid gap-4 sm:grid-cols-2 lg:grid-cols-3`.

**Minimal fix:** `grid-cols-1 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_6rem]` on both `:54` and
`:65`, plus `hidden sm:grid` on the header strip at `:53` (the stacked rows label themselves).
Also `:32` — `flex items-start gap-4` holding the heading and the "Use suggestions" button with
no wrap; make it `flex-col sm:flex-row`.

## 3. [blocker] ImagesStep forces horizontal overflow

`components/import/steps/ImagesStep.vue:75`

```vue
<TabButtons v-model="imp.imagesMode" class="shrink-0" :options="[…3 labels…]" />
```

Three labels — "Drop a folder", "From a URL column", "One by one" — pinned `shrink-0` in a flex
row beside the `text-xl` heading. `shrink-0` *guarantees* the row is wider than 375px; the
dialog body has no `overflow-x`, so the whole import panel gains a horizontal scrollbar.

**Fix:** `flex-col sm:flex-row` on the wrapper at `:68`, drop `shrink-0` at `:77`.

Same file, same class of bug:

- `:160` — `<Select … class="w-64 shrink-0" />` (256px) in a row that also holds a thumb and a
  filename. Overflows on its own. → `w-full sm:w-64`, stack the row below `sm`.
- `:184-197` and `:219-233` — four-element rows (thumb / two-line text / badge / button) with
  `shrink-0` on both trailing items and no `flex-wrap`.
- `:211-215` — text + `Progress class="max-w-56 flex-1"` + a ghost button in one unwrapping row.
- `:115` — `grid gap-4 sm:grid-cols-3` is correct; leave it.

## 4. [major] ImportDialog: 100vh, and a footer that cannot wrap

`components/import/ImportDialog.vue:47`, `:51`, `:73-92`

**`100vh` (`:51`).** `max-h-[calc(100vh-8rem)]` — on mobile Safari and Chrome `100vh` is the
*expanded* viewport, taller than what is actually visible with the URL bar shown. The panel's
own footer, which holds the only Continue button, is pushed under the browser chrome. The
wizard becomes unadvanceable.

**Precedent, in the same library:** `SettingsDialog.vue:14` hit exactly this and uses
`h-[100dvh] … sm:h-[min(860px,calc(100vh-8rem))]`.

**Fix:** `max-h-[calc(100dvh-8rem)] sm:max-h-[calc(100vh-8rem)]`.

**Header (`:53`).** `flex items-center gap-3` with `text-lg-semibold` title + a "Step 3 of 6"
badge + the close button. At 375px the badge squeezes the close button off the edge — and the
badge is redundant: `ImportStepNav.vue:22-24` already prints "Step 3 of 6". → `hidden sm:flex`
on the badge.

**Footer (`:73-92`).** One `flex items-center gap-3` holding: Back button, the 38-character
sentence "Nothing is saved until the last step.", a "Do this later" ghost button, and the
primary "Import 128 products" CTA. No `flex-wrap`. At 375px the primary CTA is compressed to a
few characters.

**Fix:** `flex-wrap` on `:75`, `hidden sm:inline` on the help sentence at `:78`, and
`w-full sm:w-auto` on the primary button. The precedent for a full-width single action on a
narrow dialog is `Dialog.vue:112` (`isSingleActionFullWidth`), and
`~/.claude/skills/frappe-ui/DESIGN.md:150` ("action clusters → one Dropdown").

**Gutters.** `px-6` on `:53`, `:63`, `:67`, `:76` leaves 327px at 375. `DESIGN.md:155` — "section
cards go flush: border/rounding/padding only at `sm:`+". → `px-4 sm:px-6`.

**The bigger, cheaper move.** A six-step wizard is not a centered dialog on a phone, and it is
not a `BottomSheet` either (`BottomSheet.md`: "sizes itself to its content up to 90% of the
viewport height"). The right primitive is the one `SettingsDialog` already uses — `Dialog bare`
with a root that goes full-screen below `sm`. Copying that one class string from
`SettingsDialog.vue:14` onto `ImportDialog.vue:51` is the single highest-leverage change in this
group.

## 5. [major] ImportStepNav ships 4px-tall tap targets

`components/import/ImportStepNav.vue:26-33`

```vue
<button type="button" class="h-1 flex-1 rounded-full …" @click="go(i)" />
```

`h-1` = 4px. Six of them. They are real `<button>`s with a real `@click` handler that navigates
back to a completed step — a 4px target against a 44px minimum, wrapped in a `Tooltip` that
never fires on touch, so on mobile the affordance is both invisible and unhittable. Nothing in
frappe-ui ships anything this small; `DESIGN.md:110` starts row heights at 40px.

**Fix:** keep the 4px bar as an inner `<span>`, give the `<button>` a transparent `py-2` hit
area — 20px total, and `py-2.5` gets you to 24px without moving the visual.

Same file, `:18-24`: step label + hint + "Step n of N" in one `flex items-baseline gap-2` with
no wrap. At 375px "Match your columns" + "we matched 7 of 9 columns for you" + "Step 3 of 6"
collide. → `hidden sm:inline` on the hint at `:20`.

## 6. [major] The primary CTA scrolls off screen

`components/AddProductDialog.vue:182-264` · `components/VariantDialog.vue:61-113`

Neither dialog has a scroll container. `Dialog`'s own container does scroll
(`Dialog.vue:21`, `fixed inset-0 overflow-y-auto`), so nothing is clipped — but the whole card
scrolls as one unit, footer included.

**AddProductDialog** stacks: title, collection row, option row, two `AttributeMultiSelect`es, an
option×size grid, a summary line, an error slot, two price fields and an Alert. At 375px that
is comfortably 900px+ tall. The `#actions` "Add product" button at `:251-264` sits below all of
it, off-screen, with no indication it exists.

**VariantDialog** is worse: its footer is not even in `#actions`, it is the last child of the
default slot (`:102-112`), so the **Save** button is buried under the photo grid and six form
controls.

**Fix (both):** the `ImportDialog` pattern already in this codebase —
`<div class="flex max-h-[calc(100dvh-8rem)] flex-col">` with a `min-h-0 flex-1 overflow-y-auto`
body and the actions outside it. For `VariantDialog` this also means moving `:102-112` into a
`#actions` slot, which is where `Dialog` expects them (`Dialog.vue:101`).

Also `VariantDialog.vue:102` — `flex items-center gap-2` with "Open full page" (+ icon),
"Cancel" and "Save variant". Roughly 320px of buttons against 343px of available width; it
clears by a hair with the icon and then does not. No `flex-wrap`. → `flex-wrap`, and
`w-full sm:w-auto` on the primary.

And `VariantDialog.vue:96` — `:model-value="skuList"` puts a comma-joined list of every size's
SKU into a single-line disabled input. At 375px the merchant sees the first ~15 characters,
cannot scroll a disabled input, and cannot copy it. → `type="textarea"` or a wrapped chip row.

## 7. [major] ReviewStep is a 704px table in a 327px viewport

`components/import/steps/ReviewStep.vue:61-63`

`<List class="min-w-[44rem]" :columns="[…5 columns…]">` inside `overflow-x-auto`. It does not
break the layout — it just makes the merchant horizontally scroll a table inside a modal inside
a page, to do the one thing this step exists for: confirm what is about to be written.

**Precedent:** the mobile recipes never scroll the desktop column set — they collapse it.
`docs/components/recipes/FilesMobile.vue:696` and `DealsMobile.vue` render the same rows as
stacked two-line `ListRow`s. `DESIGN.md:150` — "multi-value fields collapse".

**Minimal fix:** below `sm`, render `filtered` as a stacked list (thumb + title / variant · row,
status badge right); keep the wide `List` at `sm:+`. Both read the same `filtered` computed, so
no model fork.

Also `:28` — `grid gap-4 sm:grid-cols-4`. At 375px four stat cards stack to ~320px of vertical
padding before the merchant reaches the table. → `grid-cols-2 sm:grid-cols-4`, one class.

## 8. [major] UploadStep's drop zone is a gesture that does not exist

`components/import/steps/UploadStep.vue:66-83`

The primary affordance is "Drop your spreadsheet here" (`:75`) with the actual working control —
"Browse files" — demoted below an "or" (`:76-78`). On touch there is no drag-and-drop; the
merchant reads an instruction they cannot follow. The `py-14` box is 56px of vertical padding
spent saying so.

**Also hand-rolled.** `frappe-ui`'s `FileUploader` already owns the hidden input and exposes
`openFileSelector` through its default slot
(`frappe-ui/src/components/FileUploader/FileUploader.vue:3-9,20`), including `uploading`,
`progress` and `error`. This file instead writes its own `<input type="file" class="hidden">`
at `:77` and reaches it with `$refs.fileInput.click()` at `:78` — template `$refs` is what L4
tells you to replace with `useTemplateRef`, and here the component that removes the need
entirely already exists.

**Fix:** `<FileUploader :file-types="['.csv','.xlsx']" private v-slot="{ openFileSelector, uploading }">`,
and make the copy responsive — "Tap to choose a file" below `sm`, "Drop your spreadsheet here"
above. Reordering so the button is primary on mobile is the same edit.

Dead code while you are in there: `:2` imports `ref` from vue and never calls it.

Lower priority, same file: `:104` `min-w-[42rem]` preview table inside `overflow-x-auto` — it
scrolls, but there is no affordance telling the merchant it does. A right-edge fade or a
"scroll to see all N columns" caption at `:121` would close it.

## 9. [minor] IntegrationCard squeezes its title to nothing

`components/settings/IntegrationCard.vue:24-51`

Inside the 235px from finding #1: `32 (BrandMark) + 12 + ~80 (Button) + 12 + ~36 (Switch) =
172px`, leaving **~62px** for the label plus up to three badges — "Live", "Not installed", "Keys
missing" (`:30`, `:33`, `:34`). The truncating title at `:29` gets nothing. The trailing cluster
is `shrink-0` (`:39`) so it never yields.

**Fix:** `flex-col items-start gap-2 sm:flex-row sm:items-center` on `:24`, and let the action
cluster take its own full-width row below the text on mobile.

The same squeeze hits `AppSettingsDialog.vue:167` (`max-w-xs text-right` address in a
`gap-8` SettingsRow) and the three list rows at `:203-209` (locations), `:228-236` (users) and
`:309-319` (apps) — each `flex items-center justify-between py-3` with an unwrapped trailing
Button.

**Reuse note (house law: `existing_utility > extraction > individual`).** Those three rows plus
`IntegrationCard.vue` are four copies of the same shape — mark/avatar, two-line truncating text,
optional badge, trailing action. Extracting one `components/settings/SettingsListRow.vue` means
the mobile stacking fix is written once instead of four times.

---

## Lower-priority flags (not mobile)

- **`AppSettingsDialog.vue:64-68`** — `users` is an array of positional arrays read as
  `person[0]`…`person[3]` in the template (`:230-233`). House naming law: name what it does.
  Should be objects with `name` / `email` / `role` / `scope`. Blocking under house code law
  independently of this audit.
- **snake_case.** This group is camelCase throughout — `imp.imagesMode`, `compareAt`,
  `optionAttribute`, `resetToSuggested`, `perProduct`, `pageUrl`, `skuList`. House rule is
  snake_case in JS. Systemic across the dashboard, noted once rather than per line; not a
  mobile issue.
- **`ImagesStep.vue:8`** — `const delay = (ms) => ms` is an identity function used only to wrap
  `setTimeout` arguments. Dead indirection.
- **Colour tokens are clean.** Only two raw-colour hits in 18 files, both defensible:
  `BrandMark.vue:13` (`:style="{ backgroundColor: brand }"` — a third-party brand colour from a
  data registry, the legitimate escape hatch; you cannot tokenize Razorpay navy) and
  `ProductThumb.vue:19-21` (a deterministic HSL gradient standing in for a real product photo,
  which goes away when photos land). No `bg-gray-*`, no `text-gray-*`, no `surface-white`,
  no hex literals.
- **Data layer is clean.** `data/api.js` wraps `useCall` from frappe-ui with shared error
  toasting; no legacy `createResource` / `createListResource` anywhere in this group.
- **`index.html:5`** — `<meta name="viewport" content="width=device-width, initial-scale=1.0">`
  lacks `viewport-fit=cover`, which `env(safe-area-inset-bottom)` needs. Relevant when the
  pinned dialog footers from findings #4 and #6 land. Out of this group's file list; flagged
  for whoever owns the shell.

## The reference implementation in this group

`components/storefront/FooterLinkDialog.vue` has zero findings. Native form validation via
`:form="formId"` + `required` rather than a JS regex (`:69`, `:89`, `:95`), `defineModel('open')`
(`:12`), a `w-full` CTA (`:103`), `Combobox` rather than a hand-rolled picker (`:81`), and not a
single fixed width. It is what the other seven dialogs should be measured against.
