// Unit tests for A11y Tree Stability Detector
// Requirements: 3.1, 3.2, 3.3, 3.4

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { waitForA11yTreeStable } from './stability.js';

/** Helper to create a mock Playwright Page */
function createMockPage(snapshotSequence: (string | Error)[]) {
  let callIndex = 0;
  const locatorMock = {
    ariaSnapshot: vi.fn(async () => {
      if (callIndex >= snapshotSequence.length) {
        // Repeat last value if we exceed the sequence
        const last = snapshotSequence[snapshotSequence.length - 1];
        if (last instanceof Error) throw last;
        return last;
      }
      const value = snapshotSequence[callIndex++];
      if (value instanceof Error) throw value;
      return value;
    }),
  };

  return {
    locator: vi.fn(() => locatorMock),
    url: vi.fn(() => 'https://example.com'),
    _locatorMock: locatorMock,
  } as unknown as import('playwright').Page;
}

describe('waitForA11yTreeStable', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('returns stable when two consecutive snapshots match (Req 3.2)', async () => {
    const page = createMockPage([
      '- heading "Hello"',
      '- heading "Hello"',
    ]);

    const result = await waitForA11yTreeStable(page, {
      intervalMs: 10,
      timeoutMs: 5000,
    });

    expect(result.stable).toBe(true);
    expect(result.attempts).toBe(2);
    expect(result.snapshot).toEqual({ ariaTree: '- heading "Hello"' });
    expect(result.stabilizationMs).toBeGreaterThanOrEqual(0);
  });

  it('returns stable after initial instability then stabilization', async () => {
    const page = createMockPage([
      '- heading "Loading..."',
      '- heading "Hello"',
      '- heading "Hello"',
    ]);

    const result = await waitForA11yTreeStable(page, {
      intervalMs: 10,
      timeoutMs: 5000,
    });

    expect(result.stable).toBe(true);
    expect(result.attempts).toBe(3);
    expect(result.snapshot).toEqual({ ariaTree: '- heading "Hello"' });
  });

  it('returns unstable with latest snapshot on timeout (Req 3.3)', async () => {
    // Each snapshot is different — never stabilizes
    let counter = 0;
    const page = createMockPage([]);
    // Override ariaSnapshot to always return unique values
    const locatorMock = (page as unknown as { _locatorMock: { ariaSnapshot: ReturnType<typeof vi.fn> } })._locatorMock;
    locatorMock.ariaSnapshot.mockImplementation(async () => `- heading "v${counter++}"`);

    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    const result = await waitForA11yTreeStable(page, {
      intervalMs: 10,
      timeoutMs: 50,
    });

    expect(result.stable).toBe(false);
    expect(result.attempts).toBeGreaterThanOrEqual(1);
    expect(result.snapshot).toBeDefined();
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining('did not stabilize'),
    );
  });

  it('uses default options when none provided', async () => {
    const page = createMockPage([
      '- heading "Stable"',
      '- heading "Stable"',
    ]);

    const result = await waitForA11yTreeStable(page);

    expect(result.stable).toBe(true);
    expect(result.attempts).toBe(2);
  });

  it('handles snapshot errors gracefully (log and continue)', async () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const page = createMockPage([
      new Error('Page crashed'),
      '- heading "Recovered"',
      '- heading "Recovered"',
    ]);

    const result = await waitForA11yTreeStable(page, {
      intervalMs: 10,
      timeoutMs: 5000,
    });

    expect(result.stable).toBe(true);
    expect(result.attempts).toBe(3);
    expect(errorSpy).toHaveBeenCalledWith(
      expect.stringContaining('Failed to take A11y tree snapshot'),
    );
  });

  it('respects maxRetries option', async () => {
    let counter = 0;
    const page = createMockPage([]);
    const locatorMock = (page as unknown as { _locatorMock: { ariaSnapshot: ReturnType<typeof vi.fn> } })._locatorMock;
    locatorMock.ariaSnapshot.mockImplementation(async () => `- heading "v${counter++}"`);

    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    const result = await waitForA11yTreeStable(page, {
      intervalMs: 10,
      timeoutMs: 60000, // large timeout
      maxRetries: 3,
    });

    expect(result.stable).toBe(false);
    expect(result.attempts).toBe(3);
    expect(warnSpy).toHaveBeenCalled();
  });

  it('serializes the snapshot used for measurement (Req 3.4)', async () => {
    const yamlContent = '- list "Nav":\n  - listitem:\n    - link "Home"';
    const page = createMockPage([yamlContent, yamlContent]);

    const result = await waitForA11yTreeStable(page, {
      intervalMs: 10,
      timeoutMs: 5000,
    });

    expect(result.stable).toBe(true);
    expect(result.snapshot).toEqual({ ariaTree: yamlContent });
  });

  it('polls at the configured interval (Req 3.1)', async () => {
    const timestamps: number[] = [];
    const page = createMockPage([]);
    const locatorMock = (page as unknown as { _locatorMock: { ariaSnapshot: ReturnType<typeof vi.fn> } })._locatorMock;
    let counter = 0;
    locatorMock.ariaSnapshot.mockImplementation(async () => {
      timestamps.push(Date.now());
      // Return same value on 2nd and 3rd call to stabilize
      if (counter >= 1) return '- heading "Stable"';
      counter++;
      return `- heading "v${counter}"`;
    });

    const intervalMs = 50;
    await waitForA11yTreeStable(page, {
      intervalMs,
      timeoutMs: 5000,
    });

    // Check that there's roughly an interval gap between polls
    if (timestamps.length >= 3) {
      const gap = timestamps[2] - timestamps[1];
      expect(gap).toBeGreaterThanOrEqual(intervalMs - 15); // allow some timing slack
    }
  });
});
