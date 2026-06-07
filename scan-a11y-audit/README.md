# scan-a11y-audit — Tier-3 Ecological Prevalence Probe

This is a **self-contained subproject** (not part of the repo's `make verify-all`
suite). It measures how often real websites already exhibit the accessibility
violations that the AMT Low-variant operators inject, providing the *ecological
validity* evidence for the paper's Tier-3 analysis (`phase4b_ecological`).

The question it answers: *are the Low-variant manipulations (P1–P12) artificial,
or do they mirror accessibility defects that already exist in the wild?*

## What it does

1. `scan.ts` drives Playwright + Chromium over a corpus of sites, running
   axe-core (WCAG 2.0/2.1 A/AA + best-practice) plus a set of custom DOM checks
   (`custom-checks.ts`) for patterns axe-core does not cover (div-as-link,
   non-semantic headings/tables, Shadow DOM). Per-site JSON lands in `results/`.
2. `analysis.py` loads `results/*.json`, maps axe rule IDs + custom signals onto
   the 12 Low-variant patches, and prints the prevalence tables (Tables 1–5),
   a category summary, and `results/prevalence_matrix.csv`.

`analysis.py` is the **authoritative analysis source** — it holds the canonical
patch → axe-core rule mapping (`PATCH_AXE_RULES`). `config.ts` deliberately does
**not** carry a second copy of that mapping; a duplicate that had drifted
out of sync was removed so there is exactly one source of truth.

## The corpus

`config.ts` defines **34 sites** scanned at 3 pages each (home / search / detail):

- **30 real-world public sites** across 5 categories — ecommerce (8), China
  platforms (6), SaaS/tools (6), media (5), government/education (5).
- **4 WebArena Docker environments** (`requiresInternalNetwork: true`) reachable
  only from the EC2 private network (`10.0.1.x`): gitlab, shopping, admin, reddit.

Headline figure: the paper §4 Tier-3 prevalence (82.4%, L3 structural) is
computed over **all 34 scanned sites**. An alternate 83.3% figure uses a
30-site real-world-only denominator — cite the 82.4%/34 figure to avoid
mixing the two denominators.

## What's tracked vs. delivered

Only the **source** of this subproject is in git (`scan.ts`, `analysis.py`,
`config.ts`, `custom-checks.ts`, `package*.json`, this README). The two data
artifacts are git-ignored and delivered by the HuggingFace tarball, placed by
`../setup-workspace.sh` (the same mechanism as `data/`):

- `results/*.json` — the 34 per-site axe-core scan outputs (the 82.4% source;
  read by `phase4b_ecological`).
- `html-snapshots/` — ~21 MB of raw site captures (`<site>/<label>.html` +
  `metadata.json` provenance index) for the 7 sites that cannot be scanned live
  (auth walls / anti-bot / geo gating). These are **audit evidence only**;
  `make verify-all` does not read them.

A fresh checkout therefore has no `results/` or `html-snapshots/` until
`setup-workspace.sh` runs; re-scanning live (or `--local ./html-snapshots` once
the snapshots are present) regenerates `results/`.

## Live vs. `--local` scanning

There are two scan paths:

- **Live scan** — `scan.ts` fetches public sites over the network. Pages flagged
  `requiresAuth: true` (most China-platform search/detail pages) hit login walls
  and are recorded as skipped, not scanned.
- **`--local <dir>` scan** — points at a directory of manually saved HTML
  snapshots (`<site>/<label>.html`, optional `metadata.json`). This path exists
  precisely because several sites cannot be scanned live: auth walls, anti-bot
  blocking, or geo/region gating. Snapshot-derived results carry
  `source: "local-snapshot"` on each page.

```
npx tsx scan.ts                          # live scan, public sites only
npx tsx scan.ts --site amazon,jd         # live scan, specific sites
npx tsx scan.ts --include-internal       # add WebArena sites (EC2 network only)
npx tsx scan.ts --local ./html-snapshots # scan saved HTML snapshots
python analysis.py                       # regenerate tables from results/
```

## Prerequisites

```
cd scan-a11y-audit
npm install                       # tsx + playwright + @axe-core/playwright
npx playwright install chromium   # Chromium binary (not pulled by npm install)
```

`analysis.py` needs only the Python standard library (no third-party deps).

## ⚠️ The `results/` corpus is FROZEN — do NOT re-scan

**`results/` is a locked snapshot of the data behind the published Tier-3
numbers. Do not regenerate it.**

- 7 of the per-site JSONs (`bestbuy`, `ebay`, `taobao`, `weibo`, `walmart`,
  `zhihu`, `xiaohongshu`) are **derived from local HTML snapshots**, not live
  scans, because those sites are auth-walled or anti-bot-blocked. A live
  `npm run scan` cannot reproduce them — it would overwrite them with
  near-empty error records.
- A naive `npm run scan` writes per-site JSON to `results/` as it goes
  (`writeFileSync` is crash-safe / overwrite-on-success) and would **clobber the
  frozen corpus**, including those 7 snapshot-derived files, and silently
  change the paper's published prevalence figures.
- Live sites also drift over time (layout, anti-bot, A/B tests), so a re-scan
  would not reproduce the original numbers even for the non-snapshot sites.

If you genuinely need to re-run, do it against a **copy** of the directory or a
throwaway results path — never against the committed `results/`. The `.json`
files in `results/` and `results/prevalence_matrix.csv` are treated as
read-only artifacts.
