# Stage 3 URL Extraction — for trace-URL SSIM replay

## Scope

- Cases scanned: **7488**
- Cases with ≥1 URL: **742**
- Total step-URL pairs: **1196**
- **Unique URLs**: **352**
- Internal WebArena URLs: **336** (95.5%)
- Replayable WebArena URLs: **336** (95.5%)

## URL-frequency filter (replayable URLs only)

| min visits | URLs |
|---:|---:|
| ≥1 | 336 |
| ≥2 | 123 |
| ≥3 | 87 |
| ≥5 | 52 |
| ≥10 | 25 |

## URLs per app (replayable)

| app | unique URLs | total visits |
|---|---:|---:|
| shopping_admin | 160 | 427 |
| gitlab | 138 | 666 |
| shopping | 31 | 89 |
| reddit | 7 | 14 |

## Replay cost estimate

Each capture = Playwright new context + cookie inject + navigate + wait-for-settle (1.5s) + optional operator inject + screenshot. Measured in Phase 7 at ~4-6 s/capture on burner EC2 with WebArena on a local IP.

Stage 3 has 26 operators. Full matrix = `N_urls × (1 base + 26 ops) × reps`. Baseline-noise estimate requires `reps ≥ 2` for at least the base variant (one real base, one "base2" in its own context).

| scenario | URLs | variants | reps | captures | ~h at 5s/capture |
|---|---:|---:|---:|---:|---:|
| all replayable: full 27 variants ×1 rep  | 336 | 27 | 1 | 9,072 | 12.6 |
| all replayable: top-6 ops ×2 reps       | 336 | 7 | 2 | 4,704 | 6.5 |
| visits ≥ 2: full 27 variants ×1 rep  | 123 | 27 | 1 | 3,321 | 4.6 |
| visits ≥ 2: top-6 ops ×2 reps       | 123 | 7 | 2 | 1,722 | 2.4 |
| visits ≥ 5: full 27 variants ×1 rep  | 52 | 27 | 1 | 1,404 | 1.9 |
| visits ≥ 5: top-6 ops ×2 reps       | 52 | 7 | 2 | 728 | 1.0 |

**Recommended minimal setup**: visits≥2 URLs × (base + L1 L5 L9 L11 L12 ML1) × 2 reps. This targets the operators where the visual-confound question actually matters (bottom-5 most destructive + ML1). Budget: ~1-2h wall, trivial S3 output.

**Paper-maximal setup**: all 27 variants × visits≥1 URLs × 1 rep. Produces per-operator SSIM distribution for every AMT operator. Budget: ~10-15h wall; fine to run unattended on burner B.

## Top 20 most-visited URLs

- `http://10.0.1.50:7780/admin/admin/dashboard/` — 48 visits
- `https://github.com/facebook/react` — 46 visits  ⚠ external
- `http://10.0.1.50:7780/admin/admin/customer/index/` — 38 visits
- `http://10.0.1.50:8023/thoughtbot/administrate` — 35 visits
- `http://10.0.1.50:7780/admin/catalog/product/` — 34 visits
- `http://10.0.1.50:8023/prime/design` — 34 visits
- `http://10.0.1.50:7780/admin/customer/index/` — 32 visits
- `http://10.0.1.50:7770/sales/order/history/` — 31 visits
- `https://github.com/thoughtbot/administrate` — 31 visits  ⚠ external
- `https://gitlab.com/facebook/react` — 21 visits  ⚠ external
- `http://10.0.1.50:8023/CellularPrivacy/Android-IMSI-Catcher-Detector/-/graphs/main` — 20 visits
- `http://10.0.1.50:8023/primer/design` — 19 visits
- `http://10.0.1.50:8023/explore` — 16 visits
- `http://10.0.1.50:8023/thoughtbot%20inc/administrate` — 15 visits
- `http://10.0.1.50:7780/admin/sales/invoice/` — 14 visits
- `http://10.0.1.50:8023/CellularPrivacy/Android-IMSI-Catcher-Detector/-/commits/main` — 14 visits
- `http://10.0.1.50:8023/amwhalen` — 14 visits
- `http://10.0.1.50:7780/admin/admin/reports/` — 13 visits
- `http://10.0.1.50:8023/primer/design/-/graphs/main` — 13 visits
- `http://10.0.1.50:8023/byteblaze/solarized-prism-theme/-/project_members` — 13 visits
