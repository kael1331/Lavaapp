import requests
import sys
import json
from datetime import datetime

class AuthenticationAPITester:
    def __init__(self, base_url="https://espanol-assist.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.employee_token = None
        self.test_user_id = None
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

    def test_health_check(self):
        """Test health check endpoint"""
        return self.run_test("Health Check", "GET", "health", 200)

    def test_register_user(self, email, password, nombre, rol):
        """Test user registration"""
        success, response = self.run_test(
            f"Register User ({rol})",
            "POST",
            "register",
            200,
            data={
                "email": email,
                "password": password,
                "nombre": nombre,
                "rol": rol
            }
        )
        if success and 'id' in response:
            return success, response['id']
        return success, None

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

    def test_get_current_user(self, token, role_name):
        """Test getting current user info"""
        return self.run_test(
            f"Get Current User ({role_name})",
            "GET",
            "me",
            200,
            token=token
        )

    def test_dashboard_stats(self, token, role_name):
        """Test dashboard statistics"""
        return self.run_test(
            f"Dashboard Stats ({role_name})",
            "GET",
            "dashboard/stats",
            200,
            token=token
        )

    def test_protected_route(self, token, role_name):
        """Test protected route"""
        return self.run_test(
            f"Protected Route ({role_name})",
            "GET",
            "protected",
            200,
            token=token
        )

    def test_admin_only_route(self, token, role_name, should_succeed=True):
        """Test admin-only route"""
        expected_status = 200 if should_succeed else 403
        return self.run_test(
            f"Admin Only Route ({role_name})",
            "GET",
            "admin-only",
            expected_status,
            token=token
        )

    def test_get_all_users(self, token, should_succeed=True):
        """Test getting all users (admin only)"""
        expected_status = 200 if should_succeed else 403
        return self.run_test(
            "Get All Users (Admin)",
            "GET",
            "admin/users",
            expected_status,
            token=token
        )

    def test_toggle_user_status(self, token, user_id, should_succeed=True):
        """Test toggling user status (admin only)"""
        expected_status = 200 if should_succeed else 403
        return self.run_test(
            "Toggle User Status (Admin)",
            "PUT",
            f"admin/users/{user_id}/toggle-status",
            expected_status,
            token=token
        )

    def test_delete_user(self, token, user_id, should_succeed=True):
        """Test deleting user (admin only)"""
        expected_status = 200 if should_succeed else 403
        return self.run_test(
            "Delete User (Admin)",
            "DELETE",
            f"admin/users/{user_id}",
            expected_status,
            token=token
        )

    def test_session_data_endpoint(self, session_id=None):
        """Test Google OAuth session data endpoint"""
        if session_id:
            headers = {'X-Session-ID': session_id}
            url = f"{self.base_url}/session-data"
            
            self.tests_run += 1
            print(f"\n🔍 Testing Google OAuth Session Data...")
            print(f"   URL: {url}")
            
            try:
                response = requests.get(url, headers=headers)
                success = response.status_code in [200, 400]  # 400 is expected for invalid session
                if success:
                    self.tests_passed += 1
                    print(f"✅ Passed - Status: {response.status_code}")
                    if response.status_code == 200:
                        print(f"   Response: {json.dumps(response.json(), indent=2)}")
                        return True, response.json()
                    else:
                        print(f"   Expected error for invalid session: {response.text}")
                        return True, {}
                else:
                    print(f"❌ Failed - Unexpected status: {response.status_code}")
                    return False, {}
            except Exception as e:
                print(f"❌ Failed - Error: {str(e)}")
                return False, {}
        else:
            # Test without session ID (should fail)
            return self.run_test(
                "Session Data (No Session ID)",
                "GET",
                "session-data",
                400
            )

    def test_set_session_cookie(self, session_token=None):
        """Test setting session cookie"""
        if session_token:
            return self.run_test(
                "Set Session Cookie",
                "POST",
                "set-session-cookie",
                200,
                data={"session_token": session_token}
            )
        else:
            # Test without session token (should fail)
            return self.run_test(
                "Set Session Cookie (No Token)",
                "POST",
                "set-session-cookie",
                422,  # Validation error
                data={}
            )

    def test_check_session(self):
        """Test session check endpoint"""
        return self.run_test(
            "Check Session (No Session)",
            "GET",
            "check-session",
            200
        )

    def test_logout(self):
        """Test logout endpoint"""
        return self.run_test(
            "Logout",
            "POST",
            "logout",
            200
        )

def main():
    print("🚀 Starting Authentication API Tests")
    print("=" * 50)
    
    tester = AuthenticationAPITester()
    
    # Test 1: Health Check
    print("\n📋 BASIC CONNECTIVITY TESTS")
    tester.test_health_check()
    
    # Test 2: User Registration
    print("\n📋 USER REGISTRATION TESTS")
    test_timestamp = datetime.now().strftime('%H%M%S')
    
    # Register test employee
    emp_email = f"test_emp_{test_timestamp}@test.com"
    success, emp_user_id = tester.test_register_user(
        emp_email, "testpass123", f"Test Employee {test_timestamp}", "EMPLEADO"
    )
    
    # Register test admin
    admin_email = f"test_admin_{test_timestamp}@test.com"
    success, admin_user_id = tester.test_register_user(
        admin_email, "testpass123", f"Test Admin {test_timestamp}", "ADMIN"
    )
    
    # Test invalid role registration
    tester.run_test(
        "Register Invalid Role",
        "POST",
        "register",
        400,
        data={
            "email": f"invalid_{test_timestamp}@test.com",
            "password": "testpass123",
            "nombre": "Invalid User",
            "rol": "INVALID_ROLE"
        }
    )
    
    # Test duplicate email registration
    tester.run_test(
        "Register Duplicate Email",
        "POST",
        "register",
        400,
        data={
            "email": emp_email,
            "password": "testpass123",
            "nombre": "Duplicate User",
            "rol": "EMPLEADO"
        }
    )
    
    # Test 3: Login Tests
    print("\n📋 LOGIN TESTS")
    
    # Login with demo accounts
    admin_success, admin_token, admin_user = tester.test_login("admin@demo.com", "admin123", "Demo Admin")
    if admin_success:
        tester.admin_token = admin_token
    
    emp_success, emp_token, emp_user = tester.test_login("empleado@demo.com", "emp123", "Demo Employee")
    if emp_success:
        tester.employee_token = emp_token
    
    # Test invalid login
    tester.test_login("invalid@test.com", "wrongpass", "Invalid User")
    
    # Test 4: Current User Tests
    print("\n📋 CURRENT USER TESTS")
    if tester.admin_token:
        tester.test_get_current_user(tester.admin_token, "Admin")
    if tester.employee_token:
        tester.test_get_current_user(tester.employee_token, "Employee")
    
    # Test 5: Dashboard Stats Tests
    print("\n📋 DASHBOARD STATISTICS TESTS")
    if tester.admin_token:
        tester.test_dashboard_stats(tester.admin_token, "Admin")
    if tester.employee_token:
        tester.test_dashboard_stats(tester.employee_token, "Employee")
    
    # Test 6: Protected Route Tests
    print("\n📋 PROTECTED ROUTE TESTS")
    if tester.admin_token:
        tester.test_protected_route(tester.admin_token, "Admin")
    if tester.employee_token:
        tester.test_protected_route(tester.employee_token, "Employee")
    
    # Test unauthorized access
    tester.run_test(
        "Protected Route (No Token)",
        "GET",
        "protected",
        401
    )
    
    # Test 7: Admin-Only Route Tests
    print("\n📋 ADMIN-ONLY ROUTE TESTS")
    if tester.admin_token:
        tester.test_admin_only_route(tester.admin_token, "Admin", should_succeed=True)
    if tester.employee_token:
        tester.test_admin_only_route(tester.employee_token, "Employee", should_succeed=False)
    
    # Test 8: User Management Tests (Admin Only)
    print("\n📋 USER MANAGEMENT TESTS")
    if tester.admin_token:
        # Get all users
        success, users_data = tester.test_get_all_users(tester.admin_token, should_succeed=True)
        
        # Find a test user to manipulate
        test_user_id = None
        if success and isinstance(users_data, list) and len(users_data) > 0:
            # Find our test employee
            for user in users_data:
                if user.get('email') == emp_email:
                    test_user_id = user.get('id')
                    break
            
            if not test_user_id and len(users_data) > 0:
                # Use any user except admin
                for user in users_data:
                    if user.get('rol') != 'ADMIN':
                        test_user_id = user.get('id')
                        break
        
        if test_user_id:
            # Test toggle user status
            tester.test_toggle_user_status(tester.admin_token, test_user_id, should_succeed=True)
            
            # Test delete user (only if it's our test user)
            if emp_user_id:
                tester.test_delete_user(tester.admin_token, emp_user_id, should_succeed=True)
    
    # Test employee trying admin operations
    if tester.employee_token:
        tester.test_get_all_users(tester.employee_token, should_succeed=False)
        if admin_user_id:
            tester.test_toggle_user_status(tester.employee_token, admin_user_id, should_succeed=False)
    
    # Test 9: Google OAuth Endpoints
    print("\n📋 GOOGLE OAUTH TESTS")
    
    # Test session data endpoint without session ID
    tester.test_session_data_endpoint()
    
    # Test session data endpoint with invalid session ID
    tester.test_session_data_endpoint("invalid-session-id")
    
    # Test set session cookie without token
    tester.test_set_session_cookie()
    
    # Test set session cookie with dummy token
    tester.test_set_session_cookie("dummy-session-token")
    
    # Test check session endpoint
    tester.test_check_session()
    
    # Test logout endpoint
    tester.test_logout()
    
    # Print final results
    print("\n" + "=" * 50)
    print(f"📊 FINAL RESULTS")
    print(f"Tests Run: {tester.tests_run}")
    print(f"Tests Passed: {tester.tests_passed}")
    print(f"Tests Failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success Rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())