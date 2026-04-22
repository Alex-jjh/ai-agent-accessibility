# Visual-Equivalence Decision Memo (C++ path)

**Date**: 2026-04-22
**Author**: Alex Jiang
**Status**: Committed strategic direction for CHI 2027 submission
**Audience**: self, Brennan, future co-authors

---

## 0. Context in one paragraph

Phase B of the URL-replay experiment (2026-04-22) showed that **apply-low.js is
not visually equivalent to base**: mean SSIM 0.78 (std 0.14, min 0.55), with
**60/60 URLs** classified as Group B (visible change). Human visual inspection
confirmed this: patch 5 (shadow DOM wrap) strips CSS cascade → GitLab nav
buttons become browser-default huge; patch 6 (heading → div) forces inline
`font-size: 2em` that overrides site CSS; patch 11 (link → span) forces inline
`color: blue; text-decoration: underline; cursor: pointer` that makes every
link on every page turn blue and underlined. The production `apply-low.js` that
ran the full 13-task × 4-agent × 4-variant × 5-rep × N=1,040 Track A experiment
produces these visible changes.

This means the paper's §6 Limitations #7 claim — "CUA 35.4pp drop reflects
functional, not visual, degradation" — cannot rest on a naked "visual
equivalence" argument. Three strategic paths emerged (A = cherry-pick subset;
B = rewrite apply-low.js to visual-identical + re-run 1,040 cases; C = reframe
the contribution and use per-patch ablation + PSL). This memo commits to
**C++**, the hardened variant of C, and records the three load-bearing
corrections made over the initial proposal.

---

## 1. Why not A or B

**A — subset reporting.** Rejected. SSIM median is already 0.90, so any
"high-SSIM subset" is < 20% of URLs with no principled selection rule. A
reviewer will read it as cherry-picking and the decomposition story collapses.

**B — fix apply-low.js to visual-identical + re-run 1,040 cases.** Rejected on
**ecological-validity grounds, not technical ones**. Contrary to my earlier
intuition, patch 11 (a→span) *can* be made pixel-identical by copying
`getComputedStyle()` of the `<a>` as inline-style on the `<span>` before
swapping. But a real "inaccessible web" page does not do this — real div-soup
pages *do* look visibly different from their semantic equivalents, which is
precisely why they're also a11y-tree hostile. Over-engineering the operator
to force pixel equivalence produces an artificial failure mode that doesn't
exist in the wild. Cost of B (~30–40h agent runs + ~$1,500 LLM spend) buys a
*less* ecologically valid comparison, not a more valid one. Patch 5 (shadow
DOM) genuinely cannot be made visual-identical without defeating its purpose,
which reinforces the same conclusion.

**C (Kiro baseline)** — reframe around PSL (semantic-only) + apply-low
(semantic+visual) as **natural endpoints** of a deliberately mixed operator;
use per-patch SSIM distribution to show which patches are semantic-dominant
vs visual-dominant; admit visual change openly; keep all 1,040 cases valid.

## 2. Three load-bearing corrections to baseline C (→ C++)

These are the points where baseline-C would have broken under reviewer
pressure. Fixing them is the difference between C (70–75% accept) and C++
(80–85%).

### 2.1 Verify PSL actually reaches the agent observation — NOT assumed

**The risk.** My current narrative uses PSL (pure-semantic-low) as the
"zero-visual, full-semantic" control: if PSL → 0pp drop, then the 35–55pp
drops under full low can't be pure-semantic. But PSL's historical smoke
result (`5/6 success`) was previously interpreted as **"BrowserGym's a11y
tree serialization doesn't respect `aria-hidden="true"`"** — i.e., the
variant silently failed to modify agent observation. If that's still the
case, PSL is not a "semantic-only control", it's a **no-op control**, and
using it as a decomposition anchor collapses immediately.

**Exact reviewer question I must pre-empt:** *"How do you know the PSL null
result reflects agent robustness to pure semantic degradation, versus the
variant simply not being applied by BrowserGym's serialization?"*

**Verification protocol (must run before writing §5.3 decomposition):**
1. Launch BrowserGym agent on one base task, dump the serialized a11y tree
2. Launch same task with PSL variant, dump again
3. Diff the two dumps
4. **Gate condition:** At least one of (aria-hidden'd elements disappear;
   role=presentation propagates; landmark stripping shows up) must be
   visible in the diff
5. If the diff is empty → PSL is a no-op under BrowserGym → C++ loses one
   of its two anchors. Escalate to SRF (Screen-Reader-Faithful) serialization
   work before writing the paper

**Do not write §5.3 before this runs. Two hours of work guards the thesis.**

### 2.2 CUA 35pp = visual + functional, NOT "functional upper bound"

**Earlier wording (Kiro and I both got this wrong):** "CUA sees visual + tree
absence + functional, so 35pp = functional upper bound."

**Problem:** CUA is architecturally a pure-pixel agent. By design it ignores
the a11y tree. Therefore tree degradation is **not a driver** of CUA's
performance. CUA's 35pp drop under low is driven by:

- **(a)** visual degradation (low SSIM makes visual targets harder to find)
- **(b)** DOM functional degradation (click on correct pixel → no nav when
       `href` is gone or event delegation is broken)

So CUA 35pp = (a) + (b). Text-only's 55pp = (a) + (b) + (c) a11y-tree
degradation. The residual 20pp upper-bounds the **a11y-tree-specific** pathway.
PSL (if it verifies per §2.1) then independently bounds (c) from below at ~0pp.

**This is the correct three-way decomposition:**

```
  text-only (55pp) = visual + functional + a11y-tree
  CUA        (35pp) = visual + functional
  ────────────────────────────────────────────────
  residual   (20pp) = a11y-tree upper bound
  PSL        (~0pp) = a11y-tree lower bound (under BrowserGym
                      serialization, pending verification §2.1)
```

Use this table verbatim in the paper. Kiro's wording and my previous wording
both invert the load-bearing logic.

### 2.3 Phase C admin login failure needs root-cause diagnosis BEFORE re-running

My Phase C run had all `shopping_admin` URLs fall back to the Magento admin
login page (visual confirmation: every admin screenshot shows login form).
Before re-running the per-patch ablation, three root causes need to be
distinguished:

1. **Cookie-injection bug in ablation script only** — the ablation script
   does login-once before 15×14 captures but doesn't re-login. Phase B had
   `--relogin-every 50` which covered 15×14=210 captures in 4 cycles. Phase
   C script had no re-login at all. **Likely cause.** ~10 min to fix.
2. **Phase B also quietly lost admin sessions but without visible
   symptoms** (admin URL still rendered something, SSIM still computable).
   To check: grep Phase B `manifest.json` for `shopping_admin` records
   where `final_url` contains `/admin/admin/` (the login page) or
   `session_lost: true`. If > 0, Phase B admin data is partially
   contaminated and those pairs have to be excluded from the aggregate SSIM.
3. **SSM/burner token expiry during long runs** (1h TTL) — less likely
   since Phase B ran ~28 min total, but worth checking if 1 + 2 don't
   explain it.

**Required check before re-running Phase C:** Run a one-liner on the local
Phase B manifest that counts admin URL records whose `final_url` contains
`/admin/admin/` or `login` (but whose source URL didn't). If that count is
0, root cause is purely ablation script's missing re-login, fix in place
and re-run. If > 0, document which URLs were contaminated and treat that as
a known limitation for Phase B too.

---

## 3. The reframe that makes C++ stronger than C

**Root problem I was trapped in:** treating "visual equivalence" as the
validation *target*. Under environment-centric paradigm, that target is the
wrong one — it constructs a counterfactual that doesn't exist in the real
inaccessible web.

**New framing (planned for Brennan discussion):**

> "Our contribution is not to isolate a 'pure semantic' effect from a 'pure
> visual' effect — those are artificial decompositions that don't exist in
> real inaccessible websites. Real-world accessibility degradation patterns
> (WebAIM Million 2025: 94.8% of the web) are inherently mixed: a `<div>`
> standing in for a `<button>` breaks both the a11y tree and the CSS
> rendering simultaneously. Our contribution is to show that this mixed,
> real-world degradation produces measurable, large, replicated agent
> performance drops (13 tasks × 4 agent types × 2 models, N=1,040). The
> per-patch SSIM distribution reveals which patches are semantic-dominant
> versus visual-dominant; the aggregate 'Same Barrier' claim holds for the
> realistic mixed low variant."

This lines up with the Reverse-Curb-Cut narrative already in the proposal:
humans and agents see different projections of the same DOM, but they face
the **same** barrier when DOM semantics and visual cues degrade together,
which is how real inaccessible websites degrade.

---

## 4. Exact execution order (do not skip)

### Step 1 — Methodological sanity check (tonight, ~2.5h)
- [ ] PSL observation dump verification (§2.1) — 2h
  - launch BrowserGym once at base, once at PSL, diff serialized tree
  - commit dump artifacts to `results/visual-equivalence/psl-observation-diff/`
  - write pass/fail gate in commit message
- [ ] Phase B admin-session audit (§2.3 check) — 20min
  - one-liner: `python -c "import json; m=json.load(open('.../replay/manifest.json')); ..."`
  - count admin records whose `final_url` lands on `/admin/admin/`
  - document finding in the same admin audit commit

### Step 2 — Phase C fix + re-run (tomorrow, ~2–4h)
- [ ] Patch `replay-url-patch-ablation.py`: add per-URL cookie re-injection
  (or `--relogin-every` like main replay)
- [ ] Re-run Phase C (15 URLs × 14 patches = 210 captures ≈ 12 min)
- [ ] Re-run aggregate analysis
- [ ] Obtain per-patch SSIM distribution table

### Step 3 — Read the clustering (when Step 2 data lands)
- Expected natural clustering (to validate, not assume):
  - **Category I (SSIM ≈ 1.0):** patches 1 (landmark→div, if CSS survives),
    2 (aria strip), 7 (img alt delete), 8 (tabindex delete), 10 (lang delete),
    12 (duplicate IDs)
  - **Category II (SSIM < 0.95):** patches 3 (label removal), 5 (shadow DOM),
    6 (heading→div + font-size override), 9 (table→div losing table CSS),
    11 (link→span losing link CSS + forced blue/underline), 13 (focus blur;
    may or may not change visuals depending on focus rings)
- **Gate:** If the distribution is bimodal with a clear gap, C++ natural-
  clustering narrative is supported. If it's a continuum with no gap, retreat
  to a more conservative "per-patch spectrum" description. Commit to whichever
  the data gives us; don't force the story.

### Step 4 — Paper rewrite (2 weeks)
Per Kiro baseline, plus three hardening additions:

1. **§4 Methods — add "Variant Authenticity Verification"**
   Show PSL observation diff proves PSL actually alters agent observation
   (assuming §2.1 passes)
2. **§5.3 Decomposition — use the exact four-line table from §2.2** above
3. **§6 Limitations — add "Ecological Validity of Variant Design"**
   Explain why not over-engineering operator pixel-equivalence: doing so
   produces an artificial counterfactual not found on real inaccessible
   websites. Cite HTTP Archive div/span ≈ 40% and WebAIM 2025.

### Step 5 — Brennan discussion
Bring §3 reframe memo. Ask whether to promote it to §2.1 Contribution framing
(it may be a stronger opening than the current visual-equivalence hedge).

---

## 5. Scorecard (honest)

| Option | Methodological rigor | Time | Ecological validity | CHI accept |
|--------|---------------------|------|--------------------|-----------|
| A (cherry-pick subset)       | 2/10 | 1 day    | 3/10 | 10–20% |
| B (rewrite + re-run 1,040)   | 9/10 but over-engineered | 4–6 wks + $1.5k | 4/10 | 50–60% |
| C (baseline reframe)         | 7.5/10 | 2 wks  | 8/10 | 70–75% |
| **C++ (this memo)**          | **9/10** | **2.5 wks** | **9/10** | **80–85%** |

## 6. What stays, what changes

**Stays (valid under this reframe):**
- All 1,040 Track A cases, unchanged
- `apply-low.js` production code, unchanged
- Pilot 4 / CUA 120 / Llama 4 / SoM / expansion result tables
- PSL finding (pending §2.1 verification)
- Ecological-validity 34-site audit
- 77.8% CUA failure click-inert trace signature

**Changes:**
- §5.3 decomposition rewritten per §2.2
- §6 Limitations #7 reframed per §3
- §4 Methods adds Variant Authenticity Verification subsection
- Group A/B/C definitions replaced with per-patch Category I/II classification
  derived empirically from per-patch SSIM distribution

**Added (never existed):**
- Per-patch SSIM ± std table, 15 URLs × 13 patches (Phase C output)
- PSL observation-diff artifact as evidence of variant-applied status
- "Ecological Validity of Variant Design" subsection

---

## 7. One line I'm telling myself

> The 1,040 cases are not "smoker". They are valid data under a specific
> variant specification. The ask is to re-position the story, not the data.


---

## Addendum: Phase B admin contamination revealed (2026-04-22, +2h)

### What happened

Initial §2.3 admin audit (by `final_url` pattern matching) returned
"0 login-page redirects". That result was **wrong** because Magento
renders the admin login form **at the protected URL path** — the URL
doesn't change to `/admin/auth/login`, the page content changes while
the URL stays `/admin/sales/order/`. My audit missed this entirely.

Second audit (by `page.title()` content) shows:

| App             | captures | OK content | Login content | ? |
|-----------------|---------:|-----------:|--------------:|--:|
| ecommerce       | 9        | 9          | 0             | 0 |
| **ecommerce_admin** | **96**   | **0**      | **96**        | **0** |
| gitlab          | 48       | 48         | 0             | 0 |
| reddit          | 44       | 44         | 0             | 0 |
| **Total**       | 197      | 101        | 96            | 0 |

All 32 unique admin URLs × 3 variants = 96 captures rendered the
"Magento Admin" login form, never the real admin content.

### Root cause

The admin login logic in `replay-url-screenshots.py::login_and_capture_cookies`
wraps the Magento admin flow correctly (`.action-login` selector) — the
login smoke test (2026-04-22 morning) confirmed 1 auth cookie was
captured for admin. But between the login and the 96 captures, the
admin session either:
- Expired (Magento admin session TTL is short by default), **or**
- Was silently invalidated by Magento after the first request from a
  different Playwright context (each `capture_one()` opens a new context)

The `--relogin-every 50` logic **only kicks in on multiples of 50 URLs**,
so admin was logged in once at Phase B start and never refreshed before
it expired. Phase B spanned ~27 minutes, longer than Magento's default
admin session TTL (often 15 minutes).

The silent part is the bug: Phase B's `capture_one()` returns
`session_lost=True` only if `final_url` contains a login-path pattern.
Magento's behavior of "URL unchanged, content becomes login form" 
defeats this check. We need to either:
- Detect login content via title/DOM markers instead of URL
- Re-login per-app per-context (expensive)
- Keep a shared authenticated browser-level context for all admin
  captures (mutually exclusive with our "new context per capture" design)

### Impact on §5.3 decomposition

**Phase B effective sample size for SSIM: 31 base-vs-low pairs** (was
60 pre-audit). New distribution, admin excluded:

- Mean SSIM **0.679** (was 0.785 pre-exclusion)
- Median SSIM **0.629**
- Min **0.548**, Max **0.990**
- 29/31 pairs have SSIM < 0.95 → still clearly Group B
- Only 1 pair (reddit search, title "Search") has SSIM > 0.97

This **strengthens** the finding that apply-low produces large visual
change: removing the "artificially stable" admin login rendering makes
the real degradation magnitude clearer, not hides it.

### Next actions (updated)

Adding to Step 1 of the execution plan:

**Step 1.3 — Re-run Phase B admin with fixed login strategy (~20min)**

Required changes to `replay-url-screenshots.py`:
1. Detect session loss by page content signatures (`page.title()` against
   per-app login markers), not just by `final_url` pattern
2. Re-login admin every 10 URLs instead of 50 (Magento session TTL < 15min)
3. Alternative: use a single long-lived browser context for all admin
   captures so the session cookie persists

Re-capture Phase B admin only (32 URLs × 3 variants = 96 captures),
merge into existing manifest, re-run analysis. Other apps unaffected.

**Step 1.4 — Add authentication verification to Phase C + D as well**

The same bug almost certainly affects Phase C admin captures (confirmed
by your visual inspection) and Phase D click-probe. Fix ablation script
with same strategy before re-running.

### Lesson for decision memo §2.3

Change the root-cause list:
- ❌ Old: "Cookie-injection bug in ablation script only"
- ✅ New: "Magento admin session TTL < experiment duration, combined
   with URL-based-only session-loss detection. Same root cause affects
   Phase B and Phase C. Fix is content-based session detection +
   shorter re-login interval."
