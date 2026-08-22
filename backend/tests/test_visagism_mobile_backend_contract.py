"""Contract tests for the backend pieces required by the future mobile visagism flow.

These tests intentionally avoid asserting the future Claude interpretation schema or
frontend behavior. They only lock the routes that are already part of the backend
contract: upload, photo triage, analysis start/result and fail-closed simulation.
"""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _route_map():
    return {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }


def test_mobile_visagism_required_routes_are_registered():
    routes = _route_map()

    expected = {
        ("POST", "/api/v1/photoshoots"),
        ("POST", "/api/v1/photoshoots/{photoshoot_id}/photos"),
        ("POST", "/api/v1/photos/{photo_id}/triage"),
        ("POST", "/api/v1/ai/analyze"),
        ("GET", "/api/v1/analyses/{analysis_id}"),
        ("GET", "/api/v1/analyses/{analysis_id}/visagism"),
        ("POST", "/api/v1/analyses/{analysis_id}/visagism/simulate"),
    }

    missing = expected - routes
    assert not missing, f"Missing mobile visagism backend routes: {sorted(missing)}"


def test_photo_triage_requires_authentication():
    response = client.post("/api/v1/photos/00000000-0000-0000-0000-000000000001/triage")
    assert response.status_code == 403


def test_fail_closed_simulation_requires_authentication():
    response = client.post(
        "/api/v1/analyses/00000000-0000-0000-0000-000000000001/visagism/simulate",
        json={"haircut_name": "grounded-cut"},
    )
    assert response.status_code == 403


def test_visagism_result_requires_authentication():
    response = client.get(
        "/api/v1/analyses/00000000-0000-0000-0000-000000000001/visagism"
    )
    assert response.status_code == 403
