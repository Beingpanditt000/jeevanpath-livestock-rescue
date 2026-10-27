import pytest
from database import get_db_connection, assign_rescue_resource

def test_welcome_page_for_anonymous_user(client):
    """Anonymous user accessing '/' sees the professional welcome page with sign-in and register buttons."""
    res = client.get("/")
    assert res.status_code == 200
    assert b"Rapid Emergency Coordination" in res.data
    assert b"Demo Accounts" in res.data
    assert b"coord_admin" in res.data
    assert b"Sign In" in res.data

def test_three_connected_dashboards_workflow(client, app_instance):
    """
    Demonstration Workflow (Requirement 6):
    1. A farmer registers livestock and submits a rescue request.
    2. The request appears on the rescue team's dashboard.
    3. The rescue coordinator verifies it and assigns a suitable volunteer, vehicle, and shelter.
    4. The assignment appears on that volunteer's dashboard.
    5. The volunteer accepts the task and updates its status.
    6. The farmer can see the updated status.
    7. The rescue team can monitor the operation until completion.
    """
    # 1. Farmer Registration & Login
    reg_res = client.post("/register/farmer", data={
        "username": "farmer_kamal",
        "password": "KamalPass123!",
        "confirm_password": "KamalPass123!",
        "full_name": "Kamal Nath",
        "phone": "9864223344",
        "village": "Rawnapar",
        "livestock_type": "Cattle",
        "cattle_count": "4",
        "buffalo_count": "2",
        "other_count": "0",
        "special_needs": "1 cow with broken leg"
    }, follow_redirects=False)
    assert reg_res.status_code == 302
    assert "/login" in reg_res.headers["Location"]

    # Farmer logs in
    login_res = client.post("/login", data={
        "username": "farmer_kamal",
        "password": "KamalPass123!"
    }, follow_redirects=False)
    assert login_res.status_code == 302
    assert "/farmer/dashboard" in login_res.headers["Location"]

    # Farmer submits rescue request
    farmer_dash = client.post("/farmer/dashboard", data={
        "action": "request_rescue",
        "cattle_count": "4",
        "buffalo_count": "2",
        "urgency": "Critical",
        "location": "Rawnapar Ghat",
        "special_needs": "1 cow with broken leg",
        "notes": "Floodwaters rising fast near barn"
    }, follow_redirects=True)
    assert farmer_dash.status_code == 200
    assert b"Rescue request submitted" in farmer_dash.data

    # Retrieve farmer ID
    with app_instance.app_context():
        conn = get_db_connection(app_instance.config["DATABASE_PATH"])
        farmer = conn.execute("SELECT * FROM farmers WHERE name = 'Kamal Nath'").fetchone()
        farmer_id = farmer["id"]
        assert farmer["rescue_status"] in ("Requested", "Pending")
        assert farmer["priority"] == "Critical"
        conn.close()

    # 2. Rescue Coordinator Dashboard Check
    coord_client = app_instance.test_client()
    coord_client.post("/login", data={
        "username": "coord_admin",
        "password": "CoordPass123!"
    })

    rescue_dash = coord_client.get("/rescue/dashboard")
    assert rescue_dash.status_code == 200
    assert b"Kamal Nath" in rescue_dash.data
    assert b"Rawnapar" in rescue_dash.data

    # 3. Coordinator verifies and assigns volunteer & shelter
    coord_client.post("/rescue/dashboard", data={
        "action": "verify_request",
        "farmer_id": str(farmer_id),
        "priority": "Critical"
    }, follow_redirects=True)

    with app_instance.app_context():
        conn = get_db_connection(app_instance.config["DATABASE_PATH"])
        vol = conn.execute("SELECT * FROM volunteers WHERE availability = 'Available' AND capacity >= 6 LIMIT 1").fetchone()
        vol_id = vol["id"]
        vol_username = "volunteer_bhaben"  # Seeded volunteer user
        shelter = conn.execute("SELECT * FROM shelters WHERE (total_capacity - occupied_capacity) >= 6 LIMIT 1").fetchone()
        shelter_id = shelter["id"]
        conn.close()

    dispatch_res = coord_client.post("/rescue/dashboard", data={
        "action": "assign_resources",
        "farmer_id": str(farmer_id),
        "volunteer_id": str(vol_id),
        "shelter_id": str(shelter_id),
        "notes": "Emergency boat evacuation needed immediately",
        "coordinator_instructions": "Bring animal harness and medical kit"
    }, follow_redirects=True)
    assert dispatch_res.status_code == 200
    assert b"Evacuation resources dispatched" in dispatch_res.data

    # 4. Volunteer Dashboard Check
    vol_client = app_instance.test_client()
    vol_client.post("/login", data={
        "username": vol_username,
        "password": "VolunteerPass123!"
    })

    vol_dash = vol_client.get("/volunteer/dashboard")
    assert vol_dash.status_code == 200
    assert b"Kamal Nath" in vol_dash.data
    assert b"Bring animal harness" in vol_dash.data

    # 5. Volunteer accepts the task
    with app_instance.app_context():
        conn = get_db_connection(app_instance.config["DATABASE_PATH"])
        assignment = conn.execute("SELECT * FROM rescue_assignments WHERE farmer_id = ?", (farmer_id,)).fetchone()
        assignment_id = assignment["id"]
        conn.close()

    accept_res = vol_client.post("/volunteer/dashboard", data={
        "action": "task_response",
        "assignment_id": str(assignment_id),
        "response_status": "Accepted"
    }, follow_redirects=True)
    assert accept_res.status_code == 200
    assert b"accepted successfully" in accept_res.data

    # Volunteer updates progress
    prog_res = vol_client.post("/volunteer/dashboard", data={
        "action": "update_progress",
        "assignment_id": str(assignment_id),
        "rescue_status": "Safe in Shelter",
        "animals_collected": "6",
        "animals_delivered": "6",
        "notes": "All 6 cattle safely transported to relief camp"
    }, follow_redirects=True)
    assert prog_res.status_code == 200
    assert b"progress updated" in prog_res.data

    # 6. Farmer sees updated status
    farmer_check = client.get("/farmer/dashboard")
    assert farmer_check.status_code == 200
    assert b"Safe in Shelter" in farmer_check.data or b"Rescued" in farmer_check.data

    # 7. Rescue Team monitors completed status and activity log
    rescue_final = coord_client.get("/rescue/dashboard")
    assert rescue_final.status_code == 200
    assert b"Activity Audit Log" in rescue_final.data
    assert b"Kamal Nath" in rescue_final.data

def test_volunteer_decline_task_with_reason(client, app_instance):
    """Test volunteer can decline an assigned task with a required reason, freeing resource."""
    with app_instance.app_context():
        conn = get_db_connection(app_instance.config["DATABASE_PATH"])
        farmer = conn.execute("SELECT * FROM farmers WHERE rescue_status = 'Pending' LIMIT 1").fetchone()
        vol = conn.execute("SELECT * FROM volunteers WHERE availability = 'Available' LIMIT 1").fetchone()
        shelter = conn.execute("SELECT * FROM shelters LIMIT 1").fetchone()
        farmer_id = farmer["id"]
        vol_id = vol["id"]
        shelter_id = shelter["id"]

        assign_rescue_resource(conn, farmer_id, vol_id, shelter_id, notes="Test dispatch")
        assignment = conn.execute("SELECT * FROM rescue_assignments WHERE farmer_id = ?", (farmer_id,)).fetchone()
        assignment_id = assignment["id"]
        conn.close()

    vol_client = app_instance.test_client()
    vol_client.post("/login", data={
        "username": "volunteer_bhaben",
        "password": "VolunteerPass123!"
    })

    decline_res = vol_client.post("/volunteer/dashboard", data={
        "action": "task_response",
        "assignment_id": str(assignment_id),
        "response_status": "Declined",
        "decline_reason": "Engine malfunction on rescue boat"
    }, follow_redirects=True)

    assert decline_res.status_code == 200
    assert b"declined successfully" in decline_res.data

    with app_instance.app_context():
        conn = get_db_connection(app_instance.config["DATABASE_PATH"])
        a_check = conn.execute("SELECT * FROM rescue_assignments WHERE id = ?", (assignment_id,)).fetchone()
        assert a_check["acceptance_status"] == "Declined"
        assert "Engine malfunction" in a_check["decline_reason"]
        conn.close()

def test_role_access_control_isolation(client, farmer_client, volunteer_client):
    """Test strict role boundary enforcement across all 3 dashboards."""
    # Anonymous cannot access any dashboard
    assert client.get("/farmer/dashboard", follow_redirects=False).status_code == 302
    assert client.get("/volunteer/dashboard", follow_redirects=False).status_code == 302
    assert client.get("/rescue/dashboard", follow_redirects=False).status_code == 302

    # Farmer cannot access volunteer or coordinator dashboards
    assert farmer_client.get("/volunteer/dashboard").status_code == 403
    assert farmer_client.get("/rescue/dashboard").status_code == 403

    # Volunteer cannot access farmer or coordinator dashboards
    assert volunteer_client.get("/farmer/dashboard").status_code == 403
    assert volunteer_client.get("/rescue/dashboard").status_code == 403

def test_volunteer_availability_status_toggle(volunteer_client, app_instance):
    """Test volunteer updating availability to Available, Busy, Unavailable."""
    for state in ["Busy", "Unavailable", "Available"]:
        res = volunteer_client.post("/volunteer/dashboard", data={
            "action": "set_availability",
            "availability": state
        }, follow_redirects=True)
        assert res.status_code == 200
        assert f"Availability updated to: {state}".encode() in res.data
