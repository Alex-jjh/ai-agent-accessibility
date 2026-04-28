// AMT operator L2 — Remove all aria-* attributes and role attributes
//
// WCAG: SC 2.5.3 (Label in Name) and related. CAT: I (visual-invariant).
//
// Source: apply-low.js block 2.
(() => {
  const changes = [];

  const ariaElements = Array.from(document.querySelectorAll(
    '[role], [aria-label], [aria-labelledby], [aria-describedby], [aria-hidden], [aria-expanded], [aria-haspopup], [aria-controls], [aria-live], [aria-atomic], [aria-relevant], [aria-busy], [aria-checked], [aria-selected], [aria-pressed], [aria-disabled], [aria-required], [aria-invalid], [aria-valuemin], [aria-valuemax], [aria-valuenow], [aria-valuetext]'
  ));
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

  return changes;
})();
