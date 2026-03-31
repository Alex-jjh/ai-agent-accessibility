// Module 1: Scanner — Tier 1 Scanner (axe-core + Lighthouse)
// Requirements: 1.1, 1.2, 1.3, 1.4, 1.5

import type { Page } from 'playwright';
import type {
  Tier1Metrics,
  Tier1ScanOptions,
  AxeCoreResult,
  AxeViolation,
  LighthouseResult,
} from '../types.js';

/** Map user-facing WCAG levels to axe-core tag names */
const WCAG_LEVEL_TAGS: Record<string, string> = {
  A: 'wcag2a',
  AA: 'wcag2aa',
  AAA: 'wcag2aaa',
};

/** Default empty axe-core result for when scanning fails */
function emptyAxeResult(): AxeCoreResult {
  return {
    violationCount: 0,
    violationsByWcagCriterion: {},
    impactSeverity: { critical: 0, serious: 0, moderate: 0, minor: 0 },
  };
}

/** Default empty Lighthouse result for when scanning fails */
function emptyLighthouseResult(): LighthouseResult {
  return {
    accessibilityScore: 0,
    audits: {},
  };
}

/**
 * Run axe-core analysis on the given page.
 * Returns structured AxeCoreResult with violations grouped by WCAG criterion.
 */
async function runAxeCore(
  page: Page,
  wcagLevels: ('A' | 'AA' | 'AAA')[]
): Promise<AxeCoreResult> {
  // Dynamic import to avoid top-level ESM issues
  const { AxeBuilder } = await import('@axe-core/playwright');

  const tags = wcagLevels.map((level) => WCAG_LEVEL_TAGS[level]).filter(Boolean);
  const results = await new AxeBuilder({ page }).withTags(tags).analyze();

  const impactSeverity: AxeCoreResult['impactSeverity'] = {
    critical: 0,
    serious: 0,
    moderate: 0,
    minor: 0,
  };
  const violationsByWcagCriterion: Record<string, AxeViolation[]> = {};

  for (const violation of results.violations) {
    const impact = (violation.impact ?? 'minor') as AxeViolation['impact'];
    impactSeverity[impact] += 1;

    const axeViolation: AxeViolation = {
      id: violation.id,
      impact,
      description: violation.description,
      helpUrl: violation.helpUrl,
      nodes: violation.nodes.length,
    };

    // Group by WCAG criterion from tags (e.g. "wcag412" → "4.1.2")
    const wcagTags = (violation.tags ?? []).filter((t: string) =>
      /^wcag\d+$/.test(t)
    );

    if (wcagTags.length === 0) {
      // No specific WCAG criterion — file under "other"
      const key = 'other';
      if (!violationsByWcagCriterion[key]) violationsByWcagCriterion[key] = [];
      violationsByWcagCriterion[key].push(axeViolation);
    } else {
      for (const tag of wcagTags) {
        const criterion = parseWcagTag(tag);
        if (!violationsByWcagCriterion[criterion])
          violationsByWcagCriterion[criterion] = [];
        violationsByWcagCriterion[criterion].push(axeViolation);
      }
    }
  }

  return {
    violationCount: results.violations.length,
    violationsByWcagCriterion,
    impactSeverity,
  };
}

/**
 * Parse an axe-core WCAG tag like "wcag412" into dotted form "4.1.2".
 * Falls back to returning the raw tag if it doesn't match the expected pattern.
 */
function parseWcagTag(tag: string): string {
  // axe-core tags: "wcag111" → "1.1.1", "wcag412" → "4.1.2"
  const match = tag.match(/^wcag(\d)(\d)(\d+)$/);
  if (!match) return tag;
  return `${match[1]}.${match[2]}.${match[3]}`;
}

/**
 * Run Lighthouse accessibility audit on the given page.
 * Lighthouse needs a raw CDP port to connect. We try multiple strategies:
 * 1. Use an explicit port passed via options
 * 2. Extract from browser wsEndpoint (available when using launchServer)
 * 3. Create a temporary CDP session and query the browser version endpoint
 * If none work, Lighthouse is skipped gracefully (Req 1.4).
 */
async function runLighthouse(page: Page, url: string, cdpPort?: number): Promise<LighthouseResult> {
  const lighthouse = (await import('lighthouse')).default;

  let port = cdpPort;

  if (!port) {
    // Try extracting from browser wsEndpoint
    const browser = page.context().browser();
    if (browser) {
      const wsEndpoint = (browser as any).wsEndpoint?.() as string | undefined;
      if (wsEndpoint) {
        const match = wsEndpoint.match(/:(\d+)\//);
        if (match) port = parseInt(match[1], 10);
      }
    }
  }

  if (!port) {
    // Try getting debugger URL via CDP
    try {
      const cdpSession = await page.context().newCDPSession(page);
      const { webSocketDebuggerUrl } = await cdpSession.send('Browser.getVersion' as any) as any;
      if (webSocketDebuggerUrl) {
        const match = (webSocketDebuggerUrl as string).match(/:(\d+)\//);
        if (match) port = parseInt(match[1], 10);
      }
      await cdpSession.detach();
    } catch {
      // CDP approach failed
    }
  }

  if (!port) {
    throw new Error('Could not determine browser CDP port for Lighthouse');
  }

  const result = await lighthouse(
    url,
    {
      onlyCategories: ['accessibility'],
      output: 'json',
      logLevel: 'error' as const,
      port,
    },
  );

  if (!result?.lhr) {
    return emptyLighthouseResult();
  }

  const lhr = result.lhr;
  const accessibilityScore = Math.round(
    (lhr.categories?.accessibility?.score ?? 0) * 100
  );

  const audits: LighthouseResult['audits'] = {};
  if (lhr.audits) {
    for (const [auditId, audit] of Object.entries(lhr.audits)) {
      audits[auditId] = {
        pass: audit.score === 1,
        details: audit.details ?? undefined,
      };
    }
  }

  return { accessibilityScore, audits };
}

/**
 * Scan a page using both axe-core and Lighthouse (Tier 1).
 *
 * Uses Promise.allSettled() so one tool's failure doesn't block the other (Req 1.4).
 * Logs errors with URL and tool name on failure, continues processing.
 *
 * @param page - Playwright Page object (must be navigated to the target URL)
 * @param options - Scan options including URL and WCAG conformance levels
 * @returns Tier1Metrics with results from both tools (empty defaults on failure)
 */
export async function scanTier1(
  page: Page,
  options: Tier1ScanOptions
): Promise<Tier1Metrics> {
  const { url, wcagLevels, lighthouseCdpPort } = options;

  // Run both tools concurrently — neither blocks the other (Req 1.4)
  const [axeSettled, lighthouseSettled] = await Promise.allSettled([
    runAxeCore(page, wcagLevels),
    runLighthouse(page, url, lighthouseCdpPort),
  ]);

  let axeCore: AxeCoreResult;
  if (axeSettled.status === 'fulfilled') {
    axeCore = axeSettled.value;
  } else {
    console.error(
      `[Scanner] axe-core failed for URL "${url}":`,
      axeSettled.reason
    );
    axeCore = emptyAxeResult();
  }

  let lighthouse: LighthouseResult;
  if (lighthouseSettled.status === 'fulfilled') {
    lighthouse = lighthouseSettled.value;
  } else {
    console.error(
      `[Scanner] Lighthouse failed for URL "${url}":`,
      lighthouseSettled.reason
    );
    lighthouse = emptyLighthouseResult();
  }

  return {
    url,
    axeCore,
    lighthouse,
    scannedAt: new Date().toISOString(),
  };
}
