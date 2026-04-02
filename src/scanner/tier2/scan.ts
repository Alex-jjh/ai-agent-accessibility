// Module 1: Scanner — Tier 2 Scanner (CDP-based functional metrics)
// Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9

import type { Page, CDPSession } from 'playwright';
import type { Tier2Metrics } from '../types.js';

// --- Constants ---

/** Semantic HTML elements counted for Req 2.1 */
const SEMANTIC_ELEMENTS = [
  'nav', 'main', 'header', 'footer', 'article', 'section', 'aside',
  'figure', 'figcaption', 'details', 'summary', 'dialog', 'time', 'mark', 'address',
];

/** Interactive roles for accessible name coverage (Req 2.2) */
const INTERACTIVE_AX_ROLES = [
  'button', 'link', 'textbox', 'combobox', 'checkbox', 'radio',
  'slider', 'spinbutton', 'switch', 'tab', 'menuitem', 'menuitemcheckbox',
  'menuitemradio', 'searchbox', 'listbox', 'option', 'treeitem',
];

/** Landmark selectors for Req 2.7 */
const LANDMARK_SELECTORS = [
  '[role="banner"]', '[role="navigation"]', '[role="main"]', '[role="contentinfo"]',
  '[role="complementary"]', '[role="form"]', '[role="region"]', '[role="search"]',
  'nav', 'main', 'header', 'footer', 'aside',
  'form', 'section[aria-label]', 'section[aria-labelledby]',
];

/** Required ARIA properties per role (subset of WAI-ARIA 1.2 spec, Req 2.4) */
const REQUIRED_ARIA_PROPS: Record<string, string[]> = {
  checkbox: ['aria-checked'],
  combobox: ['aria-expanded'],
  heading: ['aria-level'],
  meter: ['aria-valuenow'],
  option: ['aria-selected'],
  progressbar: [],
  radio: ['aria-checked'],
  scrollbar: ['aria-controls', 'aria-valuenow'],
  separator: [],
  slider: ['aria-valuenow'],
  spinbutton: ['aria-valuenow'],
  switch: ['aria-checked'],
  tab: ['aria-selected'],
  treeitem: [],
};

/** Keyboard navigability safety limits (Req 2.3) */
const MAX_TAB_PRESSES = 200;
const KEYBOARD_TIMEOUT_MS = 30000;
const TRAP_THRESHOLD = 5; // consecutive same-element = trapped
const MAX_SHADOW_DEPTH = 10; // prevent infinite recursion in deep Shadow DOM

// --- Helper functions ---

/**
 * Clamp a value to the 0.0–1.0 range (Req 2.9).
 */
function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(1, value));
}

/**
 * Safe ratio: returns 0 when denominator is 0.
 */
function safeRatio(numerator: number, denominator: number): number {
  if (denominator === 0) return 0;
  return clamp01(numerator / denominator);
}

// --- Metric computation functions ---

/**
 * Req 2.1: Semantic HTML ratio.
 * Count of semantic elements / count of structural container elements.
 * Uses structural containers (div, section, article, nav, header, footer, aside, main)
 * as denominator instead of ALL elements, so the ratio is meaningful on real sites.
 * Traverses Shadow DOM when enabled (Req 2.8).
 */
async function computeSemanticHtmlRatio(
  page: Page,
  traverseShadowDOM: boolean,
): Promise<number> {
  const [semanticCount, structuralCount] = await page.evaluate(
    ({ semanticTags, traverseShadow, maxDepth }) => {
      // structuralTags: non-semantic container elements only (div, span).
      // Semantic elements (nav, main, etc.) are counted separately in semanticTags.
      // The ratio measures: semantic elements / (semantic + non-semantic containers).
      const nonSemanticContainers = ['div', 'span'];

      const collectElements = (root: Document | ShadowRoot, depth = 0): Element[] => {
        const elements = Array.from(root.querySelectorAll('*'));
        if (traverseShadow && depth < maxDepth) {
          for (const el of elements) {
            if (el.shadowRoot) {
              elements.push(...collectElements(el.shadowRoot, depth + 1));
            }
          }
        }
        return elements;
      };

      const allElements = collectElements(document);
      const nonSemantic = allElements.filter((el) =>
        nonSemanticContainers.includes(el.tagName.toLowerCase()),
      ).length;
      const semantic = allElements.filter((el) =>
        semanticTags.includes(el.tagName.toLowerCase()),
      ).length;
      return [semantic, semantic + nonSemantic];
    },
    { semanticTags: SEMANTIC_ELEMENTS, traverseShadow: traverseShadowDOM, maxDepth: MAX_SHADOW_DEPTH },
  );

  return safeRatio(semanticCount, structuralCount);
}

/**
 * Req 2.2: Accessible name coverage.
 * Proportion of interactive elements with a non-empty accessible name.
 * Uses CDP Accessibility.getFullAXTree().
 */
async function computeAccessibleNameCoverage(
  cdpSession: CDPSession,
): Promise<number> {
  const { nodes } = await cdpSession.send('Accessibility.getFullAXTree' as any);
  const axNodes = nodes as Array<{
    role?: { value?: string };
    name?: { value?: string };
    ignored?: boolean;
  }>;

  let interactiveCount = 0;
  let namedCount = 0;

  for (const node of axNodes) {
    if (node.ignored) continue;
    const role = node.role?.value?.toLowerCase();
    if (!role || !INTERACTIVE_AX_ROLES.includes(role)) continue;

    interactiveCount++;
    const name = node.name?.value?.trim();
    if (name && name.length > 0) {
      namedCount++;
    }
  }

  return safeRatio(namedCount, interactiveCount);
}

/**
 * Req 2.3: Keyboard navigability.
 * Programmatic Tab cycle with safety guards:
 * - Max 200 Tab presses
 * - 30s timeout
 * - Trap detection (5 consecutive same-element = trapped)
 */
async function computeKeyboardNavigability(page: Page): Promise<number> {
  // Count total focusable elements first
  const totalFocusable = await page.evaluate(() => {
    const focusableSelector =
      'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])';
    return document.querySelectorAll(focusableSelector).length;
  });

  if (totalFocusable === 0) return 0;

  // Use page.keyboard.press('Tab') — the real browser focus management —
  // instead of dispatchEvent which doesn't actually move focus.
  // Bug 4 fix: use a counter instead of a Set to avoid deduplicating
  // elements with identical tag/id/class (e.g. multiple bare <input>).
  let focusedCount = 0;
  let consecutiveSame = 0;
  let lastFingerprint = '';
  const startTime = Date.now();

  // Record the starting element
  const startInfo = await page.evaluate(() => {
    const el = document.activeElement;
    return { tag: el?.tagName?.toLowerCase() ?? '', id: el?.id ?? '' };
  });

  for (let tabCount = 0; tabCount < MAX_TAB_PRESSES; tabCount++) {
    // Timeout guard
    if (Date.now() - startTime > KEYBOARD_TIMEOUT_MS) break;

    await page.keyboard.press('Tab');

    // Check where focus landed — use a unique index stamped on the element
    // so we can distinguish between multiple elements with the same tag/id/class.
    const current = await page.evaluate((idx) => {
      const el = document.activeElement;
      if (!el || el === document.body) return null;
      // Stamp a unique data attribute if not already present
      if (!el.hasAttribute('data-kb-nav-idx')) {
        el.setAttribute('data-kb-nav-idx', String(idx));
      }
      return {
        tag: el.tagName.toLowerCase(),
        id: el.id ?? '',
        fingerprint: el.getAttribute('data-kb-nav-idx') ?? String(idx),
      };
    }, tabCount);

    if (!current) {
      // Focus went to body — cycle complete
      if (tabCount > 0) break;
      continue;
    }

    // Count this as a new focused element if it's different from the last
    if (current.fingerprint !== lastFingerprint) {
      focusedCount++;
    }

    // Trap detection: same element N times in a row
    const currentFingerprint = current.fingerprint;
    if (currentFingerprint === lastFingerprint) {
      consecutiveSame++;
      if (consecutiveSame >= TRAP_THRESHOLD) break; // keyboard trap
    } else {
      consecutiveSame = 0;
    }
    lastFingerprint = currentFingerprint;

    // Cycle complete: focus returned to starting element.
    const startKey = `${startInfo.tag.toLowerCase()}#${startInfo.id}`;
    const currentKey = `${current.tag}#${current.id}`;
    if (tabCount > 0 && currentKey === startKey) {
      break;
    }
  }

  return safeRatio(focusedCount, totalFocusable);
}


/**
 * Req 2.4: ARIA correctness.
 * Validate elements with [role] or [aria-*] attributes against WAI-ARIA 1.2 spec.
 * Score = valid elements / total ARIA-annotated elements.
 */
async function computeAriaCorrectness(
  page: Page,
  traverseShadowDOM: boolean,
): Promise<number> {
  const { valid, total } = await page.evaluate(
    ({ requiredProps, traverseShadow, maxDepth }) => {
      const collectElements = (root: Document | ShadowRoot, depth = 0): Element[] => {
        const elements = Array.from(root.querySelectorAll('[role], [aria-hidden], [aria-label], [aria-labelledby], [aria-checked], [aria-expanded], [aria-selected], [aria-valuenow], [aria-controls], [aria-level]'));
        if (traverseShadow && depth < maxDepth) {
          const allEls = Array.from(root.querySelectorAll('*'));
          for (const el of allEls) {
            if (el.shadowRoot) {
              elements.push(...collectElements(el.shadowRoot, depth + 1));
            }
          }
        }
        return elements;
      };

      const ariaElements = collectElements(document);
      if (ariaElements.length === 0) return { valid: 0, total: 0 };

      let validCount = 0;

      for (const el of ariaElements) {
        let isValid = true;
        const role = el.getAttribute('role');

        // Check: aria-hidden="true" on focusable elements is invalid
        if (el.getAttribute('aria-hidden') === 'true') {
          const focusable =
            el.matches('a[href], button, input, select, textarea, [tabindex]');
          if (focusable) {
            isValid = false;
          }
        }

        // Check: required properties for known roles
        if (role && requiredProps[role]) {
          for (const prop of requiredProps[role]) {
            if (!el.hasAttribute(prop)) {
              isValid = false;
              break;
            }
          }
        }

        // Check: invalid aria-* attribute values
        for (const attr of el.getAttributeNames()) {
          if (!attr.startsWith('aria-')) continue;
          const value = el.getAttribute(attr);
          // aria-hidden, aria-checked, aria-expanded, aria-selected must be true/false
          if (['aria-hidden', 'aria-checked', 'aria-expanded', 'aria-selected', 'aria-disabled', 'aria-required'].includes(attr)) {
            if (value !== 'true' && value !== 'false' && value !== 'mixed') {
              isValid = false;
              break;
            }
          }
        }

        if (isValid) validCount++;
      }

      return { valid: validCount, total: ariaElements.length };
    },
    { requiredProps: REQUIRED_ARIA_PROPS, traverseShadow: traverseShadowDOM, maxDepth: MAX_SHADOW_DEPTH },
  );

  return safeRatio(valid, total);
}

/**
 * Req 2.5: Pseudo-compliance detection.
 * Elements with interactive ARIA roles but no corresponding event listeners.
 * Uses CDP DOMDebugger.getEventListeners().
 */
async function computePseudoCompliance(
  page: Page,
  cdpSession: CDPSession,
): Promise<{ count: number; ratio: number }> {
  // Get all elements with interactive ARIA roles (Req 2.5)
  // Use page.$$ to get ALL matching elements, not just the first one
  const elementHandles = await page.$$('[role="button"], [role="link"], [role="checkbox"], [role="tab"], [role="menuitem"]');

  if (elementHandles.length === 0) {
    return { count: 0, ratio: 0 };
  }

  let pseudoCompliantCount = 0;

  for (const handle of elementHandles) {
    try {
      // Stamp a unique data attribute on this specific element so we can
      // locate it via CDP Runtime.evaluate and get its remote objectId.
      // This avoids the bug of always querying document.querySelector('[role]')
      // which would only ever inspect the first role element.
      const uid = `__pc_${Math.random().toString(36).slice(2)}`;
      await handle.evaluate((el: Element, id: string) => {
        el.setAttribute('data-pc-uid', id);
      }, uid);

      const { result } = await cdpSession.send('Runtime.evaluate' as any, {
        expression: `document.querySelector('[data-pc-uid="${uid}"]')`,
        returnByValue: false,
      });

      // Clean up the temporary attribute
      await handle.evaluate((el: Element) => {
        el.removeAttribute('data-pc-uid');
      });

      if (!result?.objectId) continue;

      // Check for event listeners on this specific element
      const { listeners } = await cdpSession.send('DOMDebugger.getEventListeners' as any, {
        objectId: result.objectId,
      }) as { listeners: Array<{ type: string }> };

      const hasInteractiveHandler = listeners.some(
        (l) => l.type === 'click' || l.type === 'keydown' || l.type === 'keyup',
      );

      if (!hasInteractiveHandler) {
        pseudoCompliantCount++;
      }
    } catch {
      // Skip elements that can't be inspected
    }
  }

  return {
    count: pseudoCompliantCount,
    ratio: safeRatio(pseudoCompliantCount, elementHandles.length),
  };
}


/**
 * Req 2.6: Form labeling completeness.
 * Proportion of form controls with an associated label, aria-label, or aria-labelledby.
 */
async function computeFormLabelingCompleteness(
  page: Page,
  traverseShadowDOM: boolean,
): Promise<number> {
  const { labeled, total } = await page.evaluate(
    ({ traverseShadow, maxDepth }) => {
      const collectFormControls = (root: Document | ShadowRoot, depth = 0): Element[] => {
        const controls = Array.from(root.querySelectorAll('input, select, textarea'));
        if (traverseShadow && depth < maxDepth) {
          const allEls = Array.from(root.querySelectorAll('*'));
          for (const el of allEls) {
            if (el.shadowRoot) {
              controls.push(...collectFormControls(el.shadowRoot, depth + 1));
            }
          }
        }
        return controls;
      };

      const controls = collectFormControls(document);
      if (controls.length === 0) return { labeled: 0, total: 0 };

      let labeledCount = 0;

      for (const control of controls) {
        // Skip hidden inputs
        if (control.getAttribute('type') === 'hidden') continue;

        const hasAriaLabel = !!control.getAttribute('aria-label');
        const hasAriaLabelledBy = !!control.getAttribute('aria-labelledby');

        // Check for <label for="id"> association
        const id = control.getAttribute('id');
        const hasLabelFor = id ? !!document.querySelector(`label[for="${id}"]`) : false;

        // Check for wrapping <label>
        const hasWrappingLabel = !!control.closest('label');

        if (hasAriaLabel || hasAriaLabelledBy || hasLabelFor || hasWrappingLabel) {
          labeledCount++;
        }
      }

      // Exclude hidden inputs from total
      const visibleControls = controls.filter(
        (c) => c.getAttribute('type') !== 'hidden',
      );

      return { labeled: labeledCount, total: visibleControls.length };
    },
    { traverseShadow: traverseShadowDOM, maxDepth: MAX_SHADOW_DEPTH },
  );

  return safeRatio(labeled, total);
}

/**
 * Req 2.7: Landmark coverage.
 * Proportion of visible text content inside ARIA landmark regions.
 */
async function computeLandmarkCoverage(
  page: Page,
  traverseShadowDOM: boolean,
): Promise<number> {
  const { landmarkTextLength, totalTextLength } = await page.evaluate(
    ({ landmarkSels, traverseShadow, maxDepth }) => {
      const getVisibleTextLength = (root: Element | ShadowRoot, depth = 0): number => {
        let length = 0;
        const walker = document.createTreeWalker(
          root as Node,
          NodeFilter.SHOW_TEXT,
          null,
        );
        let node: Node | null;
        while ((node = walker.nextNode())) {
          const parent = node.parentElement;
          if (parent) {
            const style = window.getComputedStyle(parent);
            if (style.display === 'none' || style.visibility === 'hidden') continue;
          }
          length += (node.textContent?.trim().length ?? 0);
        }
        if (traverseShadow && depth < maxDepth && root instanceof Element) {
          const allEls = Array.from(root.querySelectorAll('*'));
          for (const el of allEls) {
            if (el.shadowRoot) {
              length += getVisibleTextLength(el.shadowRoot, depth + 1);
            }
          }
        }
        return length;
      };

      const totalLen = getVisibleTextLength(document.body);
      if (totalLen === 0) return { landmarkTextLength: 0, totalTextLength: 0 };

      // Collect all landmark elements
      const landmarkSet = new Set<Element>();
      for (const sel of landmarkSels) {
        for (const el of document.querySelectorAll(sel)) {
          landmarkSet.add(el);
        }
      }

      // Sum text length inside landmarks (avoid double-counting nested landmarks)
      let landmarkLen = 0;
      for (const landmark of landmarkSet) {
        // Skip if this landmark is nested inside another landmark
        let isNested = false;
        for (const other of landmarkSet) {
          if (other !== landmark && other.contains(landmark)) {
            isNested = true;
            break;
          }
        }
        if (isNested) continue;
        landmarkLen += getVisibleTextLength(landmark);
      }

      return { landmarkTextLength: landmarkLen, totalTextLength: totalLen };
    },
    { landmarkSels: LANDMARK_SELECTORS, traverseShadow: traverseShadowDOM, maxDepth: MAX_SHADOW_DEPTH },
  );

  return safeRatio(landmarkTextLength, totalTextLength);
}

// --- Main Tier 2 scan function ---

/**
 * Compute all 7 Tier 2 functional accessibility metrics.
 *
 * All ratio metrics are returned as decimals 0.0–1.0 (Req 2.9).
 * Shadow DOM is traversed by default (Req 2.8).
 *
 * @param page - Playwright Page object (must be navigated to the target URL)
 * @param cdpSession - CDP session for low-level browser access
 * @param options - Optional: traverseShadowDOM (default true)
 * @returns Tier2Metrics with all 7 metrics computed
 */
export async function scanTier2(
  page: Page,
  cdpSession: CDPSession,
  options?: { traverseShadowDOM?: boolean },
): Promise<Tier2Metrics> {
  const traverseShadowDOM = options?.traverseShadowDOM ?? true;

  // Helper: run a metric computation with fallback to 0 on error.
  // Some pages (e.g. Bing) have DOM proxies that cause stack overflow
  // when querySelectorAll('*') triggers page-internal getters.
  const safe = async <T>(fn: () => Promise<T>, fallback: T): Promise<T> => {
    try { return await fn(); } catch { return fallback; }
  };

  // Run independent metrics concurrently where possible
  const [
    semanticHtmlRatio,
    accessibleNameCoverage,
    ariaCorrectness,
    formLabelingCompleteness,
    landmarkCoverage,
  ] = await Promise.all([
    safe(() => computeSemanticHtmlRatio(page, traverseShadowDOM), 0),
    safe(() => computeAccessibleNameCoverage(cdpSession), 0),
    safe(() => computeAriaCorrectness(page, traverseShadowDOM), 0),
    safe(() => computeFormLabelingCompleteness(page, traverseShadowDOM), 0),
    safe(() => computeLandmarkCoverage(page, traverseShadowDOM), 0),
  ]);

  // Keyboard navigability must run sequentially (modifies focus state)
  const keyboardNavigability = await safe(() => computeKeyboardNavigability(page), 0);

  // Pseudo-compliance needs both page and CDP
  const pseudoCompliance = await safe(
    () => computePseudoCompliance(page, cdpSession),
    { count: 0, ratio: 0 },
  );

  return {
    semanticHtmlRatio: clamp01(semanticHtmlRatio),
    accessibleNameCoverage: clamp01(accessibleNameCoverage),
    keyboardNavigability: clamp01(keyboardNavigability),
    ariaCorrectness: clamp01(ariaCorrectness),
    pseudoComplianceCount: pseudoCompliance.count,
    pseudoComplianceRatio: clamp01(pseudoCompliance.ratio),
    formLabelingCompleteness: clamp01(formLabelingCompleteness),
    landmarkCoverage: clamp01(landmarkCoverage),
    shadowDomIncluded: traverseShadowDOM,
  };
}
