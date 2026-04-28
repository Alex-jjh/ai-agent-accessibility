// AMT operator H7 — aria-current="page" on links matching current URL
//
// WCAG: SC 2.4.8 (Location). Positive enhancement. Reads
// window.location.pathname — one of only two operators that reads
// location state (H7 and nothing else currently). Wrapped in try/catch
// because some sandboxed iframes throw on location access.
//
// Source: apply-high.js block 7.
(() => {
  const changes = [];

  try {
    const currentPath = window.location.pathname;
    const navLinks = Array.from(document.querySelectorAll(
      'nav a[href], [role="navigation"] a[href]'
    ));
    for (const navLink of navLinks) {
      const linkHref = navLink.getAttribute('href') || '';
      if (linkHref === currentPath || linkHref === window.location.href) {
        if (!navLink.hasAttribute('aria-current')) {
          const navSelector = 'a' + (navLink.id ? '#' + navLink.id : '');
          navLink.setAttribute('aria-current', 'page');
          changes.push({
            selector: navSelector,
            changeType: 'add-attr',
            original: '',
            modified: 'aria-current="page"',
          });
        }
      }
    }
  } catch (e) { /* non-fatal */ }

  return changes;
})();
