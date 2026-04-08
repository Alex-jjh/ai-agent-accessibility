#!/usr/bin/env python3
"""
Generate three architecture diagrams for the AI Agent Accessibility research platform.

Figure 1: System Architecture Overview — data flow, component interaction, 3-layer injection
Figure 2: A11y Tree Processing Pipeline — from Chrome internals to agent observation
Figure 3: Variant Injection Detail — what each variant patches and where

Output: figures/figure1_system_architecture.png
        figures/figure2_axtree_pipeline.png
        figures/figure3_variant_injection.png

Usage: python figures/generate_figures.py
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D
import textwrap

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 9,
    'axes.linewidth': 0.5,
    'figure.dpi': 300,
})

# ── Colors ──
C_TEXT   = '#D6EAF8'
C_SOM    = '#D5F5E3'
C_CUA    = '#FADBD8'
C_BGYM   = '#FEF9E7'
C_BROWSER = '#F2F3F4'
C_PLAND  = '#F9EBEA'
C_WEBARENA = '#E8DAEF'
C_HIGHLIGHT = '#FDEBD0'
C_WARNING = '#F5B7B1'
C_GRAY   = '#D7DBDD'
C_LOW    = '#F5B7B1'
C_MEDLOW = '#FAD7A0'
C_BASE   = '#D5F5E3'
C_HIGH   = '#AED6F1'
BORDER   = '#2C3E50'
A_TEXT   = '#2471A3'
A_SOM    = '#1E8449'
A_CUA    = '#C0392B'
A_MAIN   = '#2C3E50'


def _box(ax, x, y, w, h, text, fc, fs=7.5, bold=False, ec=BORDER, lw=0.8,
         ls='-', tc='black', va='center', ha='center'):
    r = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02",
                       facecolor=fc, edgecolor=ec, linewidth=lw, linestyle=ls)
    ax.add_patch(r)
    wt = 'bold' if bold else 'normal'
    ax.text(x + w/2, y + h/2, text, fontsize=fs, fontweight=wt,
            ha=ha, va=va, color=tc)
    return r

def _arr(ax, x1, y1, x2, y2, c=A_MAIN, lw=1.0, ls='-', cs='arc3,rad=0', st='->'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=st, color=c, lw=lw,
                                linestyle=ls, connectionstyle=cs))

def _lbl(ax, x, y, text, fs=7, c='black', ha='center', va='center',
         style='normal', wt='normal', rot=0):
    ax.text(x, y, text, fontsize=fs, color=c, ha=ha, va=va,
            fontstyle=style, fontweight=wt, rotation=rot)


# ══════════════════════════════════════════════════════════════════════════
# FIGURE 1: System Architecture Overview (redesigned)
# ══════════════════════════════════════════════════════════════════════════
def draw_figure1():
    fig, ax = plt.subplots(1, 1, figsize=(15, 11))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 11)
    ax.axis('off')
    ax.set_aspect('equal')

    # Title
    _lbl(ax, 7.5, 10.7, 'Figure 1: System Architecture Overview', fs=13, wt='bold')
    _lbl(ax, 7.5, 10.35,
         'Three agent types × BrowserGym bridge × three-layer variant injection',
         fs=8, c='#555')

    # ════════════════════════════════════════════════════════════════
    # LEFT COLUMN: Agents + LLM Backend
    # ════════════════════════════════════════════════════════════════
    _lbl(ax, 1.6, 9.8, 'AI Agents', fs=10, wt='bold')

    _box(ax, 0.3, 8.8, 2.6, 0.7,
         'Text-Only Agent\nObserves: AXTree text (role+name+bid)',
         C_TEXT, fs=7, bold=True)
    _box(ax, 0.3, 7.8, 2.6, 0.7,
         'SoM Vision Agent\nObserves: Screenshot + bid overlays',
         C_SOM, fs=7, bold=True)
    _box(ax, 0.3, 6.8, 2.6, 0.7,
         'CUA Agent (computer_use)\nObserves: Raw screenshot only',
         C_CUA, fs=7, bold=True)

    # LLM Backend
    _box(ax, 0.3, 5.6, 2.6, 0.8,
         'LLM Backend\nClaude Sonnet 3.5\n(AWS Bedrock)',
         '#EBF5FB', fs=7, bold=True)
    _lbl(ax, 1.6, 5.25, 'Text/SoM: LiteLLM proxy → Bedrock', fs=5.5, c=A_TEXT)
    _lbl(ax, 1.6, 5.05, 'CUA: boto3 → Bedrock Converse API', fs=5.5, c=A_CUA)

    # Arrows: agents → LLM
    for y in [8.8, 7.8, 6.8]:
        _arr(ax, 1.6, y, 1.6, 5.6+0.8, c='#888', lw=0.6, ls=':')

    # ════════════════════════════════════════════════════════════════
    # MIDDLE COLUMN: BrowserGym + Executor
    # ════════════════════════════════════════════════════════════════
    # Outer BrowserGym box
    bgym = FancyBboxPatch((3.5, 5.0), 4.8, 5.0, boxstyle="round,pad=0.06",
                          facecolor=C_BGYM, edgecolor=BORDER, linewidth=1.3)
    ax.add_patch(bgym)
    _lbl(ax, 5.9, 9.8, 'BrowserGym Layer', fs=10, wt='bold')
    _lbl(ax, 5.9, 9.5, 'browsergym_bridge.py (Python subprocess)', fs=6.5, c='#666')

    # Observation
    _box(ax, 3.7, 8.4, 4.4, 0.9,
         'Observation Generation\n'
         '├─ AXTree: CDP getFullAXTree → flatten_axtree_to_str()\n'
         '├─ SoM: DOM traversal → bid labels → PIL overlay on screenshot\n'
         '└─ Screenshot: page.screenshot() → base64 PNG',
         '#EBF5FB', fs=6.5)

    # Action
    _box(ax, 3.7, 7.3, 4.4, 0.7,
         'Action Execution\n'
         '├─ bid-based: click("bid") → DOM element lookup → .click()\n'
         '└─ coord-based (CUA): page.mouse.click(x/scale, y/scale)',
         '#EBF5FB', fs=6.5)

    # bid system
    _box(ax, 3.7, 6.5, 4.4, 0.5,
         'bid Mapping: browsergym_set_of_marks attr ↔ AXTree nodeId',
         '#EBF5FB', fs=6.5)

    # JSON protocol
    _box(ax, 3.7, 5.7, 4.4, 0.5,
         'JSON-line Protocol: executor.ts ↔ bridge.py (stdin/stdout)',
         '#EBF5FB', fs=6.5)

    # Executor (below BrowserGym)
    _box(ax, 3.5, 4.2, 4.8, 0.5,
         'executor.ts — Step loop · LLM dispatch · Reward evaluation · Wall-clock timeout',
         C_HIGHLIGHT, fs=7, bold=True)

    # Arrows: Text/SoM → BrowserGym
    _arr(ax, 2.9, 9.15, 3.7, 8.9, c=A_TEXT, lw=1.5)
    _lbl(ax, 3.3, 9.25, 'AXTree', fs=5.5, c=A_TEXT)
    _arr(ax, 2.9, 8.15, 3.7, 8.15, c=A_SOM, lw=1.5)
    _lbl(ax, 3.3, 8.3, 'SoM img', fs=5.5, c=A_SOM)

    # Arrow: CUA bypasses BrowserGym
    _arr(ax, 2.9, 7.15, 9.0, 8.5, c=A_CUA, lw=2.0, ls='--', cs='arc3,rad=-0.2')
    _lbl(ax, 6.0, 6.15, 'CUA bypasses BrowserGym →\ndirect Playwright page access',
         fs=6.5, c=A_CUA, wt='bold')

    # ════════════════════════════════════════════════════════════════
    # RIGHT COLUMN: Browser + WebArena
    # ════════════════════════════════════════════════════════════════
    br = FancyBboxPatch((9.0, 4.2), 5.5, 5.8, boxstyle="round,pad=0.06",
                        facecolor=C_BROWSER, edgecolor=BORDER, linewidth=1.3)
    ax.add_patch(br)
    _lbl(ax, 11.75, 9.8, 'Browser + WebArena', fs=10, wt='bold')

    # Playwright
    _box(ax, 9.2, 9.0, 5.1, 0.5,
         'Playwright (browser automation — controls Chromium)',
         '#FDFEFE', fs=7.5, bold=True)

    # Chrome
    _box(ax, 9.2, 7.8, 5.1, 0.9,
         'Chromium\n'
         '├─ Blink AX Tree (internal a11y representation)\n'
         '├─ CDP Accessibility.getFullAXTree ← source of ALL a11y data\n'
         '└─ DOM (live document)',
         '#FDFEFE', fs=6.5)

    # Three-layer injection box
    inj = FancyBboxPatch((9.2, 5.3), 5.1, 2.2, boxstyle="round,pad=0.04",
                         facecolor=C_PLAND, edgecolor='#C0392B', linewidth=1.5)
    ax.add_patch(inj)
    _lbl(ax, 11.75, 7.35, 'Three-Layer Variant Injection', fs=8, wt='bold', c='#922B21')

    _box(ax, 9.4, 6.8, 4.7, 0.4,
         'Layer 1: page.evaluate(variant_js) — initial DOM injection after env.reset()',
         '#FADBD8', fs=6, bold=True)
    _box(ax, 9.4, 6.2, 4.7, 0.4,
         'Layer 2: page.on("load") — re-inject on same-page navigation events',
         '#FADBD8', fs=6, bold=True)
    _box(ax, 9.4, 5.5, 4.7, 0.5,
         'Layer 3 (Plan D): context.route("**/*") — network-level HTML\n'
         'interception + deferred script (load+500ms) + MutationObserver guard',
         '#F1948A', fs=6, bold=True)

    # WebArena
    _box(ax, 9.2, 4.3, 5.1, 0.7,
         'WebArena: Magento (:7770 storefront, :7780 admin) · Postmill (:9999) · GitLab (:8023)',
         C_WEBARENA, fs=7, bold=True)

    # Arrows: BrowserGym ↔ Browser
    _arr(ax, 8.3, 8.8, 9.2, 8.8, c=A_MAIN, lw=1.2)
    _arr(ax, 9.2, 8.4, 8.3, 8.4, c=A_MAIN, lw=1.2)
    _lbl(ax, 8.75, 9.0, 'CDP', fs=6, wt='bold')
    _lbl(ax, 8.75, 8.25, 'actions', fs=6)

    # Arrows: internal browser
    _arr(ax, 11.75, 7.8, 11.75, 7.35+0.15, c=A_MAIN, lw=0.8)
    _arr(ax, 11.75, 5.3, 11.75, 4.3+0.7, c=A_MAIN, lw=0.8)
    _lbl(ax, 12.3, 5.1, 'patches modify\nDOM before\nChrome builds\nAX Tree', fs=5.5, c='#922B21')

    # ════════════════════════════════════════════════════════════════
    # BOTTOM: Variant scripts summary
    # ════════════════════════════════════════════════════════════════
    _lbl(ax, 7.5, 3.7, 'Variant Patch Scripts (injected by all 3 layers)', fs=9, wt='bold')

    _box(ax, 0.3, 2.4, 3.5, 1.1,
         'apply-low.js (13 patches)\n'
         '• Semantic: rm ARIA, roles, alt, lang\n'
         '• Structure: h1-h6→div, nav→div\n'
         '• Cross-layer: rm labels, thead→div\n'
         '• Functional: a→span ⚠, Shadow DOM',
         C_LOW, fs=6.5, bold=True)

    _box(ax, 4.1, 2.4, 3.5, 1.1,
         'apply-medium-low.js\n'
         '(pseudo-compliance)\n'
         '• Empty button→div (keeps role)\n'
         '• Strip keyboard handlers\n'
         '• Remove labels for inputs\n'
         '  ARIA present, handlers missing',
         C_MEDLOW, fs=6.5, bold=True)

    _box(ax, 7.9, 2.4, 3.5, 1.1,
         'base (no patches)\n\n'
         '• Original WebArena DOM\n'
         '• No injection applied\n'
         '• Control condition',
         C_BASE, fs=6.5, bold=True)

    _box(ax, 11.7, 2.4, 3.0, 1.1,
         'apply-high.js\n'
         '• Add aria-label to unnamed\n'
         '• Skip-nav link, landmarks\n'
         '• Form labels, img alt\n'
         '• Table scope, aria-current',
         C_HIGH, fs=6.5, bold=True)

    # Arrows from variant boxes up to injection layer
    for bx in [2.05, 5.85, 9.65, 13.2]:
        _arr(ax, bx, 3.5, 11.75, 5.3, c='#922B21', lw=0.5, ls=':', cs='arc3,rad=0')

    # ════════════════════════════════════════════════════════════════
    # BOTTOM: Key annotations
    # ════════════════════════════════════════════════════════════════
    _box(ax, 0.3, 0.8, 14.4, 1.3,
         'Key Design Points\n\n'
         '• Text-Only & SoM agents go through BrowserGym (JSON-line protocol); '
         'CUA bypasses BrowserGym entirely (direct Playwright + Bedrock Converse API)\n'
         '• Plan D (Layer 3) is the primary persistence mechanism — catches ALL HTML responses '
         'including agent-triggered goto() navigations\n'
         '• Layers 1 & 2 are fallbacks for initial injection and same-page JS re-rendering '
         '(Magento KnockoutJS)\n'
         '• Variant patches modify DOM BEFORE Chrome builds the Blink AX Tree → '
         'agent sees degraded/enhanced a11y tree\n'
         '• CDP Accessibility.getFullAXTree (Experimental) is the single source of truth '
         'for all a11y tree data',
         '#EBF5FB', fs=6.5)

    # Legend
    legend_elements = [
        Line2D([0], [0], color=A_TEXT, lw=2, label='Text-Only Agent'),
        Line2D([0], [0], color=A_SOM, lw=2, label='SoM Vision Agent'),
        Line2D([0], [0], color=A_CUA, lw=2, ls='--', label='CUA Agent (bypasses BrowserGym)'),
        Line2D([0], [0], color='#922B21', lw=1.5, ls=':', label='Variant injection path'),
    ]
    ax.legend(handles=legend_elements, loc='upper left', fontsize=6.5,
              framealpha=0.9, edgecolor='#999', bbox_to_anchor=(0.0, 0.55))

    fig.tight_layout(pad=0.3)
    fig.savefig('figures/figure1_system_architecture.png', dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    print('✓ Figure 1 saved')


# ══════════════════════════════════════════════════════════════════════════
# FIGURE 2: A11y Tree Processing Pipeline (kept from before, minor tweaks)
# ══════════════════════════════════════════════════════════════════════════
def draw_figure2():
    fig, ax = plt.subplots(1, 1, figsize=(14, 11))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 11)
    ax.axis('off')
    ax.set_aspect('equal')

    _lbl(ax, 7, 10.7, 'Figure 2: Accessibility Tree Processing Pipeline', fs=12, wt='bold')
    _lbl(ax, 7, 10.4, 'From Chrome Blink internals to agent observation, with screen reader comparison',
         fs=8, c='#555')

    # ── MAIN PIPELINE (left, x=1..7) ──
    cx, cw = 1.5, 5.0

    _box(ax, cx, 9.4, cw, 0.7,
         'Stage 1: Chrome Blink AX Tree (Internal)\n'
         'Chromium builds accessibility representation from DOM + CSS + ARIA',
         '#D6EAF8', fs=7.5, bold=True)

    _arr(ax, cx+cw/2, 9.4, cx+cw/2, 9.0, c=A_MAIN, lw=1.5)
    _lbl(ax, cx+cw/2+0.1, 9.15, 'CDP Accessibility.getFullAXTree (Experimental)',
         fs=6.5, c='#2471A3', wt='bold', ha='left')

    _box(ax, cx, 8.0, cw, 0.7,
         'Stage 2: CDP Raw AXTree JSON\n'
         'Nodes: nodeId, role, name, properties, childIds, backendDOMNodeId',
         '#D5F5E3', fs=7.5, bold=True)

    _arr(ax, cx+cw/2, 8.0, cx+cw/2, 7.6, c=A_MAIN, lw=1.5)
    _lbl(ax, cx+cw/2+0.1, 7.75, 'BrowserGym processing',
         fs=6.5, c='#1E8449', wt='bold', ha='left')

    _box(ax, cx, 5.2, cw, 2.2,
         'Stage 3: BrowserGym Processing\n\n'
         '1. Assign bid (browsergym_set_of_marks attr → DOM)\n'
         '2. Filter/Retain strategy:\n'
         '   ├─ aria-hidden="true" → hidden=True BUT keeps bid & role ⚠️\n'
         '   ├─ role="presentation" → may be IGNORED on headings ⚠️\n'
         '   ├─ display:none → filtered out ✓\n'
         '   └─ Normal elements → preserve role + name + bid\n'
         '3. Serialize: flatten_axtree_to_str() → text\n'
         '4. SoM overlay: bid numbers drawn on screenshot (PIL)',
         C_BGYM, fs=6.5)

    _box(ax, cx+0.1, 5.3, 2.2, 0.35,
         '⚠️ PSL Divergence Point',
         C_WARNING, fs=6.5, bold=True, ls='--', ec='#C0392B')

    _box(ax, cx+cw+0.3, 5.8, 2.8, 0.6,
         'SRF Filter (proposed)\n'
         'Insert between Stage 3 & 4:\n'
         'Remove hidden=True nodes',
         '#FADBD8', fs=6.5, bold=True, ls='--', ec='#C0392B')
    _arr(ax, cx+cw, 6.1, cx+cw+0.3, 6.1, c='#C0392B', lw=1.0, ls='--')

    _arr(ax, cx+cw/2, 5.2, cx+cw/2, 4.8, c=A_MAIN, lw=1.5)

    _box(ax, cx, 3.6, cw, 1.0,
         'Stage 4: Agent Observation\n\n'
         '├─ Text-Only: serialized AXTree text (role + name + bid per line)\n'
         '├─ SoM Vision: screenshot with bid number overlays\n'
         '└─ CUA: raw screenshot only (skips Stages 2–3 entirely)',
         C_HIGHLIGHT, fs=7, bold=True)

    _arr(ax, cx+cw/2+2.5, 9.4, cx+cw/2+2.5, 3.6+1.0,
         c=A_CUA, lw=2.0, ls='--')
    _lbl(ax, cx+cw/2+2.7, 7.0, 'CUA bypasses\nStages 2–3\n(zero DOM\ndependency)',
         fs=7, c=A_CUA, wt='bold', ha='left')

    # ── SCREEN READER PATH (right) ──
    sx, sw = 8.5, 4.5
    _lbl(ax, sx+sw/2, 9.9, 'Real Screen Reader Path', fs=9, wt='bold')

    _arr(ax, cx+cw, 9.75, sx, 9.75, c=C_GRAY, lw=1.0, ls=':')
    _lbl(ax, 7.3, 9.85, 'same source', fs=6, c='#888')

    _box(ax, sx, 8.8, sw, 0.7,
         'OS Platform Accessibility API\n'
         'UIA (Windows) / ATK (Linux) / AXCocoa (macOS)',
         C_GRAY, fs=7.5, bold=True)

    _arr(ax, sx+sw/2, 8.8, sx+sw/2, 8.4, c='#666', lw=1.0)

    _box(ax, sx, 6.8, sw, 1.4,
         'Screen Reader Processing\n\n'
         '├─ JAWS: proprietary patches + virtual document\n'
         '│   → aria-hidden="true" = COMPLETELY HIDDEN ✓\n'
         '├─ NVDA: virtual buffer + single-key navigation\n'
         '│   → role="presentation" = ROLE REMOVED ✓\n'
         '└─ VoiceOver: macOS AX API translation\n'
         '    → display:none = HIDDEN ✓',
         C_GRAY, fs=6.5)

    _box(ax, sx, 5.6, sw, 0.9,
         'KEY DIVERGENCE (PSL finding)\n\n'
         'BrowserGym: aria-hidden → hidden=True, keeps bid ✗\n'
         'Screen Reader: aria-hidden → element GONE entirely ✓\n'
         'Impact: PSL variant 5/6 success (should be ~0%)',
         C_WARNING, fs=6.5, bold=True, ec='#C0392B', lw=1.5)

    _arr(ax, sx, 6.0, cx+cw+0.1, 5.5, c='#C0392B', lw=1.5, ls='--', cs='arc3,rad=0.2')

    _box(ax, 1.0, 2.2, 12.0, 1.0,
         'Token Flow Impact (Pilot 4)\n\n'
         'Low: avg 172K tokens/task (inflated by non-semantic DOM exploration)  │  '
         'Base: avg 135K tokens/task  │  Extreme: 608K → context overflow\n'
         'Semantic Density = interactive_nodes / total_a11y_tree_tokens — '
         'quantifies signal-to-noise ratio in agent observation',
         '#EBF5FB', fs=7)

    ax.text(7, 1.7,
            '⚠️ marks BrowserGym vs screen reader divergence. '
            'Red dashed = PSL findings. SRF = Screen-Reader-Faithful proposed filter.',
            fontsize=6.5, ha='center', color='#555', fontstyle='italic')

    fig.tight_layout(pad=0.5)
    fig.savefig('figures/figure2_axtree_pipeline.png', dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    print('✓ Figure 2 saved')


# ══════════════════════════════════════════════════════════════════════════
# FIGURE 3: Variant Injection Detail (redesigned)
# ══════════════════════════════════════════════════════════════════════════
def draw_figure3():
    fig, ax = plt.subplots(1, 1, figsize=(15, 14))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 14)
    ax.axis('off')
    ax.set_aspect('equal')

    _lbl(ax, 7.5, 13.7, 'Figure 3: Variant Patch Detail — What Each Level Injects and Where',
         fs=13, wt='bold')
    _lbl(ax, 7.5, 13.35,
         'Each variant applies a different set of DOM mutations via shared JS scripts',
         fs=8, c='#555')

    # ════════════════════════════════════════════════════════════════
    # TOP: Three-layer injection mechanism
    # ════════════════════════════════════════════════════════════════
    _lbl(ax, 7.5, 12.9, 'Injection Mechanism (3 layers, all use the same variant JS)',
         fs=9, wt='bold')

    _box(ax, 0.5, 12.0, 4.5, 0.6,
         'Layer 1: page.evaluate(js)\n'
         'One-shot DOM injection after env.reset()',
         '#FADBD8', fs=7, bold=True)

    _box(ax, 5.3, 12.0, 4.5, 0.6,
         'Layer 2: page.on("load", re-inject)\n'
         'Re-apply on same-page navigation events',
         '#FADBD8', fs=7, bold=True)

    _box(ax, 10.1, 12.0, 4.5, 0.6,
         'Layer 3 (Plan D): context.route("**/*")\n'
         'Network HTML intercept + deferred + MutationObserver',
         '#F1948A', fs=7, bold=True)

    # Arrows showing evolution
    _arr(ax, 5.0, 12.3, 5.3, 12.3, c='#888', lw=0.8)
    _arr(ax, 9.8, 12.3, 10.1, 12.3, c='#888', lw=0.8)
    _lbl(ax, 5.15, 12.55, 'fallback', fs=5.5, c='#888')
    _lbl(ax, 9.95, 12.55, 'primary', fs=5.5, c='#888')

    # Divider
    ax.plot([0.3, 14.7], [11.6, 11.6], color='#999', linewidth=0.5, linestyle='--')

    # ════════════════════════════════════════════════════════════════
    # FOUR VARIANT COLUMNS
    # ════════════════════════════════════════════════════════════════
    _lbl(ax, 7.5, 11.35, 'Variant Patch Details', fs=10, wt='bold')

    # Column positions
    vx = [0.3, 3.8, 7.5, 11.2]
    vw = 3.2

    # ── LOW ──
    _box(ax, vx[0], 10.4, vw, 0.6,
         'LOW (apply-low.js)\n13 patch operations',
         C_LOW, fs=8, bold=True, ec='#922B21', lw=1.5)

    # Low: what it targets
    _lbl(ax, vx[0]+vw/2, 10.1, 'Injection targets:', fs=7, wt='bold')

    _box(ax, vx[0], 9.0, vw, 0.9,
         'SEMANTIC (pure a11y)\n'
         '① Remove ALL aria-* & role attrs\n'
         '② Remove alt, title from <img>\n'
         '③ Remove lang from <html>\n'
         '④ Remove tabindex attrs\n'
         '⑤ Replace h1-h6 → styled <div>',
         '#FBEEE6', fs=6, bold=True)
    _lbl(ax, vx[0]+vw-0.1, 9.85, 'DOM attrs', fs=5.5, c='#888', ha='right')

    _box(ax, vx[0], 7.8, vw, 0.9,
         'STRUCTURAL\n'
         '⑥ nav/main/header/footer → <div>\n'
         '⑦ thead/tbody/th → <div>/<td>\n'
         '⑧ Remove <label> elements\n'
         '⑨ Duplicate IDs (F77)',
         '#FBEEE6', fs=6, bold=True)
    _lbl(ax, vx[0]+vw-0.1, 8.65, 'DOM structure', fs=5.5, c='#888', ha='right')

    _box(ax, vx[0], 6.6, vw, 0.9,
         'FUNCTIONAL ⚠️\n'
         '(10) <a href> → <span onclick>\n'
         '     (deletes href = breaks navigation)\n'
         '(11) Closed Shadow DOM wrapping\n'
         '(12) onfocus="this.blur()" (F55)\n'
         '(13) Remove keyboard handlers',
         C_WARNING, fs=6, bold=True, ec='#C0392B')
    _lbl(ax, vx[0]+vw-0.1, 7.45, 'JS behavior', fs=5.5, c='#C0392B', ha='right')

    # Ma11y mapping
    _box(ax, vx[0], 5.9, vw, 0.5,
         'Ma11y operators: F2, F42, F44, F55,\n'
         'F65, F68, F77, F91, F96 + E1-E4 novel',
         '#F2F3F4', fs=5.5)

    # ── MEDIUM-LOW ──
    _box(ax, vx[1], 10.4, vw, 0.6,
         'MEDIUM-LOW\n(apply-medium-low.js)',
         C_MEDLOW, fs=8, bold=True, ec='#B7950B', lw=1.5)

    _lbl(ax, vx[1]+vw/2, 10.1, 'Injection targets:', fs=7, wt='bold')

    _box(ax, vx[1], 8.8, vw, 1.1,
         'PSEUDO-COMPLIANCE\n'
         '(ARIA present, behavior missing)\n\n'
         '① Empty <button> → <div>\n'
         '   (visual same, no button semantics)\n'
         '② role="button" elements:\n'
         '   clone-replace to strip keyboard\n'
         '   event listeners (keeps role attr)',
         '#FEF9E7', fs=6, bold=True)
    _lbl(ax, vx[1]+vw-0.1, 9.85, 'DOM + JS', fs=5.5, c='#888', ha='right')

    _box(ax, vx[1], 7.5, vw, 1.0,
         'FORM DEGRADATION\n\n'
         '③ Remove <label> for inputs\n'
         '   that lack placeholder attr\n'
         '④ Remove aria-label and\n'
         '   aria-labelledby from those inputs',
         '#FEF9E7', fs=6, bold=True)
    _lbl(ax, vx[1]+vw-0.1, 8.45, 'DOM attrs', fs=5.5, c='#888', ha='right')

    _box(ax, vx[1], 6.6, vw, 0.6,
         'Design intent: models real-world\n'
         '"looks accessible but isn\'t" pattern\n'
         '(ARIA present, handlers missing)',
         '#F2F3F4', fs=5.5)

    # ── BASE ──
    _box(ax, vx[2], 10.4, vw, 0.6,
         'BASE (no patches)\nOriginal WebArena DOM',
         C_BASE, fs=8, bold=True, ec='#1E8449', lw=1.5)

    _lbl(ax, vx[2]+vw/2, 10.1, 'Control condition:', fs=7, wt='bold')

    _box(ax, vx[2], 8.4, vw, 1.5,
         'NO INJECTION\n\n'
         '• Original Magento / Postmill HTML\n'
         '• Whatever a11y the site ships with\n'
         '• Serves as the baseline for\n'
         '  statistical comparison\n\n'
         'WebAIM Million 2025:\n'
         '94.8% of top 1M sites fail WCAG\n'
         '→ "base" is already imperfect',
         '#E8F8F5', fs=6.5, bold=True)

    _box(ax, vx[2], 7.2, vw, 0.9,
         'Pilot 4 base results:\n'
         'Text-only: 86.7% success\n'
         'SoM: 20.0% success\n'
         'CUA: 96.7% success',
         '#D5F5E3', fs=6.5)

    # ── HIGH ──
    _box(ax, vx[3], 10.4, vw, 0.6,
         'HIGH (apply-high.js)\nEnhance accessibility',
         C_HIGH, fs=8, bold=True, ec='#2471A3', lw=1.5)

    _lbl(ax, vx[3]+vw/2, 10.1, 'Injection targets:', fs=7, wt='bold')

    _box(ax, vx[3], 8.8, vw, 1.1,
         'ARIA ENHANCEMENT\n\n'
         '① aria-label on unnamed interactive\n'
         '② Skip-navigation link (appended\n'
         '   at body END to avoid bid shift)\n'
         '③ Landmark roles: banner, nav,\n'
         '   main, contentinfo, complementary',
         '#D6EAF8', fs=6, bold=True)
    _lbl(ax, vx[3]+vw-0.1, 9.85, 'DOM attrs', fs=5.5, c='#888', ha='right')

    _box(ax, vx[3], 7.5, vw, 1.0,
         'FORM & CONTENT\n\n'
         '④ <label> for unlabeled controls\n'
         '⑤ alt text for images without alt\n'
         '⑥ lang="en" on <html>\n'
         '⑦ aria-required on required inputs\n'
         '⑧ aria-current="page" on nav links',
         '#D6EAF8', fs=6, bold=True)
    _lbl(ax, vx[3]+vw-0.1, 8.45, 'DOM attrs', fs=5.5, c='#888', ha='right')

    _box(ax, vx[3], 6.6, vw, 0.6,
         'TABLE ENHANCEMENT\n'
         '⑨ scope="col"/"row" on <th>\n'
         '⑩ Discernible text on empty links',
         '#D6EAF8', fs=6, bold=True)

    # ════════════════════════════════════════════════════════════════
    # BOTTOM: Impact matrix
    # ════════════════════════════════════════════════════════════════
    ax.plot([0.3, 14.7], [5.5, 5.5], color='#999', linewidth=0.5, linestyle='--')
    _lbl(ax, 7.5, 5.25, 'Agent Impact Matrix (Pilot 4 results, N=240)', fs=9, wt='bold')

    # Table
    hdrs = ['', 'LOW', 'MEDIUM-LOW', 'BASE', 'HIGH']
    hx = [0.3, 2.8, 5.6, 8.4, 11.2]
    hw = [2.2, 2.5, 2.5, 2.5, 2.5]
    for i, (h, x, w) in enumerate(zip(hdrs, hx, hw)):
        _box(ax, x, 4.7, w, 0.35, h, '#D5D8DC', fs=7, bold=True)

    rows = [
        ('Text-Only\n(a11y tree)', '23.3% ✗', '100% ✓', '86.7% ✓', '76.7% ✓'),
        ('SoM Vision\n(screenshot+bid)', '0.0% ✗✗', '23.3%', '20.0%', '30.0%'),
        ('CUA\n(raw screenshot)', '66.7%', '100% ✓', '96.7% ✓', '100% ✓'),
    ]
    row_cs = [C_TEXT, C_SOM, C_CUA]
    for ri, (r0, r1, r2, r3, r4) in enumerate(rows):
        ry = 4.0 - ri * 0.55
        _box(ax, hx[0], ry, hw[0], 0.45, r0, row_cs[ri], fs=6.5, bold=True)
        _box(ax, hx[1], ry, hw[1], 0.45, r1, C_LOW if '✗' in r1 else '#F2F3F4', fs=6.5)
        _box(ax, hx[2], ry, hw[2], 0.45, r2, '#F2F3F4', fs=6.5)
        _box(ax, hx[3], ry, hw[3], 0.45, r3, '#F2F3F4', fs=6.5)
        _box(ax, hx[4], ry, hw[4], 0.45, r4, '#F2F3F4', fs=6.5)

    # ════════════════════════════════════════════════════════════════
    # BOTTOM: Patch classification & causal decomposition
    # ════════════════════════════════════════════════════════════════
    _lbl(ax, 7.5, 2.55, 'Low Variant Patch Classification (CUA causal decomposition)',
         fs=9, wt='bold')

    _box(ax, 0.3, 1.5, 4.5, 0.8,
         'Pure Semantic (~6 patches)\n'
         'alt, aria-label, lang, tabindex,\n'
         'heading roles, ARIA attrs\n'
         '→ Affects Text-Only only',
         '#EBF5FB', fs=6.5, bold=True)

    _box(ax, 5.2, 1.5, 4.5, 0.8,
         'Cross-Layer (~3 patches)\n'
         'label removal, thead→div\n'
         '→ Affects Text-Only + partial CUA\n'
         '  (visual layout may shift)',
         '#FEF9E7', fs=6.5, bold=True)

    _box(ax, 10.1, 1.5, 4.5, 0.8,
         'Functional Breakage (~4 patches)\n'
         '<a>→<span> (deletes href), Shadow DOM\n'
         '→ Affects ALL agents\n'
         '  CUA: 100% of low failures here',
         '#FADBD8', fs=6.5, bold=True, ec='#C0392B')

    # Causal decomposition
    _box(ax, 0.3, 0.4, 14.4, 0.8,
         'Causal Decomposition (Pilot 4): Text-only 63.3pp drop (base→low) ≈ '
         '33pp semantic (pure a11y tree degradation) + 30pp cross-layer functional breakage\n'
         'Evidence: CUA (zero DOM dependency) drops only 30pp at low → '
         'the remaining 33pp is purely semantic, invisible to vision agents\n'
         'Plan D verified: 33/33 goto traces show persistent degradation. '
         'ecom:23 low: 80% (Pilot 3b, goto escape) → 0% (Pilot 4, Plan D)',
         '#EBF5FB', fs=6.5, bold=True)

    fig.tight_layout(pad=0.3)
    fig.savefig('figures/figure3_variant_injection.png', dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    print('✓ Figure 3 saved')


# ══════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print('Generating architecture diagrams...')
    draw_figure1()
    draw_figure2()
    draw_figure3()
    print('\nAll 3 figures saved to figures/')
