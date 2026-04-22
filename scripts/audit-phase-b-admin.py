#!/usr/bin/env python3
"""Audit Phase B admin records for silent login failures.

Prior (WRONG) audit checked only `final_url` against login-path patterns;
that missed the common case where Magento renders a login form **inside**
a page with the protected URL (final_url looks fine; content is login).

This audit relies on page.title() which was recorded per-capture.
Exits 0 if admin content is actually admin (dashboard, orders, etc).
Exits 1 if admin content is the Magento login screen (title contains
'Login' / 'Magento Admin' with no "Dashboard" etc.)
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

MANIFEST = Path(__file__).parent.parent / "data/visual-equivalence/replay/manifest.json"

if not MANIFEST.exists():
    print(f"ERROR: manifest not found at {MANIFEST}")
    sys.exit(2)

m = json.loads(MANIFEST.read_text(encoding="utf-8"))
recs = m["records"]
admin = [r for r in recs if r.get("app") in ("shopping_admin", "ecommerce_admin")]
print(f"Total admin records in Phase B: {len(admin)}")
print(f"Successful: {sum(1 for r in admin if r.get('success'))}")
print()

# Title frequency
print("Title frequency (admin records):")
titles = Counter(r.get("title", "?") for r in admin if r.get("success"))
for title, n in titles.most_common(20):
    t = title[:100] if title else "(empty)"
    print(f"  {n:3d}x: {t!r}")
print()

# Login-page signatures
LOGIN_TITLE_MARKERS = ("login", "sign in", "magento admin")
ADMIN_TITLE_MARKERS = ("dashboard", "magento", "orders", "products", "customers",
                       "analytics", "catalog", "sales", "reports")

login_content = []
admin_content = []
unknown = []
for r in admin:
    if not r.get("success"):
        continue
    t = (r.get("title") or "").lower()
    is_login = any(m in t for m in LOGIN_TITLE_MARKERS) and "dashboard" not in t
    is_admin = (not is_login) and any(m in t for m in ADMIN_TITLE_MARKERS)
    if is_login:
        login_content.append(r)
    elif is_admin:
        admin_content.append(r)
    else:
        unknown.append(r)

print(f"Login-content admin captures (title contains 'login'/'sign in'): "
      f"{len(login_content)}")
print(f"Real-admin-content captures (title contains 'dashboard'/'orders'/..): "
      f"{len(admin_content)}")
print(f"Ambiguous (title empty or unrecognized): {len(unknown)}")
print()

if login_content:
    print("Sample admin records that rendered LOGIN content:")
    for r in login_content[:5]:
        slug = r["slug"][:60]
        variant = r["variant"]
        src = (r.get("url") or "")[:80]
        final = (r.get("final_url") or "")[:80]
        title = (r.get("title") or "")[:80]
        print(f"  slug={slug} variant={variant}")
        print(f"    src:   {src}")
        print(f"    final: {final}")
        print(f"    title: {title!r}")
        print()

if unknown:
    print("Sample admin records with ambiguous title:")
    for r in unknown[:5]:
        slug = r["slug"][:60]
        variant = r["variant"]
        title = (r.get("title") or "(empty)")[:80]
        print(f"  slug={slug} variant={variant} title={title!r}")

# Verdict
n_login = len(login_content)
n_total_successful = n_login + len(admin_content) + len(unknown)
print()
print(f"VERDICT: {n_login}/{n_total_successful} ({100*n_login/max(n_total_successful,1):.1f}%) admin captures actually rendered LOGIN content.")
if n_login > 0:
    print("Phase B admin data IS contaminated — those captures were not authenticated.")
    print("Base vs low SSIM on these pairs compares two login-page screenshots,")
    print("not two admin-app screenshots.")
    sys.exit(1)
