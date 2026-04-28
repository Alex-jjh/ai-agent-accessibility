// AMT operator H5c — aria-label for empty-text <a> (derived from href)
//
// WCAG: SC 2.4.4 (Link Purpose, In Context). Positive enhancement.
// Surrogate: label is "Link to {lastSegment}" — purely structural, not
// content-aware. Source: apply-high.js block 5c.
(() => {
  const changes = [];

  const emptyLinks = Array.from(document.querySelectorAll('a:not([aria-label])'));
  for (const link of emptyLinks) {
    const text = (link.textContent || '').trim();
    if (!text && !link.getAttribute('aria-labelledby') && !link.getAttribute('title')) {
      const href = link.getAttribute('href') || '';
      const labelText = href ? 'Link to ' + (href.split('/').pop() || 'page') : 'link';
      const selector = 'a' +
        (link.id ? '#' + link.id : String(link.className) ? '.' + String(link.className).split(' ')[0] : '');
      link.setAttribute('aria-label', labelText);
      changes.push({
        selector,
        changeType: 'add-attr',
        original: '',
        modified: 'aria-label="' + labelText + '"',
      });
    }
  }

  return changes;
})();
