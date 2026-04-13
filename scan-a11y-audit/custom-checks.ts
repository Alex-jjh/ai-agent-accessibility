/**
 * Custom DOM checks for patches that axe-core doesn't cover.
 * Runs inside page.evaluate() — must be self-contained (no imports).
 */

export interface CustomCheckResults {
  // P11: link→span — div/span used as links instead of <a>
  divAsLink: {
    divOnclick: number;       // div[onclick] count
    spanOnclick: number;      // span[onclick] count
    roleLink: number;         // [role="link"]:not(a) count
    jsEventListeners: number; // elements with click listeners via getEventListeners (CDP)
    totalAnchorLinks: number; // a[href] count (denominator)
  };
  // P5: heading→div — non-semantic heading patterns
  headingSemantics: {
    semanticHeadings: number;   // h1-h6 count
    ariaHeadings: number;       // [role="heading"] not h1-h6
    divClassHeadings: number;   // div/span with class containing "heading" or "title" (heuristic)
  };
  // P9: table semantics — div-based tables
  tableSemantics: {
    semanticTables: number;     // <table> count
    roleTables: number;         // [role="table"] or [role="grid"] not <table>
    divClassTables: number;     // div with class containing "table" or "grid" (heuristic)
  };
  // P7: landmark presence
  landmarks: {
    nav: number;
    main: number;
    header: number;
    footer: number;
    aside: number;
    roleNavigation: number;     // [role="navigation"]
    roleMain: number;           // [role="main"]
    roleBanner: number;         // [role="banner"]
    roleContentinfo: number;    // [role="contentinfo"]
  };
  // General DOM stats
  domStats: {
    totalElements: number;
    totalInteractive: number;   // a, button, input, select, textarea, [role="button"], [role="link"]
    ariaLiveRegions: number;
    shadowRoots: number;        // elements with shadowRoot
    iframes: number;
  };
}

/**
 * Script to evaluate inside the page context.
 * Returns CustomCheckResults as a plain object.
 */
export const CUSTOM_CHECK_SCRIPT = `(() => {
  const qsa = (sel) => document.querySelectorAll(sel).length;

  // P11: div-as-link detection
  const divOnclick = qsa('div[onclick]');
  const spanOnclick = qsa('span[onclick]');
  const roleLink = qsa('[role="link"]:not(a)');
  const totalAnchorLinks = qsa('a[href]');

  // P5: heading semantics
  const semanticHeadings = qsa('h1,h2,h3,h4,h5,h6');
  const ariaHeadings = qsa('[role="heading"]:not(h1):not(h2):not(h3):not(h4):not(h5):not(h6)');
  // Heuristic: class names containing heading/title on non-heading elements
  let divClassHeadings = 0;
  document.querySelectorAll('div,span,p').forEach(el => {
    const cls = (el.className || '').toString().toLowerCase();
    if ((cls.includes('heading') || cls.includes('title')) &&
        !el.tagName.match(/^H[1-6]$/)) {
      divClassHeadings++;
    }
  });

  // P9: table semantics
  const semanticTables = qsa('table');
  const roleTables = qsa('[role="table"]:not(table), [role="grid"]:not(table)');
  let divClassTables = 0;
  document.querySelectorAll('div').forEach(el => {
    const cls = (el.className || '').toString().toLowerCase();
    if (cls.includes('table') || cls.includes('grid')) {
      divClassTables++;
    }
  });

  // P7: landmarks
  const nav = qsa('nav');
  const main = qsa('main');
  const header = qsa('header');
  const footer = qsa('footer');
  const aside = qsa('aside');
  const roleNavigation = qsa('[role="navigation"]');
  const roleMain = qsa('[role="main"]');
  const roleBanner = qsa('[role="banner"]');
  const roleContentinfo = qsa('[role="contentinfo"]');

  // DOM stats
  const totalElements = qsa('*');
  const totalInteractive = qsa('a,button,input,select,textarea,[role="button"],[role="link"],[tabindex]');
  const ariaLiveRegions = qsa('[aria-live]');
  let shadowRoots = 0;
  document.querySelectorAll('*').forEach(el => {
    if (el.shadowRoot) shadowRoots++;
  });
  const iframes = qsa('iframe');

  return {
    divAsLink: { divOnclick, spanOnclick, roleLink, jsEventListeners: 0, totalAnchorLinks },
    headingSemantics: { semanticHeadings, ariaHeadings, divClassHeadings },
    tableSemantics: { semanticTables, roleTables, divClassTables },
    landmarks: { nav, main, header, footer, aside, roleNavigation, roleMain, roleBanner, roleContentinfo },
    domStats: { totalElements, totalInteractive, ariaLiveRegions, shadowRoots, iframes },
  };
})()`;
