
# Design Profiles (Examples **Source of Truth**)

This folder contains the **canonical** UI design profiles for QaAI used by the examples in this template.  
Keep these files up to date and treat them as the **single source of truth** for tokens, structure, and copy used in the UI.

> If you mirror these JSONs into your app code (e.g., `/apps/web/src/design/`), you **must** keep them in sync. Log any sync actions in `TASK.md` under “Discovered During Work”.

---

## Files

- `assistant.profile.json` — Default **Assistant** page (tabs, prompt area, attachments, discover/gallery).
- `vault.profile.json` — **Vault** projects view (filters, search, project grid & cards).
- `workflow.draft-from-template.profile.json` — Example **Workflow**: “Draft from Template” (intro modal + step-by-step run).

Each file includes:
- **Meta** (title, purpose, observed_on)
- **Core tokens** (colors, typography, radii, spacing, shadows)
- **Layout** (app shell, content constraints)
- **Components** (props, styles, structure)
- **A11y** patterns and **copy** text
- **Example structure tree** (for scaffolding)

---

## How to consume these profiles in the examples

You have two simple options for the example apps/demos:

### A) Runtime load (browser/Node)
Load the JSON and map a minimal subset of tokens to CSS variables. Example (browser):

```html
<script type="module">
  async function applyDesign(profileUrl = 'examples/design/assistant.profile.json') {
    const p = await fetch(profileUrl).then(r => r.json());

    const cs = p?.colors?.semantic ?? {};
    const rad = p?.radii ?? {};
    const ty = p?.typography?.scale ?? {};

    const setVar = (k, v) => document.documentElement.style.setProperty(k, v);

    // Colors → CSS vars
    cs.bg?.canvas && setVar('--bg-canvas', cs.bg.canvas);
    cs.bg?.card && setVar('--bg-card', cs.bg.card);
    cs.bg?.subtle && setVar('--bg-subtle', cs.bg.subtle);
    cs.border?.default && setVar('--border', cs.border.default);
    cs.text?.primary && setVar('--text', cs.text.primary);
    cs.text?.secondary && setVar('--text-2', cs.text.secondary);
    cs.text?.muted && setVar('--text-muted', cs.text.muted);
    cs.action?.primary?.bg && setVar('--btn-bg', cs.action.primary.bg);

    // Radii
    rad.md && setVar('--radius-md', `${rad.md}px`);
    rad.lg && setVar('--radius-lg', `${rad.lg}px`);
    rad.pill && setVar('--radius-pill', `${rad.pill}px`);

    // Typography
    ty.body?.size && setVar('--font-size-body', `${ty.body.size}px`);
    ty.h1?.size && setVar('--font-size-h1', `${ty.h1.size}px`);
  }

  applyDesign();
</script>
Use in markup/Tailwind:

html
Copy
Edit
<div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-lg)"></div>
<h1 style="font-size: var(--font-size-h1)">Assistant</h1>
B) Build-time import (TypeScript)
Import the JSON and run a small mapper on app boot:

ts
Copy
Edit
import profile from '../../examples/design/assistant.profile.json';

// call a helper that maps tokens to CSS variables
applyDesignVariables(profile);
Tip: Only map what you actually need (bg/border/text/radii/typography). Additional component-level values can be read directly from the JSON where you render them.

Token mapping (recommended minimal set)
JSON path	CSS Variable	Purpose
colors.semantic.bg.canvas	--bg-canvas	App background
colors.semantic.bg.card	--bg-card	Card background
colors.semantic.bg.subtle	--bg-subtle	Subtle blocks (thinking states)
colors.semantic.border.default	--border	Borders
colors.semantic.text.primary	--text	Primary text
colors.semantic.text.secondary	--text-2	Secondary text
colors.semantic.text.muted	--text-muted	Muted text/captions
colors.semantic.action.primary.bg	--btn-bg	Neutral action background
radii.md	--radius-md	Inputs/cards
radii.lg	--radius-lg	Large cards/modals
radii.pill	--radius-pill	Segmented/tab/pill controls
typography.scale.body.size	--font-size-body	Body text size
typography.scale.h1.size	--font-size-h1	Page header size

You can extend this map with shadows (shadows.sm/md) and focus ring colors as needed.

Naming & structure conventions
Profiles:

Assistant: assistant.profile.json

Vault: vault.profile.json

Workflow: workflow.<slug>.profile.json (e.g., workflow.draft-from-template.profile.json)

Keys should remain consistent across profiles (meta, colors, typography, layout, components, a11y, copy).

References like {colors.semantic.text.primary} are allowed; resolve them when rendering if needed.

