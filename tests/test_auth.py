import pytest
from database import get_db_connection, get_user_by_username
from werkzeug.security import check_password_hash

def test_login_success_coordinator(client):
    """Test successful login for Coordinator role."""
    response = client.post("/login", data={
        "username": "coord_admin",
        "password": "CoordPass123!"
    }, follow_redirects=False)

    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert sess.get("username") == "coord_admin"
        assert sess.get("role") == "Coordinator"
        assert sess.get("user_id") is not None

def test_login_success_farmer(client):
    """Test successful login for Farmer role redirects to /farmer/dashboard."""
    response = client.post("/login", data={
        "username": "farmer_ramesh",
        "password": "FarmerPass123!"
    }, follow_redirects=False)

    assert response.status_code == 302
    assert "/farmer/dashboard" in response.headers["Location"]
    with client.session_transaction() as sess:
        assert sess.get("role") == "Farmer"

def test_login_success_volunteer(client):
    """Test successful login for Volunteer role redirects to /volunteer/dashboard."""
    response = client.post("/login", data={
        "username": "volunteer_bhaben",
        "password": "VolunteerPass123!"
    }, follow_redirects=False)

    assert response.status_code == 302
    assert "/volunteer/dashboard" in response.headers["Location"]
    with client.session_transaction() as sess:
        assert sess.get("role") == "Volunteer"

def test_login_failure_wrong_password(client):
    """Test login failure with wrong password leaves session empty."""
    response = client.post("/login", data={
        "username": "coord_admin",
        "password": "WrongPassword999!"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Invalid username or password" in response.data
    with client.session_transaction() as sess:
        assert sess.get("user_id") is None

def test_login_failure_nonexistent_user(client):
    """Test login failure with nonexistent username."""
    response = client.post("/login", data={
        "username": "ghost_user",
        "password": "SomePassword123!"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Invalid username or password" in response.data

def test_logout(client):
    """Test logout clears session and redirects to login page."""
    # First log in
    client.post("/login", data={
        "username": "coord_admin",
        "password": "CoordPass123!"
    })

    # Log out
    response = client.get("/logout", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    with client.session_transaction() as sess:
        assert sess.get("user_id") is None
        assert sess.get("role") is None

def test_unauthorized_access_redirects(client):
    """Test anonymous user accessing private route redirects to login with next parameter."""
    response = client.get("/coordinate", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert "next=" in response.headers["Location"] and "coordinate" in response.headers["Location"]

def test_role_permission_farmer_cannot_access_coordinate(farmer_client):
    """Test Farmer cannot access Coordinator Operations Board (403 Forbidden)."""
    response = farmer_client.get("/coordinate")
    assert response.status_code == 403
    assert b"Access Denied" in response.data or b"Access denied" in response.data

def test_role_permission_volunteer_cannot_access_coordinate(volunteer_client):
    """Test Volunteer cannot access Coordinator Operations Board (403 Forbidden)."""
    response = volunteer_client.get("/coordinate")
    assert response.status_code == 403
    assert b"Access Denied" in response.data or b"Access denied" in response.data

def test_role_permission_farmer_cannot_broadcast_alerts(farmer_client):
    """Test Farmer cannot issue disaster alerts (403 Forbidden)."""
    response = farmer_client.post("/alerts", data={
        "title": "Unauthorized Alert",
        "disaster_type": "Flood",
        "affected_area": "Salmora",
        "severity": "Critical",
        "description": "Unauthorized broadcast"
    })
    assert response.status_code == 403

def test_role_permission_volunteer_cannot_broadcast_alerts(volunteer_client):
    """Test Volunteer cannot issue disaster alerts (403 Forbidden)."""
    response = volunteer_client.post("/alerts", data={
        "title": "Unauthorized Alert",
        "disaster_type": "Flood",
        "affected_area": "Salmora",
        "severity": "Critical",
        "description": "Unauthorized broadcast"
    })
    assert response.status_code == 403

def test_password_hashing(app_instance):
    """Test that user passwords in the database are properly hashed and never plaintext."""
    with app_instance.app_context():
        conn = get_db_connection(app_instance.config["DATABASE_PATH"])
        user = conn.execute("SELECT * FROM users WHERE username = 'coord_admin'").fetchone()
        
        # Verify hash format and ensure password is never plaintext
        assert user["password_hash"] != "CoordPass123!"
        assert "scrypt:" in user["password_hash"] or "pbkdf2:" in user["password_hash"]
        
        # Verify Werkzeug check_password_hash succeeds on correct and fails on incorrect
        assert check_password_hash(user["password_hash"], "CoordPass123!") is True
        assert check_password_hash(user["password_hash"], "WrongPassword!") is False
        conn.close()

def test_farmer_self_registration(client, app_instance):
    """Test public farmer self-registration creates user and links livestock record."""
    response = client.post("/register/farmer", data={
        "username": "new_farmer_dhiren",
        "password": "SecretPass123!",
        "confirm_password": "SecretPass123!",
        "full_name": "Dhiren Borah",
        "phone": "9864771122",
        "village": "Jengraimukh",
        "livestock_type": "Mixed",
        "cattle_count": "5",
        "buffalo_count": "3",
        "other_count": "0",
        "special_needs": "1 calf with fever"
    }, follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    with app_instance.app_context():
        conn = get_db_connection(app_instance.config["DATABASE_PATH"])
        user = conn.execute("SELECT * FROM users WHERE username = 'new_farmer_dhiren'").fetchone()
        assert user is not None
        assert user["role"] == "Farmer"

        # Verify linked farmer record
        farmer = conn.execute("SELECT * FROM farmers WHERE user_id = ?", (user["id"],)).fetchone()
        assert farmer is not None
        assert farmer["animal_count"] == 8
        assert farmer["cattle_count"] == 5
        conn.close()

def test_volunteer_self_registration(client, app_instance):
    """Test public volunteer self-registration creates user and links resource."""
    response = client.post("/register/volunteer", data={
        "username": "new_vol_pranjal",
        "password": "SecretPass123!",
        "confirm_password": "SecretPass123!",
        "full_name": "Pranjal Dutta",
        "phone": "9435882233",
        "organization": "Majuli River Drivers",
        "village": "Salmora",
        "resource_type": "Vehicle",
        "capacity": "10",
        "resource_details": "Rescue boat with animal safety deck"
    }, follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    with app_instance.app_context():
        conn = get_db_connection(app_instance.config["DATABASE_PATH"])
        user = conn.execute("SELECT * FROM users WHERE username = 'new_vol_pranjal'").fetchone()
        assert user is not None
        assert user["role"] == "Volunteer"

        vol = conn.execute("SELECT * FROM volunteers WHERE user_id = ?", (user["id"],)).fetchone()
        assert vol is not None
        assert vol["capacity"] == 10
        conn.close()

def test_change_password_workflow(farmer_client, app_instance):
    """Test change password requires valid old password and updates credentials."""
    # Attempt change with wrong old password
    fail_res = farmer_client.post("/change-password", data={
        "current_password": "WrongOldPassword",
        "new_password": "NewFarmerPass123!",
        "confirm_password": "NewFarmerPass123!"
    }, follow_redirects=True)
    assert b"Current password does not match" in fail_res.data

    # Successful change
    good_res = farmer_client.post("/change-password", data={
        "current_password": "FarmerPass123!",
        "new_password": "NewFarmerPass123!",
        "confirm_password": "NewFarmerPass123!"
    }, follow_redirects=True)
    assert b"password has been changed successfully" in good_res.data

    # Verify new password works in database
    with app_instance.app_context():
        conn = get_db_connection(app_instance.config["DATABASE_PATH"])
        user = conn.execute("SELECT * FROM users WHERE username = 'farmer_ramesh'").fetchone()
        assert check_password_hash(user["password_hash"], "NewFarmerPass123!") is True
        conn.close()

def test_farmer_portal_update_livestock(farmer_client, app_instance):
    """Test farmer updating their own livestock census via /my-livestock."""
    response = farmer_client.post("/my-livestock", data={
        "action": "update_details",
        "cattle_count": "7",
        "buffalo_count": "2",
        "other_count": "1",
        "special_needs": "Water rising near barn; 1 pregnant Sahiwal cow",
        "priority": "High",
        "village": "Salmora North",
        "phone": "9864119988"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"records and risk notes have been updated" in response.data

    with app_instance.app_context():
        conn = get_db_connection(app_instance.config["DATABASE_PATH"])
        farmer = conn.execute("SELECT * FROM farmers WHERE name = 'Rameshwar Saikia'").fetchone()
        assert farmer["animal_count"] == 10
        assert farmer["cattle_count"] == 7
        assert "Water rising" in farmer["special_needs"]
        conn.close()

def test_volunteer_portal_update_availability(volunteer_client, app_instance):
    """Test volunteer updating their deployment status via /my-resource."""
    response = volunteer_client.post("/my-resource", data={
        "action": "set_availability",
        "availability": "Standby"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"status updated to: Standby" in response.data

    with app_instance.app_context():
        conn = get_db_connection(app_instance.config["DATABASE_PATH"])
        vol = conn.execute("SELECT * FROM volunteers WHERE name LIKE '%Bhaben%'").fetchone()
        assert vol["availability"] == "Standby"
        conn.close()

def test_create_admin_script(app_instance):
    """Test create_admin.py script function provisions coordinator account safely."""
    from create_admin import setup_admin
    db_path = app_instance.config["DATABASE_PATH"]
    
    result = setup_admin(
        username="lead_officer",
        password="LeadPassword123!",
        full_name="Lead DDMA Officer",
        phone="9864999999",
        db_path=db_path
    )
    assert result is True

    with app_instance.app_context():
        conn = get_db_connection(db_path)
        user = conn.execute("SELECT * FROM users WHERE username = 'lead_officer'").fetchone()
        assert user is not None
        assert user["role"] == "Coordinator"
        assert check_password_hash(user["password_hash"], "LeadPassword123!") is True
        conn.close()
