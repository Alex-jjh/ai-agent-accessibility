# D.4 Figure Plan — AMT Paper Figures

**Date**: 2026-05-02
**Target**: 8 main figures + supplementary for CHI 2027 submission
**Tools**: matplotlib/seaborn (data-accurate) + GPT Image 2 (conceptual/architectural)

---

## Assessment of Existing Figures

### What exists (in `figures/`):
| File | Content | Status |
|------|---------|--------|
| `figure1_teaser.py` | Variant injection pipeline diagram | ⚠️ OUTDATED — uses old 3-layer (L1/L2/L3) framing, needs AMT 26-operator reframe |
| `figure2_main_results.png` | 2×3 bar chart (composite variants) | ✅ KEEP — shows Pilot 4 + expansion composite results |
| `figure3_severity_framework.png` | L1/L2/L3 severity infographic | ⚠️ OUTDATED — old severity framework, replaced by AMT taxonomy |
| `figure3_three_agent_arch.png` | Three-agent architecture | ✅ KEEP — still valid for §3 |
| `figure5_causal_decomposition.png` | Causal decomposition schematic | ✅ KEEP — still valid for §5 |
| `table2_per_task_heatmap.png` | Per-task success heatmap | ⚠️ OUTDATED — only shows composite variants, needs operator-level |

### Problems with existing figures:
1. **Old framing**: Figures 1 and 3 use the pre-AMT "L1/L2/L3 severity" framework. Paper is now AMT (26 operators, 3 families).
2. **Missing AMT-specific figures**: No DOM signature heatmap, no behavioral drop chart, no alignment matrix, no composition scatter.
3. **No cross-model comparison**: Existing figures don't show Claude vs Llama 4 per-operator.
4. **Composite-only**: Existing figures show composite variant results (Low/ML/Base/High). AMT paper needs individual operator results.

---

## New Figure Set (8 main + supplementary)

### Figure 1: AMT Framework Overview (CONCEPTUAL — GPT Image 2)
**Purpose**: Teaser/overview diagram showing the AMT taxonomy structure.
**Content**: 26 operators organized in 3 families (Low/Midlow/High), with arrows showing DOM injection → agent observation → behavioral measurement pipeline.
**Style**: Clean academic diagram, white background, minimal color.
**Tool**: GPT Image 2 (conceptual diagram, not data-driven).

### Figure 2: DOM Signature Heatmap (DATA — matplotlib)
**Purpose**: §4.X "Variant Authenticity Verification" — show each operator's objective DOM fingerprint.
**Content**: 26 rows (operators) × 8 key columns (D1, A1, A2, A3, V1, F1, F2, F3). Color-coded by magnitude. Operators sorted by behavioral drop.
**Style**: Seaborn heatmap, diverging colormap (blue-white-red), row labels with operator ID + short description.
**Tool**: matplotlib/seaborn (must be pixel-accurate).

### Figure 3: Behavioral Drop Bar Chart (DATA — matplotlib)
**Purpose**: §5.1 main results — per-operator behavioral impact.
**Content**: 26 operators sorted by Claude text-only drop. Bars colored by family (L=red, ML=orange, H=green). Llama 4 overlay as markers. H-baseline dashed line.
**Style**: Horizontal bar chart, error bars optional (only 39 cases per operator).
**Tool**: matplotlib (must be data-accurate).

### Figure 4: Signature Alignment Matrix (DATA + CONCEPTUAL — matplotlib)
**Purpose**: §5.2 core contribution — DOM category vs behavioral category cross-tabulation.
**Content**: 2×2 grid showing: ALIGNED (both active), ALIGNED (both null), MISALIGNED (DOM active/beh null), MISALIGNED (DOM minimal/beh active). Operators placed in each quadrant. Key examples highlighted (L1, L11, L5).
**Style**: Scatter plot with DOM magnitude on X-axis, behavioral drop on Y-axis. Quadrant labels. Key operators annotated.
**Tool**: matplotlib (data-driven scatter with annotations).

### Figure 5: Cross-Model Comparison (DATA — matplotlib)
**Purpose**: §5.3 — show Claude vs Llama 4 per-operator drops.
**Content**: Paired bar chart or connected dot plot. Top-10 operators by drop. Highlight L11 adaptive recovery gap (Claude +1.5pp vs Llama +14.6pp).
**Style**: Cleveland dot plot (connected dots, two colors).
**Tool**: matplotlib.

### Figure 6: Compositional Scatter (DATA — matplotlib)
**Purpose**: §5.4 — expected vs observed drop for 28 pairwise combinations.
**Content**: Scatter plot. X = expected (sum of individual drops), Y = observed (pair drop). Diagonal = perfect additivity. Points colored by interaction type (super/additive/sub). Key pairs labeled (L6+L11, L1+L5).
**Style**: Square aspect ratio, diagonal reference line, 3 colors.
**Tool**: matplotlib.

### Figure 7: Agent vs Human Comparison (DATA — matplotlib)
**Purpose**: §5.5 — integrate A11y-CUA human baseline.
**Content**: Bar chart comparing agent performance (our data) vs human performance (A11y-CUA BLVU/SU data) on overlapping task types.
**Style**: Grouped bars, human=gray, agents=colored.
**Tool**: matplotlib.

### Figure 8: Per-Task × Operator Heatmap (DATA — matplotlib)
**Purpose**: Supplementary — full 13×26 matrix showing task sensitivity.
**Content**: 13 task rows × 26 operator columns. Cell color = success rate (0-100%). Highlight task 67 (most sensitive) and task 132/188 (controls).
**Style**: Large heatmap, annotated cells with percentages.
**Tool**: matplotlib/seaborn.

---

## GPT Image 2 Prompts

### Prompt Strategy for Scientific Figures

Based on [OpenAI's official prompting guide](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide) (2026-04-21):

**Key principles for GPT Image 2 scientific diagrams:**
1. **Structure > length**: Use the 5-element formula: Subject → Style → Composition → Details → Constraints
2. **Explicit layout**: Specify exact positions ("top-left", "centered", "3 columns")
3. **Text rendering**: GPT Image 2 handles text well — include exact labels in the prompt
4. **Color specification**: Use hex codes or named colors for precision
5. **Aspect ratio**: Specify explicitly (e.g., "16:9 landscape", "3:2")
6. **Style anchoring**: Reference "academic paper figure", "Nature/Science journal style"
7. **Negative constraints**: "No decorative elements", "No gradients", "No 3D effects"

### Figure 1 Prompt (AMT Framework Overview)

```
Create a clean academic paper figure (landscape, 16:9 aspect ratio) showing the "Accessibility Manipulation Taxonomy (AMT)" framework.

Layout: Three horizontal sections stacked vertically.

TOP SECTION - "26 Operators (3 Families)":
- Three colored boxes side by side:
  - Left box (light red fill, red border): "Low Family (L1-L13)" with subtitle "13 degradation operators"
  - Middle box (light orange fill, orange border): "Midlow Family (ML1-ML3)" with subtitle "3 pseudo-compliance operators"  
  - Right box (light green fill, green border): "High Family (H1-H8)" with subtitle "8 enhancement operators"

MIDDLE SECTION - "Dual Signature Measurement":
- Two parallel measurement paths shown as rounded rectangles:
  - Left path: "DOM Signature (12 dimensions)" → lists "D1-D3 Structure | A1-A3 Semantics | V1-V3 Visual | F1-F3 Functional"
  - Right path: "Behavioral Signature (3 agents)" → lists "Text-only | SoM Vision | CUA Coordinate"
- Both paths have downward arrows converging to:

BOTTOM SECTION - "Signature Alignment Analysis":
- A 2×2 grid labeled:
  - Top-left: "✓ ALIGNED (both active)" 
  - Top-right: "✗ DOM active, Behavior null (Agent Adaptation)"
  - Bottom-left: "✗ DOM minimal, Behavior active (Structural Criticality)"
  - Bottom-right: "✓ ALIGNED (both null)"

Style: Clean, minimal, white background. Thin black borders. No shadows, no gradients, no 3D effects. Font: sans-serif, 10-12pt equivalent. Colors: muted academic palette (no saturated neon). Similar to figures in Nature or CHI conference papers.

Constraints: No decorative elements. No icons. Text must be perfectly legible. All text in English. No watermarks.
```

### Figure 4 Prompt (Signature Alignment Conceptual Overlay)

```
Create an academic scatter plot figure (square, 1:1 aspect ratio) for a research paper.

Title at top: "Signature Alignment: DOM Magnitude vs Behavioral Impact"

X-axis label: "DOM Change Magnitude (log scale)" ranging from 1 to 1000
Y-axis label: "Behavioral Drop (percentage points)" ranging from -10 to +45

Plot contains:
- A horizontal dashed line at y=5 labeled "detection threshold"
- A vertical dashed line at x=10 labeled "minimal DOM threshold"
- These lines divide the plot into 4 quadrants

Quadrant labels (in gray italic):
- Top-right: "ALIGNED (both active)" — 6 operators
- Bottom-right: "Agent Adaptation" — 11 operators  
- Top-left: "Structural Criticality" — 4 operators
- Bottom-left: "ALIGNED (both null)" — 5 operators

Key data points as colored circles:
- L1 (red, large): x=11, y=40, labeled "L1: Landmark→div"
- L5 (red, large): x=338, y=22, labeled "L5: Shadow DOM"
- L11 (blue, large): x=365, y=1.5, labeled "L11: Link→span"
- L12 (orange, medium): x=1, y=14, labeled "L12: Dup IDs"
- Several small gray dots scattered in bottom-right quadrant (the 11 "agent adaptation" operators)
- Several small gray dots in bottom-left quadrant (the 5 "both null" operators)

Style: Clean academic figure. White background. Thin axis lines. No grid. Sans-serif font. Muted colors. Similar to scatter plots in CHI or UIST papers.

Constraints: Data points must be at approximately correct positions. Labels must not overlap. No decorative elements.
```

---

## Python Script Plan

For data-accurate figures (2, 3, 5, 6, 7, 8), I'll write `figures/generate_amt_figures.py` that:
1. Reads `results/amt/dom_signature_matrix.csv`
2. Reads `results/amt/behavioral_signature_matrix.csv`
3. Reads `results/amt/signature_alignment.csv`
4. Reads C.2 composition data
5. Generates all 6 data-driven figures as 300dpi PNGs + vector PDFs

Style conventions (matching existing figures):
- Font: DejaVu Sans, 8pt base
- DPI: 300
- Colors: `C_LOW='#C0392B'`, `C_ML='#E67E22'`, `C_BASE='#2471A3'`, `C_HIGH='#27AE60'`
- Colorblind-safe: use viridis/RdBu diverging for heatmaps
- No chartjunk: minimal gridlines, no 3D, no shadows
- CHI column width: ~3.33" (single) or ~7" (double)

---

## Execution Order

1. **Figure 3** (behavioral drop bar chart) — simplest, most impactful, validates data pipeline
2. **Figure 2** (DOM heatmap) — straightforward seaborn heatmap
3. **Figure 4** (alignment scatter) — the paper's signature figure
4. **Figure 6** (composition scatter) — needs C.2 data integration
5. **Figure 5** (cross-model) — Cleveland dot plot
6. **Figure 8** (per-task heatmap) — large but mechanical
7. **Figure 7** (human comparison) — depends on A11y-CUA mapping quality
8. **Figure 1** (AMT overview) — GPT Image 2 or hand-drawn last

---

## Notes on GPT Image 2 for Scientific Figures

**What GPT Image 2 is good for:**
- Conceptual/architectural diagrams (Figure 1)
- Flow charts and process diagrams
- Schematic illustrations with text labels
- Clean infographic-style layouts

**What GPT Image 2 is NOT good for:**
- Data-accurate charts (bar heights, scatter positions must be exact)
- Heatmaps with specific numeric values
- Any figure where a reviewer could check if the data matches the text
- Figures that need to be regenerated when data changes

**Rule**: If the figure contains quantitative data that must be pixel-accurate, use matplotlib. If it's a conceptual diagram that communicates structure/process, GPT Image 2 is faster and often prettier.

**GPT Image 2 workflow for this paper:**
1. Generate with detailed prompt (include all text, positions, colors)
2. Download and inspect — check text accuracy, layout
3. Iterate 1-2 times with "keep everything but fix X" follow-ups
4. Final version: export at 2K resolution (2560×1440 or similar)
5. Convert to vector (SVG trace) if needed for camera-ready

---

## CHI 2027 Figure Requirements

- Format: PDF or high-res PNG (300+ DPI)
- Color: must be interpretable in grayscale (for print)
- Accessibility: alt-text required in camera-ready
- Size: single column (3.33") or double column (7")
- Font: minimum 7pt in final printed size
- Colorblind-safe: avoid red-green only distinctions (use shape + color)
