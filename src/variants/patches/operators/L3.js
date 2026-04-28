// AMT operator L3 — Remove all <label> elements
//
// WCAG: F68 / SC 4.1.2 (Name, Role, Value). CAT: II (form controls lose
// their visible label text entirely — visual impact).
//
// Source: apply-low.js block 3.
(() => {
  const changes = [];

  const labels = Array.from(document.querySelectorAll('label'));
  for (const label of labels) {
    const originalHtml = label.outerHTML;
    const selector = 'label' + (label.htmlFor ? '[for="' + label.htmlFor + '"]' : '');
    label.remove();
    changes.push({
      selector,
      changeType: 'remove-element',
      original: originalHtml.substring(0, 500),
      modified: '',
    });
  }

  return changes;
})();
