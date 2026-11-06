# dotBANG — consulting front door

Static site for dotBANG: AI systems built on a company's own data. This repo is the public front door (services, work, contact) and the free notes that earn the audience. Merch and starter kits are downstream pages here, never the thesis.

**Design system:** DIR-06 BLACKOUT, refined 2026-11-05 — the type scale, spacing rhythm, hairline restraint and the three-colour palette (`#000000` field, `#FFFFFF` ink, `#6CACE4` signal) come from the brand pack at `~/.hermes/shared/dotbang-brand-2026-11-05/`. The pack's `base.css` and `dir-06-refined.css` are vendored here as `assets/base.css` and `assets/dir06.css`; `assets/site.css` adds only page-level blocks on top and introduces no new colour, radius, gradient or shadow. Fonts are the pack's Inter and JetBrains Mono subsets (OFL-1.1), copied into `assets/fonts/`.

**Brand casing:** the name is written `dotBANG` — dot lowercase, BANG uppercase, `.!` in code and as the mark. `scripts/smoke_test.py` fails on `DOTBANG` or `DotBang` anywhere in the HTML.

## Pages

| Page | Path | What it is |
|---|---|---|
| Home | `index.html` | Consulting front door: what dotBANG builds, the work, how an engagement runs, contact |
| Services | `pages/services.html` | The three engagement shapes, what is deliberately out of scope, hosting options, payment terms |
| Work | `pages/work.html` | Case 001, the Territory Brief: the ask, what was built, how it was verified, what is not proven |
| Learn | `pages/learn.html` | Free notes — real public repos only |
| Merch | `pages/merch.html` | Designs in progress; explicitly no store yet |
| Giveaways | `pages/giveaways.html` | Standing rules; no invented prize |
| Affiliates | `pages/affiliates.html` | Disclosed links; list pending, nothing invented |

## Stack

Plain static HTML/CSS. No framework, no npm dependencies, no JavaScript on any page.

The CSS is **inlined at commit time**, not at request time: `scripts/inline_css.py` assembles the five
stylesheets in `assets/` into a `<style>` block in each page and emits the two font preloads. That removes
the only render-blocking resource the site had (five stylesheet round trips, ~1.2s estimated on a throttled
phone). The sources in `assets/` are the editable truth; `scripts/inline_css.py --check` fails CI if a page's
inlined block is stale, so the two cannot drift.

Why no framework: it deploys identically on GitHub Pages and on any static host after a domain lands,
cannot break on a dependency update, and any person can edit it.

**Performance budget** (declared, then measured): performance ≥95, LCP ≤1.2s, TBT ≤50ms, CLS ≤0.02,
transfer ≤500 KiB on Lighthouse's throttled mobile profile, nothing render-blocking. Current build:
**100 / 1.20s / 0ms / 0 / 72 KiB**, desktop 100 with LCP 0.3s. Receipts and method: `docs/WEBSITE-2026-11-05.md`.

**Palette ratio** (Tyler's Nov 5 rule): field 70–80%, ink 10–15%, accent `#6CACE4` 4–14%, one pink element
≤1%. Enforced on rendered pixels with the brand pack's `audit_palette.py`; every page measures inside the
bands at 1440 and 390. The closing accent plate and ink plate footer are what carry the ratio —
`assets/ratio.css` holds the per-page, measured values.

## Deploy

`.github/workflows/pages.yml` — GitHub Actions, `actions/configure-pages` + `actions/upload-pages-artifact` + `actions/deploy-pages`, on push to `main`. No secrets. Manual fallback: Settings → Pages → Deploy from branch → `main` / (root).

**No canonical URL, no sitemap domain and no analytics until Tyler picks a domain.** Candidates checked 2026-11-03 via RDAP: dotbang.com is taken and parked for sale (HugeDomains since 2014, do not plan around it); dotbang.ai, dotbang.labs and dotbang.io were unregistered on that date. `.io` was a TLD in the original pitch, not a pun. The `.!` mark is a logo, not a TLD.

## Tests

```bash
python3 scripts/inline_css.py --check # fails if a page's inlined CSS block is stale
python3 scripts/privacy-audit.py      # no emails, IPs or internal hostnames in any public file
PORT=8765 python3 scripts/smoke_test.py  # serves the repo, fetches every page and asset, follows every
                                         # same-origin link, asserts page markers and brand casing
```

All three run in `.github/workflows/pages.yml` on every pull request and on every push to `main`, before
the Pages deploy step. The palette-ratio and Lighthouse checks need a browser, so they run from the brand
pack's tooling (`python3 build/tools/measure.py`, `build/tools/serve.py` + Lighthouse) — see
`docs/WEBSITE-2026-11-05.md` §8.

The smoke test crawls same-origin `href`/`src` links, so a renamed stylesheet or a moved page fails the run instead of shipping a broken link.

## Privacy rule

No personal data, real IPs, hostnames, emails or internal URLs in any public file. There is deliberately **no contact form and no displayed email**: the contact path is a DM link and the public GitHub organisation. Enforced in `scripts/privacy-audit.py`.

## Local preview

```bash
python3 -m http.server 8000
# http://localhost:8000/
```

## Open decisions for Tyler

1. **Domain** — nothing registered until he picks; the site carries no canonical URL until then.
2. **Contact path** — Instagram DM (`@dot___bang`) and GitHub today. A real form or booking link is a later decision, not a launch blocker.
3. **Entity name on the site** — the footer says "Utah, United States". It flips to "dotBANG LLC" the day the certificate exists.
4. **Hero treatment** — the hero does not use the brand pack's "mark as final punctuation" idea yet (that is Tyler's open taste call). The mark sits in the header; swapping in the punctuation variant is one block of CSS.
5. **Affiliate/resource URL list**, giveaway prize + mechanic, merch designs and prices — all explicit TODOs, never invented.
