import math

import pytest

from bsolver.geometry import (
    HalfPlane,
    distance,
    intersect_halfplanes,
    online_envelope,
    outer_disk,
    wedge_halfplanes,
)
from bsolver.models import RegionType


def test_center_ray_and_angle_wrap_are_inside_wedge():
    for bearing in (0, 0.001, 90, 359.999):
        planes = wedge_halfplanes((10, -5), bearing)
        p = (10 + 1000 * math.cos(math.radians(bearing)), -5 + 1000 * math.sin(math.radians(bearing)))
        assert all(h.contains(p) for h in planes)


@pytest.mark.parametrize("error", [-1, -0.995, 0, 0.995, 1])
def test_rounding_boundary_keeps_true_source(error):
    true = 359.999
    measured = round((true + error) % 360, 2) % 360
    source = (1499 * math.cos(math.radians(true)), 1499 * math.sin(math.radians(true)))
    assert all(h.contains(source) for h in wedge_halfplanes((0, 0), measured))


def test_empty_unbounded_point_segment_and_polygon():
    empty = intersect_halfplanes([HalfPlane((1, 0), -1), HalfPlane((-1, 0), -1)])
    assert empty.region_type == RegionType.EMPTY
    assert intersect_halfplanes(wedge_halfplanes((0, 0), 0)).region_type == RegionType.UNBOUNDED
    point = intersect_halfplanes([HalfPlane((1, 0), 0), HalfPlane((-1, 0), 0),
                                  HalfPlane((0, 1), 0), HalfPlane((0, -1), 0)])
    assert point.region_type == RegionType.POINT
    segment = intersect_halfplanes([HalfPlane((1, 0), 1), HalfPlane((-1, 0), 0),
                                    HalfPlane((0, 1), 0), HalfPlane((0, -1), 0)])
    assert segment.region_type == RegionType.SEGMENT
    square = intersect_halfplanes([HalfPlane((1, 0), 1), HalfPlane((-1, 0), 1),
                                   HalfPlane((0, 1), 1), HalfPlane((0, -1), 1)])
    assert square.region_type == RegionType.POLYGON
    assert square.diameter_by_enumeration == pytest.approx(square.diameter_by_calipers)


def test_real_bearing_counterexample_not_covered_by_diameter_circle():
    observations = [
        ((219.6371773220712, -565.8863934992728), 111.109854244211),
        ((1167.8950275233592, 754.4756498642071), 212.8725349764743),
        ((-661.6684160721672, 421.60928928259386), 326.766884769148),
    ]
    result = intersect_halfplanes([h for s, a in observations for h in wedge_halfplanes(s, a)])
    assert result.diameter == pytest.approx(47.35857023942303, abs=1e-8)
    assert result.diameter_circle_covers is False


def test_outer_polygon_contains_disk_boundary_and_online_envelope_source():
    poly = outer_disk((0, 0), 1800)
    for deg in range(360):
        p = (1800 * math.cos(math.radians(deg)), 1800 * math.sin(math.radians(deg)))
        # Convex CCW polygon containment.
        assert all((b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= -1e-7
                   for a, b in zip(poly, poly[1:] + poly[:1]))
    source = (1499.0, 0.0)
    env = online_envelope([((0, 0), 0)])
    assert min(distance(source, p) for p in env) >= 0
    assert all((b[0] - a[0]) * (source[1] - a[1]) - (b[1] - a[1]) * (source[0] - a[0]) >= -1e-7
               for a, b in zip(env, env[1:] + env[:1]))


def test_near_parallel_decimal_review_is_reported():
    result = intersect_halfplanes([HalfPlane((1, 0), 1), HalfPlane((-1, 1e-14), 1), HalfPlane((0, 1), 1)])
    assert result.region_type in {RegionType.UNBOUNDED, RegionType.NUMERIC_UNCERTAIN}
    assert result.diagnostic is not None
