# Oks Cars demo: notes

## Logo
The business's real logo (`/workspace/refs/okscars/logo-original.jpg`, their Facebook profile image), used as is with a circular crop. It's not redrawn and not badged as illustrative. Exports in `assets/`: `logo-96/192/512` (.png and .webp, circular), `icon-192/512.png` (square, used by the manifest), `apple-touch-icon.png` (180), `favicon.ico` (16/32/48), `favicon-32.png`, `site.webmanifest`, and `og-source.jpg` (the logo plus the tagline, used for the share image). The made-up wordmark (`logo.svg`/`logo.png`, `work/logo.py`) was removed.

## Brand palette (sampled with PIL k-means, Oct 9 2026)
| Token | Hex | Source | Used for |
|---|---|---|---|
| --ok-yellow (brand gold) | #DBA923 | cover lettering "OKS CARS" (01_header.png) | headings accent, stats, links, eyebrow text, chips/active, promo strip bg, focus ring, gold buttons, road lines, OG text |
| --ok-gold | #D09F51 | logo "OKS Cars" lettering, mid gold | eyebrow, calculator border, accents |
| --ok-gold-lt | #E9CC8E | logo lettering highlight | gradient tops, button hover, headlight beam, SVG headlights |
| --ok-gold-dk | #9C6E2F | logo lettering shadow | gradient ends (photo frame, SVG gold) |
| bronze border | #8C663F | logo ring/edge | input, chip and outline borders (3:1+ UI contrast) |
| --ok-red | #A60E0F | logo red car body | primary buttons, demo banner, CTA band, icon tiles, hero/404 SVG car. Fill only: 2.6:1 as text on black |
| --ok-red-hi / coral | #E05C54 | logo red car highlight | red text-safe tint (5.7:1): APPROVED stamp, list bullets, eyebrow rule |
| --ok-red-dk | #8A0B0C | darker tint of #A60E0F | primary button hover |
| --ok-black | #050404 | cover background | page background, theme-color, manifest, OG bg |
| --ok-ink / --ok-surface | #1A1313 / #1C1213 | cover and logo dark warm blacks | panels, cards |
| --ok-line | #3B322D | logo dark ring | dividers |
| --ok-brown | #3D2613 | cover warm brown | reserved accent |
| --ok-text | #F4F4F4 | logo white smoke | body text |
| --ok-muted | #CACAC9 | cover silver | secondary text |
| listing art | #1C1213, #A60E0F, #DCD9D5, #838080, #3B322D, #E05C54 | logo greys/reds | sample car fills |

Not used: the cover's purple (#372564) and blue (#4C90CD), which come from clothing and backgrounds in the photo, not the brand.

Contrast (WCAG AA): text 18.6, muted 11.2, gold on black 9.5 (8.5 on surface), red tint 5.7, white on red 7.8, black on gold 9.5.
