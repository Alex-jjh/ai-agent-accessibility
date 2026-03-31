/**
 * Unit tests for HAR Capture module.
 * Tests: valid HAR capture with metadata, error handling, concurrent capture.
 * Requirements: 11.1–11.6, 19.1
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { HarCaptureOptions, HarCaptureResult, HarMetadata } from '../types.js';

// Mock playwright and fs before importing the module
const mockGoto = vi.fn().mockResolvedValue(undefined);
const mockWaitForTimeout = vi.fn().mockResolvedValue(undefined);
const mockRouteFromHAR = vi.fn().mockResolvedValue(undefined);
const mockEvaluate = vi.fn().mockResolvedValue('en');
const mockNewPage = vi.fn().mockResolvedValue({
  goto: mockGoto,
  waitForTimeout: mockWaitForTimeout,
  routeFromHAR: mockRouteFromHAR,
  evaluate: mockEvaluate,
});
const mockContextClose = vi.fn().mockResolvedValue(undefined);
const mockNewContext = vi.fn().mockResolvedValue({
  newPage: mockNewPage,
  close: mockContextClose,
});
const mockBrowserClose = vi.fn().mockResolvedValue(undefined);

vi.mock('playwright', () => ({
  chromium: {
    launch: vi.fn().mockResolvedValue({
      newContext: mockNewContext,
      close: mockBrowserClose,
    }),
  },
}));

vi.mock('node:fs/promises', () => ({
  mkdir: vi.fn().mockResolvedValue(undefined),
  writeFile: vi.fn().mockResolvedValue(undefined),
}));

// Import after mocks are set up
const { captureHar } = await import('./capture.js');

describe('captureHar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNewPage.mockResolvedValue({
      goto: mockGoto,
      waitForTimeout: mockWaitForTimeout,
      routeFromHAR: mockRouteFromHAR,
      evaluate: mockEvaluate,
    });
    mockNewContext.mockResolvedValue({
      newPage: mockNewPage,
      close: mockContextClose,
    });
  });

  it('should capture a single URL and return success with metadata', async () => {
    const options: HarCaptureOptions = {
      urls: ['https://example.com'],
      waitAfterLoadMs: 1000,
      concurrency: 5,
      outputDir: '/tmp/har-test',
    };

    const results = await captureHar(options);

    expect(results).toHaveLength(1);
    expect(results[0].success).toBe(true);
    expect(results[0].harFilePath).toContain('https___example_com');
    expect(results[0].harFilePath).toContain('.har');
    expect(results[0].metadata.targetUrl).toBe('https://example.com');
    expect(results[0].metadata.pageLanguage).toBe('en');
    expect(results[0].metadata.recordingTimestamp).toBeTruthy();
  });

  it('should produce metadata with all required fields', async () => {
    const options: HarCaptureOptions = {
      urls: ['https://example.com'],
      waitAfterLoadMs: 500,
      concurrency: 1,
      outputDir: '/tmp/har-test',
    };

    const results = await captureHar(options);
    const meta: HarMetadata = results[0].metadata;

    expect(meta).toHaveProperty('recordingTimestamp');
    expect(meta).toHaveProperty('targetUrl');
    expect(meta).toHaveProperty('geoRegion');
    expect(meta).toHaveProperty('sectorClassification');
    expect(meta).toHaveProperty('pageLanguage');
  });

  it('should use routeFromHAR in recording mode', async () => {
    const options: HarCaptureOptions = {
      urls: ['https://example.com'],
      waitAfterLoadMs: 500,
      concurrency: 1,
      outputDir: '/tmp/har-test',
    };

    await captureHar(options);

    expect(mockRouteFromHAR).toHaveBeenCalledWith(
      expect.stringContaining('.har'),
      { update: true },
    );
  });

  it('should wait the configured time after page load for dynamic content', async () => {
    const options: HarCaptureOptions = {
      urls: ['https://example.com'],
      waitAfterLoadMs: 7500,
      concurrency: 1,
      outputDir: '/tmp/har-test',
    };

    await captureHar(options);

    expect(mockWaitForTimeout).toHaveBeenCalledWith(7500);
  });

  it('should handle URL load failure gracefully and continue', async () => {
    // First URL fails, second succeeds
    let callCount = 0;
    mockNewPage.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) {
        return {
          goto: vi.fn().mockRejectedValue(new Error('Navigation timeout')),
          waitForTimeout: mockWaitForTimeout,
          routeFromHAR: mockRouteFromHAR,
          evaluate: mockEvaluate,
        };
      }
      return {
        goto: mockGoto,
        waitForTimeout: mockWaitForTimeout,
        routeFromHAR: mockRouteFromHAR,
        evaluate: mockEvaluate,
      };
    });

    const options: HarCaptureOptions = {
      urls: ['https://fail.example.com', 'https://success.example.com'],
      waitAfterLoadMs: 500,
      concurrency: 1,
      outputDir: '/tmp/har-test',
    };

    const results = await captureHar(options);

    expect(results).toHaveLength(2);
    expect(results[0].success).toBe(false);
    expect(results[0].error).toContain('Navigation timeout');
    expect(results[1].success).toBe(true);
  });

  it('should process URLs concurrently up to the concurrency limit', async () => {
    const urls = Array.from({ length: 8 }, (_, i) => `https://site${i}.example.com`);
    const options: HarCaptureOptions = {
      urls,
      waitAfterLoadMs: 100,
      concurrency: 3,
      outputDir: '/tmp/har-test',
    };

    const results = await captureHar(options);

    // All 8 URLs should be processed
    expect(results).toHaveLength(8);
    expect(results.every((r) => r.success)).toBe(true);
  });

  it('should close the browser after all captures complete', async () => {
    const options: HarCaptureOptions = {
      urls: ['https://example.com'],
      waitAfterLoadMs: 100,
      concurrency: 1,
      outputDir: '/tmp/har-test',
    };

    await captureHar(options);

    expect(mockBrowserClose).toHaveBeenCalledOnce();
  });
});
