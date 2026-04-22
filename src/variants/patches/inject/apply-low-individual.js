// Variant: Low — INDIVIDUAL PATCH MODE for visual equivalence ablation.
// Runs a single one of the 13 low-variant patches, selected by the
// `ONLY_PATCH_ID` key on window (set before evaluation).
//
// DO NOT USE FOR EXPERIMENTS. This file exists solely for the
// visual-equivalence validation study. The production variant pipeline uses
// apply-low.js which applies all 13 patches together.
//
// Usage (from Playwright):
//   await page.evaluate('window.__ONLY_PATCH_ID = 11');
//   const changes = await page.evaluate(jsCode);
//
// Patch IDs (matches numbered comments in apply-low.js):
//   1  — semantic landmark tags → div (nav, main, header, footer, article, section, aside)
//   2  — remove all aria-* and role attributes
//   3  — remove all <label> elements
//   4  — remove keyboard event handlers (onkeydown/up/press)
//   5  — wrap interactive elements in closed Shadow DOM
//   6  — replace h1-h6 with styled divs
//   7  — remove img alt/aria-label/title
//   8  — remove tabindex attributes
//   9  — replace thead/tbody/tfoot/th with divs
//   10 — remove html lang attribute
//   11 — replace <a href> with <span onclick="..."> (blue underlined)
//   12 — inject duplicate IDs
//   13 — add onfocus="this.blur()" (keyboard trap)
//
(() => {
  const onlyPatchId = window.__ONLY_PATCH_ID;
  if (typeof onlyPatchId !== 'number' || onlyPatchId < 1 || onlyPatchId > 13) {
    throw new Error('apply-low-individual: set window.__ONLY_PATCH_ID to 1..13');
  }
  const changes = [];

  if (onlyPatchId === 1) {
    const semanticTags = ['nav', 'main', 'header', 'footer', 'article', 'section', 'aside'];
    for (const tag of semanticTags) {
      const elements = Array.from(document.querySelectorAll(tag));
      for (const el of elements) {
        const originalHtml = el.outerHTML;
        const div = document.createElement('div');
        div.innerHTML = el.innerHTML;
        for (const attr of Array.from(el.attributes)) {
          if (attr.name !== 'role') div.setAttribute(attr.name, attr.value);
        }
        const revertId = '__variant_' + tag + '_' + changes.length;
        div.setAttribute('data-variant-revert', revertId);
        el.replaceWith(div);
        changes.push({ selector: '[data-variant-revert="' + revertId + '"]', changeType: 'replace',
          original: originalHtml.substring(0, 300), modified: div.outerHTML.substring(0, 300) });
      }
    }
  }

  else if (onlyPatchId === 2) {
    const ariaElements = Array.from(document.querySelectorAll(
      '[role], [aria-label], [aria-labelledby], [aria-describedby], [aria-hidden], [aria-expanded], [aria-haspopup], [aria-controls], [aria-live], [aria-atomic], [aria-relevant], [aria-busy], [aria-checked], [aria-selected], [aria-pressed], [aria-disabled], [aria-required], [aria-invalid], [aria-valuemin], [aria-valuemax], [aria-valuenow], [aria-valuetext]'
    ));
    for (const el of ariaElements) {
      const attrsToRemove = [];
      for (const attr of Array.from(el.attributes)) {
        if (attr.name === 'role' || attr.name.startsWith('aria-')) attrsToRemove.push(attr.name);
      }
      for (const attrName of attrsToRemove) {
        const originalValue = el.getAttribute(attrName) || '';
        el.removeAttribute(attrName);
        changes.push({ selector: el.tagName.toLowerCase(), changeType: 'remove-attr',
          original: attrName + '="' + originalValue + '"', modified: '' });
      }
    }
  }

  else if (onlyPatchId === 3) {
    const labels = Array.from(document.querySelectorAll('label'));
    for (const label of labels) {
      const originalHtml = label.outerHTML;
      label.remove();
      changes.push({ selector: 'label', changeType: 'remove-element',
        original: originalHtml.substring(0, 300), modified: '' });
    }
  }

  else if (onlyPatchId === 4) {
    const allInteractive = Array.from(document.querySelectorAll(
      'button, a, input, select, textarea, [tabindex], [onclick], [onkeydown], [onkeyup], [onkeypress]'
    ));
    for (const el of allInteractive) {
      for (const attr of ['onkeydown', 'onkeyup', 'onkeypress']) {
        if (el.hasAttribute(attr)) {
          const originalValue = el.getAttribute(attr) || '';
          el.removeAttribute(attr);
          changes.push({ selector: el.tagName.toLowerCase(), changeType: 'remove-handler',
            original: attr + '="' + originalValue + '"', modified: '' });
        }
      }
    }
  }

  else if (onlyPatchId === 5) {
    const interactiveForShadow = Array.from(document.querySelectorAll(
      'button, [role="button"], [role="link"], [role="checkbox"], [role="tab"], [role="menuitem"]'
    ));
    for (const el of interactiveForShadow) {
      if (el.parentElement && !el.parentElement.shadowRoot) {
        const wrapper = document.createElement('div');
        const originalHtml = el.outerHTML;
        el.parentElement.insertBefore(wrapper, el);
        const shadow = wrapper.attachShadow({ mode: 'closed' });
        shadow.appendChild(el);
        changes.push({ selector: el.tagName.toLowerCase(), changeType: 'replace',
          original: originalHtml.substring(0, 300),
          modified: '<div>[closed shadow containing: ' + el.tagName.toLowerCase() + ']</div>' });
      }
    }
  }

  else if (onlyPatchId === 6) {
    const headingTags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'];
    for (const tag of headingTags) {
      const headings = Array.from(document.querySelectorAll(tag));
      for (const heading of headings) {
        const originalHtml = heading.outerHTML;
        const div = document.createElement('div');
        div.innerHTML = heading.innerHTML;
        for (const attr of Array.from(heading.attributes)) {
          if (attr.name !== 'role') div.setAttribute(attr.name, attr.value);
        }
        const fontSize = { h1: '2em', h2: '1.5em', h3: '1.17em', h4: '1em', h5: '0.83em', h6: '0.67em' };
        div.style.fontSize = fontSize[tag] || '1em';
        div.style.fontWeight = 'bold';
        const revertId = '__variant_heading_' + tag + '_' + changes.length;
        div.setAttribute('data-variant-revert', revertId);
        heading.replaceWith(div);
        changes.push({ selector: '[data-variant-revert="' + revertId + '"]', changeType: 'replace',
          original: originalHtml.substring(0, 300), modified: div.outerHTML.substring(0, 300) });
      }
    }
  }

  else if (onlyPatchId === 7) {
    const images = Array.from(document.querySelectorAll('img'));
    for (const img of images) {
      for (const attrName of ['alt', 'aria-label', 'title']) {
        if (img.hasAttribute(attrName)) {
          const originalValue = img.getAttribute(attrName) || '';
          img.removeAttribute(attrName);
          changes.push({ selector: 'img', changeType: 'remove-attr',
            original: attrName + '="' + originalValue.substring(0, 100) + '"', modified: '' });
        }
      }
    }
  }

  else if (onlyPatchId === 8) {
    const tabindexEls = Array.from(document.querySelectorAll('[tabindex]'));
    for (const el of tabindexEls) {
      const origTabindex = el.getAttribute('tabindex') || '';
      el.removeAttribute('tabindex');
      changes.push({ selector: el.tagName.toLowerCase(), changeType: 'remove-attr',
        original: 'tabindex="' + origTabindex + '"', modified: '' });
    }
  }

  else if (onlyPatchId === 9) {
    const tableParts = ['thead', 'tbody', 'tfoot', 'th'];
    for (const tag of tableParts) {
      const els = Array.from(document.querySelectorAll(tag));
      for (const el of els) {
        const originalHtml = el.outerHTML;
        const replacement = document.createElement(tag === 'th' ? 'td' : 'div');
        replacement.innerHTML = el.innerHTML;
        for (const attr of Array.from(el.attributes)) {
          if (attr.name !== 'role') replacement.setAttribute(attr.name, attr.value);
        }
        const revertId = '__variant_table_' + tag + '_' + changes.length;
        replacement.setAttribute('data-variant-revert', revertId);
        el.replaceWith(replacement);
        changes.push({ selector: '[data-variant-revert="' + revertId + '"]', changeType: 'replace',
          original: originalHtml.substring(0, 300), modified: replacement.outerHTML.substring(0, 300) });
      }
    }
  }

  else if (onlyPatchId === 10) {
    const htmlEl = document.documentElement;
    if (htmlEl.hasAttribute('lang')) {
      const origLang = htmlEl.getAttribute('lang') || '';
      htmlEl.removeAttribute('lang');
      changes.push({ selector: 'html', changeType: 'remove-attr',
        original: 'lang="' + origLang + '"', modified: '' });
    }
  }

  else if (onlyPatchId === 11) {
    const allLinks = Array.from(document.querySelectorAll('a[href]'));
    for (const link of allLinks) {
      const linkHref = link.getAttribute('href') || '';
      const linkOriginal = link.outerHTML;
      const linkSpan = document.createElement('span');
      linkSpan.innerHTML = link.innerHTML;
      for (const attr of Array.from(link.attributes)) {
        if (attr.name !== 'href' && attr.name !== 'role') {
          linkSpan.setAttribute(attr.name, attr.value);
        }
      }
      linkSpan.setAttribute('onclick', "window.location.href='" + linkHref.replace(/'/g, "\\'") + "';");
      linkSpan.style.textDecoration = 'underline';
      linkSpan.style.cursor = 'pointer';
      linkSpan.style.color = 'blue';
      const linkRevertId = '__variant_link_' + changes.length;
      linkSpan.setAttribute('data-variant-revert', linkRevertId);
      link.replaceWith(linkSpan);
      changes.push({ selector: '[data-variant-revert="' + linkRevertId + '"]', changeType: 'replace',
        original: linkOriginal.substring(0, 300), modified: linkSpan.outerHTML.substring(0, 300) });
    }
  }

  else if (onlyPatchId === 12) {
    const elementsWithId = Array.from(document.querySelectorAll('[id]'));
    let dupCount = 0;
    for (let di = 0; di < elementsWithId.length - 1 && dupCount < 5; di++) {
      const el1 = elementsWithId[di];
      const el2 = elementsWithId[di + 1];
      if (el1.id && el2.id && el1.id !== el2.id && el1.tagName !== 'SCRIPT' && el2.tagName !== 'SCRIPT') {
        const origId2 = el2.id;
        el2.id = el1.id;
        changes.push({ selector: el2.tagName.toLowerCase() + '#' + el1.id, changeType: 'replace',
          original: 'id="' + origId2 + '"', modified: 'id="' + el1.id + '"' });
        dupCount++;
        di++;
      }
    }
  }

  else if (onlyPatchId === 13) {
    const focusableLinks = Array.from(document.querySelectorAll('a[href]'));
    for (let fi = 0; fi < Math.min(focusableLinks.length, 10); fi++) {
      const focusEl = focusableLinks[fi];
      if (focusEl && focusEl.tagName) {
        focusEl.setAttribute('onfocus', 'this.blur();');
        changes.push({ selector: focusEl.tagName.toLowerCase(), changeType: 'add-attr',
          original: '', modified: 'onfocus="this.blur();"' });
      }
    }
    const focusableControls = Array.from(document.querySelectorAll(
      'button, input, select, textarea, [tabindex]'
    ));
    for (let fci = 0; fci < Math.min(focusableControls.length, 10); fci++) {
      const fCtrl = focusableControls[fci];
      fCtrl.setAttribute('onfocus', 'this.blur();');
      changes.push({ selector: fCtrl.tagName.toLowerCase(), changeType: 'add-attr',
        original: '', modified: 'onfocus="this.blur();"' });
    }
  }

  return changes;
})();
