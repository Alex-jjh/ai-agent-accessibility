// Variant: Medium-Low (Level 1) — Pseudo-compliance (ARIA present, handlers missing)
// Extracted from patches/index.ts applyMediumLow() for shared use by TS and Python bridge.
// Contract: pure browser JS IIFE, returns DomChange[], no imports.
(() => {
  const changes = [];

  // 1. Replace <button> elements that have no text content with <div> equivalents
  const buttons = Array.from(document.querySelectorAll('button'));
  for (const btn of buttons) {
    const textContent = (btn.textContent || '').trim();
    if (textContent.length === 0) {
      const originalHtml = btn.outerHTML;
      const div = document.createElement('div');
      div.innerHTML = btn.innerHTML;
      for (const attr of Array.from(btn.attributes)) {
        if (attr.name !== 'type') {
          div.setAttribute(attr.name, attr.value);
        }
      }
      const selector = 'button' + (btn.id ? '#' + btn.id : String(btn.className) ? '.' + String(btn.className).split(' ')[0] : '');
      const revertId = '__variant_btn_' + changes.length;
      div.setAttribute('data-variant-revert', revertId);
      btn.replaceWith(div);
      changes.push({
        selector: '[data-variant-revert="' + revertId + '"]',
        changeType: 'replace',
        original: originalHtml.substring(0, 500),
        modified: div.outerHTML.substring(0, 500),
      });
    }
  }

  // 2. Remove keydown/keyup handlers from ALL elements with role="button"
  const roleButtons = Array.from(document.querySelectorAll('[role="button"]'));
  for (const el of roleButtons) {
    const handlerAttrs = ['onkeydown', 'onkeyup'];
    for (const attr of handlerAttrs) {
      if (el.hasAttribute(attr)) {
        const originalValue = el.getAttribute(attr) || '';
        const selector = el.tagName.toLowerCase() +
          (el.id ? '#' + el.id : String(el.className) ? '.' + String(el.className).split(' ')[0] : '') +
          '[role="button"]';
        el.removeAttribute(attr);
        changes.push({
          selector,
          changeType: 'remove-handler',
          original: attr + '="' + originalValue + '"',
          modified: '',
        });
      }
    }
    // Clone-replace to strip JS-registered keydown/keyup listeners
    const originalHtml = el.outerHTML;
    const clone = el.cloneNode(true);
    const selector = el.tagName.toLowerCase() +
      (el.id ? '#' + el.id : String(el.className) ? '.' + String(el.className).split(' ')[0] : '') +
      '[role="button"]';
    el.replaceWith(clone);
    changes.push({
      selector,
      changeType: 'remove-handler',
      original: 'keydown/keyup listeners on ' + originalHtml.substring(0, 200),
      modified: 'listeners removed via clone',
    });
  }

  // 3. Remove <label> association for <input> elements that lack a placeholder attribute
  const inputs = Array.from(document.querySelectorAll('input'));
  for (const input of inputs) {
    if (!input.hasAttribute('placeholder')) {
      const inputId = input.id;
      if (inputId) {
        const label = document.querySelector('label[for="' + inputId + '"]');
        if (label) {
          const originalHtml = label.outerHTML;
          const selector = 'label[for="' + inputId + '"]';
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
      const ariaAttrs = ['aria-label', 'aria-labelledby'];
      for (const attr of ariaAttrs) {
        if (input.hasAttribute(attr)) {
          const originalValue = input.getAttribute(attr) || '';
          const selector = 'input' + (inputId ? '#' + inputId : '');
          input.removeAttribute(attr);
          changes.push({
            selector,
            changeType: 'remove-attr',
            original: attr + '="' + originalValue + '"',
            modified: '',
          });
        }
      }
    }
  }

  return changes;
})();
