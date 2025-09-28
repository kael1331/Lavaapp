import requests
import sys
import json
from datetime import datetime

class ComprehensiveBankAliasAPITester:
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

    def test_comprehensive_bank_alias_functionality(self, super_admin_token):
        """Comprehensive test of bank alias functionality"""
        print("\n🎯 COMPREHENSIVE BANK ALIAS FUNCTIONALITY TESTING...")
        print("=" * 70)
        
        results = {
            'super_admin_config_works': False,
            'juan_login_works': False,
            'juan_has_pending_payment': False,
            'pago_pendiente_includes_alias': False,
            'alias_matches_config': False,
            'existing_functionality_works': False,
            'frontend_integration_ready': False,
            'super_admin_alias': None,
            'pago_pendiente_alias': None,
            'complete_response': None
        }
        
        # Step 1: Verify Super Admin configuration
        print("\n1️⃣ Verifying Super Admin configuration...")
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
            print(f"   Configured precio mensualidad: ${config_data.get('precio_mensualidad')}")
        else:
            print("❌ Failed to get Super Admin configuration")
            return results
        
        # Step 2: Login as Juan and ensure he has pending payment
        print("\n2️⃣ Setting up Juan with pending payment...")
        juan_login_success, juan_token, juan_user = self.test_login(
            "juan@lavaderonorte.com", "juan123", "Juan Pérez"
        )
        
        if juan_login_success and juan_token:
            results['juan_login_works'] = True
            print("✅ Juan login successful")
            
            # Check current payment status
            pago_check_success, pago_check_data = self.run_test(
                "Check Juan's Payment Status",
                "GET",
                "admin/pago-pendiente",
                200,
                token=juan_token
            )
            
            if pago_check_success and pago_check_data.get('tiene_pago_pendiente'):
                results['juan_has_pending_payment'] = True
                print("✅ Juan already has pending payment")
            else:
                print("⚠️  Juan needs pending payment - this was set up in previous test")
                # In a real scenario, we'd create the payment here
                results['juan_has_pending_payment'] = False
                return results
        else:
            print("❌ Juan login failed")
            return results
        
        # Step 3: Test the NEW FUNCTIONALITY - alias_bancario_superadmin field
        print("\n3️⃣ Testing NEW FUNCTIONALITY: alias_bancario_superadmin field...")
        pago_success, pago_data = self.run_test(
            "Get Pago Pendiente with NEW Bank Alias Field",
            "GET",
            "admin/pago-pendiente",
            200,
            token=juan_token
        )
        
        if pago_success and isinstance(pago_data, dict):
            results['complete_response'] = pago_data
            print("✅ Pago pendiente endpoint working")
            
            # CRITICAL TEST: Check for the new field
            if 'alias_bancario_superadmin' in pago_data:
                results['pago_pendiente_includes_alias'] = True
                results['pago_pendiente_alias'] = pago_data.get('alias_bancario_superadmin')
                print("🎉 NEW FIELD CONFIRMED: alias_bancario_superadmin found!")
                print(f"   ✅ alias_bancario_superadmin: '{results['pago_pendiente_alias']}'")
                
                # CRITICAL TEST: Verify it matches Super Admin configuration
                if results['pago_pendiente_alias'] == results['super_admin_alias']:
                    results['alias_matches_config'] = True
                    print("🎉 PERFECT MATCH: Bank alias matches Super Admin configuration!")
                    print(f"   ✅ Super Admin config: '{results['super_admin_alias']}'")
                    print(f"   ✅ Pago pendiente response: '{results['pago_pendiente_alias']}'")
                else:
                    print("❌ MISMATCH: Bank alias does NOT match Super Admin configuration")
                    print(f"   Expected: '{results['super_admin_alias']}'")
                    print(f"   Got: '{results['pago_pendiente_alias']}'")
            else:
                print("❌ CRITICAL FAILURE: alias_bancario_superadmin field is MISSING!")
                print(f"   Available fields: {list(pago_data.keys())}")
                return results
            
            # Verify existing functionality is preserved
            expected_fields = [
                'tiene_pago_pendiente', 'pago_id', 'monto', 'mes_año', 
                'fecha_vencimiento', 'tiene_comprobante', 'estado_comprobante'
            ]
            
            existing_fields_present = all(field in pago_data for field in expected_fields)
            if existing_fields_present:
                results['existing_functionality_works'] = True
                print("✅ All existing fields preserved - no breaking changes")
            else:
                missing_fields = [field for field in expected_fields if field not in pago_data]
                print(f"❌ Some existing fields missing: {missing_fields}")
                
        else:
            print("❌ Pago pendiente endpoint failed")
            return results
        
        # Step 4: Verify frontend integration readiness
        print("\n4️⃣ Verifying frontend integration readiness...")
        if results['complete_response']:
            print("   Frontend can now display:")
            print(f"   🏦 Datos para la Transferencia:")
            print(f"   💰 Monto a pagar: ${results['complete_response'].get('monto')}")
            print(f"   🏦 Alias bancario: {results['complete_response'].get('alias_bancario_superadmin')}")
            print(f"   📅 Vencimiento: {results['complete_response'].get('fecha_vencimiento')}")
            print(f"   📄 Mes/Año: {results['complete_response'].get('mes_año')}")
            
            # Check if all required data for frontend is present
            frontend_required = ['monto', 'alias_bancario_superadmin', 'fecha_vencimiento']
            if all(field in results['complete_response'] for field in frontend_required):
                results['frontend_integration_ready'] = True
                print("✅ All data required for frontend integration is present")
            else:
                print("❌ Some data required for frontend integration is missing")
        
        return results

def main():
    """Main function to run comprehensive bank alias functionality tests"""
    print("🚀 COMPREHENSIVE BANK ALIAS FUNCTIONALITY TESTING")
    print("=" * 70)
    print("TESTING: New alias_bancario_superadmin field in /admin/pago-pendiente")
    print("PURPOSE: Admins can see Super Admin's bank alias for transfers")
    print("REVIEW REQUEST VERIFICATION: All requirements from review request")
    print("=" * 70)
    
    tester = ComprehensiveBankAliasAPITester()
    
    # Test Super Admin login
    super_admin_success, super_admin_token, super_admin_user = tester.test_super_admin_login()
    
    if super_admin_success and super_admin_token:
        print(f"✅ Super Admin authenticated: {super_admin_user.get('email')}")
        
        # Run comprehensive tests
        test_results = tester.test_comprehensive_bank_alias_functionality(super_admin_token)
        
    else:
        print("❌ Super Admin login failed")
        return 1
    
    # Final comprehensive summary
    print("\n" + "=" * 70)
    print("📊 COMPREHENSIVE TEST RESULTS SUMMARY")
    print("=" * 70)
    print(f"Total API calls: {tester.tests_run}")
    print(f"Successful calls: {tester.tests_passed}")
    print(f"Failed calls: {tester.tests_run - tester.tests_passed}")
    print(f"Success rate: {(tester.tests_passed / tester.tests_run * 100):.1f}%")
    
    # Detailed results analysis
    print("\n🔍 DETAILED FUNCTIONALITY ANALYSIS:")
    print("=" * 50)
    
    status_icon = lambda x: "✅" if x else "❌"
    
    print(f"{status_icon(test_results['super_admin_config_works'])} Super Admin Configuration Access")
    print(f"{status_icon(test_results['juan_login_works'])} Admin Login (Juan)")
    print(f"{status_icon(test_results['juan_has_pending_payment'])} Admin Has Pending Payment")
    print(f"{status_icon(test_results['pago_pendiente_includes_alias'])} NEW FIELD: alias_bancario_superadmin")
    print(f"{status_icon(test_results['alias_matches_config'])} Alias Matches Configuration")
    print(f"{status_icon(test_results['existing_functionality_works'])} Existing Functionality Preserved")
    print(f"{status_icon(test_results['frontend_integration_ready'])} Frontend Integration Ready")
    
    # Review request verification
    print("\n📋 REVIEW REQUEST VERIFICATION:")
    print("=" * 50)
    
    review_requirements = [
        ("Login as admin with pending payment (juan@lavaderonorte.com)", test_results['juan_login_works'] and test_results['juan_has_pending_payment']),
        ("GET /admin/pago-pendiente includes alias_bancario_superadmin", test_results['pago_pendiente_includes_alias']),
        ("Alias matches Super Admin configuration", test_results['alias_matches_config']),
        ("Existing functionality still works", test_results['existing_functionality_works'])
    ]
    
    all_requirements_met = True
    for requirement, status in review_requirements:
        print(f"{status_icon(status)} {requirement}")
        if not status:
            all_requirements_met = False
    
    # Final verdict
    print("\n" + "=" * 70)
    if all_requirements_met:
        print("🎉 ALL REVIEW REQUEST REQUIREMENTS VERIFIED!")
        print("✅ New bank alias functionality is working correctly")
        print("✅ Admins can now see Super Admin's bank alias for transfers")
        print("✅ Frontend integration is ready")
        print("✅ No breaking changes to existing functionality")
        
        if test_results['complete_response']:
            print(f"\n📄 SAMPLE RESPONSE FOR FRONTEND:")
            print(json.dumps(test_results['complete_response'], indent=2))
        
        return 0
    else:
        print("⚠️  SOME REVIEW REQUEST REQUIREMENTS NOT MET!")
        print("❌ New bank alias functionality needs attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())