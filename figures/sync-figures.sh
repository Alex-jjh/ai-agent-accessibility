#!/usr/bin/env bash
# sync-figures.sh — push DATA-figure deliverables from the code repo (source of
# truth) into the paper repo's figures/ (the self-contained submission window).
#
# This is the data-figure half of the figure pipeline. The schematic half lives
# in the paper repo: paper/figures/src/*.drawio + export.sh.
#
#   Data figures (here):     fig3, fig6, fig7, fig8, fig9, fig10
#     source = generate_fig*.py in THIS dir (read results/ CSVs; tied to V&V).
#     Regenerate first if data changed:
#         analysis/.venv/bin/python -m analysis.stage3_statistics   # fig7/fig10 CSVs
#         analysis/.venv/bin/python figures/generate_figN_*.py      # then each fig
#     Then run this script to copy the PDFs into the paper.
#
#   Schematic figures (NOT here): fig1, fig4, fig5, figA1
#     source = paper/figures/src/*.drawio ; render with that dir's export.sh.
#
#   fig2 (three-agent arch): legacy matplotlib, stable PNG already in the paper;
#     its generator is in archive/generate_figure3_simplified.py. Not synced.
#
# Usage:  ./sync-figures.sh           # copy all data-figure PDFs
#         ./sync-figures.sh --check   # report drift without copying
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PAPER_FIG="$(cd "$SRC_DIR/../../paper/figures" 2>/dev/null && pwd || true)"
if [ -z "$PAPER_FIG" ]; then
  echo "ERROR: paper/figures not found at ../../paper/figures relative to $SRC_DIR" >&2
  exit 1
fi

DATA_FIGS=(fig3_task_funnel fig6_token_violin fig7_behavioral_drop \
           fig8_alignment_scatter fig9_composition fig10_cross_model)

CHECK=0
[ "${1:-}" = "--check" ] && CHECK=1

echo "data-figure sync: $SRC_DIR -> $PAPER_FIG"
for b in "${DATA_FIGS[@]}"; do
  src="$SRC_DIR/$b.pdf"
  dst="$PAPER_FIG/$b.pdf"
  if [ ! -f "$src" ]; then
    echo "  WARN  $b.pdf missing in code repo (run its generator first)" >&2
    continue
  fi
  if [ "$CHECK" = "1" ]; then
    if [ ! -f "$dst" ] || ! cmp -s "$src" "$dst"; then
      echo "  DRIFT  $b.pdf differs (paper is stale)"
    else
      echo "  ok     $b.pdf in sync"
    fi
  else
    cp "$src" "$dst"
    echo "  copied $b.pdf"
  fi
done
[ "$CHECK" = "1" ] || echo "Done. (Schematic figs come from paper/figures/src/export.sh.)"
