// AMT operator H5a — Auto-generate alt from img filename
//
// WCAG: SC 1.1.1. Positive enhancement, SURROGATE: the alt text is
// derived from the image src filename (last path segment, extension
// stripped, hyphens/underscores → spaces). Not semantically accurate;
// real production enhancement would use ML vision. Paper discloses this
// as a surrogate enhancement.
//
// Source: apply-high.js block 5a.
(() => {
  const changes = [];

  const images = Array.from(document.querySelectorAll('img:not([alt])'));
  for (const img of images) {
    const src = img.getAttribute('src') || '';
    const altText = (src.split('/').pop() || 'image').replace(/\.[^.]+$/, '').replace(/[-_]/g, ' ') || 'image';
    const selector = 'img' +
      (img.id ? '#' + img.id : String(img.className) ? '.' + String(img.className).split(' ')[0] : '');
    img.setAttribute('alt', altText);
    changes.push({
      selector,
      changeType: 'add-attr',
      original: '',
      modified: 'alt="' + altText + '"',
    });
  }

  return changes;
})();
