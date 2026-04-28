// AMT operator L13 — onfocus="this.blur()" keyboard trap on focusables
//
// WCAG: F55 / SC 2.1.1, 3.2.1. CAT: I (attribute addition only; visible
// effect only when user tabs, not at initial render).
//
// Limited to first 10 links + first 10 form controls. Source: apply-low.js
// block 13.
(() => {
  const changes = [];

  const focusableLinks = Array.from(document.querySelectorAll('a[href]'));
  for (let fi = 0; fi < Math.min(focusableLinks.length, 10); fi++) {
    const focusEl = focusableLinks[fi];
    if (focusEl && focusEl.tagName) {
      const focusSelector = focusEl.tagName.toLowerCase() +
        (focusEl.id ? '#' + focusEl.id : '');
      focusEl.setAttribute('onfocus', 'this.blur();');
      changes.push({
        selector: focusSelector,
        changeType: 'add-attr',
        original: '',
        modified: 'onfocus="this.blur();"',
      });
    }
  }

  const focusableControls = Array.from(document.querySelectorAll(
    'button, input, select, textarea, [tabindex]'
  ));
  for (let fci = 0; fci < Math.min(focusableControls.length, 10); fci++) {
    const fCtrl = focusableControls[fci];
    const fCtrlSelector = fCtrl.tagName.toLowerCase() +
      (fCtrl.id ? '#' + fCtrl.id : '');
    fCtrl.setAttribute('onfocus', 'this.blur();');
    changes.push({
      selector: fCtrlSelector,
      changeType: 'add-attr',
      original: '',
      modified: 'onfocus="this.blur();"',
    });
  }

  return changes;
})();
