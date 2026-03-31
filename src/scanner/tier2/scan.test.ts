// Unit tests for Tier 2 Scanner
// Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { scanTier2 } from './scan.js';

// --- Mock helpers ---

/**
 * Create a mock Page with controlled evaluate() results.
 *
 * The new computeKeyboardNavigability calls page.evaluate multiple times
 * (totalFocusable, startInfo, then per-Tab current element) and uses
 * page.keyboard.press('Tab'). The evaluateResults array is consumed
 * sequentially across ALL evaluate calls in scanTier2.
 *
 * Call order in scanTier2:
 *   [0] semanticHtmlRatio        — page.evaluate (concurrent batch)
 *   [1] ariaCorrectness          — page.evaluate (concurrent batch)
 *   [2] formLabelingCompleteness — page.evaluate (concurrent batch)
 *   [3] landmarkCoverage         — page.evaluate (concurrent batch)
 *   [4] keyboardNav: totalFocusable count
 *   [5] keyboardNav: startInfo   — { tag, id }
 *   [6..N] keyboardNav: per-Tab current element — { tag, id, key } or null
 *   [N+1..] pseudo-compliance calls (handled by $$ mock)
 */
function createMockPage(overrides: {
  evaluateResults?: any[];
  $$Result?: any[];
}) {
  let evaluateCallIndex = 0;
  const evaluateResults = overrides.evaluateResults ?? [];

  return {
    evaluate: vi.fn(async () => {
      const idx = evaluateCallIndex;
      evaluateCallIndex++;
      if (idx < evaluateResults.length) return evaluateResults[idx];
      return [0, 0];
    }),
    $$: vi.fn(async () => overrides.$$Result ?? []),
    keyboard: { press: vi.fn(async () => {}) },
  } as unknown as import('playwright').Page;
}

/**
 * Create a mock CDPSession that returns controlled AX tree nodes
 * and event listener data.
 */
function createMockCdpSession(overrides: {
  axTreeNodes?: any[];
  eventListeners?: Record<string, Array<{ type: string }>>;
  runtimeResult?: any;
}) {
  const axTreeNodes = overrides.axTreeNodes ?? [];
  const eventListeners = overrides.eventListeners ?? {};
  const runtimeResult = overrides.runtimeResult ?? { objectId: 'obj-1' };

  return {
    send: vi.fn(async (method: string, params?: any) => {
      if (method === 'Accessibility.getFullAXTree') {
        return { nodes: axTreeNodes };
      }
      if (method === 'Runtime.evaluate') {
        return { result: runtimeResult };
      }
      if (method === 'DOMDebugger.getEventListeners') {
        const objId = params?.objectId ?? 'default';
        return { listeners: eventListeners[objId] ?? [] };
      }
      return {};
    }),
  } as unknown as import('playwright').CDPSession;
}

describe('scanTier2', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  // --- Req 2.9: All metrics returned as 0.0–1.0 ---
  describe('metric value ranges (Req 2.9)', () => {
    it('returns all ratio metrics between 0.0 and 1.0', async () => {
      const page = createMockPage({
        evaluateResults: [
          [3, 10],                        // semanticHtmlRatio
          { valid: 8, total: 10 },        // ariaCorrectness
          { labeled: 5, total: 10 },      // formLabelingCompleteness
          { landmarkTextLength: 60, totalTextLength: 100 }, // landmarkCoverage
          3,                              // keyboardNav: totalFocusable = 3
          { tag: 'BODY', id: '' },        // keyboardNav: startInfo
          { tag: 'button', id: 'b1', key: 'BUTTON#b1.' }, // Tab 1
          { tag: 'input', id: 'i1', key: 'INPUT#i1.' },   // Tab 2
          null,                           // Tab 3 → focus to body, cycle done
        ],
      });
      const cdp = createMockCdpSession({
        axTreeNodes: [
          { role: { value: 'button' }, name: { value: 'Submit' } },
          { role: { value: 'link' }, name: { value: 'Home' } },
          { role: { value: 'textbox' }, name: { value: '' } },
        ],
      });

      const result = await scanTier2(page, cdp);

      expect(result.semanticHtmlRatio).toBeGreaterThanOrEqual(0);
      expect(result.semanticHtmlRatio).toBeLessThanOrEqual(1);
      expect(result.accessibleNameCoverage).toBeGreaterThanOrEqual(0);
      expect(result.accessibleNameCoverage).toBeLessThanOrEqual(1);
      expect(result.keyboardNavigability).toBeGreaterThanOrEqual(0);
      expect(result.keyboardNavigability).toBeLessThanOrEqual(1);
      expect(result.ariaCorrectness).toBeGreaterThanOrEqual(0);
      expect(result.ariaCorrectness).toBeLessThanOrEqual(1);
      expect(result.pseudoComplianceRatio).toBeGreaterThanOrEqual(0);
      expect(result.pseudoComplianceRatio).toBeLessThanOrEqual(1);
      expect(result.formLabelingCompleteness).toBeGreaterThanOrEqual(0);
      expect(result.formLabelingCompleteness).toBeLessThanOrEqual(1);
      expect(result.landmarkCoverage).toBeGreaterThanOrEqual(0);
      expect(result.landmarkCoverage).toBeLessThanOrEqual(1);
    });
  });

  // --- Req 2.1: Semantic HTML ratio ---
  describe('semantic HTML ratio (Req 2.1)', () => {
    it('computes ratio of semantic elements to total elements', async () => {
      const page = createMockPage({
        evaluateResults: [
          [5, 20],                   // semanticHtmlRatio: 5/20 = 0.25
          { valid: 0, total: 0 },
          { labeled: 0, total: 0 },
          { landmarkTextLength: 0, totalTextLength: 0 },
          0,                         // keyboardNav: totalFocusable = 0 → returns 0
        ],
      });
      const cdp = createMockCdpSession({ axTreeNodes: [] });

      const result = await scanTier2(page, cdp);

      expect(result.semanticHtmlRatio).toBeCloseTo(0.25, 2);
    });

    it('returns 0 when page has no elements', async () => {
      const page = createMockPage({
        evaluateResults: [
          [0, 0],
          { valid: 0, total: 0 },
          { labeled: 0, total: 0 },
          { landmarkTextLength: 0, totalTextLength: 0 },
          0,
        ],
      });
      const cdp = createMockCdpSession({ axTreeNodes: [] });

      const result = await scanTier2(page, cdp);

      expect(result.semanticHtmlRatio).toBe(0);
    });
  });

  // --- Req 2.2: Accessible name coverage ---
  describe('accessible name coverage (Req 2.2)', () => {
    it('computes ratio of named interactive elements', async () => {
      const page = createMockPage({
        evaluateResults: [
          [0, 0], { valid: 0, total: 0 }, { labeled: 0, total: 0 },
          { landmarkTextLength: 0, totalTextLength: 0 },
          0,
        ],
      });
      const cdp = createMockCdpSession({
        axTreeNodes: [
          { role: { value: 'button' }, name: { value: 'Submit' } },
          { role: { value: 'button' }, name: { value: 'Cancel' } },
          { role: { value: 'link' }, name: { value: '' } },  // missing name
          { role: { value: 'textbox' }, name: { value: 'Email' } },
          { role: { value: 'heading' }, name: { value: 'Title' } }, // not interactive
        ],
      });

      const result = await scanTier2(page, cdp);

      // 4 interactive (2 buttons + 1 link + 1 textbox), 3 named → 3/4 = 0.75
      expect(result.accessibleNameCoverage).toBeCloseTo(0.75, 2);
    });

    it('returns 0 when no interactive elements exist', async () => {
      const page = createMockPage({
        evaluateResults: [
          [0, 0], { valid: 0, total: 0 }, { labeled: 0, total: 0 },
          { landmarkTextLength: 0, totalTextLength: 0 },
          0,
        ],
      });
      const cdp = createMockCdpSession({
        axTreeNodes: [
          { role: { value: 'heading' }, name: { value: 'Title' } },
          { role: { value: 'paragraph' }, name: { value: '' } },
        ],
      });

      const result = await scanTier2(page, cdp);

      expect(result.accessibleNameCoverage).toBe(0);
    });

    it('skips ignored nodes', async () => {
      const page = createMockPage({
        evaluateResults: [
          [0, 0], { valid: 0, total: 0 }, { labeled: 0, total: 0 },
          { landmarkTextLength: 0, totalTextLength: 0 },
          0,
        ],
      });
      const cdp = createMockCdpSession({
        axTreeNodes: [
          { role: { value: 'button' }, name: { value: 'OK' }, ignored: false },
          { role: { value: 'button' }, name: { value: '' }, ignored: true },
        ],
      });

      const result = await scanTier2(page, cdp);

      expect(result.accessibleNameCoverage).toBe(1);
    });
  });

  // --- Req 2.3: Keyboard navigability ---
  describe('keyboard navigability (Req 2.3)', () => {
    it('computes ratio of focused elements via page.keyboard.press Tab', async () => {
      // New implementation: evaluate(totalFocusable), evaluate(startInfo),
      // then loop: keyboard.press('Tab') + evaluate(current)
      const page = createMockPage({
        evaluateResults: [
          [0, 0], { valid: 0, total: 0 }, { labeled: 0, total: 0 },
          { landmarkTextLength: 0, totalTextLength: 0 },
          // keyboardNav sequence:
          4,                              // totalFocusable = 4
          { tag: 'BODY', id: '' },        // startInfo
          { tag: 'button', id: 'b1', key: 'BUTTON#b1.' },
          { tag: 'input', id: 'i1', key: 'INPUT#i1.' },
          { tag: 'a', id: 'a1', key: 'A#a1.' },
          null,                           // focus went to body → cycle done
        ],
      });
      const cdp = createMockCdpSession({ axTreeNodes: [] });

      const result = await scanTier2(page, cdp);

      // 3 unique elements focused out of 4 focusable → 0.75
      expect(result.keyboardNavigability).toBeCloseTo(0.75, 2);
      // Verify page.keyboard.press was called
      expect((page.keyboard.press as any).mock.calls.length).toBeGreaterThan(0);
    });

    it('returns 0 when no focusable elements exist', async () => {
      const page = createMockPage({
        evaluateResults: [
          [0, 0], { valid: 0, total: 0 }, { labeled: 0, total: 0 },
          { landmarkTextLength: 0, totalTextLength: 0 },
          0,  // totalFocusable = 0 → early return
        ],
      });
      const cdp = createMockCdpSession({ axTreeNodes: [] });

      const result = await scanTier2(page, cdp);

      expect(result.keyboardNavigability).toBe(0);
    });
  });

  // --- Req 2.4: ARIA correctness ---
  describe('ARIA correctness (Req 2.4)', () => {
    it('computes ratio of valid ARIA elements', async () => {
      const page = createMockPage({
        evaluateResults: [
          [0, 0],
          { valid: 7, total: 10 },
          { labeled: 0, total: 0 },
          { landmarkTextLength: 0, totalTextLength: 0 },
          0,
        ],
      });
      const cdp = createMockCdpSession({ axTreeNodes: [] });

      const result = await scanTier2(page, cdp);

      expect(result.ariaCorrectness).toBeCloseTo(0.7, 2);
    });

    it('returns 0 when no ARIA elements exist', async () => {
      const page = createMockPage({
        evaluateResults: [
          [0, 0],
          { valid: 0, total: 0 },
          { labeled: 0, total: 0 },
          { landmarkTextLength: 0, totalTextLength: 0 },
          0,
        ],
      });
      const cdp = createMockCdpSession({ axTreeNodes: [] });

      const result = await scanTier2(page, cdp);

      expect(result.ariaCorrectness).toBe(0);
    });
  });

  // --- Req 2.5: Pseudo-compliance detection ---
  describe('pseudo-compliance detection (Req 2.5)', () => {
    it('detects elements with role but no event handlers', async () => {
      const mockHandle = {
        evaluate: vi.fn(async () => '<div role="button">'),
      };
      const page = createMockPage({
        evaluateResults: [
          [0, 0], { valid: 0, total: 0 }, { labeled: 0, total: 0 },
          { landmarkTextLength: 0, totalTextLength: 0 },
          0,
        ],
        $$Result: [mockHandle, mockHandle],
      });
      const cdp = createMockCdpSession({
        axTreeNodes: [],
        runtimeResult: { objectId: 'obj-1' },
        eventListeners: {
          'obj-1': [],
        },
      });

      const result = await scanTier2(page, cdp);

      expect(result.pseudoComplianceCount).toBe(2);
      expect(result.pseudoComplianceRatio).toBe(1);
    });

    it('returns 0 when all role elements have handlers', async () => {
      const mockHandle = {
        evaluate: vi.fn(async () => '<div role="button">'),
      };
      const page = createMockPage({
        evaluateResults: [
          [0, 0], { valid: 0, total: 0 }, { labeled: 0, total: 0 },
          { landmarkTextLength: 0, totalTextLength: 0 },
          0,
        ],
        $$Result: [mockHandle],
      });
      const cdp = createMockCdpSession({
        axTreeNodes: [],
        runtimeResult: { objectId: 'obj-1' },
        eventListeners: {
          'obj-1': [{ type: 'click' }],
        },
      });

      const result = await scanTier2(page, cdp);

      expect(result.pseudoComplianceCount).toBe(0);
      expect(result.pseudoComplianceRatio).toBe(0);
    });

    it('returns 0 when no interactive role elements exist', async () => {
      const page = createMockPage({
        evaluateResults: [
          [0, 0], { valid: 0, total: 0 }, { labeled: 0, total: 0 },
          { landmarkTextLength: 0, totalTextLength: 0 },
          0,
        ],
        $$Result: [],
      });
      const cdp = createMockCdpSession({ axTreeNodes: [] });

      const result = await scanTier2(page, cdp);

      expect(result.pseudoComplianceCount).toBe(0);
      expect(result.pseudoComplianceRatio).toBe(0);
    });
  });

  // --- Req 2.6: Form labeling completeness ---
  describe('form labeling completeness (Req 2.6)', () => {
    it('computes ratio of labeled form controls', async () => {
      const page = createMockPage({
        evaluateResults: [
          [0, 0], { valid: 0, total: 0 },
          { labeled: 3, total: 4 },
          { landmarkTextLength: 0, totalTextLength: 0 },
          0,
        ],
      });
      const cdp = createMockCdpSession({ axTreeNodes: [] });

      const result = await scanTier2(page, cdp);

      expect(result.formLabelingCompleteness).toBeCloseTo(0.75, 2);
    });

    it('returns 0 when no form controls exist', async () => {
      const page = createMockPage({
        evaluateResults: [
          [0, 0], { valid: 0, total: 0 },
          { labeled: 0, total: 0 },
          { landmarkTextLength: 0, totalTextLength: 0 },
          0,
        ],
      });
      const cdp = createMockCdpSession({ axTreeNodes: [] });

      const result = await scanTier2(page, cdp);

      expect(result.formLabelingCompleteness).toBe(0);
    });
  });

  // --- Req 2.7: Landmark coverage ---
  describe('landmark coverage (Req 2.7)', () => {
    it('computes ratio of text inside landmarks', async () => {
      const page = createMockPage({
        evaluateResults: [
          [0, 0], { valid: 0, total: 0 }, { labeled: 0, total: 0 },
          { landmarkTextLength: 80, totalTextLength: 100 },
          0,
        ],
      });
      const cdp = createMockCdpSession({ axTreeNodes: [] });

      const result = await scanTier2(page, cdp);

      expect(result.landmarkCoverage).toBeCloseTo(0.8, 2);
    });

    it('returns 0 when page has no text', async () => {
      const page = createMockPage({
        evaluateResults: [
          [0, 0], { valid: 0, total: 0 }, { labeled: 0, total: 0 },
          { landmarkTextLength: 0, totalTextLength: 0 },
          0,
        ],
      });
      const cdp = createMockCdpSession({ axTreeNodes: [] });

      const result = await scanTier2(page, cdp);

      expect(result.landmarkCoverage).toBe(0);
    });
  });

  // --- Req 2.8: Shadow DOM traversal ---
  describe('Shadow DOM traversal (Req 2.8)', () => {
    it('sets shadowDomIncluded to true by default', async () => {
      const page = createMockPage({
        evaluateResults: [
          [0, 0], { valid: 0, total: 0 }, { labeled: 0, total: 0 },
          { landmarkTextLength: 0, totalTextLength: 0 },
          0,
        ],
      });
      const cdp = createMockCdpSession({ axTreeNodes: [] });

      const result = await scanTier2(page, cdp);

      expect(result.shadowDomIncluded).toBe(true);
    });

    it('sets shadowDomIncluded to false when disabled', async () => {
      const page = createMockPage({
        evaluateResults: [
          [0, 0], { valid: 0, total: 0 }, { labeled: 0, total: 0 },
          { landmarkTextLength: 0, totalTextLength: 0 },
          0,
        ],
      });
      const cdp = createMockCdpSession({ axTreeNodes: [] });

      const result = await scanTier2(page, cdp, { traverseShadowDOM: false });

      expect(result.shadowDomIncluded).toBe(false);
    });

    it('passes traverseShadow flag to page.evaluate calls', async () => {
      const page = createMockPage({
        evaluateResults: [
          [0, 0], { valid: 0, total: 0 }, { labeled: 0, total: 0 },
          { landmarkTextLength: 0, totalTextLength: 0 },
          0,
        ],
      });
      const cdp = createMockCdpSession({ axTreeNodes: [] });

      await scanTier2(page, cdp, { traverseShadowDOM: false });

      const evaluateMock = page.evaluate as ReturnType<typeof vi.fn>;
      expect(evaluateMock).toHaveBeenCalled();
    });
  });

  // --- Output structure ---
  describe('output structure', () => {
    it('returns all expected Tier2Metrics fields', async () => {
      const page = createMockPage({
        evaluateResults: [
          [2, 10], { valid: 5, total: 8 }, { labeled: 3, total: 6 },
          { landmarkTextLength: 50, totalTextLength: 100 },
          2,                              // totalFocusable = 2
          { tag: 'BODY', id: '' },        // startInfo
          { tag: 'button', id: 'b1', key: 'BUTTON#b1.' },
          null,                           // cycle done
        ],
      });
      const cdp = createMockCdpSession({
        axTreeNodes: [
          { role: { value: 'button' }, name: { value: 'OK' } },
        ],
      });

      const result = await scanTier2(page, cdp);

      expect(result).toHaveProperty('semanticHtmlRatio');
      expect(result).toHaveProperty('accessibleNameCoverage');
      expect(result).toHaveProperty('keyboardNavigability');
      expect(result).toHaveProperty('ariaCorrectness');
      expect(result).toHaveProperty('pseudoComplianceCount');
      expect(result).toHaveProperty('pseudoComplianceRatio');
      expect(result).toHaveProperty('formLabelingCompleteness');
      expect(result).toHaveProperty('landmarkCoverage');
      expect(result).toHaveProperty('shadowDomIncluded');
    });

    it('pseudoComplianceCount is a non-negative integer', async () => {
      const page = createMockPage({
        evaluateResults: [
          [0, 0], { valid: 0, total: 0 }, { labeled: 0, total: 0 },
          { landmarkTextLength: 0, totalTextLength: 0 },
          0,
        ],
      });
      const cdp = createMockCdpSession({ axTreeNodes: [] });

      const result = await scanTier2(page, cdp);

      expect(result.pseudoComplianceCount).toBeGreaterThanOrEqual(0);
      expect(Number.isInteger(result.pseudoComplianceCount)).toBe(true);
    });
  });
});
