"""Tests for semantic density metric computation."""

import pytest
from analysis.semantic_density import (
    compute_semantic_density,
    count_nodes_by_role,
    count_tokens,
    SemanticDensityResult,
)


class TestCountTokens:
    def test_empty_string(self):
        assert count_tokens('') == 0

    def test_single_word(self):
        assert count_tokens('hello') == 1

    def test_typical_axtree_line(self):
        assert count_tokens("[42] link 'Home page'") == 4


class TestCountNodesByRole:
    def test_empty(self):
        assert count_nodes_by_role('') == (0, 0, 0)

    def test_single_interactive(self):
        text = "[1] button 'Submit'"
        interactive, landmark, total = count_nodes_by_role(text)
        assert interactive == 1
        assert landmark == 0
        assert total == 1

    def test_mixed_roles(self):
        text = (
            "[1] navigation 'Main nav'\n"
            "  [2] link 'Home'\n"
            "  [3] link 'About'\n"
            "[4] main 'Content'\n"
            "  [5] heading 'Welcome'\n"
            "  [6] textbox 'Search'\n"
            "  [7] StaticText 'Some text'\n"
        )
        interactive, landmark, total = count_nodes_by_role(text)
        assert interactive == 3  # link, link, textbox
        assert landmark == 3     # navigation, main, heading
        assert total == 7

    def test_non_node_lines_ignored(self):
        text = (
            "Page title: Example\n"
            "[1] button 'OK'\n"
            "  some random text\n"
        )
        interactive, landmark, total = count_nodes_by_role(text)
        assert interactive == 1
        assert total == 1


class TestComputeSemanticDensity:
    def test_high_density_page(self):
        """A page with many interactive elements and few tokens = high density."""
        text = (
            "[1] navigation 'Nav'\n"
            "  [2] link 'Home'\n"
            "  [3] link 'Products'\n"
            "  [4] link 'Contact'\n"
            "[5] main 'Content'\n"
            "  [6] button 'Buy Now'\n"
            "  [7] textbox 'Email'\n"
        )
        result = compute_semantic_density(text)
        assert result.interactive_nodes == 5  # 3 links + button + textbox
        assert result.landmark_nodes == 2     # navigation + main
        assert result.total_nodes == 7
        assert result.semantic_density > 0.1  # high density

    def test_low_density_page(self):
        """A page with few interactive elements and many tokens = low density."""
        lines = []
        for i in range(100):
            lines.append(f"[{i}] StaticText 'Lorem ipsum dolor sit amet'")
        lines.append("[100] button 'Submit'")
        text = '\n'.join(lines)

        result = compute_semantic_density(text)
        assert result.interactive_nodes == 1
        assert result.total_nodes == 101
        assert result.semantic_density < 0.01  # low density

    def test_empty_returns_zeros(self):
        result = compute_semantic_density('')
        assert result.semantic_density == 0.0
        assert result.interactive_nodes == 0
        assert result.total_tokens == 0

    def test_interactive_ratio(self):
        text = (
            "[1] link 'A'\n"
            "[2] link 'B'\n"
            "[3] StaticText 'C'\n"
            "[4] StaticText 'D'\n"
        )
        result = compute_semantic_density(text)
        assert result.interactive_ratio == pytest.approx(0.5)
