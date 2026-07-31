"""Tests for app.api.main — routes and SSE framing, with Claude mocked out."""

import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from src import db, store


@pytest.fixture(autouse=True)
def _patch_db_path(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")


@pytest.fixture(autouse=True)
def _mock_sensei(monkeypatch):
    """Replace Claude with three deterministic tokens."""
    async def fake_stream(register, payload, memory, question=None):
        for chunk in ("You held the pace. ", "Not a failure. ", "Rest tomorrow."):
            yield chunk

    from app.api import main as api_main
    monkeypatch.setattr(api_main, "stream_voice", fake_stream)


@pytest.fixture
def client():
    from app.api.main import app
    return TestClient(app)


@pytest.fixture
def seeded():
    """Twelve runs over four weeks, the most recent this morning."""
    now = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    acts = []
    for i in range(12):
        start = now - timedelta(days=i * 2)
        acts.append({
            "activityId": 5000 + i,
            "activityName": "Run",
            "startTimeLocal": start.strftime("%Y-%m-%d %H:%M:%S"),
            "distance": 6000.0, "duration": 2220.0, "calories": 400.0,
            "averageHR": 148.0, "maxHR": 165.0, "averageSpeed": 2.7,
            "elevationGain": 20.0,
            "averageRunningCadenceInStepsPerMinute": 170.0,
        })
    db.save_activities(acts)
    return acts


@pytest.fixture
def seeded_no_hr():
    """Same shape as `seeded`, but with no heart-rate data at all.

    This is what the real database looks like: avg_hr is null for every row,
    so pandas types the column as object full of None rather than float NaN.
    Guards written for NaN silently fail here.
    """
    now = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    acts = []
    for i in range(12):
        start = now - timedelta(days=i * 2)
        acts.append({
            "activityId": 7000 + i,
            "activityName": "Run",
            "startTimeLocal": start.strftime("%Y-%m-%d %H:%M:%S"),
            "distance": 6000.0, "duration": 2220.0, "calories": 400.0,
            "averageHR": None, "maxHR": None, "averageSpeed": 2.7,
            "elevationGain": 20.0,
            "averageRunningCadenceInStepsPerMinute": 170.0,
        })
    db.save_activities(acts)
    return acts


def _events(response) -> list[tuple[str, dict]]:
    """Parse an SSE body into (event_name, payload) pairs."""
    out, name = [], None
    for line in response.text.splitlines():
        if line.startswith("event: "):
            name = line[7:]
        elif line.startswith("data: ") and name:
            out.append((name, json.loads(line[6:])))
    return out


class TestToday:
    def test_shape(self, client, seeded):
        r = client.get("/api/today")
        assert r.status_code == 200
        body = r.json()
        assert "prescription" in body
        assert "streak" in body
        assert "week" in body
        assert len(body["last_7_days"]) == 7

    def test_works_with_empty_database(self, client):
        r = client.get("/api/today")
        assert r.status_code == 200
        assert r.json()["prescription"]["session_type"] in (
            "rest", "easy", "long", "tempo")

    def test_works_when_no_activity_has_heart_rate(self, client, seeded_no_hr):
        """The real database has avg_hr null on every row — object dtype, not NaN."""
        r = client.get("/api/today")
        assert r.status_code == 200


class TestSession:
    def test_returns_prescription_detail(self, client, seeded):
        r = client.get("/api/session")
        assert r.status_code == 200
        assert "session_type" in r.json()


class TestBrief:
    def test_streams_prescription_then_tokens_then_done(self, client, seeded):
        r = client.get("/api/brief")
        assert r.status_code == 200
        events = _events(r)
        assert events[0][0] == "prescription"
        assert [n for n, _ in events].count("token") == 3
        assert events[-1][0] == "done"

    def test_second_call_replays_without_calling_claude(self, client, seeded, monkeypatch):
        client.get("/api/brief")

        async def explode(*a, **k):
            raise AssertionError("Claude called on replay")
            yield  # pragma: no cover

        from app.api import main as api_main
        monkeypatch.setattr(api_main, "stream_voice", explode)

        events = _events(client.get("/api/brief"))
        assert events[-1][0] == "done"
        assert "".join(p["t"] for n, p in events if n == "token")


class TestDebrief:
    def test_streams_verdict_then_tokens_then_done(self, client, seeded):
        events = _events(client.get("/api/debrief/latest"))
        assert events[0][0] == "verdict"
        assert events[-1][0] == "done"
        assert events[-1][1]["debrief_id"] > 0

    def test_persists_instruction(self, client, seeded):
        client.get("/api/debrief/latest")
        assert store.recent_instructions() == ["Rest tomorrow."]

    def test_replay_makes_no_second_call(self, client, seeded, monkeypatch):
        first = _events(client.get("/api/debrief/latest"))[-1][1]["debrief_id"]

        async def explode(*a, **k):
            raise AssertionError("Claude called on replay")
            yield  # pragma: no cover

        from app.api import main as api_main
        monkeypatch.setattr(api_main, "stream_voice", explode)

        second = _events(client.get("/api/debrief/latest"))[-1][1]["debrief_id"]
        assert first == second

    def test_empty_database_is_idle_state(self, client):
        events = _events(client.get("/api/debrief/latest"))
        assert events[0][1]["state"] == "no_new_run"

    def test_judges_a_run_with_no_heart_rate(self, client, seeded_no_hr):
        events = _events(client.get("/api/debrief/latest"))
        assert events[0][0] == "verdict"
        assert events[0][1]["run"]["avg_hr"] is None
        assert events[-1][0] == "done"


class TestFeelAndReply:
    def test_feel_once(self, client, seeded):
        did = _events(client.get("/api/debrief/latest"))[-1][1]["debrief_id"]
        assert client.post(f"/api/debrief/{did}/feel", json={"feel": "good"}).status_code == 200
        assert client.post(f"/api/debrief/{did}/feel", json={"feel": "flat"}).status_code == 409

    def test_feel_rejects_unknown_value(self, client, seeded):
        did = _events(client.get("/api/debrief/latest"))[-1][1]["debrief_id"]
        r = client.post(f"/api/debrief/{did}/feel", json={"feel": "amazing"})
        assert r.status_code == 422

    def test_reply_once(self, client, seeded):
        did = _events(client.get("/api/debrief/latest"))[-1][1]["debrief_id"]
        r = client.post(f"/api/debrief/{did}/reply", json={"question": "Why?"})
        assert r.status_code == 200
        assert [n for n, _ in _events(r)].count("token") == 3
        again = client.post(f"/api/debrief/{did}/reply", json={"question": "Again?"})
        assert again.status_code == 409

    def test_reply_unknown_debrief_is_404(self, client):
        assert client.post("/api/debrief/999/reply", json={"question": "?"}).status_code == 404
