# Task Expansion Plan — April 12, 2026

## Goal

Expand from 6 tasks (Pilot 4) to 13 tasks across 4 WebArena apps for CHI 2027 submission.
Adds GitLab as 4th app (critical for generalizability argument).

## Current Tasks (Pilot 4, N=360)

| Task ID | App | Template | Eval | Nav Depth | Intent |
|---------|-----|----------|------|-----------|--------|
| 4 | shopping_admin | 279 | string_match | Medium (3-4) | Top-3 best-selling products Jan 2023 |
| 23 | shopping | 222 | string_match | Shallow (1-2) | Reviewers mentioning fingerprint resistant |
| 24 | shopping | 222 | string_match | Shallow (1-2) | Reviewers mentioning unfair price |
| 26 | shopping | 222 | string_match | Shallow (1-2) | Reviewers mentioning customer service |
| 29 | reddit | 33 | string_match | Medium (3-4) | Count downvoted comments for user |
| 67 | reddit | 17 | string_match | Shallow (2) | Book names from top 10 books posts |

Note: Tasks 23/24/26 share template 222 (same page structure, different search terms).
Effective template count = 4 (279, 222, 33, 17). Apps covered = 3.

## New Candidate Tasks (7 tasks, 7 new templates)

### Phase 1 — GitLab (highest risk, verify first)

| Task ID | Template | Eval | Nav Depth | Intent | Selection Rationale |
|---------|----------|------|-----------|--------|---------------------|
| **132** | 322 | string_match | Medium (3) | How many commits did kilian make to a11yproject on 3/5/2023? | Contributors data page. Table/chart DOM. Answer="1". |
| **293** | 329 | string_match | Medium (2-3) | Show me the command to clone Super_Awesome_Robot with SSH. | Repo detail page. Clone panel (button expand + hidden panel). |
| **308** | 323 | string_match | Deep (4-5) | Who made the most contributions to primer/design? | Search → repo → Contributors → sort. Longest nav chain. |

GitLab risk: Vue.js virtual DOM may conflict with MutationObserver guard.
Must verify variant injection works before committing to full runs.

### Phase 2 — Admin + Shopping (verified environments)

| Task ID | Template | Eval | Nav Depth | Intent | Selection Rationale |
|---------|----------|------|-----------|--------|---------------------|
| **41** | 285 | string_match | Medium (3) | List the top 1 search terms in my store | Marketing → Search Terms (different admin section from task 4). |
| **94** | 274 | string_match | Deep (4) | Grand total of invoice 000000001 | Sales → Invoices → detail. Table semantics (th→td patch). |
| **198** | 366 | string_match | Deep (4-5) | Customer name of most recent cancelled order | Sales → Orders → filter Canceled → read. Table filtering. |
| **124** | 159 | string_match | Medium (3) | Price range of wireless earphone | Search box → results → extract prices. Label removal affects search. |

### Phase 3 — Reddit (no new tasks needed)

Reddit has only 2 string_match info-retrieval templates (33 and 17), both already covered
by tasks 29 and 67. Adding task 69 (template 17, same as 67) would violate template
independence. Reddit coverage is sufficient at 2 tasks.

## Backup Candidates (if smoke tests fail)

| Task ID | App | Template | Intent |
|---------|-----|----------|--------|
| 349 | gitlab | 298 | Who has access to my repo gimmiethat.space? (Settings → Members) |
| 188 | shopping | 214 | Total cost of latest cancelled order (Account → Orders) |

## Selection Criteria Applied

1. **One template per task** — avoids inflating N without adding diversity.
   Final: 11 unique templates across 13 tasks (23/24/26 share template 222).
2. **All 4 deployed apps** — GitLab adds Vue.js DOM (vs Magento KnockoutJS, Postmill).
3. **string_match eval only** — reliable, no OpenAI dependency.
4. **Information retrieval only** — no state mutation, repeatable runs.
   Limitation: form interaction scenarios not tested (acknowledged in paper).
5. **Navigation depth diversity** — shallow (2), medium (3-4), deep (4-5).
   Low variant's nav/landmark removal has larger effect on deep navigation.
6. **Different page types per app** — tables, search, reports, repo details, contributors.

## Navigation Depth Distribution (Final 13 Tasks)

| Depth | Tasks | Count |
|-------|-------|-------|
| Shallow (1-2 steps) | 23, 24, 26, 67 | 4 |
| Medium (3 steps) | 4, 29, 132, 293, 41, 124 | 6 |
| Deep (4-5 steps) | 308, 94, 198 | 3 |

## Projected Experiment Size

| Config | Tasks | Variants | Reps | Agents | Cases |
|--------|-------|----------|------|--------|-------|
| Existing Pilot 4 | 6 | 4 | 5 | text-only + SoM | 240 |
| Existing Pilot 4 CUA | 6 | 4 | 5 | CUA | 120 |
| New expansion (text-only) | 7 | 4 | 5 | text-only | 140 |
| New expansion (CUA, optional) | 7 | 4 | 5 | CUA | 140 |
| **Total** | **13** | — | — | — | **~640** |

Time estimate: 140 text-only cases × ~3 min = ~7 hours. With CUA: ~14 hours total.
Fits within one burner account cycle if started promptly after deployment.

## Execution Order

1. Deploy new AWS account (terraform + bootstrap)
2. Verify WebArena services (all 5 Docker containers including GitLab)
3. Phase 1: GitLab smoke (132, 293, 308 × 4 variants × 1 rep × text-only = 12 cases)
   - READ TRACES — verify variant injection on Vue.js DOM
   - If Type 2 bug found: fix first, then re-smoke
4. Phase 2: Admin + Shopping smoke (41, 94, 198, 124 × 4 variants × 1 rep = 16 cases)
5. Full runs per task (4 variants × 5 reps × text-only = 20 cases each)
6. Optional: CUA runs for new tasks (same config but observationMode=cua)

## Consistency Requirements

Before starting expansion, FREEZE:
- apply-low.js, apply-medium-low.js, apply-high.js (variant patches)
- browsergym_bridge.py, cua_bridge.py (bridge code)
- Bedrock model ID: us.anthropic.claude-sonnet-4-20250514-v1:0

If any of these change mid-expansion, mark batch boundary per steering rules.

## Limitations to Acknowledge in Paper

- Task set is information retrieval only; form interaction not tested
- Reddit limited to 2 templates (pool exhaustion, not selection bias)
- Tasks 23/24/26 share template 222 (sensitivity analysis: exclude 2, check stability)
- GitLab tasks not yet validated (pending Phase 1 smoke)
