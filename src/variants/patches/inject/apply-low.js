// Variant: Low (Level 0) — Aggressively degrade accessibility
// Extracted from patches/index.ts applyLow() for shared use by TS and Python bridge.
// Contract: pure browser JS IIFE, returns DomChange[], no imports.
(() => {
  const changes = [];

  // 1. [Extension E1] Replace semantic landmark elements with divs — breaks page structure
  // No direct Ma11y equivalent (Ma11y F2 only targets headings). Novel extension to all HTML5 landmarks.
  // Reference: WCAG SC 1.3.1 (Info and Relationships)
  const semanticTags = ['nav', 'main', 'header', 'footer', 'article', 'section', 'aside'];
  for (const tag of semanticTags) {
    const elements = Array.from(document.querySelectorAll(tag));
    for (const el of elements) {
      const originalHtml = el.outerHTML;
      const div = document.createElement('div');
      div.innerHTML = el.innerHTML;
      for (const attr of Array.from(el.attributes)) {
        if (attr.name !== 'role') {
          div.setAttribute(attr.name, attr.value);
        }
      }
      const selector = tag + (el.id ? '#' + el.id : String(el.className) ? '.' + String(el.className).split(' ')[0] : '');
      const revertId = '__variant_' + tag + '_' + changes.length;
      div.setAttribute('data-variant-revert', revertId);
      el.replaceWith(div);
      changes.push({
        selector: '[data-variant-revert="' + revertId + '"]',
        changeType: 'replace',
        original: originalHtml.substring(0, 500),
        modified: div.outerHTML.substring(0, 500),
      });
    }
  }

  // 2. [Ma11y F96/CBL superset] Remove all aria-* attributes and role attributes
  // Ma11y F96 corrupts aria-label with random strings on buttons (SC 2.5.3).
  // We extend to remove ALL aria-* and role attrs on ALL elements — more aggressive.
  const ariaElements = Array.from(document.querySelectorAll('[role], [aria-label], [aria-labelledby], [aria-describedby], [aria-hidden], [aria-expanded], [aria-haspopup], [aria-controls], [aria-live], [aria-atomic], [aria-relevant], [aria-busy], [aria-checked], [aria-selected], [aria-pressed], [aria-disabled], [aria-required], [aria-invalid], [aria-valuemin], [aria-valuemax], [aria-valuenow], [aria-valuetext]'));
  for (const el of ariaElements) {
    const attrsToRemove = [];
    for (const attr of Array.from(el.attributes)) {
      if (attr.name === 'role' || attr.name.startsWith('aria-')) {
        attrsToRemove.push(attr.name);
      }
    }
    for (const attrName of attrsToRemove) {
      const originalValue = el.getAttribute(attrName) || '';
      const selector = el.tagName.toLowerCase() +
        (el.id ? '#' + el.id : String(el.className) ? '.' + String(el.className).split(' ')[0] : '');
      el.removeAttribute(attrName);
      changes.push({
        selector,
        changeType: 'remove-attr',
        original: attrName + '="' + originalValue + '"',
        modified: '',
      });
    }
  }

  // 3. [Ma11y F68/RIN] Remove all <label> elements — breaks form control identification
  // Reference: WCAG F68 (SC 4.1.2) — form input not associated with label
  const labels = Array.from(document.querySelectorAll('label'));
  for (const label of labels) {
    const originalHtml = label.outerHTML;
    const selector = 'label' + (label.htmlFor ? '[for="' + label.htmlFor + '"]' : '');
    label.remove();
    changes.push({
      selector,
      changeType: 'remove-element',
      original: originalHtml.substring(0, 500),
      modified: '',
    });
  }

  // 4. [Ma11y F54/CDP related] Remove keyboard event handlers from all elements
  // Ma11y F54 replaces onclick→onmousedown (device-dependent). We remove keyboard handlers.
  // Reference: WCAG SC 2.1.1 (Keyboard)
  const allInteractive = Array.from(document.querySelectorAll(
    'button, a, input, select, textarea, [tabindex], [onclick], [onkeydown], [onkeyup], [onkeypress]'
  ));
  for (const el of allInteractive) {
    const handlerAttrs = ['onkeydown', 'onkeyup', 'onkeypress'];
    for (const attr of handlerAttrs) {
      if (el.hasAttribute(attr)) {
        const originalValue = el.getAttribute(attr) || '';
        const selector = el.tagName.toLowerCase() +
          (el.id ? '#' + el.id : String(el.className) ? '.' + String(el.className).split(' ')[0] : '');
        el.removeAttribute(attr);
        changes.push({
          selector,
          changeType: 'remove-handler',
          original: attr + '="' + originalValue + '"',
          modified: '',
        });
      }
    }
  }

  // 5. [Extension E2] Wrap interactive elements in closed Shadow DOM — hides from a11y tree
  // Novel operator: no Ma11y equivalent. Tests agent discovery of Shadow DOM-hidden elements.
  const interactiveForShadow = Array.from(document.querySelectorAll(
    'button, [role="button"], [role="link"], [role="checkbox"], [role="tab"], [role="menuitem"]'
  ));
  for (const el of interactiveForShadow) {
    if (el.parentElement && !el.parentElement.shadowRoot) {
      const wrapper = document.createElement('div');
      const originalHtml = el.outerHTML;
      const selector = el.tagName.toLowerCase() +
        (el.id ? '#' + el.id : String(el.className) ? '.' + String(el.className).split(' ')[0] : '');
      el.parentElement.insertBefore(wrapper, el);
      const shadow = wrapper.attachShadow({ mode: 'closed' });
      shadow.appendChild(el);
      changes.push({
        selector,
        changeType: 'replace',
        original: originalHtml.substring(0, 500),
        modified: '<div>[closed shadow containing: ' + el.tagName.toLowerCase() + ']</div>',
      });
    }
  }

  // 6. [Ma11y F2/RHP] Replace heading elements (h1-h6) with styled divs — breaks document outline
  // Reference: WCAG F2 (SC 1.3.1) — using CSS to include heading presentation without semantic markup
  // Ma11y F2 targets h2→p only; we extend to all heading levels h1-h6→div.
  const headingTags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'];
  for (const tag of headingTags) {
    const headings = Array.from(document.querySelectorAll(tag));
    for (const heading of headings) {
      const originalHtml = heading.outerHTML;
      const div = document.createElement('div');
      div.innerHTML = heading.innerHTML;
      // Copy non-semantic attributes
      for (const attr of Array.from(heading.attributes)) {
        if (attr.name !== 'role') {
          div.setAttribute(attr.name, attr.value);
        }
      }
      // Apply visual styling to maintain appearance without semantics
      var fontSize = { h1: '2em', h2: '1.5em', h3: '1.17em', h4: '1em', h5: '0.83em', h6: '0.67em' };
      div.style.fontSize = fontSize[tag] || '1em';
      div.style.fontWeight = 'bold';
      var revertId = '__variant_heading_' + tag + '_' + changes.length;
      div.setAttribute('data-variant-revert', revertId);
      heading.replaceWith(div);
      changes.push({
        selector: '[data-variant-revert="' + revertId + '"]',
        changeType: 'replace',
        original: originalHtml.substring(0, 500),
        modified: div.outerHTML.substring(0, 500),
      });
    }
  }

  // 7. [Ma11y F65/RIA] Remove alt text from images — breaks image accessibility
  // Reference: WCAG F65 (SC 1.1.1) — omitting alt attribute on img elements
  // Enhanced: also remove aria-label and title (full F65 alignment)
  var images = Array.from(document.querySelectorAll('img'));
  for (var ii = 0; ii < images.length; ii++) {
    var img = images[ii];
    var imgSelector = 'img' + (img.id ? '#' + img.id : String(img.className) ? '.' + String(img.className).split(' ')[0] : '');
    // Remove alt
    if (img.hasAttribute('alt')) {
      var originalAlt = img.getAttribute('alt') || '';
      img.removeAttribute('alt');
      changes.push({
        selector: imgSelector,
        changeType: 'remove-attr',
        original: 'alt="' + originalAlt.substring(0, 100) + '"',
        modified: '',
      });
    }
    // Remove aria-label and title (full F65 scope)
    var imgExtraAttrs = ['aria-label', 'title'];
    for (var iei = 0; iei < imgExtraAttrs.length; iei++) {
      if (img.hasAttribute(imgExtraAttrs[iei])) {
        var imgExtraVal = img.getAttribute(imgExtraAttrs[iei]) || '';
        img.removeAttribute(imgExtraAttrs[iei]);
        changes.push({
          selector: imgSelector,
          changeType: 'remove-attr',
          original: imgExtraAttrs[iei] + '="' + imgExtraVal.substring(0, 100) + '"',
          modified: '',
        });
      }
    }
  }

  // 8. [Ma11y F44/CTO related] Remove tabindex attributes — breaks keyboard navigation order
  // Ma11y F44 reverses tabindex order; we remove tabindex entirely.
  // Reference: WCAG F44 (SC 2.4.3) — using tabindex to create tab order that doesn't preserve meaning
  const tabindexEls = Array.from(document.querySelectorAll('[tabindex]'));
  for (const el of tabindexEls) {
    var origTabindex = el.getAttribute('tabindex') || '';
    var tabSelector = el.tagName.toLowerCase() +
      (el.id ? '#' + el.id : String(el.className) ? '.' + String(el.className).split(' ')[0] : '');
    el.removeAttribute('tabindex');
    changes.push({
      selector: tabSelector,
      changeType: 'remove-attr',
      original: 'tabindex="' + origTabindex + '"',
      modified: '',
    });
  }

  // 9. [Ma11y F91/RHD] Break table semantics — replace table/thead/tbody/th with divs
  // Reference: WCAG F91 (SC 1.3.1) — not correctly marking up table headers
  // Ma11y F91 replaces th→td only; we also flatten thead/tbody/tfoot→div.
  var tableParts = ['thead', 'tbody', 'tfoot', 'th'];
  for (var tp = 0; tp < tableParts.length; tp++) {
    var tpTag = tableParts[tp];
    var tpEls = Array.from(document.querySelectorAll(tpTag));
    for (var tpi = 0; tpi < tpEls.length; tpi++) {
      var tpEl = tpEls[tpi];
      var tpOriginal = tpEl.outerHTML;
      var tpDiv = document.createElement(tpTag === 'th' ? 'td' : 'div');
      tpDiv.innerHTML = tpEl.innerHTML;
      for (var ai = 0; ai < tpEl.attributes.length; ai++) {
        var tpAttr = tpEl.attributes[ai];
        if (tpAttr.name !== 'role') {
          tpDiv.setAttribute(tpAttr.name, tpAttr.value);
        }
      }
      var tpRevertId = '__variant_table_' + tpTag + '_' + changes.length;
      tpDiv.setAttribute('data-variant-revert', tpRevertId);
      tpEl.replaceWith(tpDiv);
      changes.push({
        selector: '[data-variant-revert="' + tpRevertId + '"]',
        changeType: 'replace',
        original: tpOriginal.substring(0, 300),
        modified: tpDiv.outerHTML.substring(0, 300),
      });
    }
  }

  // 10. Remove lang attribute from html element [Extension E3 — SC 3.1.1]
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

  // 11. [Ma11y F42/RAS] Replace <a> links with <span> + onclick — breaks link semantics
  // Reference: WCAG F42 (SC 1.3.1, 2.1.1) — Using scripting events to emulate links
  // Agent impact: a11y tree shows <span> instead of <a>, agent cannot identify navigable links
  var allLinks = Array.from(document.querySelectorAll('a[href]'));
  for (var li = 0; li < allLinks.length; li++) {
    var link = allLinks[li];
    var linkHref = link.getAttribute('href') || '';
    var linkOriginal = link.outerHTML;
    var linkSpan = document.createElement('span');
    linkSpan.innerHTML = link.innerHTML;
    for (var lai = 0; lai < link.attributes.length; lai++) {
      var linkAttr = link.attributes[lai];
      if (linkAttr.name !== 'href' && linkAttr.name !== 'role') {
        linkSpan.setAttribute(linkAttr.name, linkAttr.value);
      }
    }
    linkSpan.setAttribute('onclick', "window.location.href='" + linkHref.replace(/'/g, "\\'") + "';");
    linkSpan.style.textDecoration = 'underline';
    linkSpan.style.cursor = 'pointer';
    linkSpan.style.color = 'blue';
    var linkRevertId = '__variant_link_' + changes.length;
    linkSpan.setAttribute('data-variant-revert', linkRevertId);
    link.replaceWith(linkSpan);
    changes.push({
      selector: '[data-variant-revert="' + linkRevertId + '"]',
      changeType: 'replace',
      original: linkOriginal.substring(0, 300),
      modified: linkSpan.outerHTML.substring(0, 300),
    });
  }

  // 12. [Ma11y F77/MDI] Inject duplicate IDs on adjacent elements — breaks ARIA references
  // Reference: WCAG F77 (SC 4.1.1) — Failure of SC 4.1.1 due to duplicate values of type ID
  // Agent impact: aria-labelledby/aria-describedby resolve to wrong element
  var elementsWithId = Array.from(document.querySelectorAll('[id]'));
  var dupCount = 0;
  for (var di = 0; di < elementsWithId.length - 1 && dupCount < 5; di++) {
    var el1 = elementsWithId[di];
    var el2 = elementsWithId[di + 1];
    if (el1.id && el2.id && el1.id !== el2.id && el1.tagName !== 'SCRIPT' && el2.tagName !== 'SCRIPT') {
      var origId2 = el2.id;
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

  // 13. [Ma11y F55/RFA] Add onfocus="this.blur()" to focusable links — keyboard trap
  // Reference: WCAG F55 (SC 2.1.1, 3.2.1) — Using script to remove focus when focus is received
  // Agent impact: keyboard navigation gets stuck, agent cannot tab through interactive elements
  var focusableLinks = Array.from(document.querySelectorAll('a[href]'));
  for (var fi = 0; fi < Math.min(focusableLinks.length, 10); fi++) {
    var focusEl = focusableLinks[fi];
    // Note: after patch #11, these are now <span> elements, but onfocus still applies
    // if any <a> survived (e.g. inside shadow DOM or dynamically added)
    if (focusEl && focusEl.tagName) {
      var focusSelector = focusEl.tagName.toLowerCase() +
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
  // Also apply to buttons and inputs for broader keyboard trap effect
  var focusableControls = Array.from(document.querySelectorAll('button, input, select, textarea, [tabindex]'));
  for (var fci = 0; fci < Math.min(focusableControls.length, 10); fci++) {
    var fCtrl = focusableControls[fci];
    var fCtrlSelector = fCtrl.tagName.toLowerCase() +
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
