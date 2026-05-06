#!/usr/bin/env python3.11
"""Check which of the 13 Mode A tasks would pass the proposed gate.
Data from docs/analysis/mode-a-analysis.md §2.3 (GT-corrected per-task rates).

Each task's published rate is success across ALL 26 operators × 3 reps.
True "base 3/3" means: at baseline (no patches), would 3/3 reps succeed?
We infer this from (a) H-operator rates and (b) documented task noise.
"""

# Success out of 78 (26 operators × 3 reps) from Mode A GT-corrected
mode_a = {
    ("ecommerce_admin", "4"):   (60, 78, "Operator-sensitive (L1, L5, L11 = 0%)"),
    ("ecommerce",       "23"):  (75, 78, "L1 = 0% (content invisibility)"),
    ("ecommerce",       "24"):  (74, 78, "Near-ceiling"),
    ("ecommerce",       "26"):  (75, 78, "Near-ceiling"),
    ("reddit",          "29"):  (62, 78, "L12 = 0%, L2 = 33%"),
    ("ecommerce_admin", "41"):  (73, 78, "GT-corrected (abomin)"),
    ("reddit",          "67"):  (36, 78, "MOST operator-sensitive"),
    ("ecommerce_admin", "94"):  (75, 78, "L5 = 0%"),
    ("gitlab",          "132"): (78, 78, "Perfect — no operator affects it"),
    ("ecommerce",       "188"): (78, 78, "Perfect — control task"),
    ("ecommerce_admin", "198"): (75, 78, "GT-corrected (Veronica Costello)"),
    ("gitlab",          "293"): (72, 78, "GT-corrected (10.0.1.50 URL)"),
    ("gitlab",          "308"): (75, 78, "L1 = 0%"),
}

# Inferred base-variant behavior at unmodified baseline (no patches):
#   Most tasks: H-operator rate (no DOM changes, ≈ base) = 3/3 success
#   Exceptions documented in Mode A analysis:
#     task 29 — "baseline noise ~33%, 11 operators incl. H-ops have 1/3 reps answering '0'"
#       → H-baseline was NOT 3/3 on task 29; it was ~2/3 stochastic
#     task 67 — "most sensitive task", base rate 80% per Pilot 4 data
#       → H-baseline was 3/3 or 2/3 depending on rep
#     task 4 — L1/L5/L11 = 0%; H-operators = 3/3 = 12/12 → base 3/3
task_inference = {
    "4":   ("3/3_base", "medium", "H-ops all 3/3"),
    "23":  ("3/3_base", "short", "H-ops all 3/3"),
    "24":  ("3/3_base", "short", "H-ops all 3/3"),
    "26":  ("3/3_base", "short", "H-ops all 3/3"),
    "29":  ("NOT_3/3",  "medium", "task noise, 11 ops incl H have 1/3 wrong"),
    "41":  ("3/3_base", "medium", "H-ops all 3/3 post-GT"),
    "67":  ("NOT_3/3",  "medium", "stochastic base 2/3-3/3 per Pilot 4"),
    "94":  ("3/3_base", "deep",   "H-ops all 3/3"),
    "132": ("3/3_base", "medium", "control, 26/26 ops succeed"),
    "188": ("3/3_base", "short",  "control, 26/26 ops succeed"),
    "198": ("3/3_base", "deep",   "H-ops all 3/3 post-GT"),
    "293": ("3/3_base", "medium", "H-ops all 3/3 post-GT"),
    "308": ("3/3_base", "deep",   "H-ops all 3/3"),
}

nav_to_steps = {"short": 3, "medium": 7, "deep": 12}

print(f"\n{'Task':22} {'26-op rate':>12} {'Est base':>12} {'Steps':>6} {'3/3 gate':>10} {'3/3+≥3':>9}")
print("-" * 85)

p33 = 0
p33s3 = 0
for (app, tid), (succ, tot, note) in mode_a.items():
    pct = 100 * succ / tot
    base_status, nav, why = task_inference[tid]
    steps = nav_to_steps[nav]
    g1 = "YES" if base_status == "3/3_base" else "NO"
    g2 = "YES" if (base_status == "3/3_base" and steps >= 3) else "NO"
    p33 += 1 if g1 == "YES" else 0
    p33s3 += 1 if g2 == "YES" else 0
    label = f"{app}:{tid}"
    print(f"{label:22} {succ}/{tot} ({pct:3.0f}%)   {base_status:11}  {steps:>4}     {g1:>7}      {g2:>6}")

print()
print(f"13 Mode A tasks:")
print(f"  Pass 3/3 gate:            {p33}/13 ({100*p33/13:.0f}%)")
print(f"  Pass 3/3 + steps>=3 gate: {p33s3}/13 ({100*p33s3/13:.0f}%)")
print()
print(f"Notes:")
print(f"  - Tasks dropped by 3/3 gate: 29 (task noise), 67 (stochastic)")
print(f"  - Note: task 29/67 were KEPT in Mode A and produced interesting variance")
print(f"    (67 is \"most operator-sensitive\", revealed forced-simplification)")
