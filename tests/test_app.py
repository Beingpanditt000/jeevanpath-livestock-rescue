import pytest

def test_page_routes_status_ok(coordinator_client):
    """Test all main frontend pages load with HTTP 200 for authenticated coordinator."""
    pages = ["/", "/rescue/dashboard", "/farmer/dashboard", "/volunteer/dashboard", "/farmers", "/volunteers", "/alerts", "/coordinate", "/map"]
    for page in pages:
        res = coordinator_client.get(page, follow_redirects=True)
        assert res.status_code == 200, f"Page {page} returned status {res.status_code}"
        assert b"JEEVANPATH" in res.data

def test_public_pages_status_ok(client):
    """Test public pages load without requiring authentication."""
    public_pages = ["/", "/login", "/register", "/register/farmer", "/register/volunteer", "/map"]
    for page in public_pages:
        res = client.get(page)
        assert res.status_code == 200, f"Public page {page} returned status {res.status_code}"

def test_protected_routes_redirect_to_login(client):
    """Test private operational routes redirect anonymous users to login page."""
    protected_pages = ["/rescue/dashboard", "/farmer/dashboard", "/volunteer/dashboard", "/coordinate", "/my-livestock", "/my-resource", "/change-password"]
    for page in protected_pages:
        res = client.get(page)
        assert res.status_code == 302, f"Protected page {page} should redirect"
        assert "/login" in res.headers["Location"]

def test_api_stats(client):
    """Test dashboard stats API returns all required metrics."""
    res = client.get("/api/stats")
    assert res.status_code == 200
    data = res.get_json()
    assert "total_farms" in data
    assert "total_livestock" in data
    assert "active_alerts_count" in data
    assert "available_volunteers" in data
    assert "available_vehicles" in data
    assert "available_shelter_capacity" in data

def test_api_map_data(client):
    """Test GIS bundled data endpoint."""
    res = client.get("/api/map-data")
    assert res.status_code == 200
    data = res.get_json()
    assert "farmers" in data
    assert "volunteers" in data
    assert "shelters" in data
    assert "alerts" in data
    assert "map_center" in data

def test_coordinator_pin_toggle(client):
    """Test entering PIN 1234 enables coordinator mode session."""
    # Incorrect PIN
    bad_res = client.post("/toggle-coordinator", data={"pin": "9999"}, follow_redirects=True)
    assert b"Invalid PIN" in bad_res.data

    # Correct PIN
    good_res = client.post("/toggle-coordinator", data={"pin": "1234"}, follow_redirects=True)
    assert b"Coordinator mode activated" in good_res.data

    # Toggle off
    off_res = client.post("/toggle-coordinator", follow_redirects=True)
    assert b"Coordinator mode disabled" in off_res.data
