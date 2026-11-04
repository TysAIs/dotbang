# dotBANG mark — assets and construction

The mark is `. !` — a period and a bang that share one baseline. It is a logo,
not a TLD, and it is never typeset as characters when it can be an asset.

Geometry (module `m`, integers only): box 3m × 5m, period 1m × 1m at column 1
row 5, bang stem 1m × 3m at column 3 rows 1-3, bang dot 1m × 1m at column 3 row
5. Clearspace 2 modules on all sides. Minimum size 12 × 20 px (m = 4); never
scale below it, never scale non-integrally, never rotate, outline, bevel, glow,
shadow or gradient it.

## Vector

| File | State | Use |
|---|---|---|
| `mark.svg` | white on transparent | default, on the black field |
| `mark-signal.svg` | accent dot `#6CACE4`, white bang | hero / brand moment, once per page |
| `mark-inverse.svg` | black on transparent | print or inverted (white) sections only |

There are exactly three legal colour states. `#6CACE4` on white is the banned
fourth state (2.43:1, fails AA). Alpha steps of `#FFFFFF` and `#6CACE4` are
allowed; no fourth hue, ever.

## Raster

`png/mark-{default,signal,inverse}-{1x,2x,4x}.png` — the transparent mark at
12×20, 24×40 and 48×80.

`../social/dotbang-{avatar-400x400,banner-1500x500,cover-1280x720}-{default,signal,inverse}.png`
— the platform sizes, each in the three legal states. The banner and cover also
carry the wordmark and the site tagline; the avatar is the mark alone.

`../favicon.svg`, `../favicon-16.png`, `../favicon-32.png` — the mark on the
module grid, black field, white mark.

## Rebuild

```sh
python3 scripts/build_brand_assets.py --ttf-dir /path/to/jetbrains-mono-ttf
```

Vector output needs no dependencies. The PNG and social exports need Pillow, and
the wordmark text needs a JetBrains Mono TTF (the site's woff2 is not readable
by Pillow); without it the social art is written mark-only and the script says
so. The wordmark face is provisional — the design brief leaves "Departure Mono
versus custom letterforms" open.

Source of truth for every number here: `DOTBANG-DESIGN-LANGUAGE-2026-11-04.md`
§2 (palette) and §4 (mark).
