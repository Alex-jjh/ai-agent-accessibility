// Module 2: Variant Generator — DOM Reversal Engine
// Requirements: 6.1, 6.2, 6.3
//
// Restores DOM to its pre-manipulation state using a recorded VariantDiff.
// Iterates through changes in REVERSE order and undoes each change.
// Verifies restoration by comparing SHA-256 hash of the restored DOM
// against the original domHashBefore from the diff.

import type { Page } from 'playwright';
import type { VariantDiff, DomChange } from '../types.js';

/**
 * Compute hash of the serialized DOM inside the browser.
 * Uses djb2 hash instead of crypto.subtle because WebArena
 * runs on HTTP (not a secure context).
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
 * Revert a single DOM change by undoing the recorded modification.
 *
 * NOTE on 'remove-handler' changes: JavaScript event listeners added via
 * addEventListener() cannot be fully restored through DOM manipulation alone.
 * The original handler function references are lost once removed. This is a
 * known limitation — only inline handlers (onkeydown, etc.) stored in the
 * `original` field can be partially restored.
 */
function buildRevertScript(change: DomChange): string {
  const sel = JSON.stringify(change.selector);
  const original = JSON.stringify(change.original);
  const modified = JSON.stringify(change.modified);

  switch (change.changeType) {
    case 'replace':
      // Find the modified element and restore the original HTML.
      // The selector may be a data-variant-revert marker (from apply) or a tag-based selector.
      return `
        (() => {
          const el = document.querySelector(${sel});
          if (el) {
            const temp = document.createElement('template');
            temp.innerHTML = ${original};
            if (temp.content.firstElementChild) {
              el.replaceWith(temp.content.firstElementChild);
            }
          }
        })();
      `;

    case 'remove-attr':
      // Re-add the removed attribute. original is "attrName=\\"value\\""
      return `
        (() => {
          const el = document.querySelector(${sel});
          if (el) {
            const attrStr = ${original};
            const eqIdx = attrStr.indexOf('=');
            if (eqIdx !== -1) {
              const name = attrStr.substring(0, eqIdx);
              // Strip surrounding quotes from value
              let value = attrStr.substring(eqIdx + 1);
              if (value.startsWith('"') && value.endsWith('"')) {
                value = value.slice(1, -1);
              }
              el.setAttribute(name, value);
            }
          }
        })();
      `;

    case 'add-attr':
      // Remove the added attribute. modified is "attrName=\\"value\\""
      return `
        (() => {
          const el = document.querySelector(${sel});
          if (el) {
            const attrStr = ${modified};
            const eqIdx = attrStr.indexOf('=');
            if (eqIdx !== -1) {
              const name = attrStr.substring(0, eqIdx);
              el.removeAttribute(name);
            }
          }
        })();
      `;

    case 'remove-element':
      // Re-insert the removed element. original contains the element HTML.
      // We insert it at the location indicated by the selector.
      return `
        (() => {
          const temp = document.createElement('template');
          temp.innerHTML = ${original};
          const restored = temp.content.firstElementChild;
          if (restored) {
            // Try to find a logical insertion point using the selector
            const selector = ${sel};
            // For label[for="id"] selectors, insert before the associated input
            const forMatch = selector.match(/label\\[for="([^"]+)"\\]/);
            if (forMatch) {
              const input = document.getElementById(forMatch[1]);
              if (input && input.parentElement) {
                input.parentElement.insertBefore(restored, input);
                return;
              }
            }
            // Fallback: append to body
            document.body.appendChild(restored);
          }
        })();
      `;

    case 'add-element':
      // Remove the added element
      return `
        (() => {
          const el = document.querySelector(${sel});
          if (el) {
            el.remove();
          }
        })();
      `;

    case 'remove-handler':
      // JS event listeners cannot be fully restored via DOM manipulation alone.
      // We can only restore inline handlers if the original field contains them.
      return `
        (() => {
          const el = document.querySelector(${sel});
          if (el) {
            const attrStr = ${original};
            // Check if original is an inline handler like 'onkeydown="..."'
            const eqIdx = attrStr.indexOf('=');
            if (eqIdx !== -1) {
              const name = attrStr.substring(0, eqIdx);
              if (name.startsWith('on')) {
                let value = attrStr.substring(eqIdx + 1);
                if (value.startsWith('"') && value.endsWith('"')) {
                  value = value.slice(1, -1);
                }
                el.setAttribute(name, value);
              }
            }
            // NOTE: addEventListener-based handlers cannot be restored.
            // The original function references are lost once removed.
          }
        })();
      `;

    default:
      return '';
  }
}

/**
 * Revert all DOM changes from a VariantDiff, restoring the page to its
 * pre-manipulation state.
 *
 * Changes are applied in REVERSE order to correctly undo nested or
 * dependent modifications.
 *
 * After reversal, computes a SHA-256 hash of the DOM and compares it
 * with `diff.domHashBefore` to verify success (Req 6.3).
 *
 * @param page - Playwright Page instance
 * @param diff - The VariantDiff produced by applyVariant
 * @returns Object with success flag and the DOM hash after reversal
 */
export async function revertVariant(
  page: Page,
  diff: VariantDiff,
): Promise<{ success: boolean; domHashAfterRevert: string }> {
  // Iterate through changes in reverse order
  const reversedChanges = [...diff.changes].reverse();

  for (const change of reversedChanges) {
    const script = buildRevertScript(change);
    if (script) {
      await page.evaluate(script);
    }
  }

  // Compute DOM hash after reversal
  const domHashAfterRevert = await computeDomHash(page);

  // Verify restored DOM matches original (Req 6.3)
  const success = domHashAfterRevert === diff.domHashBefore;

  return { success, domHashAfterRevert };
}
