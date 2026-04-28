// AMT operator L10 — Remove <html lang> attribute
//
// WCAG: SC 3.1.1 (Language of Page). CAT: I (attribute removal only).
//
// Source: apply-low.js block 10.
(() => {
  const changes = [];

  const htmlEl = document.documentElement;
  if (htmlEl.hasAttribute('lang')) {
    const origLang = htmlEl.getAttribute('lang') || '';
    htmlEl.removeAttribute('lang');
    changes.push({
      selector: 'html',
      changeType: 'remove-attr',
      original: 'lang="' + origLang + '"',
      modified: '',
    });
  }

  return changes;
})();
