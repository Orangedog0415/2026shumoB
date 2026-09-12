from __future__ import annotations

import json
import hashlib
import math
import random
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

from .geometry import distance, dot
from .models import ClearObservation, MeasureObservation, Point


@dataclass
class SourceSpec:
    channel: int
    position: Point
    radius_m: float
    kind: str = "O"
    direction_deg: float = 0.0


ERROR_MODELS = frozenset({"sin", "uniform", "plus_one", "minus_one", "pm_one", "zero"})


class _SimulatorCore:
    """Truth-bearing component. It is never passed to strategy code."""

    def __init__(self, sources: list[SourceSpec], error_salt: int = 0,
                 error_model: str = "sin") -> None:
        if error_model not in ERROR_MODELS:
            raise ValueError(f"unsupported direction-error model: {error_model}")
        self.__sources = {
            s.channel: {
                "position": s.position,
                "radius": s.radius_m,
                "kind": s.kind,
                "direction": math.radians(s.direction_deg),
                "cleared": False,
            }
            for s in sources
        }
        self.position: Point = (0.0, 0.0)
        self.channel = 1
        self.virtual_time_s = 0.0
        self.entered = False
        self.exited = False
        self.error_salt = error_salt
        self.error_model = error_model
        self.breakdown = {"movement_s": 0.0, "measure_s": 0.0, "switch_s": 0.0, "clear_s": 0.0}

    def _direction_error(self, p: Point, channel: int) -> float:
        if self.error_model == "zero":
            return 0.0
        if self.error_model == "plus_one":
            return 1.0
        if self.error_model == "minus_one":
            return -1.0
        if self.error_model == "sin":
            return math.sin(0.007 * p[0] + 0.011 * p[1] + channel * 1.7 + self.error_salt)

        # A stable digest makes the same measurement repeatable across Python
        # processes, unlike the randomized built-in hash().
        key = f"{p[0]:.9f}|{p[1]:.9f}|{channel}|{self.error_salt}".encode("ascii")
        unit = int.from_bytes(hashlib.sha256(key).digest()[:8], "big") / (2**64 - 1)
        if self.error_model == "pm_one":
            return 1.0 if unit >= 0.5 else -1.0
        return 2.0 * unit - 1.0

    def enter(self) -> dict[str, Any]:
        if self.entered or self.exited:
            return self._base(False)
        self.entered = True
        return {**self._base(True), "max_virtual_duration_s": 360000,
                "max_real_duration_s": 1200, "remaining_real_duration_s": 1200}

    def _base(self, accepted: bool) -> dict[str, Any]:
        return {"accepted": accepted, "real_timestamp_ms": int(time.time() * 1000),
                "virtual_time_s": self.virtual_time_s if accepted else 0}

    def _move(self, p: Point) -> None:
        dt = distance(self.position, p) / 5
        self.virtual_time_s += dt
        self.breakdown["movement_s"] += dt
        self.position = p

    def measure(self, p: Point, channel: int) -> dict[str, Any]:
        if not self.entered or self.exited:
            return self._base(False)
        self._move(p)
        switch = float(channel != self.channel)
        self.channel = channel
        self.virtual_time_s += 5 + switch
        self.breakdown["measure_s"] += 5
        self.breakdown["switch_s"] += switch
        source = self.__sources.get(channel)
        result: dict[str, Any] = {**self._base(True), "measure_result": "no_signal"}
        if source is None or source["cleared"]:
            return result
        d = distance(p, source["position"])
        direction = source["direction"]
        forward = (math.cos(direction), math.sin(direction))
        covered = source["kind"] == "O" or dot((p[0] - source["position"][0], p[1] - source["position"][1]), forward) >= -1e-10
        if d > source["radius"] or not covered:
            return result
        if d <= 5:
            result["measure_result"] = "near"
            return result
        error = self._direction_error(p, channel)
        bearing = math.degrees(math.atan2(source["position"][1] - p[1], source["position"][0] - p[0]))
        result.update(measure_result="direction", svd_deg=round((bearing + error) % 360, 2) % 360)
        return result

    def clear(self, p: Point, channel: int) -> dict[str, Any]:
        if not self.entered or self.exited:
            return self._base(False)
        self._move(p)
        source = self.__sources.get(channel)
        success = source is not None and not source["cleared"] and distance(p, source["position"]) <= 20
        dt = 5.0 if success else 3.0
        self.virtual_time_s += dt
        self.breakdown["clear_s"] += dt
        if success:
            source["cleared"] = True
        return {**self._base(True), "clear_result": "success" if success else "no_target_in_range"}

    def exit(self) -> dict[str, Any]:
        if not self.entered or self.exited:
            return self._base(False)
        self.exited = True
        return {**self._base(True), "exit_reason": "user_exit"}

    def inspect(self) -> dict[str, Any]:
        return {"source_count": len(self.__sources),
                "cleared_count": sum(bool(s["cleared"]) for s in self.__sources.values()),
                "all_cleared": all(bool(s["cleared"]) for s in self.__sources.values())}


class LocalObservationClient:
    """Observation-only facade used by the strategy."""

    def __init__(self, core: _SimulatorCore) -> None:
        self.__core = core
        self.position: Point = (0.0, 0.0)
        self.current_channel = 1
        self.virtual_time_s = 0.0
        self.time_breakdown = core.breakdown
        self.action_log: list[dict[str, Any]] = []
        self._entered = False
        self._last_breakdown = dict(core.breakdown)

    @property
    def has_pending_action(self) -> bool:
        return False

    def _record(self, path: str, p: Point | None, ch: int | None, response: dict[str, Any]) -> None:
        components = {k: self.time_breakdown[k] - self._last_breakdown[k] for k in self.time_breakdown}
        self._last_breakdown = dict(self.time_breakdown)
        self.action_log.append({"sequence": len(self.action_log) + 1,
                                "request_id": f"offline-{len(self.action_log) + 1}",
                                "path": path, "position": p,
                                "channel": ch, "response": response,
                                "http_status": None, "sent_monotonic": None, "received_monotonic": None,
                                "virtual_time_components": components,
                                "committed_position": self.position,
                                "committed_measure_channel": self.current_channel})

    def enter(self) -> dict[str, Any]:
        r = self.__core.enter()
        self._entered = r["accepted"]
        self._record("/enter", None, None, r)
        return r

    def measure(self, position: Point, channel: int) -> MeasureObservation:
        r = self.__core.measure(position, channel)
        if not r["accepted"]:
            raise RuntimeError("local simulator rejected measure")
        self.position, self.current_channel, self.virtual_time_s = position, channel, r["virtual_time_s"]
        self._record("/measure", position, channel, r)
        return MeasureObservation(r["measure_result"], r.get("svd_deg"), r["virtual_time_s"])

    def clear(self, position: Point, channel: int) -> ClearObservation:
        r = self.__core.clear(position, channel)
        if not r["accepted"]:
            raise RuntimeError("local simulator rejected clear")
        self.position, self.virtual_time_s = position, r["virtual_time_s"]
        self._record("/clear", position, channel, r)
        return ClearObservation(r["clear_result"], r["virtual_time_s"])

    def exit(self) -> dict[str, Any]:
        r = self.__core.exit()
        self._record("/exit", None, None, r)
        return r


class ScenarioInspector:
    def __init__(self, callback: Callable[[], dict[str, Any]]) -> None:
        self.__callback = callback

    def summary(self) -> dict[str, Any]:
        return self.__callback()


def random_sources(seed: int, count: int, mixed: bool) -> list[SourceSpec]:
    if count not in (10, 13, 16):
        raise ValueError("offline count must be 10, 13, or 16")
    rng = random.Random(seed)
    sources: list[SourceSpec] = []
    for channel in rng.sample(range(1, 21), count):
        angle = rng.random() * 2 * math.pi
        radius = 1800 * math.sqrt(rng.random())
        sources.append(SourceSpec(channel, (radius * math.cos(angle), radius * math.sin(angle)),
                                  rng.uniform(1000, 1500), "D" if mixed and rng.random() < 0.65 else "O",
                                  math.degrees(rng.random() * 2 * math.pi)))
    return sources


def make_local_client(sources: list[SourceSpec], error_salt: int = 0,
                      error_model: str = "sin") -> tuple[LocalObservationClient, ScenarioInspector]:
    core = _SimulatorCore(sources, error_salt, error_model)
    return LocalObservationClient(core), ScenarioInspector(core.inspect)


def _duplicates_rejected(text: str) -> dict[str, Any]:
    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise ValueError("duplicate JSON key")
            out[key] = value
        return out
    value = json.loads(text, object_pairs_hook=hook)
    if not isinstance(value, dict):
        raise ValueError("request must be an object")
    return value


class LocalHTTPService:
    """Attachment-2 compatible local HTTP service with idempotency support."""

    def __init__(self, sources: list[SourceSpec], robot_id: str = "offline-team") -> None:
        self.core = _SimulatorCore(sources)
        self.robot_id = robot_id
        self.cache: dict[str, tuple[str, bytes, int, dict[str, Any]]] = {}
        self.drop_after_execute_ids: set[str] = set()
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "LocalHTTPService":
        service = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_: Any) -> None:
                return

            def _write(self, status: int, payload: dict[str, Any]) -> None:
                body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self) -> None:  # noqa: N802
                if self.path not in {"/enter", "/measure", "/clear", "/exit"}:
                    self._write(404, service.core._base(False)); return
                content_type = self.headers.get("Content-Type", "")
                content_encoding = self.headers.get("Content-Encoding", "identity")
                if content_type not in {"application/json", "application/json; charset=utf-8"} or content_encoding not in {"", "identity"}:
                    self._write(415, service.core._base(False)); return
                try:
                    size = int(self.headers.get("Content-Length", "0"))
                    if size > 65536:
                        self._write(413, service.core._base(False)); return
                    raw = self.rfile.read(size)
                    if raw.startswith(b"\xef\xbb\xbf"):
                        raise ValueError("BOM is forbidden")
                    data = _duplicates_rejected(raw.decode("utf-8"))
                except Exception:
                    self._write(400, service.core._base(False)); return
                rid = data.get("request_id")
                if isinstance(rid, str) and rid in service.cache:
                    old_path, old_raw, status, response = service.cache[rid]
                    if old_path != self.path or old_raw != raw:
                        self._write(409, service.core._base(False))
                    else:
                        self._write(status, response)
                    return
                common = {"arena_id", "robot_id", "request_id"}
                allowed = common if self.path in {"/enter", "/exit"} else common | {"position", "channel"}
                if set(data) != allowed or data.get("arena_id") != "default" or data.get("robot_id") != service.robot_id:
                    self._write(200, service.core._base(False)); return
                if not isinstance(rid, str) or not 1 <= len(rid.encode("utf-8")) <= 128:
                    self._write(400, service.core._base(False)); return
                if self.path in {"/measure", "/clear"}:
                    p, ch = data.get("position"), data.get("channel")
                    valid_p = isinstance(p, dict) and set(p) == {"x", "y"} and all(
                        isinstance(p.get(k), (int, float)) and not isinstance(p.get(k), bool)
                        and math.isfinite(p[k]) and abs(p[k]) <= 2_000_000 for k in ("x", "y"))
                    if not valid_p or not isinstance(ch, (int, float)) or isinstance(ch, bool) or int(ch) != ch or not 1 <= ch <= 20:
                        self._write(400, service.core._base(False)); return
                    point, channel = (float(p["x"]), float(p["y"])), int(ch)
                    response = service.core.measure(point, channel) if self.path == "/measure" else service.core.clear(point, channel)
                elif self.path == "/enter":
                    response = service.core.enter()
                else:
                    response = service.core.exit()
                service.cache[rid] = (self.path, raw, 200, response)
                if rid in service.drop_after_execute_ids:
                    service.drop_after_execute_ids.remove(rid)
                    self.close_connection = True
                    return
                self._write(200, response)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    @property
    def base_url(self) -> str:
        assert self._server is not None
        return f"http://127.0.0.1:{self._server.server_port}"

    def __exit__(self, *_: Any) -> None:
        assert self._server is not None and self._thread is not None
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)
