#!/usr/bin/env python3
"""
Read-only re-analysis for ECO-1..6 audit remediation (CHI/ASSETS 2027 paper).
Reads frozen results/prevalence_matrix.csv + results/*.json; writes ONLY to
results/supplementary/eco_reground.csv. Does NOT mutate any frozen artifact.
"""
import csv, json, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.dirname(HERE)  # results/
SCAN_RES = os.path.join(os.path.dirname(RES), "scan-a11y-audit", "results")
MATRIX = os.path.join(SCAN_RES, "prevalence_matrix.csv")

rows = []
with open(MATRIX) as f:
    for r in csv.DictReader(f):
        rows.append(r)

def num(r, col):
    return int(r[col])

P7 = "P7: landmark→div"
P9 = "P9: thead→div"
P11 = "P11: link→span"
P5 = "P5: heading→div"
P12 = "P12: Shadow DOM"
P6 = "P6: tabindex"

all34 = rows
real = [r for r in rows if r["category"] != "webarena"]
wa = [r for r in rows if r["category"] == "webarena"]

def affected(rowset, cols):
    """count sites with sum over cols > 0"""
    return sum(1 for r in rowset if sum(num(r, c) for c in cols) > 0)

def nodes(rowset, cols):
    return [sum(num(r, c) for c in cols) for r in rowset]

out = []
def log(k, v):
    out.append((k, v))
    print(f"{k}: {v}")

print("="*70)
log("n_all34", len(all34))
log("n_real", len(real))
log("n_webarena", len(wa))

# ECO-1 / ECO-2 / ECO-6 : prevalence under different rule sets
L3_code = [P7, P9, P11]  # analysis.py L3_structural
log("P7_alone_affected_/34", f"{affected(all34,[P7])}/34 = {affected(all34,[P7])/34*100:.1f}%")
log("P9_alone_affected_/34", f"{affected(all34,[P9])}/34")
log("P11_alone_affected_/34", f"{affected(all34,[P11])}/34 = {affected(all34,[P11])/34*100:.1f}%")
log("P5_alone_affected_/34", f"{affected(all34,[P5])}/34")
log("P12_alone_affected_/34", f"{affected(all34,[P12])}/34")
log("L3_code(P7|P9|P11)_/34", f"{affected(all34,L3_code)}/34 = {affected(all34,L3_code)/34*100:.1f}%")

# ECO-2: paper-consistent Tier-3 adds P5(L6 heading) + P12(L5 ShadowDOM)
L3_paper = [P7, P9, P11, P5, P12]
log("L3_paper(+P5+P12)_/34", f"{affected(all34,L3_paper)}/34 = {affected(all34,L3_paper)/34*100:.1f}%")
# how many NEW sites P5 and P12 add beyond P7|P9|P11
base_sites = set(r["site"] for r in all34 if sum(num(r,c) for c in L3_code) > 0)
p5_sites = set(r["site"] for r in all34 if num(r,P5) > 0)
p12_sites = set(r["site"] for r in all34 if num(r,P12) > 0)
p9_sites = set(r["site"] for r in all34 if num(r,P9) > 0)
p11_sites = set(r["site"] for r in all34 if num(r,P11) > 0)
p7_sites = set(r["site"] for r in all34 if num(r,P7) > 0)
log("P9_new_beyond_P7", sorted(p9_sites - p7_sites))
log("P11_new_beyond_P7", sorted(p11_sites - p7_sites))
log("P5_new_beyond_codeL3", sorted(p5_sites - base_sites))
log("P12_new_beyond_codeL3", sorted(p12_sites - base_sites))

# ECO-3: denominators
log("L3_code_real_/30", f"{affected(real,L3_code)}/{len(real)} = {affected(real,L3_code)/len(real)*100:.1f}%")
mean_all = sum(nodes(all34, L3_code))/len(all34)
mean_real = sum(nodes(real, L3_code))/len(real)
log("mean_L3nodes_all34", f"{mean_all:.1f}")
log("mean_L3nodes_real30", f"{mean_real:.1f}")
log("sum_L3nodes_all34", sum(nodes(all34, L3_code)))
log("sum_L3nodes_real30", sum(nodes(real, L3_code)))
# webarena L3 contribution
for r in wa:
    log(f"  webarena_{r['site']}_L3nodes", sum(num(r,c) for c in L3_code))

# ECO-5: distribution among affected real sites
real_affected_nodes = sorted(n for n in nodes(real, L3_code) if n > 0)
log("real_affected_count", len(real_affected_nodes))
log("real_affected_sorted_nodes", real_affected_nodes)
log("real_affected_median", statistics.median(real_affected_nodes))
log("real_affected_mean", f"{statistics.mean(real_affected_nodes):.1f}")
log("real_affected_min", min(real_affected_nodes))
log("real_affected_max", max(real_affected_nodes))
# affected over all 34
all_affected_nodes = sorted(n for n in nodes(all34, L3_code) if n > 0)
log("all34_affected_count", len(all_affected_nodes))
log("all34_affected_median", statistics.median(all_affected_nodes))
log("all34_affected_mean", f"{statistics.mean(all_affected_nodes):.1f}")
log("all34_affected_max", max(all_affected_nodes))
# top sites by L3 nodes
site_nodes = [(r["site"], sum(num(r,c) for c in L3_code)) for r in real]
site_nodes.sort(key=lambda x:-x[1])
log("top5_real_sites_by_L3nodes", site_nodes[:5])
# co-occurrence: distinct L3 op types per affected real site
def types(r):
    return sum(1 for c in L3_code if num(r,c) > 0)
multi = [(r["site"], types(r)) for r in real if sum(num(r,c) for c in L3_code) > 0]
log("real_affected_with_>=2_L3types", [s for s,t in multi if t>=2])
log("real_affected_landmark_only", sum(1 for r in real if num(r,P7)>0 and num(r,P9)==0 and num(r,P11)==0 and sum(num(r,c) for c in L3_code)>0))

# ECO-1: landmark-unique sensitivity needs raw JSON (per-rule breakdown).
# Recompute P7 prevalence with and without landmark-unique from the JSONs.
def load_axe(site):
    # mirror analysis.py get_axe_violations exactly: page["axe"]["violations"], v["nodes"] is an int
    p = os.path.join(SCAN_RES, f"{site}.json")
    with open(p) as f:
        d = json.load(f)
    agg = {}
    for pg in d.get("pages", []):
        for v in pg.get("axe", {}).get("violations", []):
            rid = v["id"]
            agg[rid] = agg.get(rid, 0) + v["nodes"]
    return agg

P7_RULES = ["landmark-main-is-top-level", "region", "landmark-one-main", "landmark-unique"]
P7_NO_UNIQUE = ["landmark-main-is-top-level", "region", "landmark-one-main"]
DISCLOSED_L387 = ["landmark-one-main", "region", "empty-heading", "heading-order",
                  "td-has-header", "th-has-data-cells"]  # + div-as-link(P11 custom)

site_axe = {}
for r in all34:
    try:
        site_axe[r["site"]] = load_axe(r["site"])
    except Exception as e:
        site_axe[r["site"]] = None

def p7_with(site, rules):
    a = site_axe.get(site)
    if a is None:
        return None
    return sum(a.get(rr,0) for rr in rules) > 0

# count with landmark-unique vs without, over 34
have_axe = [s for s in site_axe if site_axe[s] is not None]
log("sites_with_loadable_axe", len(have_axe))
if len(have_axe) >= 30:
    with_u = sum(1 for s in have_axe if p7_with(s, P7_RULES))
    no_u = sum(1 for s in have_axe if p7_with(s, P7_NO_UNIQUE))
    log("P7_with_landmark_unique", f"{with_u}/{len(have_axe)} = {with_u/len(have_axe)*100:.1f}%")
    log("P7_without_landmark_unique", f"{no_u}/{len(have_axe)} = {no_u/len(have_axe)*100:.1f}%")
    # sites flagged ONLY by landmark-unique
    only_u = [s for s in have_axe if p7_with(s, P7_RULES) and not p7_with(s, P7_NO_UNIQUE)]
    log("sites_flagged_only_by_landmark_unique", sorted(only_u))
    # disclosed L387 rule set (+ P11 custom div-as-link)
    def disclosed_affected(site):
        a = site_axe.get(site)
        if a is None: return False
        axe_hit = sum(a.get(rr,0) for rr in DISCLOSED_L387) > 0
        # P11 div-as-link custom
        rr = [x for x in all34 if x["site"]==site][0]
        p11_hit = num(rr, P11) > 0
        return axe_hit or p11_hit
    disc = sum(1 for s in have_axe if disclosed_affected(s))
    log("disclosed_L387_ruleset_affected", f"{disc}/{len(have_axe)} = {disc/len(have_axe)*100:.1f}%")

# write supplementary CSV
csv_out = os.path.join(HERE, "eco_reground.csv")
with open(csv_out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["metric","value"])
    for k,v in out:
        w.writerow([k, v])
print(f"\nWrote {csv_out}")
