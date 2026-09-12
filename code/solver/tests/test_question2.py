import pytest

from bsolver.question2 import design_second_station


def test_near_is_immediate_clear():
    result = design_second_station((3, 4), "near")
    assert result.status == "IMMEDIATE_CLEAR"
    assert result.nominal_point == (3, 4)


def test_frozen_design_example_and_disclaimer():
    result = design_second_station((0, 0), "direction", 0)
    assert result.status == "DESIGNED"
    assert result.nominal_point in {(850.0, -500.0), (850.0, 500.0)}
    assert len(result.score_rows) == 169
    assert all(row["distance_margin_m"] >= 1 - 1e-7 for row in result.score_rows)
    assert "不是连续全局最优" in result.note
    assert all(c["radius_m"] <= 10 for c in result.candidate_circles)


def test_invalid_first_observation_is_explicit_error():
    assert design_second_station((0, 0), "no_signal").status == "GEOMETRY_INPUT_ERROR"
