#!/usr/bin/env python3
"""Audit ALL Phase B apps for silent auth failure.

⚠ DEPRECATED (2026-05-15): targets the 13-task Phase 7 prototype under
  `data/visual-equivalence/replay/` (see that dir's STATUS.md).
  Stage 4b — `data/stage4b-ssim-replay/` — superseded this workflow;
  see `analysis/stages/phase6_stage4b.py` for the current login-contamination
  health check (informational, non-failing).
  Retained for forensic / historical use only; not part of `make verify-all`.

Same principle as admin audit but extended to all 4 apps.
Login-page / signed-out signatures:
  shopping (Magento storefront) — title starts with "Customer Login" or "One Stop Market"
    when logged out; "My Account" in nav when logged in
  shopping_admin — title "Magento Admin" without "Dashboard"/"Orders" etc.
  reddit (Postmill) — has "Log in" in nav / title when logged out
  gitlab — GitLab login at /users/sign_in shows title "Sign in · GitLab"
"""
import json
import sys
from collections import Counter
from pathlib import Path

MANIFEST = Path(__file__).parent.parent.parent / "data/visual-equivalence/replay/manifest.json"

# Per-app: (title markers that indicate LOGIN page, title markers that indicate OK content)
APP_SIGNATURES = {
    "ecommerce": {
        "login_markers": ["customer login", "sign in"],
        # shopping title is usually product name or "One Stop Market"
        "ok_markers": [],
    },
    "shopping_admin": {
        "login_markers": [],
        "ok_markers": ["dashboard", "orders", "catalog", "sales", "customers", "reports"],
    },
    "ecommerce_admin": {
        "login_markers": [],
        "ok_markers": ["dashboard", "orders", "catalog", "sales", "customers", "reports"],
    },
    "reddit": {
        "login_markers": ["log in · postmill"],
        "ok_markers": [],
    },
    "gitlab": {
        "login_markers": ["sign in · gitlab"],
        "ok_markers": [],
    },
}


def classify(app: str, title: str) -> str:
    sig = APP_SIGNATURES.get(app)
    if not sig:
        return "unknown_app"
    t = (title or "").lower()
    for m in sig["login_markers"]:
        if m in t:
            return "login"
    if sig["ok_markers"]:
        for m in sig["ok_markers"]:
            if m in t:
                return "ok"
        # Has markers list but title matched none → probably login or partial
        return "suspicious"
    return "ok"  # app with no ok_markers defaults to ok


if not MANIFEST.exists():
    print(f"ERROR: manifest not found at {MANIFEST}")
    sys.exit(2)

m = json.loads(MANIFEST.read_text(encoding="utf-8"))
recs = [r for r in m["records"] if r.get("success")]

# Per app statistics
by_app = {}
for r in recs:
    app = r.get("app", "?")
    by_app.setdefault(app, []).append(r)

print(f"Total successful Phase B captures: {len(recs)}\n")

contaminated = {}
for app, rs in sorted(by_app.items()):
    titles = Counter(r.get("title", "") for r in rs)
    print(f"=== App: {app} ({len(rs)} captures) ===")
    print(f"Top titles:")
    for title, n in titles.most_common(5):
        t = title[:80] if title else "(empty)"
        print(f"  {n:3d}x: {t!r}")
    # Classify
    klass = Counter(classify(app, r.get("title", "")) for r in rs)
    print(f"Classification: {dict(klass)}")
    if klass.get("login", 0) > 0:
        pct = 100 * klass["login"] / len(rs)
        print(f"  ⚠️  LOGIN content: {klass['login']}/{len(rs)} ({pct:.1f}%)")
        contaminated[app] = klass["login"]
    if klass.get("suspicious", 0) > 0:
        pct = 100 * klass["suspicious"] / len(rs)
        print(f"  ? suspicious:     {klass['suspicious']}/{len(rs)} ({pct:.1f}%)")
    print()

print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)
if contaminated:
    total = sum(contaminated.values())
    print(f"{total} total captures contaminated by login-page rendering:")
    for app, n in sorted(contaminated.items()):
        print(f"  {app}: {n}")
    sys.exit(1)
else:
    print("No login-page contamination detected across all apps.")
    sys.exit(0)
