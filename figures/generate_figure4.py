#!/usr/bin/env python3
"""
Figure 4: Layer Model — Observation, Action, Injection, and bid Lifecycle

Shows the 5-layer architecture with:
- Where each agent observes and acts
- Where variant patches inject
- The full bid lifecycle (birth → AX Tree → serialization → agent → action → DOM)
- Phantom bid failure mechanism

Output: figures/figure4_layer_model.png
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrow
from matplotlib.lines import Line2D
import numpy as np

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 9,
    'figure.dpi': 300,
})

# Colors
C_L0 = '#E8DAEF'   # purple - server
C_L1 = '#D5F5E3'   # green - DOM
C_L2 = '#D6EAF8'   # blue - AX Tree
C_L3 = '#FEF9E7'   # yellow - BrowserGym
C_L4 = '#FADBD8'   # pink - Agent
C_BID = '#F9E79F'   # gold - bid lifecycle
C_PHANTOM = '#F5B7B1'  # red - phantom bid
C_INJECT = '#F1948A'    # dark red - injection
C_TEXT_AG = '#2471A3'
C_SOM_AG = '#1E8449'
C_CUA_AG = '#C0392B'
BORDER = '#2C3E50'


def _box(ax, x, y, w, h, text, fc, fs=7.5, bold=False, ec=BORDER, lw=0.8,
         ls='-', tc='black'):
    r = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02",
                       facecolor=fc, edgecolor=ec, linewidth=lw, linestyle=ls)
    ax.add_patch(r)
    wt = 'bold' if bold else 'normal'
    ax.text(x + w/2, y + h/2, text, fontsize=fs, fontweight=wt,
            ha='center', va='center', color=tc)

def _arr(ax, x1, y1, x2, y2, c=BORDER, lw=1.0, ls='-', cs='arc3,rad=0', st='->'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=st, color=c, lw=lw,
                                linestyle=ls, connectionstyle=cs))

def _lbl(ax, x, y, text, fs=7, c='black', ha='center', va='center',
         wt='normal', sty='normal', rot=0):
    ax.text(x, y, text, fontsize=fs, color=c, ha=ha, va=va,
            fontweight=wt, fontstyle=sty, rotation=rot)


def draw_figure4():
    fig, ax = plt.subplots(1, 1, figsize=(16, 16))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 16)
    ax.axis('off')
    ax.set_aspect('equal')

    # ── Title ──
    _lbl(ax, 8, 15.7, 'Figure 4: Five-Layer Architecture — Observation, Action, Injection & bid Lifecycle',
         fs=13, wt='bold')
    _lbl(ax, 8, 15.35,
         'Where agents observe, where agents act, where we inject, and how bid connects them all',
         fs=8, c='#555')

    # ════════════════════════════════════════════════════════════════
    # FIVE LAYERS (horizontal bands, bottom to top)
    # ════════════════════════════════════════════════════════════════
    # Each layer: full-width band
    lx = 0.5   # left x
    lw = 10.0  # layer width
    lh = 2.0   # layer height
    gap = 0.3

    layers = [
        (0.5,  C_L0, 'Layer 0', 'WebArena Server (HTTP)'),
        (2.8,  C_L1, 'Layer 1', 'DOM (Live Document Object Model)'),
        (5.3,  C_L2, 'Layer 2', 'Blink AX Tree (Chrome Internal)'),
        (7.8,  C_L3, 'Layer 3', 'BrowserGym Processing'),
        (10.5, C_L4, 'Layer 4', 'Agent Observation & Action'),
    ]

    for ly, lc, label, title in layers:
        # Background band
        band = FancyBboxPatch((lx, ly), lw, lh, boxstyle="round,pad=0.04",
                              facecolor=lc, edgecolor=BORDER, linewidth=1.0, alpha=0.5)
        ax.add_patch(band)
        _lbl(ax, lx + 0.15, ly + lh - 0.15, label, fs=9, wt='bold', ha='left', va='top')
        _lbl(ax, lx + 1.5, ly + lh - 0.15, title, fs=8, ha='left', va='top', c='#444')

    # ════════════════════════════════════════════════════════════════
    # LAYER 0: WebArena Server
    # ════════════════════════════════════════════════════════════════
    _box(ax, 1.0, 0.8, 4.0, 1.0,
         'Magento (ecommerce)\nPostmill (reddit clone)\nGitLab\n'
         'Return original HTML via HTTP',
         C_L0, fs=6.5)
    _box(ax, 5.5, 0.8, 4.5, 1.0,
         'We do NOT modify this layer\n\n'
         'No server-side changes, no DB edits,\n'
         'no template modifications.\n'
         'All manipulation happens client-side.',
         '#F2F3F4', fs=6.5, bold=True)

    # Arrow L0 → L1
    _arr(ax, 3.0, 1.8, 3.0, 2.8, c='#888', lw=1.5)
    _lbl(ax, 3.3, 2.3, 'HTTP Response\n(HTML)', fs=6, c='#888', ha='left')

    # ════════════════════════════════════════════════════════════════
    # LAYER 1: DOM
    # ════════════════════════════════════════════════════════════════
    _box(ax, 1.0, 3.1, 3.0, 1.3,
         'Live DOM\n\n'
         '<nav>, <a href>, <button>,\n'
         '<h1>, <img alt="...">,\n'
         'aria-label, role, tabindex',
         C_L1, fs=6.5)

    _box(ax, 4.3, 3.1, 2.8, 1.3,
         'bid attr on DOM\n\n'
         'BrowserGym writes:\n'
         'browsergym_set_of_marks="42"\n'
         'on each interactive element',
         C_BID, fs=6.5, bold=True, ec='#B7950B')

    _box(ax, 7.4, 3.1, 3.0, 1.3,
         'Rendered Pixels\n\n'
         'CSS + DOM = visual layout\n'
         'page.screenshot() captures\n'
         'this as PNG bitmap',
         '#E8E8E8', fs=6.5)

    # Arrow L1 → L2
    _arr(ax, 2.5, 4.4, 2.5, 5.3, c='#888', lw=1.5)
    _lbl(ax, 2.8, 4.85, 'Chrome auto-builds\nAX Tree from DOM', fs=6, c='#888', ha='left')

    # bid write-back arrow (L3 → L1)
    _arr(ax, 5.7, 7.8, 5.7, 4.4, c='#B7950B', lw=2.0, ls='--')
    _lbl(ax, 6.0, 6.1, 'BrowserGym\nwrites bid\nback to DOM', fs=6, c='#B7950B', ha='left', wt='bold')

    # ════════════════════════════════════════════════════════════════
    # LAYER 2: Blink AX Tree
    # ════════════════════════════════════════════════════════════════
    _box(ax, 1.0, 5.6, 4.5, 1.3,
         'Blink AX Tree (Chrome internal)\n\n'
         'Nodes: role, name, properties, children\n'
         'Derived from: DOM elements + CSS + ARIA attrs\n'
         'bid appears as node property\n'
         '(from browsergym_set_of_marks DOM attr)',
         C_L2, fs=6.5)

    _box(ax, 5.8, 5.6, 4.5, 1.3,
         'Key: AX Tree is DERIVED, not independent\n\n'
         'If DOM changes (variant patch removes aria-label)\n'
         '-> Blink rebuilds AX Tree automatically\n'
         '-> node loses its accessible name\n'
         '-> agent sees degraded information',
         '#EBF5FB', fs=6.5, bold=True)

    # Arrow L2 → L3
    _arr(ax, 3.25, 6.9, 3.25, 7.8, c='#888', lw=1.5)
    _lbl(ax, 3.6, 7.35, 'CDP\ngetFullAXTree', fs=6, c='#2471A3', ha='left', wt='bold')

    # ════════════════════════════════════════════════════════════════
    # LAYER 3: BrowserGym
    # ════════════════════════════════════════════════════════════════
    _box(ax, 1.0, 8.1, 3.2, 1.3,
         'AXTree Serialization\n\n'
         'flatten_axtree_to_str()\n'
         '[42] link "Home"\n'
         '[43] button "Submit"\n'
         '[44] textbox "Search"',
         C_L3, fs=6.5)

    _box(ax, 4.5, 8.1, 3.0, 1.3,
         'SoM Overlay Generation\n\n'
         'For each bid with clickable=True:\n'
         '  getBoundingClientRect()\n'
         '  PIL: draw red box + white "42"\n'
         '  on screenshot image',
         C_L3, fs=6.5)

    _box(ax, 7.8, 8.1, 2.5, 1.3,
         'bid Mapping Table\n\n'
         'bid "42" -> DOM element\n'
         'Used to resolve\n'
         'click("42") actions',
         C_BID, fs=6.5, bold=True, ec='#B7950B')

    # Arrow L3 → L4
    _arr(ax, 2.6, 9.4, 2.6, 10.5, c=C_TEXT_AG, lw=2.0)
    _lbl(ax, 2.9, 9.95, 'AXTree text', fs=6.5, c=C_TEXT_AG, ha='left', wt='bold')

    _arr(ax, 6.0, 9.4, 6.0, 10.5, c=C_SOM_AG, lw=2.0)
    _lbl(ax, 6.3, 9.95, 'SoM screenshot', fs=6.5, c=C_SOM_AG, ha='left', wt='bold')

    # ════════════════════════════════════════════════════════════════
    # LAYER 4: Agent Observation & Action
    # ════════════════════════════════════════════════════════════════
    _box(ax, 0.7, 10.8, 3.0, 1.3,
         'Text-Only Agent\n\n'
         'OBSERVES: AXTree text\n'
         '  "[42] link Home"\n'
         'ACTS: click("42")\n'
         '  -> BrowserGym resolves bid',
         C_L4, fs=6.5, bold=True, ec=C_TEXT_AG, lw=1.5)

    _box(ax, 4.0, 10.8, 3.0, 1.3,
         'SoM Vision Agent\n\n'
         'OBSERVES: screenshot with\n'
         '  red "42" labels overlaid\n'
         'ACTS: click("42")\n'
         '  -> same bid resolution',
         C_L4, fs=6.5, bold=True, ec=C_SOM_AG, lw=1.5)

    _box(ax, 7.3, 10.8, 3.0, 1.3,
         'CUA Agent\n\n'
         'OBSERVES: raw screenshot\n'
         '  (NO bid, NO AXTree)\n'
         'ACTS: mouse.click(x, y)\n'
         '  -> direct Playwright API',
         C_L4, fs=6.5, bold=True, ec=C_CUA_AG, lw=1.5)

    # CUA direct path (L1 → L4, bypassing L2-L3)
    _arr(ax, 8.9, 4.4, 8.8, 10.8, c=C_CUA_AG, lw=2.5, ls='--')
    _lbl(ax, 9.2, 7.5, 'CUA: direct\nscreenshot\n(skips L2-L3)', fs=7, c=C_CUA_AG, wt='bold', ha='left')

    # Action arrows going back down
    _arr(ax, 2.2, 10.8, 9.05, 9.4, c=C_TEXT_AG, lw=1.2, ls=':', cs='arc3,rad=0.1')
    _arr(ax, 5.5, 10.8, 9.05, 9.2, c=C_SOM_AG, lw=1.2, ls=':', cs='arc3,rad=0.05')
    _lbl(ax, 8.5, 10.1, 'click("bid")\nresolves via\nbid mapping', fs=5.5, c='#666', ha='right')

    # bid mapping → DOM (action execution)
    _arr(ax, 9.05, 8.1, 9.05, 4.4, c='#B7950B', lw=1.5, ls=':')
    _lbl(ax, 9.3, 6.2, 'Resolve bid\n-> find DOM\nelement\n-> Playwright\n.click()',
         fs=5.5, c='#B7950B', ha='left')

    # CUA action path
    _arr(ax, 8.8, 10.8, 8.9, 4.4, c=C_CUA_AG, lw=1.5, ls=':')
    _lbl(ax, 8.3, 7.5, '', fs=1)  # spacer

    # ════════════════════════════════════════════════════════════════
    # RIGHT COLUMN: Injection & Phantom bid
    # ════════════════════════════════════════════════════════════════
    rx = 11.0
    rw = 4.5

    # Injection section
    _lbl(ax, rx + rw/2, 15.0, 'Variant Injection', fs=10, wt='bold')
    _lbl(ax, rx + rw/2, 14.7, '(all 3 layers target Layer 1: DOM)', fs=7, c='#922B21')

    _box(ax, rx, 13.5, rw, 0.8,
         'Three Injection Mechanisms\n'
         '(different timing, same target: DOM)',
         C_INJECT, fs=7.5, bold=True)

    _box(ax, rx, 12.4, rw, 0.8,
         'L1: page.evaluate(variant_js)\n'
         'One-shot after env.reset(). Direct DOM manipulation.',
         '#FADBD8', fs=6.5)

    _box(ax, rx, 11.4, rw, 0.8,
         'L2: page.on("load", re-inject)\n'
         'Re-apply when Magento KnockoutJS re-renders DOM.',
         '#FADBD8', fs=6.5)

    _box(ax, rx, 10.2, rw, 1.0,
         'L3 (Plan D): context.route("**/*")\n'
         'Intercept HTTP response, inject <script> into HTML.\n'
         'Script executes: load + 500ms + MutationObserver.\n'
         'Catches goto() navigations that L1/L2 miss.',
         '#F1948A', fs=6.5, bold=True)

    # Arrow from injection to Layer 1
    _arr(ax, rx, 12.0, 5.7, 4.4, c='#922B21', lw=2.5, cs='arc3,rad=0.3')
    _lbl(ax, 8.5, 8.0, '', fs=1)  # spacer

    _box(ax, rx + 0.2, 9.0, rw - 0.4, 0.8,
         'All 3 mechanisms execute the SAME JS:\n'
         'apply-low.js / apply-medium-low.js / apply-high.js\n'
         'Target: DOM elements, attrs, event handlers',
         '#F2F3F4', fs=6.5, bold=True)

    # Arrow label
    _lbl(ax, 10.0, 5.5, 'Variant JS\nmodifies DOM\n(Layer 1)', fs=7, c='#922B21', wt='bold')

    # ── Phantom bid section ──
    _lbl(ax, rx + rw/2, 8.3, 'Phantom bid Mechanism', fs=10, wt='bold', c='#922B21')

    _box(ax, rx, 5.5, rw, 2.5,
         'How variant patches break bid:\n\n'
         '1. Step N: BrowserGym assigns bid="229"\n'
         '   to <a href="/forum"> in DOM\n\n'
         '2. Variant patch: <a> -> <span onclick>\n'
         '   Old DOM node (with bid) is DELETED\n'
         '   New <span> has NO bid attribute\n\n'
         '3. SoM overlay was drawn at Step N\n'
         '   Red "229" label persists in screenshot\n\n'
         '4. Step N+1: Agent sees "229" in image\n'
         '   Outputs click("229")\n'
         '   BrowserGym: "Could not find element"\n'
         '   Agent retries 20+ times -> FAILURE',
         C_PHANTOM, fs=6.5, ec='#922B21', lw=1.5)

    _box(ax, rx, 4.3, rw, 0.9,
         'Two phantom bid modes (Pilot 4):\n\n'
         'Mode A (Magento): element exists, bid="0"\n'
         '  -> "element is not visible" error\n'
         'Mode B (Postmill): element replaced entirely\n'
         '  -> "Could not find element with bid" error',
         '#FADBD8', fs=6.5)

    _box(ax, rx, 3.2, rw, 0.8,
         'CUA is IMMUNE to phantom bids\n\n'
         'CUA never uses bid. It clicks (x,y) coordinates.\n'
         'But if <a> -> <span> deletes href,\n'
         'CUA click lands but navigation fails.',
         '#D5F5E3', fs=6.5, bold=True, ec=C_CUA_AG)

    # ── Propagation summary ──
    _box(ax, rx, 1.5, rw, 1.4,
         'Variant Propagation Paths:\n\n'
         'Pure semantic (rm aria-label, role):\n'
         '  DOM -> AX Tree -> BrowserGym -> Text-Only\n'
         '  Screenshot unchanged -> CUA unaffected\n\n'
         'Structural (h1->div, nav->div):\n'
         '  DOM -> AX Tree -> Text-Only affected\n'
         '  Screenshot: minimal visual change\n\n'
         'Functional (a->span, rm href):\n'
         '  DOM behavior changed -> ALL agents affected\n'
         '  CUA: 100% of low failures are here',
         '#EBF5FB', fs=6, bold=True)

    # ── Bottom caption ──
    _box(ax, 0.5, 0.1, 15.0, 0.5,
         'bid is born in Layer 3 (BrowserGym), written to Layer 1 (DOM), read back via Layer 2 (AX Tree), '
         'and used by agents in Layer 4 to execute actions back on Layer 1. '
         'Variant patches at Layer 1 can break this cycle -> phantom bids.',
         '#EBF5FB', fs=7, bold=True)

    # ── Legend ──
    legend_elements = [
        Line2D([0], [0], color=C_TEXT_AG, lw=2, label='Text-Only Agent path'),
        Line2D([0], [0], color=C_SOM_AG, lw=2, label='SoM Vision Agent path'),
        Line2D([0], [0], color=C_CUA_AG, lw=2, ls='--', label='CUA Agent path (bypasses L2-L3)'),
        Line2D([0], [0], color='#B7950B', lw=2, ls='--', label='bid lifecycle (L3 -> L1 -> L2 -> L3 -> L4)'),
        Line2D([0], [0], color='#922B21', lw=2.5, label='Variant injection (all target Layer 1)'),
    ]
    ax.legend(handles=legend_elements, loc='lower left', fontsize=7,
              framealpha=0.9, edgecolor='#999', bbox_to_anchor=(0.0, 0.04))

    fig.tight_layout(pad=0.3)
    fig.savefig('figures/figure4_layer_model.png', dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    print('Done: figures/figure4_layer_model.png')


if __name__ == '__main__':
    draw_figure4()
