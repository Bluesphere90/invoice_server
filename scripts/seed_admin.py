#!/usr/bin/env python3
"""
Seed script to create initial admin user.
Run this after database migration to create the first admin user.

Usage:
    python scripts/seed_admin.py

Environment variables:
    ADMIN_USERNAME: Admin username (default: admin)
    ADMIN_PASSWORD: Admin password (required, or prompts interactively)
    ADMIN_FULLNAME: Admin full name (default: Administrator)
"""
import os
import sys
import getpass

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.connection import get_connection, close_connection
from backend.database.user_repository import UserRepository
from backend.api.auth import get_password_hash


def main():
    """Create initial admin user."""
    print("=" * 50)
    print("Creating Admin User")
    print("=" * 50)
    
    # Get credentials
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD")
    full_name = os.getenv("ADMIN_FULLNAME", "Administrator")
    
    if not password:
        print(f"\nEnter password for admin user '{username}':")
        password = getpass.getpass("Password: ")
        password_confirm = getpass.getpass("Confirm password: ")
        
        if password != password_confirm:
            print("Error: Passwords do not match!")
            sys.exit(1)
        
        if len(password) < 8:
            print("Error: Password must be at least 8 characters!")
            sys.exit(1)
    
    try:
        conn = get_connection()
        user_repo = UserRepository(conn)
        
        # Check if user exists
        existing = user_repo.get_user_by_username(username)
        if existing:
            print(f"\nUser '{username}' already exists (ID: {existing['id']})")
            print("Skipping creation.")
            return
        
        # Create admin user
        password_hash = get_password_hash(password)
        user = user_repo.create_user(
            username=username,
            password_hash=password_hash,
            full_name=full_name,
            role="admin"
        )
        
        print(f"\n✓ Admin user created successfully!")
        print(f"  ID: {user['id']}")
        print(f"  Username: {user['username']}")
        print(f"  Role: {user['role']}")
        print(f"\nYou can now login at /api/auth/login")
        
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
    finally:
        close_connection()


if __name__ == "__main__":
    main()
