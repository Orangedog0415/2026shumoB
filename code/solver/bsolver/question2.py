from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .geometry import (
    DELTA_RAD,
    clip_with_wedge,
    distance,
    online_envelope,
    polygon_diameter,
    polygon_radius,
    vertex_average,
)
from .models import Point


@dataclass
class SecondStationResult:
    status: str
    nominal_point: Point | None
    candidate_circles: list[dict[str, Any]]
    score_rows: list[dict[str, float]]
    sample_config: dict[str, Any]
    note: str
    diagnostic: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__


def _boundary_samples(poly: list[Point], step: float = 100.0) -> list[Point]:
    samples: list[Point] = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        count = max(1, math.ceil(distance(a, b) / step))
        samples.extend((a[0] + i / count * (b[0] - a[0]), a[1] + i / count * (b[1] - a[1]))
                       for i in range(count))
    samples.append(vertex_average(poly))
    return samples


def design_second_station(first: Point, result: str, bearing_deg: float | None = None) -> SecondStationResult:
    config = {
        "candidate_step_m": 50,
        "source_edge_step_m": 100,
        "error_samples_deg": [-1.005, 0.0, 1.005],
        "safe_vertex_distance_m": 999,
        "movement_weight_m_per_s": 0.05,
        "qualified_ratio": 1.2,
    }
    note = "有限采样设计结果，不是连续全局最优或连续严格最坏误差证明。"
    if result == "near":
        return SecondStationResult("IMMEDIATE_CLEAR", first, [], [], config, note)
    if result != "direction" or bearing_deg is None or not math.isfinite(bearing_deg):
        return SecondStationResult("GEOMETRY_INPUT_ERROR", None, [], [], config, note,
                                   "首次观测必须是 near 或带有限 svd_deg 的 direction")
    poly = online_envelope([(first, bearing_deg)])
    if not poly:
        return SecondStationResult("GEOMETRY_INPUT_ERROR", None, [], [], config, note,
                                   "首次观测外包络为空")
    theta = math.radians(bearing_deg)
    u, w = (math.cos(theta), math.sin(theta)), (-math.sin(theta), math.cos(theta))
    samples = _boundary_samples(poly)
    rows: list[dict[str, float]] = []
    for a in range(0, 1501, 50):
        for b in range(-1000, 1001, 50):
            s = (first[0] + a * u[0] + b * w[0], first[1] + a * u[1] + b * w[1])
            if not all(math.isfinite(v) and abs(v) <= 2_000_000 for v in s):
                continue
            max_distance = polygon_radius(poly, s)
            if max_distance > 999 + 1e-9:
                continue
            worst = 0.0
            for g in samples:
                if distance(g, s) <= 5:
                    worst = max(worst, 10.0)
                    continue
                true_angle = math.degrees(math.atan2(g[1] - s[1], g[0] - s[0]))
                for e in (-math.degrees(DELTA_RAD), 0.0, math.degrees(DELTA_RAD)):
                    worst = max(worst, polygon_diameter(clip_with_wedge(poly, s, true_angle + e)))
            move = distance(first, s)
            score = worst + 0.05 * move / 5
            rows.append({"x": s[0], "y": s[1], "a": float(a), "b": float(b),
                         "score": score, "sampled_worst_diameter_m": worst,
                         "movement_m": move, "distance_margin_m": 1000 - max_distance})
    if not rows:
        fallback = (first[0] + 750 * u[0], first[1] + 750 * u[1])
        margin = 1000 - polygon_radius(poly, fallback)
        if margin < 0:
            return SecondStationResult("GEOMETRY_INPUT_ERROR", None, [], [], config, note,
                                       "固定网格和 750 m 备用点均无法认证接收")
        rows.append({"x": fallback[0], "y": fallback[1], "a": 750.0, "b": 0.0,
                     "score": math.inf, "sampled_worst_diameter_m": math.inf,
                     "movement_m": 750.0, "distance_margin_m": margin})
    rows.sort(key=lambda r: (r["score"], r["movement_m"], r["a"], r["b"]))
    best = rows[0]
    limit = 1.2 * best["score"]
    circles = []
    for row in rows:
        if row["score"] <= limit:
            eps = min(10.0, row["distance_margin_m"] / 2)
            circles.append({"center": [row["x"], row["y"]], "radius_m": max(0.0, eps),
                            "center_score": row["score"], "distance_margin_m": row["distance_margin_m"]})
    return SecondStationResult("DESIGNED", (best["x"], best["y"]), circles, rows, config, note)
