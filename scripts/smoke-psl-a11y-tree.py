#!/usr/bin/env python3
"""
Smoke test: Verify pure-semantic-low ARIA manipulations in Chromium.

Tests how role="presentation", aria-hidden="true", and attribute removal
affect the Accessibility Tree for different element types.

This answers the critical question: does role="presentation" on focusable
elements (links, buttons) actually remove them from the a11y tree in
Chromium's headless mode (which BrowserGym uses)?

Usage:
  python scripts/smoke-psl-a11y-tree.py

Requires: playwright (pip install playwright && playwright install chromium)
"""

import json
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("pip install playwright && playwright install chromium")
    sys.exit(1)


# Test HTML with various elements we want to manipulate
TEST_HTML = """
<!DOCTYPE html>
<html lang="en">
<head><title>PSL A11y Tree Test</title></head>
<body>
  <nav id="main-nav">
    <a href="/page1" id="link1">Page 1</a>
    <a href="/page2" id="link2">Page 2</a>
  </nav>
  <main>
    <h1 id="heading1">Main Heading</h1>
    <h2 id="heading2">Sub Heading</h2>
    <p>Some paragraph text</p>
    <button id="btn1">Click Me</button>
    <label id="label1" for="input1">Username</label>
    <input id="input1" type="text" aria-label="Username field">
    <table id="table1">
      <thead><tr><th>Name</th><th>Value</th></tr></thead>
      <tbody><tr><td>Item</td><td>123</td></tr></tbody>
    </table>
    <img id="img1" src="test.png" alt="Test image">
  </main>
</body>
</html>
"""


def get_a11y_snapshot(page):
    """Get the accessibility tree snapshot via CDP."""
    snapshot = page.accessibility.snapshot()
    return snapshot


def flatten_snapshot(node, depth=0, lines=None):
    """Flatten a11y snapshot to readable text."""
    if lines is None:
        lines = []
    if node is None:
        return lines
    role = node.get("role", "")
    name = node.get("name", "")
    indent = "  " * depth
    line = f"{indent}{role}"
    if name:
        line += f' "{name}"'
    lines.append(line)
    for child in node.get("children", []):
        flatten_snapshot(child, depth + 1, lines)
    return lines


def count_roles(node, role_counts=None):
    """Count occurrences of each role in the tree."""
    if role_counts is None:
        role_counts = {}
    if node is None:
        return role_counts
    role = node.get("role", "unknown")
    role_counts[role] = role_counts.get(role, 0) + 1
    for child in node.get("children", []):
        count_roles(child, role_counts)
    return role_counts


def run_test(page, label, js_code):
    """Run a manipulation and show the a11y tree diff."""
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print(f"{'='*60}")

    # Reset page
    page.set_content(TEST_HTML)
    page.wait_for_load_state("domcontentloaded")

    # Get baseline
    baseline = get_a11y_snapshot(page)
    baseline_roles = count_roles(baseline)

    # Apply manipulation
    if js_code:
        page.evaluate(js_code)
        page.wait_for_timeout(200)

    # Get result
    result = get_a11y_snapshot(page)
    result_roles = count_roles(result)

    # Show key role changes
    key_roles = ["link", "heading", "button", "navigation", "table",
                 "row", "cell", "columnheader", "img", "textbox"]
    print("\nRole counts (baseline → after):")
    for role in key_roles:
        b = baseline_roles.get(role, 0)
        a = result_roles.get(role, 0)
        if b != a:
            print(f"  {role}: {b} → {a}  {'⚠️ CHANGED' if b != a else ''}")
        elif b > 0:
            print(f"  {role}: {b} → {a}")

    # Show full tree (truncated)
    lines = flatten_snapshot(result)
    print(f"\nA11y tree ({len(lines)} nodes):")
    for line in lines[:30]:
        print(f"  {line}")
    if len(lines) > 30:
        print(f"  ... ({len(lines) - 30} more)")

    return baseline_roles, result_roles


def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  Pure-Semantic-Low A11y Tree Smoke Test                 ║")
    print("╚══════════════════════════════════════════════════════════╝")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Test 0: Baseline (no changes)
        run_test(page, "BASELINE (no changes)", None)

        # Test 1: role="presentation" on nav
        run_test(page, 'nav role="presentation"',
                 'document.querySelector("#main-nav").setAttribute("role", "presentation")')

        # Test 2: role="presentation" on link (THE critical test)
        run_test(page, 'link role="presentation" (focusable!)',
                 'document.querySelector("#link1").setAttribute("role", "presentation")')

        # Test 3: role="presentation" on heading
        run_test(page, 'h1 role="presentation"',
                 'document.querySelector("#heading1").setAttribute("role", "presentation")')

        # Test 4: aria-hidden="true" on link (focusable)
        run_test(page, 'link aria-hidden="true" (focusable!)',
                 'document.querySelector("#link1").setAttribute("aria-hidden", "true")')

        # Test 5: aria-hidden on label + remove for
        run_test(page, 'label aria-hidden + remove for',
                 '''
                 var l = document.querySelector("#label1");
                 l.setAttribute("aria-hidden", "true");
                 l.removeAttribute("for");
                 ''')

        # Test 6: table role="presentation"
        run_test(page, 'table role="presentation"',
                 'document.querySelector("#table1").setAttribute("role", "presentation")')

        # Test 7: button aria-hidden="true" (focusable)
        run_test(page, 'button aria-hidden="true" (focusable!)',
                 'document.querySelector("#btn1").setAttribute("aria-hidden", "true")')

        # Test 8: Combined PSL — all patches at once
        run_test(page, "COMBINED: Full pure-semantic-low",
                 '''
                 // Landmarks → presentation
                 document.querySelectorAll("nav, main, header, footer, article, section, aside")
                   .forEach(el => el.setAttribute("role", "presentation"));
                 // Headings → presentation
                 document.querySelectorAll("h1, h2, h3, h4, h5, h6")
                   .forEach(el => el.setAttribute("role", "presentation"));
                 // Links → presentation (keep href!)
                 document.querySelectorAll("a[href]")
                   .forEach(el => el.setAttribute("role", "presentation"));
                 // Remove all aria-* attributes
                 document.querySelectorAll("[aria-label], [aria-labelledby], [aria-describedby]")
                   .forEach(el => {
                     Array.from(el.attributes)
                       .filter(a => a.name.startsWith("aria-"))
                       .forEach(a => el.removeAttribute(a.name));
                   });
                 // Labels → hidden + unlink
                 document.querySelectorAll("label[for]").forEach(el => {
                   el.setAttribute("aria-hidden", "true");
                   el.removeAttribute("for");
                 });
                 // Table → presentation
                 document.querySelectorAll("table")
                   .forEach(el => el.setAttribute("role", "presentation"));
                 // Remove img alt
                 document.querySelectorAll("img[alt]")
                   .forEach(el => el.removeAttribute("alt"));
                 // Remove html lang
                 document.documentElement.removeAttribute("lang");
                 ''')

        browser.close()

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("Check the role counts above. Key questions:")
    print("1. Does role='presentation' on <a> remove 'link' role?")
    print("2. Does aria-hidden='true' on <button> remove it?")
    print("3. Does the combined PSL remove all semantic roles")
    print("   while keeping the element count the same?")


if __name__ == "__main__":
    main()
