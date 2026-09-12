from __future__ import annotations

import json
import math
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable

import requests

from .geometry import distance
from .models import BudgetExceeded, ClearObservation, CommunicationFailure, MeasureObservation, Point, ProtocolFailure


def _strict_json(text: str) -> dict[str, Any]:
    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise ValueError(f"duplicate response field: {key}")
            out[key] = value
        return out
    data = json.loads(text, object_pairs_hook=hook)
    if not isinstance(data, dict):
        raise ValueError("response is not an object")
    return data


class OfficialHttpClient:
    def __init__(self, base_url: str, robot_id: str, journal_dir: Path,
                 timeout_s: float = 5.0, max_retries: int = 3, finish_reserve_s: float = 5.0,
                 session: requests.Session | None = None,
                 clock: Callable[[], float] = time.monotonic,
                 sleeper: Callable[[float], None] = time.sleep) -> None:
        if not robot_id:
            raise ValueError("official mode requires robot_id")
        self.base_url = base_url.rstrip("/")
        self.__robot_id = robot_id
        self.journal_dir = journal_dir
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        self.pending_file = journal_dir / "pending_request.json"
        self.timeout_s, self.max_retries, self.finish_reserve_s = timeout_s, max_retries, finish_reserve_s
        self.session = session or requests.Session()
        self.clock, self.sleeper = clock, sleeper
        self.position: Point = (0.0, 0.0)
        self.current_channel = 1
        self.virtual_time_s = 0.0
        self.time_breakdown = {"movement_s": 0.0, "measure_s": 0.0, "switch_s": 0.0, "clear_s": 0.0,
                               "request_latency_s": 0.0, "retry_wait_s": 0.0}
        self.action_log: list[dict[str, Any]] = []
        self.transport_log: list[dict[str, Any]] = []
        self.warnings: list[str] = []
        self._response_latencies: list[float] = []
        self._lock = threading.Lock()
        self._session_id = str(uuid.uuid4())
        self._counter = 0
        self._deadline: float | None = None

    @property
    def has_pending_action(self) -> bool:
        return self.pending_file.exists()

    def _id(self) -> str:
        self._counter += 1
        return f"{self._session_id}-{self._counter}"

    def _base(self) -> dict[str, Any]:
        return {"arena_id": "default", "robot_id": self.__robot_id, "request_id": self._id()}

    def _validate_action(self, position: Point, channel: int) -> None:
        if isinstance(channel, bool) or not isinstance(channel, int) or not 1 <= channel <= 20:
            raise ValueError("channel must be an integer in 1..20")
        if len(position) != 2 or not all(math.isfinite(v) and abs(v) <= 2_000_000 for v in position):
            raise ValueError("coordinates must be finite and within +/-2000000")

    def _write_pending(self, path: str, payload: dict[str, Any], body: bytes) -> None:
        public = dict(payload)
        public["robot_id"] = "<redacted>"
        record = {"path": path, "payload": payload, "public_payload": public,
                  "body_sha256": __import__("hashlib").sha256(body).hexdigest()}
        tmp = self.pending_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.pending_file)

    def _remaining(self) -> float:
        return math.inf if self._deadline is None else self._deadline - self.clock()

    def _send(self, path: str, payload: dict[str, Any], enter_sent_at: float | None = None) -> dict[str, Any]:
        if not self._lock.acquire(blocking=False):
            raise ProtocolFailure("another action is pending")
        try:
            body = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
            if self._remaining() <= self.finish_reserve_s:
                raise BudgetExceeded("real-time finish reserve reached before sending action")
            self._write_pending(path, payload, body)
            last_error = "unknown response"
            for attempt in range(self.max_retries + 1):
                remaining = self._remaining()
                if remaining <= self.finish_reserve_s:
                    raise BudgetExceeded("real-time finish reserve reached")
                timeout = self.timeout_s if math.isinf(remaining) else min(self.timeout_s, max(0.001, remaining - self.finish_reserve_s))
                started = self.clock()
                try:
                    response = self.session.post(self.base_url + path, data=body,
                                                 headers={"Content-Type": "application/json; charset=utf-8"}, timeout=timeout)
                    received = self.clock()
                    latency = received - started
                    self.time_breakdown["request_latency_s"] += latency
                    self._response_latencies.append(latency)
                    if len(self._response_latencies) == 30:
                        mean = sum(self._response_latencies) / 30
                        self.warnings.append(
                            f"first-30 mean request latency={mean:.6f}s; "
                            f"4454-action rough real-time estimate={4454 * mean:.3f}s"
                        )
                    self.transport_log.append({"request_id": payload["request_id"], "path": path,
                                               "attempt": attempt, "sent_monotonic": started,
                                               "received_monotonic": received,
                                               "http_status": response.status_code,
                                               "raw_response": response.text})
                    if response.status_code in {400, 404, 405, 409, 413, 415}:
                        self.pending_file.unlink(missing_ok=True)
                        raise ProtocolFailure(f"HTTP {response.status_code}: {response.text[:500]}")
                    if response.status_code not in {200, 429, 500}:
                        raise CommunicationFailure(f"unexpected HTTP {response.status_code}")
                    if response.status_code == 429:
                        last_error, wait = "HTTP 429", 1.0
                    elif response.status_code == 500:
                        last_error, wait = "HTTP 500", (0.2, 0.5, 1.0)[min(attempt, 2)]
                    else:
                        try:
                            data = _strict_json(response.text)
                        except Exception as exc:
                            last_error, wait = f"non-JSON response: {exc}", (0.2, 0.5, 1.0)[min(attempt, 2)]
                        else:
                            if data.get("accepted") is not True:
                                self.pending_file.unlink(missing_ok=True)
                                raise ProtocolFailure("HTTP 200 with accepted=false")
                            self._validate_response(path, data)
                            self._commit(path, payload, data, enter_sent_at,
                                         response.status_code, started, received, attempt)
                            self.pending_file.unlink(missing_ok=True)
                            return data
                except (requests.Timeout, requests.ConnectionError) as exc:
                    failed_at = self.clock()
                    self.time_breakdown["request_latency_s"] += failed_at - started
                    self.transport_log.append({"request_id": payload["request_id"], "path": path,
                                               "attempt": attempt, "sent_monotonic": started,
                                               "received_monotonic": failed_at, "http_status": None,
                                               "error": type(exc).__name__, "detail": str(exc)})
                    last_error, wait = str(exc), (0.2, 0.5, 1.0)[min(attempt, 2)]
                if attempt == self.max_retries:
                    break
                if self._remaining() <= self.finish_reserve_s + wait:
                    raise BudgetExceeded("not enough real time for retry")
                self.sleeper(wait)
                self.time_breakdown["retry_wait_s"] += wait
            raise CommunicationFailure(f"unconfirmed action after retries: {last_error}")
        finally:
            self._lock.release()

    def _validate_response(self, path: str, data: dict[str, Any]) -> None:
        for key in ("real_timestamp_ms", "virtual_time_s"):
            if not isinstance(data.get(key), (int, float)):
                raise CommunicationFailure(f"missing numeric {key}")
        if path == "/measure":
            kind = data.get("measure_result")
            if kind not in {"no_signal", "near", "direction"}:
                raise CommunicationFailure("invalid measure_result")
            if kind == "direction" and not isinstance(data.get("svd_deg"), (int, float)):
                raise CommunicationFailure("direction lacks svd_deg")
        if path == "/clear" and data.get("clear_result") not in {"success", "no_target_in_range"}:
            raise CommunicationFailure("invalid clear_result")

    def _commit(self, path: str, payload: dict[str, Any], data: dict[str, Any], enter_sent_at: float | None,
                http_status: int, sent_monotonic: float, received_monotonic: float,
                retry_index: int) -> None:
        old_position, old_channel, old_virtual = self.position, self.current_channel, self.virtual_time_s
        components = {"movement_s": 0.0, "measure_s": 0.0, "switch_s": 0.0, "clear_s": 0.0}
        if path == "/enter":
            assert enter_sent_at is not None
            self._deadline = enter_sent_at + float(data["remaining_real_duration_s"])
        elif path in {"/measure", "/clear"}:
            p = payload["position"]
            new_position = (float(p["x"]), float(p["y"]))
            move = distance(old_position, new_position) / 5
            self.time_breakdown["movement_s"] += move
            components["movement_s"] = move
            if path == "/measure":
                switch = float(payload["channel"] != old_channel)
                self.time_breakdown["switch_s"] += switch
                self.time_breakdown["measure_s"] += 5
                components["switch_s"] = switch
                components["measure_s"] = 5.0
                expected = old_virtual + move + switch + 5
                self.current_channel = int(payload["channel"])
            else:
                clear_time = 5 if data["clear_result"] == "success" else 3
                self.time_breakdown["clear_s"] += clear_time
                components["clear_s"] = float(clear_time)
                expected = old_virtual + move + clear_time
            tolerance = max(0.001, (len(self.action_log) + 1) * 1e-6)
            if abs(float(data["virtual_time_s"]) - expected) > tolerance:
                self.warnings.append(f"virtual time mismatch: server={data['virtual_time_s']} local={expected}")
            self.position = new_position
        self.virtual_time_s = float(data["virtual_time_s"])
        public_payload = dict(payload)
        public_payload["robot_id"] = "<redacted>"
        self.action_log.append({"sequence": len(self.action_log) + 1,
                                "request_id": payload["request_id"], "path": path,
                                "request": public_payload, "response": data,
                                "http_status": http_status,
                                "sent_monotonic": sent_monotonic,
                                "received_monotonic": received_monotonic,
                                "retry_index": retry_index,
                                "virtual_time_components": components,
                                "committed_position": self.position,
                                "committed_measure_channel": self.current_channel,
                                "warnings": list(self.warnings)})

    def enter(self) -> dict[str, Any]:
        sent = self.clock()
        return self._send("/enter", self._base(), sent)

    def measure(self, position: Point, channel: int) -> MeasureObservation:
        self._validate_action(position, channel)
        payload = {**self._base(), "position": {"x": position[0], "y": position[1]}, "channel": channel}
        r = self._send("/measure", payload)
        return MeasureObservation(r["measure_result"], r.get("svd_deg"), r["virtual_time_s"])

    def clear(self, position: Point, channel: int) -> ClearObservation:
        self._validate_action(position, channel)
        payload = {**self._base(), "position": {"x": position[0], "y": position[1]}, "channel": channel}
        r = self._send("/clear", payload)
        return ClearObservation(r["clear_result"], r["virtual_time_s"])

    def exit(self) -> dict[str, Any]:
        if self.has_pending_action:
            raise ProtocolFailure("cannot exit while an action is unconfirmed")
        return self._send("/exit", self._base())
