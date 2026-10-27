"""
Safe Development & Administrative Account Creation Utility for JEEVANPATH.
Usage:
    Interactive mode:
        python create_admin.py

    Non-interactive / CI / Scripted mode:
        python create_admin.py --username admin --password "YourStrongPassword" --name "Lead Coordinator" --phone "9864000000"
    
    Environment variables:
        ADMIN_USERNAME=admin ADMIN_PASSWORD=YourStrongPassword python create_admin.py
"""

import os
import sys
import argparse
import getpass
from config import Config
from database import get_db_connection, init_db, create_user, get_user_by_username
from werkzeug.security import generate_password_hash

def setup_admin(username=None, password=None, full_name=None, phone=None, update=False, db_path=None):
    db_file = db_path or Config.DATABASE_PATH
    init_db(db_file)
    conn = get_db_connection(db_file)

    try:
        # Check environment variables as fallback
        username = username or os.environ.get("ADMIN_USERNAME")
        password = password or os.environ.get("ADMIN_PASSWORD")
        full_name = full_name or os.environ.get("ADMIN_FULL_NAME")
        phone = phone or os.environ.get("ADMIN_PHONE")

        # Interactive prompts if still not provided
        if not username:
            default_user = "admin"
            entered = input(f"Enter administrator username [{default_user}]: ").strip()
            username = entered if entered else default_user

        existing = get_user_by_username(conn, username)
        if existing and not update:
            print(f"[!] User '{username}' already exists (Role: {existing['role']}).")
            if sys.stdin.isatty():
                ans = input("Do you wish to update this administrator's password? [y/N]: ").strip().lower()
                if ans != 'y':
                    print("Operation cancelled. Existing account preserved.")
                    return False
                update = True
            else:
                print("Pass --update or set UPDATE_ADMIN=1 to overwrite existing credentials.")
                return False

        if not password:
            while True:
                p1 = getpass.getpass("Enter secure administrator password (min 8 chars): ")
                if len(p1) < 8:
                    print("Password must be at least 8 characters long.")
                    continue
                p2 = getpass.getpass("Confirm administrator password: ")
                if p1 != p2:
                    print("Passwords do not match. Please try again.")
                    continue
                password = p1
                break
        elif len(password) < 8:
            print("[Error] Administrator password must be at least 8 characters long.")
            return False

        if not full_name:
            default_name = "Disaster Rescue Coordinator"
            if sys.stdin.isatty():
                entered_name = input(f"Enter full name [{default_name}]: ").strip()
                full_name = entered_name if entered_name else default_name
            else:
                full_name = default_name

        if not phone:
            default_phone = "9864000000"
            if sys.stdin.isatty():
                entered_phone = input(f"Enter contact phone [{default_phone}]: ").strip()
                phone = entered_phone if entered_phone else default_phone
            else:
                phone = default_phone

        clean_phone = "".join(c for c in phone if c.isdigit())
        if len(clean_phone) < 10:
            print("[Error] Valid 10-digit phone number is required.")
            return False

        if existing and update:
            pwd_hash = generate_password_hash(password)
            conn.execute("""
                UPDATE users 
                SET password_hash = ?, role = 'Coordinator', full_name = ?, phone = ?
                WHERE id = ?
            """, (pwd_hash, full_name, phone, existing["id"]))
            conn.commit()
            print(f"[Success] Administrator account '{username}' credentials updated successfully.")
            return True
        else:
            uid = create_user(
                conn,
                username=username,
                password=password,
                role="Coordinator",
                full_name=full_name,
                phone=phone,
                village="Coordination HQ"
            )
            print(f"[Success] Initial administrator account '{username}' created successfully (ID: {uid}).")
            return True

    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="Create or update initial JEEVANPATH administrator account.")
    parser.add_argument("--username", "-u", help="Administrator username")
    parser.add_argument("--password", "-p", help="Administrator password (min 8 chars)")
    parser.add_argument("--name", "-n", help="Full name of administrator")
    parser.add_argument("--phone", help="10-digit contact phone")
    parser.add_argument("--update", action="store_true", help="Update existing account password")
    parser.add_argument("--db", help="Path to database file (optional)")
    args = parser.parse_args()

    success = setup_admin(
        username=args.username,
        password=args.password,
        full_name=args.name,
        phone=args.phone,
        update=args.update,
        db_path=args.db
    )
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
