// Variant: Pure-Semantic-Low — Degrade ONLY a11y tree semantics
//
// Design principle: modify ONLY attributes that affect the browser's
// Accessibility Tree construction. ZERO changes to visual rendering,
// CSS layout, interactive functionality, or DOM structure.
//
// This is the causal isolation variant: if text-only agent fails under PSL
// but CUA (coordinate-based vision) agent succeeds → the a11y tree is
// definitively the causal mechanism for agent failure.
//
// Verified via smoke-psl-a11y-tree.py on Chromium headless:
//   - role="presentation" works on non-focusable elements (h1, nav, table)
//   - role="presentation" is IGNORED on focusable elements (<a>, <button>)
//   - aria-hidden="true" works on ALL elements including focusable ones
//
// Visual rendering: ZERO change (all CSS, layout, text content preserved)
// Interactive functionality: ZERO change (all href, onclick, tabindex preserved)
// A11y tree: severely degraded (landmarks, headings, links, buttons hidden)
//
// Contract: pure browser JS IIFE, returns DomChange[], no imports.
(() => {
  var changes = [];

  // 1. Landmarks → role="presentation" (removes landmark semantics from a11y tree)
  // Non-focusable elements: role="presentation" is respected by Chromium.
  // Visual: nav/main/header still render with their default/CSS styles.
  var landmarkTags = ['nav', 'main', 'header', 'footer', 'article', 'section', 'aside'];
  for (var li = 0; li < landmarkTags.length; li++) {
    var tag = landmarkTags[li];
    var elements = document.querySelectorAll(tag);
    for (var ei = 0; ei < elements.length; ei++) {
      var el = elements[ei];
      var revertId = '__psl_landmark_' + tag + '_' + changes.length;
      el.setAttribute('role', 'presentation');
      el.setAttribute('data-variant-revert', revertId);
      changes.push({
        selector: '[data-variant-revert="' + revertId + '"]',
        changeType: 'add-attr',
        original: '',
        modified: 'role="presentation"',
      });
    }
  }

  // 2. Remove all aria-* attributes globally (pure semantic — no visual/functional effect)
  // Same as current low #2 — already verified as pure semantic operation.
  var ariaSelector = '[role], [aria-label], [aria-labelledby], [aria-describedby], ' +
    '[aria-hidden], [aria-expanded], [aria-haspopup], [aria-controls], [aria-live], ' +
    '[aria-atomic], [aria-relevant], [aria-busy], [aria-checked], [aria-selected], ' +
    '[aria-pressed], [aria-disabled], [aria-required], [aria-invalid], ' +
    '[aria-valuemin], [aria-valuemax], [aria-valuenow], [aria-valuetext]';
  var ariaElements = document.querySelectorAll(ariaSelector);
  for (var ai = 0; ai < ariaElements.length; ai++) {
    var ael = ariaElements[ai];
    // Skip elements we just set role="presentation" on (don't remove our own patches)
    if (ael.getAttribute('data-variant-revert') &&
        ael.getAttribute('data-variant-revert').indexOf('__psl_') === 0) {
      continue;
    }
    var attrsToRemove = [];
    for (var ati = 0; ati < ael.attributes.length; ati++) {
      var attr = ael.attributes[ati];
      if (attr.name === 'role' || attr.name.indexOf('aria-') === 0) {
        attrsToRemove.push(attr.name);
      }
    }
    for (var ri = 0; ri < attrsToRemove.length; ri++) {
      var attrName = attrsToRemove[ri];
      var originalValue = ael.getAttribute(attrName) || '';
      ael.removeAttribute(attrName);
      changes.push({
        selector: ael.tagName.toLowerCase() + (ael.id ? '#' + ael.id : ''),
        changeType: 'remove-attr',
        original: attrName + '="' + originalValue.substring(0, 100) + '"',
        modified: '',
      });
    }
  }

  // 3. Labels → aria-hidden="true" + remove for association
  // Visual: label text STAYS visible on page (unlike current low which removes it).
  // A11y tree: label disappears, input loses its programmatic label association.
  // Functional: input still works, user can still type in it.
  var labels = document.querySelectorAll('label');
  for (var lbi = 0; lbi < labels.length; lbi++) {
    var label = labels[lbi];
    var revertId = '__psl_label_' + changes.length;
    label.setAttribute('aria-hidden', 'true');
    label.setAttribute('data-variant-revert', revertId);
    if (label.hasAttribute('for')) {
      var origFor = label.getAttribute('for');
      label.removeAttribute('for');
      changes.push({
        selector: '[data-variant-revert="' + revertId + '"]',
        changeType: 'remove-attr',
        original: 'for="' + origFor + '"',
        modified: 'aria-hidden="true" (label hidden from a11y tree)',
      });
    }
    changes.push({
      selector: '[data-variant-revert="' + revertId + '"]',
      changeType: 'add-attr',
      original: '',
      modified: 'aria-hidden="true"',
    });
  }

  // 4. [SKIP] Keyboard handler removal — pure functional, not semantic.
  // Current low #4 removes onkeydown/onkeyup. PSL does NOT do this.

  // 5. Interactive elements (buttons, [role=button]) → aria-hidden="true"
  // Replaces current low's Shadow DOM wrapping (which breaks CSS/functionality).
  // Visual: button still visible and clickable.
  // A11y tree: button and its subtree disappear.
  // Verified: Chromium respects aria-hidden on focusable button elements.
  var interactiveSelector = 'button, [role="tab"], [role="tabpanel"], [role="menuitem"]';
  var interactiveEls = document.querySelectorAll(interactiveSelector);
  for (var ii = 0; ii < interactiveEls.length; ii++) {
    var iel = interactiveEls[ii];
    // Don't double-hide elements already processed
    if (iel.getAttribute('aria-hidden') === 'true') continue;
    var revertId = '__psl_interactive_' + changes.length;
    iel.setAttribute('aria-hidden', 'true');
    iel.setAttribute('data-variant-revert', revertId);
    changes.push({
      selector: '[data-variant-revert="' + revertId + '"]',
      changeType: 'add-attr',
      original: '',
      modified: 'aria-hidden="true"',
    });
  }

  // 6. Headings (h1-h6) → role="presentation"
  // Visual: heading text stays with its original CSS styling (font-size, weight).
  // A11y tree: no longer recognized as heading — just plain text.
  // Verified: Chromium respects role="presentation" on non-focusable h1-h6.
  var headingTags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'];
  for (var hi = 0; hi < headingTags.length; hi++) {
    var htag = headingTags[hi];
    var headings = document.querySelectorAll(htag);
    for (var hei = 0; hei < headings.length; hei++) {
      var heading = headings[hei];
      var revertId = '__psl_heading_' + htag + '_' + changes.length;
      heading.setAttribute('role', 'presentation');
      heading.setAttribute('data-variant-revert', revertId);
      changes.push({
        selector: '[data-variant-revert="' + revertId + '"]',
        changeType: 'add-attr',
        original: '',
        modified: 'role="presentation"',
      });
    }
  }

  // 7. Remove img alt (pure semantic — same as current low #7)
  // Visual: image still displays. Alt only shows if image fails to load.
  var images = document.querySelectorAll('img[alt]');
  for (var imi = 0; imi < images.length; imi++) {
    var img = images[imi];
    var origAlt = img.getAttribute('alt') || '';
    img.removeAttribute('alt');
    changes.push({
      selector: 'img' + (img.id ? '#' + img.id : ''),
      changeType: 'remove-attr',
      original: 'alt="' + origAlt.substring(0, 100) + '"',
      modified: '',
    });
  }

  // 8. Tables → role="presentation" (removes table semantics)
  // Visual: table layout completely preserved (CSS table display unchanged).
  // A11y tree: no table/row/cell/columnheader roles — just flat text.
  var tables = document.querySelectorAll('table');
  for (var ti = 0; ti < tables.length; ti++) {
    var table = tables[ti];
    var revertId = '__psl_table_' + changes.length;
    table.setAttribute('role', 'presentation');
    table.setAttribute('data-variant-revert', revertId);
    changes.push({
      selector: '[data-variant-revert="' + revertId + '"]',
      changeType: 'add-attr',
      original: '',
      modified: 'role="presentation"',
    });
  }

  // 9. Remove html lang (pure semantic — same as current low #10)
  var htmlEl = document.documentElement;
  if (htmlEl.hasAttribute('lang')) {
    var origLang = htmlEl.getAttribute('lang') || '';
    htmlEl.removeAttribute('lang');
    changes.push({
      selector: 'html',
      changeType: 'remove-attr',
      original: 'lang="' + origLang + '"',
      modified: '',
    });
  }

  // 10. Links → aria-hidden="true" (hide from a11y tree, keep functional)
  // Visual: link text still visible, still blue/underlined, still clickable.
  // A11y tree: link disappears — agent can't see it as a navigable element.
  // Verified: Chromium respects aria-hidden on focusable <a> elements.
  // NOTE: role="presentation" does NOT work on <a> (Chromium ignores it).
  var links = document.querySelectorAll('a[href]');
  for (var lki = 0; lki < links.length; lki++) {
    var link = links[lki];
    // Don't double-hide
    if (link.getAttribute('aria-hidden') === 'true') continue;
    var revertId = '__psl_link_' + changes.length;
    link.setAttribute('aria-hidden', 'true');
    link.setAttribute('data-variant-revert', revertId);
    changes.push({
      selector: '[data-variant-revert="' + revertId + '"]',
      changeType: 'add-attr',
      original: '',
      modified: 'aria-hidden="true"',
    });
  }

  // 11. Duplicate IDs (pure semantic — same as current low #12)
  var elementsWithId = document.querySelectorAll('[id]');
  var dupCount = 0;
  for (var di = 0; di < elementsWithId.length - 1 && dupCount < 5; di++) {
    var el1 = elementsWithId[di];
    var el2 = elementsWithId[di + 1];
    if (el1.id && el2.id && el1.id !== el2.id &&
        el1.tagName !== 'SCRIPT' && el2.tagName !== 'SCRIPT') {
      var origId2 = el2.id;
      el2.id = el1.id;
      changes.push({
        selector: el2.tagName.toLowerCase() + '#' + el1.id,
        changeType: 'replace',
        original: 'id="' + origId2 + '"',
        modified: 'id="' + el1.id + '" (duplicate)',
      });
      dupCount++;
      di++;
    }
  }

  // [SKIP] #4 keyboard handlers, #13 onfocus blur — pure functional, not semantic.

  return changes;
})();
