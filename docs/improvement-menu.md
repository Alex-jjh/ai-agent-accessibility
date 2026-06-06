# AMT Workspace — Improvement Menu

> Verified backlog produced 2026-06-06 by an 8-subsystem understanding sweep
> (60 candidates raised, each adversarially re-checked against the real code;
> 8 dropped as intentional/already-handled, **52 confirmed real or partial**).
> Use this as a pick-list for future sessions.
>
> **Baseline at time of audit:** `make verify-all` → **108/108 PASS** across 8
> stages; venv Python **3.11.15**; data collection COMPLETE and frozen
> (N=14,768); paper repo clean. Remaining work is paper-writing, archival,
> reproducibility polish, and code/doc quality.
>
> **Legend** — Severity: HIGH / MEDIUM / LOW. Effort: trivial / small / medium / large.
> `⚠ NEEDS-USER-APPROVAL` = touches frozen artifacts, paper source/numbers,
> `git commit`/`git tag`, or regenerates a locked CSV.

---

## ✅ Execution status (2026-06-06)

A full apply pass ran the same day (commits `40025f4`, `2ca3ae2`, `100fd08`,
`4e1d2da`, `2fd1753`). **All auto-executable items in Groups A, B, C, and E are
DONE.** Verified afterward: `make verify-all` still **108/108**, `tsc --noEmit`
clean, vitest **414/414**, pytest now **0 collection errors** (18 passed + 1
skipped, was 19 + 2 errors).

**Done:** AppleDouble note (folded into hygiene), figure PDF-`CreationDate`
reproducibility + `figures/README.md` interpreter fix, `verify-ts` target,
ecological-corpus README, bootstrap p-value sourced from CSV (stale 2.83e-11 →
2.51e-11), dead `PATCH_AXE_RULES` (was already gone), stat-doc count fixes,
`stage3_statistics` import cleanup, pytest collection fix (`conftest.py`), the
new `audit-ecological` wrapper + Makefile target + `phase4b-ecological.md`
by-stage doc, and the entire Group C doc-accuracy sweep (8 stages/108, 26
operators, 414 TS, HuggingFace data location, reworded non-existent rollback
tags). All checkboxes below predate this pass — trust this banner, not the boxes.

**Deliberately NOT done (still open):**
- **Group D (paper)** — user deferred all of it this round (documentclass/anonymization,
  L11 sign convention, latexmk config, figure dedup, bib prune). ⚠ paper source.
- **`setup-workspace.sh` `._*` purge** (A, HIGH) — the runbook hardening; still worth
  adding so a Mac-packed tarball reproduce can't fail the 9,408-PNG assert.
- **`shasum` masked-exit + macOS `hf` probe** (A, LOW) — `setup-workspace.sh` robustness.
- **Stat-primitive consolidation onto `lib/stats.py`** (B) — deferred (low value, frozen).
- **`expect_rate` `tol_frac`→`abs_tol` rename, `scan.ts` helper extract** (B, LOW) — deferred.
- Creating the rollback git **tags** — left as reworded prose, not fabricated. ⚠

---

## How to read this

Every item below was checked against the actual files — the `evidence`
file:line references are real, and proposals that the verifier found
**overstated** have been corrected in place (look for *"corrected:"* notes).
Items that survived as `partial` are genuine but minor/nuanced; they say so.

Nothing in this document has been applied except the two committed-this-round
hygiene changes (see [§7](#7-applied-this-round)).

---

## 1. Workspace map (one line each)

| Subsystem | Health | One-line |
|---|---|---|
| `analysis/` — Python stats + V&V (Module 6) | 🟢 strong | 3-layer `_constants → lib → stages → verify_all`; re-derives every paper number to `results/key-numbers.json`. Weak spots: pytest collection break on core install, a few hardcoded p-values, doc drift. |
| `src/` — TS data-collection modules 1–5 | 🟢 strong | Frozen instrument: 26 AMT operators, scanner/runner/classifier/recorder/export. `tsc --strict` clean, vitest **414/414**. Weak: doc drift, no automated path runs the suite. |
| `figures/` — paper figure generators | 🟡 fn-good, hygiene-weak | 7 matplotlib scripts redraw data figures from frozen CSVs. Weak: README uses wrong interpreter, 3 naming schemes, binary churn, copy-paste boilerplate. |
| `scripts/` — operational tooling (14 subdirs) | 🟢 disciplined | Live `audit/`+`maintenance/` (Makefile depends on them) vs vestigial collection-era runners. Weak: 8th stage missing from audit surface. |
| `docs/` + root `CLAUDE.md`/`README.md`/`REPRODUCE.md` | 🟡 drifted | Rich + cross-referenced but behind the 80→98→108 / 7→8-stage evolution. `CLAUDE.md` (auto-loaded) is the worst offender. |
| `paper/` — LaTeX (CHI/ASSETS 2027) | 🟢 content-strong | All figures/cites resolve, numbers trace to `key-numbers.json`. Weak: wrong documentclass + non-anonymized for double-blind, no build config, L11 sign inconsistency. |
| repro/hygiene — setup scripts, Makefile, gitignore, SHA256SUMS | 🟢 solid | Fresh-machine rebuild from GitHub+HuggingFace. One open defect: AppleDouble `._*` never purged after Mac-packed tarball unpack. |
| `scan-a11y-audit/` — Phase 4b ecological probe | 🟢 fn-healthy | 34-site Tier-3 prevalence; `analysis.py` is the SoT the verifier imports (3/3). Weak: no README, dead divergent `PATCH_AXE_RULES`, "30 sites" doc strings. |

---

## 2. Group A — Reproducibility & hygiene

- [ ] **[HIGH / trivial] Purge AppleDouble `._*` after tarball unpack.**
  `setup-workspace.sh` never strips `._*`; `analysis/stages/phase6_stage4b.py:61`
  `glob("*/*.png")` matches `._*.png` and `data/SHA256SUMS` has 0 `._*` entries,
  so a Mac-packed reproduce would fail the 9,408-PNG assertion. Add
  `find "$STAGE" -name '._*' -type f -delete` (and `.DS_Store`) after the unpack
  at `setup-workspace.sh:110`, before the rsync/cp move.
  *Frame as hardening — the off-repo tarball's actual `._*` content is unverified;
  the "~97k files" figure from the handoff is uncorroborated. Idempotent no-op on
  the current clean tree; cannot affect 108/108.*
- [ ] **[HIGH / small] Make figure regen produce stable diffs / document churn.**
  All 14 `figures/*.{png,pdf}` show modified after regen. PDF churn is a real
  3-byte `/CreationDate` diff — fix with `savefig(..., metadata={'CreationDate': None})`
  in all 7 generators. PNG churn is environment rasterization (not a timestamp),
  so document it instead. Minimum: note in `figures/README.md` + `REPRODUCE.md §4`
  that regen dirties binaries and to `git checkout -- figures/` if data is unchanged.
- [x] **[MEDIUM / trivial] Commit the 3 pending hygiene changes.** ✅ done this round —
  see [§7](#7-applied-this-round). `.gitignore` (+`.hf-stage`, now with comment +
  trailing newline) and exec-bit (100644→100755) on `setup.sh`/`setup-workspace.sh`;
  both are invoked as `./setup*.sh` so the bit is required. ⚠ git commit was
  user-approved this round.
- [ ] **[MEDIUM / small] Add `verify-ts` target + document it.** `verify_all.py`
  is Python-only; `setup*.sh`/`Makefile` have no npm refs; the load-bearing B2/B3
  guards (`src/.../ci-guards.test.ts`) and there is no CI, so they fire on no
  automated path. Add `verify-ts:` (`npm ci && npm run lint && npm test` — verified
  green: tsc exit 0, vitest 414/414 <4s) as an **optional** step in `REPRODUCE.md §4`.
  **Do NOT** fold into `verify-all` (would change the analysis-only reproduce contract).
- [ ] **[MEDIUM / small] Reproduce recipe for the 34-site ecological corpus.**
  7 JSONs are `category=local-snapshot`; `npm run scan` re-scans ebay/walmart/bestbuy
  live (clobbering snapshots) and skips auth-walled China pages. Add
  `scan-a11y-audit/README.md` documenting the live-vs-`--local` split, ordering, and
  `npm install` + `npx playwright install chromium` prereqs, with a "data is locked,
  don't re-scan" warning. *Corrected: drop the overwrite-guard code change.*
- [ ] **[MEDIUM / small] Hardcoded cross-model p-values in `analysis/bootstrap_decomposition.py:100-101`.**
  `2.83e-11` (Claude) is already **stale** — recomputes to `2.51e-11`; `1.09e-04`
  (Llama4) matches. Read both from `results/stats/primary_tests.csv`
  (`comparison=low_vs_base`, `chi2_p`). *Negligible impact — file is uncited, outside
  `verify-all`, Holm verdict unaffected. Corrected: drop the "read from breslow_day
  output" idea (different statistic). Regenerating the frozen CSV ⚠ NEEDS-USER-APPROVAL.*
- [ ] **[LOW / trivial] Surface masked shasum exit in `setup-workspace.sh:134`.**
  `shasum -c | grep -v ': OK$'` makes the subshell exit 0 even on FAILED, so
  corruption is printed but not aborted. Capture shasum's own status and `exit 1`
  (or a loud WARNING) on failure. *Corrected: the "all files OK always fires" claim
  is wrong — it only fires when truly OK.*
- [ ] **[LOW / trivial] Generalize the macOS `hf` probe.** `setup-workspace.sh:49`
  hardcodes `Library/Python/3.9/bin/hf` but the project pins 3.11. Use a glob
  `"$HOME"/Library/Python/3.*/bin/hf`. Fallback-only; minor.
- [ ] **[LOW / trivial] `scripts/maintenance/check-archival-state.sh` header overstates
  a count-check as SHA verification.** It does `wc -l` vs `find | wc -l`, never
  `shasum -c`. Correct the header comment (or add an opt-in `--verify-hashes` gated
  pass). Not in `verify-all`.
- [ ] **[LOW / trivial] Archival-state warnings unsatisfiable in a live dev checkout.**
  `check-archival-state.sh` flags `analysis/.venv` as "should NOT exist" though it's
  required for `verify-all`. Reword the script's "caches" section heading to note it
  targets the post-archival tree. *Corrected: drop the env-marker branching idea.*

---

## 3. Group B — Code quality

- [ ] **[MEDIUM / bug / trivial] Delete dead, divergent `PATCH_AXE_RULES` in
  `scan-a11y-audit/config.ts:46-60`.** Never imported; its 3-rule P7 (missing
  `landmark-unique`) yields **76.5%** Tier-3 vs the paper's **82.4%** from
  `analysis.py`'s 4-rule copy. `analysis.py` is the authoritative source the verifier
  loads — delete the export (optionally keep the doc-comment). Self-contained
  subproject, not in `verify-all`.
- [ ] **[MEDIUM / small] Consolidate stat primitives onto `analysis/lib/stats.py`.**
  `wilson_ci`/`cochran_armitage`/`odds_ratio_ci` duplicated across
  `compute_primary_stats.py`, `run_statistics.py`, `majority_vote_sensitivity.py`,
  `generate_results_tables.py`. **Do NOT touch `stages/` inline copies** (intentionally
  self-contained; risks 108/108). Numeric divergence is invisible (z=1.96 vs ppf =
  3.6e-05). Low-value in a frozen repo — defer unless already refactoring.
- [ ] **[LOW / trivial] Rename `expect_rate`'s `tol_frac` → `abs_tol`
  (`analysis/lib/assertions.py:53`).** Reused for Z-stats/betas/pp across `stages/`;
  `_constants.py:134` already documents `±0.05 in Z value`. Mechanical keyword-arg
  rename across ~18 callsites; behaviorally inert. Skip if keeping diff-free.
- [ ] **[LOW / trivial] Replace `sys.path` hack in `analysis/stage3_statistics.py:40-49`**
  with `from analysis.amt_statistics import (...)`. Eliminates an observable (benign)
  double-load. Verified to keep both invocations passing. Stylistic only.
- [ ] **[LOW / small] Extract `runAxeAndCustom(page)` helper in `scan-a11y-audit/scan.ts`**
  (~30 dup lines, *corrected: not ~90*, between `scanPage` 140-171 and `scanLocalDir`
  381-411). Latent maintainability only; no tests/type-check in `verify-all` path —
  hand-verify with `npx tsc --noEmit`. Defer.
- [ ] **[LOW / trivial] `jsEventListeners` permanently `0` in
  `scan-a11y-audit/custom-checks.ts:108`** with a misleading "via CDP" comment. CDP
  is unavailable in `page.evaluate()` context (so can't implement here). Fix the
  comment only; removing the field touches frozen JSONs. Reasonable to drop.
- [ ] **[LOW / small] Figure-generator boilerplate.** Real for `save_fig(png+pdf)`
  (all 7) and rcParams (4 truly identical). **Do NOT centralize `FAMILY_COLORS`** —
  hexes are intentionally repurposed per figure; `family_of()` is defined once already.
  Frozen, manually-run set — defer.

---

## 4. Group C — Docs accuracy

- [ ] **[HIGH / trivial] `CLAUDE.md:49` "7 stages (80/80)" → "8 stages (108/108) as of
  2026-06-06".** Auto-loaded every session = highest leverage. Fix BOTH counts. The
  same stale "7 stages" also lives in `analysis/README.md:24`, `scripts/audit/README.md:11`,
  `paper-supplementary/reproducibility-statement.md:60,65`,
  `docs/by-stage/pre-submission-checklist.md:15,25` — fix in the same pass.
  **Do NOT touch dated records** `docs/by-stage/audit-2026-05-15.md` /
  `_baseline-verify-all-2026-05-15.txt`.
- [ ] **[MEDIUM / trivial] Operator count 24→26 in `docs/amt-operator-spec.md`.**
  Lines 3, 31, and 400 (`24×23=552`→`26×25=650`), PLUS the family table line 28
  (`High | H1–H8 | 8` → `H1–H4, H5a/b/c, H6–H8 | 10`, the actual root cause) and
  `src/variants/patches/operators/README.md:3`. Code (`OPERATOR_ORDER`, 26 `.js`
  files, `operators.test.ts:134`) is ground truth.
- [ ] **[MEDIUM / small] Add `phase4b_ecological` to the audit surface.** Create
  `scripts/audit/audit-ecological.sh` (mirror `audit-stage4b.sh`,
  `python -m analysis.stages.phase4b_ecological`), add an `audit-ecological` Makefile
  target + `.PHONY`, and a row in `scripts/audit/README.md` (no doc-link —
  `phase4b-ecological.md` doesn't exist yet). Pairs with the docs index fix below.
- [ ] **[MEDIUM / small] Add Phase 4b row + by-stage doc to `docs/by-stage/README.md`.**
  Table lists 7 rows / "7 datasets"; create `docs/by-stage/phase4b-ecological.md`
  (corpus = `scan-a11y-audit/results/` ~34 JSONs, distinct from N=14,768). Reconcile
  "7 datasets"→8.
- [ ] **[MEDIUM / small] Refresh stale `README.md`.** Lead with `make verify-all`
  (108/108) not `make verify-numbers` (legacy); add full N=14,768 / 48-task Stage 3
  scope; mark EC2/SSM/`config-pilot4` sections HISTORICAL (burner accounts expired
  2026-05-12); add a `REPRODUCE.md`/HuggingFace pointer. Keep the 93.8%→38.5%
  composite headline (still valid).
- [ ] **[MEDIUM / small] Missing git tags `pre-archival-2026-05-14` + `pre-vv-2026-05-15`.**
  Asserted as existing in `docs/data-inventory.md:133`, `CLAUDE.md:79`,
  `paper/CLAUDE.md:74`, `paper-supplementary/reproducibility-statement.md:158`,
  `results/by-stage/README.md:50`; `git tag -l` returns **none** in both repos.
  `pre-submission-checklist.md:99-100` even has a `git reset --hard pre-vv-2026-05-15`
  that would fail. Reword to "create before submission" / drop the rollback-anchor
  language (preferred — historical commits can't be reliably reconstructed).
  ⚠ **Creating tags NEEDS-USER-APPROVAL.**
- [ ] **[MEDIUM / docs] Audit `.md` notes in `paper/` describe the pre-revision (v7) draft.**
  `ml-reviewer-audit.md`/`rebuttal-prep.md` use the old title and raise already-resolved
  temperature/F_UNK issues. Add "Historical (pre-2026-05 rewrite)" banners; fix
  `rebuttal-prep.md:3` title (it's a designated live doc). *Corrected: drop the
  "re-run the audit scripts" idea — the generator only survives in git history.*
  *(In `paper/` — out of scope this round per user.)*
- [ ] **[MEDIUM / docs] `docs/by-stage/audit-2026-05-15.md` frozen at 98/98.** Do NOT
  rewrite the dated body — add a "Superseded 2026-06-05: 8th stage, 108/108" banner
  (matches the file's own convention).
- [ ] **[LOW / trivial] TS test count 334→414** in `README.md:184` + `CLAUDE.md:59`
  (vitest reports 414). Leave the unrelated "334" SoM bid label in
  `mode-a-L5-shadow-dom-trace-report.md`.
- [ ] **[LOW / trivial] `docs/data-schema.md` S3/Zenodo → HuggingFace** at lines 119,
  190, 211 (per `REPRODUCE.md`). Leave genuinely-historical S3 mentions in handoff
  docs / the Zenodo future-task line.
- [ ] **[LOW / trivial] `CLAUDE.md:53` per-stage doc glob uses underscores**
  (`phase6_stage4b.md`); real files are hyphenated. Fix to `docs/by-stage/phase{1..6}-*.md`.
  *Corrected: drop the speculative "add ecological doc" clause.*
- [ ] **[LOW / trivial] `REPRODUCE.md:76` "~77k JSON files" vs `:118` "~59k".** ~59k
  is JSON-only; ~77k is total manifested files (incl. ~18k PNGs). Reword line 76 to
  "~77k small files (~59k JSON + ~18k PNGs)". Leave 118.
- [ ] **[LOW / trivial] `docs/data-inventory.md:4` "~22.5k case JSON" is wrong.** Real:
  ~16.8k dedup cases (N=14,768 selected) / ~59k JSON files on disk (~56.6k excl
  `archive/`). Note the dual flat + per-case-subdir layout. **Do NOT carry the
  "~22.5k" figure forward.**
- [ ] **[LOW / trivial] `scan-a11y-audit` "30 sites" → 34** in `analysis.py:5-6`,
  `config.ts:3`, `scan.ts:4` (real `SITES` = 34 = 30 + 4 WebArena). Mirror the actual
  Table-1/2 (all 34) vs Table-3/5 (30 real-world) split.
- [ ] **[LOW / trivial] Two Tier-3 denominators (82.4%/34 vs 83.3%/30)** — already
  mis-cited once in `paper/ml-reviewer-audit.md:125`. Add a one-line comment at
  `scan-a11y-audit/analysis.py:511` clarifying the paper §4 headline uses 82.4%/34.
- [ ] **[LOW / trivial] `docs/project-phases.md` stale (2026-05-06, "~7,000+/~300-task").**
  Add a status banner pointing to the final 48-task / 7,488 Stage 3 / N=14,768 and
  `docs/by-stage/phase6-stage3.md` (matches existing banner convention).
- [ ] **[LOW / trivial] `src/.../operators.test.ts:265-267` cites non-existent
  `scripts/scan-operator-pairs.ts`** + missing `operator-non-commutativity-matrix.json`.
  Reword the comment + `amt-operator-spec.md §9.4` to reflect the matrix was never
  generated and the composition study uses fixed canonical ordering. Do NOT regenerate.
- [ ] **[LOW / small] Label vestigial script dirs.** Add a one-line banner to
  `scripts/README.md`: `runners/launchers/infra/data-pipeline/ssm` are
  data-collection-era (accounts expired 2026-05-12), retained for forensics, not in
  `verify-all`.

---

## 5. Group D — Paper (`../paper/`) — ⚠ ALL OUT OF SCOPE THIS ROUND (user deferred)

- [ ] **[HIGH / trivial] ⚠ Wrong documentclass + non-anonymized authors for
  double-blind review.** `main.tex:31` is `[sigplan,screen]`; switch to
  `[sigconf,review,anonymous]{acmart}`. *Corrected: the `anonymous` option
  auto-suppresses the author block — no manual wrapping needed.* Restore real
  authors for camera-ready only. Deadline 2026-09-11 (open). **NEEDS-USER-APPROVAL.**
- [ ] **[MEDIUM / small] No LaTeX build toolchain/config.** `CLAUDE.md:9` documents
  `latexmk -pdf` but there's no `latexmk`/`.latexmkrc`/Makefile in `paper/`. Add a
  minimal Makefile/`.latexmkrc` (pdflatex + biber, clean target).
- [ ] **[MEDIUM / small] ⚠ L11 sign-convention: `+2.3pp` used to mean a drop.**
  `key-numbers.json` stores drops negative; the paper writes large drops with `−` but
  L11/Llama-L11 with `+` while calling them "drops" — and `06-discussion.tex:24` pairs
  a real `+8.5pp` gain with the `+2.3pp` drop under identical `+`. Rewrite L11 drop
  mentions as `−2.3pp`/`−14.1pp` (`main.tex:133,135`; `05-results.tex:78,108,117,122,139`).
  **NEEDS-USER-APPROVAL (touches paper numbers).**
- [ ] **[MEDIUM / hygiene / small] Stale duplicate figure PNGs (18 unused, ~15 MiB,
  3 naming schemes).** Safe part: fix `paper/CLAUDE.md:52-58` "Figures used in PDF"
  list → the actual `fig1..fig10`+`figA1`. Optional: delete the 7 byte-identical
  old-scheme dups (~5 MiB). **Do NOT bulk-delete the 11 unique-content orphans** —
  `figures-status.md` reserves their fate for the user.
- [ ] **[LOW / hygiene / small] 48 of 109 bib entries uncited.** No `\nocite{*}`, so
  they don't render — pure `.bib` tidiness. Optional prune. `norman2013` is superseded
  by Gibson/Gaver — prune, don't re-cite. Confirm 2026-cited entries aren't staged for
  unfinished sections.
- [ ] **[LOW / quality / trivial] L11 SSIM 0.976 (appendix mean/39) vs 0.979
  (methodology median/9408).** Both already labeled in situ; not co-located. Optional
  half-clause at `main.tex:449`. Reasonable to drop.

---

## 6. Group E — Tests

- [ ] **[HIGH / small] pytest collection aborts on the documented core install.**
  `analysis/models/secondary.py:19` top-level `from sklearn...`, re-exported by
  `models/__init__.py:15`, cascades to break collection of 48 tests (`test_primary`
  32 + `test_secondary` 16); core install collects only 19. Add
  `pytest.importorskip("sklearn")` at the top of `models/test_primary.py` +
  `models/test_secondary.py` (or wrap the `__init__.py` import in try/except). For
  SHAP: gate only `TestShapSummaryPlot` (function-local import in `viz/figures.py:180`)
  — **do NOT** `importorskip("shap")` at `viz/test_figures.py` top (would over-skip 7
  passing tests). Result: ~18 passed + skips instead of a 0-run abort. *Not in `verify-all`.*
- [ ] **[TRIVIAL] Reconcile the "67 tests" claim** (`README.md:188`, `CLAUDE.md:61`):
  "67 tests; 48 require scikit-learn (+shap for the SHAP test) via
  `requirements-optional.txt`; core install collects 19." *(Same root cause as above;
  do together.)*

---

## 7. Applied this round

These are the only changes made in the session that produced this document
(user-approved: "this round's edits + the 3 pending hygiene changes, committed together"):

1. **`.gitignore`** — `.hf-stage` entry given a section comment + trailing newline
   (was a bare, newline-less last line). Tracks the HuggingFace download staging dir
   that `setup-workspace.sh` creates.
2. **`setup.sh`** — exec bit `100644 → 100755` (invoked as `./setup.sh`).
3. **`setup-workspace.sh`** — exec bit `100644 → 100755` (invoked as `./setup-workspace.sh`).
4. **`docs/improvement-menu.md`** — this file.

Everything else above is unstarted.

---

## 8. Out of scope / do-not-touch

- **`.kiro/steering/` frozen records** — `project-context.md` and any locked narrative.
- **Frozen data** — `data/`, `data/SHA256SUMS`, `scan-a11y-audit/results/*.json`
  (34 frozen audit JSONs), `data/stage4b-ssim-replay/` (9,408 PNGs + manifest). Do
  not re-run experiments or re-scan; AWS burner accounts expired 2026-05-12.
- **Dated/point-in-time audit records** — `docs/by-stage/audit-2026-05-15.md`,
  `docs/by-stage/_baseline-verify-all-2026-05-15.txt`, the historical snapshots in
  `pre-submission-checklist.md`, and the `paper/` audit `.md` files (banner them,
  don't rewrite their bodies).
- **Locked paper numbers / `results/key-numbers.json`** — never edit derived numbers.
- **`paper/` source (this round)** — user deferred all Group D.
- **`stages/` inline stat re-implementations** — intentionally self-contained;
  rewiring risks the 108/108 verifier for zero numeric gain.
- **Actions requiring user direction (⚠):** any `git tag`, regenerating any frozen
  artifact (e.g. `results/stats/primary_tests.csv`), and deleting the 11
  unique-content orphan figures in `paper/`.
