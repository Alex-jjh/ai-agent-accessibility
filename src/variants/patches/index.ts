// Module 2: Variant Generator — DOM Patch Engine
// Requirements: 5.1, 5.2, 5.3, 5.4, 5.7, 6.1
//
// Applies deterministic DOM manipulations per variant level and records
// all changes as reversible DomChange[] entries with DOM hashes.
//
// Variant JS logic lives in inject/*.js — shared between this TypeScript
// module (Playwright page.evaluate) and the Python BrowserGym bridge.

import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { Page } from 'playwright';
import type { VariantLevel, DomChange, VariantDiff } from '../types.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

/** Cache loaded JS scripts to avoid repeated disk reads */
const scriptCache = new Map<string, string>();

/**
 * Load a variant injection script from the inject/ directory.
 * Scripts are cached after first read.
 */
function loadInjectScript(level: 'low' | 'medium-low' | 'high' | 'pure-semantic-low'): string {
  const cached = scriptCache.get(level);
  if (cached) return cached;
  const filename = `apply-${level}.js`;
  const script = readFileSync(join(__dirname, 'inject', filename), 'utf-8');
  scriptCache.set(level, script);
  return script;
}

/**
 * Compute DOM hash inside the browser using djb2.
 * crypto.subtle is unavailable on HTTP (WebArena runs on HTTP).
 */
async function computeDomHash(page: Page): Promise<string> {
  return page.evaluate(() => {
    const html = document.documentElement.outerHTML;
    let hash = 5381;
    for (let i = 0; i < html.length; i++) {
      hash = ((hash << 5) + hash + html.charCodeAt(i)) >>> 0;
    }
    return hash.toString(16).padStart(8, '0');
  });
}

/**
 * Low variant (Level 0): Aggressively degrade accessibility. (Req 5.1)
 */
async function applyLow(page: Page): Promise<DomChange[]> {
  const script = loadInjectScript('low');
  return page.evaluate(script);
}

/**
 * Medium-Low variant (Level 1): Pseudo-compliance strategy. (Req 5.2)
 */
async function applyMediumLow(page: Page): Promise<DomChange[]> {
  const script = loadInjectScript('medium-low');
  return page.evaluate(script);
}

/**
 * High variant (Level 2): Enhance accessibility. (Req 5.4)
 */
async function applyHigh(page: Page): Promise<DomChange[]> {
  const script = loadInjectScript('high');
  return page.evaluate(script);
}

/**
 * Apply a DOM variant to a Playwright page.
 *
 * Deterministic for the same input DOM and variant level (Req 5.7).
 * Records all changes as reversible DomChange[] with original/modified
 * state and DOM hash before/after (Req 6.1).
 *
 * @param page - Playwright Page instance
 * @param level - Variant level to apply
 * @param appName - WebArena app name (reddit, gitlab, cms, ecommerce)
 * @returns VariantDiff with all recorded changes and DOM hashes
 */
export async function applyVariant(
  page: Page,
  level: VariantLevel,
  appName: string,
): Promise<VariantDiff> {
  // Compute DOM hash before manipulation
  const domHashBefore = await computeDomHash(page);

  let changes: DomChange[];

  switch (level) {
    case 'low':
      changes = await applyLow(page);
      break;
    case 'medium-low':
      changes = await applyMediumLow(page);
      break;
    case 'base':
      // No-op — return unmodified DOM with empty diff (Req 5.3)
      changes = [];
      break;
    case 'high':
      changes = await applyHigh(page);
      break;
    case 'pure-semantic-low': {
      const pslScript = loadInjectScript('pure-semantic-low');
      changes = await page.evaluate(pslScript);
      break;
    }
    default:
      changes = [];
      break;
  }

  // Compute DOM hash after manipulation
  const domHashAfter = await computeDomHash(page);

  return {
    variantLevel: level,
    appName,
    changes,
    domHashBefore,
    domHashAfter,
  };
}
