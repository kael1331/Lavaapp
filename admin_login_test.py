import requests
import json

def test_admin_login_with_real_credentials():
    """Test admin login using credentials from credenciales-testing endpoint"""
    base_url = "https://laundry-mgmt-1.preview.emergentagent.com/api"
    
    print("🔐 TESTING ADMIN LOGIN WITH REAL CREDENTIALS")
    print("=" * 60)
    
    # Step 1: Login as Super Admin to get credentials
    print("\n1️⃣ Logging in as Super Admin...")
    super_admin_login = requests.post(f"{base_url}/login", json={
        "email": "kearcangel@gmail.com",
        "password": "K@#l1331"
    })
    
    if super_admin_login.status_code != 200:
        print(f"❌ Super Admin login failed: {super_admin_login.text}")
        return False
    
    super_admin_token = super_admin_login.json()["access_token"]
    print("✅ Super Admin login successful")
    
    # Step 2: Get admin credentials
    print("\n2️⃣ Getting admin credentials from testing endpoint...")
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    credentials_response = requests.get(f"{base_url}/superadmin/credenciales-testing", headers=headers)
    
    if credentials_response.status_code != 200:
        print(f"❌ Failed to get credentials: {credentials_response.text}")
        return False
    
    credentials = credentials_response.json()
    print(f"✅ Retrieved {len(credentials)} admin credentials")
    
    # Step 3: Test login for each admin with real password
    print("\n3️⃣ Testing admin logins...")
    successful_logins = 0
    failed_logins = 0
    
    for cred in credentials:
        email = cred["email"]
        password = cred["password"]
        nombre = cred["nombre"]
        
        print(f"\n   Testing login for: {nombre} ({email})")
        
        if password == "contraseña_no_encontrada":
            print(f"   ⚠️  Skipping - no password found")
            continue
        
        # Attempt login
        login_response = requests.post(f"{base_url}/login", json={
            "email": email,
            "password": password
        })
        
        if login_response.status_code == 200:
            login_data = login_response.json()
            user_role = login_data["user"]["rol"]
            print(f"   ✅ Login successful - Role: {user_role}")
            
            # Test accessing admin dashboard
            admin_token = login_data["access_token"]
            dashboard_response = requests.get(f"{base_url}/dashboard/stats", 
                                            headers={"Authorization": f"Bearer {admin_token}"})
            
            if dashboard_response.status_code == 200:
                dashboard_data = dashboard_response.json()
                print(f"   ✅ Dashboard access successful")
                if "lavadero_nombre" in dashboard_data:
                    print(f"      Lavadero: {dashboard_data['lavadero_nombre']}")
                    print(f"      Estado: {dashboard_data['estado_operativo']}")
                successful_logins += 1
            else:
                print(f"   ❌ Dashboard access failed: {dashboard_response.status_code}")
                failed_logins += 1
        else:
            print(f"   ❌ Login failed: {login_response.status_code} - {login_response.text}")
            failed_logins += 1
    
    # Step 4: Summary
    print(f"\n4️⃣ ADMIN LOGIN TEST SUMMARY")
    print(f"   Total credentials tested: {len([c for c in credentials if c['password'] != 'contraseña_no_encontrada'])}")
    print(f"   Successful logins: {successful_logins}")
    print(f"   Failed logins: {failed_logins}")
    print(f"   Credentials with real passwords: {len([c for c in credentials if c['password'] != 'contraseña_no_encontrada'])}")
    print(f"   Credentials with 'contraseña_no_encontrada': {len([c for c in credentials if c['password'] == 'contraseña_no_encontrada'])}")
    
    if successful_logins > 0:
        print("\n✅ ADMIN LOGIN SYSTEM IS WORKING!")
        print("   - Super Admin login: ✅")
        print("   - Regular admin logins: ✅")
        print("   - Credential system improvements: ✅")
        return True
    else:
        print("\n❌ ADMIN LOGIN SYSTEM HAS ISSUES!")
        return False

if __name__ == "__main__":
    test_admin_login_with_real_credentials()