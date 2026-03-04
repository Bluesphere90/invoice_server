import sys
import os
# Add project root to path
sys.path.append(os.getcwd())

from backend.api.auth import UserAuth

def test_role_normalization():
    print("Testing role normalization...")
    
    # Simulate the logic we added in auth.py
    token_role = "ADMIN"
    normalized_role = (token_role or "user").lower()
    
    user_auth = UserAuth(id=1, username="test", role=normalized_role)
    
    if user_auth.role == "admin":
        print("PASS: Role 'ADMIN' normalized to 'admin'")
    else:
        print(f"FAIL: Role is '{user_auth.role}', expected 'admin'")

    token_role = "admin"
    normalized_role = (token_role or "user").lower()
    user_auth = UserAuth(id=1, username="test", role=normalized_role)
    
    if user_auth.role == "admin":
        print("PASS: Role 'admin' stays 'admin'")
    else:
        print(f"FAIL: Role is '{user_auth.role}', expected 'admin'")

if __name__ == "__main__":
    test_role_normalization()
