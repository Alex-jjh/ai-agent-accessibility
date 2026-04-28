// AMT operator H5b — Add lang="en" to <html>
//
// WCAG: SC 3.1.1 (Language of Page). Positive enhancement. Hardcoded to
// "en" for WebArena apps (all English). Real enhancement would detect
// content language. Paper notes this as a surrogate enhancement.
//
// Source: apply-high.js block 5b.
(() => {
  const changes = [];

  const htmlEl = document.documentElement;
  if (!htmlEl.hasAttribute('lang')) {
    htmlEl.setAttribute('lang', 'en');
    changes.push({
      selector: 'html',
      changeType: 'add-attr',
      original: '',
      modified: 'lang="en"',
    });
  }

  return changes;
})();
