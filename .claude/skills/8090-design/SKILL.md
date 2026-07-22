---
name: 8090-design
description: "8090 Design System: Industrial Blueprint Editorial with Tailwind Slate and shadcn/ui Nova. Apply when building any 8090-branded UI, prototype, dashboard, landing page, or web application. Triggers: '8090 design', '8090 style', '8090 prototype', 'apply 8090', 'Factory Blue', 'industrial blueprint', or when building UI for any 8090 project. Also triggers when styling components with slate palette, IBM Plex Sans, or shadcn Nova conventions. Enforces Factory Blue (#0052CC) as sole accent, slate palette neutrals, IBM Plex Sans typography, shadcn Nova component conventions, and industrial editorial illustration style."
---

# 8090 Design System

Apply the Industrial Blueprint Editorial design system to every 8090 prototype and UI.

## Quick Start

1. Read [references/design-system.md](references/design-system.md) for the full spec
2. Apply core tokens below
3. Run the preflight checklist before finalizing

## Core Tokens

```
accent:  #0052CC          (Factory Blue — ONLY accent color)
bg:      slate-50         (#f8fafc — page canvas)
card:    white            (rounded-md border-slate-200 shadow-sm p-6)
text:    slate-950 / slate-700 / slate-500  (headlines / body / captions)
font:    IBM Plex Sans    (tracking-[-0.01em] global)
mono:    Geist Mono       (code, data labels)
```

Brand variants use opacity only: `bg-brand/10`, `text-brand/60`, `border-brand/20` — never separate hex tints.

## Key Constraints

- **One accent**: Factory Blue `#0052CC` only — no other hues
- **Slate grays only**: never zinc, neutral, or stone
- **Corner radii**: max `rounded-lg` (8px) — never `rounded-xl`+
- **No gradients** on UI surfaces
- **Opacity for brand variants**: `bg-brand/10` not `#e6effa`
- **Red for errors only**: `red-500` never decorative
- **Success**: `green-600` for functional success states only
- **Warning**: `amber-500` for functional warnings only

## Component Quick-Ref (shadcn Nova)

| Element | Key classes |
|---------|------------|
| Card | `rounded-md border-slate-200 bg-white shadow-sm p-6` |
| Primary btn | `rounded bg-brand text-white h-10 px-4 font-medium` |
| Secondary btn | `rounded border-slate-200 bg-white text-slate-700 h-10 px-4` |
| Input | `rounded border-slate-200 bg-white h-10 px-3 text-sm` |
| Badge | `rounded-sm bg-slate-100 text-slate-700 text-xs font-semibold px-2.5 py-0.5` |
| Focus ring | `ring-2 ring-brand/40 ring-offset-2` |

Full component specs with hover/focus/disabled states → [references/design-system.md](references/design-system.md)

## Preflight Checklist

Verify every item before finalizing:

- [ ] **Slate palette only** — no zinc, neutral, or stone grays
- [ ] **Factory Blue (`#0052CC`)** is the ONLY accent — no other hues
- [ ] **One blue accent** per panel highlighting the core concept
- [ ] **No text inside illustrations** — headlines live outside
- [ ] **No warning symbols in illustrations** (allowed in functional UI for errors)
- [ ] **Illustrations are metaphorical**, not literal software depictions
- [ ] **Background is `slate-50`** (`#f8fafc`)
- [ ] **Cards use Nova style**: `rounded-md border-slate-200 bg-white shadow-sm`
- [ ] **Corner radii max `rounded-lg`** (8px) — no `rounded-xl`+
- [ ] **Spacing follows 8px grid** — only Tailwind tokens (2, 4, 6, 8, 12, 16)
- [ ] **Focus states** use `ring-brand/40`
- [ ] **Buttons**: `rounded` (4px), `h-10`, `font-medium`
- [ ] **Brand variants use opacity only** — `bg-brand/10`, not separate hex
- [ ] **No gradients** on UI surfaces
- [ ] **IBM Plex Sans** typography — no Inter, Roboto, or system defaults
- [ ] **Geist Mono** for data labels and code
- [ ] **Responsive**: works at `sm`, `md`, and `lg` breakpoints minimum
- [ ] **Red (`red-500`)** only for true error states — never decorative
- [ ] **Green (`green-600`)** only for success states — never decorative
- [ ] **Amber (`amber-500`)** only for warnings — never decorative
- [ ] **Contrast**: text meets WCAG AA (4.5:1 body, 3:1 large text)
- [ ] **Focus visible** on all interactive elements
- [ ] **Transitions** use `duration-150` or `duration-200` — no slow fades

## Detailed Reference

For the complete specification — typography scale, spacing system, Tailwind config, all component variants, illustration guidelines, color opacity scale, accessibility, dark mode strategy, and motion — read [references/design-system.md](references/design-system.md).
