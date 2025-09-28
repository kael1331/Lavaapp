import requests
import sys
import json
from datetime import datetime

class BankAliasAPITester:
    def __init__(self, base_url="https://laundry-mgmt-1.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None, expect_json=True):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                if expect_json and response.text:
                    try:
                        response_data = response.json()
                        print(f"   Response: {json.dumps(response_data, indent=2)}")
                        return success, response_data
                    except:
                        print(f"   Response (text): {response.text}")
                        return success, response.text
                else:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_login(self, email, password, role_name):
        """Test login and get token"""
        success, response = self.run_test(
            f"Login as {role_name}",
            "POST",
            "login",
            200,
            data={"email": email, "password": password}
        )
        if success and 'access_token' in response:
            return True, response['access_token'], response['user']
        return False, None, None

    def test_super_admin_login(self):
        """Test Super Admin login"""
        return self.test_login("kearcangel@gmail.com", "K@#l1331", "Super Admin")

    def test_new_bank_alias_functionality(self, super_admin_token):
        """Test new bank alias functionality in /admin/pago-pendiente endpoint"""
        print("\n🎯 TESTING NEW BANK ALIAS FUNCTIONALITY IN PAGO-PENDIENTE ENDPOINT...")
        print("=" * 70)
        
        results = {
            'super_admin_config_works': False,
            'juan_login_works': False,
            'juan_has_pending_payment': False,
            'pending_payment_created': False,
            'pago_pendiente_includes_alias': False,
            'alias_matches_config': False,
            'existing_functionality_works': False,
            'super_admin_alias': None,
            'pago_pendiente_alias': None
        }
        
        # Step 1: Get Super Admin configuration
        print("\n1️⃣ Getting Super Admin configuration...")
        config_success, config_data = self.run_test(
            "Get Super Admin Configuration",
            "GET",
            "superadmin/configuracion",
            200,
            token=super_admin_token
        )
        
        if config_success and isinstance(config_data, dict):
            results['super_admin_config_works'] = True
            results['super_admin_alias'] = config_data.get('alias_bancario')
            print("✅ Super Admin configuration retrieved")
            print(f"   Configured alias bancario: {results['super_admin_alias']}")
        else:
            print("❌ Failed to get Super Admin configuration")
            return results
        
        # Step 2: Login as Juan
        print("\n2️⃣ Login as Juan (juan@lavaderonorte.com / juan123)...")
        juan_login_success, juan_token, juan_user = self.test_login(
            "juan@lavaderonorte.com", "juan123", "Juan Pérez (Bank Alias Test)"
        )
        
        if juan_login_success and juan_token:
            results['juan_login_works'] = True
            print("✅ Juan login successful")
        else:
            print("❌ Juan login failed")
            return results
        
        # Step 3: Check if Juan has pending payment
        print("\n3️⃣ Checking if Juan has pending payment...")
        pago_check_success, pago_check_data = self.run_test(
            "Check Juan's Current Payment Status",
            "GET",
            "admin/pago-pendiente",
            200,
            token=juan_token
        )
        
        if pago_check_success and isinstance(pago_check_data, dict):
            if pago_check_data.get('tiene_pago_pendiente'):
                results['juan_has_pending_payment'] = True
                print("✅ Juan already has pending payment")
            else:
                print("⚠️  Juan doesn't have pending payment - need to create one")
                
                # Get Juan's admin_id
                admins_success, admins_data = self.run_test(
                    "Get All Admins to find Juan's ID",
                    "GET",
                    "superadmin/admins",
                    200,
                    token=super_admin_token
                )
                
                juan_admin_id = None
                if admins_success and isinstance(admins_data, list):
                    for admin in admins_data:
                        if admin.get('email') == 'juan@lavaderonorte.com':
                            juan_admin_id = admin.get('admin_id')
                            break
                
                if juan_admin_id:
                    print(f"   Found Juan's admin_id: {juan_admin_id}")
                    
                    # Use toggle lavadero to create pending payment
                    toggle_success, toggle_data = self.run_test(
                        "Toggle Juan's Lavadero to Create Pending Payment",
                        "POST",
                        f"superadmin/toggle-lavadero/{juan_admin_id}",
                        200,
                        token=super_admin_token
                    )
                    
                    if toggle_success:
                        print("✅ Toggle successful - checking if pending payment created...")
                        
                        # Check again if Juan now has pending payment
                        pago_recheck_success, pago_recheck_data = self.run_test(
                            "Recheck Juan's Payment Status After Toggle",
                            "GET",
                            "admin/pago-pendiente",
                            200,
                            token=juan_token
                        )
                        
                        if pago_recheck_success and pago_recheck_data.get('tiene_pago_pendiente'):
                            results['juan_has_pending_payment'] = True
                            results['pending_payment_created'] = True
                            print("✅ Pending payment created successfully")
                        else:
                            print("❌ Toggle didn't create pending payment as expected")
                            return results
                    else:
                        print("❌ Failed to toggle lavadero")
                        return results
                else:
                    print("❌ Could not find Juan's admin_id")
                    return results
        else:
            print("❌ Failed to check Juan's payment status")
            return results
        
        # Step 4: Test the new alias field
        print("\n4️⃣ Testing GET /admin/pago-pendiente with new alias field...")
        pago_success, pago_data = self.run_test(
            "Get Pago Pendiente with Bank Alias (Juan)",
            "GET",
            "admin/pago-pendiente",
            200,
            token=juan_token
        )
        
        if pago_success and isinstance(pago_data, dict):
            print("✅ Pago pendiente endpoint working")
            
            if pago_data.get('tiene_pago_pendiente'):
                # Check if it includes the new field
                if 'alias_bancario_superadmin' in pago_data:
                    results['pago_pendiente_includes_alias'] = True
                    results['pago_pendiente_alias'] = pago_data.get('alias_bancario_superadmin')
                    print("✅ NEW FIELD FOUND: alias_bancario_superadmin included in response")
                    print(f"   alias_bancario_superadmin: {results['pago_pendiente_alias']}")
                    
                    # Verify it matches Super Admin configuration
                    if results['pago_pendiente_alias'] == results['super_admin_alias']:
                        results['alias_matches_config'] = True
                        print("✅ Bank alias matches Super Admin configuration")
                    else:
                        print("❌ Bank alias does NOT match Super Admin configuration")
                        print(f"   Expected: {results['super_admin_alias']}")
                        print(f"   Got: {results['pago_pendiente_alias']}")
                else:
                    print("❌ NEW FIELD MISSING: alias_bancario_superadmin not found in response")
                    print(f"   Available fields: {list(pago_data.keys())}")
                
                # Verify existing functionality still works
                expected_fields = [
                    'tiene_pago_pendiente', 'pago_id', 'monto', 'mes_año', 
                    'fecha_vencimiento', 'tiene_comprobante', 'estado_comprobante'
                ]
                
                existing_fields_present = all(field in pago_data for field in expected_fields)
                if existing_fields_present:
                    results['existing_functionality_works'] = True
                    print("✅ All existing fields still present")
                    print(f"   tiene_pago_pendiente: {pago_data.get('tiene_pago_pendiente')}")
                    print(f"   pago_id: {pago_data.get('pago_id')}")
                    print(f"   monto: ${pago_data.get('monto')}")
                    print(f"   mes_año: {pago_data.get('mes_año')}")
                    print(f"   tiene_comprobante: {pago_data.get('tiene_comprobante')}")
                else:
                    print("❌ Some existing fields are missing")
                    missing_fields = [field for field in expected_fields if field not in pago_data]
                    print(f"   Missing fields: {missing_fields}")
            else:
                print("❌ Juan still doesn't have pending payment after setup")
                return results
                
        else:
            print("❌ Pago pendiente endpoint failed")
            return results
        
        # Step 5: Verify complete response structure
        print("\n5️⃣ Verifying complete response structure...")
        if pago_success and isinstance(pago_data, dict):
            print("   Complete response structure:")
            for key, value in pago_data.items():
                print(f"   • {key}: {value}")
        
        return results

def main():
    """Main function to run bank alias functionality tests"""
    print("🚀 Starting Bank Alias Functionality Testing...")
    print("=" * 70)
    print("OBJECTIVE: Test new bank alias functionality in /admin/pago-pendiente endpoint")
    print("NEW FEATURE: alias_bancario_superadmin field added to pago-pendiente response")
    print("=" * 70)
    
    tester = BankAliasAPITester()
    
    # Test Super Admin login first
    super_admin_success, super_admin_token, super_admin_user = tester.test_super_admin_login()
    
    if super_admin_success and super_admin_token:
        print(f"✅ Super Admin authenticated: {super_admin_user.get('email')}")
        
        # Test the new bank alias functionality
        alias_results = tester.test_new_bank_alias_functionality(super_admin_token)
        print(f"\n📊 Bank Alias Functionality Test Results: {alias_results}")
        
    else:
        print("❌ Super Admin login failed - cannot test bank alias functionality")
        return 1
    
    # Final summary
    print("\n" + "=" * 70)
    print("📊 BANK ALIAS FUNCTIONALITY TEST SUMMARY")
    print("=" * 70)
    print(f"Total tests run: {tester.tests_run}")
    print(f"Tests passed: {tester.tests_passed}")
    print(f"Tests failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success rate: {(tester.tests_passed / tester.tests_run * 100):.1f}%")
    
    # Check if all critical tests passed
    critical_tests = [
        alias_results['super_admin_config_works'],
        alias_results['juan_login_works'],
        alias_results.get('juan_has_pending_payment', False),
        alias_results['pago_pendiente_includes_alias'],
        alias_results['alias_matches_config'],
        alias_results['existing_functionality_works']
    ]
    
    all_critical_passed = all(critical_tests)
    
    if all_critical_passed:
        print("🎉 ALL BANK ALIAS FUNCTIONALITY TESTS PASSED!")
        print("✅ New alias_bancario_superadmin field working correctly")
        print("✅ Alias matches Super Admin configuration")
        print("✅ Existing functionality preserved")
        print("✅ Juan can access pending payment with bank alias")
        return 0
    else:
        print("⚠️  SOME CRITICAL TESTS FAILED!")
        failed_tests = []
        if not alias_results['super_admin_config_works']: failed_tests.append("Super Admin config access")
        if not alias_results['juan_login_works']: failed_tests.append("Juan login")
        if not alias_results.get('juan_has_pending_payment', False): failed_tests.append("Juan pending payment setup")
        if not alias_results['pago_pendiente_includes_alias']: failed_tests.append("New alias field missing")
        if not alias_results['alias_matches_config']: failed_tests.append("Alias mismatch")
        if not alias_results['existing_functionality_works']: failed_tests.append("Existing functionality broken")
        print(f"❌ Failed tests: {', '.join(failed_tests)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())