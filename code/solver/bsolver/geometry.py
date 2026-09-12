from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal, localcontext
from itertools import combinations
from typing import Iterable

from .models import Point, RegionType

LENGTH_EPS = 1e-7
DIRECTION_EPS = 1e-12
DELTA_RAD = math.radians(1.005)


def dot(a: Point, b: Point) -> float:
    return a[0] * b[0] + a[1] * b[1]


def cross(a: Point, b: Point) -> float:
    return a[0] * b[1] - a[1] * b[0]


def sub(a: Point, b: Point) -> Point:
    return a[0] - b[0], a[1] - b[1]


def distance(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


@dataclass(frozen=True)
class HalfPlane:
    normal: Point
    bound: float

    def __post_init__(self) -> None:
        n = math.hypot(*self.normal)
        if not math.isfinite(n) or n == 0 or not math.isfinite(self.bound):
            raise ValueError("half-plane must contain finite nonzero values")
        object.__setattr__(self, "normal", (self.normal[0] / n, self.normal[1] / n))
        object.__setattr__(self, "bound", self.bound / n)

    def contains(self, p: Point, eps: float = LENGTH_EPS) -> bool:
        return dot(self.normal, p) <= self.bound + eps


@dataclass
class RegionResult:
    region_type: RegionType
    vertices: list[Point]
    diameter: float | None
    diameter_endpoints: tuple[Point, Point] | None
    diameter_by_enumeration: float | None
    diameter_by_calipers: float | None
    diameter_circle_covers: bool | None
    diagnostic: str | None = None

    def to_dict(self) -> dict:
        return {
            "region_type": self.region_type.value,
            "vertices": self.vertices,
            "diameter": self.diameter,
            "diameter_endpoints": self.diameter_endpoints,
            "diameter_by_enumeration": self.diameter_by_enumeration,
            "diameter_by_calipers": self.diameter_by_calipers,
            "diameter_circle_covers": self.diameter_circle_covers,
            "diagnostic": self.diagnostic,
        }


def wedge_halfplanes(station: Point, bearing_deg: float, delta_rad: float = DELTA_RAD) -> list[HalfPlane]:
    theta = math.radians(bearing_deg % 360.0)
    lo, hi = theta - delta_rad, theta + delta_rad
    # (X-S).n(lo)>=0 and (X-S).n(hi)<=0, both converted to a.X<=b.
    n_lo = (math.sin(lo), -math.cos(lo))
    n_hi = (-math.sin(hi), math.cos(hi))
    return [HalfPlane(n_lo, dot(n_lo, station)), HalfPlane(n_hi, dot(n_hi, station))]


def _intersection(a: HalfPlane, b: HalfPlane) -> tuple[Point | None, bool]:
    det = cross(a.normal, b.normal)
    if abs(det) > DIRECTION_EPS:
        x = (a.bound * b.normal[1] - a.normal[1] * b.bound) / det
        y = (a.normal[0] * b.bound - a.bound * b.normal[0]) / det
        return (x, y), False
    with localcontext() as ctx:
        ctx.prec = 50
        ax, ay = map(lambda z: Decimal(str(z)), a.normal)
        bx, by = map(lambda z: Decimal(str(z)), b.normal)
        ab, bb = Decimal(str(a.bound)), Decimal(str(b.bound))
        exact_det = ax * by - ay * bx
        if exact_det == 0:
            return None, False
        x = (ab * by - ay * bb) / exact_det
        y = (ax * bb - ab * bx) / exact_det
        try:
            p = float(x), float(y)
        except (OverflowError, ValueError):
            return None, True
        return (p if all(math.isfinite(v) for v in p) else None), True


def _unique(points: Iterable[Point], eps: float = LENGTH_EPS) -> list[Point]:
    out: list[Point] = []
    for p in points:
        if not any(distance(p, q) <= eps for q in out):
            out.append(p)
    return out


def convex_hull(points: Iterable[Point]) -> list[Point]:
    pts = sorted(_unique(points))
    if len(pts) <= 1:
        return pts

    def turn(o: Point, a: Point, b: Point) -> float:
        return cross(sub(a, o), sub(b, o))

    lower: list[Point] = []
    for p in pts:
        while len(lower) >= 2 and turn(lower[-2], lower[-1], p) <= LENGTH_EPS:
            lower.pop()
        lower.append(p)
    upper: list[Point] = []
    for p in reversed(pts):
        while len(upper) >= 2 and turn(upper[-2], upper[-1], p) <= LENGTH_EPS:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def enumerate_diameter(poly: list[Point]) -> tuple[float, tuple[Point, Point] | None]:
    if not poly:
        return 0.0, None
    if len(poly) == 1:
        return 0.0, (poly[0], poly[0])
    pair = max(combinations(poly, 2), key=lambda ab: distance(*ab))
    return distance(*pair), pair


def rotating_calipers_diameter(poly: list[Point]) -> float:
    n = len(poly)
    if n < 3:
        return enumerate_diameter(poly)[0]
    best, j = 0.0, 1
    for i in range(n):
        ni = (i + 1) % n
        edge = sub(poly[ni], poly[i])
        while True:
            nj = (j + 1) % n
            cur = abs(cross(edge, sub(poly[j], poly[i])))
            nxt = abs(cross(edge, sub(poly[nj], poly[i])))
            if nxt > cur + 1e-9:
                j = nj
            else:
                break
        for k in {j, (j + 1) % n}:
            best = max(best, distance(poly[i], poly[k]), distance(poly[ni], poly[k]))
    return best


def _unbounded(planes: list[HalfPlane]) -> bool:
    if not planes:
        return True
    for hp in planes:
        tx, ty = -hp.normal[1], hp.normal[0]
        for d in ((tx, ty), (-tx, -ty)):
            if all(dot(q.normal, d) <= DIRECTION_EPS for q in planes):
                return True
    return False


def intersect_halfplanes(planes: list[HalfPlane]) -> RegionResult:
    if not planes:
        return RegionResult(RegionType.UNBOUNDED, [], math.inf, None, math.inf, math.inf, None)
    candidates: list[Point] = [(0.0, 0.0)]
    candidates.extend((hp.normal[0] * hp.bound, hp.normal[1] * hp.bound) for hp in planes)
    uncertain = False
    for a, b in combinations(planes, 2):
        p, delicate = _intersection(a, b)
        uncertain |= delicate
        if p is not None:
            candidates.append(p)
    feasible = _unique(p for p in candidates if all(h.contains(p) for h in planes))
    if not feasible:
        if uncertain:
            return RegionResult(RegionType.NUMERIC_UNCERTAIN, [], None, None, None, None, None,
                                "near-parallel boundaries prevent a stable empty-set classification")
        return RegionResult(RegionType.EMPTY, [], None, None, None, None, None)
    if _unbounded(planes):
        return RegionResult(RegionType.UNBOUNDED, [], math.inf, None, math.inf, math.inf, None,
                            "near-parallel boundary used Decimal review" if uncertain else None)
    vertices = convex_hull(
        p for a, b in combinations(planes, 2)
        for p, _ in [_intersection(a, b)]
        if p is not None and all(h.contains(p) for h in planes)
    )
    if not vertices:
        return RegionResult(RegionType.NUMERIC_UNCERTAIN, [], None, None, None, None, None,
                            "bounded feasible set has no stable boundary vertices")
    d_enum, pair = enumerate_diameter(vertices)
    d_cal = rotating_calipers_diameter(vertices)
    if abs(d_enum - d_cal) > max(LENGTH_EPS, d_enum * 1e-10):
        return RegionResult(RegionType.NUMERIC_UNCERTAIN, vertices, None, pair, d_enum, d_cal, None,
                            "diameter implementations disagree")
    kind = RegionType.POINT if len(vertices) == 1 else RegionType.SEGMENT if len(vertices) == 2 else RegionType.POLYGON
    assert pair is not None
    mid = ((pair[0][0] + pair[1][0]) / 2, (pair[0][1] + pair[1][1]) / 2)
    covers = max(distance(v, mid) for v in vertices) <= d_enum / 2 + LENGTH_EPS
    return RegionResult(kind, vertices, d_enum, pair, d_enum, d_cal, covers,
                        "near-parallel boundary used Decimal review" if uncertain else None)


def clip_polygon(poly: list[Point], hp: HalfPlane) -> list[Point]:
    if not poly:
        return []
    out: list[Point] = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        fa = dot(hp.normal, a) - hp.bound
        fb = dot(hp.normal, b) - hp.bound
        ina, inb = fa <= LENGTH_EPS, fb <= LENGTH_EPS
        if ina != inb:
            den = fa - fb
            if abs(den) > 1e-30:
                t = fa / den
                out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
        if inb:
            out.append(b)
    return _unique(out)


def outer_disk(center: Point, radius: float, sides: int = 64) -> list[Point]:
    if sides < 3 or radius <= 0:
        raise ValueError("invalid outer polygon")
    vertex_radius = radius / math.cos(math.pi / sides)
    return [
        (center[0] + vertex_radius * math.cos((2 * i + 1) * math.pi / sides),
         center[1] + vertex_radius * math.sin((2 * i + 1) * math.pi / sides))
        for i in range(sides)
    ]


def clip_with_wedge(poly: list[Point], station: Point, bearing_deg: float) -> list[Point]:
    for hp in wedge_halfplanes(station, bearing_deg):
        poly = clip_polygon(poly, hp)
    return poly


def clip_with_outer_disk(poly: list[Point], center: Point, radius: float, sides: int = 64) -> list[Point]:
    for i in range(sides):
        a = 2 * math.pi * i / sides
        n = (math.cos(a), math.sin(a))
        poly = clip_polygon(poly, HalfPlane(n, radius + dot(n, center)))
    return poly


def online_envelope(observations: list[tuple[Point, float]]) -> list[Point]:
    poly = outer_disk((0.0, 0.0), 1800.0)
    for station, bearing in observations:
        poly = clip_with_wedge(poly, station, bearing)
        poly = clip_with_outer_disk(poly, station, 1500.0)
    return poly


def polygon_radius(poly: list[Point], center: Point) -> float:
    return max((distance(v, center) for v in poly), default=0.0)


def vertex_average(poly: list[Point]) -> Point:
    if not poly:
        raise ValueError("empty polygon")
    return sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)


def polygon_diameter(poly: list[Point]) -> float:
    return enumerate_diameter(poly)[0]
