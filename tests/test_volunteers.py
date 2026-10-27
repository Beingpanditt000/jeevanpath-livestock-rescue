import pytest
from database import get_volunteers, get_db_connection

def test_volunteer_registration_success(coordinator_client):
    """Test registering a new volunteer transport vehicle as coordinator."""
    response = coordinator_client.post("/volunteers", data={
        "name": "Barpeta Water Rescue Unit",
        "phone": "9854778899",
        "organization": "Community NGO",
        "village": "Kamalabari",
        "resource_type": "Vehicle",
        "resource_details": "Rescue boat with animal safety harnesses",
        "capacity": "10",
        "availability": "Available"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Barpeta Water Rescue Unit" in response.data
    assert b"registered successfully" in response.data

def test_volunteer_validation_missing_name(coordinator_client):
    """Test validation fails if volunteer name is missing."""
    response = coordinator_client.post("/volunteers", data={
        "name": "",
        "phone": "9854778899",
        "village": "Kamalabari"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Volunteer or organization name is required" in response.data

def test_volunteer_validation_negative_capacity(coordinator_client):
    """Test validation fails if capacity is negative."""
    response = coordinator_client.post("/volunteers", data={
        "name": "Invalid Unit",
        "phone": "9854778899",
        "village": "Kamalabari",
        "capacity": "-5"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Capacity cannot be negative" in response.data

def test_volunteer_filtering(coordinator_client):
    """Test filtering volunteers by resource type as coordinator."""
    response = coordinator_client.get("/volunteers?resource_type=Vehicle")
    assert response.status_code == 200
    assert b"Vehicle" in response.data
