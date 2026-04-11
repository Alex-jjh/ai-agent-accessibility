# AI Agent Accessibility Platform — Project Steering

## Project Overview

Empirical research platform studying web accessibility vs AI agent task success.
Dual-track: Track A (WebArena controlled experiments), Track B (HAR replay ecological survey).
Six modules: Scanner, Variants, Runner, Classifier, Recorder, Analysis (Python).

## Current Status

Tasks 1–22 complete (all 6 modules implemented, 334 TS + 67 Python tests passing).
Scanner verified on real websites (EC2 + local). LiteLLM → Bedrock verified.
Infrastructure: private subnet + SSM (no public access, burner account compliant).
Pilot 1 completed 2026-04-01 — 54 cases, 4 successes (7.4% raw / 66.7% effective).
Root cause analysis identified 5 failure categories; 3 P0 code fixes applied and pushed.
Round 5 regression (2026-04-02): task ID mapping corrected from test.raw.json,
BrowserGym 500ms→3000ms timeout fixed, wikipedia excluded (map dependency),
agent prompt tuned for concise answers, send_msg_to_user sanitized.

Screening completed (2026-04-03):
- ecommerce_admin: 2/12 success (16.7%) — tasks 4, 14. Admin routing fixed (/admin path).
- ecommerce storefront: 3/10 success (30%) — tasks 23, 24, 26 (review search type).
- reddit: 4/9 success (44%) — tasks 27, 29, 30, 67 (forum navigation type).
- Regression v5: 3/9 (33%) — platform stable, zero crashes/timeouts/ValueError.

Shopping login fix completed (2026-04-04):
- Root cause: BrowserGym hooks ALL Playwright navigation after env.reset() +
  Magento regenerates PHPSESSID on login + Docker URL misconfiguration.
- Fix: HTTP login via Python requests (bypasses browser entirely), cookie injection
  via context.add_cookies(), reload via env.step(goto(start_url)).
- Verified: Task 47 agent sees "Sign Out", navigates to My Account, sees order history.
- Tasks 47-50 now viable for Pilot 2.

Literature-driven experiment hardening completed (2026-04-05):
- Low variant patches aligned to Ma11y [ISSTA 2024] WCAG failure operators.
  8 direct matches + 4 novel extensions (E1-E4) documented.
  3 new operators added: F42 (link→span), F77 (duplicate IDs), F55 (focus blur).
- Vision-only agent control condition implemented. ObservationMode extended to
  'text-only' | 'vision' | 'vision-only'. Vision-only agent receives screenshot
  only (no a11y tree) — serves as causal control since DOM mutations change
  semantics but not visual appearance.
- Semantic density metric defined: interactive_nodes / total_a11y_tree_tokens.
  Python module with CLI and 11 tests. Quantifies "token inflation pathway".
- Aegis failure taxonomy comparison: 6 modes vs our 12 types, 5 novel types.
- Pilot 3 config updated: 2 agents × 6 tasks × 4 variants × 5 reps = 240 runs.

Pilot 4 in progress (2026-04-07): 240 cases with Plan D variant injection.
- Plan D: context.route() + deferred patch (load+500ms) + MutationObserver guard
- Smoke test confirmed: ecom:23 low 0/1, no tablist/tabpanel in trace (goto escape blocked)
- 52/240 completed before bridge hang fix; resumed with 120s bridge timeout + vision skip
- Mid-run text-only: low 25% → ml/base/high 100% (step function replicates)
- Three-layer hang prevention: bridge 120s timeout, wall-clock 10min, vision-only skip

Open issues:
- Pilot 4 running (~188 cases remaining, ~10-12 hours)
- reddit × vision-only may still be slow (large SoM overlay on 200+ elements)
- Composite score compression persists (0.386–0.461 vs 0.00–1.00)

Pilot 3a completed (2026-04-05): 120 cases, 87/120 (72.5%).
- Monotonic gradient: low 20% → ml 86.7% → base 90% → high 93.3%
- Low vs base: χ²=29.70, p<0.0001, V=0.704. Core finding confirmed.
- Dose-response is step function: low→ml jump = 91% of total effect.
- Two failure pathways: token inflation (admin:4, reddit:67) + content invisibility (ecom:23/24/26).

Pilot 3b completed (2026-04-05/06): 240 cases (text-only + vision-only).
- Text-only replicates 3a: 71.7% overall, low vs base p<0.001.
- Vision-only failed first run (LiteLLM config not loaded), re-running.
- Variant injection race condition discovered: goto() reload clears patches non-deterministically.
  Fixed with three-layer defense (init_script + listeners + secondary verification).
- SoM overlay implemented for vision-only agent (PIL-based bid label rendering).

Next: Analyze Pilot 3b vision-only results when re-run completes.
See docs/platform-engineering-log.md for full bug catalog and analysis reports.

Pilot 4 completed (2026-04-07): 240/240 cases, N=240 full design matrix.
- Text-only: low 23.3% → ml 100% → base 86.7% → high 76.7%
- Vision-only (SoM): low 0% → ml 23.3% → base 20% → high 30%
- Primary stat: low vs base χ²=24.31, p<0.000001, Cramér's V=0.637
- Plan D verified: 33/33 goto traces show persistent degradation
- Three failure pathways: content invisibility, token inflation, phantom bids

CUA (Computer Use Agent) integration completed (2026-04-07):
- Pure coordinate-based vision agent via Anthropic Computer Use tool + Bedrock
- LiteLLM cannot forward computer_use → direct boto3 Bedrock Converse API
- Architecture: bridge self-driven (cua_bridge.py), fully decoupled from existing modes
- Smoke test: ecom:23 base, reward=1.0, 11 steps, 139K tokens, 72s
- Two rounds of code review: 11 issues found, all fixed
- Pilot 4 CUA running: 6 tasks × 4 variants × 5 reps = 120 cases

Pilot 4 CUA completed (2026-04-08): 120/120 cases, 109/120 (90.8%).
- CUA: low 66.7% → ml 100% → base 96.7% → high 100%
- Low vs base: χ²=9.02, p=0.0027, V=0.388
- Causal decomposition: text-only 63.3pp drop = ~33.3pp semantic + ~30.0pp cross-layer
- reddit:29 INVERSION: CUA 0/5 vs text-only 4/5 at low (link→span breaks navigation)
- All 10 low-variant CUA failures are cross-layer confounds (0 pure-semantic)
- admin:4 base 1 failure = UI complexity (coordinate precision), not a11y-related
- Detailed analysis: data/pilot4-cua-analysis.md

PSL expanded smoke completed (2026-04-08): 6 cases, 5/6 (83.3%).
- PSL does NOT work: aria-hidden="true" shows as `hidden=True` in BrowserGym but
  elements retain bid/role/name and are fully clickable via click(bid)
- role="presentation" on headings/landmarks also ignored in BrowserGym snapshot
- BrowserGym serialization divergence from real screen readers = publishable finding
- Detailed analysis: data/psl-expanded-smoke-analysis.md

Cross-layer confound identified — low variant patches classified:
- ✅ Pure semantic (~6 patches): alt, aria-label, lang, tabindex, heading role
- ⚠️ Cross-layer (~3 patches): label removal, thead→div
- 🔴 Functional breakage (~4 patches): link→span (deletes href), Shadow DOM

Architecture diagrams generated (2026-04-08):
- 4 figures in figures/ (matplotlib, 300dpi PNG):
  - figure1_system_architecture.png: system overview with 3-layer injection mechanism
  - figure2_axtree_pipeline.png: a11y tree processing from Chrome to agent observation
  - figure3_variant_injection.png: variant patch detail per level + agent impact matrix
  - figure4_layer_model.png: five-layer architecture (L0-L4) with bid lifecycle
- figure4_layer_model_spec.md: detailed text spec for hand-drawing the layer diagram
- Five-layer model documented: L0 Server (untouched) → L1 DOM (all patches target here)
  → L2 Blink AX Tree (auto-derived) → L3 BrowserGym (serialization + bid + SoM)
  → L4 Agent (observation + action)
- bid lifecycle: born in L3, written to L1, read via L2, serialized in L3, used by L4, resolved back to L1
- Phantom bid mechanism: variant patch replaces DOM node → bid attr lost → SoM label persists
  in screenshot → agent clicks stale bid → "Could not find element" → 20+ retry loop

Next steps — Task expansion with incremental validation:
- Phase 0 (ongoing): Fix low variant cross-layer confound
  - Fix Patch 11 (link→span → preserve href), run CUA 30 cases
  - SRF (Screen-Reader-Faithful) serialization — filter hidden=True nodes in bridge
- Phase 1: Incremental task addition workflow (see Task Expansion Workflow below)
  - Add 1-3 new tasks at a time from WebArena task pool
  - Smoke test each task × 4 variants (1 rep, text-only) to verify DOM observations
  - Read traces to confirm variant patches produce expected a11y tree changes
  - Run full experiment (5 reps × 2-3 agents) only after smoke validation passes
- Phase 2: Scale to 15-20 tasks across all 4 WebArena apps
- Phase 3 (optional): Full 3-agent × 4-variant decomposition matrix

## Task Expansion Workflow

When adding new tasks to the experiment, follow this incremental validation process:

### Step 1: Select candidate tasks
- Check test.raw.json for tasks on the target app (use task-site-mapping.json)
- Prefer tasks with eval_type: string_match or program_html (avoid llm_eval)
- Prefer tasks that exercise different page types (product pages, search, forms, lists)

### Step 2: Smoke test — variant DOM observation
- Create a smoke config with the new task(s), all 4 variants, 1 rep, text-only only
- Run on EC2: `npx tsx scripts/run-pilot3.ts --config config-smoke-newtask.yaml`
- Download traces and READ THEM — verify for each variant:
  - low: ARIA attrs removed, headings→div, links→span in a11y tree
  - medium-low: role="button" present but no keyboard handlers
  - base: original DOM, no patches
  - high: aria-label added, landmarks present, skip-link exists
- Check: does the task's critical information survive each variant?
  (e.g., if task asks "what is the price?" — is the price still visible in low?)
- Annotate task feasibility per variant (feasible / infeasible / ambiguous)

### Step 3: Full experiment run
- Only after smoke validation passes for all variants
- Config: new task(s) × 4 variants × 5 reps × text-only (+ optionally CUA)
- Use experiment-run-and-upload.sh for auto S3 upload on completion
- Download locally, run analysis, compare with existing task results

### Step 4: Integrate into main experiment
- Add validated tasks to the primary config (config-pilot5.yaml or similar)
- Update task count in steering and proposal

## Weekly Account Rotation Workflow

Burner accounts expire after 7 days. Deployment is automated:

### Before account expires (day 5-6):
1. Upload experiment data: `bash scripts/experiment-upload.sh <name> ./data/<dir>`
2. Or use auto-upload wrapper in launch scripts
3. Download to local: `bash scripts/experiment-download.sh --latest <name>`

### New account setup (day 1):
1. Get new burner account from https://iad.merlon.amazon.dev/burner-accounts
2. Configure credentials:
   `ada credentials update --account=<ID> --provider=conduit --role=IibsAdminAccess-DO-NOT-DELETE --once --profile=a11y-pilot`
3. Enable Bedrock model access in console (Claude Sonnet 4, Haiku 3.5, Nova Pro, Llama 4)
4. Run: `bash scripts/deploy-new-account.sh` (terraform apply + SSM wait, ~5 min)
5. SSM into Platform EC2, run `bash scripts/bootstrap-platform.sh`
6. Start LiteLLM, run smoke test to verify

### What does NOT change between accounts:
- WebArena private IP: fixed at 10.0.1.50 (Terraform `private_ip` parameter)
- Platform private IP: fixed at 10.0.1.51
- All config YAML files: no changes needed
- All source code: git clone from repo
- Region: always us-east-2

### What DOES change:
- EC2 instance IDs (update in steering if needed for reference)
- S3 bucket name (auto-detected by scripts)
- IAM role ARNs (managed by Terraform, transparent to code)

## Experiment Data Pipeline

Data flows: EC2 → S3 → Local machine

### On EC2 (after experiment):
- Manual: `bash scripts/experiment-upload.sh pilot5 ./data/pilot5`
  → Creates s3://bucket/experiments/pilot5-20260411-143022.tar.gz + manifest
- Auto: Use `scripts/experiment-run-and-upload.sh` wrapper in launch scripts
  → Uploads automatically when experiment finishes (success or failure)

### On local machine:
- List: `bash scripts/experiment-download.sh --list`
- Download latest: `bash scripts/experiment-download.sh --latest pilot5`
  → Downloads, extracts to data/pilot5/
- Download specific: `bash scripts/experiment-download.sh pilot5-20260411-143022`

### S3 layout:
```
s3://a11y-platform-data-XXXX/
  experiments/
    pilot4-full-20260407-120000.tar.gz
    pilot4-full-20260407-120000-manifest.txt
    pilot5-smoke-20260412-090000.tar.gz
    pilot5-20260412-180000.tar.gz
```

### Naming convention:
- Experiment name: descriptive, no timestamp (e.g., pilot5, pilot5-cua, smoke-newtask)
- Archive name: experiment-name + timestamp (auto-generated by upload script)
- Local directory: experiment name only (timestamp stripped on download)

## WebArena Task ID Mapping (CRITICAL)

Task IDs are interleaved across sites in webarena/test.raw.json — NOT contiguous ranges.
Each task_id maps to exactly one site. Using wrong IDs = silent misrouting.

```
shopping_admin (Magento backend :7780):  182 tasks, first: 0,1,2,3,4,5,6,11,12,13
shopping       (Magento storefront :7770): 192 tasks, first: 21,22,23,24,25,26,47,48
reddit         (Postmill :9999):         114 tasks, first: 27,28,29,30,31,66,67,68
gitlab         (:8023):                  196 tasks, first: 44,45,46,102,103,104,105
wikipedia      (Kiwix :8888):             16 tasks, first: 265,266,267,268,424,425
map            (:3000):                  128 tasks — NOT DEPLOYED, excluded
```

NEVER assume contiguous ranges (e.g. "reddit=100-199" is WRONG).
Always use explicit tasksPerApp in YAML config, or verify against test.raw.json.

## Deployment Rules (CRITICAL)

- ALWAYS run experiments via nohup or the launch-*.sh scripts on EC2.
  SSM sessions disconnect after ~20 min idle. Running `npx tsx` directly
  in foreground WILL be killed when the session drops. Use:
  `bash scripts/launch-pilot3b.sh` (nohup wrapper with PID tracking)
  or: `nohup npx tsx scripts/run-pilot3.ts --config X.yaml > log 2>&1 &`
- For auto S3 upload after experiment, use the wrapper:
  `bash scripts/experiment-run-and-upload.sh <name> <data-dir> <command>`
- Burner accounts auto-close after 7 days. Use `scripts/deploy-new-account.sh`
  for one-command deployment to new accounts.
- Burner accounts auto-close if EC2 has public access (0.0.0.0/0 inbound SG)
- ALWAYS use private subnet + SSM Session Manager (no SSH, no public IP)
- Use `terraform apply` from infra/ — it handles all security correctly
- NEVER manually create EC2 via AWS console
- Connect via: `aws ssm start-session --target <instance-id>`
- Fixed IPs (no config changes needed between accounts):
  - WebArena EC2: 10.0.1.50 (r6i.2xlarge, 8 vCPU, 64GB)
  - Platform EC2: 10.0.1.51 (r6i.4xlarge, 16 vCPU, 128GB)
- Instance IDs change per account — get from `terraform output`
- See docs/deployment.md and docs/new-account-migration-guide.md for full guide

## EC2 Reproducibility Rules (CRITICAL)

- NEVER make manual edits on EC2 that aren't tracked in the repo
- All config, scripts, and code changes MUST go through git (edit locally → push → pull on EC2)
- EC2 instances are ephemeral — redeployed weekly on new burner accounts
- The only exception is one-time env setup (BrowserGym timeout sed patch, pip installs)
  which MUST be documented in scripts/ec2-setup.sh so they can be re-applied
- Experiment data lifecycle: EC2 → S3 (experiment-upload.sh) → local (experiment-download.sh)
  Never store data only on EC2 — it will be destroyed when the account expires.
- `task-site-mapping.json` (repo root) is committed — do NOT regenerate on EC2 unless
  the webarena package version changes
- ALWAYS download experiment data to local workspace and read actual trace files
  before drawing conclusions. Never assume outcomes from summary statistics alone —
  trace-level analysis has repeatedly revealed unexpected mechanisms (variant escape,
  false positives, stochastic divergence points) that summary numbers hide.

## Architecture Rules

- TypeScript (ES2022, strict mode) for modules 1–5; Python for module 6
- Modules communicate via TypeScript interfaces and JSON files, no runtime RPC
- Experiment matrix scheduler (Module 3) orchestrates sequential execution
- Python Analysis Engine consumes CSV exports only
- Always read before you edit if the file exists
- Commit when a feature is completed
- TRACE IS KING: After any change to variant injection, observation extraction,
  bridge communication, or agent prompts, ALWAYS run a smoke test (config-reinject-smoke.yaml),
  download the trace data, and read the actual agent observations step-by-step before
  concluding the fix works. Summary statistics (success rates) are not sufficient —
  multiple times a "fix" appeared to work from summary numbers but trace analysis
  revealed the underlying mechanism was unchanged (e.g., goto escape, Magento re-rendering).
  Never assume a code change affects what the agent sees without reading the trace.

## Coding Standards

- All metric values must be 0.0–1.0 inclusive (use `isValidMetricValue`)
- Use `.js` extensions in all TypeScript imports (ESM)
- Prefer `Promise.allSettled()` for parallel operations that should not fail together
- Log errors and continue — never crash the pipeline on a single URL/tool failure
- Every module exports from its `index.ts` barrel file
- Tests use vitest; run with `npx vitest --run`
- Type check with `npx tsc --noEmit`

## Key Design Decisions

- Composite Score is supplementary — primary analysis uses criterion-level feature vectors
- Vision-only agent is a control condition (expected weak/null a11y gradient).
  Uses screenshot only, no a11y tree. Causal logic: if text-only drops but
  vision-only stays constant across variants → a11y tree is the causal factor.
  NOTE: Pilot 4 proved SoM overlays depend on DOM (phantom bids at low=0%).
- CUA agent is the TRUE pure-vision control (zero DOM dependency).
  Uses Anthropic Computer Use tool via direct Bedrock Converse API (bypasses LiteLLM).
  Bridge self-driven: cua_bridge.py runs agent loop internally, executor just waits.
  ObservationMode: 'text-only' | 'vision' | 'vision-only' | 'cua'
  CUA bridge read timeout: wallClockTimeoutMs + 30s (default 630s, vs 120s for others).
  Screenshot eviction: sliding window keeps last 5 turns to avoid 20MB Bedrock limit.
  CUA RESULTS: 109/120 (90.8%). Low 66.7% vs base 96.7%. Causal decomposition:
  text-only 63.3pp drop = ~33pp semantic + ~30pp cross-layer functional.
  reddit:29 inversion (CUA 0/5 vs text-only 4/5) = link→span functional breakage.
- PSL (Pure-Semantic-Low) variant: DOES NOT WORK with default BrowserGym serialization.
  aria-hidden="true" → BrowserGym shows `hidden=True` but elements remain clickable.
  role="presentation" → ignored on headings/landmarks in BrowserGym snapshot.
  Root cause: BrowserGym serialization is more permissive than real screen readers.
  Solution: SRF (Screen-Reader-Faithful) mode — filter hidden=True nodes in bridge.
- Low variant cross-layer confound: Patch 11 (link→span) deletes href functionality,
  not just semantics. CUA data proves 100% of low CUA failures are functional breakage.
  Fix: preserve <a href> but add aria-hidden="true" (semantic-only degradation).
- Variant levels: low (0.0–0.25), medium-low (0.25–0.50), base (0.40–0.70), high (0.75–1.0)
- Medium-Low variant models real-world pseudo-compliance (ARIA present, handlers missing)
- Low variant operators grounded in Ma11y [ISSTA 2024] WCAG failure techniques:
  8 direct matches (F2, F42, F44, F55, F65, F68, F77, F91, F96) + 4 novel extensions
- Semantic density metric: interactive_nodes / total_a11y_tree_tokens (novel contribution)
- A11y Tree stability: poll at 2s intervals, SHA-256 hash comparison, 30s timeout
- Config: only `webarena.apps` is required; all other fields have documented defaults
- Failure taxonomy: 12 types across 5 domains (accessibility, model, environmental, task, unclassified)
  — 5 types novel vs Aegis [2025] (F_KBT, F_PCT, F_SDI, F_AMB, F_UNK)

## Key Reference Files (repo root)

- `test.raw.json` — WebArena's 812 task definitions (from `webarena` Python package).
  Contains task_id, sites, start_url, intent, eval config, and ground truth for each task.
  Eval types: `string_match` (substring), `url_match`, `program_html` (DOM check),
  `llm_eval` (GPT-4 judge — requires OPENAI_API_KEY via LiteLLM proxy).
- `task-site-mapping.json` — Derived lookup: task_id → site name. Used by screen-tasks
  to filter tasks by app. Regenerate only if webarena package version changes.

## File Structure

```
src/scanner/     — Tier 1 (axe-core + Lighthouse) + Tier 2 (CDP metrics)
src/variants/    — DOM patch engine for 4 accessibility variant levels
src/runner/      — Agent executor, LLM backend, experiment matrix scheduler
  cua_bridge.py  — CUA agent loop (boto3 Bedrock, coordinate actions, screenshot eviction)
src/classifier/  — Auto-classifier (12 failure types) + manual review
src/recorder/    — HAR capture and replay for Track B
src/config/      — YAML/JSON config loader with validation and defaults
src/export/      — Manifest, CSV export, JSON store
analysis/        — Python: CLMM, GEE, Random Forest + SHAP, semantic density
docs/            — Engineering log, analysis reports, literature comparisons
scripts/         — Launch scripts, smoke tests, analysis tools, deployment automation
  deploy-new-account.sh — One-command deployment to new burner account
  experiment-upload.sh  — Package + upload experiment data to S3 (run on EC2)
  experiment-download.sh — Download + extract experiment data from S3 (run locally)
  experiment-run-and-upload.sh — Wrapper: run experiment then auto-upload
  smoke-cua-*.   — CUA API verification scripts (LiteLLM + Bedrock direct)
figures/         — Architecture diagrams (matplotlib-generated PNGs + source scripts)
```

## Key Documentation Files

- `docs/platform-engineering-log.md` — Full bug/fix/regression history
- `docs/new-account-migration-guide.md` — Complete guide for deploying to new AWS accounts
- `docs/ma11y-operator-mapping.md` — Ma11y operator audit + novel extensions
- `docs/aegis-taxonomy-comparison.md` — Failure taxonomy comparison with Aegis
- `docs/pilot2-trace-deep-dive.md` — Pilot 2 trace analysis
- `docs/screening-analysis.md` — Task screening results
- `figures/figure4_layer_model_spec.md` — Five-layer architecture text spec

## Spec Reference

Full requirements, design, and tasks at:
#[[file:.kiro/specs/ai-agent-accessibility-platform/requirements.md]]
#[[file:.kiro/specs/ai-agent-accessibility-platform/design.md]]
#[[file:.kiro/specs/ai-agent-accessibility-platform/tasks.md]]
