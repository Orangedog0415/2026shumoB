from __future__ import annotations

import math
import random
import time
from typing import Iterable

from .geometry import (
    HalfPlane,
    clip_polygon,
    clip_with_outer_disk,
    clip_with_wedge,
    distance,
    dot,
    online_envelope,
    polygon_radius,
    vertex_average,
)
from .models import (
    BudgetExceeded,
    ChannelRecord,
    ChannelStatus,
    CommunicationFailure,
    ModelContradiction,
    ObservationClient,
    Point,
    ProtocolFailure,
    RunResult,
    Termination,
)

EPS = 1e-7
DETOUR_LIMIT_M = 530.0
READY_RADIUS_M = 130.0
PROBE_GEOMETRY_DEG = 12.0
LOCAL_PROBE_CAP_M = 540.0
LOCAL_AXIS_ANGLE_DEG = 40.0
LOCAL_MAX_PROBES = 2
COVER_CELL_LIMIT = 6
ALNS_ITERATIONS = 200


def omni_coverage_points() -> list[Point]:
    """Strategy B Q3 net: an eight-point ring without a center stop."""
    return [(974 * math.cos(k * math.pi / 4), 974 * math.sin(k * math.pi / 4)) for k in range(8)]


def mixed_coverage_points() -> list[Point]:
    """Scheme 4 Q4 net: rotated h=950 triangular lattice with optimized offset."""
    h, offset_x = 950.0, 475.0
    offset_y = h * math.sqrt(3) / 4
    rotation = math.radians(30)
    cos_rotation, sin_rotation = math.cos(rotation), math.sin(rotation)
    points: set[Point] = set()

    def lattice_point(k: int, row: int) -> Point:
        x = offset_x + k * h + row * h / 2
        y = offset_y + row * h * math.sqrt(3) / 2
        return (round(cos_rotation * x - sin_rotation * y, 6),
                round(sin_rotation * x + cos_rotation * y, 6))

    def segment_distance(a: Point, b: Point) -> float:
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = max(0.0, min(1.0, -(a[0] * dx + a[1] * dy) / (dx * dx + dy * dy)))
        return math.hypot(a[0] + t * dx, a[1] + t * dy)

    def triangle_hits_target(vertices: list[Point]) -> bool:
        signs = [
            (vertices[(i + 1) % 3][0] - vertices[i][0]) * -vertices[i][1]
            - (vertices[(i + 1) % 3][1] - vertices[i][1]) * -vertices[i][0]
            for i in range(3)
        ]
        contains_origin = all(v >= 0 for v in signs) or all(v <= 0 for v in signs)
        return contains_origin or min(segment_distance(vertices[i], vertices[(i + 1) % 3]) for i in range(3)) < 1800

    extent = int(2 * 1800 / h) + 3
    for k in range(-extent, extent + 1):
        for row in range(-extent, extent + 1):
            triangles = (((k, row), (k + 1, row), (k, row + 1)),
                         ((k + 1, row), (k + 1, row + 1), (k, row + 1)))
            for triangle in triangles:
                vertices = [lattice_point(*index) for index in triangle]
                if triangle_hits_target(vertices):
                    points.update(vertices)
    return sorted(points, key=lambda p: (math.hypot(*p), p[0], p[1]))


def _baseline_omni_coverage_points() -> list[Point]:
    return [(0.0, 0.0)] + [
        (1200 * math.cos(k * math.pi / 3), 1200 * math.sin(k * math.pi / 3)) for k in range(6)
    ]


def _baseline_mixed_coverage_points() -> list[Point]:
    points: list[Point] = []
    for row in range(-4, 5):
        for column in range(-4, 5):
            p = (900 * (column + (row % 2) / 2), 900 * math.sqrt(3) * row / 2)
            if math.hypot(*p) <= 2700 + EPS:
                points.append(p)
    return sorted(points, key=lambda p: (math.hypot(*p), p[0], p[1]))


def _tour(points: list[Point], start: Point = (0.0, 0.0)) -> list[Point]:
    """Nearest-neighbour route followed by deterministic open-path 2-opt."""
    remaining = list(range(len(points)))
    order: list[int] = []
    current = start
    while remaining:
        index = min(remaining, key=lambda i: (distance(current, points[i]), i))
        order.append(index)
        remaining.remove(index)
        current = points[index]

    def route_length(candidate: list[int]) -> float:
        if not candidate:
            return 0.0
        return distance(start, points[candidate[0]]) + sum(
            distance(points[candidate[i]], points[candidate[i + 1]]) for i in range(len(candidate) - 1)
        )

    improved = True
    while improved:
        improved = False
        current_length = route_length(order)
        for i in range(len(order) - 1):
            for j in range(i + 1, len(order)):
                candidate = order[:i] + list(reversed(order[i:j + 1])) + order[j + 1:]
                candidate_length = route_length(candidate)
                if candidate_length < current_length - 1e-9:
                    order, current_length, improved = candidate, candidate_length, True
    return [points[i] for i in order]


def _alns_order(points: list[Point], start: Point, iterations: int = ALNS_ITERATIONS,
                seed: int = 0) -> list[Point]:
    """Deterministic ALNS improvement for the final open clearing route."""
    if len(points) <= 2:
        return _tour(points, start)
    rng = random.Random(seed)
    current = _tour(points, start)

    def route_length(route: list[Point]) -> float:
        return distance(start, route[0]) + sum(
            distance(route[i], route[i + 1]) for i in range(len(route) - 1)
        )

    best = list(current)
    best_length = route_length(best)
    for _ in range(iterations):
        candidate = list(current)
        removed_count = max(1, min(len(candidate) - 1,
                                   rng.randint(1, max(1, len(candidate) // 3))))
        if rng.random() < 0.5:
            removed = rng.sample(candidate, removed_count)
        else:
            gains: list[tuple[float, int]] = []
            for i, point in enumerate(candidate):
                before = start if i == 0 else candidate[i - 1]
                after = candidate[i + 1] if i + 1 < len(candidate) else None
                gain = distance(before, point)
                if after is not None:
                    gain += distance(point, after) - distance(before, after)
                gains.append((gain, i))
            gains.sort(reverse=True)
            removed = [candidate[i] for _, i in gains[:removed_count]]
        for point in removed:
            candidate.remove(point)
        for point in removed:
            insertion = min(range(len(candidate) + 1),
                            key=lambda i: route_length(candidate[:i] + [point] + candidate[i:]))
            candidate.insert(insertion, point)
        improved = True
        while improved:
            improved = False
            candidate_length = route_length(candidate)
            for i in range(len(candidate) - 1):
                for j in range(i + 1, len(candidate)):
                    trial = candidate[:i] + list(reversed(candidate[i:j + 1])) + candidate[j + 1:]
                    trial_length = route_length(trial)
                    if trial_length < candidate_length - 1e-9:
                        candidate, candidate_length, improved = trial, trial_length, True
        candidate_length = route_length(candidate)
        if candidate_length < best_length - 1e-9:
            best, best_length, current = list(candidate), candidate_length, list(candidate)
        elif rng.random() < 0.1:
            current = list(candidate)
    return best


def _fallback_grid(anchor: Point, bearing_deg: float) -> list[tuple[Point, list[Point]]]:
    theta = math.radians(bearing_deg)
    u, w = (math.cos(theta), math.sin(theta)), (-math.sin(theta), math.cos(theta))
    result: list[tuple[Point, list[Point]]] = []
    for i in range(75):
        rows: Iterable[int] = range(3) if i % 2 == 0 else reversed(range(3))
        for j in rows:
            x0, y0 = 20 * i, -30 + 20 * j
            local = [(x0, y0), (x0 + 20, y0), (x0 + 20, y0 + 20), (x0, y0 + 20)]
            cell = [(anchor[0] + x * u[0] + y * w[0], anchor[1] + x * u[1] + y * w[1]) for x, y in local]
            center = (anchor[0] + (x0 + 10) * u[0] + (y0 + 10) * w[0],
                      anchor[1] + (x0 + 10) * u[1] + (y0 + 10) * w[1])
            result.append((center, cell))
    return result


def _cell_intersects_polygon(cell: list[Point], polygon: list[Point]) -> bool:
    clipped = list(polygon)
    for a, b in zip(cell, cell[1:] + cell[:1]):
        edge = (b[0] - a[0], b[1] - a[1])
        normal = (edge[1], -edge[0])
        clipped = clip_polygon(clipped, HalfPlane(normal, dot(normal, a)))
        if not clipped:
            return False
    return True


def _update_polygon(poly: list[Point], station: Point, bearing_deg: float) -> list[Point]:
    updated = clip_with_wedge(poly, station, bearing_deg)
    return clip_with_outer_disk(updated, station, 1500.0)


def _clear_or_raise(client: ObservationClient, point: Point, channel: int, reason: str) -> bool:
    response = client.clear(point, channel)
    if response.result == "success":
        return True
    if reason in {"near", "certified"}:
        raise ModelContradiction(f"{reason} clear failed on channel {channel}")
    return False


def _transition(client: ObservationClient, record: ChannelRecord, status: ChannelStatus, reason: str) -> None:
    old = record.status
    record.status = status
    if client.action_log:
        client.action_log[-1].setdefault("channel_state_changes", []).append(
            {"channel": record.channel, "from": old.value, "to": status.value, "reason": reason}
        )


def _axis_info(poly: list[Point]) -> tuple[Point, float]:
    center = vertex_average(poly)
    a, b = max(((a, b) for a in poly for b in poly), key=lambda pair: distance(*pair))
    return center, math.atan2(b[1] - a[1], b[0] - a[0])


def _cover_centers(poly: list[Point]) -> list[Point]:
    """Return centers of 28 m cells intersecting the possible-source polygon."""
    center, angle = _axis_info(poly)
    u, w = (math.cos(angle), math.sin(angle)), (-math.sin(angle), math.cos(angle))
    xs = [dot((p[0] - center[0], p[1] - center[1]), u) for p in poly]
    ys = [dot((p[0] - center[0], p[1] - center[1]), w) for p in poly]
    side = 28.0
    nx = max(1, math.ceil((max(xs) - min(xs)) / side))
    ny = max(1, math.ceil((max(ys) - min(ys)) / side))
    x0 = (max(xs) + min(xs)) / 2 - nx * side / 2
    y0 = (max(ys) + min(ys)) / 2 - ny * side / 2
    result: list[Point] = []
    for i in range(nx):
        for j in range(ny):
            clipped = list(poly)
            bounds = [
                (u, dot(u, center) + x0 + (i + 1) * side),
                ((-u[0], -u[1]), -dot(u, center) - (x0 + i * side)),
                (w, dot(w, center) + y0 + (j + 1) * side),
                ((-w[0], -w[1]), -dot(w, center) - (y0 + j * side)),
            ]
            for normal, bound in bounds:
                clipped = clip_polygon(clipped, HalfPlane(normal, bound))
            if clipped:
                cx, cy = x0 + (i + 0.5) * side, y0 + (j + 0.5) * side
                result.append((center[0] + cx * u[0] + cy * w[0],
                               center[1] + cx * u[1] + cy * w[1]))
    return result


def _good_geometry(record: ChannelRecord, point: Point) -> bool:
    center = vertex_average(record.polygon)
    candidate_angle = math.atan2(center[1] - point[1], center[0] - point[0])
    threshold = math.sin(math.radians(PROBE_GEOMETRY_DEG))
    return all(abs(math.sin(candidate_angle - math.radians(bearing))) > threshold
               for _, bearing in record.bearing_history)


def _add_direction(record: ChannelRecord, point: Point, bearing_deg: float) -> None:
    if record.first_bearing is None:
        record.first_bearing = (point, bearing_deg)
        record.bearing_history.append((point, bearing_deg))
        record.polygon = online_envelope([record.first_bearing])
        return
    updated = _update_polygon(record.polygon, point, bearing_deg)
    if updated:
        record.bearing_history.append((point, bearing_deg))
        record.polygon = updated


def clear_active_channel(client: ObservationClient, record: ChannelRecord, force_fallback: bool = False) -> None:
    if record.first_bearing is None:
        raise ModelContradiction("ACTIVE channel lacks first bearing")
    first, first_bearing = record.first_bearing
    initial = online_envelope([(first, first_bearing)])
    poly = list(record.polygon or initial)
    measured = [p for p, _ in record.bearing_history]
    probes = 0
    if not force_fallback:
        while poly:
            center = vertex_average(poly)
            radius = polygon_radius(poly, center)
            if radius <= 19.5:
                if _clear_or_raise(client, center, record.channel, "certified"):
                    return
            cover = _cover_centers(poly)
            if len(cover) <= COVER_CELL_LIMIT:
                remaining = list(cover)
                current = client.position
                ordered: list[Point] = []
                while remaining:
                    point = min(remaining, key=lambda p: (distance(current, p), p[0], p[1]))
                    remaining.remove(point)
                    ordered.append(point)
                    current = point
                for point in ordered:
                    if _clear_or_raise(client, point, record.channel, "trial"):
                        return
                    record.failed_clear_centers.append(point)
                raise ModelContradiction(f"certified finite-circle cover failed on channel {record.channel}")
            if probes >= LOCAL_MAX_PROBES:
                break
            _, axis_angle = _axis_info(poly)
            probe_distance = max(radius + 15, min(LOCAL_PROBE_CAP_M, distance(client.position, center)))
            candidates = []
            for k in range(36):
                angle = 2 * math.pi * k / 36
                if abs(math.sin(angle - axis_angle)) < math.sin(math.radians(LOCAL_AXIS_ANGLE_DEG)):
                    continue
                point = (center[0] + probe_distance * math.cos(angle),
                         center[1] + probe_distance * math.sin(angle))
                if all(distance(point, old) >= 1 for old in measured):
                    candidates.append(point)
            if not candidates:
                break
            detecting_angles = [math.atan2(p[1] - center[1], p[0] - center[0]) for p in measured]

            def risk(point: Point) -> float:
                angle = math.atan2(point[1] - center[1], point[0] - center[0])
                return min(abs(math.atan2(math.sin(angle - old), math.cos(angle - old)))
                           for old in detecting_angles)

            point = min(candidates, key=lambda p: (distance(client.position, p) / 5
                                                   + (0 if risk(p) < math.radians(60) else 60), p[0], p[1]))
            probes += 1
            obs = client.measure(point, record.channel)
            measured.append(point)
            if obs.result == "near":
                if _clear_or_raise(client, point, record.channel, "near"):
                    return
            elif obs.result == "direction":
                assert obs.svd_deg is not None
                new_poly = _update_polygon(poly, point, obs.svd_deg)
                if new_poly:
                    record.bearing_history.append((point, obs.svd_deg))
                    poly = new_poly
                    record.polygon = new_poly
            elif obs.result != "no_signal":
                raise ProtocolFailure(f"unknown measure result {obs.result}")

    trusted = poly or initial
    attempted: set[tuple[float, float]] = set()
    full_grid = _fallback_grid(first, first_bearing)
    for center, cell in full_grid:
        if not _cell_intersects_polygon(cell, trusted):
            continue
        if any(max(distance(v, failed) for v in cell) <= 20 - EPS for failed in record.failed_clear_centers):
            continue
        key = (round(center[0], 10), round(center[1], 10))
        attempted.add(key)
        if _clear_or_raise(client, center, record.channel, "fallback"):
            return
        record.failed_clear_centers.append(center)
    # Numerical safety pass: every previously pruned center is retried at most once.
    for center, _ in full_grid:
        key = (round(center[0], 10), round(center[1], 10))
        if key in attempted:
            continue
        attempted.add(key)
        if _clear_or_raise(client, center, record.channel, "fallback"):
            return
    raise ModelContradiction(f"225-center certified cover exhausted on channel {record.channel}")


def _run_strategy_a(client: ObservationClient, mixed: bool, force_fallback: bool = False) -> RunResult:
    started_at = time.monotonic()
    points = _baseline_mixed_coverage_points() if mixed else _baseline_omni_coverage_points()
    records = [ChannelRecord(channel=i) for i in range(1, 21)]
    failure_message = ""
    try:
        enter = client.enter()
        if enter.get("accepted") is not True:
            raise ProtocolFailure("enter rejected")
        while True:
            cleared = sum(r.status == ChannelStatus.CLEARED for r in records)
            for record in records:
                if record.status == ChannelStatus.UNKNOWN and len(record.no_signal_site_ids) == len(points):
                    _transition(client, record, ChannelStatus.EXCLUDED, "all coverage sites returned no_signal")
            if cleared == 16 or all(r.status in {ChannelStatus.CLEARED, ChannelStatus.EXCLUDED} for r in records):
                client.exit()
                return RunResult(Termination.COMPLETED, cleared,
                                 sum(r.status == ChannelStatus.EXCLUDED for r in records), client.virtual_time_s,
                                 len(client.action_log), "coverage certificate complete", records,
                                 dict(client.time_breakdown), time.monotonic() - started_at)
            unknown = [r for r in records if r.status == ChannelStatus.UNKNOWN]
            remaining = [i for i in range(len(points)) if any(i not in r.no_signal_site_ids for r in unknown)]
            if not remaining:
                raise ModelContradiction("scheduler has UNKNOWN channels but no remaining site")
            site_id = min(remaining, key=lambda i: (distance(client.position, points[i]), i))
            channels = [r for r in unknown if site_id not in r.no_signal_site_ids]
            channels.sort(key=lambda r: (r.channel != client.current_channel, r.channel))
            for record in channels:
                obs = client.measure(points[site_id], record.channel)
                if obs.result == "no_signal":
                    record.no_signal_site_ids.add(site_id)
                    continue
                if obs.result == "near":
                    if _clear_or_raise(client, points[site_id], record.channel, "near"):
                        _transition(client, record, ChannelStatus.CLEARED, "near followed by successful clear")
                    break
                if obs.result != "direction" or obs.svd_deg is None:
                    raise ProtocolFailure("direction result lacks bearing")
                _transition(client, record, ChannelStatus.ACTIVE, "direction observation")
                record.first_bearing = (points[site_id], obs.svd_deg)
                record.bearing_history.append((points[site_id], obs.svd_deg))
                record.polygon = online_envelope([record.first_bearing])
                clear_active_channel(client, record, force_fallback)
                _transition(client, record, ChannelStatus.CLEARED, "local controller successful clear")
                break
    except BudgetExceeded as exc:
        termination = Termination.BUDGET_EXHAUSTED
        failure_message = str(exc)
    except (CommunicationFailure, ProtocolFailure) as exc:
        termination = Termination.COMMUNICATION_ERROR
        failure_message = str(exc)
    except ModelContradiction as exc:
        termination = Termination.MODEL_CONTRADICTION
        failure_message = str(exc)
        for record in records:
            if record.status == ChannelStatus.ACTIVE:
                _transition(client, record, ChannelStatus.ERROR, failure_message)
    else:  # pragma: no cover - all successful paths return above
        raise AssertionError("unreachable")
    return RunResult(termination, sum(r.status == ChannelStatus.CLEARED for r in records),
                     sum(r.status == ChannelStatus.EXCLUDED for r in records), client.virtual_time_s,
                     len(client.action_log), failure_message, records, dict(client.time_breakdown),
                     time.monotonic() - started_at)


def _run_strategy_b(client: ObservationClient, mixed: bool, force_fallback: bool = False) -> RunResult:
    started_at = time.monotonic()
    points = _tour(mixed_coverage_points() if mixed else omni_coverage_points())
    records = [ChannelRecord(channel=i) for i in range(1, 21)]
    failure_message = ""

    def finish() -> RunResult:
        client.exit()
        return RunResult(Termination.COMPLETED,
                         sum(r.status == ChannelStatus.CLEARED for r in records),
                         sum(r.status == ChannelStatus.EXCLUDED for r in records),
                         client.virtual_time_s, len(client.action_log), "coverage certificate complete",
                         records, dict(client.time_breakdown), time.monotonic() - started_at)

    def clear_record(record: ChannelRecord) -> None:
        clear_active_channel(client, record, force_fallback)
        _transition(client, record, ChannelStatus.CLEARED, "scheme 4 local controller successful clear")

    try:
        enter = client.enter()
        if enter.get("accepted") is not True:
            raise ProtocolFailure("enter rejected")
        next_site = 0
        while True:
            cleared = sum(r.status == ChannelStatus.CLEARED for r in records)
            if cleared == 16:
                return finish()

            unknown = [r for r in records if r.status == ChannelStatus.UNKNOWN]
            active = [r for r in records if r.status == ChannelStatus.ACTIVE]
            if next_site >= len(points):
                for record in unknown:
                    if len(record.no_signal_site_ids) != len(points):
                        raise ModelContradiction("coverage route ended before all unknown channels were certified")
                    _transition(client, record, ChannelStatus.EXCLUDED, "all strategy B coverage sites returned no_signal")
                if not active:
                    return finish()
                remaining = list(active)
                centers = [vertex_average(record.polygon) for record in remaining]
                for center in _alns_order(centers, client.position):
                    record = min(remaining,
                                 key=lambda r: (distance(center, vertex_average(r.polygon)), r.channel))
                    remaining.remove(record)
                    clear_record(record)
                    if sum(r.status == ChannelStatus.CLEARED for r in records) == 16:
                        break
                continue

            target = points[next_site]
            detours: list[tuple[float, int, ChannelRecord]] = []
            for record in active:
                center = vertex_average(record.polygon)
                radius = polygon_radius(record.polygon, center)
                if radius > READY_RADIUS_M:
                    continue
                detour = (distance(client.position, center) + distance(center, target)
                          - distance(client.position, target))
                if detour <= DETOUR_LIMIT_M:
                    detours.append((detour, record.channel, record))
            if detours:
                clear_record(min(detours)[2])
                continue

            site_id = next_site
            next_site += 1
            scan = sorted(unknown, key=lambda r: (r.channel != client.current_channel, r.channel))
            extras = [
                record for record in active
                if polygon_radius(record.polygon, vertex_average(record.polygon)) > 19.5
                and polygon_radius(record.polygon, target) <= 1500
                and _good_geometry(record, target)
            ]
            for record in scan + sorted(extras, key=lambda r: (r.channel != client.current_channel, r.channel)):
                if record.status == ChannelStatus.UNKNOWN:
                    record.no_signal_site_ids.add(site_id)
                obs = client.measure(target, record.channel)
                if obs.result == "near":
                    if _clear_or_raise(client, target, record.channel, "near"):
                        _transition(client, record, ChannelStatus.CLEARED, "near followed by successful clear")
                elif obs.result == "direction":
                    if obs.svd_deg is None:
                        raise ProtocolFailure("direction result lacks bearing")
                    if record.status == ChannelStatus.UNKNOWN:
                        _transition(client, record, ChannelStatus.ACTIVE, "strategy B direction observation")
                    _add_direction(record, target, obs.svd_deg)
                elif obs.result != "no_signal":
                    raise ProtocolFailure(f"unknown measure result {obs.result}")
                if sum(r.status == ChannelStatus.CLEARED for r in records) == 16:
                    break
    except BudgetExceeded as exc:
        termination = Termination.BUDGET_EXHAUSTED
        failure_message = str(exc)
    except (CommunicationFailure, ProtocolFailure) as exc:
        termination = Termination.COMMUNICATION_ERROR
        failure_message = str(exc)
    except ModelContradiction as exc:
        termination = Termination.MODEL_CONTRADICTION
        failure_message = str(exc)
        for record in records:
            if record.status == ChannelStatus.ACTIVE:
                _transition(client, record, ChannelStatus.ERROR, failure_message)
    else:  # pragma: no cover - all successful paths return above
        raise AssertionError("unreachable")
    return RunResult(termination, sum(r.status == ChannelStatus.CLEARED for r in records),
                     sum(r.status == ChannelStatus.EXCLUDED for r in records), client.virtual_time_s,
                     len(client.action_log), failure_message, records, dict(client.time_breakdown),
                     time.monotonic() - started_at)


def run_strategy(client: ObservationClient, mixed: bool, force_fallback: bool = False,
                 strategy: str = "b") -> RunResult:
    """Run Strategy B by default; Strategy A remains available as a rollback path."""
    normalized = strategy.lower()
    if normalized == "a":
        return _run_strategy_a(client, mixed, force_fallback)
    if normalized == "b":
        return _run_strategy_b(client, mixed, force_fallback)
    raise ValueError("strategy must be 'a' or 'b'")
