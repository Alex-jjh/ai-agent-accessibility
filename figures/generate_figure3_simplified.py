#!/usr/bin/env python3
"""
Figure 3 (simplified): Three-Agent Observation Architecture
Main paper version — clean, 30-second comprehension target.

Shows: L1 shared DOM → L2/L3 path for Text-Only/SoM → CUA bypasses both.
Strips: CDP API names, function names, Plan D details, pilot numbers.
Keeps: Layer structure, three agent paths, variant injection, phantom bid callout.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8, 'figure.dpi': 300})

# Colors
C_DOM = '#D5F5E3'       # L1 green
C_AX = '#D6EAF8'        # L2 blue
C_BG = '#FEF9E7'        # L3 yellow
C_AGENT = '#FADBD8'     # L4 pink
C_GRAY = '#E5E7E9'      # skipped
C_INJ = '#F9EBEA'       # injection highlight
C_WARN = '#F5B7B1'      # phantom bid
BORDER = '#2C3E50'

# Agent path colors
AT = '#2471A3'  # text-only blue
AS = '#1E8449'  # SoM green
AC = '#C0392B'  # CUA red

def box(ax, x, y, w, h, text, fc, fs=8, bold=False, ec=BORDER, lw=0.8, ls='-', al=1.0, tc='black'):
    r = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03",
                        facecolor=fc, edgecolor=ec, linewidth=lw, linestyle=ls, alpha=al)
    ax.add_patch(r)
    ax.text(x + w/2, y + h/2, text, fontsize=fs, fontweight='bold' if bold else 'normal',
            ha='center', va='center', color=tc, linespacing=1.3)

def arr(ax, x1, y1, x2, y2, c=BORDER, lw=1.2, ls='-'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=c, lw=lw, linestyle=ls))

def lbl(ax, x, y, text, fs=7, c='black', ha='center', va='center', wt='normal', sty='normal'):
    ax.text(x, y, text, fontsize=fs, color=c, ha=ha, va=va, fontweight=wt, fontstyle=sty,
            linespacing=1.2)


def draw():
    fig, ax = plt.subplots(1, 1, figsize=(12, 9))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_aspect('equal')

    # ── L1: DOM (shared, full width) ──────────────────────────
    box(ax, 0.5, 0.3, 11, 1.8, '', C_DOM, ec='#1E8449', lw=2)
    lbl(ax, 6, 1.9, 'L1: DOM — ★ THE ONLY LAYER WE MODIFY', fs=10, wt='bold', c='#1E8449')

    # DOM content (left)
    box(ax, 0.8, 0.5, 4.5, 1.0,
        'Semantic HTML Elements\n<nav>, <a href>, <button>, <h1>\naria-label, role, tabindex',
        '#E8F8F5', fs=7)

    # Rendered pixels (right)
    box(ax, 6.5, 0.5, 4.7, 1.0,
        'Rendered Pixels\nCSS + DOM → visual layout\nCUA observes this directly',
        '#EEEEEE', fs=7)

    # Variant injection bar
    box(ax, 0.8, 1.55, 10.4, 0.35,
        '▶ Variant injection: DOM patches applied here (low / medium-low / base / high)',
        C_INJ, fs=7, bold=True, ec=AC, lw=1.5, tc='#922B21')

    # ── Branch point ──────────────────────────────────────────
    lbl(ax, 6, 2.35, 'Observation paths diverge ↑', fs=7, c='#555', sty='italic')

    # Left arrow: L1 → L2 (Text-Only / SoM path)
    arr(ax, 4, 2.1, 4, 2.8, c=AT, lw=2)
    lbl(ax, 2.8, 2.45, 'Chrome auto-derives', fs=6.5, c=AT, ha='right')

    # Right arrow: L1 → L4 CUA (skip L2/L3)
    arr(ax, 9.5, 2.1, 9.5, 7.0, c=AC, lw=2.5, ls='--')
    lbl(ax, 10.2, 4.5, 'CUA bypasses\nL2 + L3\nentirely', fs=8, c=AC, wt='bold', ha='left')

    # ── L2: AX Tree (left side only) ─────────────────────────
    box(ax, 0.5, 2.8, 7, 1.2,
        'L2: Accessibility Tree (Chrome Internal)\n'
        'Auto-derived from DOM. Roles, names, states, children.\n'
        'If variant removes aria-label → this node loses its name.',
        C_AX, fs=7.5)
    lbl(ax, 0.2, 3.4, 'L2', fs=9, wt='bold', ha='right', c=AT)

    # Grayed L2 for CUA
    box(ax, 8, 2.8, 3.5, 1.2,
        'L2: AX Tree\n\n(CUA never reads)',
        C_GRAY, fs=7, ec='#AAA', ls='--', al=0.5)
    lbl(ax, 9.75, 3.0, 'SKIPPED', fs=8, c='#999', wt='bold')

    # Arrow L2 → L3
    arr(ax, 4, 4.0, 4, 4.5, c=AT, lw=2)

    # ── L3: BrowserGym (left side only) ──────────────────────
    box(ax, 0.5, 4.5, 7, 1.5, '', C_BG)
    lbl(ax, 0.2, 5.25, 'L3', fs=9, wt='bold', ha='right', c='#7D6608')
    lbl(ax, 4, 5.85, 'L3: BrowserGym Processing', fs=8, wt='bold', c='#7D6608')

    # Two output sub-boxes
    box(ax, 0.8, 4.65, 3.0, 0.9,
        'AXTree Serialization\n[42] link "Home"\n[43] button "Submit"',
        '#FFF9E6', fs=7)

    box(ax, 4.1, 4.65, 3.1, 0.9,
        'SoM Overlay Generation\nbid labels drawn on\nscreenshot as numbered tags',
        '#FFF9E6', fs=7)

    # Grayed L3 for CUA
    box(ax, 8, 4.5, 3.5, 1.5,
        'L3: BrowserGym\n\n(CUA uses only for\nsetup + evaluation)',
        C_GRAY, fs=7, ec='#AAA', ls='--', al=0.5)
    lbl(ax, 9.75, 4.7, 'SKIPPED', fs=8, c='#999', wt='bold')

    # ── L3 → L4 output arrows ────────────────────────────────
    # Text-Only
    arr(ax, 2.3, 5.55, 2.3, 7.0, c=AT, lw=2)
    lbl(ax, 1.5, 6.3, 'AXTree\ntext', fs=7, c=AT, wt='bold', ha='right')

    # SoM
    arr(ax, 5.6, 5.55, 5.6, 7.0, c=AS, lw=2)
    lbl(ax, 6.4, 6.3, 'Screenshot\n+ bid labels', fs=7, c=AS, wt='bold', ha='left')

    # ── L4: Three Agent boxes ─────────────────────────────────
    lbl(ax, 6, 8.7, 'L4: Agent Observation & Action', fs=10, wt='bold')

    # Text-Only
    box(ax, 0.3, 7.0, 3.2, 1.5,
        'Text-Only Agent\n\nObserves: AXTree text\nActs: click("bid")\n→ BrowserGym resolves',
        C_AGENT, fs=7.5, bold=True, ec=AT, lw=2)

    # SoM
    box(ax, 4.0, 7.0, 3.2, 1.5,
        'SoM Vision Agent\n\nObserves: Screenshot + bids\nActs: click("bid")\n→ same resolution path',
        C_AGENT, fs=7.5, bold=True, ec=AS, lw=2)

    # CUA
    box(ax, 8.0, 7.0, 3.5, 1.5,
        'CUA Agent\n\nObserves: Raw screenshot\nActs: mouse.click(x, y)\n→ direct to DOM (no bid)',
        C_AGENT, fs=7.5, bold=True, ec=AC, lw=2)

    # ── Phantom bid callout ───────────────────────────────────
    box(ax, 4.2, 6.15, 3.0, 0.7,
        '⚠ PHANTOM BID\nVariant removes DOM node →\nbid label persists in screenshot',
        C_WARN, fs=6.5, bold=True, ec='#C0392B', lw=1.5)

    # ── Legend ────────────────────────────────────────────────
    legend_elements = [
        Line2D([0], [0], color=AT, lw=2, label='Text-Only path (L1→L2→L3→L4)'),
        Line2D([0], [0], color=AS, lw=2, label='SoM path (same pipeline, different L3 output)'),
        Line2D([0], [0], color=AC, lw=2, ls='--', label='CUA path (L1→L4 direct, skips L2+L3)'),
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=7.5,
              framealpha=0.95, edgecolor='#999', bbox_to_anchor=(1.0, -0.02))

    fig.tight_layout(pad=0.3)
    fig.savefig('figures/figure3_three_agent_arch.png', dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    print('✅ Figure 3 saved: figures/figure3_three_agent_arch.png')


if __name__ == '__main__':
    draw()
