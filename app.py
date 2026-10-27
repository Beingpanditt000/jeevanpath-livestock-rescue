import os
import re
import secrets
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, session, g, abort
)
from config import Config
from database import (
    get_db_connection, init_db, mask_phone,
    get_dashboard_stats, add_farmer, get_farmers, get_farmer_by_id,
    add_volunteer, get_volunteers, get_shelters, add_shelter,
    add_disaster_alert, get_disaster_alerts, resolve_disaster_alert,
    assign_rescue_resource, update_rescue_status, get_recent_assignments,
    create_user, authenticate_user, get_user_by_id, get_user_by_username,
    update_user_password, get_farmer_by_user_id, update_farmer_for_user,
    get_volunteer_by_user_id, update_volunteer_for_user,
    log_activity, get_activity_logs, get_farmer_rescue_details,
    submit_rescue_request, verify_rescue_request, cancel_rescue_request,
    get_volunteer_tasks, volunteer_respond_task, volunteer_update_progress,
    update_volunteer_availability, update_volunteer_resource,
    update_disaster_alert, verify_disaster_alert, get_coverage_shortage_analysis
)
from seed_data import seed_database

def create_app(config_class=Config):
    """Application factory for JEEVANPATH Flask MVP."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Secure Cookie Settings
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")

    # Initialize and seed database if necessary
    db_path = app.config["DATABASE_PATH"]
    if db_path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        init_db(db_path)
        seed_database(db_path)
    else:
        # In-memory database (for testing)
        init_db(db_path)

    def get_db():
        if "db" not in g:
            g.db = get_db_connection(app.config["DATABASE_PATH"])
        return g.db

    @app.teardown_appcontext
    def close_db(exception=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    # --- Session & CSRF Security ---
    def get_csrf_token():
        if "_csrf_token" not in session:
            session["_csrf_token"] = secrets.token_hex(32)
        return session["_csrf_token"]

    @app.before_request
    def load_authenticated_user():
        uid = session.get("user_id")
        if uid:
            conn = get_db()
            g.user = get_user_by_id(conn, uid)
        else:
            g.user = None

    @app.before_request
    def csrf_protect():
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            # Skip CSRF check in tests if testing or CSRF explicitly disabled
            if app.config.get("TESTING") or app.config.get("WTF_CSRF_ENABLED") is False:
                return
            token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
            expected = session.get("_csrf_token")
            if not token or not expected or not secrets.compare_digest(token, expected):
                if request.is_json:
                    return jsonify({"error": "CSRF token missing or invalid."}), 400
                flash("Security verification failed (invalid CSRF token). Please try again.", "danger")
                return render_template("400.html", message="CSRF token validation failed. Please refresh and try again."), 400

    # Template context processor for global variables
    @app.context_processor
    def inject_globals():
        user = getattr(g, "user", None)
        is_coord = (user is not None and user.get("role") in ("Coordinator", "Admin")) or session.get("is_coordinator", False)
        is_farmer = user is not None and user.get("role") == "Farmer"
        is_vol = user is not None and user.get("role") == "Volunteer"
        return {
            "current_user": user,
            "is_authenticated": user is not None,
            "user_role": user.get("role") if user else None,
            "is_coordinator": is_coord,
            "is_farmer": is_farmer,
            "is_volunteer": is_vol,
            "csrf_token": get_csrf_token(),
            "mask_phone": mask_phone,
            "app_name": "JEEVANPATH",
            "prototype_disclaimer": "JEEVANPATH EMERGENCY RESPONSE — Disaster Coordination System (Preserving Livestock During Floods)",
        }

    # Validation Helpers
    def validate_phone(phone: str) -> bool:
        """Validate Indian mobile / general phone number (minimum 10 digits)."""
        clean = re.sub(r"[^\d]", "", phone or "")
        return len(clean) >= 10

    # --- Role-Based Authorization Decorators ---
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not getattr(g, "user", None):
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("login", next=request.path))
            return f(*args, **kwargs)
        return decorated_function

    def role_required(*allowed_roles):
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not getattr(g, "user", None):
                    flash("Please log in to access this page.", "warning")
                    return redirect(url_for("login", next=request.path))
                user_role = g.user.get("role")
                if user_role not in allowed_roles:
                    # Allow backwards-compatible coordinator session toggle
                    if "Coordinator" in allowed_roles and session.get("is_coordinator"):
                        return f(*args, **kwargs)
                    flash(f"Access denied: This section requires {' or '.join(allowed_roles)} privileges.", "danger")
                    return render_template("403.html"), 403
                return f(*args, **kwargs)
            return decorated_function
        return decorator

    # ------------------ AUTHENTICATION & ACCOUNTS ------------------

    @app.route("/login", methods=["GET", "POST"])
    def login():
        """User login with Werkzeug password hash verification."""
        if getattr(g, "user", None):
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            conn = get_db()
            user = authenticate_user(conn, username, password)

            if user:
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session["role"] = user["role"]
                # If coordinator, set coordinator mode session
                if user["role"] in ("Coordinator", "Admin"):
                    session["is_coordinator"] = True

                flash(f"Welcome back, {user['full_name']}! Signed in as {user['role']}.", "success")
                log_activity(conn, f"User '{user['username']}' ({user['role']}) signed in", user_id=user["id"], username=user["username"], action_type="User Signin")
                next_url = request.args.get("next")
                if next_url and next_url.startswith("/") and not next_url.startswith("//"):
                    return redirect(next_url)

                if user["role"] == "Farmer":
                    return redirect(url_for("farmer_dashboard"))
                elif user["role"] == "Volunteer":
                    return redirect(url_for("volunteer_dashboard"))
                return redirect(url_for("rescue_dashboard"))
            else:
                flash("Invalid username or password. Please verify your credentials.", "danger")

        return render_template("login.html", active_page="login")

    @app.route("/logout")
    def logout():
        """Log out user, clear session, and redirect to welcome/login page."""
        user = getattr(g, "user", None)
        if user:
            try:
                conn = get_db()
                log_activity(conn, f"User '{user['username']}' signed out", user_id=user["id"], username=user["username"], action_type="User Signout")
            except Exception:
                pass
        session.clear()
        flash("You have been securely signed out.", "info")
        return redirect(url_for("login"))

    @app.route("/register")
    def register():
        """Registration entry page."""
        return render_template("register.html", active_reg="farmer", active_page="register")

    @app.route("/register/farmer", methods=["GET", "POST"])
    def register_farmer():
        """Public Farmer registration with account credentials and livestock details."""
        if getattr(g, "user", None):
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            conn = get_db()
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            confirm_pwd = request.form.get("confirm_password", "").strip()
            full_name = request.form.get("full_name", "").strip()
            phone = request.form.get("phone", "").strip()
            village = request.form.get("village", "").strip()
            livestock_type = request.form.get("livestock_type", "Cattle").strip()
            cattle_count = request.form.get("cattle_count", 0)
            buffalo_count = request.form.get("buffalo_count", 0)
            other_count = request.form.get("other_count", 0)
            special_needs = request.form.get("special_needs", "").strip()
            latitude = request.form.get("latitude", "")
            longitude = request.form.get("longitude", "")

            errors = []
            if not username or len(username) < 3:
                errors.append("Username must be at least 3 characters.")
            if not full_name:
                errors.append("Farmer full name is required.")
            if not password or len(password) < 6:
                errors.append("Password must be at least 6 characters.")
            if password != confirm_pwd:
                errors.append("Passwords do not match.")
            if not validate_phone(phone):
                errors.append("Valid 10-digit contact phone number is required.")
            if not village:
                errors.append("Village is required.")

            try:
                c_cnt = int(cattle_count or 0)
                b_cnt = int(buffalo_count or 0)
                o_cnt = int(other_count or 0)
                total = c_cnt + b_cnt + o_cnt
                if total <= 0:
                    errors.append("Total livestock count must be greater than zero.")
            except ValueError:
                errors.append("Animal counts must be valid integers.")

            if errors:
                for err in errors:
                    flash(err, "danger")
            else:
                try:
                    uid = create_user(
                        conn,
                        username=username,
                        password=password,
                        role="Farmer",
                        full_name=full_name,
                        phone=phone,
                        village=village
                    )
                    data = {
                        "name": full_name,
                        "phone": phone,
                        "village": village,
                        "tehsil": request.form.get("tehsil", ""),
                        "district": request.form.get("district", "Majuli"),
                        "livestock_type": livestock_type,
                        "cattle_count": c_cnt,
                        "buffalo_count": b_cnt,
                        "other_count": o_cnt,
                        "special_needs": special_needs,
                        "latitude": latitude if latitude else None,
                        "longitude": longitude if longitude else None
                    }
                    add_farmer(conn, data, user_id=uid)

                    log_activity(conn, f"New Farmer registered: {full_name} ({village}) with {total} livestock", user_id=uid, username=username, action_type="Farmer Registration")
                    flash(f"Account registered successfully for {full_name}! Please sign in below.", "success")
                    return redirect(url_for("login"))
                except ValueError as ve:
                    flash(str(ve), "danger")
                except Exception as e:
                    flash(f"Registration failed: {str(e)}", "danger")

        return render_template("register.html", active_reg="farmer", active_page="register")

    @app.route("/register/volunteer", methods=["GET", "POST"])
    def register_volunteer():
        """Public Volunteer registration with offered resources."""
        if getattr(g, "user", None):
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            conn = get_db()
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            confirm_pwd = request.form.get("confirm_password", "").strip()
            full_name = request.form.get("full_name", "").strip()
            phone = request.form.get("phone", "").strip()
            organization = request.form.get("organization", "Independent").strip()
            village = request.form.get("village", "").strip()
            resource_type = request.form.get("resource_type", "Vehicle").strip()
            resource_details = request.form.get("resource_details", "").strip()
            capacity = request.form.get("capacity", 0)

            errors = []
            if not username or len(username) < 3:
                errors.append("Username must be at least 3 characters.")
            if not full_name:
                errors.append("Volunteer or organization name is required.")
            if not password or len(password) < 6:
                errors.append("Password must be at least 6 characters.")
            if password != confirm_pwd:
                errors.append("Passwords do not match.")
            if not validate_phone(phone):
                errors.append("Valid 10-digit phone number is required.")
            if not village:
                errors.append("Base village/location is required.")

            try:
                cap_val = int(capacity or 0)
                if cap_val < 0:
                    errors.append("Capacity cannot be negative.")
            except ValueError:
                errors.append("Capacity must be a valid integer.")

            if errors:
                for err in errors:
                    flash(err, "danger")
            else:
                try:
                    uid = create_user(
                        conn,
                        username=username,
                        password=password,
                        role="Volunteer",
                        full_name=full_name,
                        phone=phone,
                        village=village
                    )
                    data = {
                        "name": full_name,
                        "phone": phone,
                        "organization": organization,
                        "village": village,
                        "resource_type": resource_type,
                        "resource_details": resource_details,
                        "capacity": cap_val,
                        "availability": "Available"
                    }
                    add_volunteer(conn, data, user_id=uid)

                    log_activity(conn, f"New Volunteer registered: {full_name} ({village}) - {resource_type} (Capacity: {cap_val})", user_id=uid, username=username, action_type="Volunteer Registration")
                    flash(f"Account registered successfully for {full_name}! Please sign in below.", "success")
                    return redirect(url_for("login"))
                except ValueError as ve:
                    flash(str(ve), "danger")
                except Exception as e:
                    flash(f"Registration failed: {str(e)}", "danger")

        return render_template("register.html", active_reg="volunteer", active_page="register")

    @app.route("/change-password", methods=["GET", "POST"])
    @login_required
    def change_password():
        """Change password for authenticated user."""
        if request.method == "POST":
            conn = get_db()
            current_pwd = request.form.get("current_password", "")
            new_pwd = request.form.get("new_password", "")
            confirm_pwd = request.form.get("confirm_password", "")

            if not new_pwd or len(new_pwd) < 6:
                flash("New password must be at least 6 characters long.", "danger")
            elif new_pwd != confirm_pwd:
                flash("New passwords do not match.", "danger")
            else:
                try:
                    update_user_password(conn, g.user["id"], current_pwd, new_pwd)
                    flash("Your password has been changed successfully!", "success")
                    return redirect(url_for("dashboard"))
                except ValueError as ve:
                    flash(str(ve), "danger")
                except Exception as e:
                    flash(f"Password update failed: {str(e)}", "danger")

        return render_template("change_password.html", active_page="change_password")

    # ------------------ THREE CONNECTED ROLE-BASED DASHBOARDS ------------------

    @app.route("/farmer/dashboard", methods=["GET", "POST"])
    @role_required("Farmer", "Coordinator", "Admin")
    def farmer_dashboard():
        """Farmer self-service portal to manage livestock records, submit rescue requests, and track rescue lifecycle."""
        conn = get_db()
        farmer = get_farmer_by_user_id(conn, g.user["id"])

        # If coordinator/admin is testing farmer dashboard and has no linked farmer record, allow viewing first farmer
        if not farmer and g.user.get("role") in ("Coordinator", "Admin"):
            farmer_list = get_farmers(conn)
            farmer = farmer_list[0] if farmer_list else None

        farmer_id = farmer["id"] if farmer else None

        if request.method == "POST":
            action = request.form.get("action")
            if not farmer:
                flash("No livestock record currently linked to your account.", "danger")
                return redirect(url_for("farmer_dashboard"))

            if action == "request_rescue":
                try:
                    c_cnt = int(request.form.get("cattle_count") or farmer["cattle_count"])
                    b_cnt = int(request.form.get("buffalo_count") or farmer["buffalo_count"])
                    urgency = request.form.get("urgency", "Urgent")
                    location = request.form.get("location", farmer["village"]).strip()
                    default_sn = farmer["special_needs"] if "special_needs" in farmer.keys() else ""
                    special_needs = (request.form.get("special_needs") or default_sn).strip()
                    notes = request.form.get("notes", "").strip()

                    submit_rescue_request(
                        conn,
                        farmer["id"],
                        animal_count=c_cnt + b_cnt,
                        urgency=urgency,
                        location=location,
                        special_needs=special_needs,
                        notes=notes
                    )
                    log_activity(
                        conn,
                        f"Farmer {farmer['name']} requested rescue for {c_cnt + b_cnt} livestock (Priority: {urgency}) at {location}",
                        user_id=g.user["id"],
                        username=g.user["username"],
                        action_type="Rescue Request"
                    )
                    flash(f"🚨 Rescue request submitted! Urgency: {urgency}. Coordinators and volunteers have been alerted.", "success")
                except Exception as e:
                    flash(f"Failed to submit rescue request: {str(e)}", "danger")

            elif action == "cancel_request":
                try:
                    cancel_rescue_request(conn, farmer["id"])
                    log_activity(
                        conn,
                        f"Farmer {farmer['name']} cancelled rescue request #{farmer['id']}",
                        user_id=g.user["id"],
                        username=g.user["username"],
                        action_type="Rescue Cancelled"
                    )
                    flash("Rescue request has been cancelled.", "info")
                except Exception as e:
                    flash(f"Failed to cancel request: {str(e)}", "danger")

            elif action == "update_livestock":
                try:
                    update_farmer_for_user(conn, g.user["id"], request.form.to_dict())
                    log_activity(
                        conn,
                        f"Farmer {farmer['name']} updated livestock census records",
                        user_id=g.user["id"],
                        username=g.user["username"],
                        action_type="Livestock Updated"
                    )
                    flash("Livestock records and care requirements have been updated successfully.", "success")
                except ValueError as ve:
                    flash(str(ve), "danger")
                except Exception as e:
                    flash(f"Update failed: {str(e)}", "danger")

            return redirect(url_for("farmer_dashboard"))

        # Re-fetch farmer record after possible updates
        farmer = get_farmer_by_id(conn, farmer_id) if farmer_id else None
        rescue_details = get_farmer_rescue_details(conn, farmer_id) if farmer_id else None

        # Alerts relevant to farmer
        all_alerts = get_disaster_alerts(conn, status="Active")
        farmer_village = (farmer["village"] if farmer and "village" in farmer.keys() else "").lower()
        relevant_alerts = []
        for alert in all_alerts:
            aff = (alert["affected_area"] or "").lower() if "affected_area" in alert.keys() else ""
            v_status = alert["verification_status"] if "verification_status" in alert.keys() else ""
            if not farmer_village or farmer_village in aff or "majuli" in aff or "all" in aff or v_status == "Verified":
                relevant_alerts.append(alert)
        if not relevant_alerts and all_alerts:
            relevant_alerts = all_alerts[:3]

        total_animals = (farmer["cattle_count"] + farmer["buffalo_count"] + (farmer["other_count"] if "other_count" in farmer.keys() and farmer["other_count"] else 0)) if farmer else 0
        r_status = farmer["rescue_status"] if farmer and "rescue_status" in farmer.keys() else ""
        pending_count = 1 if r_status in ("Requested", "Pending", "Verified", "Assigned", "In Progress") else 0
        safe_count = total_animals if r_status in ("Rescued", "Safe in Shelter") else 0
        active_alerts_count = len(relevant_alerts)

        return render_template(
            "farmer_dashboard.html",
            farmer=farmer,
            rescue_details=rescue_details,
            relevant_alerts=relevant_alerts,
            total_animals=total_animals,
            pending_count=pending_count,
            safe_count=safe_count,
            active_alerts_count=active_alerts_count,
            active_page="farmer_dashboard"
        )

    @app.route("/my-livestock", methods=["GET", "POST"])
    @role_required("Farmer", "Coordinator", "Admin")
    def my_livestock():
        """Farmer self-service portal backward-compatible redirect and form handler."""
        if request.method == "POST":
            conn = get_db()
            action = request.form.get("action")
            if action == "update_details":
                try:
                    update_farmer_for_user(conn, g.user["id"], request.form.to_dict())
                    flash("Your livestock records and risk notes have been updated successfully.", "success")
                except Exception as e:
                    flash(f"Update failed: {str(e)}", "danger")
            return redirect(url_for("farmer_dashboard"))
        return redirect(url_for("farmer_dashboard"))

    @app.route("/volunteer/dashboard", methods=["GET", "POST"])
    @role_required("Volunteer", "Coordinator", "Admin")
    def volunteer_dashboard():
        """Volunteer dashboard: manage transport resources, set availability, accept/decline tasks, and update progress."""
        conn = get_db()
        volunteer = get_volunteer_by_user_id(conn, g.user["id"])
        if not volunteer and g.user.get("role") in ("Coordinator", "Admin"):
            vol_list = get_volunteers(conn)
            volunteer = vol_list[0] if vol_list else None

        volunteer_id = volunteer["id"] if volunteer else None

        if request.method == "POST":
            action = request.form.get("action")
            if not volunteer:
                flash("No volunteer resource currently linked to your account.", "danger")
                return redirect(url_for("volunteer_dashboard"))

            if action == "set_availability":
                new_avail = request.form.get("availability")
                if new_avail in ("Available", "Busy", "Unavailable"):
                    update_volunteer_availability(conn, volunteer["id"], new_avail)
                    log_activity(
                        conn,
                        f"Volunteer {volunteer['name']} set availability to {new_avail}",
                        user_id=g.user["id"],
                        username=g.user["username"],
                        action_type="Availability Changed"
                    )
                    flash(f"Availability updated to: {new_avail}", "success")
                return redirect(url_for("volunteer_dashboard"))

            elif action == "task_response":
                try:
                    assignment_id = int(request.form.get("assignment_id"))
                    response_status = request.form.get("response_status")  # 'Accepted' or 'Declined'
                    decline_reason = request.form.get("decline_reason", "").strip()
                    volunteer_respond_task(conn, assignment_id, volunteer["id"], response_status, decline_reason=decline_reason)
                    log_activity(
                        conn,
                        f"Volunteer {volunteer['name']} {response_status.lower()} rescue task #{assignment_id}" + (f" (Reason: {decline_reason})" if decline_reason else ""),
                        user_id=g.user["id"],
                        username=g.user["username"],
                        action_type=f"Task {response_status}"
                    )
                    flash(f"Task #{assignment_id} {response_status.lower()} successfully.", "success" if response_status == "Accepted" else "info")
                except Exception as e:
                    flash(f"Response failed: {str(e)}", "danger")
                return redirect(url_for("volunteer_dashboard"))

            elif action == "update_progress":
                try:
                    assignment_id = int(request.form.get("assignment_id"))
                    rescue_status = request.form.get("rescue_status", "In Progress")
                    collected = int(request.form.get("animals_collected") or 0)
                    delivered = int(request.form.get("animals_delivered") or 0)
                    notes = request.form.get("notes", "").strip()
                    volunteer_update_progress(
                        conn,
                        assignment_id,
                        volunteer["id"],
                        rescue_status,
                        animals_collected=collected,
                        animals_delivered=delivered,
                        notes=notes
                    )
                    log_activity(
                        conn,
                        f"Volunteer {volunteer['name']} updated task #{assignment_id} progress: {rescue_status} (Collected: {collected}, Delivered: {delivered})",
                        user_id=g.user["id"],
                        username=g.user["username"],
                        action_type="Progress Update"
                    )
                    flash(f"Rescue operation progress updated to: {rescue_status}.", "success")
                except Exception as e:
                    flash(f"Progress update failed: {str(e)}", "danger")
                return redirect(url_for("volunteer_dashboard"))

            elif action == "update_resource":
                try:
                    update_volunteer_resource(conn, volunteer["id"], request.form.to_dict())
                    log_activity(
                        conn,
                        f"Volunteer {volunteer['name']} updated transport specifications & assistance capabilities",
                        user_id=g.user["id"],
                        username=g.user["username"],
                        action_type="Resource Profile Updated"
                    )
                    flash("Resource profile and support capabilities updated successfully.", "success")
                except ValueError as ve:
                    flash(str(ve), "danger")
                except Exception as e:
                    flash(f"Update failed: {str(e)}", "danger")
                return redirect(url_for("volunteer_dashboard"))

        # Re-fetch volunteer after possible updates
        volunteer = get_volunteer_by_user_id(conn, g.user["id"]) if (g.user and "role" in g.user.keys() and g.user["role"] == "Volunteer") else (get_volunteers(conn)[0] if get_volunteers(conn) else None)
        tasks = get_volunteer_tasks(conn, volunteer_id) if volunteer_id else []
        assigned_count = 0
        completed_count = 0
        for t in tasks:
            acc_status = t["acceptance_status"] if "acceptance_status" in t.keys() else ""
            f_status = t["farmer_status"] if "farmer_status" in t.keys() else ""
            if f_status in ("Rescued", "Safe in Shelter"):
                completed_count += 1
            elif acc_status in ("Pending", "Accepted"):
                assigned_count += 1

        available_resources_count = volunteer["capacity"] if (volunteer and "capacity" in volunteer.keys()) else 0
        current_avail = volunteer["availability"] if (volunteer and "availability" in volunteer.keys()) else "Available"

        return render_template(
            "volunteer_dashboard.html",
            volunteer=volunteer,
            tasks=tasks,
            assigned_count=assigned_count,
            completed_count=completed_count,
            available_resources_count=available_resources_count,
            current_avail=current_avail,
            active_page="volunteer_dashboard"
        )

    @app.route("/my-resource", methods=["GET", "POST"])
    @role_required("Volunteer", "Coordinator", "Admin")
    def my_resource():
        """Volunteer self-service portal backward-compatible redirect and form handler."""
        if request.method == "POST":
            conn = get_db()
            action = request.form.get("action")
            volunteer = get_volunteer_by_user_id(conn, g.user["id"])
            if volunteer and action == "set_availability":
                new_avail = request.form.get("availability")
                conn.execute("UPDATE volunteers SET availability = ? WHERE id = ?", (new_avail, volunteer["id"]))
                conn.commit()
                flash(f"Deployment status updated to: {new_avail}", "success")
            return redirect(url_for("volunteer_dashboard"))
        return redirect(url_for("volunteer_dashboard"))

    @app.route("/rescue/dashboard", methods=["GET", "POST"])
    @role_required("Coordinator", "Admin")
    def rescue_dashboard():
        """Command Center Rescue Team Dashboard: Overview metrics, alerts, request prioritization, dispatching, shortage analysis, and activity audit log."""
        conn = get_db()

        if request.method == "POST":
            action = request.form.get("action")

            if action == "create_alert":
                title = request.form.get("title", "").strip()
                disaster_type = request.form.get("disaster_type", "Flood").strip()
                affected_area = request.form.get("affected_area", "").strip()
                severity = request.form.get("severity", "High").strip()
                description = request.form.get("description", "").strip()
                source = request.form.get("source", "Assam State Disaster Management Authority (ASDMA)").strip()
                verification_status = request.form.get("verification_status", "Verified")
                radius_km = float(request.form.get("radius_km") or 5.0)
                lat = float(request.form.get("latitude") or 26.9800)
                lon = float(request.form.get("longitude") or 94.2100)

                if not title or not affected_area or not description:
                    flash("Alert title, affected area, and description are required.", "danger")
                else:
                    data = {
                        "title": title,
                        "disaster_type": disaster_type,
                        "affected_area": affected_area,
                        "severity": severity,
                        "description": description,
                        "source": source,
                        "verification_status": verification_status,
                        "radius_km": radius_km,
                        "latitude": lat,
                        "longitude": lon,
                        "issued_by": f"Coordinator ({g.user['username']})"
                    }
                    alert_id = add_disaster_alert(conn, data)
                    log_activity(
                        conn,
                        f"Created {verification_status} alert '{title}' ({severity}) for {affected_area}",
                        user_id=g.user["id"],
                        username=g.user["username"],
                        action_type="Disaster Alert Created"
                    )
                    flash(f"Disaster alert '{title}' broadcasted to response teams.", "success")
                return redirect(url_for("rescue_dashboard"))

            elif action == "verify_alert":
                try:
                    alert_id = int(request.form.get("alert_id"))
                    v_status = request.form.get("verification_status", "Verified")
                    verify_disaster_alert(conn, alert_id, v_status)
                    log_activity(
                        conn,
                        f"Alert #{alert_id} verification status changed to '{v_status}'",
                        user_id=g.user["id"],
                        username=g.user["username"],
                        action_type="Alert Verified"
                    )
                    flash(f"Alert #{alert_id} updated to {v_status}.", "info")
                except Exception as e:
                    flash(f"Failed to update alert verification: {str(e)}", "danger")
                return redirect(url_for("rescue_dashboard"))

            elif action == "deactivate_alert":
                try:
                    alert_id = int(request.form.get("alert_id"))
                    resolve_disaster_alert(conn, alert_id)
                    log_activity(
                        conn,
                        f"Deactivated disaster alert #{alert_id}",
                        user_id=g.user["id"],
                        username=g.user["username"],
                        action_type="Alert Deactivated"
                    )
                    flash(f"Alert #{alert_id} deactivated successfully.", "info")
                except Exception as e:
                    flash(f"Failed to deactivate alert: {str(e)}", "danger")
                return redirect(url_for("rescue_dashboard"))

            elif action == "verify_request":
                try:
                    farmer_id = int(request.form.get("farmer_id"))
                    priority = request.form.get("priority", "High")
                    verify_rescue_request(conn, farmer_id, priority=priority)
                    log_activity(
                        conn,
                        f"Verified and prioritized rescue request #{farmer_id} as {priority}",
                        user_id=g.user["id"],
                        username=g.user["username"],
                        action_type="Request Verified"
                    )
                    flash(f"Rescue request #{farmer_id} verified and prioritized as {priority}.", "success")
                except Exception as e:
                    flash(f"Verification failed: {str(e)}", "danger")
                return redirect(url_for("rescue_dashboard"))

            elif action == "assign_resources":
                try:
                    farmer_id = int(request.form.get("farmer_id"))
                    volunteer_id = int(request.form.get("volunteer_id")) if request.form.get("volunteer_id") else None
                    shelter_id = int(request.form.get("shelter_id")) if request.form.get("shelter_id") else None
                    notes = request.form.get("notes", "").strip()
                    instructions = request.form.get("coordinator_instructions", "").strip()

                    assign_rescue_resource(
                        conn,
                        farmer_id,
                        volunteer_id,
                        shelter_id,
                        notes=notes,
                        coordinator_instructions=instructions,
                        assigned_by=g.user["username"]
                    )
                    log_activity(
                        conn,
                        f"Dispatched team to Farmer #{farmer_id}: Vol #{volunteer_id}, Shelter #{shelter_id}",
                        user_id=g.user["id"],
                        username=g.user["username"],
                        action_type="Resource Dispatched"
                    )
                    flash("Evacuation resources dispatched successfully! Assigned volunteer notified.", "success")
                except ValueError as ve:
                    flash(f"Dispatch Rejected: {str(ve)}", "danger")
                except Exception as e:
                    flash(f"Dispatch failed: {str(e)}", "danger")
                return redirect(url_for("rescue_dashboard"))

            elif action == "update_request_status":
                try:
                    farmer_id = int(request.form.get("farmer_id"))
                    new_status = request.form.get("new_status")
                    update_rescue_status(conn, farmer_id, new_status)
                    log_activity(
                        conn,
                        f"Coordinator updated Farmer #{farmer_id} status to '{new_status}'",
                        user_id=g.user["id"],
                        username=g.user["username"],
                        action_type="Status Updated"
                    )
                    flash(f"Farmer #{farmer_id} status updated to: {new_status}", "success")
                except Exception as e:
                    flash(f"Failed to update status: {str(e)}", "danger")
                return redirect(url_for("rescue_dashboard"))

        # GET request with filters
        req_village = request.args.get("village", "").strip()
        req_urgency = request.args.get("urgency", "").strip()
        req_status = request.args.get("status", "").strip()

        all_farmers = get_farmers(conn)
        filtered_farmers = []
        for f in all_farmers:
            if req_village and f["village"] != req_village:
                continue
            if req_urgency and f["priority"] != req_urgency:
                continue
            if req_status and f["rescue_status"] != req_status:
                continue
            filtered_farmers.append(f)

        stats = get_dashboard_stats(conn)
        alerts = get_disaster_alerts(conn)
        volunteers = get_volunteers(conn)
        available_volunteers = [v for v in volunteers if v["availability"] == "Available"]
        shelters = get_shelters(conn)
        coverage_analysis = get_coverage_shortage_analysis(conn)
        activity_logs = get_activity_logs(conn, limit=30)
        villages = sorted(list(set(f["village"] for f in all_farmers if "village" in f.keys() and f["village"])))

        return render_template(
            "rescue_dashboard.html",
            stats=stats,
            alerts=alerts,
            volunteers=volunteers,
            available_volunteers=available_volunteers,
            shelters=shelters,
            farmers=filtered_farmers,
            villages=villages,
            coverage=coverage_analysis,
            coverage_analysis=coverage_analysis,
            activity_logs=activity_logs,
            selected_village=req_village,
            selected_urgency=req_urgency,
            selected_status=req_status,
            active_page="rescue_dashboard"
        )

    # ------------------ PAGES & ROUTES ------------------

    @app.route("/")
    @app.route("/dashboard")
    def dashboard():
        """Welcome landing page for anonymous users; role dashboard router for authenticated users."""
        conn = get_db()
        stats = get_dashboard_stats(conn)
        user = getattr(g, "user", None)

        if not user:
            # Welcome page for logged-out visitors with clear Register/Login and demo testing helper
            return render_template("welcome.html", stats=stats, active_page="welcome")

        # Authenticated user routing
        if user.get("role") == "Farmer":
            return redirect(url_for("farmer_dashboard"))
        elif user.get("role") == "Volunteer":
            return redirect(url_for("volunteer_dashboard"))
        else:
            return redirect(url_for("rescue_dashboard"))

    @app.route("/farmers", methods=["GET", "POST"])
    @login_required
    def farmers():
        """Farmer directory & registration."""
        conn = get_db()

        if request.method == "POST":
            # Only coordinators can register other farmers from general directory
            user_role = g.user.get("role")
            if user_role not in ("Coordinator", "Admin") and not session.get("is_coordinator"):
                flash("Only Coordinators can register third-party farmers from this view.", "danger")
                return render_template("403.html"), 403

            name = request.form.get("name", "").strip()
            phone = request.form.get("phone", "").strip()
            village = request.form.get("village", "").strip()
            livestock_type = request.form.get("livestock_type", "Cattle").strip()
            cattle_count = request.form.get("cattle_count", 0)
            buffalo_count = request.form.get("buffalo_count", 0)
            other_count = request.form.get("other_count", 0)
            special_needs = request.form.get("special_needs", "").strip()
            latitude = request.form.get("latitude", "")
            longitude = request.form.get("longitude", "")

            errors = []
            if not name:
                errors.append("Farmer name is required.")
            if not validate_phone(phone):
                errors.append("Valid 10-digit phone number is required.")
            if not village:
                errors.append("Village name is required.")

            try:
                c_cnt = int(cattle_count or 0)
                b_cnt = int(buffalo_count or 0)
                o_cnt = int(other_count or 0)
                total = c_cnt + b_cnt + o_cnt
                if total <= 0:
                    errors.append("At least one animal count must be greater than zero.")
            except ValueError:
                errors.append("Animal counts must be valid integers.")

            if errors:
                for err in errors:
                    flash(err, "danger")
            else:
                try:
                    data = {
                        "name": name,
                        "phone": phone,
                        "village": village,
                        "tehsil": request.form.get("tehsil", ""),
                        "district": request.form.get("district", "Majuli"),
                        "livestock_type": livestock_type,
                        "cattle_count": c_cnt,
                        "buffalo_count": b_cnt,
                        "other_count": o_cnt,
                        "special_needs": special_needs,
                        "latitude": latitude if latitude else None,
                        "longitude": longitude if longitude else None
                    }
                    add_farmer(conn, data)
                    flash(f"Farmer {name} with {total} livestock registered successfully!", "success")
                    return redirect(url_for("farmers"))
                except Exception as e:
                    flash(f"Error registering farmer: {str(e)}", "danger")

        # GET request with optional filters
        village_filter = request.args.get("village", "")
        livestock_filter = request.args.get("livestock_type", "")
        status_filter = request.args.get("rescue_status", "")
        search_query = request.args.get("q", "")

        farmer_list = get_farmers(
            conn,
            village=village_filter if village_filter else None,
            livestock_type=livestock_filter if livestock_filter else None,
            rescue_status=status_filter if status_filter else None,
            search=search_query if search_query else None
        )

        villages = [row["village"] for row in conn.execute(
            "SELECT DISTINCT village FROM farmers ORDER BY village ASC"
        ).fetchall()]

        return render_template(
            "farmers.html",
            farmers=farmer_list,
            villages=villages,
            selected_village=village_filter,
            selected_type=livestock_filter,
            selected_status=status_filter,
            search_query=search_query,
            active_page="farmers"
        )

    @app.route("/volunteers", methods=["GET", "POST"])
    @login_required
    def volunteers():
        """Volunteer and rescue resource directory & registration."""
        conn = get_db()

        if request.method == "POST":
            user_role = g.user.get("role")
            if user_role not in ("Coordinator", "Admin") and not session.get("is_coordinator"):
                flash("Only Coordinators can register third-party volunteers from this view.", "danger")
                return render_template("403.html"), 403

            name = request.form.get("name", "").strip()
            phone = request.form.get("phone", "").strip()
            organization = request.form.get("organization", "Independent").strip()
            village = request.form.get("village", "").strip()
            resource_type = request.form.get("resource_type", "Vehicle").strip()
            resource_details = request.form.get("resource_details", "").strip()
            capacity = request.form.get("capacity", 0)
            availability = request.form.get("availability", "Available").strip()
            latitude = request.form.get("latitude", "")
            longitude = request.form.get("longitude", "")

            errors = []
            if not name:
                errors.append("Volunteer or organization name is required.")
            if not validate_phone(phone):
                errors.append("Valid 10-digit phone number is required.")
            if not village:
                errors.append("Village or operating base is required.")
            try:
                cap_val = int(capacity or 0)
                if cap_val < 0:
                    errors.append("Capacity cannot be negative.")
            except ValueError:
                errors.append("Capacity must be a valid integer.")

            if errors:
                for err in errors:
                    flash(err, "danger")
            else:
                try:
                    data = {
                        "name": name,
                        "phone": phone,
                        "organization": organization,
                        "village": village,
                        "resource_type": resource_type,
                        "resource_details": resource_details,
                        "capacity": cap_val,
                        "availability": availability,
                        "latitude": latitude if latitude else None,
                        "longitude": longitude if longitude else None
                    }
                    add_volunteer(conn, data)
                    flash(f"Resource '{name}' ({resource_type}) registered successfully!", "success")
                    return redirect(url_for("volunteers"))
                except Exception as e:
                    flash(f"Error registering volunteer: {str(e)}", "danger")

        # GET with filters
        resource_filter = request.args.get("resource_type", "")
        avail_filter = request.args.get("availability", "")

        volunteer_list = get_volunteers(
            conn,
            resource_type=resource_filter if resource_filter else None,
            availability=avail_filter if avail_filter else None
        )

        return render_template(
            "volunteers.html",
            volunteers=volunteer_list,
            selected_resource=resource_filter,
            selected_avail=avail_filter,
            active_page="volunteers"
        )

    @app.route("/alerts", methods=["GET", "POST"])
    def alerts():
        """Disaster alert center."""
        conn = get_db()
        if request.method == "POST":
            # Only Coordinators/Admins can create alerts
            user = getattr(g, "user", None)
            is_coord = (user and user.get("role") in ("Coordinator", "Admin")) or session.get("is_coordinator")
            if not is_coord:
                flash("Access denied: Only authorized Disaster Coordinators can issue disaster alerts.", "danger")
                return render_template("403.html"), 403

            title = request.form.get("title", "").strip()
            disaster_type = request.form.get("disaster_type", "Flood").strip()
            affected_area = request.form.get("affected_area", "").strip()
            severity = request.form.get("severity", "High").strip()
            description = request.form.get("description", "").strip()
            radius_km = request.form.get("radius_km", 5.0)
            latitude = request.form.get("latitude", "")
            longitude = request.form.get("longitude", "")

            errors = []
            if not title:
                errors.append("Alert title is required.")
            if not affected_area:
                errors.append("Affected villages/area must be specified.")
            if not description:
                errors.append("Disaster description is required.")

            if errors:
                for err in errors:
                    flash(err, "danger")
            else:
                try:
                    data = {
                        "title": title,
                        "disaster_type": disaster_type,
                        "affected_area": affected_area,
                        "severity": severity,
                        "description": description,
                        "radius_km": float(radius_km or 5.0),
                        "latitude": float(latitude) if latitude else 26.9500,
                        "longitude": float(longitude) if longitude else 94.2000,
                        "issued_by": f"JEEVANPATH Coordinator ({user['username'] if user else 'HQ'})"
                    }
                    add_disaster_alert(conn, data)
                    flash(f"Disaster alert '{title}' broadcasted! Affected farms flagged.", "success")
                    return redirect(url_for("alerts"))
                except Exception as e:
                    flash(f"Error issuing alert: {str(e)}", "danger")

        status_filter = request.args.get("status", "")
        alerts_list = get_disaster_alerts(conn, status=status_filter if status_filter else None)

        return render_template(
            "alerts.html",
            alerts=alerts_list,
            selected_status=status_filter,
            active_page="alerts"
        )

    @app.route("/alerts/<int:alert_id>/resolve", methods=["POST"])
    @role_required("Coordinator", "Admin")
    def resolve_alert(alert_id):
        """Mark a disaster alert as resolved (Coordinators only)."""
        conn = get_db()
        resolve_disaster_alert(conn, alert_id)
        flash("Alert marked as Resolved. Danger zone deactivated.", "info")
        return redirect(url_for("alerts"))

    @app.route("/coordinate", methods=["GET", "POST"])
    @role_required("Coordinator", "Admin")
    def coordinate():
        """Rescue Operations & Resource Allocation Command Board (Coordinators only)."""
        conn = get_db()

        if request.method == "POST":
            action = request.form.get("action")
            farmer_id = request.form.get("farmer_id")

            if action == "assign":
                volunteer_id = request.form.get("volunteer_id")
                shelter_id = request.form.get("shelter_id")
                notes = request.form.get("notes", "").strip()

                try:
                    assign_rescue_resource(
                        conn,
                        int(farmer_id),
                        int(volunteer_id) if volunteer_id else None,
                        int(shelter_id) if shelter_id else None,
                        notes=notes
                    )
                    flash("Evacuation team and shelter assigned successfully! Status is now In Progress.", "success")
                except ValueError as ve:
                    flash(str(ve), "danger")
                except Exception as e:
                    flash(f"Assignment failed: {str(e)}", "danger")

            elif action == "update_status":
                new_status = request.form.get("new_status")
                try:
                    update_rescue_status(conn, int(farmer_id), new_status)
                    flash(f"Farmer #{farmer_id} rescue status updated to: {new_status}", "success")
                except Exception as e:
                    flash(f"Status update failed: {str(e)}", "danger")

            return redirect(url_for("coordinate"))

        # GET: Fetch data for coordination board
        pending_farmers = get_farmers(conn, rescue_status="Pending")
        in_progress_farmers = get_farmers(conn, rescue_status="In Progress")
        rescued_farmers = get_farmers(conn, rescue_status="Rescued")

        available_volunteers = get_volunteers(conn, availability="Available")
        shelters = get_shelters(conn)
        stats = get_dashboard_stats(conn)
        recent_assignments = get_recent_assignments(conn, limit=10)

        return render_template(
            "coordinate.html",
            pending_farmers=pending_farmers,
            in_progress_farmers=in_progress_farmers,
            rescued_farmers=rescued_farmers,
            available_volunteers=available_volunteers,
            shelters=shelters,
            stats=stats,
            recent_assignments=recent_assignments,
            active_page="coordinate"
        )

    @app.route("/map")
    def map_view():
        """Interactive GIS Disaster & Livestock Rescue Map."""
        return render_template("map_view.html", active_page="map")

    # ------------------ BACKWARD-COMPATIBLE PIN TOGGLE & RESET ------------------

    @app.route("/toggle-coordinator", methods=["POST"])
    def toggle_coordinator():
        """Toggle coordinator mode with demo PIN verification."""
        pin = request.form.get("pin", "").strip()
        expected_pin = app.config.get("COORDINATOR_PIN", "1234")
        current_state = session.get("is_coordinator", False)

        if current_state:
            session["is_coordinator"] = False
            flash("Coordinator mode disabled. Public view active (phone numbers masked).", "info")
        else:
            if pin == expected_pin:
                session["is_coordinator"] = True
                flash("Coordinator mode activated! Full rescue controls and unmasked contacts unlocked.", "success")
            else:
                flash("Invalid PIN. Enter '1234' for emergency coordinator PIN access.", "danger")

        ref = request.referrer or url_for("dashboard")
        return redirect(ref)

    @app.route("/reset-demo-data", methods=["POST"])
    def reset_demo():
        """Reset database to initial sample data."""
        # Check permissions
        user = getattr(g, "user", None)
        is_coord = (user and user.get("role") in ("Coordinator", "Admin")) or session.get("is_coordinator")
        if not is_coord:
            flash("Access denied: Only authorized Disaster Coordinators can reset sample data.", "danger")
            return render_template("403.html"), 403

        db_path = app.config["DATABASE_PATH"]
        if db_path != ":memory:":
            if os.path.exists(db_path):
                os.remove(db_path)
            init_db(db_path)
            seed_database(db_path)
        flash("Database has been reset to the fresh demo state with realistic Indian flood scenario data!", "success")
        return redirect(url_for("dashboard"))

    # ------------------ REST JSON API ------------------

    @app.route("/api/stats")
    def api_stats():
        """API: Dashboard stats."""
        conn = get_db()
        return jsonify(get_dashboard_stats(conn))

    @app.route("/api/farmers", methods=["GET", "POST"])
    def api_farmers():
        """API: Get or register farmers."""
        conn = get_db()
        if request.method == "POST":
            data = request.get_json() or request.form.to_dict()
            if not data.get("name") or not data.get("village") or not data.get("phone"):
                return jsonify({"error": "Name, phone, and village are required."}), 400
            try:
                farmer_id = add_farmer(conn, data)
                return jsonify({"success": True, "farmer_id": farmer_id}), 201
            except Exception as e:
                return jsonify({"error": str(e)}), 400

        # GET
        f_list = [dict(row) for row in get_farmers(conn)]
        user = getattr(g, "user", None)
        is_coord = (user and user.get("role") in ("Coordinator", "Admin")) or session.get("is_coordinator", False)
        if not is_coord:
            for f in f_list:
                f["phone"] = mask_phone(f["phone"])
                if f.get("volunteer_phone"):
                    f["volunteer_phone"] = mask_phone(f["volunteer_phone"])
        return jsonify(f_list)

    @app.route("/api/volunteers", methods=["GET", "POST"])
    def api_volunteers():
        """API: Get or register volunteers."""
        conn = get_db()
        if request.method == "POST":
            data = request.get_json() or request.form.to_dict()
            if not data.get("name") or not data.get("village") or not data.get("phone"):
                return jsonify({"error": "Name, phone, and village are required."}), 400
            try:
                vol_id = add_volunteer(conn, data)
                return jsonify({"success": True, "volunteer_id": vol_id}), 201
            except Exception as e:
                return jsonify({"error": str(e)}), 400

        v_list = [dict(row) for row in get_volunteers(conn)]
        user = getattr(g, "user", None)
        is_coord = (user and user.get("role") in ("Coordinator", "Admin")) or session.get("is_coordinator", False)
        if not is_coord:
            for v in v_list:
                v["phone"] = mask_phone(v["phone"])
        return jsonify(v_list)

    @app.route("/api/shelters")
    def api_shelters():
        """API: List shelters and available capacities."""
        conn = get_db()
        return jsonify([dict(row) for row in get_shelters(conn)])

    @app.route("/api/alerts", methods=["GET", "POST"])
    def api_alerts():
        """API: List or create alerts."""
        conn = get_db()
        if request.method == "POST":
            user = getattr(g, "user", None)
            is_coord = (user and user.get("role") in ("Coordinator", "Admin")) or session.get("is_coordinator")
            if not is_coord:
                return jsonify({"error": "Unauthorized. Coordinator role required."}), 403

            data = request.get_json() or request.form.to_dict()
            if not data.get("title") or not data.get("affected_area") or not data.get("description"):
                return jsonify({"error": "Title, affected area, and description are required."}), 400
            try:
                alert_id = add_disaster_alert(conn, data)
                return jsonify({"success": True, "alert_id": alert_id}), 201
            except Exception as e:
                return jsonify({"error": str(e)}), 400

        return jsonify([dict(row) for row in get_disaster_alerts(conn)])

    @app.route("/api/coordinate/assign", methods=["POST"])
    def api_assign():
        """API: Assign resources to a farm."""
        user = getattr(g, "user", None)
        is_coord = (user and user.get("role") in ("Coordinator", "Admin")) or session.get("is_coordinator")
        if not is_coord:
            return jsonify({"error": "Unauthorized. Coordinator role required."}), 403

        conn = get_db()
        data = request.get_json() or request.form.to_dict()
        try:
            assignment_id = assign_rescue_resource(
                conn,
                int(data["farmer_id"]),
                int(data["volunteer_id"]) if data.get("volunteer_id") else None,
                int(data["shelter_id"]) if data.get("shelter_id") else None,
                notes=data.get("notes", "")
            )
            return jsonify({"success": True, "assignment_id": assignment_id})
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/map-data")
    def api_map_data():
        """API: Bundled GIS data for Leaflet map."""
        conn = get_db()
        user = getattr(g, "user", None)
        is_coord = (user and user.get("role") in ("Coordinator", "Admin")) or session.get("is_coordinator", False)

        # 1. Farmers
        farmers_raw = get_farmers(conn)
        farmers_data = []
        for f in farmers_raw:
            farmers_data.append({
                "id": f["id"],
                "name": f["name"],
                "phone": f["phone"] if is_coord else mask_phone(f["phone"]),
                "village": f["village"],
                "latitude": f["latitude"],
                "longitude": f["longitude"],
                "livestock_type": f["livestock_type"],
                "animal_count": f["animal_count"],
                "cattle_count": f["cattle_count"],
                "buffalo_count": f["buffalo_count"],
                "special_needs": f["special_needs"],
                "priority": f["priority"],
                "rescue_status": f["rescue_status"],
                "assigned_volunteer": f["volunteer_name"],
                "assigned_shelter": f["shelter_name"]
            })

        # 2. Volunteers
        volunteers_raw = get_volunteers(conn)
        volunteers_data = []
        for v in volunteers_raw:
            volunteers_data.append({
                "id": v["id"],
                "name": v["name"],
                "phone": v["phone"] if is_coord else mask_phone(v["phone"]),
                "organization": v["organization"],
                "village": v["village"],
                "latitude": v["latitude"],
                "longitude": v["longitude"],
                "resource_type": v["resource_type"],
                "resource_details": v["resource_details"],
                "capacity": v["capacity"],
                "availability": v["availability"]
            })

        # 3. Shelters
        shelters_raw = get_shelters(conn)
        shelters_data = [dict(s) for s in shelters_raw]

        # 4. Alerts
        alerts_raw = get_disaster_alerts(conn, status="Active")
        alerts_data = [dict(a) for a in alerts_raw]

        return jsonify({
            "farmers": farmers_data,
            "volunteers": volunteers_data,
            "shelters": shelters_data,
            "alerts": alerts_data,
            "is_coordinator": is_coord,
            "map_center": [26.9800, 94.2100],  # Majuli Island center
            "zoom": 12
        })

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting JEEVANPATH on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
