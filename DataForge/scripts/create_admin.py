#!/usr/bin/env python3
"""
Create Admin User Script for DataForge

This script creates a new admin user in the DataForge database.
Run this after setting up your database with Alembic migrations.

Usage:
    python scripts/create_admin.py

Or with the virtual environment:
    source venv/bin/activate && python scripts/create_admin.py
"""
import sys
import os
from pathlib import Path
from getpass import getpass

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from sqlalchemy.orm import Session

# Load environment variables
load_dotenv()

from app.database import SessionLocal, engine
from app.models.models import User
from app.utils.auth import get_password_hash

def create_admin_user():
    """Interactive admin user creation."""
    print("""
╔════════════════════════════════════════════╗
║   DataForge - Create Admin User            ║
╚════════════════════════════════════════════╝
""")

    # Get user input
    print("Please enter the admin user details:\n")

    username = input("Username: ").strip()
    if not username:
        print("❌ Username cannot be empty!")
        return False

    email = input("Email: ").strip()
    if not email:
        print("❌ Email cannot be empty!")
        return False

    password = getpass("Password: ")
    if not password:
        print("❌ Password cannot be empty!")
        return False

    password_confirm = getpass("Confirm Password: ")
    if password != password_confirm:
        print("❌ Passwords do not match!")
        return False

    # Create database session
    db: Session = SessionLocal()

    try:
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing_user:
            print(f"\n❌ User with username '{username}' or email '{email}' already exists!")
            return False

        # Create new admin user
        hashed_password = get_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            is_active=True,
            is_admin=True
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        print(f"""
✅ Admin user created successfully!

User Details:
  ID: {new_user.id}
  Username: {new_user.username}
  Email: {new_user.email}
  Admin: {new_user.is_admin}
  Active: {new_user.is_active}
  Created: {new_user.created_at}

You can now login at /auth/token with:
  username: {new_user.username}
  password: [your password]
""")
        return True

    except Exception as e:
        print(f"\n❌ Error creating admin user: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def main():
    """Main entry point."""
    print("Checking database connection...")

    try:
        # Test database connection
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        print("✅ Database connection successful\n")
    except Exception as e:
        print(f"""
❌ Database connection failed!

Error: {e}

Please ensure:
1. PostgreSQL is running
2. Database 'dataforge' exists
3. DATABASE_URL in .env is correct
4. You have run migrations: alembic upgrade head
""")
        return 1

    # Create admin user
    success = create_admin_user()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
