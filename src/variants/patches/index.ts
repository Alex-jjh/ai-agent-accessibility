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
import type { VariantLevel, DomChange, VariantDiff, VariantSpec } from '../types.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

/** Cache loaded JS scripts to avoid repeated disk reads */
const scriptCache = new Map<string, string>();

/**
 * Load a variant injection script from the inject/ directory.
 * Scripts are cached after first read.
 */
function loadInjectScript(
  name: 'low' | 'medium-low' | 'high' | 'pure-semantic-low' | 'all-individual',
): string {
  const cached = scriptCache.get(name);
  if (cached) return cached;
  const filename = `apply-${name}.js`;
  const script = readFileSync(join(__dirname, 'inject', filename), 'utf-8');
  scriptCache.set(name, script);
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
 * AMT individual-mode (v8, Task A.4): apply a selected subset of the
 * 26 operators. The `apply-all-individual.js` artefact reads
 * `window.__OPERATOR_IDS` to decide which operators to run; we set
 * that global first, then evaluate the artefact.
 *
 * Strict mode is enabled so that typos in operator IDs throw inside
 * the page — surfacing config errors immediately rather than silently
 * producing a no-op.
 *
 * See docs/amt-operator-spec.md §8 for the runtime protocol.
 */
async function applyIndividual(page: Page, operatorIds: string[]): Promise<DomChange[]> {
  await page.evaluate(
    ([ids]) => {
      (window as unknown as { __OPERATOR_IDS: string[] }).__OPERATOR_IDS = ids;
      (window as unknown as { __OPERATOR_STRICT: boolean }).__OPERATOR_STRICT = true;
    },
    [operatorIds],
  );
  const script = loadInjectScript('all-individual');
  const result = await page.evaluate(script);
  if (!Array.isArray(result)) {
    throw new Error(
      `applyIndividual: apply-all-individual.js returned non-array (${typeof result}). ` +
        `Operator IDs: ${JSON.stringify(operatorIds)}`,
    );
  }
  return result as DomChange[];
}

/**
 * Apply a DOM variant to a Playwright page (composite-mode convenience
 * wrapper). Preserved unchanged for all legacy callers and the 5 frozen
 * composite variant levels that produced the N=1,040 baseline.
 *
 * New callers that need AMT v8 individual-mode operator injection
 * should use `applyVariantSpec` instead.
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
  return applyVariantSpec(page, { kind: 'composite', level }, appName);
}

/**
 * Apply a DOM variant to a Playwright page, supporting both legacy
 * composite levels and AMT v8 individual-mode operator injection.
 *
 * See docs/amt-operator-spec.md §8 for the individual-mode runtime
 * protocol. Composite mode is unchanged from the pre-v8 pipeline.
 *
 * @param page - Playwright Page instance
 * @param spec - Composite level (one of 5) OR individual operator ID list
 * @param appName - WebArena app name (reddit, gitlab, cms, ecommerce)
 * @returns VariantDiff with all recorded changes and DOM hashes.
 *          For individual mode, VariantDiff.variantLevel is set to 'low'
 *          as a least-surprising placeholder (individual operators derive
 *          from the Low family design goal — degradation) and
 *          VariantDiff.operatorIds records the actual spec. Downstream
 *          analysis should key on operatorIds, not variantLevel, for
 *          individual-mode runs.
 */
export async function applyVariantSpec(
  page: Page,
  spec: VariantSpec,
  appName: string,
): Promise<VariantDiff> {
  // Compute DOM hash before manipulation
  const domHashBefore = await computeDomHash(page);

  let changes: DomChange[];
  let recordedLevel: VariantLevel;
  let recordedOperatorIds: string[] | undefined;

  if (spec.kind === 'composite') {
    recordedLevel = spec.level;
    switch (spec.level) {
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
      default: {
        // Exhaustiveness guard — TS should prevent this at compile time
        const _exhaustive: never = spec.level;
        void _exhaustive;
        changes = [];
      }
    }
  } else {
    // kind === 'individual'
    recordedLevel = 'low'; // see VariantDiff docstring above for rationale
    recordedOperatorIds = [...spec.operatorIds];
    changes = await applyIndividual(page, spec.operatorIds);
  }

  // Compute DOM hash after manipulation
  const domHashAfter = await computeDomHash(page);

  return {
    variantLevel: recordedLevel,
    appName,
    changes,
    domHashBefore,
    domHashAfter,
    ...(recordedOperatorIds !== undefined ? { operatorIds: recordedOperatorIds } : {}),
  };
}
