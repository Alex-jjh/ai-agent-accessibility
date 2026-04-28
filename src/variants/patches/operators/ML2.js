// AMT operator ML2 — role="button": strip keydown/keyup + cloneReplace
//
// WCAG: SC 2.1.1 (Keyboard). Pseudo-compliance: simulates div[role=button]
// that has the ARIA role but no keyboard handlers (the most common
// real-world a11y bug per WebAIM 2025).
//
// The cloneReplace step uses node.cloneNode() to strip JS-registered
// event listeners (which .getAttribute can't see). Inline handlers
// (onkeydown attrs) are removed first; then the element is cloned,
// which discards any addEventListener-registered listeners.
//
// Source: apply-medium-low.js block 2.
(() => {
  const changes = [];

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

  return changes;
})();
