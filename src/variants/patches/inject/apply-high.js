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

  // 2. Insert skip-navigation link at the top of the page
  const existingSkipLink = document.querySelector('a.skip-link, a[href="#main-content"]');
  if (!existingSkipLink) {
    const skipLink = document.createElement('a');
    skipLink.href = '#main-content';
    skipLink.className = 'skip-link';
    skipLink.textContent = 'Skip to main content';
    skipLink.setAttribute('style',
      'position:absolute;top:-40px;left:0;background:#000;color:#fff;padding:8px;z-index:10000;' +
      'transition:top 0.3s;');
    skipLink.addEventListener('focus', function() { skipLink.style.top = '0'; });
    skipLink.addEventListener('blur', function() { skipLink.style.top = '-40px'; });

    var body = document.body;
    body.insertBefore(skipLink, body.firstChild);

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

  return changes;
})();
