# SVG Segment Breakdown — mjavfx.svg

Source: `mjavfx.svg` (863×2351, raw Figma export — all text is outlined to `<path>`, no `<text>` elements, no semantic group IDs). Every section file below is a **full copy of the original SVG's body + defs**, windowed with a different `viewBox` y-offset. This guarantees nothing is broken (every filter, gradient, mask, and the embedded avatar PNG resolves correctly in every file) at the cost of file size — each segment is ~250KB on disk before gzip. This is a deliberate tradeoff: safe-but-heavy now, trim-able later.

If you need to slim these down, the embedded defs block (`<defs>...</defs>`, ~58KB) is identical across all five files — strip out anything not referenced within that segment's viewBox window (e.g. `home.svg` doesn't need `filter2_d_0_1`, which only feeds the Contact CTA button).

## Section map (y-coordinates in original 2351px-tall canvas)

| File | y-range | Height | Contents |
|---|---|---|---|
| `nav.svg` | 0–55 | 55 | Nav bar background pill + "Home / Creators / Work / Contact" labels (each outlined-path-with-drop-shadow, see Nav detail below) |
| `home.svg` | 55–614 | 559 | 4-dot accent row, "Hero Text Goes Here" heading, "Work With Me" CTA pill, two video placeholder boxes (rounded black rects) |
| `avatars.svg` | 614–747 | 133 | Avatar carousel: 3 circles (each a grey circle + small white "play" dot overlay) + "Avatar N / 200k Subscribers" label pairs |
| `work-showcase.svg` | 747–1760 | 1013 | 3 zigzag callouts, alternating sides, each = video placeholder box + "Avatar N / 200k Subscribers" heading, connected by one continuous dashed curve path |
| `contact.svg` | 1760–2351 | 591 | "JOIN ME ON / a call together" heading, "Work With Me" CTA pill (2nd instance), tail of dashed line, "mjav — The Editor" logo mark, copyright text |

**Note on naming clash:** both `home.svg` and `contact.svg` contain a "Work With Me" CTA button — they are two separate path instances in the source, not a shared symbol. Treat them as independent elements when wiring up animations/links (both need the same hover + click behavior per the interactive notes, so this is expected, just don't assume one `<button>` covers both).

## Path-index reference (for fine-grained extraction)

Anchor points found via each path's first `M` (moveto) command's Y value, in original canvas coordinates. Listed low→high. Multiple path indices at the same Y are usually the fill + outline-shadow pair for the same glyph stroke (Figma's drop-shadow export duplicates each shape once visible + once in a `<mask>`).

```
y=23.7    paths #117, #123        — Nav: tails of "k" in "Work" / "C" in "Creators" ascenders
y=34.0    paths #112,113,114,118,119,120  — Nav: "Home" lettering
y=34.2    paths #115,116,121,122  — Nav: "Creators" lettering
y=194.0   path #111                — Decorative element near top (small accent, part of Home hero area — verify in-browser, low confidence)
y=304.7–321  paths #100-110,136-146 — Home: "Hero Text" line 1 lettering
y=356.0   paths #97, #99           — Home: video placeholder box corner notches (the diagonal-cut corners visible in the render)
y=533.0   paths #23, #96, #98, #135 — Home: video placeholder box bodies (rounded rects with cut corners)
y=614–697 paths #24,25,26-95,72,73,48,49 (large cluster) — Avatars: the 3 circles + "Avatar N / 200k Subscribers" labels (dense path cluster, this is the most fragmented region — recommend treating as one inseparable block)
y=747.7   path #0                  — Work Showcase: start of the dashed connector curve (this is the section's true top edge)
y=908     path #20                 — Work Showcase: "Avatar 1" heading
y=942     path #21                 — Work Showcase: "200k Subscribers" (under Avatar 1)
y=1045    path #22                 — Work Showcase: video box #1 body (left-side, paired with Avatar 1 text on right)
y=1242    path #17                 — Work Showcase: "Avatar 2" heading
y=1276    path #18                 — Work Showcase: "200k Subscribers" (under Avatar 2)
y=1377    path #19                 — Work Showcase: video box #2 body (right-side)
y=1602    path #14                 — Work Showcase: "Avatar 3" heading
y=1636    path #15                 — Work Showcase: "200k Subscribers" (under Avatar 3)
y=1757    path #16                 — Work Showcase: video box #3 body (left-side) — NOTE this is right at our 1760 cut line, verify it doesn't get clipped, nudge boundary down a few px if so
y=1875.6  path #13                 — likely tail-end of dashed line as it enters Contact (in contact.svg, not work-showcase.svg, since file boundary is 1760)
y=1974.7  paths #6,11,128,133      — Contact: "a call together" line lettering
y=1975.0  paths #2, #124           — Contact: CTA button pill body (the rounded-rect path, NOT the text on it)
y=1985–1991  paths #3-12,124-134   — Contact: "a call together" + button label lettering cluster
y=2194.4  path #1                  — Footer: "mjav" logo wordmark (script-style signature mark)
```

## Other embedded assets

- **`image0_0_1`**: one base64 PNG (1002×1008), used as a `<pattern>` fill. This is the avatar headshot placeholder. It's referenced once directly (`rect x="393" y="2100"` — actually the footer logo area, double check this in-browser, the coordinate looks more like a footer-zone reference than a carousel-avatar reference) — **the 3 carousel avatar circles appear to NOT use this image as their fill** (they render as flat grey `#D9D9D9`-ish circles in the static export), so this embedded image may be an unused leftover from the Figma file, or a 4th avatar reference not visible in the current crop. Worth a sanity check before assuming it's load-bearing.
- **Two `foreignObject` + backdrop-blur `<div>` pairs**: at canvas y=1956–2010 (Contact CTA area) and y=286–340 (Home CTA area). These are Figma's way of exporting a CSS `backdrop-filter: blur(2px)` effect applied to something near each CTA button — likely a soft glow/frost behind the pill, not the nav bar. **This means the "Navigation bar should be blurry" requirement from the interactive notes is NOT something already baked into the SVG** — the nav bar's blur-on-scroll has to be built fresh in CSS (`backdrop-filter: blur()` on the sticky nav container), which the homepage layout below already does.

## Confidence notes

- Nav, Home, Avatars sections: high confidence, verified by direct pixel-row inspection against rendered crops.
- Work Showcase 3-callout zigzag: high confidence on structure (verified visually), medium confidence on exact y=1757 vs y=1760 boundary for the 3rd video box — render both `work-showcase.svg` and `contact.svg` side by side in-browser and nudge by a few pixels if you see a seam or overlap.
- The dense path cluster in Avatars (y=614-697, ~70 paths) was not individually decomposed past glyph-cluster level — treat that whole region as one visual unit unless you specifically need to pull one avatar circle out independently (e.g., to make them clickable separately), in which case re-render `avatars.svg` at 2-3x scale and trace which paths sit under which circle by x-position (circles are roughly evenly spaced across x=220–660 based on the 3-circle row).
