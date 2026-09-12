import inspect
import math

import pytest

import bsolver.strategy as strategy_module
from bsolver.models import BudgetExceeded, ChannelRecord, ChannelStatus, CommunicationFailure, ModelContradiction, Termination
from bsolver.simulator import SourceSpec, make_local_client, random_sources
from bsolver.strategy import _clear_or_raise, clear_active_channel, mixed_coverage_points, omni_coverage_points, run_strategy


def test_coverage_point_counts_and_directional_boundary_samples():
    omni = omni_coverage_points()
    assert len(omni) == 8
    assert all(math.hypot(*p) == pytest.approx(974) for p in omni)
    assert (0.0, 0.0) not in omni
    points = mixed_coverage_points()
    assert len(points) == 27
    nearest_spacing = min(math.dist(a, b) for i, a in enumerate(points) for b in points[i + 1:])
    assert nearest_spacing == pytest.approx(950, abs=1e-5)
    for radius in (0, 899, 1800):
        for degree in range(0, 360, 15):
            g = (radius * math.cos(math.radians(degree)), radius * math.sin(math.radians(degree)))
            for facing in range(0, 360, 30):
                u = (math.cos(math.radians(facing)), math.sin(math.radians(facing)))
                assert any(math.dist(p, g) <= 1000 + 1e-7 and (p[0] - g[0]) * u[0] + (p[1] - g[1]) * u[1] >= -1e-7
                        for p in points)
    # A lattice vertex and the midpoint of a lattice edge exercise closed-boundary ownership.
    for g in (points[0], ((points[0][0] + points[1][0]) / 2, (points[0][1] + points[1][1]) / 2)):
        for facing in range(0, 360, 15):
            u = (math.cos(math.radians(facing)), math.sin(math.radians(facing)))
            assert any(math.dist(p, g) <= 1000 + 1e-7 and (p[0] - g[0]) * u[0] + (p[1] - g[1]) * u[1] >= -1e-7
                       for p in points)


def test_strategy_b_uses_scheme_four_parameters_and_alns_never_worsens_seed_route():
    assert strategy_module.DETOUR_LIMIT_M == 530
    assert strategy_module.READY_RADIUS_M == 130
    assert strategy_module.PROBE_GEOMETRY_DEG == 12
    assert strategy_module.LOCAL_PROBE_CAP_M == 540
    assert strategy_module.LOCAL_AXIS_ANGLE_DEG == 40
    assert strategy_module.LOCAL_MAX_PROBES == 2
    assert strategy_module.COVER_CELL_LIMIT == 6
    points = [(100, 0), (0, 100), (-100, 0), (0, -100), (30, 30)]
    optimized = strategy_module._alns_order(points, (17, -23), iterations=50)
    length = lambda route: math.dist((17, -23), route[0]) + sum(
        math.dist(route[i], route[i + 1]) for i in range(len(route) - 1)
    )
    assert sorted(optimized) == sorted(points)
    assert length(optimized) <= length(strategy_module._tour(points, (17, -23))) + 1e-9


def test_strategy_b_finishes_all_unknown_channels_at_a_site_before_clearing():
    first_site = omni_coverage_points()[0]
    source = SourceSpec(1, (first_site[0] + 500, first_site[1]), 1500, "O")
    client, inspector = make_local_client([source])
    result = run_strategy(client, False, strategy="b")
    first_site_actions = client.action_log[1:21]
    assert all(action["path"] == "/measure" for action in first_site_actions)
    assert {action["channel"] for action in first_site_actions} == set(range(1, 21))
    assert result.termination == Termination.COMPLETED
    assert inspector.summary()["all_cleared"]


@pytest.mark.parametrize("mixed", [False, True])
@pytest.mark.parametrize("count", [10, 13, 16])
def test_closed_loop_multiple_counts(mixed, count):
    seed = 20260911 + count + int(mixed)
    client, inspector = make_local_client(random_sources(seed, count, mixed), seed % 13)
    result = run_strategy(client, mixed)
    assert result.termination == Termination.COMPLETED
    assert inspector.summary()["all_cleared"]
    assert result.virtual_time_s < 360000


def test_boundary_outward_sources_and_forced_fallback():
    sources = [SourceSpec(i + 1,
                          (1800 * math.cos(i * 2 * math.pi / 15), 1800 * math.sin(i * 2 * math.pi / 15)),
                          1000, "D", math.degrees(i * 2 * math.pi / 15)) for i in range(15)]
    sources.append(SourceSpec(20, (0, 0), 1000))
    client, inspector = make_local_client(sources, 2)
    result = run_strategy(client, True, force_fallback=True)
    assert result.termination == Termination.COMPLETED
    assert inspector.summary()["all_cleared"]


def test_measure_clear_measure_time_and_clear_does_not_switch():
    client, _ = make_local_client([SourceSpec(3, (300, 400), 1000)])
    client.enter()
    client.measure((0, 0), 1)
    assert client.clear((300, 400), 3).result == "success"
    client.measure((0, 0), 1)
    assert client.virtual_time_s == 215
    assert client.current_channel == 1
    assert client.time_breakdown["switch_s"] == 0


def test_strategy_module_has_no_simulator_or_truth_access():
    source = inspect.getsource(strategy_module)
    assert "bsolver.simulator" not in source
    for forbidden in ("radius_m", "direction_deg", "source_count", "truth"):
        assert forbidden not in source


def test_three_surrounding_positive_observations_do_not_exclude_omni():
    client, _ = make_local_client([SourceSpec(1, (0, 0), 1000, "O")])
    client.enter()
    points = [(100, 0), (-50, 50 * math.sqrt(3)), (-50, -50 * math.sqrt(3))]
    assert all(client.measure(p, 1).result == "direction" for p in points)


@pytest.mark.parametrize("error_model", ["sin", "uniform", "plus_one", "minus_one", "pm_one", "zero"])
def test_local_error_models_are_bounded_and_repeatable(error_model):
    client, _ = make_local_client([SourceSpec(1, (500, 0), 1500, "O")], 7, error_model)
    client.enter()
    first = client.measure((0, 0), 1)
    second = client.measure((0, 0), 1)
    assert first.result == second.result == "direction"
    assert first.svd_deg == second.svd_deg
    signed_error = ((first.svd_deg + 180) % 360) - 180
    assert abs(signed_error) <= 1.0000001


class AlwaysFailClearClient:
    position = (0.0, 0.0)
    current_channel = 1
    virtual_time_s = 0.0
    time_breakdown = {}
    action_log = []
    has_pending_action = False

    def clear(self, point, channel):
        from bsolver.models import ClearObservation
        self.position = point
        return ClearObservation("no_target_in_range", 0)


def test_certified_clear_failure_is_model_contradiction():
    record = ChannelRecord(1, ChannelStatus.ACTIVE, first_bearing=((0, 0), 0),
                           bearing_history=[((0, 0), 0)], polygon=[(10, 0)])
    with pytest.raises(ModelContradiction):
        clear_active_channel(AlwaysFailClearClient(), record)


def test_ordinary_trial_clear_failure_is_allowed_and_recordable():
    client = AlwaysFailClearClient()
    assert _clear_or_raise(client, (0, 0), 1, "trial") is False


@pytest.mark.parametrize("error, expected", [(BudgetExceeded("budget"), Termination.BUDGET_EXHAUSTED),
                                               (CommunicationFailure("network"), Termination.COMMUNICATION_ERROR)])
def test_abnormal_termination_is_not_reported_as_complete(error, expected):
    class BrokenClient:
        position = (0.0, 0.0)
        current_channel = 1
        virtual_time_s = 0.0
        time_breakdown = {}
        action_log = []
        has_pending_action = False
        def enter(self): return {"accepted": True}
        def measure(self, *_): raise error
    result = run_strategy(BrokenClient(), False)
    assert result.termination == expected
    assert result.cleared_count == 0
