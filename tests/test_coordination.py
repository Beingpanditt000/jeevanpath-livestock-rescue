import pytest
from database import get_db_connection, assign_rescue_resource, update_rescue_status

def test_assign_rescue_resource_success(app_instance):
    """Test assigning volunteer and shelter updates farmer, volunteer, and shelter occupancy atomically."""
    with app_instance.app_context():
        conn = get_db_connection(app_instance.config["DATABASE_PATH"])
        
        # Get a pending farmer
        farmer = conn.execute("SELECT * FROM farmers WHERE rescue_status = 'Pending' LIMIT 1").fetchone()
        farmer_id = farmer["id"]
        animal_count = farmer["animal_count"]

        # Get an available volunteer vehicle
        volunteer = conn.execute("SELECT * FROM volunteers WHERE availability = 'Available' AND resource_type = 'Vehicle' LIMIT 1").fetchone()
        volunteer_id = volunteer["id"]

        # Get a shelter with enough capacity
        shelter = conn.execute("SELECT * FROM shelters WHERE (total_capacity - occupied_capacity) >= ? LIMIT 1", (animal_count,)).fetchone()
        shelter_id = shelter["id"]
        initial_occupied = shelter["occupied_capacity"]

        # Perform assignment
        assignment_id = assign_rescue_resource(conn, farmer_id, volunteer_id, shelter_id, notes="Test dispatch")
        assert assignment_id is not None

        # Verify farmer status
        f_updated = conn.execute("SELECT * FROM farmers WHERE id = ?", (farmer_id,)).fetchone()
        assert f_updated["rescue_status"] == "In Progress"
        assert f_updated["assigned_volunteer_id"] == volunteer_id
        assert f_updated["assigned_shelter_id"] == shelter_id

        # Verify volunteer status is Deployed
        v_updated = conn.execute("SELECT * FROM volunteers WHERE id = ?", (volunteer_id,)).fetchone()
        assert v_updated["availability"] == "Deployed"

        # Verify shelter occupancy increased
        s_updated = conn.execute("SELECT * FROM shelters WHERE id = ?", (shelter_id,)).fetchone()
        assert s_updated["occupied_capacity"] == initial_occupied + animal_count

        conn.close()

def test_shelter_overcapacity_prevented(app_instance):
    """Test that assigning a shelter without enough remaining capacity raises ValueError."""
    with app_instance.app_context():
        conn = get_db_connection(app_instance.config["DATABASE_PATH"])

        # Insert a nearly full shelter with only 1 space free
        cur = conn.execute("""
            INSERT INTO shelters (name, village, latitude, longitude, total_capacity, occupied_capacity)
            VALUES ('Tiny Pen', 'Salmora', 26.91, 94.22, 10, 9)
        """)
        small_shelter_id = cur.lastrowid

        # Insert a farm with 8 animals
        from database import add_farmer
        f_id = add_farmer(conn, {
            "name": "Big Herd Farmer",
            "phone": "9876543210",
            "village": "Salmora",
            "cattle_count": 8
        })

        with pytest.raises(ValueError, match="has only 1 spaces available"):
            assign_rescue_resource(conn, f_id, None, small_shelter_id)

        conn.close()

def test_complete_evacuation_frees_volunteer(app_instance):
    """Test updating status to 'Safe in Shelter' frees up volunteer back to 'Available'."""
    with app_instance.app_context():
        conn = get_db_connection(app_instance.config["DATABASE_PATH"])

        farmer = conn.execute("SELECT * FROM farmers WHERE rescue_status = 'Pending' LIMIT 1").fetchone()
        volunteer = conn.execute("SELECT * FROM volunteers WHERE availability = 'Available' LIMIT 1").fetchone()
        shelter = conn.execute("SELECT * FROM shelters LIMIT 1").fetchone()

        assign_rescue_resource(conn, farmer["id"], volunteer["id"], shelter["id"])

        # Verify volunteer is deployed
        v_dep = conn.execute("SELECT availability FROM volunteers WHERE id = ?", (volunteer["id"],)).fetchone()
        assert v_dep["availability"] == "Deployed"

        # Update status to Safe in Shelter
        update_rescue_status(conn, farmer["id"], "Safe in Shelter")

        # Verify volunteer is Available again
        v_freed = conn.execute("SELECT availability FROM volunteers WHERE id = ?", (volunteer["id"],)).fetchone()
        assert v_freed["availability"] == "Available"

        f_done = conn.execute("SELECT rescue_status FROM farmers WHERE id = ?", (farmer["id"],)).fetchone()
        assert f_done["rescue_status"] == "Safe in Shelter"

        conn.close()
