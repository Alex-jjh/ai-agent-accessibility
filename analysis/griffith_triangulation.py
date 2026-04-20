#!/usr/bin/env python3
"""
Griffith et al. (2022) triangulation analysis for §5.8.
Derives per-participant metrics from raw 40-participant × 8-task data.

Data source: openICPSR project 183081, transcribed from paper Tables 3-4
and raw data sheets provided by Alex.

Sites:
  MM = My Market (high-a11y grocery)      → maps to ~Base/High in our framework
  GG = Great Grocery (low-a11y grocery)    → maps to L3 (broken dropdown, aria-hidden)
  OU = Oakleaf University (high-a11y uni)  → maps to ~Base/High in our framework
  PU = Pinebranch University (low-a11y uni)→ maps to L3 (broken links, no landmarks)

Each participant did 2 tasks per site (task 1 and task 2).
Status: Y = completed, N = not completed
Time: in seconds
"""

import numpy as np
from collections import defaultdict

# Raw data: (status, time_seconds) for each participant × task
# Transcribed from the provided data tables
# Format: participants[i] = {task: (status_bool, time_secs)}

def parse_time(t_str):
    """Parse 'M:SS' to seconds."""
    parts = t_str.split(':')
    return int(parts[0]) * 60 + int(parts[1])

raw = {}

# P1
raw[1] = {'MM1': (True, 82), 'MM2': (True, 40), 'GG1': (True, 48), 'GG2': (False, 246),
           'OU1': (True, 83), 'OU2': (True, 45), 'PU1': (False, 578), 'PU2': (False, 520)}
# P2
raw[2] = {'MM1': (True, 125), 'MM2': (True, 59), 'GG1': (False, 100), 'GG2': (False, 164),
           'OU1': (True, 77), 'OU2': (True, 85), 'PU1': (False, 202), 'PU2': (False, 150)}
# P3
raw[3] = {'MM1': (True, 82), 'MM2': (True, 85), 'GG1': (True, 61), 'GG2': (False, 205),
           'OU1': (True, 70), 'OU2': (True, 125), 'PU1': (False, 355), 'PU2': (False, 319)}
# P4
raw[4] = {'MM1': (True, 60), 'MM2': (True, 19), 'GG1': (False, 166), 'GG2': (False, 100),
           'OU1': (True, 40), 'OU2': (True, 27), 'PU1': (False, 215), 'PU2': (False, 136)}
# P5
raw[5] = {'MM1': (True, 93), 'MM2': (True, 40), 'GG1': (True, 135), 'GG2': (False, 341),
           'OU1': (True, 61), 'OU2': (True, 136), 'PU1': (False, 307), 'PU2': (False, 189)}
# P6
raw[6] = {'MM1': (True, 77), 'MM2': (True, 34), 'GG1': (True, 58), 'GG2': (False, 98),
           'OU1': (True, 30), 'OU2': (True, 22), 'PU1': (False, 85), 'PU2': (False, 100)}
# P7
raw[7] = {'MM1': (True, 67), 'MM2': (True, 30), 'GG1': (True, 66), 'GG2': (False, 160),
           'OU1': (True, 14), 'OU2': (True, 60), 'PU1': (False, 185), 'PU2': (False, 114)}
# P8
raw[8] = {'MM1': (True, 102), 'MM2': (True, 370), 'GG1': (False, 404), 'GG2': (True, 159),
           'OU1': (True, 184), 'OU2': (True, 115), 'PU1': (False, 403), 'PU2': (False, 159)}
# P9
raw[9] = {'MM1': (True, 54), 'MM2': (True, 51), 'GG1': (False, 60), 'GG2': (False, 79),
           'OU1': (True, 38), 'OU2': (True, 81), 'PU1': (False, 47), 'PU2': (False, 33)}
# P10
raw[10] = {'MM1': (True, 105), 'MM2': (True, 36), 'GG1': (True, 61), 'GG2': (False, 95),
            'OU1': (True, 38), 'OU2': (True, 52), 'PU1': (False, 153), 'PU2': (False, 300)}
# P11
raw[11] = {'MM1': (True, 66), 'MM2': (True, 52), 'GG1': (True, 59), 'GG2': (False, 132),
            'OU1': (True, 32), 'OU2': (True, 36), 'PU1': (False, 137), 'PU2': (False, 72)}
# P12
raw[12] = {'MM1': (True, 130), 'MM2': (True, 63), 'GG1': (False, 310), 'GG2': (True, 246),
            'OU1': (True, 35), 'OU2': (True, 25), 'PU1': (True, 273), 'PU2': (True, 100)}
# P13
raw[13] = {'MM1': (True, 76), 'MM2': (True, 40), 'GG1': (True, 37), 'GG2': (False, 140),
            'OU1': (True, 100), 'OU2': (True, 80), 'PU1': (False, 235), 'PU2': (False, 120)}
# P14
raw[14] = {'MM1': (True, 32), 'MM2': (True, 30), 'GG1': (True, 32), 'GG2': (False, 151),
            'OU1': (True, 35), 'OU2': (True, 28), 'PU1': (False, 195), 'PU2': (False, 131)}
# P15
raw[15] = {'MM1': (True, 105), 'MM2': (True, 77), 'GG1': (True, 112), 'GG2': (False, 369),
            'OU1': (True, 72), 'OU2': (True, 63), 'PU1': (False, 247), 'PU2': (False, 158)}
# P16
raw[16] = {'MM1': (True, 98), 'MM2': (True, 32), 'GG1': (True, 35), 'GG2': (False, 413),
            'OU1': (True, 22), 'OU2': (True, 93), 'PU1': (False, 465), 'PU2': (False, 283)}
# P17
raw[17] = {'MM1': (True, 58), 'MM2': (True, 63), 'GG1': (True, 56), 'GG2': (False, 196),
            'OU1': (True, 70), 'OU2': (True, 32), 'PU1': (False, 328), 'PU2': (False, 226)}
# P18
raw[18] = {'MM1': (True, 99), 'MM2': (True, 135), 'GG1': (True, 125), 'GG2': (False, 99),
            'OU1': (True, 62), 'OU2': (True, 75), 'PU1': (False, 186), 'PU2': (False, 126)}
# P19
raw[19] = {'MM1': (True, 78), 'MM2': (True, 38), 'GG1': (True, 55), 'GG2': (False, 181),
            'OU1': (True, 55), 'OU2': (True, 39), 'PU1': (False, 187), 'PU2': (False, 76)}
# P20
raw[20] = {'MM1': (True, 159), 'MM2': (True, 84), 'GG1': (True, 47), 'GG2': (False, 368),
            'OU1': (True, 69), 'OU2': (True, 86), 'PU1': (False, 520), 'PU2': (False, 179)}
# P21
raw[21] = {'MM1': (True, 63), 'MM2': (True, 47), 'GG1': (True, 514), 'GG2': (False, 418),
            'OU1': (True, 153), 'OU2': (True, 54), 'PU1': (False, 338), 'PU2': (False, 97)}
# P22
raw[22] = {'MM1': (True, 88), 'MM2': (True, 265), 'GG1': (False, 474), 'GG2': (False, 313),
            'OU1': (True, 56), 'OU2': (True, 65), 'PU1': (False, 385), 'PU2': (False, 392)}
# P23 - GG1 has "N/A (3:20)" in raw data, treat as failed with time 200s
raw[23] = {'MM1': (True, 41), 'MM2': (True, 71), 'GG1': (False, 200), 'GG2': (False, 250),
            'OU1': (True, 60), 'OU2': (True, 60), 'PU1': (False, 185), 'PU2': (False, 103)}
# P24
raw[24] = {'MM1': (True, 39), 'MM2': (True, 53), 'GG1': (True, 61), 'GG2': (False, 264),
            'OU1': (True, 64), 'OU2': (True, 51), 'PU1': (False, 298), 'PU2': (False, 168)}
# P25
raw[25] = {'MM1': (True, 50), 'MM2': (True, 95), 'GG1': (True, 49), 'GG2': (False, 167),
            'OU1': (True, 36), 'OU2': (True, 45), 'PU1': (False, 233), 'PU2': (False, 210)}
# P26
raw[26] = {'MM1': (True, 22), 'MM2': (True, 55), 'GG1': (True, 44), 'GG2': (False, 188),
            'OU1': (True, 55), 'OU2': (True, 23), 'PU1': (False, 144), 'PU2': (False, 181)}
# P27
raw[27] = {'MM1': (True, 54), 'MM2': (True, 187), 'GG1': (True, 96), 'GG2': (False, 321),
            'OU1': (True, 125), 'OU2': (True, 120), 'PU1': (False, 127), 'PU2': (False, 108)}
# P28
raw[28] = {'MM1': (True, 65), 'MM2': (True, 70), 'GG1': (False, 167), 'GG2': (False, 279),
            'OU1': (True, 37), 'OU2': (True, 91), 'PU1': (False, 270), 'PU2': (False, 291)}
# P29
raw[29] = {'MM1': (True, 65), 'MM2': (True, 33), 'GG1': (False, 120), 'GG2': (True, 82),
            'OU1': (True, 56), 'OU2': (True, 173), 'PU1': (False, 165), 'PU2': (False, 235)}
# P30
raw[30] = {'MM1': (True, 60), 'MM2': (True, 56), 'GG1': (False, 207), 'GG2': (True, 84),
            'OU1': (True, 51), 'OU2': (True, 53), 'PU1': (False, 224), 'PU2': (False, 184)}
# P31
raw[31] = {'MM1': (True, 123), 'MM2': (True, 158), 'GG1': (False, 218), 'GG2': (False, 98),
            'OU1': (True, 83), 'OU2': (True, 92), 'PU1': (False, 122), 'PU2': (False, 113)}
# P32
raw[32] = {'MM1': (True, 40), 'MM2': (True, 30), 'GG1': (False, 237), 'GG2': (False, 175),
            'OU1': (True, 31), 'OU2': (True, 18), 'PU1': (False, 85), 'PU2': (False, 68)}
# P33
raw[33] = {'MM1': (True, 59), 'MM2': (True, 64), 'GG1': (True, 158), 'GG2': (False, 376),
            'OU1': (True, 45), 'OU2': (True, 60), 'PU1': (False, 205), 'PU2': (False, 120)}
# P34
raw[34] = {'MM1': (True, 64), 'MM2': (True, 71), 'GG1': (True, 182), 'GG2': (False, 345),
            'OU1': (True, 358), 'OU2': (False, 197), 'PU1': (True, 506), 'PU2': (True, 430)}
# P35
raw[35] = {'MM1': (True, 61), 'MM2': (True, 49), 'GG1': (True, 103), 'GG2': (False, 372),
            'OU1': (True, 83), 'OU2': (True, 45), 'PU1': (False, 241), 'PU2': (False, 231)}
# P36
raw[36] = {'MM1': (True, 54), 'MM2': (True, 257), 'GG1': (False, 224), 'GG2': (False, 173),
            'OU1': (True, 203), 'OU2': (True, 70), 'PU1': (False, 163), 'PU2': (False, 77)}
# P37
raw[37] = {'MM1': (True, 121), 'MM2': (True, 187), 'GG1': (True, 288), 'GG2': (False, 362),
            'OU1': (True, 81), 'OU2': (True, 91), 'PU1': (False, 428), 'PU2': (False, 230)}
# P38
raw[38] = {'MM1': (True, 47), 'MM2': (True, 64), 'GG1': (True, 33), 'GG2': (False, 172),
            'OU1': (True, 44), 'OU2': (True, 21), 'PU1': (False, 117), 'PU2': (False, 149)}
# P39
raw[39] = {'MM1': (True, 42), 'MM2': (False, 262), 'GG1': (True, 68), 'GG2': (False, 355),
            'OU1': (True, 45), 'OU2': (True, 155), 'PU1': (False, 440), 'PU2': (False, 149)}
# P40
raw[40] = {'MM1': (True, 73), 'MM2': (True, 100), 'GG1': (True, 79), 'GG2': (False, 371),
            'OU1': (True, 43), 'OU2': (True, 55), 'PU1': (False, 458), 'PU2': (False, 420)}

# ============================================================
# Analysis 1: Per-site success rates
# ============================================================
print("=" * 60)
print("ANALYSIS 1: Per-site task completion rates")
print("=" * 60)

sites = {'MM': ['MM1', 'MM2'], 'GG': ['GG1', 'GG2'], 'OU': ['OU1', 'OU2'], 'PU': ['PU1', 'PU2']}
for site, tasks in sites.items():
    successes = sum(1 for p in raw.values() for t in tasks if raw[list(raw.keys())[list(raw.values()).index(p)]][t][0])
    # Simpler:
    total = 0
    succ = 0
    for pid, pdata in raw.items():
        for t in tasks:
            total += 1
            if pdata[t][0]:
                succ += 1
    print(f"  {site}: {succ}/{total} = {succ/total*100:.1f}%")

# ============================================================
# Analysis 2: Per-participant time ratio (PU median / OU median)
# ============================================================
print("\n" + "=" * 60)
print("ANALYSIS 2: Per-participant time ratio (PU / OU)")
print("=" * 60)

time_ratios = []
for pid, pdata in raw.items():
    ou_times = [pdata['OU1'][1], pdata['OU2'][1]]
    pu_times = [pdata['PU1'][1], pdata['PU2'][1]]
    ou_med = np.median(ou_times)
    pu_med = np.median(pu_times)
    ratio = pu_med / ou_med if ou_med > 0 else float('inf')
    time_ratios.append(ratio)

time_ratios = np.array(time_ratios)
print(f"  Mean time ratio (PU/OU): {np.mean(time_ratios):.2f}")
print(f"  Median time ratio: {np.median(time_ratios):.2f}")
print(f"  SD: {np.std(time_ratios, ddof=1):.2f}")
# Bootstrap 95% CI
np.random.seed(42)
boot_means = [np.mean(np.random.choice(time_ratios, size=len(time_ratios), replace=True)) for _ in range(10000)]
ci_lo, ci_hi = np.percentile(boot_means, [2.5, 97.5])
print(f"  95% bootstrap CI: [{ci_lo:.2f}, {ci_hi:.2f}]")

# ============================================================
# Analysis 3: Per-participant success delta (high-a11y minus low-a11y)
# ============================================================
print("\n" + "=" * 60)
print("ANALYSIS 3: Per-participant success delta (high - low a11y)")
print("=" * 60)

success_deltas = []
for pid, pdata in raw.items():
    high_succ = sum(1 for t in ['MM1', 'MM2', 'OU1', 'OU2'] if pdata[t][0]) / 4.0
    low_succ = sum(1 for t in ['GG1', 'GG2', 'PU1', 'PU2'] if pdata[t][0]) / 4.0
    success_deltas.append(high_succ - low_succ)

success_deltas = np.array(success_deltas)
print(f"  Mean success delta (high - low): {np.mean(success_deltas):.3f}")
print(f"  SD: {np.std(success_deltas, ddof=1):.3f}")
boot_deltas = [np.mean(np.random.choice(success_deltas, size=len(success_deltas), replace=True)) for _ in range(10000)]
ci_lo, ci_hi = np.percentile(boot_deltas, [2.5, 97.5])
print(f"  95% bootstrap CI: [{ci_lo:.3f}, {ci_hi:.3f}]")
print(f"  All 40 participants had delta >= 0: {all(d >= 0 for d in success_deltas)}")

# ============================================================
# Analysis 4: Variance decomposition (site vs participant)
# ============================================================
print("\n" + "=" * 60)
print("ANALYSIS 4: Variance decomposition")
print("=" * 60)

# Simple two-way ANOVA-style decomposition on success (binary)
# Factors: site (4 levels: MM, GG, OU, PU) and participant (40 levels)
all_obs = []  # (site_idx, participant_idx, success)
site_names = ['MM', 'GG', 'OU', 'PU']
site_tasks = {'MM': ['MM1', 'MM2'], 'GG': ['GG1', 'GG2'], 'OU': ['OU1', 'OU2'], 'PU': ['PU1', 'PU2']}

for pid, pdata in raw.items():
    for si, site in enumerate(site_names):
        for task in site_tasks[site]:
            all_obs.append((si, pid, 1.0 if pdata[task][0] else 0.0))

obs_array = np.array(all_obs)
grand_mean = np.mean(obs_array[:, 2])

# Site means
site_means = {}
for si, site in enumerate(site_names):
    mask = obs_array[:, 0] == si
    site_means[site] = np.mean(obs_array[mask, 2])
    
# Participant means
part_means = {}
for pid in raw.keys():
    mask = obs_array[:, 1] == pid
    part_means[pid] = np.mean(obs_array[mask, 2])

# SS decomposition
ss_total = np.sum((obs_array[:, 2] - grand_mean) ** 2)
ss_site = sum(len([o for o in all_obs if o[0] == si]) * (site_means[site] - grand_mean) ** 2 
              for si, site in enumerate(site_names))
ss_part = sum(len([o for o in all_obs if o[1] == pid]) * (part_means[pid] - grand_mean) ** 2 
              for pid in raw.keys())
ss_resid = ss_total - ss_site - ss_part

print(f"  Grand mean success: {grand_mean:.3f}")
print(f"  Site means: {', '.join(f'{s}={site_means[s]:.3f}' for s in site_names)}")
print(f"  SS_total: {ss_total:.2f}")
print(f"  SS_site: {ss_site:.2f} ({ss_site/ss_total*100:.1f}%)")
print(f"  SS_participant: {ss_part:.2f} ({ss_part/ss_total*100:.1f}%)")
print(f"  SS_residual: {ss_resid:.2f} ({ss_resid/ss_total*100:.1f}%)")

# ============================================================
# Analysis 5: L3-mapped site comparison
# ============================================================
print("\n" + "=" * 60)
print("ANALYSIS 5: L3-mapped comparison (high-a11y vs L3-low)")
print("=" * 60)

# High-a11y sites: MM + OU
high_success = []
high_times = []
for pid, pdata in raw.items():
    for t in ['MM1', 'MM2', 'OU1', 'OU2']:
        high_success.append(1 if pdata[t][0] else 0)
        high_times.append(pdata[t][1])

# L3-low sites: GG + PU (both have structural violations)
low_success = []
low_times = []
for pid, pdata in raw.items():
    for t in ['GG1', 'GG2', 'PU1', 'PU2']:
        low_success.append(1 if pdata[t][0] else 0)
        low_times.append(pdata[t][1])

print(f"  High-a11y (MM+OU): {sum(high_success)}/{len(high_success)} = {sum(high_success)/len(high_success)*100:.1f}%")
print(f"  L3-low (GG+PU): {sum(low_success)}/{len(low_success)} = {sum(low_success)/len(low_success)*100:.1f}%")
print(f"  Delta: {(sum(high_success)/len(high_success) - sum(low_success)/len(low_success))*100:.1f}pp")
print(f"  High-a11y median time: {np.median(high_times):.0f}s")
print(f"  L3-low median time: {np.median(low_times):.0f}s")
print(f"  Time inflation ratio: {np.median(low_times)/np.median(high_times):.1f}x")

# ============================================================
# Analysis 6: Per-site breakdown for paper
# ============================================================
print("\n" + "=" * 60)
print("ANALYSIS 6: Per-site success rates (for L1/L2/L3 mapping)")
print("=" * 60)

for site in ['OU', 'MM', 'GG', 'PU']:
    tasks = site_tasks[site]
    succ = sum(1 for pid in raw for t in tasks if raw[pid][t][0])
    total = sum(1 for pid in raw for t in tasks)
    times = [raw[pid][t][1] for pid in raw for t in tasks]
    print(f"  {site}: success={succ}/{total} ({succ/total*100:.1f}%), "
          f"median_time={np.median(times):.0f}s, mean_time={np.mean(times):.0f}s")

# Sanity checks
print("\n" + "=" * 60)
print("SANITY CHECKS (for Alex to verify)")
print("=" * 60)
print(f"  1. P1 MM1 time = {raw[1]['MM1'][1]}s (should be 82)")
print(f"  2. P34 PU2 status = {'Y' if raw[34]['PU2'][0] else 'N'}, time = {raw[34]['PU2'][1]}s (should be Y, 430)")
print(f"  3. Total observations = {len(all_obs)} (should be 320 = 40 participants × 8 tasks)")
print(f"  4. GG1 completion count = {sum(1 for pid in raw if raw[pid]['GG1'][0])} (paper says 28 = 70% of 40)")
print(f"  5. PU1 completion count = {sum(1 for pid in raw if raw[pid]['PU1'][0])} (paper says 1 = 2.5% of 40)")
