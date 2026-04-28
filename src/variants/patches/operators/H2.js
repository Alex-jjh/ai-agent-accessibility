// AMT operator H2 — Insert skip-navigation link at body end
//
// WCAG: SC 2.4.1 (Bypass Blocks). Positive enhancement.
//
// IMPORTANT: Inserted at body END, not start. Inserting at body.firstChild
// shifts ALL subsequent BrowserGym node IDs by +1, which creates a latent
// element-targeting risk where click("42") targets different elements in
// high vs base. Appending at the end keeps IDs stable. Skip-link
// functionality works via href="#main-content" anchor, so position doesn't
// matter for functionality.
//
// Source: apply-high.js block 2.
(() => {
  const changes = [];

  const existingSkipLink = document.querySelector('a.skip-link, a[href="#main-content"]');
  if (!existingSkipLink) {
    const skipLink = document.createElement('a');
    skipLink.href = '#main-content';
    skipLink.className = 'skip-link';
    skipLink.textContent = 'Skip to main content';
    skipLink.setAttribute('tabindex', '1');
    skipLink.setAttribute('style',
      'position:absolute;top:-40px;left:0;background:#000;color:#fff;padding:8px;z-index:10000;' +
      'transition:top 0.3s;');
    skipLink.addEventListener('focus', function() { skipLink.style.top = '0'; });
    skipLink.addEventListener('blur', function() { skipLink.style.top = '-40px'; });

    const body = document.body;
    body.appendChild(skipLink);

    const mainEl = document.querySelector('main') || document.querySelector('[role="main"]');
    if (mainEl && !mainEl.id) {
      mainEl.id = 'main-content';
    } else if (!mainEl) {
      const firstContent = document.querySelector('.content, #content, .main, #main');
      if (firstContent && !firstContent.id) {
        firstContent.id = 'main-content';
      }
    }

    changes.push({
      selector: 'body > a.skip-link',
      changeType: 'add-element',
      original: '',
      modified: skipLink.outerHTML.substring(0, 500),
    });
  }

  return changes;
})();
