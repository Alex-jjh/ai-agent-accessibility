// AMT operator H8 — scope="col"/"row" on table header cells
//
// WCAG: SC 1.3.1. Positive enhancement. <th> inside <thead> gets
// scope="col"; <th> inside <tbody> (row header) gets scope="row".
// Only added if not already set.
//
// Source: apply-high.js block 8.
(() => {
  const changes = [];

  const tables = Array.from(document.querySelectorAll('table'));
  for (const table of tables) {
    const theadCells = Array.from(table.querySelectorAll('thead th:not([scope])'));
    for (const cell of theadCells) {
      cell.setAttribute('scope', 'col');
      changes.push({
        selector: 'th',
        changeType: 'add-attr',
        original: '',
        modified: 'scope="col"',
      });
    }
    const tbodyRowHeaders = Array.from(table.querySelectorAll('tbody th:not([scope])'));
    for (const cell of tbodyRowHeaders) {
      cell.setAttribute('scope', 'row');
      changes.push({
        selector: 'th',
        changeType: 'add-attr',
        original: '',
        modified: 'scope="row"',
      });
    }
  }

  return changes;
})();
