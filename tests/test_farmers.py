import pytest
from database import mask_phone, get_farmers, get_db_connection

def test_mask_phone():
    """Verify privacy phone number masking."""
    assert mask_phone("9876543210") == "98***-***210"
    assert mask_phone("+919876543210") == "+9***-***210"
    assert mask_phone("") == "N/A"
    assert mask_phone(None) == "N/A"

def test_farmer_registration_success(coordinator_client, app_instance):
    """Test registering a new farmer successfully as coordinator."""
    response = coordinator_client.post("/farmers", data={
        "name": "Bipul Barman",
        "phone": "9864998877",
        "village": "Salmora",
        "tehsil": "Majuli",
        "district": "Majuli",
        "livestock_type": "Cattle",
        "cattle_count": "4",
        "buffalo_count": "0",
        "other_count": "0",
        "special_needs": "1 pregnant cow",
        "latitude": "26.9200",
        "longitude": "94.2200"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Bipul Barman" in response.data
    assert b"registered successfully" in response.data

def test_farmer_registration_validation_empty_name(coordinator_client):
    """Test registering farmer without name fails validation."""
    response = coordinator_client.post("/farmers", data={
        "name": "",
        "phone": "9864998877",
        "village": "Salmora",
        "cattle_count": "2"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Farmer name is required" in response.data

def test_farmer_registration_validation_invalid_phone(coordinator_client):
    """Test registering farmer with short phone fails validation."""
    response = coordinator_client.post("/farmers", data={
        "name": "Test Farmer",
        "phone": "12345",
        "village": "Salmora",
        "cattle_count": "2"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Valid 10-digit phone number is required" in response.data

def test_farmer_registration_validation_zero_animals(coordinator_client):
    """Test registering farmer with 0 animals fails validation."""
    response = coordinator_client.post("/farmers", data={
        "name": "Test Farmer",
        "phone": "9876543210",
        "village": "Salmora",
        "cattle_count": "0",
        "buffalo_count": "0",
        "other_count": "0"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"At least one animal count must be greater than zero" in response.data

def test_farmer_auto_priority_escalation(app_instance):
    """Test that special needs like 'rising water' or 'pregnant' set high/critical priority."""
    with app_instance.app_context():
        conn = get_db_connection(app_instance.config["DATABASE_PATH"])
        from database import add_farmer

        f_id = add_farmer(conn, {
            "name": "Risk Farmer",
            "phone": "9864000000",
            "village": "Jengraimukh",
            "cattle_count": 3,
            "special_needs": "Water rising fast, trapped in shed"
        })

        f = conn.execute("SELECT * FROM farmers WHERE id = ?", (f_id,)).fetchone()
        assert f["priority"] == "Critical"
        conn.close()

def test_farmer_filtering(coordinator_client):
    """Test filtering farmers by village and livestock type."""
    # Filter by village Salmora
    res_salmora = coordinator_client.get("/farmers?village=Salmora")
    assert res_salmora.status_code == 200
    assert b"Salmora" in res_salmora.data

    # Filter by livestock type Buffalo
    res_buffalo = coordinator_client.get("/farmers?livestock_type=Buffalo")
    assert res_buffalo.status_code == 200
    assert b"Buffalo" in res_buffalo.data

def test_public_phone_masking_in_api(client):
    """Test that public API responses mask personal phone numbers for unauthenticated users."""
    res = client.get("/api/farmers")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data) > 0
    first = data[0]
    # Phone should be masked with asterisks
    assert "***" in first["phone"]
