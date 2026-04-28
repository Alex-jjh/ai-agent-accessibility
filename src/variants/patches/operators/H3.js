// AMT operator H3 — Associate labels with form controls
//
// WCAG: SC 4.1.2. Positive enhancement. For controls with an id, creates
// a visually-hidden <label for>; for controls without id, falls back to
// aria-label (which is less ideal than a real label but still accessible).
//
// Label text is derived from placeholder > name > type — surrogate text,
// not production-quality.
//
// Source: apply-high.js block 3.
(() => {
  const changes = [];

  const formControls = Array.from(document.querySelectorAll('input, select, textarea'));
  for (const control of formControls) {
    const controlId = control.id;
    const hasAriaLabel = control.hasAttribute('aria-label');
    const hasAriaLabelledBy = control.hasAttribute('aria-labelledby');
    const hasLabel = controlId ? !!document.querySelector('label[for="' + controlId + '"]') : false;
    const wrappedInLabel = !!control.closest('label');

    if (!hasAriaLabel && !hasAriaLabelledBy && !hasLabel && !wrappedInLabel) {
      const tagName = control.tagName.toLowerCase();
      const type = control.getAttribute('type') || '';
      const name = control.getAttribute('name') || '';
      const placeholder = control.placeholder || '';

      const labelText = placeholder || name || (tagName + ' ' + type).trim() || tagName;

      if (controlId) {
        const label = document.createElement('label');
        label.htmlFor = controlId;
        label.textContent = labelText;
        label.setAttribute('style', 'position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);');
        if (control.parentElement) {
          control.parentElement.insertBefore(label, control);
        }
        const selector = tagName + '#' + controlId;
        changes.push({
          selector,
          changeType: 'add-element',
          original: '',
          modified: label.outerHTML.substring(0, 500),
        });
      } else {
        const selector = tagName +
          (String(control.className) ? '.' + String(control.className).split(' ')[0] : '') +
          (name ? '[name="' + name + '"]' : '');
        control.setAttribute('aria-label', labelText);
        changes.push({
          selector,
          changeType: 'add-attr',
          original: '',
          modified: 'aria-label="' + labelText + '"',
        });
      }
    }
  }

  return changes;
})();
