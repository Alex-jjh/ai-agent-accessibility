// Variant: High (Level 2) — Enhance accessibility
// Extracted from patches/index.ts applyHigh() for shared use by TS and Python bridge.
// Contract: pure browser JS IIFE, returns DomChange[], no imports.
(() => {
  const changes = [];

  // 1. Add aria-label to interactive elements missing accessible names
  const interactiveSelectors = 'a, button, input, select, textarea, [role="button"], [role="link"], [role="checkbox"], [role="tab"], [role="menuitem"]';
  const interactiveElements = Array.from(document.querySelectorAll(interactiveSelectors));
  for (const el of interactiveElements) {
    const hasAriaLabel = el.hasAttribute('aria-label');
    const hasAriaLabelledBy = el.hasAttribute('aria-labelledby');
    const textContent = (el.textContent || '').trim();
    const title = el.getAttribute('title') || '';
    const placeholder = el.placeholder || '';

    const inputId = el.id;
    const hasLabel = inputId ? !!document.querySelector('label[for="' + inputId + '"]') : false;

    if (!hasAriaLabel && !hasAriaLabelledBy && !textContent && !title && !placeholder && !hasLabel) {
      const tagName = el.tagName.toLowerCase();
      const type = el.getAttribute('type') || '';
      const role = el.getAttribute('role') || '';
      const name = el.getAttribute('name') || '';
      const labelText = name
        ? tagName + ' ' + name
        : role
          ? role + ' element'
          : type
            ? tagName + ' ' + type
            : tagName + ' element';

      const selector = tagName +
        (el.id ? '#' + el.id : String(el.className) ? '.' + String(el.className).split(' ')[0] : '');
      el.setAttribute('aria-label', labelText);
      changes.push({
        selector,
        changeType: 'add-attr',
        original: '',
        modified: 'aria-label="' + labelText + '"',
      });
    }
  }

  // 2. Insert skip-navigation link at the END of body (not beginning).
  // Inserting at body.firstChild shifts ALL subsequent BrowserGym node IDs by ~1,
  // creating a latent element-targeting risk where click("42") targets different
  // elements in high vs base. Appending at the end avoids this because BrowserGym
  // assigns IDs in DOM order — existing elements keep their IDs.
  // Skip-links work via href="#main-content" anchor, so position doesn't matter
  // for functionality; tab order is controlled by tabindex if needed.
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

    var body = document.body;
    body.appendChild(skipLink);

    var mainEl = document.querySelector('main') || document.querySelector('[role="main"]');
    if (mainEl && !mainEl.id) {
      mainEl.id = 'main-content';
    } else if (!mainEl) {
      var firstContent = document.querySelector('.content, #content, .main, #main');
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

  // 3. Ensure all form controls have associated labels
  const formControls = Array.from(document.querySelectorAll('input, select, textarea'));
  for (const control of formControls) {
    const controlId = control.id;
    const hasAriaLabel = control.hasAttribute('aria-label');
    const hasAriaLabelledBy = control.hasAttribute('aria-labelledby');
    const hasLabel = controlId ? !!document.querySelector('label[for="' + controlId + '"]') : false;
    const wrappedInLabel = !!control.closest('label');

    if (!hasAriaLabel && !hasAriaLabelledBy && !hasLabel && !wrappedInLabel) {
      const tagName = control.tagName.toLowerCase();
      const type = control.getAttribute('type') || '';
      const name = control.getAttribute('name') || '';
      const placeholder = control.placeholder || '';

      const labelText = placeholder || name || (tagName + ' ' + type).trim() || tagName;

      if (controlId) {
        const label = document.createElement('label');
        label.htmlFor = controlId;
        label.textContent = labelText;
        label.setAttribute('style', 'position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);');
        if (control.parentElement) {
          control.parentElement.insertBefore(label, control);
        }
        const selector = tagName + '#' + controlId;
        changes.push({
          selector,
          changeType: 'add-element',
          original: '',
          modified: label.outerHTML.substring(0, 500),
        });
      } else {
        const selector = tagName +
          (String(control.className) ? '.' + String(control.className).split(' ')[0] : '') +
          (name ? '[name="' + name + '"]' : '');
        control.setAttribute('aria-label', labelText);
        changes.push({
          selector,
          changeType: 'add-attr',
          original: '',
          modified: 'aria-label="' + labelText + '"',
        });
      }
    }
  }

  // 4. Add landmark roles to major page sections
  const landmarkMappings = [
    { selector: 'header:not([role])', role: 'banner' },
    { selector: 'nav:not([role])', role: 'navigation' },
    { selector: 'main:not([role])', role: 'main' },
    { selector: 'footer:not([role])', role: 'contentinfo' },
    { selector: 'aside:not([role])', role: 'complementary' },
    { selector: 'form:not([role])', role: 'form' },
  ];

  for (const mapping of landmarkMappings) {
    const elements = Array.from(document.querySelectorAll(mapping.selector));
    for (const el of elements) {
      const elSelector = el.tagName.toLowerCase() +
        (el.id ? '#' + el.id : String(el.className) ? '.' + String(el.className).split(' ')[0] : '');
      el.setAttribute('role', mapping.role);
      changes.push({
        selector: elSelector,
        changeType: 'add-attr',
        original: '',
        modified: 'role="' + mapping.role + '"',
      });
    }
  }

  // 5a. Ensure all images have alt text
  const images = Array.from(document.querySelectorAll('img:not([alt])'));
  for (const img of images) {
    const src = img.getAttribute('src') || '';
    const altText = (src.split('/').pop() || 'image').replace(/\.[^.]+$/, '').replace(/[-_]/g, ' ') || 'image';
    const selector = 'img' + (img.id ? '#' + img.id : String(img.className) ? '.' + String(img.className).split(' ')[0] : '');
    img.setAttribute('alt', altText);
    changes.push({
      selector,
      changeType: 'add-attr',
      original: '',
      modified: 'alt="' + altText + '"',
    });
  }

  // 5b. Ensure html element has lang attribute
  var htmlEl = document.documentElement;
  if (!htmlEl.hasAttribute('lang')) {
    htmlEl.setAttribute('lang', 'en');
    changes.push({
      selector: 'html',
      changeType: 'add-attr',
      original: '',
      modified: 'lang="en"',
    });
  }

  // 5c. Ensure all links have discernible text
  const emptyLinks = Array.from(document.querySelectorAll('a:not([aria-label])'));
  for (const link of emptyLinks) {
    const text = (link.textContent || '').trim();
    if (!text && !link.getAttribute('aria-labelledby') && !link.getAttribute('title')) {
      const href = link.getAttribute('href') || '';
      const labelText = href ? 'Link to ' + (href.split('/').pop() || 'page') : 'link';
      const selector = 'a' + (link.id ? '#' + link.id : String(link.className) ? '.' + String(link.className).split(' ')[0] : '');
      link.setAttribute('aria-label', labelText);
      changes.push({
        selector,
        changeType: 'add-attr',
        original: '',
        modified: 'aria-label="' + labelText + '"',
      });
    }
  }

  // 6. Add aria-describedby for form validation — enhance form error association
  const requiredInputs = Array.from(document.querySelectorAll('input[required], select[required], textarea[required]'));
  for (const input of requiredInputs) {
    if (!input.hasAttribute('aria-required')) {
      var reqSelector = input.tagName.toLowerCase() +
        (input.id ? '#' + input.id : input.getAttribute('name') ? '[name="' + input.getAttribute('name') + '"]' : '');
      input.setAttribute('aria-required', 'true');
      changes.push({
        selector: reqSelector,
        changeType: 'add-attr',
        original: '',
        modified: 'aria-required="true"',
      });
    }
  }

  // 7. Add aria-current="page" to links matching current URL
  try {
    var currentPath = window.location.pathname;
    var navLinks = Array.from(document.querySelectorAll('nav a[href], [role="navigation"] a[href]'));
    for (var ni = 0; ni < navLinks.length; ni++) {
      var navLink = navLinks[ni];
      var linkHref = navLink.getAttribute('href') || '';
      if (linkHref === currentPath || linkHref === window.location.href) {
        if (!navLink.hasAttribute('aria-current')) {
          var navSelector = 'a' + (navLink.id ? '#' + navLink.id : '');
          navLink.setAttribute('aria-current', 'page');
          changes.push({
            selector: navSelector,
            changeType: 'add-attr',
            original: '',
            modified: 'aria-current="page"',
          });
        }
      }
    }
  } catch (e) { /* non-fatal */ }

  // 8. Enhance table accessibility — add scope to th, caption to tables
  var tables = Array.from(document.querySelectorAll('table'));
  for (var ti = 0; ti < tables.length; ti++) {
    var table = tables[ti];
    // Add scope="col" to header cells in thead
    var theadCells = Array.from(table.querySelectorAll('thead th:not([scope])'));
    for (var tci = 0; tci < theadCells.length; tci++) {
      theadCells[tci].setAttribute('scope', 'col');
      changes.push({
        selector: 'th',
        changeType: 'add-attr',
        original: '',
        modified: 'scope="col"',
      });
    }
    // Add scope="row" to first cell in each tbody row if it's a th
    var tbodyRowHeaders = Array.from(table.querySelectorAll('tbody th:not([scope])'));
    for (var tri = 0; tri < tbodyRowHeaders.length; tri++) {
      tbodyRowHeaders[tri].setAttribute('scope', 'row');
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
