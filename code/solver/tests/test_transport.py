import json
from pathlib import Path

import pytest
import requests

from bsolver.models import BudgetExceeded, CommunicationFailure, ProtocolFailure, Termination
from bsolver.simulator import LocalHTTPService, SourceSpec, random_sources
from bsolver.strategy import run_strategy
from bsolver.transport import OfficialHttpClient


def test_http_idempotent_replay_after_response_loss(tmp_path):
    with LocalHTTPService([SourceSpec(3, (300, 400), 1000)]) as service:
        client = OfficialHttpClient(service.base_url, "offline-team", tmp_path, timeout_s=1)
        client._session_id = "drop"
        service.drop_after_execute_ids.add("drop-1")
        response = client.enter()
        assert response["accepted"] is True
        assert len(service.cache) == 1
        assert not client.has_pending_action


def test_http_measure_clear_measure_is_215_seconds(tmp_path):
    with LocalHTTPService([SourceSpec(3, (300, 400), 1000)]) as service:
        client = OfficialHttpClient(service.base_url, "offline-team", tmp_path)
        client.enter()
        client.measure((0, 0), 1)
        client.clear((300, 400), 3)
        client.measure((0, 0), 1)
        assert client.virtual_time_s == 215
        assert client.current_channel == 1
        assert client.time_breakdown["switch_s"] == 0


def test_same_id_different_content_conflicts():
    with LocalHTTPService([]) as service:
        base = {"arena_id": "default", "robot_id": "offline-team", "request_id": "same"}
        assert requests.post(service.base_url + "/enter", json=base).status_code == 200
        changed = {**base, "position": {"x": 0, "y": 0}, "channel": 1}
        assert requests.post(service.base_url + "/measure", json=changed).status_code == 409


def test_unknown_field_is_accepted_false_and_does_not_consume_id():
    with LocalHTTPService([]) as service:
        bad = {"arena_id": "default", "robot_id": "offline-team", "request_id": "x", "extra": 1}
        r = requests.post(service.base_url + "/enter", json=bad)
        assert r.status_code == 200 and r.json()["accepted"] is False
        good = {k: bad[k] for k in ("arena_id", "robot_id", "request_id")}
        assert requests.post(service.base_url + "/enter", json=good).json()["accepted"] is True


def test_rejected_client_clears_confirmed_pending_request(tmp_path):
    with LocalHTTPService([]) as service:
        client = OfficialHttpClient(service.base_url, "wrong-team", tmp_path)
        with pytest.raises(ProtocolFailure):
            client.enter()
        assert not client.has_pending_action


def test_real_budget_is_enforced_after_enter(tmp_path):
    class Clock:
        value = 100.0
        def __call__(self): return self.value

    clock = Clock()
    with LocalHTTPService([]) as service:
        client = OfficialHttpClient(service.base_url, "offline-team", tmp_path, clock=clock)
        client.enter()
        clock.value = 1296.0
        with pytest.raises(BudgetExceeded):
            client.measure((0, 0), 1)
        assert not client.has_pending_action


def test_server_rejects_bom_invalid_coordinates_and_channel():
    with LocalHTTPService([]) as service:
        url = service.base_url + "/measure"
        headers = {"Content-Type": "application/json"}
        body = b"\xef\xbb\xbf" + json.dumps({"arena_id": "default", "robot_id": "offline-team", "request_id": "b",
                                                "position": {"x": 0, "y": 0}, "channel": 1}).encode()
        assert requests.post(url, data=body, headers=headers).status_code == 400
        for point, channel in [({"x": 2_000_001, "y": 0}, 1), ({"x": 0, "y": 0}, 1.5)]:
            payload = {"arena_id": "default", "robot_id": "offline-team", "request_id": str(point) + str(channel),
                       "position": point, "channel": channel}
            assert requests.post(url, json=payload).status_code == 400


class _Response:
    def __init__(self, status, text):
        self.status_code, self.text = status, text


class _SequenceSession:
    def __init__(self, sequence):
        self.sequence = list(sequence)
        self.bodies = []

    def post(self, _url, data, headers, timeout):
        self.bodies.append(data)
        item = self.sequence.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.mark.parametrize("first", [_Response(200, "not-json"), _Response(500, "{}"), _Response(429, "{}"), requests.Timeout("late")])
def test_unknown_responses_retry_identical_body(tmp_path, first):
    accepted = _Response(200, json.dumps({"accepted": True, "real_timestamp_ms": 0, "virtual_time_s": 0,
                                          "max_virtual_duration_s": 360000, "max_real_duration_s": 1200,
                                          "remaining_real_duration_s": 1200}))
    session = _SequenceSession([first, accepted])
    client = OfficialHttpClient("http://unused", "team", tmp_path, max_retries=1,
                                session=session, sleeper=lambda _x: None)
    assert client.enter()["accepted"] is True
    assert session.bodies[0] == session.bodies[1]


def test_unconfirmed_request_blocks_exit(tmp_path):
    session = _SequenceSession([requests.ConnectionError("closed")])
    client = OfficialHttpClient("http://unused", "team", tmp_path, max_retries=0, session=session)
    with pytest.raises(CommunicationFailure):
        client.enter()
    assert client.has_pending_action
    with pytest.raises(ProtocolFailure):
        client.exit()


def test_complete_strategy_over_local_http_service(tmp_path):
    sources = random_sources(761, 10, False)
    with LocalHTTPService(sources) as service:
        client = OfficialHttpClient(service.base_url, "offline-team", tmp_path, timeout_s=1)
        result = run_strategy(client, mixed=False)
        assert result.termination == Termination.COMPLETED
        assert result.cleared_count == 10
        assert service.core.inspect()["all_cleared"]
