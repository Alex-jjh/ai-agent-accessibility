// AMT operator H4 — Add landmark roles to major page sections
//
// WCAG: SC 1.3.1. Positive enhancement. Only adds role if not already set
// — respects author-provided roles.
//
// Source: apply-high.js block 4.
(() => {
  const changes = [];

  const landmarkMappings = [
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
        (el.id ? '#' + el.id : String(el.className) ? '.' + String(el.className).split(' ')[0] : '');
      el.setAttribute('role', mapping.role);
      changes.push({
        selector: elSelector,
        changeType: 'add-attr',
        original: '',
        modified: 'role="' + mapping.role + '"',
      });
    }
  }

  return changes;
})();
