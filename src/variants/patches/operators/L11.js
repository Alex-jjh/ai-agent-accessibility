// AMT operator L11 — <a href> → <span onclick> (keep blue underline)
//
// WCAG: F42 / SC 1.3.1, 2.1.1. CAT: II (user-agent stylesheet for <a>
// defines color/text-decoration; <span> inherits parent; inline styles
// added but computed result may still differ).
//
// Source: apply-low.js block 11.
(() => {
  const changes = [];
  let _rev = 0;

  const allLinks = Array.from(document.querySelectorAll('a[href]'));
  for (const link of allLinks) {
    const linkHref = link.getAttribute('href') || '';
    const linkOriginal = link.outerHTML;
    const linkSpan = document.createElement('span');
    linkSpan.innerHTML = link.innerHTML;
    for (const linkAttr of Array.from(link.attributes)) {
      if (linkAttr.name !== 'href' && linkAttr.name !== 'role') {
        linkSpan.setAttribute(linkAttr.name, linkAttr.value);
      }
    }
    linkSpan.setAttribute('onclick', "window.location.href='" + linkHref.replace(/'/g, "\\'") + "';");
    linkSpan.style.textDecoration = 'underline';
    linkSpan.style.cursor = 'pointer';
    linkSpan.style.color = 'blue';
    const linkRevertId = '__variant_L11_link_' + (_rev++);
    linkSpan.setAttribute('data-variant-revert', linkRevertId);
    link.replaceWith(linkSpan);
    changes.push({
      selector: '[data-variant-revert="' + linkRevertId + '"]',
      changeType: 'replace',
      original: linkOriginal.substring(0, 300),
      modified: linkSpan.outerHTML.substring(0, 300),
    });
  }

  return changes;
})();
