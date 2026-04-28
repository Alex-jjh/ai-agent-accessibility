// AMT operator L5 — Wrap interactive elements in closed Shadow DOM
//
// No direct WCAG equivalent. Novel operator. CAT: II (closed shadow root
// resets CSS cascade at the boundary; Stripe-Elements-like visual effect).
//
// Source: apply-low.js block 5.
(() => {
  const changes = [];

  const interactiveForShadow = Array.from(document.querySelectorAll(
    'button, [role="button"], [role="link"], [role="checkbox"], [role="tab"], [role="menuitem"]'
  ));
  for (const el of interactiveForShadow) {
    if (el.parentElement && !el.parentElement.shadowRoot) {
      const wrapper = document.createElement('div');
      const originalHtml = el.outerHTML;
      const selector = el.tagName.toLowerCase() +
        (el.id ? '#' + el.id : String(el.className) ? '.' + String(el.className).split(' ')[0] : '');
      el.parentElement.insertBefore(wrapper, el);
      const shadow = wrapper.attachShadow({ mode: 'closed' });
      shadow.appendChild(el);
      changes.push({
        selector,
        changeType: 'replace',
        original: originalHtml.substring(0, 500),
        modified: '<div>[closed shadow containing: ' + el.tagName.toLowerCase() + ']</div>',
      });
    }
  }

  return changes;
})();
