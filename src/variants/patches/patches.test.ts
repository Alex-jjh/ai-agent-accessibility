// Unit tests for DOM Patch Engine (applyVariant) and Reversal Engine (revertVariant)
// Requirements: 5.1–5.7, 6.1–6.3

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { applyVariant } from './index.js';
import { revertVariant } from './revert.js';
import type { VariantLevel, DomChange, VariantDiff } from '../types.js';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Create a mock Playwright Page whose `evaluate` method returns
 * predetermined values in sequence. The first and last evaluate calls
 * in applyVariant are always computeDomHash; the middle call is the
 * variant-specific DOM manipulation that returns DomChange[].
 *
 * For the base variant, only two evaluate calls happen (both hashes)
 * because the variant function is skipped (no-op).
 */
function createMockPage(options: {
  hashBefore: string;
  hashAfter: string;
  changes?: DomChange[];
}) {
  const { hashBefore, hashAfter, changes = [] } = options;
  let callIndex = 0;

  // For non-base variants: call 0 = hashBefore, call 1 = changes, call 2 = hashAfter
  // For base variant: call 0 = hashBefore, call 1 = hashAfter (no changes call)
  const evaluateFn = vi.fn(async () => {
    const idx = callIndex++;
    if (idx === 0) return hashBefore;
    if (changes.length > 0 && idx === 1) return changes;
    return hashAfter;
  });

  return { evaluate: evaluateFn } as any;
}

/**
 * Create a mock page for revertVariant testing.
 * revertVariant calls page.evaluate once per change (with a script string),
 * then once more for computeDomHash at the end.
 */
function createRevertMockPage(options: {
  hashAfterRevert: string;
  changeCount: number;
}) {
  const { hashAfterRevert, changeCount } = options;
  let callIndex = 0;

  const evaluateFn = vi.fn(async () => {
    const idx = callIndex++;
    // First N calls are revert scripts (return undefined)
    if (idx < changeCount) return undefined;
    // Last call is computeDomHash
    return hashAfterRevert;
  });

  return { evaluate: evaluateFn } as any;
}

/** Sample DomChange entries for Low variant */
function makeLowChanges(): DomChange[] {
  return [
    {
      selector: 'nav',
      changeType: 'replace',
      original: '<nav><a href="/">Home</a></nav>',
      modified: '<div><a href="/">Home</a></div>',
    },
    {
      selector: 'main',
      changeType: 'replace',
      original: '<main>Content</main>',
      modified: '<div>Content</div>',
    },
    {
      selector: 'div',
      changeType: 'remove-attr',
      original: 'role="navigation"',
      modified: '',
    },
    {
      selector: 'button',
      changeType: 'remove-attr',
      original: 'aria-label="Submit"',
      modified: '',
    },
    {
      selector: 'label[for="email"]',
      changeType: 'remove-element',
      original: '<label for="email">Email</label>',
      modified: '',
    },
  ];
}

/** Sample DomChange entries for Medium-Low variant */
function makeMediumLowChanges(): DomChange[] {
  return [
    {
      selector: 'div[role="button"]',
      changeType: 'remove-handler',
      original: 'onkeydown="handleKey()"',
      modified: '',
    },
    {
      selector: 'div[role="button"]',
      changeType: 'remove-handler',
      original: 'keydown/keyup listeners on <div role="button">Click me</div>',
      modified: 'listeners removed via clone',
    },
    {
      selector: 'label[for="username"]',
      changeType: 'remove-element',
      original: '<label for="username">Username</label>',
      modified: '',
    },
  ];
}

/** Sample DomChange entries for High variant */
function makeHighChanges(): DomChange[] {
  return [
    {
      selector: 'button',
      changeType: 'add-attr',
      original: '',
      modified: 'aria-label="button element"',
    },
    {
      selector: 'body > a.skip-link',
      changeType: 'add-element',
      original: '',
      modified: '<a href="#main-content" class="skip-link">Skip to main content</a>',
    },
    {
      selector: 'header',
      changeType: 'add-attr',
      original: '',
      modified: 'role="banner"',
    },
    {
      selector: 'nav',
      changeType: 'add-attr',
      original: '',
      modified: 'role="navigation"',
    },
    {
      selector: 'main',
      changeType: 'add-attr',
      original: '',
      modified: 'role="main"',
    },
  ];
}

const HASH_BEFORE = 'aabbccdd00112233aabbccdd00112233aabbccdd00112233aabbccdd00112233';
const HASH_AFTER_LOW = '11223344556677881122334455667788112233445566778811223344556677aa';
const HASH_AFTER_HIGH = 'ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00';

// ---------------------------------------------------------------------------
// Tests: applyVariant
// ---------------------------------------------------------------------------

describe('applyVariant', () => {
  // --- Req 5.1: Low variant removes semantic elements and ARIA attributes ---
  describe('Low variant (Req 5.1)', () => {
    it('returns a VariantDiff with changes that remove semantic elements and ARIA', async () => {
      const lowChanges = makeLowChanges();
      const page = createMockPage({
        hashBefore: HASH_BEFORE,
        hashAfter: HASH_AFTER_LOW,
        changes: lowChanges,
      });

      const diff = await applyVariant(page, 'low', 'reddit');

      expect(diff.variantLevel).toBe('low');
      expect(diff.appName).toBe('reddit');
      expect(diff.domHashBefore).toBe(HASH_BEFORE);
      expect(diff.domHashAfter).toBe(HASH_AFTER_LOW);
      expect(diff.changes).toEqual(lowChanges);
    });

    it('records replace changes for semantic elements', async () => {
      const lowChanges = makeLowChanges();
      const page = createMockPage({
        hashBefore: HASH_BEFORE,
        hashAfter: HASH_AFTER_LOW,
        changes: lowChanges,
      });

      const diff = await applyVariant(page, 'low', 'reddit');

      const replaceChanges = diff.changes.filter(c => c.changeType === 'replace');
      expect(replaceChanges.length).toBeGreaterThan(0);
      // Semantic elements should be replaced
      expect(replaceChanges.some(c => c.selector === 'nav')).toBe(true);
      expect(replaceChanges.some(c => c.selector === 'main')).toBe(true);
    });

    it('records remove-attr changes for ARIA attributes', async () => {
      const lowChanges = makeLowChanges();
      const page = createMockPage({
        hashBefore: HASH_BEFORE,
        hashAfter: HASH_AFTER_LOW,
        changes: lowChanges,
      });

      const diff = await applyVariant(page, 'low', 'reddit');

      const removeAttrChanges = diff.changes.filter(c => c.changeType === 'remove-attr');
      expect(removeAttrChanges.length).toBeGreaterThan(0);
      expect(removeAttrChanges.some(c => c.original.includes('role='))).toBe(true);
      expect(removeAttrChanges.some(c => c.original.includes('aria-label='))).toBe(true);
    });

    it('records remove-element changes for labels', async () => {
      const lowChanges = makeLowChanges();
      const page = createMockPage({
        hashBefore: HASH_BEFORE,
        hashAfter: HASH_AFTER_LOW,
        changes: lowChanges,
      });

      const diff = await applyVariant(page, 'low', 'reddit');

      const removeElChanges = diff.changes.filter(c => c.changeType === 'remove-element');
      expect(removeElChanges.length).toBeGreaterThan(0);
      expect(removeElChanges.some(c => c.selector.startsWith('label'))).toBe(true);
    });

    it('produces different DOM hash after manipulation', async () => {
      const page = createMockPage({
        hashBefore: HASH_BEFORE,
        hashAfter: HASH_AFTER_LOW,
        changes: makeLowChanges(),
      });

      const diff = await applyVariant(page, 'low', 'reddit');

      expect(diff.domHashBefore).not.toBe(diff.domHashAfter);
    });
  });

  // --- Req 5.2: Medium-Low variant creates pseudo-compliance ---
  describe('Medium-Low variant (Req 5.2)', () => {
    it('returns a VariantDiff with pseudo-compliance changes', async () => {
      const mlChanges = makeMediumLowChanges();
      const page = createMockPage({
        hashBefore: HASH_BEFORE,
        hashAfter: HASH_AFTER_LOW,
        changes: mlChanges,
      });

      const diff = await applyVariant(page, 'medium-low', 'gitlab');

      expect(diff.variantLevel).toBe('medium-low');
      expect(diff.appName).toBe('gitlab');
      expect(diff.changes).toEqual(mlChanges);
    });

    it('records handler removal for role="button" elements (role present, handler absent)', async () => {
      const mlChanges = makeMediumLowChanges();
      const page = createMockPage({
        hashBefore: HASH_BEFORE,
        hashAfter: HASH_AFTER_LOW,
        changes: mlChanges,
      });

      const diff = await applyVariant(page, 'medium-low', 'gitlab');

      const handlerRemovals = diff.changes.filter(c => c.changeType === 'remove-handler');
      expect(handlerRemovals.length).toBeGreaterThan(0);
      // Should target elements with role="button"
      expect(handlerRemovals.some(c => c.selector.includes('[role="button"]'))).toBe(true);
    });

    it('records label removal for inputs without placeholder', async () => {
      const mlChanges = makeMediumLowChanges();
      const page = createMockPage({
        hashBefore: HASH_BEFORE,
        hashAfter: HASH_AFTER_LOW,
        changes: mlChanges,
      });

      const diff = await applyVariant(page, 'medium-low', 'gitlab');

      const labelRemovals = diff.changes.filter(
        c => c.changeType === 'remove-element' && c.selector.startsWith('label'),
      );
      expect(labelRemovals.length).toBeGreaterThan(0);
    });
  });

  // --- Req 5.3: Base variant returns empty diff ---
  describe('Base variant (Req 5.3)', () => {
    it('returns empty changes array', async () => {
      const page = createMockPage({
        hashBefore: HASH_BEFORE,
        hashAfter: HASH_BEFORE, // same hash — no changes
      });

      const diff = await applyVariant(page, 'base', 'cms');

      expect(diff.variantLevel).toBe('base');
      expect(diff.appName).toBe('cms');
      expect(diff.changes).toEqual([]);
    });

    it('has matching before and after hashes (no DOM modification)', async () => {
      const page = createMockPage({
        hashBefore: HASH_BEFORE,
        hashAfter: HASH_BEFORE,
      });

      const diff = await applyVariant(page, 'base', 'cms');

      expect(diff.domHashBefore).toBe(diff.domHashAfter);
    });

    it('calls page.evaluate only for hash computation (no variant function)', async () => {
      const page = createMockPage({
        hashBefore: HASH_BEFORE,
        hashAfter: HASH_BEFORE,
      });

      await applyVariant(page, 'base', 'ecommerce');

      // Base variant: 2 evaluate calls (hashBefore + hashAfter), no variant function call
      expect(page.evaluate).toHaveBeenCalledTimes(2);
    });
  });

  // --- Req 5.4: High variant adds missing labels and landmarks ---
  describe('High variant (Req 5.4)', () => {
    it('returns a VariantDiff with accessibility enhancements', async () => {
      const highChanges = makeHighChanges();
      const page = createMockPage({
        hashBefore: HASH_BEFORE,
        hashAfter: HASH_AFTER_HIGH,
        changes: highChanges,
      });

      const diff = await applyVariant(page, 'high', 'reddit');

      expect(diff.variantLevel).toBe('high');
      expect(diff.appName).toBe('reddit');
      expect(diff.changes).toEqual(highChanges);
    });

    it('records add-attr changes for missing aria-labels', async () => {
      const highChanges = makeHighChanges();
      const page = createMockPage({
        hashBefore: HASH_BEFORE,
        hashAfter: HASH_AFTER_HIGH,
        changes: highChanges,
      });

      const diff = await applyVariant(page, 'high', 'reddit');

      const addAttrChanges = diff.changes.filter(c => c.changeType === 'add-attr');
      expect(addAttrChanges.length).toBeGreaterThan(0);
      expect(addAttrChanges.some(c => c.modified.includes('aria-label='))).toBe(true);
    });

    it('records add-element for skip-navigation link', async () => {
      const highChanges = makeHighChanges();
      const page = createMockPage({
        hashBefore: HASH_BEFORE,
        hashAfter: HASH_AFTER_HIGH,
        changes: highChanges,
      });

      const diff = await applyVariant(page, 'high', 'reddit');

      const addElChanges = diff.changes.filter(c => c.changeType === 'add-element');
      expect(addElChanges.length).toBeGreaterThan(0);
      expect(addElChanges.some(c => c.selector.includes('skip-link'))).toBe(true);
    });

    it('records landmark role additions', async () => {
      const highChanges = makeHighChanges();
      const page = createMockPage({
        hashBefore: HASH_BEFORE,
        hashAfter: HASH_AFTER_HIGH,
        changes: highChanges,
      });

      const diff = await applyVariant(page, 'high', 'reddit');

      const landmarkChanges = diff.changes.filter(
        c => c.changeType === 'add-attr' && c.modified.includes('role='),
      );
      expect(landmarkChanges.length).toBeGreaterThan(0);
      expect(landmarkChanges.some(c => c.modified.includes('role="banner"'))).toBe(true);
      expect(landmarkChanges.some(c => c.modified.includes('role="navigation"'))).toBe(true);
      expect(landmarkChanges.some(c => c.modified.includes('role="main"'))).toBe(true);
    });
  });

  // --- VariantDiff structure (Req 6.1) ---
  describe('VariantDiff structure (Req 6.1)', () => {
    it('includes variantLevel, appName, changes, and both DOM hashes', async () => {
      const page = createMockPage({
        hashBefore: HASH_BEFORE,
        hashAfter: HASH_AFTER_LOW,
        changes: makeLowChanges(),
      });

      const diff = await applyVariant(page, 'low', 'reddit');

      expect(diff).toHaveProperty('variantLevel');
      expect(diff).toHaveProperty('appName');
      expect(diff).toHaveProperty('changes');
      expect(diff).toHaveProperty('domHashBefore');
      expect(diff).toHaveProperty('domHashAfter');
      expect(typeof diff.domHashBefore).toBe('string');
      expect(typeof diff.domHashAfter).toBe('string');
      expect(Array.isArray(diff.changes)).toBe(true);
    });

    it('each DomChange has selector, changeType, original, and modified', async () => {
      const page = createMockPage({
        hashBefore: HASH_BEFORE,
        hashAfter: HASH_AFTER_LOW,
        changes: makeLowChanges(),
      });

      const diff = await applyVariant(page, 'low', 'reddit');

      for (const change of diff.changes) {
        expect(change).toHaveProperty('selector');
        expect(change).toHaveProperty('changeType');
        expect(change).toHaveProperty('original');
        expect(change).toHaveProperty('modified');
        expect(typeof change.selector).toBe('string');
        expect(typeof change.original).toBe('string');
        expect(typeof change.modified).toBe('string');
      }
    });
  });

  // --- Req 5.5: Works for all 4 WebArena apps ---
  describe('WebArena app support (Req 5.5)', () => {
    const apps = ['reddit', 'gitlab', 'cms', 'ecommerce'];

    for (const app of apps) {
      it(`applies variant to ${app}`, async () => {
        const page = createMockPage({
          hashBefore: HASH_BEFORE,
          hashAfter: HASH_AFTER_LOW,
          changes: makeLowChanges(),
        });

        const diff = await applyVariant(page, 'low', app);

        expect(diff.appName).toBe(app);
        expect(diff.changes.length).toBeGreaterThan(0);
      });
    }
  });
});

// ---------------------------------------------------------------------------
// Tests: revertVariant
// ---------------------------------------------------------------------------

describe('revertVariant', () => {
  // --- Req 6.2, 6.3: Reversal restores original DOM hash ---
  describe('reversal restores original DOM hash (Req 6.2, 6.3)', () => {
    it('returns success=true when hash after revert matches domHashBefore', async () => {
      const changes = makeLowChanges();
      const diff: VariantDiff = {
        variantLevel: 'low',
        appName: 'reddit',
        changes,
        domHashBefore: HASH_BEFORE,
        domHashAfter: HASH_AFTER_LOW,
      };

      const page = createRevertMockPage({
        hashAfterRevert: HASH_BEFORE, // matches domHashBefore
        changeCount: changes.length,
      });

      const result = await revertVariant(page, diff);

      expect(result.success).toBe(true);
      expect(result.domHashAfterRevert).toBe(HASH_BEFORE);
    });

    it('returns success=false when hash after revert does not match', async () => {
      const changes = makeLowChanges();
      const diff: VariantDiff = {
        variantLevel: 'low',
        appName: 'reddit',
        changes,
        domHashBefore: HASH_BEFORE,
        domHashAfter: HASH_AFTER_LOW,
      };

      const page = createRevertMockPage({
        hashAfterRevert: 'deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef',
        changeCount: changes.length,
      });

      const result = await revertVariant(page, diff);

      expect(result.success).toBe(false);
      expect(result.domHashAfterRevert).not.toBe(HASH_BEFORE);
    });

    it('calls page.evaluate once per change plus once for hash', async () => {
      const changes = makeLowChanges();
      const diff: VariantDiff = {
        variantLevel: 'low',
        appName: 'reddit',
        changes,
        domHashBefore: HASH_BEFORE,
        domHashAfter: HASH_AFTER_LOW,
      };

      const page = createRevertMockPage({
        hashAfterRevert: HASH_BEFORE,
        changeCount: changes.length,
      });

      await revertVariant(page, diff);

      // N changes + 1 hash computation
      expect(page.evaluate).toHaveBeenCalledTimes(changes.length + 1);
    });

    it('processes changes in reverse order', async () => {
      const changes: DomChange[] = [
        { selector: 'first', changeType: 'remove-attr', original: 'role="nav"', modified: '' },
        { selector: 'second', changeType: 'add-attr', original: '', modified: 'aria-label="x"' },
        { selector: 'third', changeType: 'replace', original: '<nav>A</nav>', modified: '<div>A</div>' },
      ];
      const diff: VariantDiff = {
        variantLevel: 'low',
        appName: 'reddit',
        changes,
        domHashBefore: HASH_BEFORE,
        domHashAfter: HASH_AFTER_LOW,
      };

      const evaluateCalls: string[] = [];
      let callIdx = 0;
      const page = {
        evaluate: vi.fn(async (arg: any) => {
          const idx = callIdx++;
          if (idx < changes.length) {
            // Record the script string to verify order
            evaluateCalls.push(typeof arg === 'string' ? arg : 'function');
            return undefined;
          }
          return HASH_BEFORE; // hash
        }),
      } as any;

      await revertVariant(page, diff);

      // The revert scripts should reference selectors in reverse order:
      // third, second, first
      expect(evaluateCalls.length).toBe(3);
      expect(evaluateCalls[0]).toContain('third');
      expect(evaluateCalls[1]).toContain('second');
      expect(evaluateCalls[2]).toContain('first');
    });
  });

  // --- Reversal with empty diff (base variant) ---
  describe('reversal with empty diff', () => {
    it('returns success=true for base variant with no changes', async () => {
      const diff: VariantDiff = {
        variantLevel: 'base',
        appName: 'cms',
        changes: [],
        domHashBefore: HASH_BEFORE,
        domHashAfter: HASH_BEFORE,
      };

      const page = createRevertMockPage({
        hashAfterRevert: HASH_BEFORE,
        changeCount: 0,
      });

      const result = await revertVariant(page, diff);

      expect(result.success).toBe(true);
      // Only 1 call: the hash computation (no changes to revert)
      expect(page.evaluate).toHaveBeenCalledTimes(1);
    });
  });
});

// ---------------------------------------------------------------------------
// Tests: Determinism (Req 5.7)
// ---------------------------------------------------------------------------

describe('deterministic output (Req 5.7)', () => {
  it('produces identical VariantDiff for same input DOM and variant level', async () => {
    const lowChanges = makeLowChanges();

    // First application
    const page1 = createMockPage({
      hashBefore: HASH_BEFORE,
      hashAfter: HASH_AFTER_LOW,
      changes: lowChanges,
    });
    const diff1 = await applyVariant(page1, 'low', 'reddit');

    // Second application with identical mock setup
    const page2 = createMockPage({
      hashBefore: HASH_BEFORE,
      hashAfter: HASH_AFTER_LOW,
      changes: lowChanges,
    });
    const diff2 = await applyVariant(page2, 'low', 'reddit');

    expect(diff1).toEqual(diff2);
  });

  it('produces identical changes for medium-low variant on same DOM', async () => {
    const mlChanges = makeMediumLowChanges();

    const page1 = createMockPage({
      hashBefore: HASH_BEFORE,
      hashAfter: HASH_AFTER_LOW,
      changes: mlChanges,
    });
    const diff1 = await applyVariant(page1, 'medium-low', 'gitlab');

    const page2 = createMockPage({
      hashBefore: HASH_BEFORE,
      hashAfter: HASH_AFTER_LOW,
      changes: mlChanges,
    });
    const diff2 = await applyVariant(page2, 'medium-low', 'gitlab');

    expect(diff1.changes).toEqual(diff2.changes);
    expect(diff1.domHashBefore).toBe(diff2.domHashBefore);
    expect(diff1.domHashAfter).toBe(diff2.domHashAfter);
  });

  it('produces identical changes for high variant on same DOM', async () => {
    const highChanges = makeHighChanges();

    const page1 = createMockPage({
      hashBefore: HASH_BEFORE,
      hashAfter: HASH_AFTER_HIGH,
      changes: highChanges,
    });
    const diff1 = await applyVariant(page1, 'high', 'reddit');

    const page2 = createMockPage({
      hashBefore: HASH_BEFORE,
      hashAfter: HASH_AFTER_HIGH,
      changes: highChanges,
    });
    const diff2 = await applyVariant(page2, 'high', 'reddit');

    expect(diff1).toEqual(diff2);
  });

  it('base variant always produces empty changes', async () => {
    const page1 = createMockPage({ hashBefore: HASH_BEFORE, hashAfter: HASH_BEFORE });
    const diff1 = await applyVariant(page1, 'base', 'cms');

    const page2 = createMockPage({ hashBefore: HASH_BEFORE, hashAfter: HASH_BEFORE });
    const diff2 = await applyVariant(page2, 'base', 'cms');

    expect(diff1.changes).toEqual([]);
    expect(diff2.changes).toEqual([]);
    expect(diff1).toEqual(diff2);
  });
});

// ---------------------------------------------------------------------------
// applyVariantSpec — AMT v8 individual-mode (Task A.4)
// ---------------------------------------------------------------------------

import { applyVariantSpec } from './index.js';

/**
 * Create a mock Playwright Page that tolerates the 4-call sequence of
 * individual-mode applyVariantSpec:
 *   0: computeDomHash (before)
 *   1: setting __OPERATOR_IDS + __OPERATOR_STRICT globals
 *   2: evaluating apply-all-individual.js (returns changes)
 *   3: computeDomHash (after)
 */
function createIndividualMockPage(opts: {
  hashBefore: string;
  hashAfter: string;
  changes: DomChange[];
}) {
  let call = 0;
  const evaluateFn = vi.fn(async (_script: unknown, _arg?: unknown) => {
    const idx = call++;
    if (idx === 0) return opts.hashBefore;
    if (idx === 1) return undefined; // setting globals, no return value
    if (idx === 2) return opts.changes; // apply-all-individual result
    return opts.hashAfter;
  });
  return { evaluate: evaluateFn, __evaluate: evaluateFn } as any;
}

describe('applyVariantSpec — individual mode', () => {
  it('records operatorIds in the returned VariantDiff', async () => {
    const page = createIndividualMockPage({
      hashBefore: 'hashA',
      hashAfter: 'hashB',
      changes: [
        {
          selector: 'label[for="q"]',
          changeType: 'remove-element',
          original: '<label for="q">Search</label>',
          modified: '',
        },
      ],
    });
    const diff = await applyVariantSpec(
      page,
      { kind: 'individual', operatorIds: ['L3'] },
      'shopping',
    );
    expect(diff.operatorIds).toEqual(['L3']);
    expect(diff.variantLevel).toBe('low'); // placeholder for individual-mode
    expect(diff.changes).toHaveLength(1);
    expect(diff.domHashBefore).toBe('hashA');
    expect(diff.domHashAfter).toBe('hashB');
    expect(diff.appName).toBe('shopping');
  });

  it('preserves operator order from caller (stored, even though runtime applies canonical order)', async () => {
    const page = createIndividualMockPage({
      hashBefore: 'h1',
      hashAfter: 'h2',
      changes: [],
    });
    const diff = await applyVariantSpec(
      page,
      { kind: 'individual', operatorIds: ['L11', 'H2'] },
      'reddit',
    );
    expect(diff.operatorIds).toEqual(['L11', 'H2']);
  });

  it('composite mode is byte-equivalent to legacy applyVariant', async () => {
    const lowChanges = makeLowChanges();
    const pageA = createMockPage({
      hashBefore: 'X',
      hashAfter: 'Y',
      changes: lowChanges,
    });
    const pageB = createMockPage({
      hashBefore: 'X',
      hashAfter: 'Y',
      changes: lowChanges,
    });
    const legacy = await applyVariant(pageA, 'low', 'gitlab');
    const spec = await applyVariantSpec(
      pageB,
      { kind: 'composite', level: 'low' },
      'gitlab',
    );
    expect(spec).toEqual(legacy);
    // operatorIds MUST NOT appear on composite-mode diffs
    expect('operatorIds' in spec).toBe(false);
  });

  it('individual mode throws if evaluate returns non-array (guards against silent no-op)', async () => {
    let call = 0;
    const evaluateFn = vi.fn(async () => {
      const idx = call++;
      if (idx === 0) return 'hashA';
      if (idx === 1) return undefined;
      if (idx === 2) return 'oops-not-an-array'; // misbehaving page.evaluate
      return 'hashB';
    });
    const page = { evaluate: evaluateFn } as any;
    await expect(
      applyVariantSpec(
        page,
        { kind: 'individual', operatorIds: ['L3'] },
        'shopping',
      ),
    ).rejects.toThrow(/non-array/);
  });
});
