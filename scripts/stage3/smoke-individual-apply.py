#!/usr/bin/env python3.11
"""Smoke-test that apply-all-individual.js works with window.__OPERATOR_IDS.

Run locally; no WebArena access needed. Uses a tiny HTML fixture.
"""
from __future__ import annotations
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
APPLY_JS = REPO_ROOT / "src" / "variants" / "patches" / "inject" / "apply-all-individual.js"

FIXTURE_HTML = """\
<!doctype html>
<html>
<head><title>fixture</title></head>
<body>
  <nav>
    <a href="#home">home</a>
    <a href="#about">about</a>
  </nav>
  <main>
    <h1>heading</h1>
    <p>para with <a href="/action">link</a></p>
    <button>btn</button>
    <img src="logo.png">
    <form>
      <label for="q">query</label>
      <input id="q" type="text">
    </form>
  </main>
</body>
</html>
"""


def main() -> int:
    from playwright.sync_api import sync_playwright

    apply_js = APPLY_JS.read_text(encoding="utf-8")

    test_ops = ["L1", "L5", "L7", "L11", "H1", "H2", "ML3"]

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for op in test_ops:
            ctx = browser.new_context(viewport={"width": 1280, "height": 720})
            page = ctx.new_page()
            page.set_content(FIXTURE_HTML)
            page.evaluate(f"window.__OPERATOR_IDS = {json.dumps([op])};")
            changes = page.evaluate(apply_js)
            n = len(changes) if isinstance(changes, list) else -1
            sentinel = page.evaluate(
                "document.body.getAttribute('data-amt-applied')"
            )
            print(f"  op={op}: {n} changes, sentinel={sentinel!r}")
            ctx.close()
        browser.close()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
