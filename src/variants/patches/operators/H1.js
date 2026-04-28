// AMT operator H1 — Add aria-label to interactives missing accessible names
//
// WCAG: SC 4.1.2. Positive enhancement. Derives a heuristic label from
// name/role/type — explicitly a *surrogate* label, not production-quality.
//
// Source: apply-high.js block 1.
(() => {
  const changes = [];

  const interactiveSelectors = 'a, button, input, select, textarea, [role="button"], [role="link"], [role="checkbox"], [role="tab"], [role="menuitem"]';
  const interactiveElements = Array.from(document.querySelectorAll(interactiveSelectors));
  for (const el of interactiveElements) {
    const hasAriaLabel = el.hasAttribute('aria-label');
    const hasAriaLabelledBy = el.hasAttribute('aria-labelledby');
    const textContent = (el.textContent || '').trim();
    const title = el.getAttribute('title') || '';
    const placeholder = el.placeholder || '';

    const inputId = el.id;
    const hasLabel = inputId ? !!document.querySelector('label[for="' + inputId + '"]') : false;

    if (!hasAriaLabel && !hasAriaLabelledBy && !textContent && !title && !placeholder && !hasLabel) {
      const tagName = el.tagName.toLowerCase();
      const type = el.getAttribute('type') || '';
      const role = el.getAttribute('role') || '';
      const name = el.getAttribute('name') || '';
      const labelText = name
        ? tagName + ' ' + name
        : role
          ? role + ' element'
          : type
            ? tagName + ' ' + type
            : tagName + ' element';

      const selector = tagName +
        (el.id ? '#' + el.id : String(el.className) ? '.' + String(el.className).split(' ')[0] : '');
      el.setAttribute('aria-label', labelText);
      changes.push({
        selector,
        changeType: 'add-attr',
        original: '',
        modified: 'aria-label="' + labelText + '"',
      });
    }
  }

  return changes;
})();
