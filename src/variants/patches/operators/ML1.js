// AMT operator ML1 — <button> with empty text content → <div>
//
// WCAG: SC 4.1.2 (Name, Role, Value). Pseudo-compliance mode: simulates
// icon-only buttons that appear styled but lack accessible names.
//
// Source: apply-medium-low.js block 1.
(() => {
  const changes = [];
  let _rev = 0;

  const buttons = Array.from(document.querySelectorAll('button'));
  for (const btn of buttons) {
    const textContent = (btn.textContent || '').trim();
    if (textContent.length === 0) {
      const originalHtml = btn.outerHTML;
      const div = document.createElement('div');
      div.innerHTML = btn.innerHTML;
      for (const attr of Array.from(btn.attributes)) {
        if (attr.name !== 'type') {
          div.setAttribute(attr.name, attr.value);
        }
      }
      const selector = 'button' +
        (btn.id ? '#' + btn.id : String(btn.className) ? '.' + String(btn.className).split(' ')[0] : '');
      const revertId = '__variant_ML1_btn_' + (_rev++);
      div.setAttribute('data-variant-revert', revertId);
      btn.replaceWith(div);
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
