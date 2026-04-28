// AMT operator L8 — Remove tabindex attributes
//
// WCAG: F44 / SC 2.4.3 (Focus Order). CAT: I (attribute removal; no visual
// change, but may affect keyboard focus order).
//
// Source: apply-low.js block 8.
(() => {
  const changes = [];

  const tabindexEls = Array.from(document.querySelectorAll('[tabindex]'));
  for (const el of tabindexEls) {
    const origTabindex = el.getAttribute('tabindex') || '';
    const tabSelector = el.tagName.toLowerCase() +
      (el.id ? '#' + el.id : String(el.className) ? '.' + String(el.className).split(' ')[0] : '');
    el.removeAttribute('tabindex');
    changes.push({
      selector: tabSelector,
      changeType: 'remove-attr',
      original: 'tabindex="' + origTabindex + '"',
      modified: '',
    });
  }

  return changes;
})();
