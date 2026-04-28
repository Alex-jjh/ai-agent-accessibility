// AMT operator L9 — thead/tbody/tfoot/th → div/td (table semantics)
//
// WCAG: F91 / SC 1.3.1. CAT: II (table layout CSS relies on these tags;
// replacing them collapses row/column structure visually).
//
// Source: apply-low.js block 9.
(() => {
  const changes = [];
  let _rev = 0;

  const tableParts = ['thead', 'tbody', 'tfoot', 'th'];
  for (const tpTag of tableParts) {
    const tpEls = Array.from(document.querySelectorAll(tpTag));
    for (const tpEl of tpEls) {
      const tpOriginal = tpEl.outerHTML;
      const tpDiv = document.createElement(tpTag === 'th' ? 'td' : 'div');
      tpDiv.innerHTML = tpEl.innerHTML;
      for (const tpAttr of Array.from(tpEl.attributes)) {
        if (tpAttr.name !== 'role') {
          tpDiv.setAttribute(tpAttr.name, tpAttr.value);
        }
      }
      const tpRevertId = '__variant_L9_table_' + tpTag + '_' + (_rev++);
      tpDiv.setAttribute('data-variant-revert', tpRevertId);
      tpEl.replaceWith(tpDiv);
      changes.push({
        selector: '[data-variant-revert="' + tpRevertId + '"]',
        changeType: 'replace',
        original: tpOriginal.substring(0, 300),
        modified: tpDiv.outerHTML.substring(0, 300),
      });
    }
  }

  return changes;
})();
