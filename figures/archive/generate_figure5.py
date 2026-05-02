#!/usr/bin/env python3
"""
Figure 5 (v2): Unified Layer Architecture — Shared base, branching at L2

Layout (bottom to top):
  L0+L1: shared full-width (Server + DOM + variant injection)
  L2: splits into two columns (Text/SoM use it, CUA skips)
  L3: splits into two columns (BrowserGym vs CUA direct)
       Left column further splits output: text vs SoM screenshot
  L4: three agent boxes at top

Like an inverted tree: shared root, branching upward.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8, 'figure.dpi': 300})

C_L0='#E8DAEF'; C_L1='#D5F5E3'; C_L2='#D6EAF8'; C_L3='#FEF9E7'
C_L4='#FADBD8'; C_BID='#F9E79F'; C_GRAY='#E5E7E9'; C_WARN='#F5B7B1'
C_INJ='#F9EBEA'; BORDER='#2C3E50'
AT='#2471A3'; AS='#1E8449'; AC='#C0392B'; AI='#922B21'

def _box(ax,x,y,w,h,text,fc,fs=7,bold=False,ec=BORDER,lw=0.7,ls='-',tc='black',al=1.0):
    r=FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.02",facecolor=fc,
                     edgecolor=ec,linewidth=lw,linestyle=ls,alpha=al)
    ax.add_patch(r)
    ax.text(x+w/2,y+h/2,text,fontsize=fs,fontweight='bold' if bold else 'normal',
            ha='center',va='center',color=tc)

def _arr(ax,x1,y1,x2,y2,c=BORDER,lw=1.0,ls='-',cs='arc3,rad=0',st='->'):
    ax.annotate('',xy=(x2,y2),xytext=(x1,y1),
                arrowprops=dict(arrowstyle=st,color=c,lw=lw,linestyle=ls,connectionstyle=cs))

def _lbl(ax,x,y,text,fs=6.5,c='black',ha='center',va='center',wt='normal',sty='normal'):
    ax.text(x,y,text,fontsize=fs,color=c,ha=ha,va=va,fontweight=wt,fontstyle=sty)


def draw():
    fig,ax=plt.subplots(1,1,figsize=(16,18))
    ax.set_xlim(0,16); ax.set_ylim(0,18); ax.axis('off'); ax.set_aspect('equal')

    # Title
    _lbl(ax,8,17.7,'Figure 5: Unified Layer Architecture',fs=14,wt='bold')
    _lbl(ax,8,17.3,'Shared DOM base, branching observation/action paths per agent type',fs=9,c='#555')

    # ════════════════════════════════════════════════════════════════
    # L0: Server (shared, full width) — bottom
    # ════════════════════════════════════════════════════════════════
    _box(ax, 1, 0.5, 14, 1.2,
         'L0: WebArena Server\n\n'
         'Magento storefront (:7770) / Magento admin (:7780) / Postmill (:9999) / GitLab (:8023)\n'
         'Returns original HTML via HTTP. We do NOT modify this layer.',
         C_L0, fs=7)
    _lbl(ax, 0.5, 1.1, 'L0', fs=9, wt='bold', ha='left')

    # ════════════════════════════════════════════════════════════════
    # L1: DOM (shared, full width) — variant injection target
    # ════════════════════════════════════════════════════════════════
    # Main DOM box
    _box(ax, 1, 2.2, 14, 2.8,
         '', C_L1, fs=7)
    _lbl(ax, 0.5, 3.6, 'L1', fs=9, wt='bold', ha='left')
    _lbl(ax, 8, 4.8, 'L1: DOM (Live Document Object Model) — THE ONLY LAYER WE MODIFY',
         fs=8, wt='bold')

    # Sub-boxes inside L1
    _box(ax, 1.3, 3.5, 4.5, 1.2,
         'DOM Elements & Attributes\n\n'
         '<nav>, <a href>, <button>, <h1>-<h6>\n'
         'aria-label, role, tabindex, alt, lang\n'
         'Event handlers: onclick, onkeydown',
         '#E8F8F5', fs=6)

    _box(ax, 6.0, 3.5, 4.0, 1.2,
         'bid Attribute (BrowserGym writes)\n\n'
         'browsergym_set_of_marks="42"\n'
         'Injected on each interactive element\n'
         'Born in L3, written back to L1',
         C_BID, fs=6, bold=True, ec='#B7950B')

    _box(ax, 10.2, 3.5, 4.5, 1.2,
         'Rendered Pixels\n\n'
         'CSS + DOM -> visual layout\n'
         'page.screenshot() captures as PNG\n'
         'CUA observes this directly',
         '#E8E8E8', fs=6)

    # Variant injection annotation (inside L1)
    _box(ax, 1.3, 2.4, 13.4, 0.8,
         'Variant Injection: apply-low.js / apply-medium-low.js / apply-high.js execute HERE via DOM APIs\n'
         'Three delivery mechanisms (page.evaluate, page.on("load"), Plan D context.route) — '
         'all just different ways to get the same JS to this layer.\n'
         'Plan D is the persistence mechanism: intercepts HTML at network level, injects <script> '
         'with deferred execution (load+500ms+MutationObserver), survives goto() navigations.',
         C_INJ, fs=5.5, bold=True, ec=AI, lw=1.2)

    # Arrow L0 -> L1
    _arr(ax, 8, 1.7, 8, 2.2, c='#888', lw=1.5)
    _lbl(ax, 8.5, 1.95, 'HTTP Response (HTML)', fs=5.5, c='#888')

    # ════════════════════════════════════════════════════════════════
    # BRANCH POINT: L1 splits into two paths
    # ════════════════════════════════════════════════════════════════
    _lbl(ax, 8, 5.3, 'Observation paths diverge here', fs=7, wt='bold', c='#555')

    # Left branch arrow (L1 -> L2, for Text-Only/SoM)
    _arr(ax, 5, 5.0, 5, 5.8, c=AT, lw=2.0)
    _lbl(ax, 4.2, 5.4, 'Chrome auto-derives\nAX Tree from DOM', fs=5.5, c=AT, ha='right')

    # Right branch arrow (L1 -> L4 CUA, skipping L2/L3)
    _arr(ax, 12, 5.0, 12, 14.0, c=AC, lw=2.5, ls='--')
    _lbl(ax, 12.5, 9.5, 'CUA: direct\nscreenshot\nfrom renderer\n(skips L2, L3\nentirely)', fs=7, c=AC, wt='bold', ha='left')

    # ════════════════════════════════════════════════════════════════
    # L2: Blink AX Tree (left column only — Text-Only/SoM)
    # ════════════════════════════════════════════════════════════════
    _box(ax, 1, 5.8, 8.5, 1.8,
         'L2: Blink AX Tree (Chrome Internal)\n\n'
         'Auto-derived from DOM + CSS + ARIA. We never directly modify this.\n'
         'Each node: role, name, properties, children\n'
         'bid appears as node property (from browsergym_set_of_marks DOM attr)\n'
         'If variant patch removes aria-label from DOM -> this node loses its name automatically',
         C_L2, fs=6.5)
    _lbl(ax, 0.5, 6.7, 'L2', fs=9, wt='bold', ha='left')

    # Grayed L2 for CUA side
    _box(ax, 10, 5.8, 5, 1.8,
         'L2: Blink AX Tree\n\n(exists but CUA never reads it)\n\nZero dependency on AX Tree',
         C_GRAY, fs=7, ec='#AAA', ls='--', al=0.5)
    _lbl(ax, 12.5, 6.2, 'SKIPPED by CUA', fs=8, c='#999', wt='bold')

    # Arrow L2 -> L3
    _arr(ax, 5, 7.6, 5, 8.3, c=AT, lw=2.0)
    _lbl(ax, 5.5, 7.95, 'CDP Accessibility.getFullAXTree', fs=5.5, c='#2471A3', wt='bold', ha='left')

    # ════════════════════════════════════════════════════════════════
    # L3: BrowserGym (left column — Text-Only/SoM share this)
    # ════════════════════════════════════════════════════════════════
    _box(ax, 1, 8.3, 8.5, 3.0,
         '', C_L3, fs=7)
    _lbl(ax, 0.5, 9.8, 'L3', fs=9, wt='bold', ha='left')
    _lbl(ax, 5.25, 11.1, 'L3: BrowserGym Processing (Text-Only & SoM share this layer)',
         fs=8, wt='bold')

    # Sub-boxes inside L3
    _box(ax, 1.3, 9.8, 3.8, 1.2,
         'AXTree Serialization\n\n'
         'flatten_axtree_to_str()\n'
         '[42] link "Home"\n'
         '[43] button "Submit"',
         '#FFF9E6', fs=6)

    _box(ax, 5.3, 9.8, 4.0, 1.2,
         'SoM Overlay Generation\n\n'
         'render_som_overlay():\n'
         'bid + bbox -> PIL draws red\n'
         'numbered labels on screenshot',
         '#FFF9E6', fs=6)

    _box(ax, 1.3, 8.5, 8.0, 1.0,
         'bid Mapping & Action Resolution\n'
         'Assigns bid to DOM elements (write-back to L1) | '
         'Resolves click("42") -> find DOM [browsergym_set_of_marks="42"] -> Playwright .click()\n'
         'send_msg_to_user("answer") -> BrowserGym evaluator -> reward (ground truth check)',
         C_BID, fs=5.5, bold=True, ec='#B7950B')

    # bid write-back arrow (L3 -> L1)
    _arr(ax, 3, 8.5, 3, 5.0, c='#B7950B', lw=1.5, ls='--')
    _lbl(ax, 2.3, 6.7, 'bid write-back\nto DOM (L1)', fs=5.5, c='#B7950B', ha='right', wt='bold')

    # Grayed L3 for CUA side
    _box(ax, 10, 8.3, 5, 3.0,
         'L3: BrowserGym\n\n(CUA uses only for setup)\n\n'
         'env.reset() + variant injection\n'
         'send_msg_to_user for reward eval\n\n'
         'NO observation extraction\n'
         'NO bid assignment\n'
         'NO AXTree serialization',
         C_GRAY, fs=6.5, ec='#AAA', ls='--', al=0.5)
    _lbl(ax, 12.5, 10.5, 'SKIPPED by CUA', fs=8, c='#999', wt='bold')

    # ════════════════════════════════════════════════════════════════
    # L3 -> L4: Output splits into Text vs SoM
    # ════════════════════════════════════════════════════════════════
    _lbl(ax, 5.25, 11.5, 'Same pipeline, different output encoding:', fs=6.5, c='#555')

    # Text-Only output arrow
    _arr(ax, 3.2, 11.0, 3.2, 14.0, c=AT, lw=2.0)
    _lbl(ax, 2.5, 12.5, 'AXTree text\n"[42] link Home"', fs=6, c=AT, wt='bold', ha='right')

    # SoM output arrow
    _arr(ax, 7.3, 11.0, 7.3, 14.0, c=AS, lw=2.0)
    _lbl(ax, 8.0, 12.5, 'Screenshot +\nbid overlay labels', fs=6, c=AS, wt='bold', ha='left')

    # ════════════════════════════════════════════════════════════════
    # L4: Three Agent boxes at top
    # ════════════════════════════════════════════════════════════════
    _lbl(ax, 8, 16.8, 'L4: Agent Observation & Action', fs=9, wt='bold')

    # Text-Only
    _box(ax, 0.8, 14.0, 4.0, 2.3,
         'Text-Only Agent\n'
         'Claude Sonnet 3.5\n'
         'LiteLLM -> Bedrock\n\n'
         'OBSERVES: AXTree text\n'
         '  [42] link "Home"\n'
         'ACTS: click("42")\n'
         '  -> L3 bid resolve -> L1\n\n'
         'Pilot 4 low: 23.3%',
         C_L4, fs=6.5, bold=True, ec=AT, lw=2)

    # SoM
    _box(ax, 5.3, 14.0, 4.0, 2.3,
         'SoM Vision Agent\n'
         'Claude Sonnet 3.5\n'
         'LiteLLM -> Bedrock\n\n'
         'OBSERVES: Screenshot + bid labels\n'
         '  (red "42" overlaid on elements)\n'
         'ACTS: click("42")\n'
         '  -> same bid resolve as Text-Only\n\n'
         'Pilot 4 low: 0.0% (phantom bid)',
         C_L4, fs=6.5, bold=True, ec=AS, lw=2)

    # CUA
    _box(ax, 10, 14.0, 5, 2.3,
         'CUA Agent (computer_use)\n'
         'Claude Sonnet 3.5\n'
         'boto3 -> Bedrock Converse API\n\n'
         'OBSERVES: Raw screenshot (no bid, no AXTree)\n'
         'ACTS: mouse.click(x, y), keyboard.type()\n'
         '  -> direct Playwright API -> L1\n'
         '  (no bid, no BrowserGym action resolution)\n\n'
         'Pilot 4 low: 66.7% (only functional patches affect)',
         C_L4, fs=6.5, bold=True, ec=AC, lw=2)

    # Action return arrows (dotted, going back down)
    # Text-Only action -> L3
    _arr(ax, 4.0, 14.0, 8.5, 9.0, c=AT, lw=1.0, ls=':')
    _lbl(ax, 6.5, 11.3, 'click("bid")', fs=5.5, c=AT, ha='center')

    # SoM action -> L3 (same path)
    _arr(ax, 8.5, 14.0, 8.5, 9.5, c=AS, lw=1.0, ls=':')

    # CUA action -> L1 direct
    _arr(ax, 14.0, 14.0, 14.0, 5.0, c=AC, lw=1.5, ls=':')
    _lbl(ax, 14.5, 9.5, 'mouse.click(x,y)\ndirect to DOM', fs=6, c=AC, ha='left', wt='bold')

    # ════════════════════════════════════════════════════════════════
    # Annotations
    # ════════════════════════════════════════════════════════════════

    # Phantom bid callout
    _box(ax, 5.5, 12.5, 3.6, 1.0,
         'PHANTOM BID\n'
         'Variant replaces DOM node\n'
         '-> bid attr deleted\n'
         '-> SoM label persists in screenshot\n'
         '-> click("229") fails 20+ times',
         C_WARN, fs=5.5, bold=True, ec='#C0392B', lw=1.2)

    # Key insight box at bottom
    _box(ax, 1, -0.8, 14, 1.0,
         'Key Insight: We only modify DOM (L1). AX Tree (L2) changes are automatic consequences, not direct operations.\n'
         'Text-Only/SoM share the same L1->L2->L3 pipeline; they differ only in L3 output encoding (text vs image+overlay).\n'
         'CUA skips L2+L3 entirely. Causal decomposition: Text-Only 63.3pp drop = ~33pp semantic (L2 path) + ~30pp functional (L1 behavior).',
         '#EBF5FB', fs=6.5, bold=True)

    # Legend
    legend_elements = [
        Line2D([0],[0],color=AT,lw=2,label='Text-Only path (L1->L2->L3->L4)'),
        Line2D([0],[0],color=AS,lw=2,label='SoM path (same as Text-Only, different L3 output)'),
        Line2D([0],[0],color=AC,lw=2,ls='--',label='CUA path (L1->L4 direct, skips L2+L3)'),
        Line2D([0],[0],color='#B7950B',lw=1.5,ls='--',label='bid lifecycle (L3->L1 write-back)'),
        Line2D([0],[0],color=AI,lw=1.5,label='Variant injection (all target L1 DOM)'),
    ]
    ax.legend(handles=legend_elements,loc='lower right',fontsize=6.5,
              framealpha=0.95,edgecolor='#999',bbox_to_anchor=(1.0,0.0))

    fig.tight_layout(pad=0.3)
    fig.savefig('figures/figure5_three_agent_layers.png',dpi=300,bbox_inches='tight',
                facecolor='white',edgecolor='none')
    plt.close(fig)
    print('Done: figures/figure5_three_agent_layers.png')

if __name__=='__main__':
    draw()
