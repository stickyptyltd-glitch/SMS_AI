#!/usr/bin/env python3
"""
Setup script to create initial admin user for SMS AI
"""

import sys
import getpass
from user_management import get_user_manager

def setup_admin():
    print("🔧 SMS AI User Management Setup")
    print("=" * 40)
    
    um = get_user_manager()
    
    # Check if admin already exists
    if "admin" in um.users:
        print("❌ Admin user already exists!")
        print("Current admin info:")
        admin = um.users["admin"]
        print(f"  Email: {admin.get('email')}")
        print(f"  Created: {admin.get('created_at')}")
        print(f"  Role: {admin.get('role')}")
        
        choice = input("\nDo you want to create a new admin user with a different username? (y/N): ")
        if choice.lower() != 'y':
            return
    
    print("\n📝 Create Admin User")
    print("-" * 20)
    
    # Get admin details
    while True:
        username = input("Admin username: ").strip()
        if username:
            if username in um.users:
                print(f"❌ User '{username}' already exists!")
                continue
            break
        print("❌ Username cannot be empty!")
    
    while True:
        email = input("Admin email: ").strip()
        if email and "@" in email:
            break
        print("❌ Please enter a valid email address!")
    
    while True:
        password = getpass.getpass("Admin password: ").strip()
        if len(password) >= 8:
            password_confirm = getpass.getpass("Confirm password: ").strip()
            if password == password_confirm:
                break
            else:
                print("❌ Passwords don't match!")
        else:
            print("❌ Password must be at least 8 characters!")
    
    # Create admin user
    print(f"\n🔨 Creating admin user '{username}'...")
    success, result = um.create_user(username, password, email, "admin")
    
    if success:
        print(f"✅ Admin user created successfully!")
        print(f"   User ID: {result}")
        print(f"   Username: {username}")
        print(f"   Email: {email}")
        print(f"   Role: admin")
        
        # Generate initial token
        print(f"\n🔑 Generating API token...")
        token_success, token = um.generate_token(username, 365, "Initial admin token")
        
        if token_success:
            print(f"✅ API token generated!")
            print(f"   Token: {token}")
            print(f"   Expires: 365 days")
            
            print(f"\n📋 Quick Start:")
            print(f"1. Save your token: {token}")
            print(f"2. Test API access:")
            print(f"   curl -H 'X-API-Token: {token}' http://127.0.0.1:8081/users/me")
            print(f"3. Login via web: http://127.0.0.1:8081/users/login-ui")
            print(f"4. Access dashboard: http://127.0.0.1:8081/users/dashboard")
            
        else:
            print(f"❌ Failed to generate token: {token}")
    else:
        print(f"❌ Failed to create admin user: {result}")

def list_users():
    print("👥 Current Users")
    print("=" * 40)
    
    um = get_user_manager()
    
    if not um.users:
        print("No users found.")
        return
    
    for username, user in um.users.items():
        print(f"\n👤 {username}")
        print(f"   Email: {user.get('email')}")
        print(f"   Role: {user.get('role')}")
        print(f"   Created: {user.get('created_at')}")
        print(f"   Active: {user.get('active')}")
        print(f"   Total Requests: {user.get('usage_stats', {}).get('total_requests', 0)}")

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "list":
            list_users()
            return
        elif sys.argv[1] == "help":
            print("Usage:")
            print("  python setup_admin.py        - Create admin user")
            print("  python setup_admin.py list   - List all users")
            print("  python setup_admin.py help   - Show this help")
            return
    
    setup_admin()

if __name__ == "__main__":
    main()
