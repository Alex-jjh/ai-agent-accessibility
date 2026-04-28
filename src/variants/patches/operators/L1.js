// AMT operator L1 — Semantic landmark tags → <div>
//
// WCAG: SC 1.3.1 (Info and Relationships). CAT: II (visual-degrading — loses
// user-agent default styles for nav/main/header/footer/article/section/aside).
//
// Source: apply-low.js block 1. Verbatim except for local revert counter.
// See docs/amt-operator-spec.md §2, §7.1 for the contract and rationale.
(() => {
  const changes = [];
  let _rev = 0;

  const semanticTags = ['nav', 'main', 'header', 'footer', 'article', 'section', 'aside'];
  for (const tag of semanticTags) {
    const elements = Array.from(document.querySelectorAll(tag));
    for (const el of elements) {
      const originalHtml = el.outerHTML;
      const div = document.createElement('div');
      div.innerHTML = el.innerHTML;
      for (const attr of Array.from(el.attributes)) {
        if (attr.name !== 'role') {
          div.setAttribute(attr.name, attr.value);
        }
      }
      const revertId = '__variant_L1_' + tag + '_' + (_rev++);
      div.setAttribute('data-variant-revert', revertId);
      el.replaceWith(div);
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
