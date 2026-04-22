# Visual Equivalence Validation — Architecture

**Goal**: close CHI 2027 paper §6 Limitations #7 — quantify pixel-level visual
difference between base and low variants on every URL agents actually visited,
to ground the claim that CUA's 35.4pp drop reflects functional degradation,
not visual degradation.

**Primary deliverable**: a short §6 subsection with SSIM/pHash numbers and
Group A/B/C classification that upgrades "not formally guaranteed" to "pixel-
level ground truth validated".

---

## 1. Design Principles

1. **Environment-centric replay, not agent re-run**. We do not need new agent
   behavior; we need new screenshots of the same DOM states. Replay URLs
   directly with Playwright, skipping BrowserGym entirely.
2. **Pipeline fidelity with Track A**. Same chromium build, same viewport
   (1280×720), same `apply-low.js` (byte-identical), same WebArena login
   cookies. Only the agent is removed.
3. **Dual capture modes**:
   - **Aggregate replay** — base vs low on every URL the agents visited
     (137 URLs), answers "does the full low bundle shift rendering?"
   - **Per-patch ablation** — 13 patches applied individually on 4
     representative URLs, answers "which patch is responsible for which
     pixel delta?"
4. **Human-in-the-loop review**. SSIM/pHash is objective but noisy; a
   self-contained HTML gallery lets us eyeball every pair and flag the
   edge cases reviewers would notice.
5. **Reversible over clever**. We tried an HTTP redirect rewriter to work
   around Magento's stale base_url; the correct fix was at the deployment
   layer (Terraform user-data + one-shot Magento re-config). Application
   code stays clean.

---

## 2. System Topology

```
┌────────────────────────────────────────────────────────────────────┐
│                   New burner account 840744349421                  │
│                                                                    │
│  ┌─────────────────────────┐      ┌──────────────────────────────┐ │
│  │ Platform EC2            │      │ WebArena EC2                 │ │
│  │ (i-0784a5f4f04495ca6)   │      │ (i-0bbaa2f34189d9080)        │ │
│  │ 10.0.1.51 / r6i.4xl     │      │ 10.0.1.50 / r6i.2xl          │ │
│  │                         │      │                              │ │
│  │ python3.11 + playwright │ ───► │ Docker: shopping, admin,     │ │
│  │ /root/platform/         │ HTTP │         reddit, gitlab,      │ │
│  │                         │      │         kiwix33              │ │
│  │  replay-url-            │      │ Magento base_url =           │ │
│  │    screenshots.py       │      │   http://10.0.1.50:7770/     │ │
│  │  replay-url-            │      │   (fixed via SSM one-shot)   │ │
│  │    patch-ablation.py    │      │                              │ │
│  └─────────────────────────┘      └──────────────────────────────┘ │
│             │                                                      │
│             │ .tar.gz via S3 sync                                  │
│             ▼                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ S3: a11y-platform-data-<acct>                               │   │
│  │   experiments/visual-equivalence-<ts>.tar.gz                │   │
│  └─────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────────────┐
│  Local workspace (Windows)                                         │
│                                                                    │
│  analysis/visual_equivalence_analysis.py                           │
│    ├─ --mode aggregate → SSIM/pHash/MAD per URL                    │
│    └─ --mode ablation  → per-patch attribution table               │
│                                                                    │
│  analysis/visual_equivalence_gallery.py                            │
│    → self-contained HTML at results/visual-equivalence/            │
│       gallery.html (local-storage-backed flags)                    │
└────────────────────────────────────────────────────────────────────┘
```

No public ingress. SSM Session Manager + SSM Run Command for all EC2
interaction. Cloud outbound (S3, Bedrock, ECR, SSM) via VPC endpoints.

---

## 3. Data Pipeline

### Phase A — Agent URL extraction (already done)

```
data/pilot4-full/        ┐
data/expansion-cua/      │   scripts/extract_agent_urls.py
data/expansion-claude/   ├──────────────────────────────────►
data/expansion-llama4/   │   walks trace-attempt-*.json for
data/expansion-som/      │   every "goto(URL)" + observation URL
data/expansion-cua/      ┘

                         results/visual-equivalence/
                            agent-urls-dedup.csv       (137 unique)
                            agent-urls-summary.md      (per-app table)
```

Historical URLs point at `10.0.1.49` (old burner) and `10.0.1.50` (recent);
replay script rewrites either to current WebArena IP (CLI flag).

### Phase B — Aggregate replay (137 URLs × 2 variants ≈ 25 min)

```
            for url in 137 URLs:
              for variant in {base, low}:
                - new Playwright context (1280×720, cookies pre-injected)
                - goto(url, wait_until=networkidle) + 1.5s settle
                - if variant == low: page.evaluate(apply_low_js) + 0.8s reflow
                - screenshot → ./data/visual-equivalence/replay/<slug>/{base,low}.png

            manifest.json:
              [{url, variant, screenshot, elapsed_s, final_url, title,
                dom_changes, success, error}, …]
```

Login is performed once per app before the loop (`_shopping_login_http`
for Magento storefront, canonical browser selectors for admin, fallback
selector chains for reddit/gitlab). Cookies are reused across every
capture context so pages render in their authenticated state — matching
what the agents saw.

### Phase C — Per-patch ablation (4 URLs × 14 captures ≈ 5 min)

```
            apply-low-individual.js has the 13 patch blocks each
            gated on `window.__ONLY_PATCH_ID === <id>`.

            for url in {one per app (4)}:
              - capture base
              - for patch_id in 1…13:
                  page.evaluate("window.__ONLY_PATCH_ID = " + patch_id)
                  page.evaluate(apply_js)
                  screenshot → patch_<id>.png

            → 4 base + 52 per-patch = 56 images
```

Each patch's SSIM vs base ranks the visual impact of that single operator.
Expected outcome:
- **Group A** (SSIM ≈ 1.0): ARIA strip, tabindex delete, lang delete,
  role=presentation changes — pure a11y tree semantics
- **Group B** (SSIM < 0.95): `label.remove()` (text disappears),
  `thead → div` (table reflow)
- **Group C** (SSIM ≈ 1.0 but click-inert): `link → span` — the blue
  underlined styling stays, `href` goes away. This is the hardest-hitting
  Same Barrier evidence.

### Phase D — Analysis (local)

```
./data/visual-equivalence/{replay,ablation}/  ┐
                                              │
                                              ▼
                                  visual_equivalence_analysis.py
                                    computes:
                                      - SSIM (structural similarity)
                                      - pHash (perceptual hash distance)
                                      - MAD (mean absolute pixel diff)
                                      - per-URL classification A / B / C
                                    writes:
                                      results/visual-equivalence/
                                        aggregate.csv
                                        ablation.csv
                                        aggregate-summary.md

                                  visual_equivalence_gallery.py
                                    writes:
                                      results/visual-equivalence/
                                        gallery.html
                                    keyboard: J/K navigate,
                                             1/2/3 flag A/B/C,
                                             S shortcut save JSON
```

---

## 4. Failure-Mode Decomposition (What This Validates)

Paper §5.3 currently claims:

| agent      | base | low  | Δ      |
|------------|------|------|--------|
| text-only  | ~95% | 40%  | -55.4  |
| CUA        | 95.4 | 58.5 | -35.4  |
|                                     |
| functional pathway (CUA Δ)   = ~35pp  |
| semantic pathway (text − CUA) = ~20pp |

The 35pp CUA drop is load-bearing for the "functional pathway" estimate.
If any meaningful fraction of that drop is actually due to CUA
mis-clicking pixels that shifted under low variant, the decomposition
breaks.

Phase B/C produce:

1. **Whole-bundle SSIM** — proves the full low variant is near-identical
   pixel-wise on > X% of agent-visited URLs (target: X ≥ 90)
2. **Per-patch attribution** — proves any visual deviation is confined
   to patches 3 (label.remove) and 9 (thead→div), both of which the
   paper can cite as "expected visual artifacts with bounded CUA impact"
3. **Group C evidence** — proves `link → span` (patch 11) produces
   visually identical output while breaking `href` clickability,
   supporting the Same Barrier claim directly

Combined with the 77.8% trace signature analysis already in hand
(`results/visual-equivalence/cua-failure-signature.md`), this closes
the §6 Limitations hole with a defensible three-source argument:

- **Visual**: SSIM-based pixel equivalence on 137 URLs
- **Structural**: Patch-level attribution showing most drop is CSS-
  preserving
- **Behavioral**: 77.8% of CUA low failures match click-inert signature
  (≥8 clicks, ≥90% inert, ≥3 same-region loops)

---

## 5. Consistency Guardrails

- Agent data frozen as of commit `d104d01`. No re-runs of the 13-task
  experiment; this is validation-only.
- `apply-low.js` not modified between experimental runs and replay.
  Replay reads the same file (via `src/variants/patches/inject/apply-low.js`).
- Viewport matches BrowserGym's 1280×720 default. Changing this would
  invalidate the pixel comparison.
- Chromium version pinned by `python3.11 -m playwright install chromium`
  at bootstrap time — documented in `scripts/bootstrap-visual-equivalence.sh`.
- If a selector breaks on a new WebArena AMI, fix it in
  `_try_login_selectors` with a fallback chain — never hardcode
  brittle CSS classes.

---

## 6. Known Failure Modes + Mitigations

| Symptom                                    | Root cause                                          | Fix location                                   |
|--------------------------------------------|-----------------------------------------------------|------------------------------------------------|
| Magento 302 → stale public hostname        | AMI bake w/ old hostname; user-data IMDSv1 failed   | `infra/webarena.tf` now uses IMDSv2 token      |
| chromium `libnspr4.so` not found           | AL2023 packages renamed; `yum install` no-op        | `scripts/bootstrap-visual-equivalence.sh` dnf  |
| `ModuleNotFoundError: requests`            | Initially not in bootstrap list                     | Added to bootstrap + `ssm-install-requests.json` |
| `python3` on Platform → 3.9 (no deps)      | AL2023 system python is 3.9; deps live in 3.11      | SSM scripts always call `/usr/bin/python3.11`  |
| Reddit/GitLab auth signal check false neg  | Version-specific nav text                           | Login confirmed by cookie presence (REMEMBERME + _gitlab_session) |
| SSM credential expiry mid-wait             | 1h burner token TTL                                 | `ada credentials update --profile=a11y-pilot`  |

---

## 7. File Manifest

| Path                                                  | Role                                |
|-------------------------------------------------------|-------------------------------------|
| `scripts/extract_agent_urls.py`                       | Phase A (done)                       |
| `results/visual-equivalence/agent-urls-dedup.csv`     | 137 URLs input                       |
| `results/visual-equivalence/cua-failure-signature.md` | Trace-side evidence (77.8%)          |
| `scripts/replay-url-screenshots.py`                   | Phase B driver                       |
| `scripts/replay-url-patch-ablation.py`                | Phase C driver                       |
| `scripts/run-visual-equivalence.sh`                   | EC2 one-shot orchestrator            |
| `src/variants/patches/inject/apply-low.js`            | FROZEN — production variant          |
| `src/variants/patches/inject/apply-low-individual.js` | Per-patch gated equivalent           |
| `analysis/visual_equivalence_analysis.py`             | SSIM/pHash/MAD compute               |
| `analysis/visual_equivalence_gallery.py`              | Human review HTML                    |
| `analysis/cua_failure_trace_validation.py`            | 77.8% signature detector             |
| `docs/analysis/visual-equivalence-plan.md`            | v2 plan + success criteria           |
| `docs/analysis/visual-equivalence-validation.md`      | §6 Limitations drop-in template      |
| `docs/analysis/visual-equivalence-architecture.md`    | This doc                             |
| `scripts/bootstrap-visual-equivalence.sh`             | EC2 bootstrap (dnf, python3.11)      |
| `scripts/ssm-*.json`                                  | One-shot SSM wrappers                |
| `scripts/ssm-fix-magento-baseurl.json`                | Fallback when user-data fails        |
| `infra/webarena.tf`                                   | IMDSv2 token, base_url seed          |

---

## 8. Next Steps (Execution Checklist)

- [x] Deploy new burner 840744349421; both EC2 online
- [x] Fix AL2023 chromium deps (nspr/nss via dnf)
- [x] Fix Magento base_url via one-shot SSM (Terraform fixed for future)
- [x] Verify login for all 4 apps
- [ ] Launch Phase B aggregate replay (30 min)
- [ ] Launch Phase C per-patch ablation (10 min)
- [ ] Upload results to S3; download locally
- [ ] Run analysis → aggregate.csv + ablation.csv
- [ ] Open gallery.html; flag ambiguous pairs
- [ ] Write final §6 numbers (SSIM p50/p90, Group breakdown, patch attribution)
- [ ] Commit SSIM results + drop-in to `docs/analysis/visual-equivalence-validation.md`
