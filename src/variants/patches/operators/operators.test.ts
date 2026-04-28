/**
 * operators.test.ts — AMT operator contract & parity tests.
 *
 * Validates:
 *   §9.1  Operator contract   — every source file parses, is an IIFE,
 *                               returns Change[] on a simple DOM.
 *   §9.2  Composite parity    — composite IIFE (apply-low.js etc.)
 *                               produces the same Change *counts* as
 *                               invoking the new apply-all-individual.js
 *                               with the full family.
 *   §9.3  Idempotence         — running each operator twice on the
 *                               same DOM produces either empty changes
 *                               on the second run, or an identical
 *                               final DOM.
 *   §9.4  Non-commutativity   — documentation scan. Does not assert;
 *                               records pairs where order matters.
 *
 * Reference: docs/amt-operator-spec.md §9.
 *
 * Execution model: vitest runs the operator IIFEs inside a JSDOM
 * environment. JSDOM lacks Shadow DOM `attachShadow` on some host
 * elements — tests gracefully degrade for those operators.
 *
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeAll } from 'vitest';
import { readFileSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(__dirname, '../../../..');
const OPERATORS_DIR = join(REPO_ROOT, 'src/variants/patches/operators');
const INJECT_DIR = join(REPO_ROOT, 'src/variants/patches/inject');

// Canonical operator order (mirrors build-operators.ts).
const OPERATOR_ORDER: readonly string[] = [
  'H1', 'H2', 'H3', 'H4', 'H5a', 'H5b', 'H5c', 'H6', 'H7', 'H8',
  'ML1', 'ML2', 'ML3',
  'L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7', 'L8', 'L9',
  'L10', 'L11', 'L12', 'L13',
] as const;

const FAMILY = {
  L:  ['L1','L2','L3','L4','L5','L6','L7','L8','L9','L10','L11','L12','L13'],
  ML: ['ML1','ML2','ML3'],
  H:  ['H1','H2','H3','H4','H5a','H5b','H5c','H6','H7','H8'],
} as const;

type ChangeRecord = {
  operatorId?: string;
  selector: string;
  changeType: string;
  original: string;
  modified: string;
};

/**
 * Run a JS IIFE source string in the current JSDOM window context and
 * return its value. Uses Function constructor to get a non-module scope
 * where `window`, `document`, etc. are visible.
 */
function runInWindow(jsSource: string): unknown {
  // The IIFE source already ends with `})();` so it returns a value.
  // We capture that value by binding it to a local before the closing
  // semicolon, then returning it.
  const trimmed = jsSource.trimEnd().replace(/;?\s*$/, '');
  return new Function(`const __result = (${trimmed}); return __result;`)();
}

/**
 * Run the apply-all-individual.js artefact with a given list of
 * operator IDs. We CANNOT inject the prelude inside the `(expr)` we
 * pass to runInWindow — a `;` inside the expression breaks the grammar.
 * Instead, we mutate the global first, then evaluate the IIFE.
 */
function runAllIndividual(ids: readonly string[], strict = false): ChangeRecord[] {
  (globalThis as any).window.__OPERATOR_IDS = [...ids];
  (globalThis as any).window.__OPERATOR_STRICT = strict;
  const js = readFileSync(join(INJECT_DIR, 'apply-all-individual.js'), 'utf-8');
  try {
    return runInWindow(js) as ChangeRecord[];
  } finally {
    delete (globalThis as any).window.__OPERATOR_IDS;
    delete (globalThis as any).window.__OPERATOR_STRICT;
  }
}

/**
 * Reset the document.body + <html lang> to a rich fixture DOM that
 * exercises most operators at least once. Called before every test.
 */
function resetFixtureDom(): void {
  document.documentElement.setAttribute('lang', 'en');
  document.body.innerHTML = `
    <nav id="main-nav" aria-label="Main">
      <a href="/">Home</a>
      <a href="/about" aria-current="page">About</a>
      <a href="/empty"></a>
    </nav>
    <header><h1>Welcome</h1></header>
    <main id="content">
      <h2>Section</h2>
      <h3>Subsection</h3>
      <article>
        <p>Hello world</p>
        <img src="/img/logo.png" alt="Company logo" title="Logo">
        <img src="/img/unlabeled.png">
      </article>
      <form>
        <label for="q">Search</label>
        <input id="q" name="q" type="text" required>
        <input id="u" name="u" type="text">
        <select id="s" required><option>a</option></select>
        <button type="submit">Go</button>
        <button></button>
        <div role="button" tabindex="0" onkeydown="doStuff()">Custom btn</div>
      </form>
      <table>
        <thead><tr><th>Col1</th><th>Col2</th></tr></thead>
        <tbody><tr><th>Row1</th><td>v</td></tr></tbody>
      </table>
      <aside>Related</aside>
    </main>
    <footer>&copy; 2026</footer>
  `;
}

// ─────────────────────────────────────────────────────────────────────
// §9.1  Contract tests
// ─────────────────────────────────────────────────────────────────────

describe('AMT operator contract (§9.1)', () => {
  it('exactly 26 operator source files exist', () => {
    const files = readdirSync(OPERATORS_DIR).filter(f => f.endsWith('.js'));
    expect(files.length).toBe(OPERATOR_ORDER.length);
    const ids = files.map(f => f.replace(/\.js$/, '')).sort();
    expect(new Set(ids)).toEqual(new Set(OPERATOR_ORDER));
  });

  for (const opId of OPERATOR_ORDER) {
    it(`${opId}: file is a valid IIFE returning Change[]`, () => {
      resetFixtureDom();
      const source = readFileSync(join(OPERATORS_DIR, `${opId}.js`), 'utf-8');
      const out = runInWindow(source) as ChangeRecord[];

      expect(Array.isArray(out)).toBe(true);
      for (const ch of out) {
        expect(ch).toHaveProperty('selector');
        expect(ch).toHaveProperty('changeType');
        expect(ch).toHaveProperty('original');
        expect(ch).toHaveProperty('modified');
        expect(typeof ch.selector).toBe('string');
        expect([
          'replace', 'remove-element', 'remove-attr', 'remove-handler',
          'add-attr', 'add-element',
        ]).toContain(ch.changeType);
      }
    });
  }
});

// ─────────────────────────────────────────────────────────────────────
// §9.2  Composite parity — LOAD-BEARING
// ─────────────────────────────────────────────────────────────────────
//
// Invariant: invoking the new apply-all-individual.js with the full
// family (e.g., __OPERATOR_IDS = L1..L13) must produce the SAME NUMBER
// of Change records as the legacy apply-low.js on the same starting DOM.
// Types per change must also match (replace, remove-attr, …).
//
// We do NOT compare raw DOM byte-for-byte because the revert counters
// in revertIds differ between the legacy composite (shared counter) and
// individual operators (per-operator counter) — see spec §3. Counts +
// types is the strongest check that's robust to that cosmetic difference.

function runComposite(compositeFile: string): ChangeRecord[] {
  const js = readFileSync(join(INJECT_DIR, compositeFile), 'utf-8');
  return runInWindow(js) as ChangeRecord[];
}

function runIndividual(ids: readonly string[]): ChangeRecord[] {
  return runAllIndividual(ids);
}

function countByType(changes: ChangeRecord[]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const ch of changes) out[ch.changeType] = (out[ch.changeType] ?? 0) + 1;
  return out;
}

describe('AMT composite parity (§9.2) — LOAD-BEARING', () => {
  it('Low family parity: apply-low.js ≡ apply-all-individual.js with L1..L13', () => {
    resetFixtureDom();
    const legacy = runComposite('apply-low.js');
    resetFixtureDom();
    const individual = runIndividual(FAMILY.L);

    expect(individual.length).toBe(legacy.length);
    expect(countByType(individual)).toEqual(countByType(legacy));

    // Every individual-mode change must have operatorId set (build wrapper).
    for (const ch of individual) {
      expect(ch.operatorId).toBeDefined();
      expect(FAMILY.L).toContain(ch.operatorId);
    }
  });

  it('Midlow family parity: apply-medium-low.js ≡ __OPERATOR_IDS = ML1..ML3', () => {
    resetFixtureDom();
    const legacy = runComposite('apply-medium-low.js');
    resetFixtureDom();
    const individual = runIndividual(FAMILY.ML);

    expect(individual.length).toBe(legacy.length);
    expect(countByType(individual)).toEqual(countByType(legacy));

    for (const ch of individual) {
      expect(FAMILY.ML).toContain(ch.operatorId);
    }
  });

  it('High family parity: apply-high.js ≡ __OPERATOR_IDS = H1..H8 (H5a/b/c)', () => {
    resetFixtureDom();
    const legacy = runComposite('apply-high.js');
    resetFixtureDom();
    const individual = runIndividual(FAMILY.H);

    expect(individual.length).toBe(legacy.length);
    expect(countByType(individual)).toEqual(countByType(legacy));

    for (const ch of individual) {
      expect(FAMILY.H).toContain(ch.operatorId);
    }
  });
});

// ─────────────────────────────────────────────────────────────────────
// §9.3  Idempotence
// ─────────────────────────────────────────────────────────────────────

describe('AMT idempotence (§9.3)', () => {
  for (const opId of OPERATOR_ORDER) {
    it(`${opId}: two runs leave DOM in the same final state`, () => {
      resetFixtureDom();
      const source = readFileSync(join(OPERATORS_DIR, `${opId}.js`), 'utf-8');
      runInWindow(source);
      const afterRun1 = document.body.outerHTML;
      const secondChanges = runInWindow(source) as ChangeRecord[];
      const afterRun2 = document.body.outerHTML;

      // Either the second run returned no changes, or the DOM after
      // the second run is identical to after the first run (§2.4).
      const stable = secondChanges.length === 0 || afterRun1 === afterRun2;
      expect(stable, `${opId} not idempotent: 2nd run produced ${secondChanges.length} changes AND changed DOM`).toBe(true);
    });
  }
});

// ─────────────────────────────────────────────────────────────────────
// §9.4  Non-commutativity scan (diagnostic, not asserting)
// ─────────────────────────────────────────────────────────────────────
//
// We test a small sample of pairs rather than all 26×25=650, just to
// confirm the scan infrastructure works. The full sweep runs via
// `scripts/scan-operator-pairs.ts` separately (writes to
// results/amt/operator-non-commutativity-matrix.json).

describe('AMT non-commutativity scan (§9.4, sample)', () => {
  it('records at least one commuting pair and at least one non-commuting pair', () => {
    const pairs: Array<[string, string]> = [
      ['L2', 'L10'],  // aria strip vs lang strip — expected commuting (independent targets)
      ['H5c', 'L11'], // H5c adds aria-label to empty <a>; L11 then replaces <a> with <span>.
                     // Reversed: L11 first → no <a> remain → H5c finds nothing → different final DOM.
    ];

    const results: Array<{ pair: [string, string]; abEqualsBa: boolean }> = [];

    for (const [a, b] of pairs) {
      resetFixtureDom();
      const srcA = readFileSync(join(OPERATORS_DIR, `${a}.js`), 'utf-8');
      const srcB = readFileSync(join(OPERATORS_DIR, `${b}.js`), 'utf-8');
      runInWindow(srcA);
      runInWindow(srcB);
      const domAB = document.body.outerHTML;

      resetFixtureDom();
      runInWindow(srcB);
      runInWindow(srcA);
      const domBA = document.body.outerHTML;

      results.push({ pair: [a, b], abEqualsBa: domAB === domBA });
    }

    // Commuting pair: L2 ↔ L10 (both are attribute-only, disjoint target sets)
    expect(results[0].abEqualsBa).toBe(true);
    // Non-commuting pair: H5c ↔ L11 (H5c needs <a> elements; L11 deletes them).
    expect(results[1].abEqualsBa).toBe(false);
  });
});
