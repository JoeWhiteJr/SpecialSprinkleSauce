"""Tests for streaming pipeline SSE endpoint."""

import json
import os

os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("USE_MOCK_DATA", "true")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def _parse_sse_events(response) -> list[dict]:
    """Parse SSE events from a streaming response."""
    events = []
    for line in response.iter_lines():
        if line.startswith("data: "):
            data = line[len("data: "):]
            events.append(json.loads(data))
    return events


def test_stream_returns_sse_content_type():
    """SSE endpoint returns text/event-stream content type."""
    client = TestClient(app)
    with client.stream("POST", "/api/pipeline/run-stream", json={"ticker": "NVDA"}) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]


def test_stream_first_and_last_events():
    """First event is pipeline_start, last is pipeline_complete."""
    client = TestClient(app)
    with client.stream("POST", "/api/pipeline/run-stream", json={"ticker": "NVDA"}) as response:
        events = _parse_sse_events(response)

    assert len(events) > 0
    assert events[0]["type"] == "pipeline_start"
    assert events[0]["ticker"] == "NVDA"
    assert events[-1]["type"] == "pipeline_complete"
    assert "result" in events[-1]


def test_stream_veto_path_emits_skipped():
    """XOM (VETO path) emits node_skipped for debate/jury nodes."""
    client = TestClient(app)
    with client.stream("POST", "/api/pipeline/run-stream", json={"ticker": "XOM"}) as response:
        events = _parse_sse_events(response)

    event_types = [e["type"] for e in events]
    assert "pipeline_start" in event_types
    assert "pipeline_complete" in event_types

    skipped_events = [e for e in events if e["type"] == "node_skipped"]
    skipped_nodes = {e["node"] for e in skipped_events}

    # XOM is vetoed — bull, bear, debate, jury_spawn, jury_aggregate, risk, pre_trade should be skipped
    assert "bull_researcher" in skipped_nodes
    assert "bear_researcher" in skipped_nodes
    assert "debate" in skipped_nodes
    assert "jury_spawn" in skipped_nodes
    assert "jury_aggregate" in skipped_nodes


def test_stream_agreement_path_skips_jury():
    """NVDA (agreement path) skips jury nodes."""
    client = TestClient(app)
    with client.stream("POST", "/api/pipeline/run-stream", json={"ticker": "NVDA"}) as response:
        events = _parse_sse_events(response)

    skipped_events = [e for e in events if e["type"] == "node_skipped"]
    skipped_nodes = {e["node"] for e in skipped_events}

    # NVDA has debate agreement — jury nodes should be skipped
    assert "jury_spawn" in skipped_nodes
    assert "jury_aggregate" in skipped_nodes

    # But debate should NOT be skipped (it was executed)
    completed_nodes = {e["node"] for e in events if e["type"] == "node_complete"}
    assert "debate" in completed_nodes
