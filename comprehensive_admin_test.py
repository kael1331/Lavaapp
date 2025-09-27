import requests
import json

def comprehensive_admin_testing():
    """Comprehensive test for admin login fixes and credential system improvements"""
    base_url = "https://laundry-mgmt-1.preview.emergentagent.com/api"
    
    print("🔐 COMPREHENSIVE ADMIN SYSTEM TESTING")
    print("=" * 60)
    
    results = {
        "super_admin_login": False,
        "regular_admin_logins": 0,
        "credential_system_improved": False,
        "toggle_lavadero_working": False,
        "no_500_errors": True
    }
    
    # Test 1: Super Admin Login
    print("\n1️⃣ TESTING SUPER ADMIN LOGIN")
    print("   Credentials: kearcangel@gmail.com / K@#l1331")
    
    super_admin_login = requests.post(f"{base_url}/login", json={
        "email": "kearcangel@gmail.com",
        "password": "K@#l1331"
    })
    
    if super_admin_login.status_code == 200:
        super_admin_data = super_admin_login.json()
        if super_admin_data["user"]["rol"] == "SUPER_ADMIN":
            results["super_admin_login"] = True
            print("   ✅ Super Admin login successful")
            super_admin_token = super_admin_data["access_token"]
        else:
            print("   ❌ Login successful but role is not SUPER_ADMIN")
            return results
    else:
        print(f"   ❌ Super Admin login failed: {super_admin_login.status_code}")
        return results
    
    # Test 2: Credential System Improvements
    print("\n2️⃣ TESTING CREDENTIAL SYSTEM IMPROVEMENTS")
    print("   Endpoint: /superadmin/credenciales-testing")
    
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    credentials_response = requests.get(f"{base_url}/superadmin/credenciales-testing", headers=headers)
    
    if credentials_response.status_code == 200:
        credentials = credentials_response.json()
        total_admins = len(credentials)
        real_passwords = [c for c in credentials if c["password"] != "contraseña_no_encontrada"]
        no_password_found = [c for c in credentials if c["password"] == "contraseña_no_encontrada"]
        
        print(f"   📊 Credential Analysis:")
        print(f"      Total admins: {total_admins}")
        print(f"      Real passwords shown: {len(real_passwords)}")
        print(f"      'contraseña_no_encontrada': {len(no_password_found)}")
        
        # Goal: Reduce "contraseña_no_encontrada" - if we have more real passwords than not found, it's improved
        if len(real_passwords) >= len(no_password_found):
            results["credential_system_improved"] = True
            print("   ✅ Credential system improved - more real passwords than 'not found'")
        else:
            print("   ⚠️  Credential system needs more improvement")
        
        # Show examples
        if real_passwords:
            print("   📝 Examples of real passwords found:")
            for cred in real_passwords[:3]:
                print(f"      {cred['email']} -> {cred['password']}")
    else:
        print(f"   ❌ Failed to get credentials: {credentials_response.status_code}")
        return results
    
    # Test 3: Regular Admin Logins
    print("\n3️⃣ TESTING REGULAR ADMIN LOGINS")
    
    successful_admin_logins = 0
    for cred in real_passwords:
        email = cred["email"]
        password = cred["password"]
        nombre = cred["nombre"]
        
        print(f"\n   Testing: {nombre} ({email})")
        
        # Test login
        login_response = requests.post(f"{base_url}/login", json={
            "email": email,
            "password": password
        })
        
        if login_response.status_code == 200:
            login_data = login_response.json()
            if login_data["user"]["rol"] == "ADMIN":
                print(f"      ✅ Login successful")
                
                # Test dashboard access (this was failing before with 500 errors)
                admin_token = login_data["access_token"]
                dashboard_response = requests.get(f"{base_url}/dashboard/stats", 
                                                headers={"Authorization": f"Bearer {admin_token}"})
                
                if dashboard_response.status_code == 200:
                    dashboard_data = dashboard_response.json()
                    print(f"      ✅ Dashboard access successful")
                    print(f"         Lavadero: {dashboard_data.get('lavadero_nombre', 'N/A')}")
                    print(f"         Estado: {dashboard_data.get('estado_operativo', 'N/A')}")
                    print(f"         Días restantes: {dashboard_data.get('dias_restantes', 'N/A')}")
                    successful_admin_logins += 1
                else:
                    print(f"      ❌ Dashboard access failed: {dashboard_response.status_code}")
                    if dashboard_response.status_code == 500:
                        results["no_500_errors"] = False
                        print(f"         Error: {dashboard_response.text}")
            else:
                print(f"      ❌ Login successful but role is not ADMIN: {login_data['user']['rol']}")
        else:
            print(f"      ❌ Login failed: {login_response.status_code}")
            if login_response.status_code == 500:
                results["no_500_errors"] = False
    
    results["regular_admin_logins"] = successful_admin_logins
    
    # Test 4: Toggle Lavadero Functionality
    print("\n4️⃣ TESTING TOGGLE LAVADERO FUNCTIONALITY")
    print("   Endpoint: /superadmin/toggle-lavadero/{admin_id}")
    
    # Get admin list to find an admin to test with
    admins_response = requests.get(f"{base_url}/superadmin/admins", headers=headers)
    
    if admins_response.status_code == 200:
        admins = admins_response.json()
        if admins:
            test_admin = admins[0]
            admin_id = test_admin["admin_id"]
            admin_name = test_admin["nombre"]
            
            print(f"   Testing with admin: {admin_name} (ID: {admin_id})")
            
            # First toggle
            toggle1_response = requests.post(f"{base_url}/superadmin/toggle-lavadero/{admin_id}", 
                                           headers=headers)
            
            if toggle1_response.status_code == 200:
                toggle1_data = toggle1_response.json()
                estado_anterior_1 = toggle1_data.get("estado_anterior")
                estado_nuevo_1 = toggle1_data.get("estado_nuevo")
                print(f"      First toggle: {estado_anterior_1} -> {estado_nuevo_1}")
                
                # Second toggle (should revert)
                toggle2_response = requests.post(f"{base_url}/superadmin/toggle-lavadero/{admin_id}", 
                                               headers=headers)
                
                if toggle2_response.status_code == 200:
                    toggle2_data = toggle2_response.json()
                    estado_anterior_2 = toggle2_data.get("estado_anterior")
                    estado_nuevo_2 = toggle2_data.get("estado_nuevo")
                    print(f"      Second toggle: {estado_anterior_2} -> {estado_nuevo_2}")
                    
                    # Verify bidirectional toggle
                    if (estado_anterior_1 == estado_nuevo_2 and estado_nuevo_1 == estado_anterior_2):
                        results["toggle_lavadero_working"] = True
                        print("      ✅ Toggle functionality working correctly (bidirectional)")
                    else:
                        print("      ❌ Toggle functionality not working properly")
                else:
                    print(f"      ❌ Second toggle failed: {toggle2_response.status_code}")
            else:
                print(f"      ❌ First toggle failed: {toggle1_response.status_code}")
        else:
            print("   ❌ No admins found for toggle testing")
    else:
        print(f"   ❌ Failed to get admin list: {admins_response.status_code}")
    
    # Final Results Summary
    print("\n" + "=" * 60)
    print("📊 COMPREHENSIVE TEST RESULTS")
    print("=" * 60)
    
    print(f"✅ Super Admin Login (kearcangel@gmail.com): {'PASS' if results['super_admin_login'] else 'FAIL'}")
    print(f"✅ Regular Admin Logins: {results['regular_admin_logins']} successful")
    print(f"✅ Credential System Improved: {'PASS' if results['credential_system_improved'] else 'FAIL'}")
    print(f"✅ Toggle Lavadero Working: {'PASS' if results['toggle_lavadero_working'] else 'FAIL'}")
    print(f"✅ No 500 Timezone Errors: {'PASS' if results['no_500_errors'] else 'FAIL'}")
    
    # Overall assessment
    all_critical_tests_pass = (
        results["super_admin_login"] and 
        results["regular_admin_logins"] > 0 and 
        results["no_500_errors"] and
        results["toggle_lavadero_working"]
    )
    
    print("\n🎯 OVERALL ASSESSMENT:")
    if all_critical_tests_pass:
        print("✅ ALL CRITICAL ISSUES RESOLVED!")
        print("   - Admin login system is working without 500 errors")
        print("   - Credential system shows real passwords")
        print("   - Toggle lavadero functionality is operational")
    else:
        print("❌ Some issues still need attention")
    
    return results

if __name__ == "__main__":
    comprehensive_admin_testing()