import pytest
from database import get_db_connection

def test_disaster_alert_creation_and_escalation(coordinator_client, app_instance):
    """Test creating an alert broadcasts and auto-escalates affected village farms to Critical priority."""
    with app_instance.app_context():
        conn = get_db_connection(app_instance.config["DATABASE_PATH"])
        # Ensure a test farm exists in 'Kalyanpur' with Normal priority
        from database import add_farmer
        f_id = add_farmer(conn, {
            "name": "Kalyan Farmer",
            "phone": "9864123456",
            "village": "Kalyanpur",
            "cattle_count": 5,
            "priority": "Normal"
        })
        conn.close()

    # Broadcast Critical Alert for Kalyanpur using Coordinator credentials
    response = coordinator_client.post("/alerts", data={
        "title": "Severe Flash Flood Inundation",
        "disaster_type": "Flood",
        "affected_area": "Kalyanpur, Salmora",
        "severity": "Critical",
        "description": "Rising Brahmaputra water breached village bunds.",
        "radius_km": "4.0",
        "latitude": "26.9300",
        "longitude": "94.2100"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Severe Flash Flood Inundation" in response.data

    # Verify farmer priority was escalated to Critical
    with app_instance.app_context():
        conn = get_db_connection(app_instance.config["DATABASE_PATH"])
        farmer = conn.execute("SELECT * FROM farmers WHERE id = ?", (f_id,)).fetchone()
        assert farmer["priority"] == "Critical"
        conn.close()

def test_resolve_disaster_alert(coordinator_client, app_instance):
    """Test resolving/deactivating an alert as Coordinator."""
    with app_instance.app_context():
        conn = get_db_connection(app_instance.config["DATABASE_PATH"])
        alert = conn.execute("SELECT id FROM disaster_alerts WHERE status = 'Active' LIMIT 1").fetchone()
        alert_id = alert["id"]
        conn.close()

    response = coordinator_client.post(f"/alerts/{alert_id}/resolve", follow_redirects=True)
    assert response.status_code == 200
    assert b"Alert marked as Resolved" in response.data

    with app_instance.app_context():
        conn = get_db_connection(app_instance.config["DATABASE_PATH"])
        updated = conn.execute("SELECT status FROM disaster_alerts WHERE id = ?", (alert_id,)).fetchone()
        assert updated["status"] == "Resolved"
        conn.close()
