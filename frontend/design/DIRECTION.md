# Design direction

Reading this as: a consumer landing page and working planner for people about to take a road trip, with an adventurous nature language, leaning toward editorial photography, a pine-and-amber palette, and motivated scroll motion on marketing pages only.

No product UI is restyled in this phase. These notes and the reference images are the source for later phases.

## Dials

Landing and projects pages, from the design-taste skill:

- DESIGN_VARIANCE: 7
- MOTION_INTENSITY: 6
- VISUAL_DENSITY: 3

Planner, when it is restyled later: keep the current density and behavior. Motion stays at hover, press, and the existing progress panel. Honor `prefers-reduced-motion`.

Image-direction dials for the reference comps:

- ART_DIRECTION: 8
- IMPLEMENTATION_CLARITY: 9
- IMAGE_USAGE_PRIORITY: 9
- SPACING_GENEROSITY: 8
- LAYOUT_VARIATION: 8

## Locked visual combination

- Theme: pristine light. Warm sand paper, not a dark glass site.
- Type: editorial serif for headlines (Fraunces), humanist sans for UI and body (Outfit). No Inter.
- Hero scale: giant statement.
- Hero architecture: massive image-first hero, text in the lower left. Not a text-left / image-right split.
- Section system: poster-like stacked storytelling.
- Narrative spine: journey. Waypoints, not feature cards.
- Second-read moment: one oversized route numeral, only in the “how a plan is made” section.
- Signature components: off-grid editorial layout, vertical rhythm lines, layered image crops, one small product-form crop in the guide.
- Motion the comps should imply: staggered float-up on the waypoint list, and a slight drift in the big photographs. Do not imply pinned scroll theaters or GSAP-style chaos.

## Tokens

Apply these in a later phase. Do not change the live planner theme in this phase.

| Token | Value | Role |
| --- | --- | --- |
| `--color-sand` | `#f3efe4` | Page canvas |
| `--color-sand-deep` | `#e7e0d2` | Quieter bands, guide surface |
| `--color-surface` | `#faf7f1` | Cards and form fields |
| `--color-pine` | `#1c3a2e` | Ink, headlines, button text on amber |
| `--color-muted` | `#5c6b62` | Secondary copy |
| `--color-line` | `rgb(28 58 46 / 0.12)` | Hairlines |
| `--color-amber` | `#e08a2a` | The only strong accent. Primary buttons. |
| `--color-amber-deep` | `#c4741c` | Amber hover |
| `--color-river` | `#3d7a78` | Tiny status marks only, such as “verified” |

`--color-ink` should become pine. `--color-primary` should become amber. Existing pale status colors can stay for validation errors and warnings.

Photography grade: warm late light, pine shadow, real roads and land. No purple, no neon, no mesh gradients, no people posing beside an SUV.

Radius: images about 16px, buttons fully round. Nav is a floating pill, detached from the top edge.

## Landing sections

Each reference is one horizontal frame. Copy in the images is the intended on-page copy.

1. Hero. Bottom-left text over a full-bleed two-lane road through tall forest, morning side light. Headline: “The long way, on purpose.” Support: “AI itineraries with driving times checked on real roads.” Amber pill: “Plan a trip.” Floating nav: Roadtrip Planner, Guide, Projects.
2. How a plan is made. Paper field. One vertical trail, not three equal cards. Oversized “01”, then “02” and “03”. Steps: Tell the trip. Build the days. Check the road. Underlined link: “See a sample route.”
3. What gets checked. Left two-thirds: graded photo of a mountain road. Right third: “Checked before you leave.” Lines: driving hours from real routes, weather on the days you travel, stops that sit on the way. Small river-teal “Verified” mark.
4. Short guide. Calmer sand field. Headline: “A short guide.” Lines: name the start, the end, and the days; wait while the route is checked; read the map, then the warnings. A small crop of the real trip form sits low and to the right.
5. Route moment. Almost all photograph: high-desert highway in late light, different from the forest hero. One line, low and centered: “Pine, asphalt, late light.”
6. Close. Mini, stacked, lots of sand. Headline: “Plan the next road.” Small amber pill: “Start planning.” Quiet line: “A few fields. A real route.”

## Projects header

Separate from the landing sequence. Same nav, type, and palette. Dusk river canyon, not the forest road and not the desert highway. Headline: “Other work.” Support: “Projects beyond the road.”

## Implementation notes from the comps

- Build the floating nav like the hero: one sand pill with the wordmark, Guide, Projects, and the amber Plan button inside it. The projects header splits Plan outside the pill; ignore that.
- Guide headline in the comp has a stray comma and an all-caps eyebrow. Use “A short guide” and sentence-case “Before you start”.
- “Tell the trip” sits inside the oversized 01. Keep that overlap. Do not turn the three steps into equal cards.

## Reference files

- `frontend/design/references/01-hero.jpg`
- `frontend/design/references/02-how-it-works.jpg`
- `frontend/design/references/03-what-gets-checked.jpg`
- `frontend/design/references/04-guide.jpg`
- `frontend/design/references/05-route-moment.jpg`
- `frontend/design/references/06-closing.jpg`
- `frontend/design/references/07-projects-header.jpg`
