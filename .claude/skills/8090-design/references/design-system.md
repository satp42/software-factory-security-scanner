# 8090 Design System Reference

## Table of Contents

- [Colors](#colors)
- [Brand Color Opacity Scale](#brand-color-opacity-scale)
- [Semantic State Colors](#semantic-state-colors)
- [Typography](#typography)
- [Layout](#layout)
- [shadcn/ui Nova Components](#shadcnui-nova-component-style)
- [Illustration Style](#illustration-style--industrial-blueprint-editorial)
- [Accessibility](#accessibility)
- [Motion & Transitions](#motion--transitions)
- [Dark Mode Strategy](#dark-mode-strategy)
- [Tailwind Config](#tailwind-config)

---

## COLORS

| Role | Tailwind Token | Hex | Usage |
|------|---------------|-----|-------|
| **Primary Accent** | `brand` (custom) | `#0052CC` | ONE accent element per panel (Factory Blue) |
| **Background** | `bg-slate-50` | `#f8fafc` | Page canvas |
| **Surface / Cards** | `bg-white` or `bg-slate-100` | `#ffffff` / `#f1f5f9` | Card panels, containers |
| **Border / Dividers** | `border-slate-200` | `#e2e8f0` | Panel edges, separators, hairlines |
| **Secondary Text** | `text-slate-500` | `#64748b` | Captions, metadata, supporting copy |
| **Body Text** | `text-slate-700` | `#334155` | Paragraphs, descriptions |
| **Headlines** | `text-slate-950` | `#020617` | All headings, titles, emphasis |
| **Linework / Shadows** | `text-slate-900` | `#0f172a` | Illustration linework, shadows at 15-30% opacity |
| **Muted / Disabled** | `text-slate-400` | `#94a3b8` | Placeholder text, disabled states |

### Color Rules

- Use ONLY Factory Blue (`#0052CC`) as the accent color — map to custom `brand` token
- All neutrals from Tailwind's **slate** palette (`slate-50` through `slate-950`)
- **All brand color variants are the same hue at different opacities** — no separate hex values
- NO gradients on UI surfaces
- ONE blue accent element per panel to highlight the key concept

### Brand Color Opacity Scale (single source: `#0052CC`)

| Token | Class Example | Opacity | Usage |
|-------|--------------|---------|-------|
| `brand` | `bg-brand` / `text-brand` | 100% | Primary buttons, key accent element |
| `brand/80` | `bg-brand/80` | 80% | Hover on primary buttons |
| `brand/60` | `text-brand/60` | 60% | Secondary emphasis, active states |
| `brand/40` | `ring-brand/40` | 40% | Focus rings |
| `brand/20` | `border-brand/20` | 20% | Accent borders, badge outlines |
| `brand/10` | `bg-brand/10` | 10% | Tinted backgrounds, hover surfaces, badges |
| `brand/5` | `bg-brand/5` | 5% | Subtle section highlights |

### Semantic State Colors

Non-brand colors are permitted ONLY for functional states — never decorative.

| State | Text | Border | Background | Button |
|-------|------|--------|------------|--------|
| **Error** | `text-red-500` | `border-red-500` | `bg-red-50` | `bg-red-500 hover:bg-red-600 text-white` |
| **Success** | `text-green-600` | `border-green-600` | `bg-green-50` | `bg-green-600 hover:bg-green-700 text-white` |
| **Warning** | `text-amber-500` | `border-amber-500` | `bg-amber-50` | `bg-amber-500 hover:bg-amber-600 text-white` |
| **Info** | `text-brand` | `border-brand/20` | `bg-brand/5` | Use primary button |

Ghost/outline destructive: `text-red-500 hover:bg-red-50`

---

## TYPOGRAPHY

**Primary Font**: `font-sans` → **IBM Plex Sans** with `-1% letter-spacing`
- Load via `@fontsource/ibm-plex-sans` or Google Fonts (`family=IBM+Plex+Sans:wght@400;500;600;700`)
- Fallback stack: `'IBM Plex Sans', ui-sans-serif, system-ui, -apple-system, sans-serif`
- **Global letter-spacing**: `tracking-[-0.01em]`

**Monospace Font**: `font-mono` → **Geist Mono** (shadcn Nova default)
- Fallback stack: `'Geist Mono', ui-monospace, 'Cascadia Code', monospace`

| Element | Class | Size | Weight | Tracking |
|---------|-------|------|--------|----------|
| **Page Title** | `text-4xl sm:text-5xl` | 36-48px | `font-bold` (700) | `tracking-tighter` |
| **Section Header** | `text-2xl sm:text-3xl` | 24-30px | `font-semibold` (600) | `tracking-tight` |
| **Panel Title** | `text-lg` | 18px | `font-semibold` (600) | `tracking-[-0.01em]` |
| **Body** | `text-base` | 16px | `font-normal` (400) | `tracking-[-0.01em]` |
| **Caption / Meta** | `text-sm` | 14px | `font-medium` (500) | `tracking-[-0.01em]` |
| **Label / Overline** | `text-xs uppercase` | 12px | `font-semibold` (600) | `tracking-widest` |

Base CSS:
```css
body { font-family: 'IBM Plex Sans', sans-serif; letter-spacing: -0.01em; }
```

---

## LAYOUT

**Spacing Scale** (Tailwind 8px base):
- `gap-2` (8px) → tight inner spacing
- `gap-4` (16px) → default component spacing
- `gap-6` (24px) → between related sections
- `gap-8` (32px) → between panels
- `gap-12` (48px) → major section breaks
- `gap-16` (64px) → page-level vertical rhythm

**Grid**:
- Max content width: `max-w-6xl mx-auto` (1152px)
- Panel grid: `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8`
- Padding: `px-6 sm:px-8 lg:px-12`

**Rules**:
- Ample whitespace between panels (`gap-8` minimum)
- One illustration per headline
- Clear visual hierarchy: title at top, panels below
- Cards use `rounded-md border border-slate-200 bg-white shadow-sm`

---

## shadcn/ui NOVA COMPONENT STYLE

### Cards / Panels
```
rounded-md border border-slate-200 bg-white shadow-sm p-6
```

### Buttons (Primary)
```
inline-flex items-center justify-center rounded
bg-brand text-white text-sm font-medium h-10 px-4
hover:bg-brand/80
focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40 focus-visible:ring-offset-2
disabled:opacity-50 disabled:pointer-events-none
transition-colors duration-150
```

### Buttons (Secondary / Ghost)
```
rounded border border-slate-200 bg-white text-slate-700
hover:bg-slate-100 hover:text-slate-900
text-sm font-medium h-10 px-4
disabled:opacity-50 disabled:pointer-events-none
transition-colors duration-150
```

### Buttons (Destructive)
```
rounded bg-red-500 text-white text-sm font-medium h-10 px-4
hover:bg-red-600
focus-visible:ring-2 focus-visible:ring-red-500/40 focus-visible:ring-offset-2
disabled:opacity-50 disabled:pointer-events-none
transition-colors duration-150
```

### Inputs
```
flex h-10 w-full rounded border border-slate-200 bg-white
px-3 py-2 text-sm text-slate-900
placeholder:text-slate-400
focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40 focus-visible:ring-offset-2
disabled:cursor-not-allowed disabled:opacity-50
transition-colors duration-150
```

### Select
```
flex h-10 w-full rounded border border-slate-200 bg-white
px-3 py-2 text-sm text-slate-900
focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40 focus-visible:ring-offset-2
disabled:cursor-not-allowed disabled:opacity-50
```

### Badges / Tags
```
inline-flex items-center rounded-sm
px-2.5 py-0.5 text-xs font-semibold
bg-slate-100 text-slate-700 border border-slate-200
```

### Badge (Brand accent)
```
bg-brand/10 text-brand border-brand/20
```

### Badge (Success)
```
bg-green-50 text-green-600 border border-green-200
```

### Badge (Warning)
```
bg-amber-50 text-amber-600 border border-amber-200
```

### Badge (Error)
```
bg-red-50 text-red-500 border border-red-200
```

### Tabs
```
// Tab list
inline-flex h-10 items-center justify-center rounded bg-slate-100 p-1

// Tab trigger
rounded-sm px-3 py-1.5 text-sm font-medium text-slate-500
data-[state=active]:bg-white data-[state=active]:text-slate-900 data-[state=active]:shadow-sm
transition-colors duration-150
```

### Separator
```
h-px bg-slate-200
```

### Tooltip / Popover
```
rounded border border-slate-200 bg-white shadow-md
px-3 py-1.5 text-sm text-slate-700
animate-in fade-in-0 zoom-in-95 duration-150
```

### Dialog / Modal
```
rounded-lg border border-slate-200 bg-white shadow-lg
p-6 max-w-lg w-full
animate-in fade-in-0 zoom-in-95 duration-200
```

### Nova Principles
- `rounded-sm` (2px) on small elements (badges, tags, tab triggers)
- `rounded` (4px) on interactive elements (buttons, inputs, tooltips)
- `rounded-md` (6px) on cards and panels
- `rounded-lg` (8px) is the **maximum** — reserved for modals and hero containers only
- **Never use `rounded-xl`, `rounded-2xl`, or `rounded-full`** on structural elements
- Borders are always `border-slate-200`
- Shadows are `shadow-sm` (cards) or `shadow-md` (popovers, dropdowns)
- Focus rings use `ring-2 ring-brand/40 ring-offset-2`
- All interactive elements must have `disabled:opacity-50 disabled:pointer-events-none`
- Transitions use `transition-colors duration-150` or `transition-all duration-200`

---

## ILLUSTRATION STYLE — Industrial Blueprint Editorial

### Proportions & Feel
Grounded and realistic, NOT cartoonish. Slightly elongated Bauhaus-influenced figures. Detailed, expressive hands. Accurate equipment proportions. Should feel like **New Yorker** or **Harvard Business Review** editorial illustrations.

### DO:
- Show abstract concepts through physical metaphors (broken chains, tangled cables, cracked nodes)
- Use architectural and engineering visual language
- Show hands doing things
- Depict struggle, friction, or disconnection through the composition itself
- Use hatching, crosshatching, and technical linework textures

### DO NOT:
- Use literal depictions of software, screens showing actual data, or real equipment
- Use generic business imagery (NO robots, light bulbs, targets, gears as decoration)
- Use warning symbols, error icons, or exclamation marks **inside illustrations**
- Add text labels, captions, or annotations inside illustrations
- Use clip art or abstract icons
- Use any accent color other than Factory Blue (`#0052CC`)

### Palette for Illustrations
- **Linework**: `#000000` (black) and `slate-800` (`#1e293b`)
- **Shadows/depth**: `slate-900` (`#0f172a`) at 15-30% opacity
- **Paper tone**: `slate-50` (`#f8fafc`) or warm cream `#f5f3ef` for editorial feel
- **Single accent**: `#0052CC` (Factory Blue) on ONE element per panel

---

## ACCESSIBILITY

### Contrast Ratios (WCAG AA minimum)

| Combination | Ratio | Passes |
|-------------|-------|--------|
| `slate-950` on `white` | 18.5:1 | AAA |
| `slate-700` on `white` | 7.2:1 | AAA |
| `slate-500` on `white` | 4.6:1 | AA (body), AAA (large) |
| `brand` (#0052CC) on `white` | 5.9:1 | AA |
| `white` on `brand` (#0052CC) | 5.9:1 | AA |
| `slate-400` on `white` | 3.0:1 | AA large only |

### Rules
- Body text (`text-sm`+): use `slate-700` or darker — minimum 4.5:1
- Large text (`text-lg`+): `slate-500` acceptable — minimum 3:1
- Placeholder text (`slate-400`): acceptable for placeholders only — never for readable content
- All interactive elements must have visible `focus-visible` states
- Do not rely on color alone to convey meaning — pair with icons or text labels
- Disabled states use `opacity-50` — exempt from contrast requirements

---

## MOTION & TRANSITIONS

### Principles
- Subtle and functional — motion signals state changes, never decorates
- Prefer `duration-150` (fast, snappy) for micro-interactions
- Use `duration-200` for larger transitions (modals, panels)
- Never exceed `duration-300` — no slow fades or dramatic animations

### Standard Patterns

| Interaction | Classes |
|-------------|---------|
| Button hover/focus | `transition-colors duration-150` |
| Card hover | `transition-shadow duration-150 hover:shadow-md` |
| Modal enter | `animate-in fade-in-0 zoom-in-95 duration-200` |
| Modal exit | `animate-out fade-out-0 zoom-out-95 duration-150` |
| Tooltip enter | `animate-in fade-in-0 zoom-in-95 duration-150` |
| Accordion expand | `transition-all duration-200 ease-out` |
| Skeleton loading | `animate-pulse` with `bg-slate-200` |

### Anti-Patterns
- No bounce, spring, or elastic easing
- No auto-playing animations or looping motion
- No parallax scrolling effects
- No transitions longer than 300ms
- Respect `prefers-reduced-motion`: wrap animations in `motion-safe:` prefix

---

## DARK MODE STRATEGY

8090 currently ships **light mode only**. If dark mode is needed in the future:

| Light Token | Dark Equivalent |
|-------------|----------------|
| `bg-slate-50` | `dark:bg-slate-950` |
| `bg-white` (cards) | `dark:bg-slate-900` |
| `border-slate-200` | `dark:border-slate-800` |
| `text-slate-950` | `dark:text-slate-50` |
| `text-slate-700` | `dark:text-slate-300` |
| `text-slate-500` | `dark:text-slate-400` |
| `bg-brand` | Unchanged — `#0052CC` works on dark backgrounds |
| `bg-brand/10` | `dark:bg-brand/20` (slightly higher opacity on dark) |

Do not implement dark mode unless explicitly requested. When implementing, add `dark:` variants to the Tailwind config and toggle via `class` strategy on `<html>`.

---

## TAILWIND CONFIG

```js
// tailwind.config.js — 8090 Design System
const config = {
  theme: {
    extend: {
      colors: {
        brand: '#0052CC',
      },
      fontFamily: {
        sans: ['IBM Plex Sans', 'ui-sans-serif', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['Geist Mono', 'ui-monospace', 'Cascadia Code', 'monospace'],
      },
      borderRadius: {
        sm: '2px',
        DEFAULT: '4px',
        md: '6px',
        lg: '8px',
      },
    },
  },
}
export default config
```

### Font Loading

```html
<!-- Google Fonts (CDN) -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
```

```bash
# Or via npm
npm install @fontsource/ibm-plex-sans
```

```js
// Import in entry file
import '@fontsource/ibm-plex-sans/400.css'
import '@fontsource/ibm-plex-sans/500.css'
import '@fontsource/ibm-plex-sans/600.css'
import '@fontsource/ibm-plex-sans/700.css'
```
