# dotBANG

A free hub for local AI under the dotbang brand.

**Concept:** Earn an audience with free, verifiable knowledge about running AI locally, and monetize that audience. Merch and USB starter kits are downstream of the audience — never the thesis. **Not a course funnel.**

## Status

- Launched scaffold: Nov 2026 weekend target (kanban t_e951c113)
- Domain: **TBD — do not register or publish a canonical domain until Tyler picks.** Candidates checked Nov 3 via RDAP: dotbang.com taken / parked for sale (HugeDomains since 2014, do not plan around it); dotbang.ai, dotbang.labs, dotbang.io returned not-registered. The `.io` in the original pitch was a TLD, not a pun. The `.!` mark is the logo, not a TLD.
- Until a domain is chosen, the site deploys to GitHub Pages and carries **no canonical URL, no sitemap domain, and no analytics**.

## Business framing (fixed 2026-11-05)

Earlier drafts said "the merch is the business". That was wrong and it is corrected everywhere in this repo.

- **The business is the audience.** @dot___bang on Instagram and TikTok, grown niche-first: local AI, measured claims, no funnel.
- **The knowledge stays free.** It is what earns the audience; nothing on the learn page may sit behind a purchase.
- **Merch and USB kits are downstream.** They are what an audience can eventually buy. They never lead, and no page claims they are the point.

## Pages

| Page | Path | Status |
|---|---|---|
| Home / hub | `index.html` | Scaffold live, copy is Tyler's pitch, no invented claims |
| Affiliate links | `pages/affiliates.html` | **Blocked:** awaiting socials' compiled affiliate URL list. No placeholder URLs are published. |
| Learning resources | `pages/learn.html` | Seeded only with real, public TysAIs repos. No link is invented. |
| Giveaways | `pages/giveaways.html` | Scaffold + rules template. No prize, date, or entry mechanic is invented. |
| Merch | `pages/merch.html` | Design concepts only. No store, price, or checkout is invented. |

## Stack choice

Plain static HTML/CSS/JS. No build step, no framework, no npm dependencies.

Why: the launch blocker is domain + affiliate list, not tooling. A zero-build site deploys identically on GitHub Pages today and on any static host after the domain lands, cannot break on a dependency update, and is editable by anyone. If Tyler later wants a CMS or store, that is a deliberate second step, not a launch prerequisite.

## Deploy pipeline

`.github/workflows/pages.yml` — GitHub Actions, `actions/configure-pages` + `actions/upload-pages-artifact` + `actions/deploy-pages`, on push to `main`. No secrets, no domain config in the workflow.

Manual fallback: Settings → Pages → Deploy from branch → `main` / (root).

## Privacy rule

No personal data, real IPs, hostnames, emails, or internal URLs on the public site. Enforced by `scripts/privacy-audit.py` in CI and locally:

```bash
python3 scripts/privacy-audit.py
```

## Local preview

```bash
python3 -m http.server 8000
# http://localhost:8000/
```

## Open decisions for Tyler

1. Domain: .com (resale), .ai, .labs, or .io — nothing registered until Tyler picks.
2. Affiliate/resource URL list (socials compiling).
3. Giveaway prize + mechanic, merch designs/prices, and the USB starter-kit contents — all currently explicit TODOs, not invented copy.
