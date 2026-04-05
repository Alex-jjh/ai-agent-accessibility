"""
Semantic Density Analysis — Novel metric for AI agent accessibility research.

Defines and computes "semantic density" of accessibility tree observations:

    semantic_density = interactive_node_count / total_a11y_tree_tokens

Rationale: Low-accessibility pages inflate the a11y tree with non-semantic
content (divs, spans without roles) while reducing interactive landmarks.
This metric quantifies the "signal-to-noise ratio" that agents face.

Reference context:
- Chung et al. (2025) found 150K token collapse threshold
- AgentOccam (2024) proposed pivotal node filtering
- Prune4Web (2025) proposed DOM element reduction
- Our metric formalizes the relationship between a11y quality and token efficiency

Usage:
    from analysis.semantic_density import compute_semantic_density, analyze_density_by_variant
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd


# Interactive roles that represent actionable elements in the a11y tree
INTERACTIVE_ROLES = frozenset({
    'link', 'button', 'textbox', 'checkbox', 'radio', 'combobox',
    'listbox', 'option', 'menuitem', 'menu', 'menubar', 'tab',
    'tabpanel', 'slider', 'spinbutton', 'searchbox', 'switch',
    'treeitem', 'gridcell', 'row', 'columnheader', 'rowheader',
})

# Landmark/structural roles that provide navigation context
LANDMARK_ROLES = frozenset({
    'banner', 'navigation', 'main', 'contentinfo', 'complementary',
    'form', 'search', 'region', 'heading',
})


@dataclass
class SemanticDensityResult:
    """Result of semantic density computation for a single observation."""
    interactive_nodes: int
    landmark_nodes: int
    total_nodes: int
    total_tokens: int
    semantic_density: float          # interactive_nodes / total_tokens
    landmark_density: float          # landmark_nodes / total_tokens
    combined_density: float          # (interactive + landmark) / total_tokens
    interactive_ratio: float         # interactive_nodes / total_nodes


def count_tokens(text: str) -> int:
    """Approximate token count using whitespace splitting.

    This is a rough approximation. For precise counts, use tiktoken.
    The a11y tree text format uses space-separated tokens, so whitespace
    splitting is a reasonable proxy.
    """
    if not text:
        return 0
    return len(text.split())


def count_nodes_by_role(axtree_text: str) -> tuple[int, int, int]:
    """Count interactive, landmark, and total nodes in an a11y tree text dump.

    The BrowserGym a11y tree format uses lines like:
        [42] link 'Home'
        [43] button 'Submit'
        [44] textbox 'Search...' required

    Returns (interactive_count, landmark_count, total_node_count).
    """
    if not axtree_text:
        return 0, 0, 0

    # Pattern: [id] role 'text' or [id] role text
    node_pattern = re.compile(r'^\s*\[(\d+)\]\s+(\w+)')

    interactive = 0
    landmark = 0
    total = 0

    for line in axtree_text.split('\n'):
        match = node_pattern.match(line)
        if match:
            total += 1
            role = match.group(2).lower()
            if role in INTERACTIVE_ROLES:
                interactive += 1
            if role in LANDMARK_ROLES:
                landmark += 1

    return interactive, landmark, total


def compute_semantic_density(axtree_text: str) -> SemanticDensityResult:
    """Compute semantic density for a single a11y tree observation.

    semantic_density = interactive_nodes / total_tokens

    A higher value means the agent sees more actionable elements per token
    of context consumed. Low-accessibility pages should have significantly
    lower semantic density.
    """
    tokens = count_tokens(axtree_text)
    interactive, landmark, total_nodes = count_nodes_by_role(axtree_text)

    return SemanticDensityResult(
        interactive_nodes=interactive,
        landmark_nodes=landmark,
        total_nodes=total_nodes,
        total_tokens=tokens,
        semantic_density=interactive / tokens if tokens > 0 else 0.0,
        landmark_density=landmark / tokens if tokens > 0 else 0.0,
        combined_density=(interactive + landmark) / tokens if tokens > 0 else 0.0,
        interactive_ratio=interactive / total_nodes if total_nodes > 0 else 0.0,
    )


def analyze_trace_file(trace_path: Path) -> Optional[dict]:
    """Analyze a single trace JSON file for semantic density.

    Expects trace files with structure:
        { steps: [{ observation: "...", ... }, ...], variant: "...", taskId: "..." }
    """
    try:
        data = json.loads(trace_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    steps = data.get('steps', [])
    if not steps:
        return None

    densities = []
    for step in steps:
        obs = step.get('observation', '')
        if obs and len(obs) > 10:  # skip empty/trivial observations
            result = compute_semantic_density(obs)
            densities.append(result)

    if not densities:
        return None

    avg_density = sum(d.semantic_density for d in densities) / len(densities)
    avg_combined = sum(d.combined_density for d in densities) / len(densities)
    avg_tokens = sum(d.total_tokens for d in densities) / len(densities)
    avg_interactive = sum(d.interactive_nodes for d in densities) / len(densities)

    return {
        'trace_file': str(trace_path.name),
        'variant': data.get('variant', ''),
        'task_id': data.get('taskId', ''),
        'success': data.get('success', False),
        'total_steps': len(steps),
        'observed_steps': len(densities),
        'avg_semantic_density': round(avg_density, 6),
        'avg_combined_density': round(avg_combined, 6),
        'avg_tokens_per_step': round(avg_tokens, 1),
        'avg_interactive_nodes': round(avg_interactive, 1),
        'max_tokens': max(d.total_tokens for d in densities),
        'min_density': round(min(d.semantic_density for d in densities), 6),
        'max_density': round(max(d.semantic_density for d in densities), 6),
    }


def analyze_density_by_variant(data_dir: str) -> pd.DataFrame:
    """Scan a data directory for trace files and compute per-variant density stats.

    Looks for trace-attempt-*.json files in the standard experiment directory structure:
        data_dir/runs/<runId>/cases/<caseId>/trace-attempt-*.json

    Returns a DataFrame with per-trace density metrics, suitable for
    statistical analysis (e.g., Wilcoxon rank-sum test between variants).
    """
    data_path = Path(data_dir)
    trace_files = list(data_path.rglob('trace-attempt-*.json'))

    results = []
    for tf in trace_files:
        row = analyze_trace_file(tf)
        if row:
            results.append(row)

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)

    # Print summary by variant
    if 'variant' in df.columns and len(df) > 0:
        summary = df.groupby('variant').agg({
            'avg_semantic_density': ['mean', 'std', 'count'],
            'avg_tokens_per_step': ['mean', 'std'],
            'avg_interactive_nodes': ['mean', 'std'],
            'success': 'mean',
        }).round(4)
        print("\n=== Semantic Density by Variant ===")
        print(summary.to_string())

    return df


# --- CLI entry point ---
if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m analysis.semantic_density <data_dir>")
        print("Example: python -m analysis.semantic_density ./data/pilot2/track-a")
        sys.exit(1)

    df = analyze_density_by_variant(sys.argv[1])
    if len(df) > 0:
        output_path = Path(sys.argv[1]) / 'semantic-density.csv'
        df.to_csv(output_path, index=False)
        print(f"\nResults written to {output_path}")
        print(f"Total traces analyzed: {len(df)}")
    else:
        print("No trace files found.")
