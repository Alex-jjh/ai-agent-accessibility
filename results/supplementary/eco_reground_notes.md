# Ecological probe (82.4%) re-grounding notes — ECO-1..6

Read-only re-analysis backing the CHI/ASSETS 2027 paper §4 ecological-probe
remediation. Source: `eco_reground.py` over frozen
`scan-a11y-audit/results/prevalence_matrix.csv` + per-site `*.json`. Outputs in
`eco_reground.csv`. **No frozen artifact was mutated.** The locked headline
(34 sites / 28 affected / 82.4%) in `results/key-numbers.json` and the
`phase4b_ecological` verifier assertions are preserved.

## ECO-1 — disclosed rule list vs. code
- Code `PATCH_AXE_RULES["P7"]` = {landmark-main-is-top-level, region,
  landmark-one-main, landmark-unique} → 28/34 = **82.4%** (headline).
- Without `landmark-unique` → 26/34 = **76.5%**.
- The rule list previously *disclosed* at main.tex:385 ({landmark-one-main,
  region, empty-heading, heading-order, td-has-header, th-has-data-cells,
  div-as-link}) reproduces only 27/34 = **79.4%** — i.e. it did NOT match the
  82.4% headline. Fixed: main.tex:385 now lists the rule families the scanner
  actually uses (landmark + table + custom div-as-link) and drops the
  empty-heading/heading-order rules (code classifies P5 heading-flatten as
  L1_decorative, not Tier-3).
- `github` and `usa-gov` are Tier-3 SOLELY via `landmark-unique`, which is
  tagged `['cat.semantics','best-practice']`, impact=moderate — not a WCAG
  A/AA failure. Disclosed as a footnote in §4.

## ECO-2 — construct scope (probe Tier-3 ⊂ operator Tier-3)
- Probe Tier-3 = P7|P9|P11 (axe-rule subset). It EXCLUDES the heading-flatten
  (L6 = P5) and Shadow-DOM (L5 = P12) operators that the operator-side Tier-3
  definition names.
- P9 adds 0 sites beyond P7; P11 adds 0 unique sites (all 4 P11 sites ⊂ P7).
  So 82.4% is numerically identical to landmark (P7) prevalence.
- Paper-consistent Tier-3 (+P5+P12) = 30/34 = **88.2%** (P5 adds notion,
  webarena-gitlab; P12 adds notion). Reported as the "full operator-side
  definition" companion in §4 and the §4 cross-validation paragraph.
- Decision: SCOPE 82.4% as a landmark-dominated subset construct (preserves the
  locked value, constraint 4); did NOT re-headline 88.2% (would require editing
  PATCH_SEVERITY + key-numbers.json + phase4b_ecological.py together).

## ECO-3 — mixed denominators
- 82.4% = 28/34 (incl. 4 WebArena). Mean affected nodes 37.4 was computed over
  30 real-world sites only. Over all 34: mean = **33.3** (sum 1133/34). Over 30
  real-only: prevalence 25/30 = **83.3%**, mean 37.4 (sum 1123/30).
- WebArena L3 nodes: admin=6, reddit=3, shopping=1, gitlab=0 (sum 10 = the
  1133→1123 gap; the 3 affected envs = the 28→25 site gap).
- Decision (Option B): keep locked 82.4%/34 as headline, disclose the 30+4
  composition, give the all-34 mean (33.3) alongside the 30-real mean (37.4),
  and note excluding WebArena changes the figure negligibly (→83.3%).

## ECO-4 — data quality / dead scans
- 5 sites have all 3 pages <100 DOM elements (custom.domStats.totalElements):
  etsy [9,9,9], medium [46,46,46], reddit [22,22,22], salesforce [7,7,7],
  weibo [13,16,27]. Of these, 4 are Tier-3-flagged (etsy, reddit, salesforce,
  weibo) via landmark-one-main/region firing on truncated/blocked DOM; medium
  is not flagged.
- Sensitivity: drop the 5 truncated sites → 24/29 = **82.8%**; force the 4
  truncated-DOM Tier-3 flags to non-affected → 24/34 = **70.6%**.
- `scan-a11y-audit/results/_summary.json` (`successfulSites:34/failedSites:0`)
  counts non-crashing site loops, NOT usable scans — FOOTNOTED in §4, not
  mutated (constraint 1). Several sites used local HTML snapshots (a few
  captured on a Windows host) rather than the live EC2/Chromium-131 pipeline;
  disclosed in §4 to remove the "uniform clean production audit" implication.

## ECO-5 — dispersion + co-occurrence
- Among the 25 affected real-world sites, sorted L3 node counts =
  [1,1,2,2,3,3,3,3,3,6,6,7,8,11,12,18,21,44,70,70,72,78,81,253,345];
  **median = 8**, mean = 44.9 (affected only) / 37.4 (over all 30 real),
  range 1–345. Five sites dominate: bilibili 345, aliexpress 253, ebay 81,
  shein 78, jd 72.
- "Typically multiple co-occurring" was unsupported: only 4/25 affected real
  sites have ≥2 distinct Tier-3 operator TYPES (aliexpress, bestbuy, shein,
  target); 21/25 are single-type and landmark-only. The probe measures node
  COUNTS, not per-page operator co-occurrence (no co-occurrence file exists).
- §5 and §4 reworded to a dispersion/node-count statement; the §6 discussion
  super-additive bridge should be softened by the discussion-owning agent
  (see "Out of scope" below).

## ECO-6 — detector-side lower bound
- P6 (tabindex) = 0/34 (no detector), P9 (div-tables) = 0/34 (axe table rules
  only fire on existing <table>s), P11 = 4/34 (11.8%) all ⊂ P7. All three push
  measured prevalence DOWN → 82.4% is a genuine lower bound (claim is
  conservatively true). Residual was a transparency gap: the dominant
  conservatism is DETECTOR blindness, not site selection. §4 footnote now
  states P11 true prevalence likely 40–60% (event delegation invisible to
  static DOM analysis) and that observed Tier-3 is carried almost entirely by
  P7.

## Out of scope for this run (flag for owning agents — cross-file consistency)
These sites use the preserved 82.4% headline (still correct) or the 37.4 mean,
and are NOT in this agent's exclusive file set:
- `sections/06-discussion.tex:30` — "mean of 37.4 ... suggesting that
  real-world websites typically exhibit multiple co-occurring structural
  violations." The inferential bridge should be softened (median affected site
  = 8 Tier-3 nodes; 21/25 affected sites are single-type/landmark-only; probe
  counts nodes, not per-page co-occurrence). Keep the existing legitimate hedge
  ("a prediction that future large-scale ecological studies could test").
- `sections/06-discussion.tex:36, :73` and `sections/08-conclusion.tex:7` —
  "82.4% ... across 34 (real-world) websites": headline preserved, so the
  number is fine; optionally append "high-traffic" / "landmark-dominated"
  qualifier for consistency with the abstract/intro.
- `sections/07-future-work.tex:9` — "34-site audit": wording unchanged
  (denominator preserved at 34).
