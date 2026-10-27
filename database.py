import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('Farmer', 'Volunteer', 'Coordinator', 'Admin')),
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    village TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shelters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    village TEXT NOT NULL,
    location_notes TEXT DEFAULT '',
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    total_capacity INTEGER NOT NULL CHECK(total_capacity >= 0),
    occupied_capacity INTEGER DEFAULT 0 CHECK(occupied_capacity >= 0),
    water_available INTEGER DEFAULT 1,
    fodder_available INTEGER DEFAULT 1,
    vet_available INTEGER DEFAULT 0,
    contact_person TEXT DEFAULT '',
    contact_phone TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS volunteers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    organization TEXT DEFAULT 'Independent',
    village TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    resource_type TEXT NOT NULL,
    resource_details TEXT DEFAULT '',
    capacity INTEGER DEFAULT 0 CHECK(capacity >= 0),
    availability TEXT DEFAULT 'Available',
    water_support INTEGER DEFAULT 0,
    fodder_support INTEGER DEFAULT 0,
    medical_support INTEGER DEFAULT 0,
    shelter_support INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS disaster_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    disaster_type TEXT NOT NULL,
    affected_area TEXT NOT NULL,
    severity TEXT NOT NULL,
    description TEXT NOT NULL,
    source TEXT DEFAULT 'Disaster Coordination Cell',
    verification_status TEXT DEFAULT 'Verified',
    latitude REAL,
    longitude REAL,
    radius_km REAL DEFAULT 5.0,
    status TEXT DEFAULT 'Active',
    issued_by TEXT DEFAULT 'Disaster Coordination Cell',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS farmers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    village TEXT NOT NULL,
    tehsil TEXT DEFAULT '',
    district TEXT DEFAULT 'Majuli',
    latitude REAL,
    longitude REAL,
    livestock_type TEXT NOT NULL,
    cattle_count INTEGER DEFAULT 0 CHECK(cattle_count >= 0),
    buffalo_count INTEGER DEFAULT 0 CHECK(buffalo_count >= 0),
    other_count INTEGER DEFAULT 0 CHECK(other_count >= 0),
    animal_count INTEGER NOT NULL CHECK(animal_count > 0),
    special_needs TEXT DEFAULT '',
    priority TEXT DEFAULT 'Normal',
    rescue_status TEXT DEFAULT 'Pending',
    request_notes TEXT DEFAULT '',
    assigned_volunteer_id INTEGER,
    assigned_shelter_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY(assigned_volunteer_id) REFERENCES volunteers(id) ON DELETE SET NULL,
    FOREIGN KEY(assigned_shelter_id) REFERENCES shelters(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS rescue_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    farmer_id INTEGER NOT NULL,
    volunteer_id INTEGER,
    shelter_id INTEGER,
    animals_transported INTEGER DEFAULT 0,
    notes TEXT DEFAULT '',
    status TEXT DEFAULT 'Assigned',
    acceptance_status TEXT DEFAULT 'Pending',
    decline_reason TEXT DEFAULT '',
    animals_collected INTEGER DEFAULT 0,
    animals_delivered INTEGER DEFAULT 0,
    coordinator_instructions TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY(farmer_id) REFERENCES farmers(id) ON DELETE CASCADE,
    FOREIGN KEY(volunteer_id) REFERENCES volunteers(id) ON DELETE SET NULL,
    FOREIGN KEY(shelter_id) REFERENCES shelters(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    role TEXT,
    action TEXT NOT NULL,
    details TEXT DEFAULT '',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
);
"""

def get_db_connection(db_path: str):
    """Get a SQLite database connection with row factory enabled."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def run_migrations(conn):
    """Safely apply schema migrations to preserve existing database records."""
    # Ensure users table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('Farmer', 'Volunteer', 'Coordinator', 'Admin')),
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            village TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Ensure activity_log table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            role TEXT,
            action TEXT NOT NULL,
            details TEXT DEFAULT '',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
        );
    """)

    # Check and add columns to disaster_alerts
    alert_cols = [c["name"] for c in conn.execute("PRAGMA table_info(disaster_alerts)").fetchall()]
    if "source" not in alert_cols:
        conn.execute("ALTER TABLE disaster_alerts ADD COLUMN source TEXT DEFAULT 'Disaster Coordination Cell';")
    if "verification_status" not in alert_cols:
        conn.execute("ALTER TABLE disaster_alerts ADD COLUMN verification_status TEXT DEFAULT 'Verified';")

    # Check and add columns to rescue_assignments
    assign_cols = [c["name"] for c in conn.execute("PRAGMA table_info(rescue_assignments)").fetchall()]
    if "acceptance_status" not in assign_cols:
        conn.execute("ALTER TABLE rescue_assignments ADD COLUMN acceptance_status TEXT DEFAULT 'Pending';")
    if "decline_reason" not in assign_cols:
        conn.execute("ALTER TABLE rescue_assignments ADD COLUMN decline_reason TEXT DEFAULT '';")
    if "animals_collected" not in assign_cols:
        conn.execute("ALTER TABLE rescue_assignments ADD COLUMN animals_collected INTEGER DEFAULT 0;")
    if "animals_delivered" not in assign_cols:
        conn.execute("ALTER TABLE rescue_assignments ADD COLUMN animals_delivered INTEGER DEFAULT 0;")
    if "coordinator_instructions" not in assign_cols:
        conn.execute("ALTER TABLE rescue_assignments ADD COLUMN coordinator_instructions TEXT DEFAULT '';")

    # Check and add columns to farmers
    farmer_cols = [c["name"] for c in conn.execute("PRAGMA table_info(farmers)").fetchall()]
    if "user_id" not in farmer_cols:
        conn.execute("ALTER TABLE farmers ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;")
    if "request_notes" not in farmer_cols:
        conn.execute("ALTER TABLE farmers ADD COLUMN request_notes TEXT DEFAULT '';")

    # Check and add columns to volunteers
    vol_cols = [c["name"] for c in conn.execute("PRAGMA table_info(volunteers)").fetchall()]
    if "user_id" not in vol_cols:
        conn.execute("ALTER TABLE volunteers ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;")
    if "water_support" not in vol_cols:
        conn.execute("ALTER TABLE volunteers ADD COLUMN water_support INTEGER DEFAULT 0;")
    if "fodder_support" not in vol_cols:
        conn.execute("ALTER TABLE volunteers ADD COLUMN fodder_support INTEGER DEFAULT 0;")
    if "medical_support" not in vol_cols:
        conn.execute("ALTER TABLE volunteers ADD COLUMN medical_support INTEGER DEFAULT 0;")
    if "shelter_support" not in vol_cols:
        conn.execute("ALTER TABLE volunteers ADD COLUMN shelter_support INTEGER DEFAULT 0;")

    # If users table is empty, seed demo accounts for immediate testing
    user_count = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    if user_count == 0:
        coord_hash = generate_password_hash("CoordPass123!")
        conn.execute("""
            INSERT INTO users (username, password_hash, role, full_name, phone, village)
            VALUES ('coord_admin', ?, 'Coordinator', 'Disaster Coordination Cell Lead', '9864000111', 'Majuli HQ')
        """, (coord_hash,))

        farmer_hash = generate_password_hash("FarmerPass123!")
        cur_f = conn.execute("""
            INSERT INTO users (username, password_hash, role, full_name, phone, village)
            VALUES ('farmer_ramesh', ?, 'Farmer', 'Rameshwar Saikia', '9864119988', 'Salmora')
        """, (farmer_hash,))
        farmer_uid = cur_f.lastrowid
        conn.execute("UPDATE farmers SET user_id = ? WHERE id = (SELECT id FROM farmers ORDER BY id ASC LIMIT 1)", (farmer_uid,))

        vol_hash = generate_password_hash("VolunteerPass123!")
        cur_v = conn.execute("""
            INSERT INTO users (username, password_hash, role, full_name, phone, village)
            VALUES ('volunteer_bhaben', ?, 'Volunteer', 'Bhaben Kalita', '9435112233', 'Kamalabari')
        """, (vol_hash,))
        vol_uid = cur_v.lastrowid
        conn.execute("UPDATE volunteers SET user_id = ? WHERE id = (SELECT id FROM volunteers ORDER BY id ASC LIMIT 1)", (vol_uid,))

    # Ensure demo accounts are safely linked to initial records if available
    farmer_user = conn.execute("SELECT id FROM users WHERE username = 'farmer_ramesh'").fetchone()
    if farmer_user:
        conn.execute("UPDATE farmers SET user_id = ? WHERE id = (SELECT id FROM farmers ORDER BY id ASC LIMIT 1) AND (user_id IS NULL OR user_id = 0)", (farmer_user["id"],))

    vol_user = conn.execute("SELECT id FROM users WHERE username = 'volunteer_bhaben'").fetchone()
    if vol_user:
        conn.execute("UPDATE volunteers SET user_id = ? WHERE id = (SELECT id FROM volunteers ORDER BY id ASC LIMIT 1) AND (user_id IS NULL OR user_id = 0)", (vol_user["id"],))

    conn.commit()

def init_db(db_path: str):
    """Initialize SQLite database tables and run safe migrations."""
    conn = get_db_connection(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        run_migrations(conn)
        conn.commit()
    finally:
        conn.close()

def mask_phone(phone: str) -> str:
    """Mask phone number for public privacy preservation (e.g. 9876543210 -> 98*** **210)."""
    if not phone:
        return "N/A"
    clean = "".join(ch for ch in str(phone) if ch.isalnum() or ch == "+")
    if len(clean) >= 10:
        return f"{clean[:2]}***-***{clean[-3:]}"
    elif len(clean) >= 6:
        return f"{clean[:2]}***{clean[-2:]}"
    return "***-***"

# ---- Dashboard Stats ----
def get_dashboard_stats(conn):
    """Aggregate high-level metrics for dashboard cards."""
    # Farmer & Livestock counts
    farmer_stats = conn.execute("""
        SELECT 
            COUNT(*) AS total_farms,
            COALESCE(SUM(animal_count), 0) AS total_livestock,
            COALESCE(SUM(cattle_count), 0) AS total_cattle,
            COALESCE(SUM(buffalo_count), 0) AS total_buffalo,
            COALESCE(SUM(other_count), 0) AS total_other,
            SUM(CASE WHEN rescue_status = 'Pending' THEN 1 ELSE 0 END) AS pending_farms,
            SUM(CASE WHEN rescue_status = 'In Progress' THEN 1 ELSE 0 END) AS in_progress_farms,
            SUM(CASE WHEN rescue_status IN ('Rescued', 'Safe in Shelter') THEN 1 ELSE 0 END) AS rescued_farms,
            SUM(CASE WHEN rescue_status = 'Pending' THEN animal_count ELSE 0 END) AS pending_livestock
        FROM farmers
    """).fetchone()

    # Active alerts
    alert_stats = conn.execute("""
        SELECT 
            COUNT(*) AS active_alerts_count,
            SUM(CASE WHEN severity = 'Critical' THEN 1 ELSE 0 END) AS critical_alerts
        FROM disaster_alerts
        WHERE status = 'Active'
    """).fetchone()

    # Volunteers & Transport
    vol_stats = conn.execute("""
        SELECT 
            COUNT(*) AS total_volunteers,
            SUM(CASE WHEN availability = 'Available' THEN 1 ELSE 0 END) AS available_volunteers,
            SUM(CASE WHEN resource_type = 'Vehicle' AND availability = 'Available' THEN 1 ELSE 0 END) AS available_vehicles,
            SUM(CASE WHEN resource_type = 'Vehicle' AND availability = 'Available' THEN capacity ELSE 0 END) AS total_vehicle_capacity
        FROM volunteers
    """).fetchone()

    # Shelters
    shelter_stats = conn.execute("""
        SELECT 
            COUNT(*) AS total_shelters,
            COALESCE(SUM(total_capacity), 0) AS total_capacity,
            COALESCE(SUM(occupied_capacity), 0) AS occupied_capacity,
            COALESCE(SUM(total_capacity - occupied_capacity), 0) AS available_capacity
        FROM shelters
    """).fetchone()

    return {
        "total_farms": farmer_stats["total_farms"] or 0,
        "total_livestock": farmer_stats["total_livestock"] or 0,
        "total_cattle": farmer_stats["total_cattle"] or 0,
        "total_buffalo": farmer_stats["total_buffalo"] or 0,
        "total_other": farmer_stats["total_other"] or 0,
        "pending_farms": farmer_stats["pending_farms"] or 0,
        "in_progress_farms": farmer_stats["in_progress_farms"] or 0,
        "rescued_farms": farmer_stats["rescued_farms"] or 0,
        "pending_livestock": farmer_stats["pending_livestock"] or 0,
        "active_alerts_count": alert_stats["active_alerts_count"] or 0,
        "critical_alerts": alert_stats["critical_alerts"] or 0,
        "total_volunteers": vol_stats["total_volunteers"] or 0,
        "available_volunteers": vol_stats["available_volunteers"] or 0,
        "available_vehicles": vol_stats["available_vehicles"] or 0,
        "total_vehicle_capacity": vol_stats["total_vehicle_capacity"] or 0,
        "total_shelters": shelter_stats["total_shelters"] or 0,
        "total_shelter_capacity": shelter_stats["total_capacity"] or 0,
        "occupied_shelter_capacity": shelter_stats["occupied_capacity"] or 0,
        "available_shelter_capacity": shelter_stats["available_capacity"] or 0,
    }

# ---- User Account & Authentication Operations ----
def create_user(conn, username, password, role, full_name, phone, village=""):
    """Create a new user with securely hashed password."""
    username = (username or "").strip().lower()
    if not username or len(username) < 3:
        raise ValueError("Username must be at least 3 characters.")
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    if role not in ("Farmer", "Volunteer", "Coordinator", "Admin"):
        raise ValueError(f"Invalid role: {role}")
    if not full_name or not full_name.strip():
        raise ValueError("Full name is required.")
    clean_phone = "".join(c for c in (phone or "") if c.isdigit())
    if len(clean_phone) < 10:
        raise ValueError("Valid 10-digit phone number is required.")

    existing = conn.execute("SELECT id FROM users WHERE LOWER(username) = ?", (username,)).fetchone()
    if existing:
        raise ValueError(f"Username '{username}' is already taken.")

    pwd_hash = generate_password_hash(password)
    cursor = conn.execute("""
        INSERT INTO users (username, password_hash, role, full_name, phone, village)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (username, pwd_hash, role, full_name.strip(), phone.strip(), village.strip()))
    conn.commit()
    return cursor.lastrowid

def authenticate_user(conn, username, password):
    """Authenticate user credentials using Werkzeug check_password_hash."""
    if not username or not password:
        return None
    user = conn.execute("SELECT * FROM users WHERE LOWER(username) = ?", (username.strip().lower(),)).fetchone()
    if not user:
        return None
    if check_password_hash(user["password_hash"], password):
        return dict(user)
    return None

def get_user_by_id(conn, user_id):
    """Retrieve user dictionary by primary key."""
    if not user_id:
        return None
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None

def get_user_by_username(conn, username):
    """Retrieve user dictionary by username."""
    if not username:
        return None
    row = conn.execute("SELECT * FROM users WHERE LOWER(username) = ?", (username.strip().lower(),)).fetchone()
    return dict(row) if row else None

def update_user_password(conn, user_id, current_password, new_password):
    """Change user password after verifying current password."""
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        raise ValueError("User not found.")
    if not check_password_hash(user["password_hash"], current_password):
        raise ValueError("Current password does not match.")
    if not new_password or len(new_password) < 6:
        raise ValueError("New password must be at least 6 characters.")
    
    new_hash = generate_password_hash(new_password)
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
    conn.commit()
    return True

def get_farmer_by_user_id(conn, user_id):
    """Retrieve farmer record linked to a specific user account."""
    if not user_id:
        return None
    return conn.execute("""
        SELECT f.*, 
               v.name AS volunteer_name, v.phone AS volunteer_phone,
               s.name AS shelter_name, s.village AS shelter_village
        FROM farmers f
        LEFT JOIN volunteers v ON f.assigned_volunteer_id = v.id
        LEFT JOIN shelters s ON f.assigned_shelter_id = s.id
        WHERE f.user_id = ?
        ORDER BY f.id DESC
        LIMIT 1
    """, (user_id,)).fetchone()

def update_farmer_for_user(conn, user_id, data):
    """Allow a farmer to update their own livestock numbers, risk needs, or location."""
    farmer = conn.execute("SELECT * FROM farmers WHERE user_id = ?", (user_id,)).fetchone()
    if not farmer:
        raise ValueError("No farmer record found for this user account.")

    cattle = int(data.get("cattle_count", farmer["cattle_count"]) or 0)
    buffalo = int(data.get("buffalo_count", farmer["buffalo_count"]) or 0)
    other = int(data.get("other_count", farmer["other_count"]) or 0)
    total = cattle + buffalo + other
    if total <= 0:
        raise ValueError("Total livestock count must be greater than zero.")

    special_needs = data.get("special_needs", farmer["special_needs"]).strip()
    priority = data.get("priority", farmer["priority"])
    village = data.get("village", farmer["village"]).strip()
    phone = data.get("phone", farmer["phone"]).strip()

    conn.execute("""
        UPDATE farmers
        SET cattle_count = ?, buffalo_count = ?, other_count = ?, animal_count = ?,
            special_needs = ?, priority = ?, village = ?, phone = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (cattle, buffalo, other, total, special_needs, priority, village, phone, farmer["id"]))
    conn.commit()
    return True

def get_volunteer_by_user_id(conn, user_id):
    """Retrieve volunteer record linked to a specific user account."""
    if not user_id:
        return None
    return conn.execute("SELECT * FROM volunteers WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()

def update_volunteer_for_user(conn, user_id, data):
    """Allow a volunteer to update their capacity, details, and availability."""
    vol = conn.execute("SELECT * FROM volunteers WHERE user_id = ?", (user_id,)).fetchone()
    if not vol:
        raise ValueError("No volunteer record found for this user account.")

    availability = data.get("availability", vol["availability"])
    capacity = int(data.get("capacity", vol["capacity"]) or 0)
    details = data.get("resource_details", vol["resource_details"]).strip()
    res_type = data.get("resource_type", vol["resource_type"]).strip()
    phone = data.get("phone", vol["phone"]).strip()

    conn.execute("""
        UPDATE volunteers
        SET availability = ?, capacity = ?, resource_details = ?, resource_type = ?, phone = ?
        WHERE id = ?
    """, (availability, capacity, details, res_type, phone, vol["id"]))
    conn.commit()
    return True

# ---- Farmers Operations ----
def add_farmer(conn, data, user_id=None):
    """Insert a new farmer registration with validation."""
    cattle = int(data.get("cattle_count", 0) or 0)
    buffalo = int(data.get("buffalo_count", 0) or 0)
    other = int(data.get("other_count", 0) or 0)
    animal_count = cattle + buffalo + other
    if animal_count <= 0:
        raise ValueError("Total livestock count must be greater than zero.")

    # Calculate default priority based on special needs
    special_needs = data.get("special_needs", "").strip()
    priority = data.get("priority", "Normal")
    if not priority or priority == "Normal":
        sn_lower = special_needs.lower()
        if any(term in sn_lower for term in ["water rising", "flooded", "trapped", "critical", "injured"]):
            priority = "Critical"
        elif any(term in sn_lower for term in ["pregnant", "calf", "calves", "sick", "elderly"]):
            priority = "High"

    assigned_uid = user_id if user_id is not None else data.get("user_id")

    cursor = conn.execute("""
        INSERT INTO farmers (
            user_id, name, phone, village, tehsil, district, latitude, longitude,
            livestock_type, cattle_count, buffalo_count, other_count,
            animal_count, special_needs, priority, rescue_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
    """, (
        assigned_uid,
        data["name"].strip(),
        data["phone"].strip(),
        data["village"].strip(),
        data.get("tehsil", "").strip(),
        data.get("district", "Majuli").strip(),
        float(data["latitude"]) if data.get("latitude") else None,
        float(data["longitude"]) if data.get("longitude") else None,
        data.get("livestock_type", "Mixed").strip(),
        cattle,
        buffalo,
        other,
        animal_count,
        special_needs,
        priority
    ))
    conn.commit()
    return cursor.lastrowid

def get_farmers(conn, village=None, livestock_type=None, rescue_status=None, search=None):
    """Retrieve farmers with optional filters."""
    query = """
        SELECT f.*, 
               v.name AS volunteer_name, v.phone AS volunteer_phone,
               s.name AS shelter_name, s.village AS shelter_village
        FROM farmers f
        LEFT JOIN volunteers v ON f.assigned_volunteer_id = v.id
        LEFT JOIN shelters s ON f.assigned_shelter_id = s.id
        WHERE 1=1
    """
    params = []
    if village:
        query += " AND LOWER(f.village) = LOWER(?)"
        params.append(village)
    if livestock_type and livestock_type != "All":
        query += " AND f.livestock_type = ?"
        params.append(livestock_type)
    if rescue_status and rescue_status != "All":
        query += " AND f.rescue_status = ?"
        params.append(rescue_status)
    if search:
        query += " AND (LOWER(f.name) LIKE LOWER(?) OR LOWER(f.village) LIKE LOWER(?) OR f.phone LIKE ?)"
        s_wild = f"%{search.strip()}%"
        params.extend([s_wild, s_wild, s_wild])

    query += " ORDER BY CASE f.priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 ELSE 3 END, f.id DESC"
    return conn.execute(query, params).fetchall()

def get_farmer_by_id(conn, farmer_id):
    """Retrieve single farmer by ID."""
    return conn.execute("""
        SELECT f.*, 
               v.name AS volunteer_name, v.phone AS volunteer_phone,
               s.name AS shelter_name
        FROM farmers f
        LEFT JOIN volunteers v ON f.assigned_volunteer_id = v.id
        LEFT JOIN shelters s ON f.assigned_shelter_id = s.id
        WHERE f.id = ?
    """, (farmer_id,)).fetchone()

# ---- Volunteers Operations ----
def add_volunteer(conn, data, user_id=None):
    """Insert a new volunteer resource."""
    assigned_uid = user_id if user_id is not None else data.get("user_id")
    cursor = conn.execute("""
        INSERT INTO volunteers (
            user_id, name, phone, organization, village, latitude, longitude,
            resource_type, resource_details, capacity, availability
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        assigned_uid,
        data["name"].strip(),
        data["phone"].strip(),
        data.get("organization", "Independent").strip(),
        data["village"].strip(),
        float(data["latitude"]) if data.get("latitude") else None,
        float(data["longitude"]) if data.get("longitude") else None,
        data["resource_type"].strip(),
        data.get("resource_details", "").strip(),
        int(data.get("capacity", 0) or 0),
        data.get("availability", "Available")
    ))
    conn.commit()
    return cursor.lastrowid

def get_volunteers(conn, resource_type=None, availability=None):
    """Retrieve volunteers with optional filters."""
    query = "SELECT * FROM volunteers WHERE 1=1"
    params = []
    if resource_type and resource_type != "All":
        query += " AND resource_type = ?"
        params.append(resource_type)
    if availability and availability != "All":
        query += " AND availability = ?"
        params.append(availability)
    query += " ORDER BY id DESC"
    return conn.execute(query, params).fetchall()

# ---- Shelters Operations ----
def get_shelters(conn):
    """Retrieve all emergency shelters with occupancy info."""
    return conn.execute("""
        SELECT *, (total_capacity - occupied_capacity) AS available_capacity
        FROM shelters
        ORDER BY available_capacity DESC
    """).fetchall()

def add_shelter(conn, data):
    """Add a new emergency livestock shelter."""
    cursor = conn.execute("""
        INSERT INTO shelters (
            name, village, location_notes, latitude, longitude,
            total_capacity, occupied_capacity, water_available, fodder_available,
            vet_available, contact_person, contact_phone
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["name"].strip(),
        data["village"].strip(),
        data.get("location_notes", "").strip(),
        float(data["latitude"]),
        float(data["longitude"]),
        int(data["total_capacity"]),
        int(data.get("occupied_capacity", 0)),
        1 if data.get("water_available") else 0,
        1 if data.get("fodder_available") else 0,
        1 if data.get("vet_available") else 0,
        data.get("contact_person", "").strip(),
        data.get("contact_phone", "").strip()
    ))
    conn.commit()
    return cursor.lastrowid

# ---- Disaster Alerts Operations ----
def add_disaster_alert(conn, data):
    """Create a new disaster alert and auto-escalate priority of affected farms."""
    cursor = conn.execute("""
        INSERT INTO disaster_alerts (
            title, disaster_type, affected_area, severity, description,
            latitude, longitude, radius_km, status, issued_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?)
    """, (
        data["title"].strip(),
        data["disaster_type"].strip(),
        data["affected_area"].strip(),
        data["severity"].strip(),
        data["description"].strip(),
        float(data["latitude"]) if data.get("latitude") else None,
        float(data["longitude"]) if data.get("longitude") else None,
        float(data.get("radius_km", 5.0) or 5.0),
        data.get("issued_by", "Disaster Coordination Cell").strip()
    ))
    alert_id = cursor.lastrowid

    # Elevate priority of any farm in the affected area if severity is High or Critical
    affected_villages = [v.strip().lower() for v in data["affected_area"].split(",") if v.strip()]
    if data["severity"] in ["High", "Critical"] and affected_villages:
        placeholders = ",".join("?" for _ in affected_villages)
        target_priority = "Critical" if data["severity"] == "Critical" else "High"
        conn.execute(f"""
            UPDATE farmers 
            SET priority = ?, updated_at = CURRENT_TIMESTAMP
            WHERE LOWER(village) IN ({placeholders}) AND rescue_status = 'Pending'
        """, [target_priority] + affected_villages)

    conn.commit()
    return alert_id

def get_disaster_alerts(conn, status=None):
    """Retrieve disaster alerts."""
    query = "SELECT * FROM disaster_alerts WHERE 1=1"
    params = []
    if status and status != "All":
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY CASE severity WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END, id DESC"
    return conn.execute(query, params).fetchall()

def resolve_disaster_alert(conn, alert_id):
    """Deactivate/Resolve a disaster alert."""
    conn.execute("""
        UPDATE disaster_alerts 
        SET status = 'Resolved', resolved_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (alert_id,))
    conn.commit()

# ---- Coordination & Resource Assignment ----
def assign_rescue_resource(conn, farmer_id, volunteer_id, shelter_id, notes="", coordinator_instructions="", assigned_by=None, **kwargs):
    """
    Coordinate rescue for a farm:
    - Atomically assign volunteer & shelter
    - Update farmer rescue_status to 'In Progress'
    - Update volunteer status to 'Deployed' (if provided)
    - Reserve shelter capacity for this farm's animals (if provided)
    - Record entry in rescue_assignments log
    """
    farmer = conn.execute("SELECT * FROM farmers WHERE id = ?", (farmer_id,)).fetchone()
    if not farmer:
        raise ValueError(f"Farmer with id {farmer_id} not found.")

    animal_count = farmer["animal_count"]

    # Verify shelter capacity if shelter assigned
    if shelter_id:
        shelter = conn.execute("SELECT * FROM shelters WHERE id = ?", (shelter_id,)).fetchone()
        if not shelter:
            raise ValueError(f"Shelter with id {shelter_id} not found.")
        remaining = shelter["total_capacity"] - shelter["occupied_capacity"]
        if remaining < animal_count:
            raise ValueError(
                f"Selected shelter '{shelter['name']}' has only {remaining} spaces available, "
                f"but {animal_count} animals need shelter."
            )

    # Verify volunteer availability if volunteer assigned
    vol_name = "None"
    if volunteer_id:
        vol = conn.execute("SELECT * FROM volunteers WHERE id = ?", (volunteer_id,)).fetchone()
        if not vol:
            raise ValueError(f"Volunteer with id {volunteer_id} not found.")
        if vol["availability"] != "Available":
            raise ValueError(
                f"Selected volunteer/resource '{vol['name']}' is currently '{vol['availability']}'. "
                f"Only available resources can be assigned."
            )
        vol_name = vol["name"]

    # 1. Update farmer
    conn.execute("""
        UPDATE farmers 
        SET assigned_volunteer_id = ?,
            assigned_shelter_id = ?,
            rescue_status = 'In Progress',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (volunteer_id, shelter_id, farmer_id))

    # 2. Update volunteer availability
    if volunteer_id:
        conn.execute("""
            UPDATE volunteers 
            SET availability = 'Deployed'
            WHERE id = ?
        """, (volunteer_id,))

    # 3. Update shelter occupied count
    shelter_name = "None"
    if shelter_id:
        conn.execute("""
            UPDATE shelters 
            SET occupied_capacity = occupied_capacity + ?
            WHERE id = ?
        """, (animal_count, shelter_id))
        shelter_name = shelter["name"]

    # 4. Insert assignment record
    instructions = (coordinator_instructions or notes or "").strip()
    cursor = conn.execute("""
        INSERT INTO rescue_assignments (
            farmer_id, volunteer_id, shelter_id, animals_transported, notes, coordinator_instructions, status, acceptance_status
        ) VALUES (?, ?, ?, ?, ?, ?, 'Assigned', 'Pending')
    """, (farmer_id, volunteer_id, shelter_id, animal_count, notes, instructions))

    conn.commit()

    log_activity(
        conn,
        action="Rescue Assigned",
        details=f"Assigned {vol_name} and shelter {shelter_name} to Farmer {farmer['name']} ({animal_count} animals). Instructions: {instructions}",
        username=assigned_by or "Coordinator",
        role="Coordinator"
    )

    return cursor.lastrowid

def update_rescue_status(conn, farmer_id, new_status):
    """
    Update rescue status of a farm ('Pending', 'In Progress', 'Rescued', 'Safe in Shelter').
    If moving to Rescued or Safe in Shelter, free up volunteer transport if assigned.
    """
    farmer = conn.execute("SELECT * FROM farmers WHERE id = ?", (farmer_id,)).fetchone()
    if not farmer:
        raise ValueError("Farmer not found.")

    conn.execute("""
        UPDATE farmers 
        SET rescue_status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_status, farmer_id))

    # Update latest assignment status
    conn.execute("""
        UPDATE rescue_assignments
        SET status = CASE ?
            WHEN 'Rescued' THEN 'Completed'
            WHEN 'Safe in Shelter' THEN 'Completed'
            ELSE 'In Transit'
        END,
        completed_at = CASE WHEN ? IN ('Rescued', 'Safe in Shelter') THEN CURRENT_TIMESTAMP ELSE NULL END
        WHERE farmer_id = ? AND status != 'Completed'
    """, (new_status, new_status, farmer_id))

    # If completed, free up volunteer availability to 'Available'
    if new_status in ["Rescued", "Safe in Shelter"] and farmer["assigned_volunteer_id"]:
        conn.execute("""
            UPDATE volunteers 
            SET availability = 'Available'
            WHERE id = ?
        """, (farmer["assigned_volunteer_id"],))

    conn.commit()

def get_recent_assignments(conn, limit=10):
    """Get recent rescue assignments for live feed."""
    return conn.execute("""
        SELECT r.*, 
               f.name AS farmer_name, f.village AS farmer_village, f.animal_count, f.livestock_type,
               v.name AS volunteer_name, v.resource_type AS volunteer_resource,
               s.name AS shelter_name
        FROM rescue_assignments r
        JOIN farmers f ON r.farmer_id = f.id
        LEFT JOIN volunteers v ON r.volunteer_id = v.id
        LEFT JOIN shelters s ON r.shelter_id = s.id
        ORDER BY r.id DESC
        LIMIT ?
    """, (limit,)).fetchall()

# ---- Activity Logging ----
def log_activity(conn, action: str = None, details: str = "", user_id: int = None, username: str = None, role: str = None, action_type: str = None, **kwargs):
    """Record an important operational action to the system activity log."""
    actual_action = action_type or action or "Activity"
    actual_details = details
    if action and action_type:
        actual_details = action
        actual_action = action_type
    try:
        conn.execute("""
            INSERT INTO activity_log (user_id, username, role, action, details)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username or "System", role or "System", actual_action, actual_details))
        conn.commit()
    except Exception as e:
        print(f"[ActivityLog] Error logging activity: {e}")

def get_activity_logs(conn, limit: int = 50):
    """Retrieve recent operational activity logs."""
    return conn.execute("""
        SELECT * FROM activity_log
        ORDER BY id DESC
        LIMIT ?
    """, (limit,)).fetchall()

# ---- Farmer Dashboard Workflows ----
def get_farmer_rescue_details(conn, farmer_id: int):
    """Retrieve full farmer profile joined with assigned volunteer and shelter data."""
    return conn.execute("""
        SELECT f.*,
               v.name AS vol_name, v.phone AS vol_phone, v.resource_type AS vol_resource,
               v.capacity AS vol_capacity, v.availability AS vol_status,
               s.name AS shelter_name, s.village AS shelter_village,
               s.total_capacity AS shelter_total, s.occupied_capacity AS shelter_occupied,
               s.water_available AS shelter_water, s.fodder_available AS shelter_fodder,
               s.vet_available AS shelter_vet, s.contact_person AS shelter_contact,
               s.contact_phone AS shelter_phone
        FROM farmers f
        LEFT JOIN volunteers v ON f.assigned_volunteer_id = v.id
        LEFT JOIN shelters s ON f.assigned_shelter_id = s.id
        WHERE f.id = ?
    """, (farmer_id,)).fetchone()

def submit_rescue_request(conn, farmer_id: int, urgency: str = "Critical", request_notes: str = "", animal_count: int = None, village: str = None, location: str = None, special_needs: str = None, notes: str = None, **kwargs):
    """Farmer submits or escalates an emergency evacuation request."""
    farmer = conn.execute("SELECT * FROM farmers WHERE id = ?", (farmer_id,)).fetchone()
    if not farmer:
        raise ValueError("Farmer not found.")

    urgency_val = urgency if urgency in ("Critical", "High", "Normal", "Urgent") else "High"
    if urgency_val == "Urgent":
        urgency_val = "Critical"
    anim_val = int(animal_count) if animal_count and int(animal_count) > 0 else farmer["animal_count"]
    vill_val = (location or village or farmer["village"]).strip()
    notes_val = (notes or request_notes or "").strip()
    s_needs = (special_needs or (farmer["special_needs"] if "special_needs" in farmer.keys() else "")).strip()

    conn.execute("""
        UPDATE farmers
        SET priority = ?,
            rescue_status = 'Requested',
            request_notes = ?,
            animal_count = ?,
            village = ?,
            special_needs = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (urgency_val, notes_val, anim_val, vill_val, s_needs, farmer_id))
    conn.commit()

    log_activity(
        conn,
        action="Rescue Requested",
        details=f"Farmer {farmer['name']} ({vill_val}) requested rescue for {anim_val} animals [Urgency: {urgency_val}]. Notes: {notes_val}",
        user_id=farmer["user_id"] if "user_id" in farmer.keys() else None,
        username=farmer["name"],
        role="Farmer"
    )
    return True

def verify_rescue_request(conn, farmer_id: int):
    """Rescue coordinator verifies and marks a farmer rescue request as verified."""
    farmer = conn.execute("SELECT * FROM farmers WHERE id = ?", (farmer_id,)).fetchone()
    if not farmer:
        raise ValueError("Farmer not found.")

    conn.execute("""
        UPDATE farmers
        SET rescue_status = 'Verified',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (farmer_id,))
    conn.commit()

    log_activity(
        conn,
        action="Request Verified",
        details=f"Rescue request for Farmer {farmer['name']} ({farmer['village']}) verified by coordinator.",
        role="Coordinator"
    )
    return True

def cancel_rescue_request(conn, farmer_id: int, reason: str = ""):
    """Cancel a rescue request (e.g. floodwaters receded or farmer safe)."""
    farmer = conn.execute("SELECT * FROM farmers WHERE id = ?", (farmer_id,)).fetchone()
    if not farmer:
        raise ValueError("Farmer not found.")

    vol_id = farmer["assigned_volunteer_id"]
    shelter_id = farmer["assigned_shelter_id"]

    conn.execute("""
        UPDATE farmers
        SET rescue_status = 'Cancelled',
            assigned_volunteer_id = NULL,
            assigned_shelter_id = NULL,
            request_notes = CASE WHEN ? != '' THEN ? ELSE request_notes END,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (reason, reason, farmer_id))

    if vol_id:
        conn.execute("UPDATE volunteers SET availability = 'Available' WHERE id = ?", (vol_id,))

    if shelter_id:
        conn.execute("""
            UPDATE shelters
            SET occupied_capacity = MAX(0, occupied_capacity - ?)
            WHERE id = ?
        """, (farmer["animal_count"], shelter_id))

    conn.execute("""
        UPDATE rescue_assignments
        SET status = 'Cancelled', completed_at = CURRENT_TIMESTAMP
        WHERE farmer_id = ? AND status NOT IN ('Completed', 'Cancelled')
    """, (farmer_id,))

    conn.commit()
    log_activity(
        conn,
        action="Request Cancelled",
        details=f"Rescue request for {farmer['name']} was cancelled. Reason: {reason or 'No reason provided'}",
        user_id=farmer["user_id"],
        username=farmer["name"],
        role="Farmer"
    )
    return True

# ---- Volunteer Dashboard Workflows ----
def get_volunteer_tasks(conn, volunteer_id: int):
    """Get active and completed tasks for a specific volunteer."""
    return conn.execute("""
        SELECT r.*,
               f.name AS farmer_name, f.phone AS farmer_phone, f.village AS farmer_village,
               f.animal_count, f.cattle_count, f.buffalo_count, f.special_needs,
               f.priority AS urgency, f.rescue_status, f.latitude AS farmer_lat, f.longitude AS farmer_lng,
               s.name AS shelter_name, s.village AS shelter_village,
               s.total_capacity AS shelter_total, s.occupied_capacity AS shelter_occupied,
               s.contact_person AS shelter_contact, s.contact_phone AS shelter_phone
        FROM rescue_assignments r
        JOIN farmers f ON r.farmer_id = f.id
        LEFT JOIN shelters s ON r.shelter_id = s.id
        WHERE r.volunteer_id = ?
        ORDER BY CASE r.status WHEN 'Assigned' THEN 1 WHEN 'In Progress' THEN 2 ELSE 3 END, r.id DESC
    """, (volunteer_id,)).fetchall()

def volunteer_respond_task(conn, assignment_id: int, volunteer_id: int, action: str, decline_reason: str = ""):
    """Volunteer accepts or declines an assigned rescue task."""
    assign = conn.execute("""
        SELECT r.*, f.name AS farmer_name, f.animal_count, v.name AS vol_name, v.user_id AS vol_user_id
        FROM rescue_assignments r
        JOIN farmers f ON r.farmer_id = f.id
        JOIN volunteers v ON r.volunteer_id = v.id
        WHERE r.id = ? AND r.volunteer_id = ?
    """, (assignment_id, volunteer_id)).fetchone()

    if not assign:
        raise ValueError("Assignment not found or you do not have permission to modify it.")

    act = (action or "").strip().lower()
    if act in ("accept", "accepted"):
        conn.execute("""
            UPDATE rescue_assignments
            SET acceptance_status = 'Accepted',
                status = 'In Progress'
            WHERE id = ?
        """, (assignment_id,))

        conn.execute("""
            UPDATE farmers
            SET rescue_status = 'In Progress',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (assign["farmer_id"],))

        conn.execute("""
            UPDATE volunteers
            SET availability = 'Deployed'
            WHERE id = ?
        """, (volunteer_id,))

        conn.commit()
        log_activity(
            conn,
            action="Task Accepted",
            details=f"Volunteer {assign['vol_name']} accepted rescue task for {assign['farmer_name']} ({assign['animal_count']} animals).",
            user_id=assign["vol_user_id"],
            username=assign["vol_name"],
            role="Volunteer"
        )
        return True

    elif act in ("decline", "declined"):
        reason = decline_reason.strip() or "Unavailable / Route Blocked"
        conn.execute("""
            UPDATE rescue_assignments
            SET acceptance_status = 'Declined',
                decline_reason = ?,
                status = 'Declined',
                completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (reason, assignment_id))

        conn.execute("""
            UPDATE farmers
            SET rescue_status = 'Verified',
                assigned_volunteer_id = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (assign["farmer_id"],))

        conn.execute("""
            UPDATE volunteers
            SET availability = 'Available'
            WHERE id = ?
        """, (volunteer_id,))

        # Free shelter capacity if reserved
        if assign["shelter_id"]:
            conn.execute("""
                UPDATE shelters
                SET occupied_capacity = MAX(0, occupied_capacity - ?)
                WHERE id = ?
            """, (assign["animal_count"], assign["shelter_id"]))

        conn.commit()
        log_activity(
            conn,
            action="Task Declined",
            details=f"Volunteer {assign['vol_name']} declined rescue task for {assign['farmer_name']}. Reason: {reason}",
            user_id=assign["vol_user_id"],
            username=assign["vol_name"],
            role="Volunteer"
        )
        return True
    else:
        raise ValueError(f"Invalid action specified: '{action}'.")

def volunteer_update_progress(conn, assignment_id: int, volunteer_id: int, rescue_status: str = "In Progress", animals_collected: int = 0, animals_delivered: int = 0, is_completed: bool = False, notes: str = "", **kwargs):
    """Volunteer updates animal rescue counts and marks evacuation progress."""
    assign = conn.execute("""
        SELECT r.*, f.name AS farmer_name, f.animal_count, v.name AS vol_name, v.user_id AS vol_user_id
        FROM rescue_assignments r
        JOIN farmers f ON r.farmer_id = f.id
        JOIN volunteers v ON r.volunteer_id = v.id
        WHERE r.id = ? AND r.volunteer_id = ?
    """, (assignment_id, volunteer_id)).fetchone()

    if not assign:
        raise ValueError("Assignment not found or you do not have permission to update it.")

    collected = max(0, int(animals_collected or 0))
    delivered = max(0, int(animals_delivered or 0))
    completed = is_completed or (rescue_status in ("Safe in Shelter", "Completed", "Rescued"))

    if completed:
        final_status = "Safe in Shelter" if rescue_status == "Safe in Shelter" else "Completed"
        conn.execute("""
            UPDATE rescue_assignments
            SET animals_collected = ?,
                animals_delivered = ?,
                status = 'Completed',
                notes = CASE WHEN ? != '' THEN ? ELSE notes END,
                completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (collected, delivered, notes, notes, assignment_id))

        conn.execute("""
            UPDATE farmers
            SET rescue_status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (final_status, assign["farmer_id"]))

        conn.execute("""
            UPDATE volunteers
            SET availability = 'Available'
            WHERE id = ?
        """, (volunteer_id,))

        conn.commit()
        log_activity(
            conn,
            action="Rescue Completed",
            details=f"Volunteer {assign['vol_name']} completed evacuation for {assign['farmer_name']} (Status: {final_status}). Animals delivered: {delivered}.",
            user_id=assign["vol_user_id"],
            username=assign["vol_name"],
            role="Volunteer"
        )
    else:
        conn.execute("""
            UPDATE rescue_assignments
            SET animals_collected = ?,
                animals_delivered = ?,
                status = ?,
                notes = CASE WHEN ? != '' THEN ? ELSE notes END
            WHERE id = ?
        """, (collected, delivered, rescue_status, notes, notes, assignment_id))

        conn.execute("""
            UPDATE farmers
            SET rescue_status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (rescue_status, assign["farmer_id"]))

        conn.commit()
        log_activity(
            conn,
            action="Progress Updated",
            details=f"Volunteer {assign['vol_name']} updated progress to '{rescue_status}': {collected} collected, {delivered} delivered for {assign['farmer_name']}.",
            user_id=assign["vol_user_id"],
            username=assign["vol_name"],
            role="Volunteer"
        )
    return True

def update_volunteer_availability(conn, volunteer_id: int, availability: str):
    """Set volunteer availability to 'Available', 'Busy', or 'Unavailable'."""
    if availability not in ("Available", "Busy", "Unavailable", "Deployed"):
        raise ValueError("Invalid availability status. Must be Available, Busy, or Unavailable.")

    vol = conn.execute("SELECT * FROM volunteers WHERE id = ?", (volunteer_id,)).fetchone()
    if not vol:
        raise ValueError("Volunteer not found.")

    conn.execute("UPDATE volunteers SET availability = ? WHERE id = ?", (availability, volunteer_id))
    conn.commit()

    log_activity(
        conn,
        action="Availability Changed",
        details=f"Volunteer {vol['name']} updated status to {availability}.",
        user_id=vol["user_id"],
        username=vol["name"],
        role="Volunteer"
    )
    return True

def update_volunteer_resource(conn, volunteer_id: int, data: dict):
    """Update volunteer equipment, transport capacity, and support resources."""
    vol = conn.execute("SELECT * FROM volunteers WHERE id = ?", (volunteer_id,)).fetchone()
    if not vol:
        raise ValueError("Volunteer not found.")

    conn.execute("""
        UPDATE volunteers
        SET resource_type = ?,
            resource_details = ?,
            capacity = ?,
            organization = ?,
            village = ?,
            water_support = ?,
            fodder_support = ?,
            medical_support = ?,
            shelter_support = ?
        WHERE id = ?
    """, (
        data.get("resource_type", vol["resource_type"]).strip(),
        data.get("resource_details", vol["resource_details"]).strip(),
        int(data.get("capacity", vol["capacity"]) or 0),
        data.get("organization", vol["organization"]).strip(),
        data.get("village", vol["village"]).strip(),
        1 if data.get("water_support") else 0,
        1 if data.get("fodder_support") else 0,
        1 if data.get("medical_support") else 0,
        1 if data.get("shelter_support") else 0,
        volunteer_id
    ))
    conn.commit()

    log_activity(
        conn,
        action="Resource Updated",
        details=f"Volunteer {vol['name']} updated resource equipment: {data.get('resource_type', vol['resource_type'])} (Capacity: {data.get('capacity', vol['capacity'])}).",
        user_id=vol["user_id"],
        username=vol["name"],
        role="Volunteer"
    )
    return True

# ---- Disaster Alerts Updates & Verification ----
def update_disaster_alert(conn, alert_id: int, data: dict):
    """Update disaster alert description, severity, and verification status."""
    conn.execute("""
        UPDATE disaster_alerts
        SET title = ?,
            disaster_type = ?,
            affected_area = ?,
            severity = ?,
            description = ?,
            source = ?,
            verification_status = ?,
            radius_km = ?
        WHERE id = ?
    """, (
        data["title"].strip(),
        data["disaster_type"].strip(),
        data["affected_area"].strip(),
        data["severity"].strip(),
        data["description"].strip(),
        data.get("source", "Disaster Coordination Cell").strip(),
        data.get("verification_status", "Verified").strip(),
        float(data.get("radius_km", 5.0) or 5.0),
        alert_id
    ))
    conn.commit()
    log_activity(
        conn,
        action="Alert Updated",
        details=f"Disaster alert #{alert_id} ({data['title']}) updated.",
        role="Coordinator"
    )
    return True

def verify_disaster_alert(conn, alert_id: int, verification_status: str = "Verified"):
    """Toggle or set disaster alert verification status."""
    conn.execute("UPDATE disaster_alerts SET verification_status = ? WHERE id = ?", (verification_status, alert_id))
    conn.commit()
    log_activity(
        conn,
        action="Alert Verification",
        details=f"Alert #{alert_id} verification status set to {verification_status}.",
        role="Coordinator"
    )
    return True

# ---- Coverage & Shortage Analysis (Requirement 5) ----
def get_coverage_shortage_analysis(conn):
    """
    Perform spatial & resource analysis to identify:
    - Villages with registered at-risk livestock having no active volunteer coverage
    - Transport capacity deficits vs pending animals needing evacuation
    - Shelters nearing or exceeding capacity
    - Food, water, and veterinary aid availability
    """
    # 1. Uncovered villages with pending rescue needs
    villages_with_requests = conn.execute("""
        SELECT village, COUNT(*) AS farm_count, SUM(animal_count) AS total_animals
        FROM farmers
        WHERE rescue_status IN ('Requested', 'Pending', 'Verified', 'Assigned', 'In Progress')
        GROUP BY village
    """).fetchall()

    volunteer_villages = [r["v"].lower() for r in conn.execute("""
        SELECT DISTINCT LOWER(village) AS v FROM volunteers WHERE availability = 'Available'
    """).fetchall()]

    uncovered_villages = []
    for v in villages_with_requests:
        if v["village"].lower() not in volunteer_villages:
            uncovered_villages.append({
                "village": v["village"],
                "farm_count": v["farm_count"],
                "total_animals": v["total_animals"]
            })

    # 2. Total pending animals needing transport
    pending_animals = conn.execute("""
        SELECT COALESCE(SUM(animal_count), 0) AS total
        FROM farmers
        WHERE rescue_status IN ('Requested', 'Pending', 'Verified')
    """).fetchone()["total"]

    # 3. Available transport capacity
    available_transport = conn.execute("""
        SELECT COALESCE(SUM(capacity), 0) AS total
        FROM volunteers
        WHERE resource_type = 'Vehicle' AND availability = 'Available'
    """).fetchone()["total"]

    # 4. Shelters near or at capacity (>=80% or <=10 spaces left)
    critical_shelters = conn.execute("""
        SELECT name, village, total_capacity, occupied_capacity,
               (total_capacity - occupied_capacity) AS remaining,
               ROUND((occupied_capacity * 100.0) / total_capacity, 1) AS pct_occupied
        FROM shelters
        WHERE (total_capacity - occupied_capacity) <= 15 OR (occupied_capacity * 1.0 / total_capacity) >= 0.75
        ORDER BY pct_occupied DESC
    """).fetchall()

    # 5. Resource supplies count
    fodder_count = conn.execute("SELECT COUNT(*) AS c FROM volunteers WHERE resource_type = 'Fodder' AND availability = 'Available'").fetchone()["c"]
    water_count = conn.execute("SELECT COUNT(*) AS c FROM volunteers WHERE (resource_type LIKE '%Water%' OR water_support = 1) AND availability = 'Available'").fetchone()["c"]
    vet_count = conn.execute("SELECT COUNT(*) AS c FROM volunteers WHERE (resource_type LIKE '%Vet%' OR medical_support = 1) AND availability = 'Available'").fetchone()["c"]

    return {
        "uncovered_villages": uncovered_villages,
        "pending_animals": pending_animals,
        "available_transport": available_transport,
        "transport_deficit": max(0, pending_animals - available_transport),
        "critical_shelters": critical_shelters,
        "fodder_available": fodder_count,
        "water_available": water_count,
        "vet_available": vet_count
    }
