#!/usr/bin/env npx tsx
/**
 * Ecological validity audit scanner.
 * Scans 30+ real websites × 3 pages each with axe-core + custom checks.
 *
 * Usage:
 *   npx tsx scan.ts                        # scan all public sites
 *   npx tsx scan.ts --site amazon          # scan single site
 *   npx tsx scan.ts --site amazon,jd       # scan multiple sites
 *   npx tsx scan.ts --resume               # skip sites with existing results
 *   npx tsx scan.ts --include-internal     # include WebArena sites (EC2 only)
 *   npx tsx scan.ts --local ./html-snapshots # scan local HTML snapshots
 */

import { chromium, type Page, type Browser, type BrowserContext } from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import { writeFileSync, mkdirSync, existsSync, readFileSync, readdirSync } from 'fs';
import { join, resolve, basename, dirname } from 'path';
import { SITES, type SiteConfig, type SitePage, type LoginConfig } from './config.js';
import { CUSTOM_CHECK_SCRIPT, type CustomCheckResults } from './custom-checks.js';

// ── Types ──

interface PageResult {
  label: string;
  url: string;
  actualUrl: string;
  scanTime: string;
  loadTimeMs: number;
  axe: {
    violations: Array<{
      id: string;
      impact: string | null;
      description: string;
      nodes: number;
      tags: string[];
    }>;
    passes: number;
    incomplete: number;
    inapplicable: number;
  };
  custom: CustomCheckResults;
  error?: string;
  /** "live" for real-time scan, "local-snapshot" for HTML file scan */
  source?: string;
}

interface SiteResult {
  name: string;
  category: string;  // site category or 'local-snapshot'
  scanDate: string;
  pages: PageResult[];
}

// ── Config ──

const RESULTS_DIR = join(import.meta.dirname || '.', 'results');
const NAV_TIMEOUT = 30_000;
const EXTRA_WAIT = 2_000; // wait for lazy-loaded content
const USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';

// ── Helpers ──

function parseArgs(): { sites: string[]; resume: boolean; includeInternal: boolean; localDir: string | null } {
  const args = process.argv.slice(2);
  let sites: string[] = [];
  let resume = false;
  let includeInternal = false;
  let localDir: string | null = null;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--site' && args[i + 1]) {
      sites = args[i + 1].split(',').map(s => s.trim());
      i++;
    }
    if (args[i] === '--resume') resume = true;
    if (args[i] === '--include-internal') includeInternal = true;
    if (args[i] === '--local' && args[i + 1]) {
      localDir = args[i + 1];
      i++;
    }
  }
  return { sites, resume, includeInternal, localDir };
}

async function scanPage(page: Page, sp: SitePage): Promise<PageResult> {
  const start = Date.now();
  let error: string | undefined;

  try {
    await page.goto(sp.url, { waitUntil: 'networkidle', timeout: NAV_TIMEOUT });
  } catch (e: any) {
    // Some sites block networkidle — fall back to domcontentloaded
    try {
      await page.goto(sp.url, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
      error = `networkidle timeout, fell back to domcontentloaded`;
    } catch (e2: any) {
      return {
        label: sp.label,
        url: sp.url,
        actualUrl: page.url(),
        scanTime: new Date().toISOString(),
        loadTimeMs: Date.now() - start,
        axe: { violations: [], passes: 0, incomplete: 0, inapplicable: 0 },
        custom: {} as CustomCheckResults,
        error: `Navigation failed: ${e2.message?.slice(0, 200)}`,
      };
    }
  }

  // Extra wait for lazy-loaded content / SPA hydration
  await page.waitForTimeout(EXTRA_WAIT);

  // Dismiss cookie banners (best-effort)
  try {
    const cookieSelectors = [
      'button:has-text("Accept")',
      'button:has-text("Accept All")',
      'button:has-text("I agree")',
      'button:has-text("OK")',
      'button:has-text("同意")',
      'button:has-text("接受")',
      '[id*="cookie"] button',
      '[class*="cookie"] button',
      '[id*="consent"] button',
      '[class*="consent"] button',
    ];
    for (const sel of cookieSelectors) {
      const btn = page.locator(sel).first();
      if (await btn.isVisible({ timeout: 500 }).catch(() => false)) {
        await btn.click({ timeout: 1000 }).catch(() => {});
        await page.waitForTimeout(500);
        break;
      }
    }
  } catch { /* ignore */ }

  const loadTimeMs = Date.now() - start;

  // axe-core scan
  let axeResult;
  try {
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'])
      .analyze();

    axeResult = {
      violations: results.violations.map(v => ({
        id: v.id,
        impact: v.impact ?? null,
        description: v.description,
        nodes: v.nodes.length,
        tags: v.tags,
      })),
      passes: results.passes.length,
      incomplete: results.incomplete.length,
      inapplicable: results.inapplicable.length,
    };
  } catch (e: any) {
    axeResult = { violations: [], passes: 0, incomplete: 0, inapplicable: 0 };
    error = (error ? error + '; ' : '') + `axe-core error: ${e.message?.slice(0, 200)}`;
  }

  // Custom checks
  let custom: CustomCheckResults;
  try {
    custom = await page.evaluate(CUSTOM_CHECK_SCRIPT) as CustomCheckResults;
  } catch (e: any) {
    custom = {} as CustomCheckResults;
    error = (error ? error + '; ' : '') + `custom check error: ${e.message?.slice(0, 200)}`;
  }

  return {
    label: sp.label,
    url: sp.url,
    actualUrl: page.url(),
    scanTime: new Date().toISOString(),
    loadTimeMs,
    axe: axeResult,
    custom,
    error,
  };
}

/**
 * Perform browser-based login for sites that require authentication (e.g. Magento admin).
 * Navigates to loginUrl, fills the form, submits, and waits for successSelector.
 */
async function performLogin(context: BrowserContext, login: LoginConfig): Promise<void> {
  const page = await context.newPage();
  try {
    console.log(`  🔑 Logging in via ${login.loginUrl}`);
    await page.goto(login.loginUrl, { waitUntil: 'networkidle', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(1000);

    // Fill form fields
    for (const [name, value] of Object.entries(login.formData)) {
      const input = page.locator(`input[name="${name}"]`);
      if (await input.isVisible({ timeout: 3000 }).catch(() => false)) {
        await input.fill(value);
      }
    }

    // Submit — try the submit button, fall back to Enter key
    const submitBtn = page.locator('button[type="submit"], input[type="submit"], .action-login').first();
    if (await submitBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await submitBtn.click();
    } else {
      await page.keyboard.press('Enter');
    }

    // Wait for login to complete
    if (login.successSelector) {
      await page.waitForSelector(login.successSelector, { timeout: 15_000 }).catch(() => {
        console.log(`    ⚠ Login success selector not found, continuing anyway`);
      });
    } else {
      await page.waitForTimeout(3000);
    }

    console.log(`    ✓ Login complete (URL: ${page.url()})`);
  } finally {
    await page.close();
  }
}

async function scanSite(site: SiteConfig, browser: Browser): Promise<SiteResult> {
  console.log(`\n━━━ Scanning: ${site.name} (${site.category}) ━━━`);

  const context: BrowserContext = await browser.newContext({
    userAgent: USER_AGENT,
    viewport: { width: 1920, height: 1080 },
    locale: 'en-US',
    timezoneId: 'America/New_York',
    // Bypass some anti-bot measures
    javaScriptEnabled: true,
    ignoreHTTPSErrors: true,
  });

  const pages: PageResult[] = [];

  // Perform login if required (e.g. Magento admin)
  if (site.login) {
    try {
      await performLogin(context, site.login);
    } catch (e: any) {
      console.log(`    ⚠ Login failed: ${e.message?.slice(0, 200)}`);
    }
  }

  for (const sp of site.pages) {
    // Skip pages that require authentication (login walls)
    if (sp.requiresAuth) {
      console.log(`  → ${sp.label}: ${sp.url} [SKIPPED — requires auth]`);
      pages.push({
        label: sp.label,
        url: sp.url,
        actualUrl: '',
        scanTime: new Date().toISOString(),
        loadTimeMs: 0,
        axe: { violations: [], passes: 0, incomplete: 0, inapplicable: 0 },
        custom: {} as CustomCheckResults,
        error: 'Skipped: requires authentication',
      });
      continue;
    }

    console.log(`  → ${sp.label}: ${sp.url}`);
    const page = await context.newPage();
    try {
      const result = await scanPage(page, sp);
      pages.push(result);

      const vCount = result.axe.violations.reduce((sum, v) => sum + v.nodes, 0);
      console.log(`    ✓ ${result.axe.violations.length} rules violated (${vCount} nodes), ${result.loadTimeMs}ms`);
      if (result.error) console.log(`    ⚠ ${result.error}`);
    } catch (e: any) {
      console.log(`    ✗ Fatal error: ${e.message?.slice(0, 200)}`);
      pages.push({
        label: sp.label,
        url: sp.url,
        actualUrl: '',
        scanTime: new Date().toISOString(),
        loadTimeMs: 0,
        axe: { violations: [], passes: 0, incomplete: 0, inapplicable: 0 },
        custom: {} as CustomCheckResults,
        error: `Fatal: ${e.message?.slice(0, 200)}`,
      });
    } finally {
      await page.close();
    }
  }

  await context.close();

  return {
    name: site.name,
    category: site.category,
    scanDate: new Date().toISOString(),
    pages,
  };
}

// ── Local HTML snapshot scanning ──

interface SnapshotMetadata {
  [filePath: string]: {
    originalUrl: string;
    savedAt: string;
    savedBy?: string;
    authenticated?: boolean;
    notes?: string;
  };
}

async function scanLocalDir(localDir: string): Promise<void> {
  const absDir = resolve(localDir);
  if (!existsSync(absDir)) {
    console.error(`Local directory not found: ${absDir}`);
    process.exit(1);
  }

  // Load metadata if present
  const metaPath = join(absDir, 'metadata.json');
  let metadata: SnapshotMetadata = {};
  if (existsSync(metaPath)) {
    metadata = JSON.parse(readFileSync(metaPath, 'utf-8'));
    console.log(`Loaded metadata for ${Object.keys(metadata).length} snapshots`);
  }

  // Discover site directories (each subdir = one site)
  const siteDirs = readdirSync(absDir, { withFileTypes: true })
    .filter(d => d.isDirectory())
    .map(d => d.name);

  if (siteDirs.length === 0) {
    console.error(`No site directories found in ${absDir}`);
    process.exit(1);
  }

  console.log(`Local mode: scanning ${siteDirs.length} sites from ${absDir}`);
  mkdirSync(RESULTS_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  let successCount = 0;

  for (const siteName of siteDirs) {
    const siteDir = join(absDir, siteName);
    const htmlFiles = readdirSync(siteDir).filter(f => f.endsWith('.html'));

    if (htmlFiles.length === 0) {
      console.log(`  ⚠ No HTML files in ${siteName}/, skipping`);
      continue;
    }

    console.log(`\n━━━ Scanning local: ${siteName} (${htmlFiles.length} pages) ━━━`);
    const context = await browser.newContext({ javaScriptEnabled: true });
    const pages: PageResult[] = [];

    for (const htmlFile of htmlFiles) {
      const label = basename(htmlFile, '.html');
      const filePath = join(siteDir, htmlFile);
      const fileUrl = `file://${resolve(filePath)}`;
      const metaKey = `${siteName}/${htmlFile}`;
      const meta = metadata[metaKey];

      console.log(`  → ${label}: ${fileUrl}`);
      if (meta) console.log(`    (original: ${meta.originalUrl}, saved: ${meta.savedAt})`);

      const page = await context.newPage();
      const start = Date.now();
      let error: string | undefined;

      try {
        await page.goto(fileUrl, { waitUntil: 'load', timeout: 15_000 });
        await page.waitForTimeout(1000);
      } catch (e: any) {
        error = `Local file load failed: ${e.message?.slice(0, 200)}`;
      }

      // axe-core scan
      let axeResult;
      try {
        const results = await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'])
          .analyze();
        axeResult = {
          violations: results.violations.map(v => ({
            id: v.id,
            impact: v.impact ?? null,
            description: v.description,
            nodes: v.nodes.length,
            tags: v.tags,
          })),
          passes: results.passes.length,
          incomplete: results.incomplete.length,
          inapplicable: results.inapplicable.length,
        };
      } catch (e: any) {
        axeResult = { violations: [], passes: 0, incomplete: 0, inapplicable: 0 };
        error = (error ? error + '; ' : '') + `axe-core error: ${e.message?.slice(0, 200)}`;
      }

      // Custom checks
      let custom: CustomCheckResults;
      try {
        custom = await page.evaluate(CUSTOM_CHECK_SCRIPT) as CustomCheckResults;
      } catch (e: any) {
        custom = {} as CustomCheckResults;
        error = (error ? error + '; ' : '') + `custom check error: ${e.message?.slice(0, 200)}`;
      }

      const vCount = axeResult.violations.reduce((sum, v) => sum + v.nodes, 0);
      console.log(`    ✓ ${axeResult.violations.length} rules violated (${vCount} nodes), ${Date.now() - start}ms`);
      if (error) console.log(`    ⚠ ${error}`);

      pages.push({
        label,
        url: meta?.originalUrl ?? fileUrl,
        actualUrl: fileUrl,
        scanTime: new Date().toISOString(),
        loadTimeMs: Date.now() - start,
        axe: axeResult,
        custom,
        source: 'local-snapshot',
        error,
      });

      await page.close();
    }

    await context.close();

    const result: SiteResult = {
      name: siteName,
      category: 'local-snapshot',
      scanDate: new Date().toISOString(),
      pages,
    };

    const outPath = join(RESULTS_DIR, `${siteName}.json`);
    writeFileSync(outPath, JSON.stringify(result, null, 2));
    successCount++;
  }

  await browser.close();
  console.log(`\n════════════════════════════════════════`);
  console.log(`Local scan complete: ${successCount}/${siteDirs.length} sites`);
  console.log(`Results saved to ${RESULTS_DIR}/`);
}

async function main() {
  const { sites: filterSites, resume, includeInternal, localDir } = parseArgs();

  // Local HTML snapshot mode — completely separate path
  if (localDir) {
    await scanLocalDir(localDir);
    return;
  }

  mkdirSync(RESULTS_DIR, { recursive: true });

  let sitesToScan = SITES;

  // Filter out internal-network sites unless --include-internal is passed
  // Exception: if --site explicitly names an internal site, include it
  if (!includeInternal && filterSites.length === 0) {
    const skipped = sitesToScan.filter(s => s.requiresInternalNetwork);
    if (skipped.length > 0) {
      console.log(`Skipping ${skipped.length} internal-network sites (use --include-internal to scan them)`);
    }
    sitesToScan = sitesToScan.filter(s => !s.requiresInternalNetwork);
  }

  if (filterSites.length > 0) {
    sitesToScan = SITES.filter(s => filterSites.includes(s.name));
    if (sitesToScan.length === 0) {
      console.error(`No matching sites found. Available: ${SITES.map(s => s.name).join(', ')}`);
      process.exit(1);
    }
  }

  if (resume) {
    sitesToScan = sitesToScan.filter(s => {
      const path = join(RESULTS_DIR, `${s.name}.json`);
      return !existsSync(path);
    });
    console.log(`Resume mode: ${sitesToScan.length} sites remaining`);
  }

  console.log(`Scanning ${sitesToScan.length} sites × 3 pages = ${sitesToScan.length * 3} page scans`);
  console.log(`Categories: ${[...new Set(sitesToScan.map(s => s.category))].join(', ')}`);

  const browser = await chromium.launch({
    headless: true,
    args: [
      '--disable-blink-features=AutomationControlled',
      '--no-sandbox',
    ],
  });

  const allResults: SiteResult[] = [];
  let successCount = 0;
  let errorCount = 0;

  for (const site of sitesToScan) {
    try {
      const result = await scanSite(site, browser);
      allResults.push(result);

      // Save per-site JSON immediately (crash-safe)
      const outPath = join(RESULTS_DIR, `${site.name}.json`);
      writeFileSync(outPath, JSON.stringify(result, null, 2));
      successCount++;
    } catch (e: any) {
      console.error(`  ✗ Site-level error for ${site.name}: ${e.message}`);
      errorCount++;
    }
  }

  await browser.close();

  // Write summary
  const summary = {
    scanDate: new Date().toISOString(),
    totalSites: sitesToScan.length,
    successfulSites: successCount,
    failedSites: errorCount,
    sites: allResults.map(r => ({
      name: r.name,
      category: r.category,
      pagesScanned: r.pages.length,
      totalViolations: r.pages.reduce(
        (sum, p) => sum + p.axe.violations.reduce((s, v) => s + v.nodes, 0), 0
      ),
      uniqueRules: [...new Set(r.pages.flatMap(p => p.axe.violations.map(v => v.id)))],
      errors: r.pages.filter(p => p.error).map(p => ({ page: p.label, error: p.error })),
    })),
  };

  writeFileSync(join(RESULTS_DIR, '_summary.json'), JSON.stringify(summary, null, 2));

  console.log(`\n════════════════════════════════════════`);
  console.log(`Scan complete: ${successCount}/${sitesToScan.length} sites`);
  console.log(`Results saved to ${RESULTS_DIR}/`);
  console.log(`Run 'python analysis.py' to generate the prevalence table.`);
}

main().catch(e => {
  console.error('Fatal error:', e);
  process.exit(1);
});
