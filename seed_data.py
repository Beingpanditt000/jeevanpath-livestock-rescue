"""
Seed realistic Indian flood disaster scenario data for JEEVANPATH MVP.
Context: Majuli River Island & Brahmaputra Basin, Assam (frequent monsoon flood zone).
"""

import sqlite3
import os
from database import get_db_connection, init_db

SAMPLE_SHELTERS = [
    {
        "name": "Kamalabari Satra High Embankment Safe Yard",
        "village": "Kamalabari",
        "location_notes": "Elevated temple grounds with perimeter fencing, floodlights, and direct highway ramp.",
        "latitude": 26.9602,
        "longitude": 94.1685,
        "total_capacity": 85,
        "occupied_capacity": 22,
        "water_available": 1,
        "fodder_available": 1,
        "vet_available": 1,
        "contact_person": "Prabin Mahanta",
        "contact_phone": "9864012345"
    },
    {
        "name": "Garmur Higher Secondary School Ground (Elevated Mound)",
        "village": "Garmur",
        "location_notes": "Reinforced earthen mound built 4 meters above maximum recorded high flood level (HFL).",
        "latitude": 27.0215,
        "longitude": 94.2380,
        "total_capacity": 65,
        "occupied_capacity": 15,
        "water_available": 1,
        "fodder_available": 1,
        "vet_available": 1,
        "contact_person": "Jatin Dutta",
        "contact_phone": "9435098765"
    },
    {
        "name": "Jengraimukh Veterinary Sub-Centre Safe Pen",
        "village": "Jengraimukh",
        "location_notes": "Concrete floor shelter adjacent to Block Vet Dispensary with clean tubewell.",
        "latitude": 27.0780,
        "longitude": 94.2850,
        "total_capacity": 50,
        "occupied_capacity": 10,
        "water_available": 1,
        "fodder_available": 1,
        "vet_available": 1,
        "contact_person": "Dr. Naren Borah",
        "contact_phone": "9854067890"
    },
    {
        "name": "Auniati Community Relief High Ground",
        "village": "Auniati",
        "location_notes": "Open grazing plateau on stone-pitched river dyke with temporary bamboo sheds.",
        "latitude": 26.9450,
        "longitude": 94.1120,
        "total_capacity": 60,
        "occupied_capacity": 0,
        "water_available": 1,
        "fodder_available": 0,
        "vet_available": 0,
        "contact_person": "Bikash Saikia",
        "contact_phone": "9706034567"
    }
]

SAMPLE_VOLUNTEERS = [
    {
        "name": "Kisan Tractor Squad (Bhaben Kalita)",
        "phone": "9435112233",
        "organization": "Local Farmers Collective",
        "village": "Kamalabari",
        "latitude": 26.9620,
        "longitude": 94.1700,
        "resource_type": "Vehicle",
        "resource_details": "45HP Mahindra 4x4 Tractor with high-snorkel air intake & reinforced livestock trailer.",
        "capacity": 8,  # cattle capacity per trip
        "availability": "Available"
    },
    {
        "name": "Majuli Riverine Disaster Volunteers (Deep Jyoti)",
        "phone": "9864223344",
        "organization": "Majuli Water Rescue Cell",
        "village": "Salmora",
        "latitude": 26.9180,
        "longitude": 94.2250,
        "resource_type": "Vehicle",
        "resource_details": "Twin-engine motorized wooden cargo boat equipped with animal loading gangways.",
        "capacity": 12,
        "availability": "Available"
    },
    {
        "name": "Karuna Animal Welfare Mobile Rescue",
        "phone": "9706114455",
        "organization": "Karuna Animal Welfare Trust",
        "village": "Garmur",
        "latitude": 27.0200,
        "longitude": 94.2400,
        "resource_type": "Vehicle",
        "resource_details": "Hydraulic flatbed livestock transport truck with veterinary first-aid kit.",
        "capacity": 6,
        "availability": "Deployed"
    },
    {
        "name": "Brahmaputra Mitras Youth Wing (Hemanta)",
        "phone": "9854335566",
        "organization": "Village Youth Council",
        "village": "Rawanapar",
        "latitude": 26.9320,
        "longitude": 94.2050,
        "resource_type": "Fodder",
        "resource_details": "Stockpile of 200 bags dried paddy straw, green corn fodder & salt lick blocks.",
        "capacity": 200,
        "availability": "Available"
    },
    {
        "name": "Dr. Ananya Sarmah & Team (Mobile Vet)",
        "phone": "9435446677",
        "organization": "State Animal Husbandry Response Unit",
        "village": "Jengraimukh",
        "latitude": 27.0750,
        "longitude": 94.2880,
        "resource_type": "Water & First Aid",
        "resource_details": "Portable water purification unit, emergency antibiotics, trauma splints, tetanus serum.",
        "capacity": 50,
        "availability": "Available"
    },
    {
        "name": "Lakhimpur Emergency Transport (Ranbir Singh)",
        "phone": "9864557788",
        "organization": "Highway Logistics Aid",
        "village": "Kamalabari",
        "latitude": 26.9680,
        "longitude": 94.1620,
        "resource_type": "Vehicle",
        "resource_details": "Eicher 6-wheel cattle container lorry with safety padding.",
        "capacity": 10,
        "availability": "Available"
    }
]

SAMPLE_ALERTS = [
    {
        "title": "Brahmaputra Flash Surge — Embankment Breach near Salmora",
        "disaster_type": "River Breach",
        "affected_area": "Salmora, Rawanapar, Kamalabari",
        "severity": "Critical",
        "description": "Rapid water ingress following a 30-meter dyke breach on southern bank. Cattle sheds in low-lying char areas experiencing up to 1.5m water. Immediate tractor and boat evacuation mobilized.",
        "latitude": 26.9200,
        "longitude": 94.2200,
        "radius_km": 6.5,
        "issued_by": "DDMA Majuli Flood Cell"
    },
    {
        "title": "Subansiri Tributary Waterlogging Alert",
        "disaster_type": "Flood",
        "affected_area": "Jengraimukh, Bengenaati",
        "severity": "High",
        "description": "Heavy rainfall in upstream catchment causing backwater flooding in low paddies. Road connectivity threatened. Prepare livestock for movement to veterinary safe pen.",
        "latitude": 27.0700,
        "longitude": 94.2750,
        "radius_km": 4.5,
        "issued_by": "Sub-Divisional Flood Watch"
    }
]

SAMPLE_FARMERS = [
    {
        "name": "Rameshwar Saikia",
        "phone": "9864119988",
        "village": "Salmora",
        "tehsil": "Majuli Central",
        "district": "Majuli",
        "latitude": 26.9165,
        "longitude": 94.2230,
        "livestock_type": "Cattle",
        "cattle_count": 6,
        "buffalo_count": 0,
        "other_count": 0,
        "animal_count": 6,
        "special_needs": "2 pregnant Sahiwal cows; water rising 3 feet near sheds. Trapped on river bank.",
        "priority": "Critical",
        "rescue_status": "Pending"
    },
    {
        "name": "Bhupen Deka",
        "phone": "9435228877",
        "village": "Kamalabari",
        "tehsil": "Kamalabari",
        "district": "Majuli",
        "latitude": 26.9580,
        "longitude": 94.1650,
        "livestock_type": "Buffalo",
        "cattle_count": 0,
        "buffalo_count": 8,
        "other_count": 0,
        "animal_count": 8,
        "special_needs": "Heavy adult buffaloes, requires boat tether or tractor trailer.",
        "priority": "Critical",
        "rescue_status": "In Progress"
    },
    {
        "name": "Manorama Gogoi",
        "phone": "9706337766",
        "village": "Rawanapar",
        "tehsil": "Majuli South",
        "district": "Majuli",
        "latitude": 26.9310,
        "longitude": 94.2080,
        "livestock_type": "Mixed",
        "cattle_count": 4,
        "buffalo_count": 2,
        "other_count": 0,
        "animal_count": 6,
        "special_needs": "2 newborn calves unable to wade through mud.",
        "priority": "Critical",
        "rescue_status": "Pending"
    },
    {
        "name": "Tarun Bora",
        "phone": "9854446655",
        "village": "Bengenaati",
        "tehsil": "Jengraimukh",
        "district": "Majuli",
        "latitude": 27.0620,
        "longitude": 94.2680,
        "livestock_type": "Cattle",
        "cattle_count": 5,
        "buffalo_count": 0,
        "other_count": 0,
        "animal_count": 5,
        "special_needs": "1 cow with injured hoof; urgent veterinary wrap needed.",
        "priority": "High",
        "rescue_status": "Pending"
    },
    {
        "name": "Hemen Nath",
        "phone": "9435555544",
        "village": "Auniati",
        "tehsil": "Kamalabari",
        "district": "Majuli",
        "latitude": 26.9480,
        "longitude": 94.1160,
        "livestock_type": "Cattle",
        "cattle_count": 4,
        "buffalo_count": 0,
        "other_count": 0,
        "animal_count": 4,
        "special_needs": "Normal condition, situated near gravel dyke.",
        "priority": "Normal",
        "rescue_status": "Rescued"
    },
    {
        "name": "Pabitra Baruah",
        "phone": "9864664433",
        "village": "Garmur",
        "tehsil": "Garmur",
        "district": "Majuli",
        "latitude": 27.0240,
        "longitude": 94.2350,
        "livestock_type": "Buffalo",
        "cattle_count": 0,
        "buffalo_count": 6,
        "other_count": 0,
        "animal_count": 6,
        "special_needs": "Needs dry fodder and safe pen at school ground.",
        "priority": "Normal",
        "rescue_status": "Safe in Shelter"
    },
    {
        "name": "Minoti Das",
        "phone": "9706773322",
        "village": "Salmora",
        "tehsil": "Majuli Central",
        "district": "Majuli",
        "latitude": 26.9140,
        "longitude": 94.2280,
        "livestock_type": "Mixed",
        "cattle_count": 3,
        "buffalo_count": 3,
        "other_count": 0,
        "animal_count": 6,
        "special_needs": "Elderly farmer, needs physical volunteer hands to lead herd.",
        "priority": "Critical",
        "rescue_status": "Pending"
    },
    {
        "name": "Dhiren Chutia",
        "phone": "9854882211",
        "village": "Jengraimukh",
        "tehsil": "Jengraimukh",
        "district": "Majuli",
        "latitude": 27.0820,
        "longitude": 94.2820,
        "livestock_type": "Cattle",
        "cattle_count": 7,
        "buffalo_count": 0,
        "other_count": 0,
        "animal_count": 7,
        "special_needs": "River water entered grazing field; need transport trailer before nightfall.",
        "priority": "High",
        "rescue_status": "Pending"
    }
]

def seed_database(db_path: str):
    """Seed sample data if tables are currently empty."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        farmer_count = conn.execute("SELECT COUNT(*) AS c FROM farmers").fetchone()["c"]
        if farmer_count > 0:
            print(f"[Seed] Database at {db_path} already has {farmer_count} farmers. Skipping seed.")
            return

        print(f"[Seed] Seeding sample data into {db_path}...")

        # 1. Insert Shelters
        shelter_ids = []
        for s in SAMPLE_SHELTERS:
            cur = conn.execute("""
                INSERT INTO shelters (
                    name, village, location_notes, latitude, longitude,
                    total_capacity, occupied_capacity, water_available,
                    fodder_available, vet_available, contact_person, contact_phone
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                s["name"], s["village"], s["location_notes"], s["latitude"], s["longitude"],
                s["total_capacity"], s["occupied_capacity"], s["water_available"],
                s["fodder_available"], s["vet_available"], s["contact_person"], s["contact_phone"]
            ))
            shelter_ids.append(cur.lastrowid)

        # 2. Insert Volunteers
        volunteer_ids = []
        for v in SAMPLE_VOLUNTEERS:
            cur = conn.execute("""
                INSERT INTO volunteers (
                    name, phone, organization, village, latitude, longitude,
                    resource_type, resource_details, capacity, availability
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                v["name"], v["phone"], v["organization"], v["village"],
                v["latitude"], v["longitude"], v["resource_type"],
                v["resource_details"], v["capacity"], v["availability"]
            ))
            volunteer_ids.append(cur.lastrowid)

        # 3. Insert Alerts
        for a in SAMPLE_ALERTS:
            conn.execute("""
                INSERT INTO disaster_alerts (
                    title, disaster_type, affected_area, severity, description,
                    latitude, longitude, radius_km, status, issued_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?)
            """, (
                a["title"], a["disaster_type"], a["affected_area"], a["severity"],
                a["description"], a["latitude"], a["longitude"], a["radius_km"], a["issued_by"]
            ))

        # 4. Insert Farmers
        farmer_ids = []
        for f in SAMPLE_FARMERS:
            cur = conn.execute("""
                INSERT INTO farmers (
                    name, phone, village, tehsil, district, latitude, longitude,
                    livestock_type, cattle_count, buffalo_count, other_count,
                    animal_count, special_needs, priority, rescue_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f["name"], f["phone"], f["village"], f["tehsil"], f["district"],
                f["latitude"], f["longitude"], f["livestock_type"],
                f["cattle_count"], f["buffalo_count"], f["other_count"],
                f["animal_count"], f["special_needs"], f["priority"], f["rescue_status"]
            ))
            farmer_ids.append(cur.lastrowid)

        # 5. Insert Sample Demo Accounts (Coordinator, Farmer, Volunteer)
        from database import create_user
        try:
            coord_uid = create_user(
                conn,
                username="coord_admin",
                password="CoordPass123!",
                role="Coordinator",
                full_name="District Disaster Coordination Lead",
                phone="9864000111",
                village="Majuli HQ"
            )
        except ValueError:
            coord_user = conn.execute("SELECT id FROM users WHERE username = 'coord_admin'").fetchone()
            coord_uid = coord_user["id"] if coord_user else None

        try:
            farmer_uid = create_user(
                conn,
                username="farmer_ramesh",
                password="FarmerPass123!",
                role="Farmer",
                full_name="Rameshwar Saikia",
                phone="9864119988",
                village="Salmora"
            )
        except ValueError:
            f_user = conn.execute("SELECT id FROM users WHERE username = 'farmer_ramesh'").fetchone()
            farmer_uid = f_user["id"] if f_user else None

        # Link first farmer to this account
        if farmer_ids and farmer_uid:
            conn.execute("UPDATE farmers SET user_id = ? WHERE id = ?", (farmer_uid, farmer_ids[0]))

        try:
            vol_uid = create_user(
                conn,
                username="volunteer_bhaben",
                password="VolunteerPass123!",
                role="Volunteer",
                full_name="Bhaben Kalita",
                phone="9435112233",
                village="Kamalabari"
            )
        except ValueError:
            v_user = conn.execute("SELECT id FROM users WHERE username = 'volunteer_bhaben'").fetchone()
            vol_uid = v_user["id"] if v_user else None

        # Link first volunteer to this account
        if volunteer_ids and vol_uid:
            conn.execute("UPDATE volunteers SET user_id = ? WHERE id = ?", (vol_uid, volunteer_ids[0]))

        # 6. Link sample assignments for realistic live demonstration
        # Farmer 2 (Bhupen Deka) is In Progress with Karuna Mobile Rescue to Kamalabari Shelter
        if len(farmer_ids) >= 2 and len(volunteer_ids) >= 3 and len(shelter_ids) >= 1:
            conn.execute("""
                UPDATE farmers 
                SET assigned_volunteer_id = ?, assigned_shelter_id = ?
                WHERE id = ?
            """, (volunteer_ids[2], shelter_ids[0], farmer_ids[1]))
            conn.execute("""
                INSERT INTO rescue_assignments (
                    farmer_id, volunteer_id, shelter_id, animals_transported, notes, status
                ) VALUES (?, ?, ?, 8, 'Flatbed truck dispatched to Kamalabari ghat.', 'Assigned')
            """, (farmer_ids[1], volunteer_ids[2], shelter_ids[0]))

        # Farmer 6 (Pabitra Baruah) is Safe in Shelter (Garmur)
        if len(farmer_ids) >= 6 and len(shelter_ids) >= 2:
            conn.execute("""
                UPDATE farmers 
                SET assigned_shelter_id = ?
                WHERE id = ?
            """, (shelter_ids[1], farmer_ids[5]))
            conn.execute("""
                INSERT INTO rescue_assignments (
                    farmer_id, shelter_id, animals_transported, notes, status, completed_at
                ) VALUES (?, ?, 6, 'Completed evacuation to Garmur School high mound.', 'Completed', CURRENT_TIMESTAMP)
            """, (farmer_ids[5], shelter_ids[1]))

        conn.commit()
        print("[Seed] Successfully seeded realistic disaster response dataset.")
    finally:
        conn.close()

if __name__ == "__main__":
    from config import Config
    seed_database(Config.DATABASE_PATH)

