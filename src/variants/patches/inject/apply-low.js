// Variant: Low (Level 0) — Aggressively degrade accessibility
// Extracted from patches/index.ts applyLow() for shared use by TS and Python bridge.
// Contract: pure browser JS IIFE, returns DomChange[], no imports.
(() => {
  const changes = [];

  // 1. Replace semantic elements with divs
  const semanticTags = ['nav', 'main', 'header', 'footer', 'article', 'section', 'aside'];
  for (const tag of semanticTags) {
    const elements = Array.from(document.querySelectorAll(tag));
    for (const el of elements) {
      const originalHtml = el.outerHTML;
      const div = document.createElement('div');
      div.innerHTML = el.innerHTML;
      for (const attr of Array.from(el.attributes)) {
        if (attr.name !== 'role') {
          div.setAttribute(attr.name, attr.value);
        }
      }
      const selector = tag + (el.id ? '#' + el.id : String(el.className) ? '.' + String(el.className).split(' ')[0] : '');
      const revertId = '__variant_' + tag + '_' + changes.length;
      div.setAttribute('data-variant-revert', revertId);
      el.replaceWith(div);
      changes.push({
        selector: '[data-variant-revert="' + revertId + '"]',
        changeType: 'replace',
        original: originalHtml.substring(0, 500),
        modified: div.outerHTML.substring(0, 500),
      });
    }
  }

  // 2. Remove all aria-* attributes and role attributes
  const ariaElements = Array.from(document.querySelectorAll('[role], [aria-label], [aria-labelledby], [aria-describedby], [aria-hidden], [aria-expanded], [aria-haspopup], [aria-controls], [aria-live], [aria-atomic], [aria-relevant], [aria-busy], [aria-checked], [aria-selected], [aria-pressed], [aria-disabled], [aria-required], [aria-invalid], [aria-valuemin], [aria-valuemax], [aria-valuenow], [aria-valuetext]'));
  for (const el of ariaElements) {
    const attrsToRemove = [];
    for (const attr of Array.from(el.attributes)) {
      if (attr.name === 'role' || attr.name.startsWith('aria-')) {
        attrsToRemove.push(attr.name);
      }
    }
    for (const attrName of attrsToRemove) {
      const originalValue = el.getAttribute(attrName) || '';
      const selector = el.tagName.toLowerCase() +
        (el.id ? '#' + el.id : String(el.className) ? '.' + String(el.className).split(' ')[0] : '');
      el.removeAttribute(attrName);
      changes.push({
        selector,
        changeType: 'remove-attr',
        original: attrName + '="' + originalValue + '"',
        modified: '',
      });
    }
  }

  // 3. Remove all <label> elements
  const labels = Array.from(document.querySelectorAll('label'));
  for (const label of labels) {
    const originalHtml = label.outerHTML;
    const selector = 'label' + (label.htmlFor ? '[for="' + label.htmlFor + '"]' : '');
    label.remove();
    changes.push({
      selector,
      changeType: 'remove-element',
      original: originalHtml.substring(0, 500),
      modified: '',
    });
  }

  // 4. Remove keyboard event handlers from all elements
  const allInteractive = Array.from(document.querySelectorAll(
    'button, a, input, select, textarea, [tabindex], [onclick], [onkeydown], [onkeyup], [onkeypress]'
  ));
  for (const el of allInteractive) {
    const handlerAttrs = ['onkeydown', 'onkeyup', 'onkeypress'];
    for (const attr of handlerAttrs) {
      if (el.hasAttribute(attr)) {
        const originalValue = el.getAttribute(attr) || '';
        const selector = el.tagName.toLowerCase() +
          (el.id ? '#' + el.id : String(el.className) ? '.' + String(el.className).split(' ')[0] : '');
        el.removeAttribute(attr);
        changes.push({
          selector,
          changeType: 'remove-handler',
          original: attr + '="' + originalValue + '"',
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
    if (el.parentElement && !el.parentElement.shadowRoot) {
      const wrapper = document.createElement('div');
      const originalHtml = el.outerHTML;
      const selector = el.tagName.toLowerCase() +
        (el.id ? '#' + el.id : String(el.className) ? '.' + String(el.className).split(' ')[0] : '');
      el.parentElement.insertBefore(wrapper, el);
      const shadow = wrapper.attachShadow({ mode: 'closed' });
      shadow.appendChild(el);
      changes.push({
        selector,
        changeType: 'replace',
        original: originalHtml.substring(0, 500),
        modified: '<div>[closed shadow containing: ' + el.tagName.toLowerCase() + ']</div>',
      });
    }
  }

  return changes;
})();
