// Variant: Low (Level 0) — Aggressively degrade accessibility
// Extracted from patches/index.ts applyLow() for shared use by TS and Python bridge.
// Contract: pure browser JS IIFE, returns DomChange[], no imports.
(() => {
  const changes = [];

  // 1. Replace semantic elements with divs
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

  // 2. Remove all aria-* attributes and role attributes
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

  // 3. Remove all <label> elements
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

  // 4. Remove keyboard event handlers from all elements
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

  // 5. Wrap interactive elements in closed Shadow DOM to hide from A11y tree
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

  // 6. Replace heading elements (h1-h6) with styled divs — breaks document outline
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

  // 7. Remove alt text from images — breaks image accessibility
  const images = Array.from(document.querySelectorAll('img[alt]'));
  for (const img of images) {
    var originalAlt = img.getAttribute('alt') || '';
    if (originalAlt) {
      var imgSelector = 'img' + (img.id ? '#' + img.id : String(img.className) ? '.' + String(img.className).split(' ')[0] : '');
      img.removeAttribute('alt');
      changes.push({
        selector: imgSelector,
        changeType: 'remove-attr',
        original: 'alt="' + originalAlt.substring(0, 100) + '"',
        modified: '',
      });
    }
  }

  // 8. Remove tabindex attributes — breaks keyboard navigation order
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

  // 9. Break table semantics — replace table/thead/tbody/th with divs
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

  // 10. Remove lang attribute from html element
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

  return changes;
})();
