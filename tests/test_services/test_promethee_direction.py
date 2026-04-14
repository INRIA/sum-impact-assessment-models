"""
Unit tests for PROMETHEE-GAIA goal direction (min/max) handling.

These tests verify that switching a goal direction between 'min' and 'max'
actually produces different rankings — the core bug that was being investigated.
"""
import pytest
from sum_impact_assessment.models.mcda_analysis.promethee_gaia_analysis import PrometheeGaiaAnalyzer
from sum_impact_assessment.schemas.mcda import Goal, Alternative


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_goal(name: str, direction: str, p: float = 10.0) -> Goal:
    return Goal(name=name, weight=1.0, direction=direction, Q=0, S=0, P=p, F="t3")


def _make_alt(name: str, **values) -> Alternative:
    return Alternative(name=name, values=dict(values))


# Three alternatives with a single criterion where order is clear:
#   alt_low=1, alt_mid=5, alt_high=9
# max direction → alt_high should rank first
# min direction → alt_low should rank first

SINGLE_CRITERION_ALTERNATIVES = [
    _make_alt("alt_low",  cost=1.0),
    _make_alt("alt_mid",  cost=5.0),
    _make_alt("alt_high", cost=9.0),
]


class TestDirectionAdjustedMatrix:
    """Low-level: verify adjusted_matrix is negated for min goals."""

    def test_max_direction_leaves_matrix_unchanged(self):
        goals = [_make_goal("g", "max")]
        alts  = [_make_alt("a1", g=3.0), _make_alt("a2", g=7.0)]
        analyzer = PrometheeGaiaAnalyzer(goals=goals, alternatives=alts)

        assert analyzer.adjusted_matrix[0, 0] == pytest.approx(3.0)
        assert analyzer.adjusted_matrix[1, 0] == pytest.approx(7.0)

    def test_min_direction_negates_matrix_column(self):
        goals = [_make_goal("g", "min")]
        alts  = [_make_alt("a1", g=3.0), _make_alt("a2", g=7.0)]
        analyzer = PrometheeGaiaAnalyzer(goals=goals, alternatives=alts)

        assert analyzer.adjusted_matrix[0, 0] == pytest.approx(-3.0)
        assert analyzer.adjusted_matrix[1, 0] == pytest.approx(-7.0)

    def test_raw_matrix_is_not_mutated(self):
        """self.matrix (raw) must stay unchanged regardless of direction."""
        goals = [_make_goal("g", "min")]
        alts  = [_make_alt("a1", g=3.0), _make_alt("a2", g=7.0)]
        analyzer = PrometheeGaiaAnalyzer(goals=goals, alternatives=alts)

        assert analyzer.matrix[0, 0] == pytest.approx(3.0)
        assert analyzer.matrix[1, 0] == pytest.approx(7.0)

    def test_mixed_directions_only_negates_min_columns(self):
        goals = [_make_goal("benefit", "max"), _make_goal("cost", "min")]
        alts  = [_make_alt("a1", benefit=2.0, cost=5.0),
                 _make_alt("a2", benefit=8.0, cost=3.0)]
        analyzer = PrometheeGaiaAnalyzer(goals=goals, alternatives=alts)

        # benefit column unchanged
        assert analyzer.adjusted_matrix[0, 0] == pytest.approx(2.0)
        assert analyzer.adjusted_matrix[1, 0] == pytest.approx(8.0)
        # cost column negated
        assert analyzer.adjusted_matrix[0, 1] == pytest.approx(-5.0)
        assert analyzer.adjusted_matrix[1, 1] == pytest.approx(-3.0)


class TestAllMaxRanking:
    """With all goals as 'max', higher values should rank first."""

    def test_highest_value_ranks_first(self):
        goals = [_make_goal("cost", "max", p=8.0)]
        analyzer = PrometheeGaiaAnalyzer(goals=goals, alternatives=SINGLE_CRITERION_ALTERNATIVES)
        output = analyzer.run_analysis(run_visualizations=False)

        top_key = output.ranking[0]
        assert output.alternative_labels[top_key] == "alt_high"

    def test_lowest_value_ranks_last(self):
        goals = [_make_goal("cost", "max", p=8.0)]
        analyzer = PrometheeGaiaAnalyzer(goals=goals, alternatives=SINGLE_CRITERION_ALTERNATIVES)
        output = analyzer.run_analysis(run_visualizations=False)

        last_key = output.ranking[-1]
        assert output.alternative_labels[last_key] == "alt_low"


class TestAllMinRanking:
    """With all goals as 'min', lower values should rank first."""

    def test_lowest_value_ranks_first(self):
        goals = [_make_goal("cost", "min", p=8.0)]
        analyzer = PrometheeGaiaAnalyzer(goals=goals, alternatives=SINGLE_CRITERION_ALTERNATIVES)
        output = analyzer.run_analysis(run_visualizations=False)

        top_key = output.ranking[0]
        assert output.alternative_labels[top_key] == "alt_low"

    def test_highest_value_ranks_last(self):
        goals = [_make_goal("cost", "min", p=8.0)]
        analyzer = PrometheeGaiaAnalyzer(goals=goals, alternatives=SINGLE_CRITERION_ALTERNATIVES)
        output = analyzer.run_analysis(run_visualizations=False)

        last_key = output.ranking[-1]
        assert output.alternative_labels[last_key] == "alt_high"


class TestDirectionProducesDistinctRankings:
    """The key regression check: min and max on the same data must differ."""

    def test_all_min_vs_all_max_produce_opposite_rankings(self):
        alts = SINGLE_CRITERION_ALTERNATIVES

        analyzer_max = PrometheeGaiaAnalyzer(
            goals=[_make_goal("cost", "max", p=8.0)], alternatives=alts
        )
        analyzer_min = PrometheeGaiaAnalyzer(
            goals=[_make_goal("cost", "min", p=8.0)], alternatives=alts
        )

        output_max = analyzer_max.run_analysis(run_visualizations=False)
        output_min = analyzer_min.run_analysis(run_visualizations=False)

        # Rankings must be different
        assert output_max.ranking != output_min.ranking

        # And specifically reversed
        assert output_max.ranking == list(reversed(output_min.ranking))

    def test_net_flows_are_negated_when_direction_flips(self):
        alts = SINGLE_CRITERION_ALTERNATIVES

        analyzer_max = PrometheeGaiaAnalyzer(
            goals=[_make_goal("cost", "max", p=8.0)], alternatives=alts
        )
        analyzer_min = PrometheeGaiaAnalyzer(
            goals=[_make_goal("cost", "min", p=8.0)], alternatives=alts
        )

        out_max = analyzer_max.run_analysis(run_visualizations=False)
        out_min = analyzer_min.run_analysis(run_visualizations=False)

        for key in out_max.net_flows:
            assert out_max.net_flows[key] == pytest.approx(-out_min.net_flows[key], abs=1e-9)


class TestMixedDirectionRanking:
    """Mixed min/max goals should produce a result distinct from both all-min and all-max."""

    def test_mixed_goals_ranking_differs_from_all_max(self):
        # Two goals: one benefit (max), one cost (min)
        # alt_A: high benefit, low cost  → should win
        # alt_B: low benefit, high cost  → should lose
        # alt_C: mid benefit, mid cost
        goals = [
            _make_goal("benefit", "max", p=8.0),
            _make_goal("cost",    "min", p=8.0),
        ]
        alts = [
            _make_alt("alt_A", benefit=9.0, cost=1.0),
            _make_alt("alt_B", benefit=1.0, cost=9.0),
            _make_alt("alt_C", benefit=5.0, cost=5.0),
        ]

        analyzer = PrometheeGaiaAnalyzer(goals=goals, alternatives=alts)
        output = analyzer.run_analysis(run_visualizations=False)

        top_key  = output.ranking[0]
        last_key = output.ranking[-1]
        assert output.alternative_labels[top_key]  == "alt_A"
        assert output.alternative_labels[last_key] == "alt_B"
