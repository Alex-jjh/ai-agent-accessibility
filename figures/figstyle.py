"""
figstyle.py — shared publication-style config for the CHI 2027 data figures.

One import to fix the issues the scipilot figure review found across all six
matplotlib figures (fig3/6/7/8/9/10):

  - pdf.fonttype/ps.fonttype = 42  → no Type-3 fonts (ACM/CHI preflight passes,
    text stays selectable/searchable).
  - axes.unicode_minus = False     → ASCII minus, no tofu box for '-'.
  - figsize helpers keyed to the REAL single-column manuscript text width
    (\columnwidth == \textwidth == 430.0pt == 5.95in, measured 2026-06-28), so
    figures are authored at final print size and LaTeX does not rescale them
    (no sub-6pt shrink).
  - SEMANTIC palette identical to the schematic drawio figures (Low/Midlow/High,
    variant ramp, model colors) so colour means the same thing across ALL
    figures — we keep this palette (NOT a swap to Okabe-Ito, which would break
    cross-figure consistency with the 5 drawio schematics) and instead add the
    REDUNDANT non-colour channel (hatch / marker) the review asked for, which is
    what actually makes a figure colourblind- and grayscale-safe.

Usage:
    from figstyle import apply_rc, COLWIDTH_IN, FAMILY_COLORS, FAMILY_HATCH
    apply_rc()
    fig, ax = plt.subplots(figsize=(COLWIDTH_IN, 4.0))
"""
import matplotlib

# Real single-column manuscript text width (acmart manuscript, measured via
# \the\columnwidth = 430.0pt; 1in = 72.27pt).
COLWIDTH_PT = 430.0
COLWIDTH_IN = COLWIDTH_PT / 72.27          # 5.95 in — full text column
HALFWIDTH_IN = COLWIDTH_IN / 2             # 2.97 in — for side-by-side use


def apply_rc(base_fontsize: float = 8.0):
    """Set the shared rcParams. Call once at the top of each figure script,
    AFTER `matplotlib.use('Agg')`."""
    matplotlib.rcParams.update({
        'font.family': 'DejaVu Sans',
        'font.size': base_fontsize,
        'figure.dpi': 300,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'pdf.fonttype': 42,      # TrueType, not Type-3 (ACM/CHI preflight)
        'ps.fonttype': 42,
        'axes.unicode_minus': False,   # ASCII '-' instead of U+2212 tofu risk
    })


# ── Semantic palette (identical to the drawio schematics fig1/4/5/figA1) ──
# One hue == one meaning across every figure in the paper.
FAMILY_COLORS = {'Low': '#C0392B', 'Midlow': '#E67E22', 'High': '#27AE60'}

# Redundant, colour-independent channel for the operator families — so the
# Low/Midlow/High distinction survives grayscale + colour-vision deficiency.
FAMILY_HATCH = {'Low': '', 'Midlow': '///', 'High': 'xxx'}

# Ordinal variant ramp (token-violin etc.). Sequential single-hue-ish ordering
# low → high; reused consistently across figures.
VARIANT_COLORS = {
    'low': '#C0392B', 'medium-low': '#E67E22',
    'base': '#2C3E50', 'high': '#27AE60',
}

# Model colours (cross-model figures). Distinct hue + always paired with a
# distinct marker shape (circle vs diamond) for redundancy.
MODEL_COLORS = {'claude': '#2471A3', 'llama': '#8E44AD'}
MODEL_MARKER = {'claude': 'o', 'llama': 'D'}

# Alignment-quadrant encoding (fig8): colour + a redundant marker shape so the
# four quadrants are distinguishable without colour.
QUADRANT_COLORS = {
    'Aligned (both active)': '#27AE60',
    'Aligned (both null)': '#2471A3',
    'Agent adaptation': '#E67E22',
    'Structural criticality': '#C0392B',
}
QUADRANT_MARKER = {
    'Aligned (both active)': 'o',
    'Aligned (both null)': 's',
    'Agent adaptation': '^',
    'Structural criticality': 'D',
}

NEUTRAL = '#2C3E50'
