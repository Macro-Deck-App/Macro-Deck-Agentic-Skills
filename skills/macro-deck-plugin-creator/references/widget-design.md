# Widget design guidelines

Use these when the plugin draws widgets, folder views, config views or other Macro Deck UI and the
user has not specified a look. If the user specified a design, follow the user. The guidelines are
derived from how the official widgets are built, in a calm, glanceable, card-like style: one clear
primary value, quiet supporting text, generous spacing, rounded tiles, restrained color.

## Derive from the source, do not trust this file's numbers

The numbers below were read from the official widget views at the time this skill was written and
will drift. Before designing, read the current source and the docs, then derive the style again:

- Official widget views: the Macro Deck repository, `host/src/MacroDeckHost.Widgets/` (weather,
  clock, music player, slider, history graph, timers; also `WidgetSafeArea.cs`).
- Docs: `/ui/` (components, sizing, theming, responsive, widget types, developer preview) and
  `/ui/views/widget/` and `/ui/views/widget-types/`.
- The component pages for every component you use; do not guess properties.

Pick the official widget closest to yours (a value tile, a list/forecast, a media card, a control
with a slider) and mirror its structure.

## Principles

1. **Glanceable.** One primary element dominates (a value, a title, an artwork). Everything else
   supports it and can be dropped when the tile is small.
2. **Hierarchy through weight, size and role, not color.** Primary value: large and bold. Title or
   condition: medium size, semibold. Supporting text: smaller, secondary role. Incidental text: muted
   role. Use at most three to four text styles per tile.
3. **Theme roles first.** Use the primary, secondary and muted text roles and let the reader repaint
   them for light and dark themes. Send a literal `#rrggbb` only where the color is data (a status
   color, a user-chosen tint). Do not hardcode text colors that break in the other theme. Leave the
   accent unset so it follows the reader's accent, unless the color carries meaning.
4. **Restraint.** No background unless the user can configure one or the content needs it (alerts).
   No borders, shadows or decoration by default. A single accent color at most, plus semantic colors
   (green ok, red alert, grey paused) where state needs them.
5. **Proportional, not pixel based.** Every length is a fraction of the tile's basis, so one tree is
   correct at every size. Cap text that should not grow with the tile (captions) so a one-cell and a
   nine-cell widget read consistently. Never use fixed pixel sizes.
6. **Rounded-tile awareness.** Keep content inside the safe area the official widgets use (the
   shared safe-area helper): inset by the larger of the tile spacing and the corner clearance, so
   nothing runs under a rounded corner. Read the corner radius from the surface and fall back to the
   default. Do not place text against the raw edge.
7. **Consistent rhythm.** Gaps are small fractions of the basis (official views use roughly 0.01 to
   0.04, larger only between distinct groups). Related items are close, groups are separated.
8. **Honest states.** Every widget handles: loading, not configured, unavailable or offline,
   error, empty, and long or missing data. The unavailable state is a centered title (secondary role,
   semibold) with a one or two line hint (muted role, capped lines) that tells the user what to do.
9. **Calm motion.** Update values in place through reactive state; avoid flashing, spinners that
   never end, and animations that move layout.

## Typical type scale (fractions of the basis, from the official views)

Treat as starting values, then verify visually at 1x1, 2x1, 1x2 and 2x2.

| Role in the tile | Size | Weight | Text role |
| --- | --- | --- | --- |
| Hero value (time, temperature, level) | about 0.17 to 0.26 | bold | primary |
| Title or condition | about 0.10 to 0.12 | semibold | primary |
| Supporting label, unit | about 0.07 to 0.11 | medium or semibold | secondary |
| Caption, hint, timestamp | about 0.05 to 0.08 | regular or medium | muted |

Give texts a `MinSize` (roughly 60 to 70 percent of the size) so they shrink before they ellipsize,
and a `MaxLines` on hints. In a row where a sibling fills, give each text its own `MainSize`.
Icons and artwork: about 0.16 to 0.20 of the basis for a header icon, about 0.06 to 0.09 for inline
row icons. Slider and progress thickness: about 0.025 to 0.07.

## Layout patterns

- **Value tile.** Vertical stack, space between: top row (icon left, hero value right-aligned),
  below it a label stack (title semibold, subtitle secondary).
- **List or forecast.** A header block at about 0.4 of the height, then rows that each `Fill`
  equally: leading label and icon, trailing values, an optional range or progress bar in between.
  Cap row text so many rows do not outgrow their row height.
- **Media card.** Artwork dominates, text overlaid or below, a thin timeline, transport controls
  only when there is room; hide secondary rows in small sizes.
- **Control tile (slider, toggle).** Label on top, value, then the control with the reader's
  accent; a clear off/disabled treatment.
- **Responsive.** Use the responsive component to switch layouts by tile shape (1x1, 2x1, 1x2)
  instead of cramming one layout. Smaller tiles drop optional rows first (location, units, forecast),
  never the primary value.
- **Configurable bits.** Offer toggles for optional elements (show icon, show location) and the
  standard appearance (background, label, colors, font) when the platform offers it; defaults
  should look right with no configuration.

## Content rules

- All user-facing text comes from localization resources, passed as localization references so
  each client renders in its own language. Do not format numbers or dates into plain strings for
  display; use the localized formats and keep units in resources.
- Handle missing or non-finite numbers with a localized placeholder, never `NaN` or empty.
- Icons: SVG or PNG assets you may redistribute (see [licensing.md](licensing.md)), registered
  through the UI resources API. Keep the style consistent: one weight, one corner style, one set.
  Do not use the Macro Deck logo as the plugin's identity.
- Picker card: when registered as a widget type, draw a representative sample without reading
  live data; nothing is connected while someone chooses a type.

## Performance and visual effects

Widgets redraw often, on many devices, some of them weak. Visual effects cost frame time and battery.

- **Never reproduce reflections** (mirrored copies, glossy floor reflections, flipped faded duplicates,
  glass shine overlays), even when a creator's example, mockup or screenshot shows them. Reproduce the
  rest of the example's layout, hierarchy and colors, leave the reflection out, and say so in the
  report. Do not emulate a reflection with duplicated trees, masks or layered gradients either.
- **Complex shadows**: do not copy stacked, blurred, large-radius or colored shadows from an example.
  Prefer no shadow. If depth is wanted, use the cheapest equivalent the official components offer
  (a subtle background tint, a thin border, an opacity step) and only on elements that need it.
  Never animate shadows.
- Avoid effect stacks: nested masks, multiple gradients, large blurs, full-size overlays, many layered
  translucent elements. One simple background or gradient per tile at most.
- Keep the tree small: no more nodes than the design needs, conditional nodes for optional parts,
  keyed repeats for lists, no per-frame rebuilding of unchanged subtrees. Update through reactive
  state rather than replacing the view.
- Update only when a visible value changes, throttle fast sources (audio levels, positions) to what
  the eye can use, and never poll faster than the data changes. No endless animation on idle tiles.
- Cache and size artwork: decode once, register resources once, scale images to the size shown,
  avoid huge source images.
- Measure when in doubt: compare frame behavior and CPU in the developer preview or a real host with
  the effect on and off; drop the effect when the difference is noticeable on a modest machine.

## Develop with the preview CLI

Develop widgets against `macrodeck-plugin preview render`
(https://docs.macro-deck.app/cli/preview/), not by guessing. It loads the plugin against a disposable
stub host and renders every `[UiPreview]` scenario to a PNG. It needs no running Macro Deck and no
sign-in, only a local Chrome, Chromium or Edge (`--browser` or `MACRODECK_BROWSER` when it is not
found). Verify the options with `macrodeck-plugin preview render --help`; at the time of writing they
include `--project`, `--size <W>x<H>`, `--cells <C>x<R>`, `--preview <name>`, `--scale`,
`--theme dark|light`, `--background`, `--radius`, `--locale` and `--output`.

Loop: write the view and its `[UiPreview]` scenarios first, render, read the PNGs with vision, fix,
render again. Write the images outside the repository (`--output <dir outside the repo>`). Render
each scenario at 1x1, 2x1, 1x2 and 2x2 (`--cells`) in both themes. Exit code 1 means a scenario
failed to build or draw (the other images are still written), 2 is a usage error, 3 a build failure
or no browser. Scenarios must be static, parameterless methods without tile access, and the clock is
fixed, so time-driven behavior and interactions need the real host (see below). Text uses the
installed fonts, so small differences from other machines are expected.

## Verify visually

Add developer-preview scenarios (the preview attribute of the UI package) for: normal, long text,
unavailable, error, empty, loading, and the extremes of the value range. Inspect them at the tile
sizes and both themes (see [testing-and-debugging.md](testing-and-debugging.md#runtime-and-ui-validation)).
Look for: clipped or overlapping text, content under rounded corners, unreadable contrast in either
theme, inconsistent gaps, jumping layout on update, hardcoded colors that ignore the theme.
