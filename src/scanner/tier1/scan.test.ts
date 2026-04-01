// Unit tests for Tier 1 Scanner
// Requirements: 1.1, 1.2, 1.3, 1.4, 1.5

import { describe, it, expect, vi, beforeEach } from 'vitest';

// --- Mock @axe-core/playwright ---
const mockAnalyze = vi.fn();
const mockWithTags = vi.fn(() => ({ analyze: mockAnalyze }));
const MockAxeBuilder = vi.fn(() => ({ withTags: mockWithTags }));

vi.mock('@axe-core/playwright', () => ({
  AxeBuilder: MockAxeBuilder,
}));

// --- Mock lighthouse ---
const mockLighthouse = vi.fn();
const mockLighthouseSnapshot = vi.fn();
vi.mock('lighthouse', () => ({
  default: mockLighthouse,
  snapshot: mockLighthouseSnapshot,
}));

import { scanTier1 } from './scan.js';
import type { Tier1ScanOptions } from '../types.js';

/** Minimal Playwright Page stub */
function createMockPage(): any {
  return {
    url: () => 'https://example.com',
    context: () => ({
      browser: () => ({
        wsEndpoint: () => 'ws://127.0.0.1:9222/devtools/browser/fake-id',
      }),
    }),
  };
}

/** Build a realistic axe-core result */
function makeAxeResult(violations: any[] = []) {
  return {
    violations,
    passes: [],
    incomplete: [],
    inapplicable: [],
  };
}

/** Build a realistic Lighthouse runner result */
function makeLighthouseResult(score: number, audits: Record<string, any> = {}) {
  return {
    lhr: {
      categories: { accessibility: { score } },
      audits,
    },
  };
}

describe('scanTier1', () => {
  const defaultOptions: Tier1ScanOptions = {
    url: 'https://example.com',
    wcagLevels: ['A', 'AA'],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // --- Req 1.5: WCAG level filtering ---
  describe('WCAG level filtering', () => {
    it('maps WCAG levels to axe-core tags', async () => {
      mockAnalyze.mockResolvedValue(makeAxeResult());
      mockLighthouse.mockResolvedValue(makeLighthouseResult(0.95));

      await scanTier1(createMockPage(), {
        url: 'https://example.com',
        wcagLevels: ['A', 'AA', 'AAA'],
      });

      expect(mockWithTags).toHaveBeenCalledWith(['wcag2a', 'wcag2aa', 'wcag2aaa']);
    });

    it('passes only requested levels', async () => {
      mockAnalyze.mockResolvedValue(makeAxeResult());
      mockLighthouse.mockResolvedValue(makeLighthouseResult(0.9));

      await scanTier1(createMockPage(), {
        url: 'https://example.com',
        wcagLevels: ['AA'],
      });

      expect(mockWithTags).toHaveBeenCalledWith(['wcag2aa']);
    });
  });

  // --- Req 1.1: axe-core result parsing and grouping by WCAG criterion ---
  describe('axe-core result parsing', () => {
    it('groups violations by WCAG criterion', async () => {
      mockAnalyze.mockResolvedValue(
        makeAxeResult([
          {
            id: 'color-contrast',
            impact: 'serious',
            description: 'Elements must have sufficient color contrast',
            helpUrl: 'https://dequeuniversity.com/rules/axe/4.10/color-contrast',
            tags: ['wcag2aa', 'wcag143'],
            nodes: [{ html: '<p>' }, { html: '<span>' }],
          },
          {
            id: 'image-alt',
            impact: 'critical',
            description: 'Images must have alternate text',
            helpUrl: 'https://dequeuniversity.com/rules/axe/4.10/image-alt',
            tags: ['wcag2a', 'wcag111'],
            nodes: [{ html: '<img>' }],
          },
        ])
      );
      mockLighthouse.mockResolvedValue(makeLighthouseResult(0.8));

      const result = await scanTier1(createMockPage(), defaultOptions);

      expect(result.axeCore.violationCount).toBe(2);
      expect(result.axeCore.violationsByWcagCriterion['1.4.3']).toHaveLength(1);
      expect(result.axeCore.violationsByWcagCriterion['1.4.3'][0].id).toBe('color-contrast');
      expect(result.axeCore.violationsByWcagCriterion['1.1.1']).toHaveLength(1);
      expect(result.axeCore.violationsByWcagCriterion['1.1.1'][0].id).toBe('image-alt');
    });

    it('counts impact severity correctly', async () => {
      mockAnalyze.mockResolvedValue(
        makeAxeResult([
          { id: 'v1', impact: 'critical', description: '', tags: ['wcag111'], nodes: [{}] },
          { id: 'v2', impact: 'serious', description: '', tags: ['wcag143'], nodes: [{}] },
          { id: 'v3', impact: 'serious', description: '', tags: ['wcag211'], nodes: [{}] },
          { id: 'v4', impact: 'minor', description: '', tags: ['wcag311'], nodes: [{}] },
        ])
      );
      mockLighthouse.mockResolvedValue(makeLighthouseResult(0.7));

      const result = await scanTier1(createMockPage(), defaultOptions);

      expect(result.axeCore.impactSeverity.critical).toBe(1);
      expect(result.axeCore.impactSeverity.serious).toBe(2);
      expect(result.axeCore.impactSeverity.moderate).toBe(0);
      expect(result.axeCore.impactSeverity.minor).toBe(1);
    });

    it('files violations without WCAG tags under "other"', async () => {
      mockAnalyze.mockResolvedValue(
        makeAxeResult([
          { id: 'custom-rule', impact: 'moderate', description: '', tags: ['best-practice'], nodes: [{}] },
        ])
      );
      mockLighthouse.mockResolvedValue(makeLighthouseResult(0.9));

      const result = await scanTier1(createMockPage(), defaultOptions);

      expect(result.axeCore.violationsByWcagCriterion['other']).toHaveLength(1);
      expect(result.axeCore.violationsByWcagCriterion['other'][0].id).toBe('custom-rule');
    });

    it('records node count per violation', async () => {
      mockAnalyze.mockResolvedValue(
        makeAxeResult([
          { id: 'link-name', impact: 'serious', description: '', tags: ['wcag412'], nodes: [{}, {}, {}] },
        ])
      );
      mockLighthouse.mockResolvedValue(makeLighthouseResult(0.85));

      const result = await scanTier1(createMockPage(), defaultOptions);

      expect(result.axeCore.violationsByWcagCriterion['4.1.2'][0].nodes).toBe(3);
    });
  });

  // --- Req 1.2: Lighthouse score extraction ---
  describe('Lighthouse score extraction', () => {
    it('extracts accessibility score as 0–100 integer', async () => {
      mockAnalyze.mockResolvedValue(makeAxeResult());
      mockLighthouse.mockResolvedValue(makeLighthouseResult(0.92, {
        'aria-roles': { score: 1, details: { type: 'table' } },
        'color-contrast': { score: 0, details: { type: 'table' } },
      }));

      const result = await scanTier1(createMockPage(), defaultOptions);

      expect(result.lighthouse.accessibilityScore).toBe(92);
      expect(result.lighthouse.audits['aria-roles'].pass).toBe(true);
      expect(result.lighthouse.audits['color-contrast'].pass).toBe(false);
    });

    it('handles missing Lighthouse result gracefully', async () => {
      mockAnalyze.mockResolvedValue(makeAxeResult());
      mockLighthouse.mockResolvedValue(null);

      const result = await scanTier1(createMockPage(), defaultOptions);

      expect(result.lighthouse.accessibilityScore).toBe(0);
      expect(result.lighthouse.audits).toEqual({});
    });
  });

  // --- Req 1.4: Error handling when one tool fails ---
  describe('error handling (Promise.allSettled)', () => {
    it('returns partial results when axe-core fails', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      mockAnalyze.mockRejectedValue(new Error('axe-core crashed'));
      mockLighthouse.mockResolvedValue(makeLighthouseResult(0.88));

      const result = await scanTier1(createMockPage(), defaultOptions);

      // Lighthouse results should be present
      expect(result.lighthouse.accessibilityScore).toBe(88);
      // axe-core should have empty defaults
      expect(result.axeCore.violationCount).toBe(0);
      expect(result.axeCore.violationsByWcagCriterion).toEqual({});
      // Error should be logged
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('axe-core failed'),
        expect.any(Error)
      );
      consoleSpy.mockRestore();
    });

    it('returns partial results when Lighthouse fails', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      mockAnalyze.mockResolvedValue(
        makeAxeResult([
          { id: 'image-alt', impact: 'critical', description: '', tags: ['wcag111'], nodes: [{}] },
        ])
      );
      mockLighthouse.mockRejectedValue(new Error('Lighthouse timed out'));

      const result = await scanTier1(createMockPage(), defaultOptions);

      // axe-core results should be present
      expect(result.axeCore.violationCount).toBe(1);
      // Lighthouse should have empty defaults
      expect(result.lighthouse.accessibilityScore).toBe(0);
      expect(result.lighthouse.audits).toEqual({});
      // Error should be logged
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Lighthouse failed'),
        expect.any(Error)
      );
      consoleSpy.mockRestore();
    });

    it('returns empty defaults when both tools fail', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      mockAnalyze.mockRejectedValue(new Error('axe boom'));
      mockLighthouse.mockRejectedValue(new Error('lh boom'));

      const result = await scanTier1(createMockPage(), defaultOptions);

      expect(result.axeCore.violationCount).toBe(0);
      expect(result.lighthouse.accessibilityScore).toBe(0);
      expect(consoleSpy).toHaveBeenCalledTimes(2);
      consoleSpy.mockRestore();
    });
  });

  // --- General output structure ---
  describe('output structure', () => {
    it('includes URL and ISO timestamp', async () => {
      mockAnalyze.mockResolvedValue(makeAxeResult());
      mockLighthouse.mockResolvedValue(makeLighthouseResult(1.0));

      const result = await scanTier1(createMockPage(), defaultOptions);

      expect(result.url).toBe('https://example.com');
      expect(result.scannedAt).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    });
  });
});
