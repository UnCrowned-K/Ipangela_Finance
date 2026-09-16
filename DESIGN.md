---
name: Profit Optimizer (Mobile Money)
description: SA phone-banking world — black till at night, paper ledger in daylight, one money-green accent, tabular money.
colors:
  money-green: "#3ddc8e"
  black-ground: "#0a0f0c"
  plate: "#101612"
  paper-ground: "#f4f1e8"
  paper-card: "#ffffff"
  deep-leaf: "#0f6b44"
  leaf-500: "#1fa868"
  ink-dark: "#16140f"
  ink-light: "#eef4ef"
  ledger-hairline: "rgba(255,255,255,0.13)"
  paper-border: "#e4e0d3"
  led-red: "#ff5c62"
  led-amber: "#ffb020"
  led-blue: "#4da3ff"
  success-green: "#10b981"
typography:
  display:
    fontFamily: "Space Grotesk, Inter, sans-serif"
    fontSize: "calc(1.25rem + 1vw)"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  body:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  money:
    fontFamily: "Space Mono, JetBrains Mono, Fira Code, monospace"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.4
    fontFeatureSetting: "'tnum' 1"
rounded:
  sm: "4px"
  md: "6px"
  lg: "12px"
  full: "9999px"
spacing:
  xs: "2px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  rail: "12px"
components:
  button-primary:
    backgroundColor: "{colors.deep-leaf}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "10px 18px"
  button-primary-dark:
    backgroundColor: "{colors.money-green}"
    textColor: "#04130b"
    rounded: "{rounded.sm}"
    padding: "10px 18px"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.ink-light}"
    rounded: "{rounded.sm}"
    padding: "10px 18px"
  status-led:
    backgroundColor: "{colors.led-red}"
    textColor: "{colors.led-red}"
    rounded: "{rounded.full}"
    height: "8px"
    width: "8px"
---

# Design System: Profit Optimizer (Mobile Money)

## Overview

**Creative North Star: "The Till at Night"**

The interface is the everyday SA phone-banking screen rebuilt as a whole product world: a terminal-grade money interface where the operator stands beside the till and reads the day at a glance. The world has two states of matter — the black till at night (the default engaged screen) and the paper ledger in daylight (the lighter theme and the printed invoice sheet). On both, money is the hero: every amount is a tabular Space Mono figure sitting on a ruled plate, statuses are LEDs rather than pills, and the only color that means anything is the money green.

This product refuses the SaaS-finance default — cream cards, rounded-everything, corporate blue-green, decorative illustrations. Instead: jet-black ground, one fresh money-green accent, hard geometric type, 1px ledger hairlines, and LED status dots. Zero ornament; trust comes from the register.

**Key Characteristics:**
- Near-black graphite ground with raised plates every surface sits on.
- 1px hairline rules create the ledger; nothing floats off the grid.
- Status is a lit LED (6–8px dot), never a badge pill.
- Money, codes, and data always render in tabular Space Mono.
- Flat hard corners (4–12px); buttons are flat rects or green fills.
- Dark is the flagship theme; light paper is the secondary mode and the invoice sheet.

## Colors

The palette is a two-state register: black graphite for the engaged screen, warm paper for the daylight theme and the printed sheet. One money-green carries meaning; amber, red, and blue are LEDs for states only.

### Primary
- **Money Green** (#3ddc8e): the flagship accent. Primary buttons in dark mode, the active rail item, the Optimizer CTA, positive amounts, and the focus ring. Always a green fill or a hairline-rule accent — never a glow.
- **Deep Leaf** (#0f6b44): the light-theme primary — white buttons on paper, section titles, and the primary action on paper surfaces.

### Secondary
- **Leaf 500** (#1fa868): light-theme companions to deep leaf; hover and complementary actions.

### Tertiary
- **LED Red** (#ff5c62): overdue/expense states and destructive actions.
- **LED Amber** (#ffb020): warnings, budget pressure.
- **LED Blue** (#4da3ff): informational, Sent states, external references.

### Neutral
- **Black Ground** (#0a0f0c): default page field (dark).
- **Plate** (#101612): raised card/rail surface on the black ground.
- **Paper Ground** (#f4f1e8): default field in light mode.
- **Paper Card** (#ffffff): raised surface in light mode and the invoice/print sheet.
- **Ink Dark** (#16140f): primary text on paper.
- **Ink Light** (#eef4ef): primary text on black.
- **Ledger Hairline** (rgba(255,255,255,0.13)): dark-theme 1px rules; light uses paper-border (#e4e0d3).
- Warm graphite neutrals (50–900) step between ground and ink; never blue.

### Named Rules
**The One Green Rule.** Money green is used sparingly and always means money or action. It appears as a fill, a hairline, or a focus ring — never as a gradient, glow, or ambient wash.

**The LED Rule.** A status is a lit dot (6–8px, fully rounded, colored, optionally a soft 3px halo ring). Never a pill, badge, or gradient chip. Canceled/unread states dim to 60% opacity.

## Typography

**Display Font:** Space Grotesk (fallback: Inter, sans-serif)
**Body Font:** Inter (fallback: -apple-system, Segoe UI, sans-serif)
**Money/Mono Font:** Space Mono (fallback: JetBrains Mono, Fira Code, monospace)

**Character:** Geometric, hard, terminal-grade. Space Grotesk carries the face for headings, labels, and the app logo; Inter handles reading; Space Mono handles every numeral and code in tabular form. The pairing reads like a cash register's display seated in a clean ledger.

### Hierarchy
- **Display** (700, clamp ~1.25–2.4rem, 1.1): page titles and the wordmark, letter-spacing −0.02em and never looser.
- **Headline** (700, 2.441rem, 1.1): section titles (finance section headers).
- **Title** (600, 1.563rem, 1.25): card titles and modal headers.
- **Body** (400, 1rem, 1.5): reading copy; keep measure around 65–75ch.
- **Label** (500, 0.8rem, 1.25): form labels and stat-cell labels, always uppercase-ish small on a hairline.
- **Money** (400/700, 1rem, 1.4, tabular): every amount via `.money`, `.value`, and spreadsheet cells — Space Mono with `font-variant-numeric: tabular-nums lining-nums` and `"tnum"`.

### Named Rules
**The Tabular Money Rule.** Every displayed amount, value, or code uses Space Mono with tabular numerals. Ordinary body text never uses the mono face; mono is reserved for data and measurement.

## Layout

The app is a full-width top navigation bar (h: 56px, sticky, hairline under) plus a full-bleed content field. The bar is a plate register: wordmark top-left (Space Grotesk 700), primary nav inline (Optimizer / Finance / Invoices) with the active item a green-tinted block, and a compact right cluster (theme toggle, account menu) — no left rail, so the invoice workspace and finance dashboard use the whole viewport width. Content columns follow the 8px spacer scale (2/8/16/24/32px), grouped tightly with generous section separation and more space above headings than below. Four money plates form the finance dashboard top row (mono label, large mono value, hairline rule, status LED). On small viewports the top bar collapses to wordmark + hamburger + account menu; the hamburger drops a full-width panel of primary nav links, and tables wrap in `.table-responsive` with horizontal scroll preserved.

## Elevation & Depth

Flat by default. Depth is carried by tonal layering of the two-state register (plate on ground) and 1px hairlines, not by big ambient shadows. Shadows exist only as small register shadows in dark mode (single-line, low opacity) and subtle lift on hover for interactive cards. No hard offset block shadows, no glow blobs, no drop-shadow decorations outside focus rings.

### Shadow Vocabulary
- **Register shadow** (`0 1px 3px rgba(0,0,0,0.55), 0 1px 2px rgba(0,0,0,0.4)`): raised plates on the black ground (dark).
- **Hover lift** (`--shadow-lg` soft enlargement): interactive cards on hover only.

### Named Rules
**The Flat-By-Default Rule.** Surfaces are flat at rest; shadows respond only to state (hover, focus, elevation). A zero-offset glow is a decoration and banned.

## Shapes

A square, ledger geometry. Radii are small and categorical: 4px for buttons and status chips, 6px for flat engineered cards and toasts, 12px for modals and the auth card plate, full round for LED dots only (8px tall elements). Borders are 1px hairlines in the surface color; nothing is rounded soft, glassy, or pill-styled except the LED itself.

## Components

### Buttons
- **Shape:** flat hard rect, 4px radius, no shadow at rest.
- **Primary:** green fill — dark mode uses money green (#3ddc8e) with near-black text (#04130b); light mode uses deep leaf (#0f6b44) with white text. Padding 10px 18px.
- **Hover:** one step lighter (money-green 400 / leaf hover); transitions use expo-ease `cubic-bezier(0.16,1,0.3,1)`, never bounce.
- **Secondary:** transparent with a hairline border and surface text; hover fills to the plate color.
- **Complementary (dark):** translucent money-green plate (rgba(61,220,142,0.14)) with money-green text and a 30%-alpha green border.

### Status LED lines
- **Style:** inline-flex mono label + an 8px fully-rounded dot; the dot carries a 3px soft halo ring in its color on active states.
- **States:** paid/success (green), sent/info (blue), draft (secondary text, gray dot), overdue (red), canceled (muted, 60% opacity). Messages and toasts use the same LED treatment against flat ground.

### Cards / Containers
- **Corner Style:** 6px flat engineered cards (12px for modal plates and the auth card).
- **Background:** plate on black (dark) or white on paper (light).
- **Shadow Strategy:** register shadows only in dark; hover lift for interactive cards. Never nested cards.
- **Border:** 1px hairline.
- **Internal Padding:** 16–24px (rail 12px).

### Inputs / Fields
- **Style:** 1px hairline stroke on the ground, transparent interior, 4px radius.
- **Focus:** money-green border (primary-400) + a 3px soft focus ring `rgba(61,220,142,0.18)` plus `:focus-visible` outlines. Form errors tint the label and border in LED red.
- **Disabled:** muted text, dimmed hairline.

### Navigation
- Top bar (56px, sticky, plate on ground): wordmark top-left (Space Grotesk 700), primary links inline (Optimizer / Finance / Invoices) allowing per-page extension (Optimizer file links), right cluster = theme toggle + account menu (Profile / Contact / Sign Out).
- Hover: translucent green plate. Active: green-tinted block, bolded (no side stripe, no pill).
- Account menu sign-out is the destructive exception: text red (tailwind red-600 / -700 light ramp, rgba(220,38,38,0.08) hover plate) — the only canonical use of red-as-action, distinct from status LED red.
- Mobile (<768px): hamburger drops a full-width panel of primary links over the content, hairline bottom; account menu stays anchored right. Toggling persists nothing; open closes on link pick, outside click, or Escape.

### Browser surfaces
- Scrollbars, text selection, and the caret are themed from the register palette in both themes; caret and selection use money green.
- Toast container is `aria-live`; modals carry `role="dialog"`, `aria-modal`, and Escape-to-close.

## Do's and Don'ts

### Do:
- **Do** set every page field to the theme's ground and every surface on it a raised plate.
- **Do** render every amount, value, ID, and code with Space Mono tabular numerals.
- **Do** represent status with a colored 8px LED dot (with its soft halo) and a mono label.
- **Do** keep corners categorical: 4px buttons/chips, 6px cards, 12px modals and auth plates.
- **Do** use the money green as a flat fill, hairline, or focus ring — it is earned, not ambient.
- **Do** keep animations to a single authored moment with expo ease-out, and honor `prefers-reduced-motion`.

### Don't:
- **Don't** use gradient text, glassmorphism, or colored `border-left`/`border-right` stripes above 1px on cards, list items, or alerts.
- **Don't** use bounce easing, layout-triggering width/margin animations, or glow blobs.
- **Don't** use a badge pill for status, decorative illustrations, or a SaaS blue-green corporate palette.
- **Don't** use monospace for non-data prose — mono is reserved for measurement.
- **Don't** add kickers/eyebrows above headings, section numbering as decoration, or hard offset block shadows outside a genuinely neobrutalist world.