#!/usr/bin/env python3
"""
Figure 1: Variant Injection Pipeline (Teaser)

Communicates the paper's experimental manipulation in three panels:
  (1) Real website source (ecological validity)
  (2) DOM-level injection engine with 3 independently controllable layers (L1/L2/L3)
  (3) 4 output accessibility variants (Low / Medium-low / Base / High)

Part of a unified figure set for the CHI 2027 submission:
  - Figure 1 (this file): Experimental design teaser
  - Figure 2: Main results bar chart (success rates)
  - Figure 3: Three-Agent Observation Architecture (simplified)
  - Figure 4: Causal decomposition schematic
  - Figure 5: Per-task heatmap
  - Appendix A1: Full layer architecture (implementation details)

Color palette and helper functions mirror Figure 3 for visual cohesion.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8, 'figure.dpi': 300})

# Shared palette (keep in sync with figure3_simplified)
C_L1 = '#D5F5E3'; C_L2 = '#D6EAF8'; C_L4 = '#FADBD8'
C_INJ_FILL = '#F9EBEA'; C_INJ_BORDER = '#922B21'
C_GRAY = '#E5E7E9'; BORDER = '#2C3E50'
# Variant colors
C_HIGH = '#27AE60'; C_BASE = '#2471A3'; C_ML = '#E67E22'; C_LOW = '#C0392B'
# Layer fills for engine sub-boxes
C_ENG_L1 = '#E8DAEF'  # decorative purple
C_ENG_L2 = '#D6EAF8'  # annotational blue
C_ENG_L3 = '#FADBD8'  # structural red
# Variant light fills
CF_HIGH = '#EAFAF1'; CF_BASE = '#EBF5FB'; CF_ML = '#FEF5E7'; CF_LOW = '#FDEDEC'


def _box(ax, x, y, w, h, text, fc, fs=7, bold=False, ec=BORDER, lw=0.7,
         ls='-', tc='black', al=1.0, va='center', ha='center', lh=1.3):
    r = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04",
                        facecolor=fc, edgecolor=ec, linewidth=lw, linestyle=ls, alpha=al)
    ax.add_patch(r)
    if text:
        ax.text(x + w/2, y + h/2, text, fontsize=fs,
                fontweight='bold' if bold else 'normal',
                ha=ha, va=va, color=tc, linespacing=lh)

def _arr(ax, x1, y1, x2, y2, c=BORDER, lw=1.2, ls='-', st='->'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=st, color=c, lw=lw, linestyle=ls))

def _lbl(ax, x, y, text, fs=7, c='black', ha='center', va='center',
         wt='normal', sty='normal'):
    ax.text(x, y, text, fontsize=fs, color=c, ha=ha, va=va,
            fontweight=wt, fontstyle=sty, linespacing=1.2)


def _draw_browser(ax, x, y, w, h, ec='#AAAAAA', fc='white', degraded=0):
    """Draw a stylized browser window mockup.
    degraded: 0=crisp, 1=slight, 2=medium, 3=heavy (visual cue for variant quality)
    """
    # Browser chrome (title bar)
    chrome_h = h * 0.18
    _box(ax, x, y + h - chrome_h, w, chrome_h, '', '#F0F0F0', ec=ec, lw=0.8)
    # Traffic light dots
    dot_y = y + h - chrome_h/2
    for i, dc in enumerate(['#E74C3C', '#F39C12', '#27AE60']):
        ax.plot(x + 0.15 + i*0.12, dot_y, 'o', color=dc, markersize=2.5, zorder=5)
    # Address bar
    _box(ax, x + 0.5, dot_y - 0.06, w - 0.65, 0.12, '', '#E8E8E8', ec='#CCC', lw=0.3)

    # Content area
    content_y = y
    content_h = h - chrome_h
    _box(ax, x, content_y, w, content_h, '', fc, ec=ec, lw=0.8)

    # Wireframe elements inside
    cx = x + 0.08
    cw = w - 0.16
    cy_top = content_y + content_h - 0.08

    # Header bar
    bar_c = '#CCCCCC' if degraded < 3 else '#DDDDDD'
    _box(ax, cx, cy_top - 0.18, cw, 0.16, '', bar_c, ec='#BBB', lw=0.3)

    # Nav links (3 small boxes)
    nav_y = cy_top - 0.42
    if degraded < 3:
        link_w = cw * 0.28
        for i in range(3):
            lc = '#B0B0B0' if degraded < 2 else '#D5D5D5'
            _box(ax, cx + i * (link_w + 0.04), nav_y, link_w, 0.12, '', lc, ec='#AAA', lw=0.3)
    else:
        # Degraded: one amorphous gray block replacing nav
        _box(ax, cx, nav_y, cw, 0.12, '', '#E0E0E0', ec='#DDD', lw=0.3)

    # Content blocks
    block_y = nav_y - 0.22
    if degraded < 2:
        _box(ax, cx, block_y - 0.25, cw * 0.6, 0.23, '', '#D0D0D0', ec='#BBB', lw=0.3)
        _box(ax, cx + cw * 0.65, block_y - 0.25, cw * 0.33, 0.23, '', '#D8D8D8', ec='#BBB', lw=0.3)
    else:
        _box(ax, cx, block_y - 0.25, cw, 0.23, '', '#E0E0E0', ec='#DDD', lw=0.3)

    # Button
    btn_y = block_y - 0.48
    if degraded < 3:
        btn_c = '#A0A0A0' if degraded < 1 else '#C0C0C0'
        _box(ax, cx + cw * 0.3, btn_y, cw * 0.4, 0.14, '', btn_c, ec='#999', lw=0.4)
    else:
        # Degraded: amorphous shape
        _box(ax, cx + cw * 0.25, btn_y, cw * 0.5, 0.14, '', '#DDDDDD', ec='#DDD', lw=0.3)


def draw():
    fig, ax = plt.subplots(1, 1, figsize=(14, 6))
    ax.set_xlim(0, 14)
    ax.set_ylim(-0.5, 6)
    ax.axis('off')
    ax.set_aspect('equal')

    # ================================================================
    # PANEL 1 (Left): Real Website Source
    # ================================================================
    _lbl(ax, 2.5, 5.6, 'Source: Real Websites', fs=9, wt='bold')

    # Large browser mockup
    _draw_browser(ax, 0.7, 2.0, 3.6, 3.2, ec='#888888')

    # Caption below
    _lbl(ax, 2.5, 1.6, 'N=34 WebArena + real-web sample\n'
         '83.3% contain L3 structural violations\n'
         '(axe-core ecological audit)',
         fs=7, c='#555555')

    # ================================================================
    # Arrow: Panel 1 → Panel 2
    # ================================================================
    _arr(ax, 4.5, 3.6, 5.2, 3.6, c=BORDER, lw=2.0)
    _lbl(ax, 4.85, 3.85, 'Load page', fs=7, wt='bold', c='#333')

    # ================================================================
    # PANEL 2 (Middle): Variant Injection Engine
    # ================================================================
    _lbl(ax, 7.25, 5.6, 'Injection Engine (DOM-level)', fs=9, wt='bold')

    # Engine outer box
    _box(ax, 5.2, 1.5, 4.1, 3.8, '', C_INJ_FILL, ec=C_INJ_BORDER, lw=1.8)

    # L1 Decorative sub-layer
    _box(ax, 5.4, 4.2, 3.7, 0.8,
         'L1  Decorative\nStrip alt text, remove decorative ARIA',
         C_ENG_L1, fs=7, ec='#8E44AD', lw=0.8)

    # L2 Annotational sub-layer
    _box(ax, 5.4, 3.15, 3.7, 0.8,
         'L2  Annotational\nRemove aria-label, break label associations',
         C_ENG_L2, fs=7, ec='#2471A3', lw=0.8)

    # L3 Structural sub-layer (emphasized)
    _box(ax, 5.4, 1.9, 3.7, 1.0,
         'L3  Structural  ★\nReplace <nav>/<button>/<a>\nwith <div>/<span> + JS handlers',
         C_ENG_L3, fs=7.5, bold=True, ec=C_LOW, lw=2.0, tc='#922B21')

    # "Independently controlled" annotation
    _lbl(ax, 9.0, 4.6, '☑ L1\n☑ L2\n☑ L3', fs=7, c='#555', ha='left')
    _lbl(ax, 9.0, 3.7, 'Independently\ncontrolled', fs=7, c='#777', ha='left', sty='italic')

    # Caption below engine
    _lbl(ax, 7.25, 1.15, 'DOM-level JS injection via\nPlaywright context.route\n'
         'Persisted across navigations',
         fs=7, c='#555555')

    # ================================================================
    # Arrow: Panel 2 → Panel 3 (fan-out into 4)
    # ================================================================
    fan_x = 9.5
    fan_end_x = 10.3
    # Main arrow stem
    _arr(ax, fan_x, 3.6, fan_end_x - 0.15, 3.6, c=BORDER, lw=2.0, st='-')

    # 4 fan-out arrows to each variant
    variant_ys = [4.85, 3.85, 2.85, 1.85]  # High, Base, ML, Low (top to bottom)
    variant_cs = [C_HIGH, C_BASE, C_ML, C_LOW]
    for vy, vc in zip(variant_ys, variant_cs):
        _arr(ax, fan_end_x - 0.15, 3.6, fan_end_x, vy + 0.35, c=vc, lw=1.5)

    # ================================================================
    # PANEL 3 (Right): 4 Output Variants
    # ================================================================
    _lbl(ax, 12.2, 5.6, 'Output: 4 Accessibility Variants', fs=9, wt='bold')

    variants = [
        ('High',       C_HIGH, CF_HIGH, 0, '+ all WCAG AAA labels'),
        ('Base',       C_BASE, CF_BASE, 0, '(real-world baseline)'),
        ('Medium-low', C_ML,   CF_ML,   2, '− ARIA labels (L2)'),
        ('Low',        C_LOW,  CF_LOW,  3, '− ARIA + structural (L2+L3)'),
    ]

    bw = 2.2   # browser width
    bh = 0.85  # browser height
    bx = 10.4  # browser x start

    for i, (name, ec, fc, deg, desc) in enumerate(variants):
        by = variant_ys[i]
        _draw_browser(ax, bx, by, bw, bh, ec=ec, fc=fc, degraded=deg)
        # Variant label to the right
        _lbl(ax, bx + bw + 0.1, by + bh * 0.6, name, fs=8, wt='bold', c=ec, ha='left')
        # Description below
        _lbl(ax, bx + bw/2, by - 0.12, desc, fs=6.5, c='#666', sty='italic')

    # ================================================================
    # Bottom bridge caption (full width)
    # ================================================================
    _lbl(ax, 7.0, -0.15,
         '→ Feed to 3 agent architectures (Text-only, SoM, CUA) × 2 models '
         '(Claude, Llama 4) × 13 tasks × 5 trials = 1,040 cases.  '
         'See Figure 2 for results, Figure 3 for agent architecture.',
         fs=8, c='#333333')

    # ================================================================
    # Save
    # ================================================================
    fig.savefig('figures/figure1_variant_injection_pipeline.png',
                dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close(fig)
    print('✅ Figure 1 saved: figures/figure1_variant_injection_pipeline.png')


if __name__ == '__main__':
    draw()
