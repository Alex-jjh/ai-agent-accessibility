// AMT operator L4 — Remove inline keyboard event handlers
//
// WCAG: SC 2.1.1 (Keyboard). CAT: I (no visual change; attribute removal only).
//
// Source: apply-low.js block 4.
(() => {
  const changes = [];

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

  return changes;
})();
