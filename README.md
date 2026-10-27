# 🐄 JEEVANPATH — Livestock Disaster Rescue & Coordination Platform

> **Emergency Livestock Evacuation and Disaster Coordination Platform**  
> *A rapid emergency response network connecting rural livestock farmers, rescue transport volunteers, and disaster coordination teams during monsoon floods and natural disasters.*

---

## 🚨 Problem & Mission

During annual monsoon floods, cyclones, and sudden river embankment breaches across rural India (such as the Brahmaputra basin in Majuli, Assam, Bihar floodplains, and the Godavari delta), smallholder farmers face severe crises evacuating heavy livestock:
1. **Lack of Verified Local Information:** Farmers do not know which flood zones have breached or where elevated shelters are open.
2. **Transport Bottlenecks:** Farmers have large livestock (cattle and buffalo) but lack animal trailers, country boats, or high-clearance transport.
3. **Uncoordinated Volunteers:** Community volunteers offering boats, fodder, water, and manpower lack central task dispatching and destination shelter details.
4. **Shelter Overcrowding:** Flood relief shelters run out of space, fodder, or clean water without real-time capacity visibility.

**JEEVANPATH** solves this with three interconnected, real-time role-based dashboards powered by a unified database: **Farmer Dashboard**, **Volunteer Dashboard**, and **Rescue Team Dashboard**.

---

## 🛠️ Technology Stack

- **Backend:** Python 3.10+ with [Flask](https://flask.palletsprojects.com/)
- **Database:** SQLite3 with relational foreign keys, schema migrations, and parameterized SQL queries
- **Frontend:** HTML5, Vanilla CSS3 (custom dark/light modern UI design system with responsive cards, alert badges, and glassmorphism), and JavaScript
- **Interactive Map:** [Leaflet.js](https://leafletjs.com/) with OpenStreetMap tiles and custom status markers
- **Automated Tests:** [pytest](https://docs.pytest.org/) with 46 passing unit, integration, and workflow tests

---

## ⚡ Quick Start Instructions (Windows PowerShell)

### 1. Prerequisites
- Python 3.10 or higher (`python --version`)
- pip package manager (`python -m pip --version`)

### 2. Setup & Installation (Windows PowerShell)

```powershell
# Navigate into the project folder
cd "C:\Users\ASHWINI BALIGA\Downloads\jeevanpath"

# (Optional) Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install -r requirements.txt
```

### 3. Initialize / Seed Database
The SQLite database (`jeevanpath.db`) is automatically initialized and migrated on first run. To manually verify or re-seed:

```powershell
python seed_data.py
```

### 4. Create Initial Rescue Team / Admin Account
Rescue Team and Coordinator accounts **cannot be registered publicly** via web forms. Run the secure administrative provisioning utility:

```powershell
# Interactive mode (password entry is securely masked):
python create_admin.py

# Or via command-line arguments:
python create_admin.py --username lead_coordinator --password "RescuePass2026!" --name "District Disaster Response Lead" --phone 9864000111
```

### 5. Run Automated Tests
Execute the complete test suite of 46 automated tests:

```powershell
python -m pytest -v
```

### 6. Restart & Launch the Application

```powershell
# Stop any existing background Python process if needed:
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force

# Start the JEEVANPATH web application:
python app.py
```

Open your web browser and navigate to:  
👉 **`http://127.0.0.1:5000`**

---

## 🧭 The Three Connected Dashboards

JEEVANPATH provides three role-specific dashboards that communicate in real-time through a single shared SQLite database:

### 1. Farmer Dashboard — `/farmer/dashboard`
- **4 Key Overview Cards:** Registered Livestock, Pending Rescue Requests, Active Local Alerts, and Confirmed Safe Animals.
- **Livestock Census Management:** Add, view, and update cattle, buffalo, and other livestock counts, farm location, and care requirements (e.g. sick cattle, pregnant cows, young calves).
- **Emergency Rescue Dispatch:** Submit emergency requests specifying animal count, urgency (`Critical`, `High`, `Normal`), exact location, and distress notes.
- **Evacuation Stepper & Request Tracking:** Track status in real time: `Requested` ➔ `Verified` ➔ `Assigned` ➔ `In Progress` ➔ `Safe in Shelter` / `Completed` (or `Cancelled`).
- **Assigned Team & Shelter Destination:** View assigned volunteer contact number, vehicle specifications, destination shelter name, shelter capacity, and emergency caretaker phone.
- **Local Verified Alerts:** Live feed of verified disaster and flood warnings relevant to the farmer's village.
- **Profile & Password:** Secure password change and contact management.

### 2. Volunteer Dashboard — `/volunteer/dashboard`
- **4 Key Overview Cards:** Transport Capacity Offered, Active Assigned Tasks, Completed Evacuations, and Deployment Availability.
- **Resource & Capabilities Profile:** Manage vehicle/boat type, maximum animal capacity, base village, and support assistance checkboxes for clean water, fodder, emergency shelter, and veterinary assistance.
- **Availability Status Toggle:** Instantly toggle status between `Available`, `Busy`, or `Unavailable` (updates coordinator dispatch queue).
- **Assigned Tasks Queue:** Receive assigned rescues with farmer name, village pickup location, animal count, priority, and coordinator instructions.
- **Accept / Decline with Reason:** Accept assigned missions or decline with a required explanation (automatically frees the task back to the rescue coordinator).
- **Live Progress Updates:** Record animals collected from the farm, animals safely delivered to the shelter, and operational status (`In Progress` or `Safe in Shelter`).
- **Shelter Destination Info:** Direct access to destination shelter address, remaining free capacity, and shelter manager contact.

### 3. Rescue Team Command Dashboard — `/rescue/dashboard`
- **8 Command Metrics Cards:** Registered Farms, Total Livestock, Active Disaster Alerts, Pending Requests, Ongoing Evacuations, Animals Rescued, Available Volunteers, and Available Vehicles & Shelter Capacity.
- **Disaster Alerts Management:** Create, verify, update, and deactivate disaster alerts (with severity, affected area, coordinates, verification status, and ASDMA source).
- **Prioritized Rescue Queue:** Filter, search, and prioritize rescue requests by village, urgency, and status.
- **Capacity-Validated Dispatching:** Assign available volunteer vehicles and shelters with remaining capacity. Prevents assigning busy/unavailable volunteers or overbooking shelters.
- **Coverage & Shortage Analysis:** Real-time spatial analytics identifying:
  - Uncovered villages with at-risk livestock and no active volunteer vehicles.
  - Transport capacity deficits vs total pending animals.
  - Shelters nearing or exceeding full capacity.
- **Tactical GIS Map:** Interactive Leaflet map displaying danger zones, at-risk herds, volunteers, and shelters.
- **Activity Audit Log:** Persistent audit trail tracking all actions, timestamps, and coordinator usernames.

---

## 🔐 Authentication, Security & Permissions Matrix

| Feature | Logged-Out / Public | Farmer (`Farmer`) | Volunteer (`Volunteer`) | Rescue Team (`Coordinator`/`Admin`) |
| :--- | :---: | :---: | :---: | :---: |
| **Welcome Landing Page (`/`)** | Full Welcome View | Redirects to Dashboard | Redirects to Dashboard | Redirects to Dashboard |
| **Public Registration** | Farmer & Volunteer | ✕ | ✕ | ✕ (CLI / Restricted Only) |
| **Farmer Dashboard (`/farmer/dashboard`)** | ✕ (Redirects to Login) | Full Access (Own Data) | ✕ (HTTP 403 Forbidden) | Read / Review Access |
| **Volunteer Dashboard (`/volunteer/dashboard`)** | ✕ (Redirects to Login) | ✕ (HTTP 403 Forbidden) | Full Access (Own Data) | Read / Review Access |
| **Rescue Dashboard (`/rescue/dashboard`)** | ✕ (Redirects to Login) | ✕ (HTTP 403 Forbidden) | ✕ (HTTP 403 Forbidden) | Full Command & Dispatch |
| **Disaster Alert Issuance** | ✕ | ✕ | ✕ | Full Control |
| **Phone Number Privacy** | Masked (`98***-***210`) | Unmasked on Own Record | Unmasked on Own Record | Fully Unmasked |

---

## 🧪 Comprehensive Test Plan

### Step-by-Step Multi-Role Demonstration Workflow

Follow this procedure to verify all three roles and connected workflow:

#### Step 1: Welcome Page & Discreet Demo Accounts
1. Open `http://127.0.0.1:5000/` in an incognito or logged-out browser window.
2. Confirm the professional welcome page renders with prominent **Register as Farmer**, **Register as Volunteer**, and **Sign In** buttons.
3. Observe the discreet **Demo Accounts** helper box at the bottom of the sign-in card displaying pre-configured accounts:
   - Coordinator: `coord_admin` / `CoordPass123!`
   - Farmer: `farmer_ramesh` / `FarmerPass123!`
   - Volunteer: `volunteer_bhaben` / `VolunteerPass123!`

#### Step 2: Farmer Role Workflow
1. Click **"Register as Farmer"** (`/register/farmer`).
2. Register a new farmer account (e.g. `farmer_anil`, password `AnilPass123!`, 5 cattle, 2 buffalo in `Salmora`).
3. Verify that registration redirects to `/login` with a green success message.
4. Log in as `farmer_anil`. Confirm automatic redirection to `/farmer/dashboard`.
5. On the Farmer Dashboard, submit an emergency rescue request with urgency `Critical` and distress note `"Floodwaters rising near barn"`.
6. Confirm the lifecycle stepper updates to **Requested** with urgency **Critical**.

#### Step 3: Rescue Team Coordinator Workflow
1. In another browser or after logging out, sign in as `coord_admin` (password `CoordPass123!`).
2. Confirm automatic redirection to `/rescue/dashboard`.
3. Locate `farmer_anil` in the **Emergency Rescue Requests Queue**.
4. Click **"Verify & Prioritize"** to confirm the distress signal.
5. Click **"Dispatch Team"**: select an available volunteer (e.g. `Bhaben Kalita` - Rescue Boat) and shelter (e.g. `Garmur High Mound Shelter`).
6. Enter coordinator instructions: `"Bring animal harness and life vests"`. Click **"Deploy Evacuation Team"**.
7. Confirm that:
   - The farmer's status transitions to `In Progress`.
   - The volunteer's status updates to `Deployed`.
   - The shelter's occupied capacity increments by 7 animals.
   - An entry is recorded in the **Activity Audit Log**.

#### Step 4: Volunteer Role Workflow
1. Sign in as `volunteer_bhaben` (password `VolunteerPass123!`).
2. Confirm automatic redirection to `/volunteer/dashboard`.
3. Under **Assigned Rescue Tasks**, observe the new task for `farmer_anil` with pickup village `Salmora` and coordinator instructions.
4. Click **"Accept Task"**.
5. After conducting the evacuation, enter animals collected (`7`) and animals delivered (`7`), choose status **"Safe in Shelter"**, and submit **"Update Progress"**.

#### Step 5: End-to-End Verification
1. Sign back in as `farmer_anil` ➔ Observe the Farmer Dashboard displaying status **Safe in Shelter** with assigned destination shelter details.
2. Sign back in as `coord_admin` ➔ Observe the Rescue Team Dashboard showing updated livestock rescued count and volunteer `volunteer_bhaben` restored to `Available`.

---

## 🔒 Security & Privacy Guarantees

1. **Password Security:** Passwords hashed with Werkzeug `pbkdf2:sha256` with random salt. Plaintext passwords are never stored.
2. **Phone Number Privacy:** Phone numbers in public directories and APIs are masked (`98***-***210`) to prevent spam and exploitation. Unmasked contact details are displayed only to authorized rescue teams and assigned volunteers.
3. **Overbooking Prevention:** Database constraints and application validation prevent assigning offline/busy volunteers or dispatching livestock beyond remaining shelter capacity.
4. **Parameterized SQL:** All SQLite queries utilize parameterized placeholders (`?`) to prevent SQL injection vulnerabilities.
5. **CSRF Protection:** Cryptographic tokens validate all state-changing POST requests.
6. **No Phantom Claims:** Emergency disclaimers clearly state that simulated scenarios are for operational planning, advising real emergency callers to dial **112 / DDMA**.
