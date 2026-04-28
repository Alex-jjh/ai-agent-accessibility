# AMT Operator Specification (v8.1)

> **Purpose**: Normative spec for the 24 independent accessibility manipulation
> operators that constitute the Accessibility Manipulation Taxonomy (AMT) for
> CHI 2027. Each operator has an identity, a single-responsibility
> implementation, and a behavioral contract that external tooling can rely on.
>
> **Supersedes**: the implicit taxonomy previously embedded in
> `apply-low.js + apply-medium-low.js + apply-high.js` (composite
> IIFEs). This document is the contract; operator source files are the
> implementation; `apply-all-individual.js` is the build artefact.
>
> **Companion**: `.kiro/steering/2026-04-27-chi2027-roadmap-v8.md` §2.1.

---

## 1. Operator identity

Each operator has a stable **operator ID** of the form `L{n}`, `ML{n}`, or
`H{n}`. Operator IDs are immutable and paper-citable. Adding a new operator
requires a new ID; modifying an operator requires a version bump (e.g.,
`L3-v2`) and a note in §6.

| Family | IDs        | Count | Purpose                       |
|--------|------------|-------|-------------------------------|
| Low    | L1–L13     | 13    | Aggressive degradation         |
| Midlow | ML1–ML3    | 3     | Pseudo-compliance edge cases   |
| High   | H1–H8      | 8     | Positive enhancement           |

**H5** is split into H5a/H5b/H5c in the roadmap; in this spec each sub-
operator is a **separate ID** for unambiguous targeting. Total: 24 operators.
The `H5a/b/c` legacy labels remain valid aliases (see §7 table).

---

## 2. Contract each operator must satisfy

An operator implementation is a **pure browser-side IIFE** (evaluated via
Playwright `page.evaluate`) that returns `Change[]`. It MUST satisfy:

### 2.1 Signature

```js
(() => {
  const changes = [];
  // ...mutate document, push Change records...
  return changes;
})();
```

No imports, no module resolution. Runs in the target page's JavaScript
context. Assumes DOM is ready (window.load has fired).

### 2.2 Change record shape

Every mutation MUST push one `Change` object onto the local `changes`
array:

```ts
type Change = {
  operatorId: string;          // e.g. "L3" — set by the build wrapper, not the body
  selector: string;            // element identifier (tag#id.class or [data-variant-revert="..."])
  changeType:                  // enum
    | 'replace'                // element replaced with different tag
    | 'remove-element'         // element removed from DOM
    | 'remove-attr'            // attribute removed
    | 'remove-handler'         // inline event handler removed (onkeydown, etc.)
    | 'add-attr'               // attribute added
    | 'add-element';           // element inserted
  original: string;            // pre-mutation snippet, truncated to 500 chars
  modified: string;            // post-mutation snippet, truncated to 500 chars
};
```

The **build wrapper** is responsible for injecting `operatorId` into each
Change. Operator bodies do not need to (and must not) set `operatorId`
themselves — this keeps bodies copy-pasted cleanly from the composite files.

### 2.3 Purity invariants

- **Pure**: no network calls, no reads/writes to `localStorage` /
  `sessionStorage` / cookies.
- **Deterministic on a fixed DOM**: two invocations on identical input
  DOMs must produce identical `changes` arrays (modulo `data-variant-
  revert` counter, see §3).
- **No global state**: each operator reads only `document`, may read
  `window.location` only if its semantic requires it (currently only H7).
- **Side-effect-bounded**: mutations restricted to `document.*`; no
  schedule of async callbacks (no `setTimeout`, no `MutationObserver`).

### 2.4 Idempotence

Running operator N twice in a row on the same DOM:

- MUST NOT throw.
- MUST either (a) produce an empty `changes` array on the second run, or
  (b) produce changes restricted to elements that were added *after* run
  1 (e.g., by JS framework re-render — irrelevant here since framework
  mutations happen asynchronously).

Concretely: if L3 removed all `<label>` on run 1, on run 2
`querySelectorAll('label')` returns nothing, so the loop body never
executes. This is tested in §4.3 of the test suite.

Idempotence matters because **Plan D** (the MutationObserver in
`browsergym_bridge.py`) can re-invoke the variant script if it detects
the DOM has been "cleaned" by a framework.

---

## 3. The `data-variant-revert` convention

Operators that replace an element (L1, L6, L9, L11, ML1) set a unique
attribute `data-variant-revert="__variant_{tag}_{counter}"` on the
replacement. The counter is local to the operator body and starts at 0.

Because each operator has its own counter, revertIds are NOT globally
unique across operators. That's fine because:

1. Revert is keyed on the selector in each Change record, which is the
   `[data-variant-revert="..."]` form; and
2. Composition invocation wraps each operator's body in its own lexical
   scope (`{ ... }` block in the built file), so counters don't collide
   at runtime.

The composite IIFE files (`apply-low.js` etc.) use a shared `changes.length`
for this counter. For the extracted operators, each body uses its own
local counter starting at 0 (the build wrapper renames them). This is
observable difference #1 between the legacy and new representations —
see §4 Parity Check for how we handle it.

---

## 4. Severity categories (from 2026-04-22 SSIM analysis)

Operators are tagged with a visual-impact category derived empirically
from the Phase B/C SSIM replay study:

- **CAT-I** (visual-invariant, SSIM ≈ 1.0): mutates only a11y-layer
  attributes (ARIA, role, tabindex, lang, duplicate IDs, img alt).
- **CAT-II** (visual-degrading, SSIM < 0.95): replaces elements whose
  default CSS `all: initial` contract is lost when the tag changes
  (heading → div, link → span, thead → div, label removal).

CAT is a property of the operator and goes in the spec table §7. It is
NOT enforced at runtime; it drives the paper's §5.3 decomposition.

This categorization is pending re-verification after A.1/A.3 admin fix
(tracked in `docs/analysis/visual-equivalence-decision-memo.md`
Step 2-3). A CAT is tentative until its per-patch SSIM 95% CI is
computed on the re-run data.

---

## 5. File layout

### 5.1 Human-readable source

```
src/variants/patches/operators/
  L1.js   L2.js   ...  L13.js
  ML1.js  ML2.js  ML3.js
  H1.js   H2.js   ...  H8.js
  README.md
```

Each file is a standalone IIFE (§2.1) implementing exactly one operator.
These files are what contributors edit.

### 5.2 Build artefact

```
src/variants/patches/inject/apply-all-individual.js
```

Single file produced by `scripts/build-operators.ts`. Runtime consumers
(BrowserGym bridge, CUA bridge, TS `applyVariant` path) read this file
via `page.evaluate` and toggle operators by setting `window.__OPERATOR_IDS`
before evaluation.

### 5.3 Build contract

```
npm run build:operators
```

Reads all files in `operators/`, validates each is a single IIFE,
concatenates bodies inside `if (should('{id}')) { ... }` wrappers with
`operatorId` injection, writes `apply-all-individual.js`. Build is
deterministic — a clean source tree produces a byte-identical artefact.

`build-operators.ts` MUST fail (non-zero exit) if:
- An operator file is malformed (not a single IIFE body).
- The operator ID isn't in the registered list.
- Two operators share a symbol in their body that would collide once
  scoped (caught by the `{ ... }` block wrapper — we verify no symbols
  leak via a static-analysis assertion).

### 5.4 Audit artefacts (Task A.5)

The DOM-signature audit tool `scripts/audit-operator.ts` consumes the
build artefact and produces a per-run output directory under
`data/amt-audit-runs/<run-id>/` containing:

- `audit.json` — per-operator 12-dim signatures (D1-D3, A1-A3, V1-V3,
  F1-F3) plus `runId`, `fixture` metadata, and for each operator a
  `screenshots: { before, after }` block with **paths relative to the
  run-dir**.
- `run.log` — stderr stream mirroring what the operator sees on
  console during the run. Captures login diagnostics, per-operator
  timing, and any warnings.
- `screenshots/<opId>_{before,after}.png` — the actual 1280×720
  PNGs used to compute V1 (SSIM), V2 (bbox), V3 (contrast).

S3 upload / local download pipeline: see `docs/amt-audit-artifacts.md`
for the full spec. Key points:

- S3 prefix is `s3://<bucket>/audits/` (parallel to but separate from
  `experiments/`, so audit and experiment listings don't cross-contaminate)
- `bash scripts/audit-upload.sh <run-id>` (on EC2)
- `bash scripts/audit-download.sh <run-id>` (on local)

The older single-file mode (`--output file.json`) still works for the
pre-existing smoke callers but emits a warning and does NOT persist
screenshots or run.log. New code should use the run-dir default.

---

## 6. Versioning & deprecation

- Operator **behaviour changes** (e.g., L3 now also removes
  `<legend>`) require a version bump `L3 → L3-v2` and MUST NOT reuse
  the old ID. Paper tables cite the exact version.
- Operator **removal** retires the ID permanently; never reused.
- Changes to this spec are version-bumped in the file header.

This policy exists so that cross-experiment data merges (e.g., comparing
Pilot 4 L3 with Mode A L3) are unambiguous.

---

## 7. Operator catalog

### 7.1 Low family (L1–L13) — aggressive degradation

| ID  | Name                                  | Source block in `apply-low.js` | WCAG          | CAT (tentative) |
|-----|---------------------------------------|--------------------------------|---------------|-----------------|
| L1  | landmark → div                        | block 1                        | SC 1.3.1      | CAT-II          |
| L2  | strip all aria-\* + role              | block 2                        | SC 2.5.3      | CAT-I           |
| L3  | remove all `<label>`                  | block 3                        | F68 / SC 4.1.2| CAT-II          |
| L4  | remove onkeydown/up/press             | block 4                        | SC 2.1.1      | CAT-I           |
| L5  | wrap interactives in closed Shadow DOM| block 5                        | —             | CAT-II          |
| L6  | `h1–h6` → div (font-size preserved)   | block 6                        | F2 / SC 1.3.1 | CAT-II          |
| L7  | strip img alt + aria-label + title    | block 7                        | F65 / SC 1.1.1| CAT-I           |
| L8  | remove tabindex                       | block 8                        | F44 / SC 2.4.3| CAT-I           |
| L9  | thead/tbody/tfoot/th → div/td         | block 9                        | F91 / SC 1.3.1| CAT-II          |
| L10 | remove `<html lang>`                  | block 10                       | SC 3.1.1      | CAT-I           |
| L11 | `<a href>` → `<span onclick>`         | block 11                       | F42 / SC 1.3.1| CAT-II          |
| L12 | duplicate IDs on adjacent elements    | block 12                       | F77 / SC 4.1.1| CAT-I           |
| L13 | `onfocus="this.blur()"` trap          | block 13                       | F55 / SC 2.1.1| CAT-I           |

**L12 idempotence note**: The extracted L12 adds a hidden
`<meta data-variant-L12-sentinel>` child to `<body>` on first run and
no-ops on subsequent runs. The legacy `apply-low.js` block 12 has no
such guard. This difference is behavioural-equivalent on a single-shot
invocation (both produce the same 2–5 ID duplications on a fresh DOM),
but under Plan D re-injection the extracted L12 is stable while legacy
L12 would keep dup-ifying additional pairs on every re-entry. Parity
test (§9.2) validates the first-run behaviour is identical; the
additional `<meta>` sentinel element is ignored by Playwright
viewport-relevant tools (it's `hidden`) and by the a11y tree.

### 7.2 Midlow family (ML1–ML3) — pseudo-compliance

| ID  | Name                                              | Source block in `apply-medium-low.js` | WCAG    |
|-----|---------------------------------------------------|---------------------------------------|---------|
| ML1 | `<button>` with empty text → `<div>`              | block 1                               | SC 4.1.2|
| ML2 | `role="button"`: strip keydown/up + cloneReplace  | block 2                               | SC 2.1.1|
| ML3 | `<input>` w/o placeholder: strip label + aria-*   | block 3                               | F68     |

### 7.3 High family (H1–H8) — positive enhancement

| ID  | Name                                        | Source block in `apply-high.js` | WCAG     |
|-----|---------------------------------------------|----------------------------------|----------|
| H1  | aria-label for interactives missing names   | block 1                          | SC 4.1.2 |
| H2  | insert skip-nav link at body end            | block 2                          | SC 2.4.1 |
| H3  | associate labels with form controls         | block 3                          | SC 4.1.2 |
| H4  | add landmark roles (header/nav/main/…)      | block 4                          | SC 1.3.1 |
| H5a | auto-generate alt from img filename         | block 5a                         | SC 1.1.1 |
| H5b | add lang="en" to html                       | block 5b                         | SC 3.1.1 |
| H5c | auto-label empty `<a>` from href            | block 5c                         | SC 2.4.4 |
| H6  | aria-required="true" for required inputs    | block 6                          | SC 3.3.2 |
| H7  | aria-current="page" for active nav link     | block 7                          | SC 2.4.8 |
| H8  | scope="col"/scope="row" on table headers    | block 8                          | SC 1.3.1 |

**Legacy aliases** (for cross-referencing older drafts): H5 in the v8
roadmap narrative decomposes into H5a/H5b/H5c here.

---

## 8. Invocation modes

### 8.1 Single operator (Mode A)

```python
page.evaluate('window.__OPERATOR_IDS = ["L3"]; window.__OPERATOR_STRICT = true')
changes = page.evaluate(apply_all_individual_js)
```

`__OPERATOR_STRICT = true` makes the wrapper `throw` if a requested
operator ID doesn't exist (guards against typos in configs).

### 8.2 Composite (Low / ML / High reproduced)

```python
# Reproduce legacy Low
page.evaluate('window.__OPERATOR_IDS = ["L1","L2","L3","L4","L5","L6","L7","L8","L9","L10","L11","L12","L13"]')

# Reproduce legacy Medium-Low
page.evaluate('window.__OPERATOR_IDS = ["ML1","ML2","ML3"]')

# Reproduce legacy High
page.evaluate('window.__OPERATOR_IDS = ["H1","H2","H3","H4","H5a","H5b","H5c","H6","H7","H8"]')
```

Applied inside `apply-all-individual.js` in the source order (H first,
then ML, then L — see §8.4). The **composite equivalence test** (§9.2)
validates that these invocations produce DOMs equivalent to the legacy
`apply-low.js` / `apply-medium-low.js` / `apply-high.js` outputs.

### 8.3 Composition (pairwise, triples)

```python
page.evaluate('window.__OPERATOR_IDS = ["L3", "H2"]')
```

Applied in source order (§8.4), which for `["L3", "H2"]` is
`H2 → L3`. Composition study §2.7.3 of the roadmap operates on top-5
pairwise combinations.

### 8.4 Canonical application order

Operators in a composition are applied in a **fixed source order**,
independent of the order in `__OPERATOR_IDS`:

```
H1, H2, H3, H4, H5a, H5b, H5c, H6, H7, H8,
ML1, ML2, ML3,
L1, L2, L3, L4, L5, L6, L7, L8, L9, L10, L11, L12, L13
```

**Rationale for "H → ML → L"**: High operators add markup (aria-label,
skip-links, landmark roles). Low operators often strip or replace the
carriers of that markup (L1 replaces `<nav>`, L2 strips `aria-*`). If
L ran first, H would have no carriers to enhance — yielding different
outcomes that don't reflect the real-world scenario of "a site that is
already enhanced being additionally degraded" (the more common
accessibility regression pattern).

Composition studies report results under this canonical order.
Non-commutativity is documented empirically in the test suite (§9.4)
and paper Appendix B.

---

## 9. Test battery (severity = this is load-bearing)

### 9.1 Operator contract tests

For every operator:

- `operator.js` exists, is syntactically valid JS (parses without
  error), is a single `(() => { ... })()` IIFE.
- Invocation on a fixture DOM returns an array (possibly empty).
- Every returned Change has all required fields (§2.2).

### 9.2 Composite parity test (LOAD-BEARING)

For each family:

- Run the legacy composite file (`apply-low.js`, etc.) on a fixture
  DOM → record final DOM + Change count per block.
- Run the new individual file with `__OPERATOR_IDS` = full family → 
  record final DOM + Change count.
- **Assert**: Change counts per block are equal, final DOM serialization
  byte-identical modulo `data-variant-revert` counter renaming.

Failure means we silently changed semantics — stops the build.

This is the single most important test in A.4. It gates merging.

### 9.3 Idempotence test

For every operator: run it twice on the same fixture DOM. Assert that
either (a) the second run returns `changes.length === 0`, or (b) the
final DOM after two runs is identical to the final DOM after one run.

### 9.4 Non-commutativity detection (documentation, not assertion)

For all 24 × 23 = 552 ordered pairs:

- Apply `op_A → op_B` and `op_B → op_A` on fresh fixture DOMs.
- Hash final DOM of each.
- Record pairs where hashes differ.

Output: `results/amt/operator-non-commutativity-matrix.json` — consumed
by the composition study. Non-commutativity is **expected for some
pairs** (e.g., H4 vs L1 both touch `<nav>`). Writing it down makes the
composition study's design explicit.

### 9.5 Fixture DOMs

We need non-trivial DOMs that exercise each operator. Candidates:

- A frozen WebArena Magento storefront product page (for L3, L9, L11,
  ML3, H3, H6)
- A frozen GitLab explore page (for L1, L6, H2, H4)
- A frozen synthetic HTML covering all element types (fallback)

Fixtures committed in `tests/fixtures/amt-dom/`.

---

## 10. Backward compatibility

- `apply-low.js`, `apply-medium-low.js`, `apply-high.js`,
  `apply-pure-semantic-low.js`, `apply-low-individual.js` are **not
  touched**. Existing Track A experiments and visual-equivalence replay
  keep using them.
- The Python BrowserGym bridge's `VARIANT_SCRIPTS` dict still maps the
  four composite variants; `apply-all-individual.js` is a sixth,
  operator-addressable mode ("individual").
- The existing TS `applyVariant()` function in
  `src/variants/patches/index.ts` gains a new case `'individual'` that
  accepts an operator-ID list.
- Data collected before 2026-04-28 is tagged `batch="composite-v1"`;
  data collected with the new mode is tagged `batch="individual-v1"`.
  The parity test (§9.2) validates the two batches can be merged.

---

## 11. Open questions

- **CAT categorization is tentative** pending A.1/A.3 replay rerun.
  Paper must not cite CAT labels before Step 2-3 of the
  visual-equivalence plan completes.
- **H5a's alt-from-filename heuristic** is a writing choice, not an
  accessibility fix — real-world enhancement would use ML vision. For
  paper honesty, H5a is labeled "surrogate enhancement" in §3 of the
  paper.

---

*End of spec. Version 8.1, 2026-04-28.*
