// AMT operator H6 — aria-required="true" for required form inputs
//
// WCAG: SC 3.3.2 (Labels or Instructions) — also informs 4.1.2.
// Positive enhancement. Reads the HTML `required` attribute and mirrors
// it as an explicit ARIA state (some AT stacks prefer the ARIA form).
//
// Source: apply-high.js block 6.
(() => {
  const changes = [];

  const requiredInputs = Array.from(document.querySelectorAll(
    'input[required], select[required], textarea[required]'
  ));
  for (const input of requiredInputs) {
    if (!input.hasAttribute('aria-required')) {
      const reqSelector = input.tagName.toLowerCase() +
        (input.id ? '#' + input.id
                  : input.getAttribute('name') ? '[name="' + input.getAttribute('name') + '"]' : '');
      input.setAttribute('aria-required', 'true');
      changes.push({
        selector: reqSelector,
        changeType: 'add-attr',
        original: '',
        modified: 'aria-required="true"',
      });
    }
  }

  return changes;
})();
