# Skill & frappe-ui freshness audit

Research only — no skill file or `ls_shop` file was edited.

Date of audit: 2026-09-04.

## Headline

Two separate staleness questions, with very different answers.

1. **The library pin (beta.55 → beta.56) is barely stale.** One breaking export
   move, two small prop removals, one bug fix. Nothing that helps a mobile pass.
2. **Our skill is badly stale, and demonstrably wrong.** Our
   `~/.claude/skills/frappe-ui/` is a byte-for-byte copy of the **official**
   skill that ships in the frappe-ui repo at `skills/frappe-ui/`. Upstream then
   rewrote that skill three times between 2026-08-29 and 2026-08-31, fixing
   **59 documented API defects** and restructuring the files. Our copy predates
   all of it. I verified six of those defects directly against library source —
   they are real, and they are in the file we load on every UI task.

The skill, not the version pin, is the thing to fix.

---

## (a) beta.55 → beta.56 delta, and upgrade recommendation

### Method

There is no git remote on the local checkout, so I diffed the two published npm
tarballs instead — that is ground truth for what a consumer receives:

```
npm pack frappe-ui@1.0.0-beta.55 / @1.0.0-beta.56, untar, diff -r
```

Working copies left at `/tmp/fui-diff/a/package` and `/tmp/fui-diff/b/package`.

I also confirmed the local checkout at
`/Users/deathstarconsole/company_projects/frappe/develop/apps/frappe-ui` is
effectively beta.55: `diff -rq src /tmp/fui-diff/a/package/src` reports only two
differing files (`Combobox/stories/MemberPicker.vue`, `Sidebar/SidebarHeader.vue`),
i.e. it is beta.55 plus a couple of post-tag commits.

### What actually changed

**1. `ThemeSwitcher` moved out of the root export into `frappe-ui/experimental` (breaking, loud).**

`/tmp/fui-diff/b/package/src/index.ts` (vs `a`):

```diff
-// Deprecated component compatibility
-/** @deprecated Use `Select` with `useColorScheme` instead. */
-export * from './components/ThemeSwitcher'
+// ThemeSwitcher moved to `frappe-ui/experimental` (#1094, P14) — parked
+// there, deprecated, while apps move to `Select` plus `useColorScheme`.
```

The whole `src/components/ThemeSwitcher/` tree moved to
`experimental/ThemeSwitcher/`. `import { ThemeSwitcher } from 'frappe-ui'` stops
resolving. Sanctioned replacement is `Select` + the `useColorScheme` composable.

Caveat: the live https://ui.frappe.io/llms.txt still lists ThemeSwitcher under
`/docs/components/themeswitcher`, not under Experimental. Either the deployed
site lags beta.56 or the docs nav was not moved. **Unverified which.**

**2. `TabButtons` — the per-tab `class` escape hatch is removed (breaking, silent).**

`src/components/TabButtons/types.ts` loses `class?: NativeButtonClass` from the
`TabButton` interface, and `NativeButtonClass` is dropped from the barrel
(`index.ts`). `TabButtons.vue` stops reading `button.customClass`. A tab is now
styled through the new `:data-value="button.value"` attribute it emits, i.e. via
CSS on `[data-slot="tab-button"][data-value="…"]`. Passing `class` on a tab
object silently does nothing now.

**3. `Button` no longer exposes `rootRef`.** `Button.vue` drops
`expose({ rootRef })` and the `ref` on the root element. Template refs on
`<Button>` no longer give you `.rootRef`.

**4. `DatePicker` stops re-exporting `./utils`** from its barrel
(`src/components/DatePicker/index.ts`) — any date helper imported from
`frappe-ui` via that path is gone.

**5. `toast` legacy-compat layer deleted.** `src/components/Toast/toast.ts`
drops `LegacyCreateOptions`, `LegacyToastObject`, `toMs`, `resolveIcon` and the
`warnDeprecated` path (the v0 `{ title, text, timeout, position }` object form).
It gains `withSafeDescription` — `description` is now DOMPurify-sanitized the
same way `message` is. Small security improvement.

**6. `portalTo` is retyped** from `string | HTMLElement` to the shared
`PortalTarget` type from `composables/usePortalTarget`, across `Select`,
`Popover`, `Combobox`, `MultiSelect`, `Dropdown`, `Menu`, `HoverCard`. Type-only.

**7. `SidebarHeader` baseline fix.** `SidebarHeader.vue` moves the text size onto
the line box itself and adds `truncate`, fixing a 1px baseline drift in apps with
a smaller base font size, and long titles now truncate rather than overflow.

**8. Calendar (experimental) reshuffle** — `ShowMoreCalendarEvent.vue` deleted;
`CalendarMonthStack.vue`, `monthStrip.ts`, `eventSpan.ts`, `useStripScroll.ts`
added. This is the "elastic month strip" work also present in our checkout's git
log (`c2fce39bc`, `a89a95fa9`). Irrelevant unless we use the experimental Calendar.

### Verdict: is beta.56 worth it for a mobile-polish pass?

**No — not for mobile.** Nothing in the delta touches `MobileShell`,
`MobileNav`, `BottomSheet`, `PageHeaderMobile`, safe-area handling, or touch
sizing. The only mobile-adjacent item is the `SidebarHeader` truncate fix, which
is desktop chrome.

Recommendation: **take the bump anyway, but as its own commit, not inside the
mobile pass.** It is cheap (`^1.0.0-beta.55` in
`/Users/deathstarconsole/company_projects/frappe/develop/apps/ls_shop/dashboard/package.json`
will already resolve beta.56, so we are arguably *already* exposed to it and
should pin deliberately), and the three breaking items are trivially greppable
in our tree before bumping:

- `ThemeSwitcher` imported from `'frappe-ui'`
- a `class` key inside a `TabButtons` `:buttons` array
- `.rootRef` off a `<Button>` template ref

If any of those three hit, fix them; otherwise pin `1.0.0-beta.56` exactly.

Note Gameplan pins beta.51 — older than us. Gameplan is not a freshness signal
here; we are ahead of it.

---

## (b) Skill gaps — and the much bigger finding

### Our skill is the official skill, frozen at an old revision

`/Users/deathstarconsole/company_projects/frappe/develop/apps/frappe-ui/skills/frappe-ui/`
contains `SKILL.md`, `COMPONENTS.md`, `TOKENS.md`, `DESIGN.md`, `SETUP.md`.
`diff` against `~/.claude/skills/frappe-ui/` reports **all five files identical**.
So our house skill is a copy taken from this checkout, whose newest skill commit
is `cf7cda1cb` (2026-08-20, "docs(skill): one action, one toast").

Upstream `main` has moved on. `gh api repos/frappe/frappe-ui/commits?path=skills`:

| sha | date | subject |
|---|---|---|
| `28835037` | 2026-08-31 | fix(skill): correct the defects an A/B eval found |
| `7caadd84` | 2026-08-29 | refactor(skill): merge three always-co-read files into CORE.md |
| `10581f19` | 2026-08-29 | fix(skill): correct 59 API defects and add an eval gate |
| `cf7cda1c` | 2026-08-20 | docs(skill): one action, one toast  ← **our copy stops here** |

Current upstream file list (`gh`/GitHub contents API on `skills/frappe-ui`):

```
CORE.md   41,268 bytes
DATA.md    7,762
SETUP.md   5,794
SKILL.md   2,618
evals/
```

`COMPONENTS.md`, `TOKENS.md` and `DESIGN.md` **no longer exist** — they were
merged into `CORE.md` because an eval found agents opened all three together in
17 of 20 cases. Data-fetching was split out into `DATA.md`. Total skill went
925 → 725 → 736 lines; mean load per invocation 700 → 559 lines.

The upstream commit messages are unusually specific and read as
source-verified. From `10581f19`:

> An eval of the frappe-ui skill, run blind to library source, found agents
> picked the right component in every case and then **called it wrong in 6 of
> 10**. Every failure was a prop, slot or option-shape error.
> … API-correct cases 4/10 -> 8/10.

### The defects, verified against our own source

I did not take the commit messages on trust. Each of these is confirmed against
`/Users/deathstarconsole/company_projects/frappe/develop/apps/frappe-ui/src/`:

| Our skill says | Source says | Citation |
|---|---|---|
| `dialog.alert({ title: 'Saved' })` (COMPONENTS.md, Imperative dialogs) | No `alert`. Namespace is `confirm` / `prompt` / `danger` | `src/utils/dialog.ts:322` `confirm`, `:498` `prompt`, `:715` `danger`, `:725` the `dialog` object |
| `const { values } = await dialog.prompt(...)` | `prompt` returns a `DialogHandle`, not a promise; values arrive via `onConfirm` | `src/utils/dialog.ts:498` — `export function prompt(args: PromptArgs): DialogHandle` |
| Popover slots `#target` (trigger), `#body` (content) | Slots are `trigger` and `default` | `src/components/Popover/Popover.vue:145-150` |
| Button `size`: `sm \| md \| lg \| xl \| 2xl` | `xs \| sm \| md \| lg` | `src/components/Button/types.ts:5` |
| `theme` includes `orange` (SKILL.md rule 4) | `gray \| blue \| green \| red` | `src/components/Button/types.ts:4` |
| Dropdown groups: `options: [{ group: 'Label', items: [...] }]` | `{ group, options }`. `items` is typed `never` **on purpose** | `src/components/Menu/types.ts:99-112` — the source comment reads *"Removed `{ group, items }` shape. `never` keeps the old key a type error instead of a silently ignored extra field."* |
| `Tabs` … `v-model:tab` | plain `v-model` on the trigger `value` | `src/components/Tabs/Tabs.vue:322` emits `update:modelValue`; `src/components/Tabs/Tabs.md:99-105` documents `v-model="value"` |
| `Calendar` listed under "Lists & data" as a root component | Calendar is parked in `frappe-ui/experimental` | `src/index.ts` comment: *"Calendar family moved to `frappe-ui/experimental` (#1020, P14)"*; directory `experimental/Calendar/` |

Six of eight independently re-verified by me; the Dropdown one is the most
damning because the library added a `never` type specifically to catch the shape
our skill teaches.

Upstream lists further defects I did **not** independently re-verify (recorded
here as upstream claims with their cited source files):

- `LoadingText` has no `lines` prop.
- Chart props are `:data` / `x` / `y` **only for the axis family**; `DonutChart`
  and `FunnelChart` take `category`/`value` (`src/charts/types.ts:764,796`),
  `HeatmapChart` adds `value`, `SankeyChart` takes `source`/`target`/`value`.
  Charts carry `title`/`subtitle` (`ChartBaseProps`, `:593`) and draw their own
  header, tooltip, empty state and (Bar/Line/Area/Donut/Scatter) legend. There
  is **no `height` prop** — the root is `h-full` (`ChartContainer.vue:7`).
  `NumberCard` is the KPI tile with `title` and `value` required (`:914`).
- `EditorFixedMenu :items` takes `MenuItem` objects, never strings
  (`src/molecules/editor/menu.ts`).
- `KeyboardShortcut` combo needs `ArrowUp` / `ArrowDown` / `Escape`; unknown key
  names render as written and never fire (`src/utils/keyboardShortcutCombo.ts`).
- `Dialog :icon` is `string | DialogIcon`, not a Vue component.
- `bg-surface-gray-2` is the subtle input fill, not `gray-1`.
- Shadows do not fade in dark mode; `--elevation-*` is `:root` only.
- `Combobox` needs `filterable` documented — left `true`, a server-searched
  picker re-filters ranked results away (`Combobox/types.ts:161`).
- `dialog setError` takes a message string, not an `Error` (`dialog.ts:36`).
- `useList` `data` is `null` before the first response (`useList.ts:72`).
- `useDoc` has no `cacheKey` (this is why `DATA.md` was split out).
- `await submit(params)` — our COMPONENTS.md writes `submit(params)` without
  `await` in one place; the promise only sequences under the `refetch: false`
  default.
- `PageHeaderTitle` takes `title` **or** a default slot that overrides it.

### Components in the library but missing from our COMPONENTS.md

Directory listing of `src/components/` cross-checked against
`https://ui.frappe.io/llms.txt` and against our `COMPONENTS.md`.

**No entry at all in our COMPONENTS.md** (exported from the root barrel,
`src/index.ts`):

- `ContextMenu`
- `Menu` (the primitive behind Dropdown; `MenuOption` / `MenuGroupOption` /
  `MenuOptions` types)
- `Radio`
- `Skeleton`
- `Duration`
- `ErrorMessage` (used in one of our own snippets but never defined)
- `Icon` (we document the CSS-class idiom, never the `Icon` component)
- `ItemListRow` (called legacy in SKILL.md rule 2, but it is still root-exported
  and still has a docs page)
- `ThemeSwitcher` (and, as of beta.56, its move to experimental)

**Named only inside a run-on sentence in the "App shell" paragraph, with no
props, slots or usage** — this is the group that matters most for a mobile pass:

- `MobileShell`, `MobileNav` / `MobileNavItem`
- `DesktopShell`
- `BottomSheet`
- `PageHeader` / `PageHeaderBase` / `PageHeaderMobile` / `PageHeaderTarget` /
  `PageHeaderBackButton`
- `Rail` / `RailItem`
- `SettingsDialog`
- `Sidebar` family (only `SidebarCard` gets real detail)

**Composables exported from the root barrel and absent from the skill entirely**
(`src/index.ts:140-200`, `src/composables/`):

- `usePageMeta`
- `useColorScheme` / `resolvedColorScheme`
- `shellScrollContainer` / `useShellScrolled`
- `useSheetDrag`
- `usePortalTarget` / `providePortalTarget` / `portalTargetKey`
- `vFocus` / `vOnOutsideClick` directives
- `upload` / `useFileUpload` / `FileUploadHandler` / `isPrivateUpload`
- `dayjs` / `dayjsLocal`, `debounce`

**Wrong**, as above: `Calendar` is listed as a root component; it is experimental.

### Proposed edits

Given the finding, "patch our COMPONENTS.md" is the wrong shape of fix. Two
options, in order of preference:

**Option 1 (recommended) — replace, don't patch.**

Pull the current upstream skill wholesale:

```
npx skills add https://github.com/frappe/frappe-ui/tree/main/skills/frappe-ui
```

or copy `skills/frappe-ui/` from an updated frappe-ui checkout. That gets
`SKILL.md` + `CORE.md` + `DATA.md` + `SETUP.md`, all 59 defect fixes, and the
eval harness that gates future changes. It also deletes `COMPONENTS.md`,
`TOKENS.md` and `DESIGN.md`, so anything of ours in those files must be
re-homed first — **but there is nothing of ours in them: all five files are
byte-identical to upstream.** There is literally nothing to preserve. This is a
clean swap.

Cost: our checkout at `a89a95fa9` does not have the new skill. We must either
`git fetch` upstream into that checkout (no remote is configured — add one), or
fetch the four files from `raw.githubusercontent.com/frappe/frappe-ui/main/skills/frappe-ui/`.

**Option 2 (fallback, if we insist on keeping our own fork) — the minimum
correctness edits**, all against the files we have today:

1. `SKILL.md` rule 4 — delete `orange` from the theme list.
2. `SKILL.md` rule 9 — `dialog.confirm / alert / prompt` → `dialog.confirm /
   prompt / danger`.
3. `SKILL.md` "Authoritative upstream docs" — it points at `PHILOSOPHY.md` and
   `CONTEXT.md` "at the repo root". Upstream cut this section because neither
   ships in the package (`files` is `src, vite, icons, tailwind, vitepress,
   experimental`) and 0 of 8 eval agents ever followed the pointer. Repoint at
   `src/`, specifically the 74 generated `.api.md` prop tables next to each
   component — those are the real API reference.
4. `COMPONENTS.md` Imperative dialogs — rewrite the block: drop `dialog.alert`,
   change `prompt` to the handle + `onConfirm` shape, add `dialog.danger`.
5. `COMPONENTS.md` Popover — `#target`/`#body` → `#trigger`/`#default`.
6. `COMPONENTS.md` Button — `size` becomes `xs | sm | md | lg`; `theme` becomes
   `gray | blue | green | red`.
7. `COMPONENTS.md` Dropdown — group shape `{ group, options }`, and note
   `placement` is `side` / `align`.
8. `COMPONENTS.md` Tabs — `v-model`, not `v-model:tab`.
9. `COMPONENTS.md` Lists & data — move `Calendar` out to an "Experimental"
   subsection alongside `CommandPalette`; add `ListView`, `TextEditor`,
   `Accordion`, `CodeEditor`, `FloatingWindow`, `MultiEmailInput`,
   `SpriteIcons`, and the parked v1 `Charts`, all of which live in
   `experimental/`.
10. `COMPONENTS.md` Charts — split the prop guidance by family (axis vs
    donut/funnel vs heatmap vs sankey), add `title`/`subtitle`/`NumberCard`,
    and state there is no `height` prop.
11. `COMPONENTS.md` — add a "Composables" section covering the ten root exports
    listed above.
12. `COMPONENTS.md` — add real entries for `MobileShell`, `MobileNav`,
    `BottomSheet`, `PageHeader*`, `Rail`, `SettingsDialog`, `ContextMenu`,
    `Menu`, `Radio`, `Skeleton`, `Duration`, `ErrorMessage`.

Option 2 is roughly a rewrite of `COMPONENTS.md`, which is why Option 1 wins.

---

## (c) The official mobile switching pattern

### There is no official breakpoint composable — deliberately

The library **removed** the one it had. From
`/Users/deathstarconsole/company_projects/frappe/develop/apps/frappe-ui/docs/content/docs/changelog.md:1842-1846`:

> **`useScreenSize`, `useIsMobile` and `ScreenSize` are no longer exported.** They
> were a thin wrapper over a `resize` listener that the library never used itself.
> Copy the ~20 lines into your app, or use `@vueuse/core`'s `useWindowSize` /
> `useMediaQuery`.

So the answer to "route-based or CSS-based?" is **neither** — it is
**app-owned media query, rendering two different component trees.** The two
shells are explicitly *not* one responsive component.

`src/components/MobileShell/MobileShell.md:5-9`:

> It's a separate family from [`DesktopShell`] — mobile and desktop are
> different navigation models, so **the app chooses which to render for the
> viewport** rather than toggling one responsive component.

`src/components/DesktopShell/DesktopShell.md:4-6` says the same from the other
side, and adds the mechanism that makes the swap safe
(`DesktopShell.md:18-21`):

> Because the registry is a stack, swapping `DesktopShell` for `MobileShell` on
> a viewport change hands the active container over cleanly.

i.e. `shellScrollContainer` and `useShellScrolled()` follow the swap
automatically; you do not need an app-level scroll global.

### The code, from a real source file

The only place in the repo that switches platforms is the docs recipe harness.
`docs/components/recipes/RecipeExample.vue:10` and `:32`:

```js
import { useMediaQuery } from '@vueuse/core'
...
const isSmallScreen = useMediaQuery('(max-width: 640px)')
```

with the two trees kept as sibling slots,
`docs/components/recipes/RecipeExample.vue:186-187`:

```html
<div v-show="platform === 'desktop'"><slot name="desktop" /></div>
<div v-show="platform === 'mobile'"><slot name="mobile" /></div>
```

Honest caveat: `RecipeExample.vue` is a docs *gallery* wrapper that shows both
platforms side by side, so it uses `v-show`. **For an app you want `v-if`**, so
only one shell mounts and only one registers into the scroll-container stack.
I could not find a first-party app-level example in this repo — every recipe
ships as a separate `*Mobile.vue` / desktop SFC pair
(`docs/components/recipes/{Files,Tasks,Deals,Tickets,Discussions,Compose,Accounting,Mail}Mobile.vue`)
with the demo route choosing one. That pairing *is* the pattern: **one SFC per
platform per screen, chosen above the router.**

### BottomSheet vs Dialog — there is an explicit rule

`src/components/BottomSheet/BottomSheet.md:49-55`:

> - Use `Dialog` on desktop and `BottomSheet` on mobile. They are separate
>   components rather than one responsive component, because the two have
>   different dismiss affordances and different content rhythms.
> - The sheet takes no `actions` prop. Put buttons in the default slot, where
>   they can sit inside the scroll region or below it as the layout needs.

Also documented there and absent from our skill: the sheet caps at 90% viewport
height then scrolls internally; `dismissible: false` disables outside-click,
`Escape` **and** swipe-down together; a drag starting inside a scrolled list
scrolls the list until it is back at top; `update:open` fires when closing
*starts*, `after-leave` when the animation *ends* (use the latter to reset state
that would flicker); and the gesture engine is exported as `useSheetDrag` for
your own surfaces.

### Safe-area insets and PWA standalone

The library handles the two shell edges for you, and only in standalone mode:

`src/components/MobileShell/MobileShell.vue:6-10`:

```html
<!-- Pages teleport their headers here. Extra top padding clears the notch /
     status bar when running as an installed PWA (display-mode: standalone). -->
<PageHeaderTarget
  class="[@media(display-mode:standalone)]:pt-[env(safe-area-inset-top)]"
/>
```

`src/components/MobileNav/MobileNav.vue:4`:

```html
class="grid shrink-0 auto-cols-fr grid-flow-col border-t border-outline-gray-2 bg-surface-elevation-2 [@media(display-mode:standalone)]:pb-4"
```

Note the asymmetry, which is worth writing down: the **top** uses
`env(safe-area-inset-top)`, the **bottom nav uses a flat `pb-4`**, not
`env(safe-area-inset-bottom)`. Any *app-owned* pinned footer (a composer bar, a
sticky CTA) must add its own inset — the pattern to copy is
`docs/components/recipes/MailMobile.vue:683`:

```html
class="flex items-center gap-2 border-t border-outline-gray-1 bg-surface-base px-4 py-3 [@media(display-mode:standalone)]:pb-[env(safe-area-inset-bottom)]"
```

Our `DESIGN.md:155-156` already carries exactly this one line. Good — but it is
the *only* mobile-mechanics fact in the whole skill.

Also from `MobileShell.vue:17-21`: the content area deliberately uses **native**
momentum scroll (`overflow-y-auto overscroll-auto
[-webkit-overflow-scrolling:touch]`), **not** `ScrollArea`. This directly
contradicts our SKILL.md rule 2 ("scroll regions → `ScrollArea`") on mobile, and
should be called out as an exception.

### Touch target sizing

**Not found.** I searched `src/`, `docs/content/docs/` and the component `.md`
files for touch-target, hit-area or minimum-tap guidance and found none. The
library gives you `Button` sizes `xs | sm | md | lg`
(`src/components/Button/types.ts:5`) and `MobileNav`'s equal-width grid columns,
but states no 44px/48px rule anywhere. Our `DESIGN.md:104-113` has row heights
(`h-15` desktop → `h-17` mobile) and icon sizes (`size-5` mobile row leading),
which is the closest thing to a house rule and appears to be our own synthesis
rather than an upstream one. **If we want a touch-target rule we have to author
it; upstream has no position to copy.**

---

## (d) External skills — verdict

### The one that matters: the official frappe-ui skill

Not "external" at all — it is first-party, it ships in the repo we already have
checked out, and **we are already running an old copy of it**. See section (b).
Install command from the frappe-ui readme:

```
npx skills add https://github.com/frappe/frappe-ui/tree/main/skills/frappe-ui
```

**Verdict: adopt, immediately.** This is the single highest-value action in this
report. It replaces a skill with 59 known API defects with one that is
eval-gated (`skills/frappe-ui/evals/`) and scores 19/20 API-correct source-blind.

### `frappe/skills` — the official Frappe org skill repo

https://github.com/frappe/skills. Contains `frappe-app-dev`,
`quality-code-review`, `code-style`, `technical-writing`, `ui-design`,
`draft-security-advisory`. **We already have all six of these installed** —
`frappe-app-dev`, `quality-code-review`, `code-style`, `technical-writing`,
`ui-design` are in our skill list verbatim. No frappe-ui skill, no gameplan
skill, no mobile skill in it. Worth a periodic `git pull` for updates, nothing
new to install.

### Is there a "gameplan" skill?

**No.** I found none in `frappe/skills`, none in `frappe/gameplan`, and none in
any third-party collection. Gameplan is a *reference app* people read, not a
packaged skill. It is also pinned to frappe-ui beta.51, four betas behind us, so
it is a weak reference for current API shapes — worth reading for product
patterns, not for API correctness. Do not invent one; if we want gameplan
conventions captured, that is a skill *we* would have to author.

### Third-party Frappe skill collections

These exist and are unvetted. Listing them for completeness, not recommending:

- `netchampfaris/frappe-agent-skills` — by a frappe/frappe maintainer; likely the
  personal precursor to `frappe/skills`. Closest to trustworthy of the third
  parties.
- `lubusIN/frappe-skills` — DocTypes, APIs, Desk, frontend, reports, testing.
- `Dkm0315/frappe-agent` — multi-tool plugin (Codex/Claude/Cursor/Copilot),
  claims frontend guidance for Vue/React/frappe-ui/desk/www.
- `UnityAppSuite/frappe-claude` — "frappe-fullstack" plugin, 11 agents including
  `frappe-frontend`.
- `OpenAEC-Foundation/Frappe_Claude_Skill_Package` and its fork
  `Impertio-Studio/…` — "60 deterministic Claude skills for Frappe v14-v16".
- A community MCP wrapper posted to the forum:
  https://discuss.frappe.io/t/mcp-frappe-skills-searchable-frappe-skills-for-ai-coding-agents-mit-github/162955

**Verdict: skip all of them.** None is frappe-ui-specific, none is eval-gated,
and several target ERPNext v14-v16 rather than a standalone frappe-ui SPA. The
first-party frappe-ui skill dominates every one of them for our use case, and
adding overlapping Frappe skills on top of the `frappe-app-dev` we already run
would just create conflicting guidance. I did not audit any of their contents —
that judgement is on scope and provenance, not on quality I measured.

---

## Recommended order of action

1. **Replace `~/.claude/skills/frappe-ui/` with upstream `main`.** Highest
   value, zero merge cost (our copy has no local changes). Do this before the
   mobile pass, not during it.
2. Add a git remote to the local frappe-ui checkout so it stops being a dead
   snapshot — this whole audit had to route around its absence.
3. Bump `dashboard/package.json` to an exact `1.0.0-beta.56` in its own commit,
   after grepping for the three breaking items.
4. Author the two things upstream does **not** give us, as house additions:
   a touch-target rule, and the app-level `v-if` shell-switch snippet (upstream
   only ships a `v-show` docs-gallery variant).

## What I could not verify

- Whether ui.frappe.io's live `llms.txt` reflects beta.56 (it still lists
  ThemeSwitcher under Components, contradicting the beta.56 barrel move).
- The exact contents of upstream's current `CORE.md` / `DATA.md` — I have their
  sizes and the commit-message summary of what changed, not a line-level read.
- The dozen upstream-claimed defects I listed as "not independently re-verified"
  in section (b); I re-verified six of the eight headline ones and cite source
  for those.
- The quality of any third-party skill collection — judged on provenance only.
