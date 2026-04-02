/**
 * HAR Replay Server — serves recorded HTTP responses via Playwright's routeFromHAR.
 * Intercepts unmatched requests (returns 404), classifies requests as functional vs
 * non-functional, computes coverage gap, and flags low-fidelity recordings.
 *
 * Requirements: 12.1, 12.2, 12.3, 12.4, 12.5
 */

import type { Browser, Page, Route } from 'playwright';
import type { HarReplayOptions, ReplaySession } from '../types.js';

/**
 * Domain patterns for non-functional requests (analytics, ads, tracking).
 * Matched against the hostname of each request URL.
 */
const NON_FUNCTIONAL_DOMAIN_PATTERNS: RegExp[] = [
  /google-analytics\.com$/,
  /googletagmanager\.com$/,
  /doubleclick\.net$/,
  /facebook\.com\/tr/,
  /facebook\.net$/,
  /fbcdn\.net$/,
  /hotjar\.com$/,
  /segment\.io$/,
  /segment\.com$/,
  /mixpanel\.com$/,
  /amplitude\.com$/,
  /sentry\.io$/,
  /newrelic\.com$/,
  /nr-data\.net$/,
  /optimizely\.com$/,
  /crazyegg\.com$/,
  /mouseflow\.com$/,
  /fullstory\.com$/,
  /heap\.io$/,
  /intercom\.io$/,
  /hubspot\.com$/,
  /marketo\.net$/,
  /ads-twitter\.com$/,
  /adsrvr\.org$/,
  /adnxs\.com$/,
  /rubiconproject\.com$/,
  /googlesyndication\.com$/,
  /googleadservices\.com$/,
];

/**
 * Functional resource content types / URL extensions.
 * If a request matches these, it's considered functional.
 */
const FUNCTIONAL_EXTENSIONS = new Set([
  '.html', '.htm', '.js', '.mjs', '.css', '.json', '.xml', '.woff', '.woff2', '.ttf', '.otf',
]);

/**
 * Classify a request URL as functional or non-functional.
 * Non-functional: analytics, ads, tracking (matched by domain patterns).
 * Functional: HTML, JS, CSS, API calls, fonts.
 */
export function classifyRequest(url: string): 'functional' | 'non-functional' {
  try {
    const parsed = new URL(url);
    const hostname = parsed.hostname;

    // Check against known non-functional domain patterns
    for (const pattern of NON_FUNCTIONAL_DOMAIN_PATTERNS) {
      if (pattern.test(hostname) || pattern.test(url)) {
        return 'non-functional';
      }
    }

    return 'functional';
  } catch {
    // If URL can't be parsed, treat as functional to be conservative
    return 'functional';
  }
}

/**
 * Compute coverage gap over functional requests only.
 * Returns a ratio 0.0–1.0 where 0 = all functional requests matched, 1 = none matched.
 */
export function computeCoverageGap(
  totalFunctionalRequests: number,
  unmatchedFunctionalRequests: number,
): number {
  if (totalFunctionalRequests === 0) return 0;
  return unmatchedFunctionalRequests / totalFunctionalRequests;
}

/**
 * Create a HAR replay session that serves recorded HTTP responses.
 *
 * Req 12.1: Serves recorded responses via Playwright's routeFromHAR.
 * Req 12.2: Intercepts all network requests and matches to HAR entries.
 * Req 12.3: Returns 404 for unmatched requests and logs them.
 * Req 12.4: Page behaves identically to live pages for Scanner/Agent_Runner.
 * Req 12.5: Flags recordings with >20% functional coverage gap as low fidelity.
 */
export async function createReplaySession(
  browser: Browser,
  options: HarReplayOptions,
): Promise<ReplaySession> {
  const context = await browser.newContext();
  const page: Page = await context.newPage();

  const functionalUnmatched: string[] = [];
  const nonFunctionalUnmatched: string[] = [];
  const totalUnmatched: string[] = [];
  let totalFunctionalRequests = 0;
  let totalNonFunctionalRequests = 0;

  // Track all requests to compute coverage
  page.on('request', (request) => {
    const url = request.url();
    const classification = classifyRequest(url);
    if (classification === 'functional') {
      totalFunctionalRequests++;
    } else {
      totalNonFunctionalRequests++;
    }
  });

  // Req 12.1, 12.2: Serve recorded responses from HAR.
  // Always use 'fallback' so unmatched requests fall through to our custom handler
  // which logs them and returns 404. Using 'abort' would skip our handler entirely,
  // making coverage tracking impossible.
  await page.routeFromHAR(options.harFilePath, {
    notFound: 'fallback',
  });

  // Req 12.3: Fallback route for unmatched requests — return 404 and log
  await page.route('**/*', async (route: Route) => {
    const url = route.request().url();
    const classification = classifyRequest(url);

    totalUnmatched.push(url);
    if (classification === 'functional') {
      functionalUnmatched.push(url);
    } else {
      nonFunctionalUnmatched.push(url);
    }

    console.warn(`[HAR Replay] Unmatched ${classification} request: ${url}`);

    await route.fulfill({
      status: 404,
      contentType: 'text/plain',
      body: 'HAR replay: no matching entry',
    });
  });

  // Compute coverage gap lazily — caller navigates the page, then reads the session fields.
  // We return a proxy-like object that computes gap on access.
  const session: ReplaySession = {
    page,
    get coverageGap() {
      return computeCoverageGap(totalFunctionalRequests, functionalUnmatched.length);
    },
    functionalUnmatched,
    nonFunctionalUnmatched,
    totalUnmatched,
    get isLowFidelity() {
      // Req 12.5: Flag as low fidelity if functional coverage gap > 20%
      return computeCoverageGap(totalFunctionalRequests, functionalUnmatched.length) > 0.20;
    },
  };

  return session;
}
