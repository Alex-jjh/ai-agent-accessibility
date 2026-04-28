// AMT operator L12 — Duplicate IDs on adjacent elements (≤5 pairs)
//
// WCAG: F77 / SC 4.1.1 (Parsing). CAT: I (attribute value change only,
// no layout change).
//
// Cap at 5 pairs — full-page duplication would swamp downstream analysis
// with noise. Source: apply-low.js block 12.
(() => {
  const changes = [];

  // Idempotence guard: once L12 has run, it adds a sentinel element as
  // a body child. Any `body.innerHTML = '...'` reset clears the
  // sentinel (and all other children) automatically. Plan D's
  // re-injection detects the sentinel and no-ops on subsequent runs.
  if (document.body && document.body.querySelector(':scope > [data-variant-L12-sentinel]')) {
    return changes;
  }

  const elementsWithId = Array.from(document.querySelectorAll('[id]'));
  let dupCount = 0;
  for (let di = 0; di < elementsWithId.length - 1 && dupCount < 5; di++) {
    const el1 = elementsWithId[di];
    const el2 = elementsWithId[di + 1];
    if (el1.id && el2.id && el1.id !== el2.id && el1.tagName !== 'SCRIPT' && el2.tagName !== 'SCRIPT') {
      const origId2 = el2.id;
      el2.id = el1.id;
      changes.push({
        selector: el2.tagName.toLowerCase() + '#' + el1.id,
        changeType: 'replace',
        original: 'id="' + origId2 + '"',
        modified: 'id="' + el1.id + '" (duplicate of previous element)',
      });
      dupCount++;
      di++; // skip the element we just modified
    }
  }

  if (dupCount > 0 && document.body) {
    const sentinel = document.createElement('meta');
    sentinel.setAttribute('data-variant-L12-sentinel', '1');
    sentinel.setAttribute('hidden', '');
    document.body.appendChild(sentinel);
  }

  return changes;
})();
