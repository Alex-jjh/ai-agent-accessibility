// AMT operator ML3 — <input> without placeholder: strip label + aria-label
//
// WCAG: F68 / SC 4.1.2. Pseudo-compliance: simulates forms where developers
// relied on visible visual labels but didn't wire up programmatic
// association. Applies only to inputs that lack placeholder (so the
// resulting input has literally no accessible name in any channel).
//
// Source: apply-medium-low.js block 3.
(() => {
  const changes = [];

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
