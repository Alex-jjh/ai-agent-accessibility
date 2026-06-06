# Pre-Submission Checklist

> Run **before** rebuilding the paper PDF for any submission, rebuttal, or
> camera-ready deadline. Most boxes auto-tick via `make pre-submit`; a few
> items are manual.

## One-line check

```sh
make pre-submit
```

Should output:
```
Total: 108 passed, 0 failed across 8 stages       (verify-all)
AUDIT COMPLETE: 28 passed, 0 failed              (audit-paper)
=== built 18 files in paper-supplementary/ ===   (build-supplementary)
✅ Pre-submission gate passed.
```

If any line above doesn't appear, fix the failure before continuing.

## Auto-checked (`make pre-submit`)

- [ ] **`make verify-all` → 108/108 PASS** across 8 stages. Failures here
  mean a paper claim drifted vs current data — read the FAIL line(s) to
  see which `_constants.py` value disagrees with which CSV/JSON.
- [ ] **`make audit-paper` → 28/28 PASS in ~3s**. Independent re-derivation
  of every paper §4–§5 claim from raw case JSONs; zero external dependency.
- [ ] **`make audit-archival` → all checks GREEN**. Disk size sane, no
  regenerable caches present, `data.zip` backup present, Stage 4b SHA-256
  manifest matches filesystem. Note: the `pre-archival-2026-05-14` tag was
  planned as a rollback anchor for the archival pass but was never actually
  created, so no such git anchor exists.
- [ ] **`paper-supplementary/` rebuilt** with 18 files (1 `MANIFEST.txt` +
  16 derived statistics + 2 manual MDs). Bundle is gitignored (derivable).

## Manual checks

- [ ] **Both repos `git status` clean** (no uncommitted files):
  ```sh
  git -C ai-agent-accessibility status --short    # → empty (or only data.zip)
  git -C paper status --short                     # → empty
  ```

- [ ] **Rollback anchors**: the `pre-archival-2026-05-14` and
  `pre-vv-2026-05-15` tags were planned as rollback anchors but were never
  actually created in either repo, so there is no reliable git anchor to
  reconstruct those historical states from. If you want a rollback point for
  this submission, create one explicitly now:
  ```sh
  git -C ai-agent-accessibility tag --list 'pre-*'   # currently empty
  git -C paper tag --list 'pre-*'                    # currently empty
  ```

- [ ] **No N-drift** in paper vs current data:
  ```sh
  cd paper && grep -nE '14,772|2,188|10/13|10 of 13|p<10\^\{-6\}|p < 10\^\{-6\}' \
                    sections/*.tex main.tex
  # → empty
  ```

- [ ] **Paper PDF rebuilt** with current text + figure files:
  ```sh
  cd paper && latexmk -pdf main.tex
  # PDF should regenerate without errors. Inspect main.pdf for:
  #   - N=14,768 in abstract / §4 / §6 / §8
  #   - C.2 N=2,184 in §4 + §5 + §3
  #   - 5/13 Mode A convergence (not 10/13) in §4
  #   - Wilcoxon p ≈ 1.3e-4 (not <10⁻⁶) in §5 + §2
  ```

- [ ] **Figures inventory reviewed**: see [`figures-status.md`](figures-status.md).
  Some figures may need redraw with current Stage 3 numbers — user separately
  redraws and replaces files in `paper/`.

- [ ] **Bibliography current**: `bibtex main` runs clean; `references.bib`
  contains all `\cite` keys.

- [ ] **Page count within venue limit**: CHI 2027 = 18 pages (excl. refs).

## Rebuttal-time additions

When responding to reviewers:

- [ ] Update `paper/rebuttal-prep.md` with anticipated reviewer concerns.
- [ ] Re-run `make pre-submit` after any text change to catch drift.
- [ ] If new analysis is added (e.g. additional sensitivity check),
  add it to the appropriate stage verifier in `analysis/stages/` so future
  drift is caught automatically.

## Camera-ready additions

- [ ] DOI archive populated (Zenodo / OSF) with `data/` + `paper-supplementary/`.
- [ ] Update `reproducibility-statement.md` with the actual DOI.
- [ ] Re-run `make pre-submit` to refresh `key-numbers.json` build timestamp.
- [ ] Final paper PDF includes the DOI in the supplementary footnote.

## Rollback

The `pre-vv-2026-05-15` tag was planned as a rollback anchor for the V&V pass
but was never actually created, so the historical pre-V&V state can't be
reliably reconstructed from a git anchor. Before starting any risky pass,
create your own rollback point and reset to *that* if anything goes wrong:

```sh
git -C ai-agent-accessibility tag pre-submit-$(date +%Y%m%d)
git -C paper tag pre-submit-$(date +%Y%m%d)
# ...then if needed:
# git -C ai-agent-accessibility reset --hard pre-submit-<date>
```

## See also

- [`audit-2026-05-15.md`](audit-2026-05-15.md) — full V&V audit narrative
- [`figures-status.md`](figures-status.md) — figure inventory + redraw status
- [`paper-supplementary/README.md`](../../paper-supplementary/README.md) —
  reviewer-facing bundle entry point
- [`paper-supplementary/reproducibility-statement.md`](../../paper-supplementary/reproducibility-statement.md) —
  full reproduction instructions
