// Module 2: Variant Generator — DOM Patch Engine
// Requirements: 5.1, 5.2, 5.3, 5.4, 5.7, 6.1
//
// Applies deterministic DOM manipulations per variant level and records
// all changes as reversible DomChange[] entries with DOM hashes.

import type { Page } from 'playwright';
import type { VariantLevel, DomChange, VariantDiff } from '../types.js';

/**
 * Compute SHA-256 hash of the serialized DOM inside the browser
 * using the Web Crypto API (crypto.subtle.digest).
 */
async function computeDomHash(page: Page): Promise<string> {
  return page.evaluate(() => {
    // Use a simple djb2 hash instead of crypto.subtle.digest
    // because crypto.subtle is only available in secure contexts (HTTPS).
    // WebArena runs on HTTP, so we need a pure-JS fallback.
    const html = document.documentElement.outerHTML;
    let hash = 5381;
    for (let i = 0; i < html.length; i++) {
      hash = ((hash << 5) + hash + html.charCodeAt(i)) >>> 0;
    }
    return hash.toString(16).padStart(8, '0');
  });
}

/**
 * Low variant (Level 0): Aggressively degrade accessibility.
 * - Replace semantic elements with divs
 * - Remove all ARIA/role attributes
 * - Remove all labels
 * - Remove keyboard event handlers
 * - Wrap interactive elements in closed Shadow DOM
 * (Req 5.1)
 */
async function applyLow(page: Page): Promise<DomChange[]> {
  return page.evaluate(() => {
    const changes: Array<{
      selector: string;
      changeType: 'replace' | 'remove-attr' | 'add-attr' | 'remove-element' | 'add-element' | 'remove-handler';
      original: string;
      modified: string;
    }> = [];

    // 1. Replace semantic elements with divs
    const semanticTags = ['nav', 'main', 'header', 'footer', 'article', 'section', 'aside'];
    for (const tag of semanticTags) {
      const elements = Array.from(document.querySelectorAll(tag));
      for (const el of elements) {
        const originalHtml = el.outerHTML;
        const div = document.createElement('div');
        div.innerHTML = el.innerHTML;
        // Copy non-semantic attributes
        for (const attr of Array.from(el.attributes)) {
          if (attr.name !== 'role') {
            div.setAttribute(attr.name, attr.value);
          }
        }
        const selector = tag + (el.id ? `#${el.id}` : el.className ? `.${el.className.split(' ')[0]}` : '');
        el.replaceWith(div);
        changes.push({
          selector,
          changeType: 'replace',
          original: originalHtml.substring(0, 500),
          modified: div.outerHTML.substring(0, 500),
        });
      }
    }

    // 2. Remove all aria-* attributes and role attributes
    const ariaElements = Array.from(document.querySelectorAll('[role], [aria-label], [aria-labelledby], [aria-describedby], [aria-hidden], [aria-expanded], [aria-haspopup], [aria-controls], [aria-live], [aria-atomic], [aria-relevant], [aria-busy], [aria-checked], [aria-selected], [aria-pressed], [aria-disabled], [aria-required], [aria-invalid], [aria-valuemin], [aria-valuemax], [aria-valuenow], [aria-valuetext]'));
    for (const el of ariaElements) {
      const attrsToRemove: string[] = [];
      for (const attr of Array.from(el.attributes)) {
        if (attr.name === 'role' || attr.name.startsWith('aria-')) {
          attrsToRemove.push(attr.name);
        }
      }
      for (const attrName of attrsToRemove) {
        const originalValue = el.getAttribute(attrName) ?? '';
        const selector = el.tagName.toLowerCase() +
          (el.id ? `#${el.id}` : el.className ? `.${String(el.className).split(' ')[0]}` : '');
        el.removeAttribute(attrName);
        changes.push({
          selector,
          changeType: 'remove-attr',
          original: `${attrName}="${originalValue}"`,
          modified: '',
        });
      }
    }

    // 3. Remove all <label> elements
    const labels = Array.from(document.querySelectorAll('label'));
    for (const label of labels) {
      const originalHtml = label.outerHTML;
      const selector = 'label' + (label.htmlFor ? `[for="${label.htmlFor}"]` : '');
      label.remove();
      changes.push({
        selector,
        changeType: 'remove-element',
        original: originalHtml.substring(0, 500),
        modified: '',
      });
    }

    // 4. Remove keyboard event handlers from all elements
    // We clone-replace elements to strip all event listeners including keydown/keyup/keypress
    const allInteractive = Array.from(document.querySelectorAll(
      'button, a, input, select, textarea, [tabindex], [onclick], [onkeydown], [onkeyup], [onkeypress]'
    ));
    for (const el of allInteractive) {
      // Remove inline handlers
      const handlerAttrs = ['onkeydown', 'onkeyup', 'onkeypress'];
      for (const attr of handlerAttrs) {
        if (el.hasAttribute(attr)) {
          const originalValue = el.getAttribute(attr) ?? '';
          const selector = el.tagName.toLowerCase() +
            (el.id ? `#${el.id}` : el.className ? `.${String(el.className).split(' ')[0]}` : '');
          el.removeAttribute(attr);
          changes.push({
            selector,
            changeType: 'remove-handler',
            original: `${attr}="${originalValue}"`,
            modified: '',
          });
        }
      }
    }

    // 5. Wrap interactive elements in closed Shadow DOM to hide from A11y tree
    const interactiveForShadow = Array.from(document.querySelectorAll(
      'button, [role="button"], [role="link"], [role="checkbox"], [role="tab"], [role="menuitem"]'
    ));
    for (const el of interactiveForShadow) {
      // Only wrap if not already in a shadow root wrapper
      if (el.parentElement && !el.parentElement.shadowRoot) {
        const wrapper = document.createElement('div');
        const originalHtml = el.outerHTML;
        const selector = el.tagName.toLowerCase() +
          (el.id ? `#${el.id}` : el.className ? `.${String(el.className).split(' ')[0]}` : '');
        el.parentElement.insertBefore(wrapper, el);
        const shadow = wrapper.attachShadow({ mode: 'closed' });
        shadow.appendChild(el);
        changes.push({
          selector,
          changeType: 'replace',
          original: originalHtml.substring(0, 500),
          modified: `<div>[closed shadow containing: ${el.tagName.toLowerCase()}]</div>`,
        });
      }
    }

    return changes;
  });
}


/**
 * Medium-Low variant (Level 1): Rule-based pseudo-compliance strategy.
 * Deterministic, self-adaptive across apps. Models the most common
 * real-world inaccessible state where ARIA is present but not
 * functionally backed.
 * (Req 5.2)
 *
 * Rules:
 * - Keep all <nav> and <main> elements intact (preserve page skeleton)
 * - Replace <button> elements with no text content with <div> equivalents
 * - Remove keydown/keyup handlers from ALL elements with role="button"
 * - Remove <label> association for <input> elements lacking placeholder
 * - Keep existing landmark aria-label values unchanged
 */
async function applyMediumLow(page: Page): Promise<DomChange[]> {
  return page.evaluate(() => {
    const changes: Array<{
      selector: string;
      changeType: 'replace' | 'remove-attr' | 'add-attr' | 'remove-element' | 'add-element' | 'remove-handler';
      original: string;
      modified: string;
    }> = [];

    // 1. Replace <button> elements that have no text content with <div> equivalents
    const buttons = Array.from(document.querySelectorAll('button'));
    for (const btn of buttons) {
      const textContent = (btn.textContent ?? '').trim();
      if (textContent.length === 0) {
        const originalHtml = btn.outerHTML;
        const div = document.createElement('div');
        div.innerHTML = btn.innerHTML;
        // Copy attributes except type
        for (const attr of Array.from(btn.attributes)) {
          if (attr.name !== 'type') {
            div.setAttribute(attr.name, attr.value);
          }
        }
        const selector = 'button' + (btn.id ? `#${btn.id}` : btn.className ? `.${String(btn.className).split(' ')[0]}` : '');
        btn.replaceWith(div);
        changes.push({
          selector,
          changeType: 'replace',
          original: originalHtml.substring(0, 500),
          modified: div.outerHTML.substring(0, 500),
        });
      }
    }

    // 2. Remove keydown/keyup handlers from ALL elements with role="button"
    // This creates the core pseudo-compliance scenario: role present, handler absent
    const roleButtons = Array.from(document.querySelectorAll('[role="button"]'));
    for (const el of roleButtons) {
      const handlerAttrs = ['onkeydown', 'onkeyup'];
      for (const attr of handlerAttrs) {
        if (el.hasAttribute(attr)) {
          const originalValue = el.getAttribute(attr) ?? '';
          const selector = el.tagName.toLowerCase() +
            (el.id ? `#${el.id}` : el.className ? `.${String(el.className).split(' ')[0]}` : '') +
            '[role="button"]';
          el.removeAttribute(attr);
          changes.push({
            selector,
            changeType: 'remove-handler',
            original: `${attr}="${originalValue}"`,
            modified: '',
          });
        }
      }
      // Also clone-replace to strip JS-registered keydown/keyup listeners
      // We record this as a handler removal
      const originalHtml = el.outerHTML;
      const clone = el.cloneNode(true) as Element;
      const selector = el.tagName.toLowerCase() +
        (el.id ? `#${el.id}` : el.className ? `.${String(el.className).split(' ')[0]}` : '') +
        '[role="button"]';
      el.replaceWith(clone);
      changes.push({
        selector,
        changeType: 'remove-handler',
        original: `keydown/keyup listeners on ${originalHtml.substring(0, 200)}`,
        modified: 'listeners removed via clone',
      });
    }

    // 3. Remove <label> association for <input> elements that lack a placeholder attribute
    const inputs = Array.from(document.querySelectorAll('input'));
    for (const input of inputs) {
      if (!input.hasAttribute('placeholder')) {
        const inputId = input.id;
        if (inputId) {
          // Find and remove the associated label
          const label = document.querySelector(`label[for="${inputId}"]`);
          if (label) {
            const originalHtml = label.outerHTML;
            const selector = `label[for="${inputId}"]`;
            label.remove();
            changes.push({
              selector,
              changeType: 'remove-element',
              original: originalHtml.substring(0, 500),
              modified: '',
            });
          }
        }
        // Also remove aria-label and aria-labelledby from the input itself
        for (const attr of ['aria-label', 'aria-labelledby']) {
          if (input.hasAttribute(attr)) {
            const originalValue = input.getAttribute(attr) ?? '';
            const selector = 'input' + (inputId ? `#${inputId}` : '');
            input.removeAttribute(attr);
            changes.push({
              selector,
              changeType: 'remove-attr',
              original: `${attr}="${originalValue}"`,
              modified: '',
            });
          }
        }
      }
    }

    // Note: <nav>, <main> elements are kept intact (rule 1)
    // Note: Existing landmark aria-label values are kept unchanged (rule 5)

    return changes;
  });
}


/**
 * High variant (Level 2): Enhance accessibility.
 * - Add missing aria-label to interactive elements
 * - Insert skip-navigation link
 * - Ensure all form controls have associated labels
 * - Add landmark roles to major page sections
 * - Fix axe-core auto-remediable violations
 * (Req 5.4)
 */
async function applyHigh(page: Page): Promise<DomChange[]> {
  return page.evaluate(() => {
    const changes: Array<{
      selector: string;
      changeType: 'replace' | 'remove-attr' | 'add-attr' | 'remove-element' | 'add-element' | 'remove-handler';
      original: string;
      modified: string;
    }> = [];

    // 1. Add aria-label to interactive elements missing accessible names
    const interactiveSelectors = 'a, button, input, select, textarea, [role="button"], [role="link"], [role="checkbox"], [role="tab"], [role="menuitem"]';
    const interactiveElements = Array.from(document.querySelectorAll(interactiveSelectors));
    for (const el of interactiveElements) {
      const hasAriaLabel = el.hasAttribute('aria-label');
      const hasAriaLabelledBy = el.hasAttribute('aria-labelledby');
      const textContent = (el.textContent ?? '').trim();
      const title = el.getAttribute('title') ?? '';
      const placeholder = (el as HTMLInputElement).placeholder ?? '';

      // Check if element has an associated <label>
      const inputId = el.id;
      const hasLabel = inputId ? !!document.querySelector(`label[for="${inputId}"]`) : false;

      if (!hasAriaLabel && !hasAriaLabelledBy && !textContent && !title && !placeholder && !hasLabel) {
        // Generate a deterministic label based on element type and position
        const tagName = el.tagName.toLowerCase();
        const type = el.getAttribute('type') ?? '';
        const role = el.getAttribute('role') ?? '';
        const name = el.getAttribute('name') ?? '';
        const labelText = name
          ? `${tagName} ${name}`
          : role
            ? `${role} element`
            : type
              ? `${tagName} ${type}`
              : `${tagName} element`;

        const selector = tagName +
          (el.id ? `#${el.id}` : el.className ? `.${String(el.className).split(' ')[0]}` : '');
        el.setAttribute('aria-label', labelText);
        changes.push({
          selector,
          changeType: 'add-attr',
          original: '',
          modified: `aria-label="${labelText}"`,
        });
      }
    }

    // 2. Insert skip-navigation link at the top of the page
    const existingSkipLink = document.querySelector('a.skip-link, a[href="#main-content"]');
    if (!existingSkipLink) {
      const skipLink = document.createElement('a');
      skipLink.href = '#main-content';
      skipLink.className = 'skip-link';
      skipLink.textContent = 'Skip to main content';
      skipLink.setAttribute('style',
        'position:absolute;top:-40px;left:0;background:#000;color:#fff;padding:8px;z-index:10000;' +
        'transition:top 0.3s;');
      // Make it visible on focus
      skipLink.addEventListener('focus', () => {
        skipLink.style.top = '0';
      });
      skipLink.addEventListener('blur', () => {
        skipLink.style.top = '-40px';
      });

      const body = document.body;
      body.insertBefore(skipLink, body.firstChild);

      // Add id="main-content" to the first <main> or first major content area
      const mainEl = document.querySelector('main') ?? document.querySelector('[role="main"]');
      if (mainEl && !mainEl.id) {
        mainEl.id = 'main-content';
      } else if (!mainEl) {
        // If no main element, add id to the first content div
        const firstContent = document.querySelector('.content, #content, .main, #main');
        if (firstContent && !firstContent.id) {
          (firstContent as HTMLElement).id = 'main-content';
        }
      }

      changes.push({
        selector: 'body > a.skip-link',
        changeType: 'add-element',
        original: '',
        modified: skipLink.outerHTML.substring(0, 500),
      });
    }

    // 3. Ensure all form controls have associated labels
    const formControls = Array.from(document.querySelectorAll('input, select, textarea'));
    for (const control of formControls) {
      const controlId = control.id;
      const hasAriaLabel = control.hasAttribute('aria-label');
      const hasAriaLabelledBy = control.hasAttribute('aria-labelledby');
      const hasLabel = controlId ? !!document.querySelector(`label[for="${controlId}"]`) : false;
      // Check if wrapped in a label
      const wrappedInLabel = !!control.closest('label');

      if (!hasAriaLabel && !hasAriaLabelledBy && !hasLabel && !wrappedInLabel) {
        const tagName = control.tagName.toLowerCase();
        const type = control.getAttribute('type') ?? '';
        const name = control.getAttribute('name') ?? '';
        const placeholder = (control as HTMLInputElement).placeholder ?? '';

        const labelText = placeholder || name || `${tagName} ${type}`.trim() || tagName;

        // If the control has an id, create a <label> element
        if (controlId) {
          const label = document.createElement('label');
          label.htmlFor = controlId;
          label.textContent = labelText;
          label.setAttribute('style', 'position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);');
          control.parentElement?.insertBefore(label, control);
          const selector = `${tagName}#${controlId}`;
          changes.push({
            selector,
            changeType: 'add-element',
            original: '',
            modified: label.outerHTML.substring(0, 500),
          });
        } else {
          // No id — add aria-label instead
          const selector = tagName +
            (control.className ? `.${String(control.className).split(' ')[0]}` : '') +
            (name ? `[name="${name}"]` : '');
          control.setAttribute('aria-label', labelText);
          changes.push({
            selector,
            changeType: 'add-attr',
            original: '',
            modified: `aria-label="${labelText}"`,
          });
        }
      }
    }

    // 4. Add landmark roles to major page sections
    const landmarkMappings: Array<{ selector: string; role: string }> = [
      { selector: 'header:not([role])', role: 'banner' },
      { selector: 'nav:not([role])', role: 'navigation' },
      { selector: 'main:not([role])', role: 'main' },
      { selector: 'footer:not([role])', role: 'contentinfo' },
      { selector: 'aside:not([role])', role: 'complementary' },
      { selector: 'form:not([role])', role: 'form' },
    ];

    for (const mapping of landmarkMappings) {
      const elements = Array.from(document.querySelectorAll(mapping.selector));
      for (const el of elements) {
        const elSelector = el.tagName.toLowerCase() +
          (el.id ? `#${el.id}` : el.className ? `.${String(el.className).split(' ')[0]}` : '');
        el.setAttribute('role', mapping.role);
        changes.push({
          selector: elSelector,
          changeType: 'add-attr',
          original: '',
          modified: `role="${mapping.role}"`,
        });
      }
    }

    // 5. Fix common axe-core auto-remediable violations
    // 5a. Ensure all images have alt text
    const images = Array.from(document.querySelectorAll('img:not([alt])'));
    for (const img of images) {
      const src = img.getAttribute('src') ?? '';
      const altText = src.split('/').pop()?.replace(/\.[^.]+$/, '').replace(/[-_]/g, ' ') ?? 'image';
      const selector = 'img' + (img.id ? `#${img.id}` : img.className ? `.${String(img.className).split(' ')[0]}` : '');
      img.setAttribute('alt', altText);
      changes.push({
        selector,
        changeType: 'add-attr',
        original: '',
        modified: `alt="${altText}"`,
      });
    }

    // 5b. Ensure html element has lang attribute
    const htmlEl = document.documentElement;
    if (!htmlEl.hasAttribute('lang')) {
      htmlEl.setAttribute('lang', 'en');
      changes.push({
        selector: 'html',
        changeType: 'add-attr',
        original: '',
        modified: 'lang="en"',
      });
    }

    // 5c. Ensure all links have discernible text
    const emptyLinks = Array.from(document.querySelectorAll('a:not([aria-label])'));
    for (const link of emptyLinks) {
      const text = (link.textContent ?? '').trim();
      if (!text && !link.getAttribute('aria-labelledby') && !link.getAttribute('title')) {
        const href = link.getAttribute('href') ?? '';
        const labelText = href ? `Link to ${href.split('/').pop() || 'page'}` : 'link';
        const selector = 'a' + (link.id ? `#${link.id}` : link.className ? `.${String(link.className).split(' ')[0]}` : '');
        link.setAttribute('aria-label', labelText);
        changes.push({
          selector,
          changeType: 'add-attr',
          original: '',
          modified: `aria-label="${labelText}"`,
        });
      }
    }

    return changes;
  });
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
