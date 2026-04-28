// AMT operator L6 — h1-h6 headings → div with font-size preserved
//
// WCAG: F2 / SC 1.3.1. CAT: II (div's default font-size is 1em, overridden
// here by inline style but CSS specificity/inheritance can differ).
//
// Source: apply-low.js block 6.
(() => {
  const changes = [];
  let _rev = 0;

  const headingTags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'];
  for (const tag of headingTags) {
    const headings = Array.from(document.querySelectorAll(tag));
    for (const heading of headings) {
      const originalHtml = heading.outerHTML;
      const div = document.createElement('div');
      div.innerHTML = heading.innerHTML;
      for (const attr of Array.from(heading.attributes)) {
        if (attr.name !== 'role') {
          div.setAttribute(attr.name, attr.value);
        }
      }
      const fontSize = { h1: '2em', h2: '1.5em', h3: '1.17em', h4: '1em', h5: '0.83em', h6: '0.67em' };
      div.style.fontSize = fontSize[tag] || '1em';
      div.style.fontWeight = 'bold';
      const revertId = '__variant_L6_heading_' + tag + '_' + (_rev++);
      div.setAttribute('data-variant-revert', revertId);
      heading.replaceWith(div);
      changes.push({
        selector: '[data-variant-revert="' + revertId + '"]',
        changeType: 'replace',
        original: originalHtml.substring(0, 500),
        modified: div.outerHTML.substring(0, 500),
      });
    }
  }

  return changes;
})();
