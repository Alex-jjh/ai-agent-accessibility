/**
 * Unit tests for HAR Replay module.
 * Tests: request classification, coverage gap computation, low-fidelity flagging,
 * and replay session creation.
 * Requirements: 12.1–12.5
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { classifyRequest, computeCoverageGap, createReplaySession } from './replay.js';
import type { Browser } from 'playwright';

describe('classifyRequest', () => {
  it('should classify analytics domains as non-functional', () => {
    expect(classifyRequest('https://www.google-analytics.com/collect')).toBe('non-functional');
    expect(classifyRequest('https://www.googletagmanager.com/gtag/js')).toBe('non-functional');
    expect(classifyRequest('https://stats.doubleclick.net/pixel')).toBe('non-functional');
    expect(classifyRequest('https://connect.facebook.net/en_US/fbevents.js')).toBe('non-functional');
  });

  it('should classify ad domains as non-functional', () => {
    expect(classifyRequest('https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js')).toBe('non-functional');
    expect(classifyRequest('https://www.googleadservices.com/pagead/conversion')).toBe('non-functional');
    expect(classifyRequest('https://ib.adnxs.com/bounce')).toBe('non-functional');
  });

  it('should classify tracking domains as non-functional', () => {
    expect(classifyRequest('https://cdn.segment.com/analytics.js')).toBe('non-functional');
    expect(classifyRequest('https://api.mixpanel.com/track')).toBe('non-functional');
    expect(classifyRequest('https://api.amplitude.com/2/httpapi')).toBe('non-functional');
    expect(classifyRequest('https://script.hotjar.com/modules')).toBe('non-functional');
  });

  it('should classify regular website URLs as functional', () => {
    expect(classifyRequest('https://example.com/index.html')).toBe('functional');
    expect(classifyRequest('https://cdn.example.com/app.js')).toBe('functional');
    expect(classifyRequest('https://api.example.com/data')).toBe('functional');
    expect(classifyRequest('https://example.com/styles.css')).toBe('functional');
  });

  it('should classify font and image CDN URLs as functional', () => {
    expect(classifyRequest('https://fonts.googleapis.com/css2')).toBe('functional');
    expect(classifyRequest('https://cdn.example.com/logo.png')).toBe('functional');
  });

  it('should treat unparseable URLs as functional (conservative)', () => {
    expect(classifyRequest('not-a-url')).toBe('functional');
    expect(classifyRequest('')).toBe('functional');
  });
});

describe('computeCoverageGap', () => {
  it('should return 0 when all functional requests are matched', () => {
    expect(computeCoverageGap(10, 0)).toBe(0);
  });

  it('should return 1 when no functional requests are matched', () => {
    expect(computeCoverageGap(10, 10)).toBe(1);
  });

  it('should return correct ratio for partial matches', () => {
    expect(computeCoverageGap(20, 5)).toBe(0.25);
    expect(computeCoverageGap(100, 15)).toBe(0.15);
  });

  it('should return 0 when there are no functional requests at all', () => {
    expect(computeCoverageGap(0, 0)).toBe(0);
  });

  it('should flag as low fidelity when gap exceeds 20%', () => {
    const gap = computeCoverageGap(10, 3); // 30%
    expect(gap).toBeGreaterThan(0.20);
  });

  it('should not flag as low fidelity when gap is at or below 20%', () => {
    const gap = computeCoverageGap(10, 2); // exactly 20%
    expect(gap).toBeLessThanOrEqual(0.20);
  });
});

describe('createReplaySession', () => {
  const mockRouteFromHAR = vi.fn().mockResolvedValue(undefined);
  const mockRoute = vi.fn().mockResolvedValue(undefined);
  let requestListeners: Array<(req: { url: () => string }) => void>;
  const mockOn = vi.fn().mockImplementation((event: string, handler: (...args: unknown[]) => void) => {
    if (event === 'request') {
      requestListeners.push(handler as (req: { url: () => string }) => void);
    }
  });
  const mockPage = {
    routeFromHAR: mockRouteFromHAR,
    route: mockRoute,
    on: mockOn,
  };
  const mockContextClose = vi.fn().mockResolvedValue(undefined);
  const mockNewPage = vi.fn().mockResolvedValue(mockPage);
  const mockNewContext = vi.fn().mockResolvedValue({
    newPage: mockNewPage,
    close: mockContextClose,
  });
  const mockBrowser = {
    newContext: mockNewContext,
  } as unknown as Browser;

  beforeEach(() => {
    vi.clearAllMocks();
    requestListeners = [];
    mockOn.mockImplementation((event: string, handler: (...args: unknown[]) => void) => {
      if (event === 'request') {
        requestListeners.push(handler as (req: { url: () => string }) => void);
      }
    });
    mockNewPage.mockResolvedValue(mockPage);
    mockNewContext.mockResolvedValue({
      newPage: mockNewPage,
      close: mockContextClose,
    });
  });

  it('should create a replay session with routeFromHAR', async () => {
    const session = await createReplaySession(mockBrowser, {
      harFilePath: '/path/to/recording.har',
      unmatchedRequestBehavior: 'return-404',
    });

    expect(mockRouteFromHAR).toHaveBeenCalledWith('/path/to/recording.har', {
      notFound: 'abort',
    });
    expect(session.page).toBeDefined();
  });

  it('should use fallback mode when unmatchedRequestBehavior is passthrough', async () => {
    await createReplaySession(mockBrowser, {
      harFilePath: '/path/to/recording.har',
      unmatchedRequestBehavior: 'passthrough',
    });

    expect(mockRouteFromHAR).toHaveBeenCalledWith('/path/to/recording.har', {
      notFound: 'fallback',
    });
  });

  it('should register a fallback route for unmatched requests', async () => {
    await createReplaySession(mockBrowser, {
      harFilePath: '/path/to/recording.har',
      unmatchedRequestBehavior: 'return-404',
    });

    expect(mockRoute).toHaveBeenCalledWith('**/*', expect.any(Function));
  });

  it('should start with empty unmatched arrays and zero coverage gap', async () => {
    const session = await createReplaySession(mockBrowser, {
      harFilePath: '/path/to/recording.har',
      unmatchedRequestBehavior: 'return-404',
    });

    expect(session.functionalUnmatched).toEqual([]);
    expect(session.nonFunctionalUnmatched).toEqual([]);
    expect(session.totalUnmatched).toEqual([]);
    expect(session.coverageGap).toBe(0);
    expect(session.isLowFidelity).toBe(false);
  });

  it('should track unmatched requests via the fallback route handler', async () => {
    const session = await createReplaySession(mockBrowser, {
      harFilePath: '/path/to/recording.har',
      unmatchedRequestBehavior: 'return-404',
    });

    // Simulate requests coming through the request listener
    for (const listener of requestListeners) {
      listener({ url: () => 'https://example.com/page.html' });
      listener({ url: () => 'https://example.com/app.js' });
      listener({ url: () => 'https://www.google-analytics.com/collect' });
    }

    // Simulate an unmatched functional request hitting the fallback route
    const fallbackHandler = mockRoute.mock.calls[0][1] as (route: {
      request: () => { url: () => string };
      fulfill: (opts: unknown) => Promise<void>;
    }) => Promise<void>;

    const mockFulfill = vi.fn().mockResolvedValue(undefined);
    await fallbackHandler({
      request: () => ({ url: () => 'https://example.com/missing.js' }),
      fulfill: mockFulfill,
    });

    expect(session.functionalUnmatched).toContain('https://example.com/missing.js');
    expect(session.totalUnmatched).toContain('https://example.com/missing.js');
    expect(mockFulfill).toHaveBeenCalledWith({
      status: 404,
      contentType: 'text/plain',
      body: 'HAR replay: no matching entry',
    });
  });

  it('should classify unmatched analytics requests as non-functional', async () => {
    const session = await createReplaySession(mockBrowser, {
      harFilePath: '/path/to/recording.har',
      unmatchedRequestBehavior: 'return-404',
    });

    const fallbackHandler = mockRoute.mock.calls[0][1] as (route: {
      request: () => { url: () => string };
      fulfill: (opts: unknown) => Promise<void>;
    }) => Promise<void>;

    const mockFulfill = vi.fn().mockResolvedValue(undefined);
    await fallbackHandler({
      request: () => ({ url: () => 'https://www.google-analytics.com/collect?v=1' }),
      fulfill: mockFulfill,
    });

    expect(session.nonFunctionalUnmatched).toContain('https://www.google-analytics.com/collect?v=1');
    expect(session.functionalUnmatched).toHaveLength(0);
  });
});
