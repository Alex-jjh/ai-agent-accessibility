// AMT operator L7 — Remove alt + aria-label + title from images
//
// WCAG: F65 / SC 1.1.1 (Non-text Content). CAT: I (attributes only; no
// layout or visual change since alt only shows when image fails to load).
//
// Source: apply-low.js block 7.
(() => {
  const changes = [];

  const images = Array.from(document.querySelectorAll('img'));
  for (const img of images) {
    const imgSelector = 'img' +
      (img.id ? '#' + img.id : String(img.className) ? '.' + String(img.className).split(' ')[0] : '');
    if (img.hasAttribute('alt')) {
      const originalAlt = img.getAttribute('alt') || '';
      img.removeAttribute('alt');
      changes.push({
        selector: imgSelector,
        changeType: 'remove-attr',
        original: 'alt="' + originalAlt.substring(0, 100) + '"',
        modified: '',
      });
    }
    const imgExtraAttrs = ['aria-label', 'title'];
    for (const attrName of imgExtraAttrs) {
      if (img.hasAttribute(attrName)) {
        const extraVal = img.getAttribute(attrName) || '';
        img.removeAttribute(attrName);
        changes.push({
          selector: imgSelector,
          changeType: 'remove-attr',
          original: attrName + '="' + extraVal.substring(0, 100) + '"',
          modified: '',
        });
      }
    }
  }

  return changes;
})();
