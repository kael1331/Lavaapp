import requests
import sys
import json
from datetime import datetime

class AuthenticationAPITester:
    def __init__(self, base_url="https://laundry-mgmt-1.preview.emergentagent.com/api"):
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

    def test_super_admin_login(self):
        """Test Super Admin login"""
        return self.test_login("kearcangel@gmail.com", "K@#l1331", "Super Admin")

    def test_get_all_admins(self, token):
        """Test getting all admins (Super Admin only)"""
        return self.run_test(
            "Get All Admins (Super Admin)",
            "GET",
            "superadmin/admins",
            200,
            token=token
        )

    def test_toggle_lavadero(self, token, admin_id):
        """Test toggle lavadero endpoint (Super Admin only)"""
        return self.run_test(
            f"Toggle Lavadero Estado (Admin ID: {admin_id})",
            "POST",
            f"superadmin/toggle-lavadero/{admin_id}",
            200,
            token=token
        )

    def test_credenciales_testing(self, token):
        """Test credenciales testing endpoint (Super Admin only)"""
        return self.run_test(
            "Get Credenciales Testing (Super Admin)",
            "GET",
            "superadmin/credenciales-testing",
            200,
            token=token
        )

    def test_create_admin_for_testing(self, token):
        """Create a test admin for toggle testing"""
        test_timestamp = datetime.now().strftime('%H%M%S')
        return self.run_test(
            "Create Admin for Testing (Super Admin)",
            "POST",
            "superadmin/crear-admin",
            200,
            data={
                "email": f"test_admin_toggle_{test_timestamp}@test.com",
                "password": "testpass123",
                "nombre": f"Test Admin Toggle {test_timestamp}",
                "lavadero": {
                    "nombre": f"Lavadero Test Toggle {test_timestamp}",
                    "direccion": "Calle Test 123",
                    "descripcion": "Lavadero para testing toggle"
                }
            },
            token=token
        )

    # ========== NEW CONFIGURATION ENDPOINTS TESTS ==========
    
    def test_admin_login_carlos(self):
        """Test login as regular admin carlos"""
        return self.test_login("carlos@lavaderosur.com", "carlos123", "Admin Carlos")
    
    def test_get_configuracion_lavadero(self, token):
        """Test GET /admin/configuracion endpoint"""
        return self.run_test(
            "Get Configuración Lavadero (Admin)",
            "GET",
            "admin/configuracion",
            200,
            token=token
        )
    
    def test_update_configuracion_lavadero(self, token):
        """Test PUT /admin/configuracion endpoint"""
        config_data = {
            "hora_apertura": "09:00",
            "hora_cierre": "17:00",
            "duracion_turno_minutos": 90,
            "dias_laborales": [1, 2, 3, 4, 5, 6],
            "alias_bancario": "carlos.lavadero.mp",
            "precio_turno": 7500.0
        }
        return self.run_test(
            "Update Configuración Lavadero (Admin)",
            "PUT",
            "admin/configuracion",
            200,
            data=config_data,
            token=token
        )
    
    def test_get_dias_no_laborales(self, token):
        """Test GET /admin/dias-no-laborales endpoint"""
        return self.run_test(
            "Get Días No Laborales (Admin)",
            "GET",
            "admin/dias-no-laborales",
            200,
            token=token
        )
    
    def test_add_dia_no_laboral(self, token):
        """Test POST /admin/dias-no-laborales endpoint"""
        from datetime import datetime, timedelta, timezone
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        dia_data = {
            "fecha": tomorrow.isoformat(),
            "motivo": "Día de mantenimiento de equipos"
        }
        return self.run_test(
            "Add Día No Laboral (Admin)",
            "POST",
            "admin/dias-no-laborales",
            200,
            data=dia_data,
            token=token
        )
    
    def test_delete_dia_no_laboral(self, token, dia_id):
        """Test DELETE /admin/dias-no-laborales/{dia_id} endpoint"""
        return self.run_test(
            f"Delete Día No Laboral (Admin) - ID: {dia_id}",
            "DELETE",
            f"admin/dias-no-laborales/{dia_id}",
            200,
            token=token
        )
    
    def test_super_admin_cannot_access_admin_endpoints(self, super_admin_token):
        """Test that super admin CANNOT access /admin/ endpoints"""
        print("\n🚫 Testing Super Admin CANNOT access /admin/ endpoints...")
        
        # Test GET configuracion - should fail
        success1, _ = self.run_test(
            "Super Admin tries GET /admin/configuracion (should fail)",
            "GET",
            "admin/configuracion",
            403,  # Should be forbidden
            token=super_admin_token
        )
        
        # Test PUT configuracion - should fail
        config_data = {
            "hora_apertura": "09:00",
            "hora_cierre": "17:00",
            "duracion_turno_minutos": 90,
            "dias_laborales": [1, 2, 3, 4, 5, 6],
            "alias_bancario": "test.alias.mp",
            "precio_turno": 7500.0
        }
        success2, _ = self.run_test(
            "Super Admin tries PUT /admin/configuracion (should fail)",
            "PUT",
            "admin/configuracion",
            403,  # Should be forbidden
            data=config_data,
            token=super_admin_token
        )
        
        # Test GET dias no laborales - should fail
        success3, _ = self.run_test(
            "Super Admin tries GET /admin/dias-no-laborales (should fail)",
            "GET",
            "admin/dias-no-laborales",
            403,  # Should be forbidden
            token=super_admin_token
        )
        
        return success1 and success2 and success3

    # ========== PAYMENT VOUCHER TESTING FOR PENDIENTE ADMINS ==========
    
    def test_payment_voucher_functionality(self, super_admin_token):
        """
        SPECIFIC TASK: Test payment voucher functionality for admins with PENDIENTE_APROBACION status
        
        Requirements:
        1. Verify current status of monthly payments for Carlos, María and Juan
        2. Create missing payments manually if necessary
        3. Test voucher upload for PENDIENTE admin (Juan)
        4. Verify GET /admin/pago-pendiente works
        5. Test POST /comprobante-mensualidad with test data
        """
        print("\n🎯 TESTING PAYMENT VOUCHER FUNCTIONALITY FOR PENDIENTE ADMINS...")
        print("=" * 70)
        
        results = {
            'admins_found': False,
            'juan_has_payment': False,
            'juan_login': False,
            'pago_pendiente_works': False,
            'voucher_upload_works': False,
            'juan_admin_id': None
        }
        
        # Step 1: Get all admins and verify we have Carlos, María, Juan
        print("\n1️⃣ Verifying test admins exist (Carlos, María, Juan)...")
        success_admins, admins_data = self.run_test(
            "Get All Admins - Verify test admins",
            "GET",
            "superadmin/admins",
            200,
            token=super_admin_token
        )
        
        if success_admins and isinstance(admins_data, list):
            expected_admins = {
                'carlos@lavaderosur.com': {'found': False, 'estado': None, 'admin_id': None},
                'maria@lavaderocentro.com': {'found': False, 'estado': None, 'admin_id': None},
                'juan@lavaderonorte.com': {'found': False, 'estado': None, 'admin_id': None}
            }
            
            for admin in admins_data:
                email = admin.get('email')
                if email in expected_admins:
                    expected_admins[email]['found'] = True
                    expected_admins[email]['estado'] = admin.get('lavadero', {}).get('estado_operativo')
                    expected_admins[email]['admin_id'] = admin.get('admin_id')
            
            # Report findings
            for email, info in expected_admins.items():
                if info['found']:
                    print(f"✅ {email} - Estado: {info['estado']} - ID: {info['admin_id']}")
                else:
                    print(f"❌ {email} - NOT FOUND")
            
            # Check if Juan is PENDIENTE and get his admin_id
            juan_info = expected_admins['juan@lavaderonorte.com']
            if juan_info['found']:
                results['juan_admin_id'] = juan_info['admin_id']
                if juan_info['estado'] == 'PENDIENTE_APROBACION':
                    print(f"✅ Juan's lavadero is PENDIENTE_APROBACION (correct for testing)")
                    results['admins_found'] = True
                else:
                    print(f"⚠️  Juan's lavadero is {juan_info['estado']} (expected PENDIENTE_APROBACION)")
                    # Still continue testing
                    results['admins_found'] = True
            else:
                print("❌ Juan not found - cannot test voucher functionality")
                return results
        else:
            print("❌ Failed to get admin list")
            return results
        
        # Step 2: Check if Juan has a monthly payment available
        print("\n2️⃣ Checking if Juan has monthly payment available...")
        
        # Login as Juan first
        print("\n   Logging in as Juan...")
        juan_login_success, juan_token, juan_user = self.test_login(
            "juan@lavaderonorte.com", "juan123", "Juan Pérez (PENDIENTE Admin)"
        )
        
        if juan_login_success and juan_token:
            results['juan_login'] = True
            print("✅ Juan login successful")
            
            # Test GET /admin/pago-pendiente
            print("\n   Testing GET /admin/pago-pendiente...")
            pago_success, pago_data = self.run_test(
                "Get Pago Pendiente (Juan)",
                "GET",
                "admin/pago-pendiente",
                200,
                token=juan_token
            )
            
            if pago_success and isinstance(pago_data, dict):
                tiene_pago = pago_data.get('tiene_pago_pendiente', False)
                if tiene_pago:
                    results['juan_has_payment'] = True
                    results['pago_pendiente_works'] = True
                    print("✅ Juan has monthly payment available")
                    print(f"   Pago ID: {pago_data.get('pago_id')}")
                    print(f"   Monto: ${pago_data.get('monto')}")
                    print(f"   Mes/Año: {pago_data.get('mes_año')}")
                    print(f"   Vencimiento: {pago_data.get('fecha_vencimiento')}")
                    print(f"   Tiene comprobante: {pago_data.get('tiene_comprobante')}")
                    
                    # Step 3: Test voucher upload if no existing voucher
                    if not pago_data.get('tiene_comprobante'):
                        print("\n3️⃣ Testing voucher upload (POST /comprobante-mensualidad)...")
                        
                        voucher_data = {
                            "imagen_url": "https://example.com/comprobante-juan-test.jpg"
                        }
                        
                        voucher_success, voucher_response = self.run_test(
                            "Upload Payment Voucher (Juan)",
                            "POST",
                            "comprobante-mensualidad",
                            200,
                            data=voucher_data,
                            token=juan_token
                        )
                        
                        if voucher_success:
                            results['voucher_upload_works'] = True
                            print("✅ Voucher upload successful")
                            print(f"   Comprobante ID: {voucher_response.get('comprobante_id')}")
                            print(f"   Estado: {voucher_response.get('estado')}")
                            
                            # Verify the voucher was created by checking pago-pendiente again
                            print("\n   Verifying voucher was created...")
                            verify_success, verify_data = self.run_test(
                                "Verify Voucher Created (Juan)",
                                "GET",
                                "admin/pago-pendiente",
                                200,
                                token=juan_token
                            )
                            
                            if verify_success and isinstance(verify_data, dict):
                                if verify_data.get('tiene_comprobante'):
                                    print("✅ Voucher creation verified - tiene_comprobante now true")
                                else:
                                    print("⚠️  Voucher creation not reflected in pago-pendiente")
                        else:
                            print("❌ Voucher upload failed")
                    else:
                        print("\n3️⃣ Juan already has a voucher uploaded")
                        print(f"   Estado comprobante: {pago_data.get('estado_comprobante')}")
                        results['voucher_upload_works'] = True  # Consider it working if already exists
                        
                else:
                    print("❌ Juan does not have monthly payment available")
                    print("   This indicates the fix may not be working properly")
                    
                    # Step 2b: Try to create missing payment manually using Super Admin
                    print("\n2b️⃣ Attempting to create missing payment manually...")
                    if results['juan_admin_id']:
                        # This would require a new endpoint or manual database operation
                        print(f"   Juan's admin_id: {results['juan_admin_id']}")
                        print("   ⚠️  Manual payment creation would require additional endpoint")
                        print("   ⚠️  This suggests the /superadmin/crear-admin fix is not working")
            else:
                print("❌ Failed to get pago pendiente data")
        else:
            print("❌ Juan login failed")
            return results
        
        # Step 4: Test admin's voucher history
        print("\n4️⃣ Testing admin's voucher history...")
        history_success, history_data = self.run_test(
            "Get Mis Comprobantes (Juan)",
            "GET",
            "admin/mis-comprobantes",
            200,
            token=juan_token
        )
        
        if history_success and isinstance(history_data, list):
            print(f"✅ Voucher history retrieved - {len(history_data)} comprobantes found")
            for i, comp in enumerate(history_data[:3]):  # Show first 3
                print(f"   Comprobante {i+1}: Estado {comp.get('estado')}, Monto ${comp.get('monto')}")
        else:
            print("❌ Failed to get voucher history")
        
        return results
    
    # ========== NEW FILE UPLOAD FUNCTIONALITY TESTS ==========
    
    def test_file_upload_comprobante_functionality(self, super_admin_token):
        """
        SPECIFIC TASK: Test new file upload functionality for payment vouchers
        
        Requirements:
        1. Login as Juan (juan@lavaderonorte.com / juan123)
        2. Create test image files
        3. Test POST /comprobante-mensualidad with multipart/form-data
        4. Verify file validation (type and size)
        5. Verify file storage in /app/uploads/comprobantes/
        6. Verify database comprobante creation
        7. Verify URL accessibility
        """
        print("\n🎯 TESTING NEW FILE UPLOAD FUNCTIONALITY FOR PAYMENT VOUCHERS...")
        print("=" * 70)
        
        results = {
            'juan_login': False,
            'has_pending_payment': False,
            'file_upload_success': False,
            'file_validation_works': False,
            'file_stored_correctly': False,
            'url_accessible': False,
            'database_updated': False
        }
        
        # Step 1: Login as Juan
        print("\n1️⃣ Login as Juan (juan@lavaderonorte.com)...")
        juan_login_success, juan_token, juan_user = self.test_login(
            "juan@lavaderonorte.com", "juan123", "Juan Pérez (File Upload Test)"
        )
        
        if not juan_login_success or not juan_token:
            print("❌ Juan login failed - cannot test file upload")
            return results
        
        results['juan_login'] = True
        print("✅ Juan login successful")
        
        # Step 2: Check if Juan has pending payment
        print("\n2️⃣ Checking if Juan has pending payment...")
        pago_success, pago_data = self.run_test(
            "Check Pending Payment (Juan)",
            "GET",
            "admin/pago-pendiente",
            200,
            token=juan_token
        )
        
        if not pago_success or not pago_data.get('tiene_pago_pendiente'):
            print("❌ Juan doesn't have pending payment - cannot test file upload")
            return results
        
        results['has_pending_payment'] = True
        print("✅ Juan has pending payment available")
        print(f"   Pago ID: {pago_data.get('pago_id')}")
        print(f"   Monto: ${pago_data.get('monto')}")
        
        # Step 3: Create test image files
        print("\n3️⃣ Creating test image files...")
        import tempfile
        import os
        
        # Create a small test image (valid JPEG)
        test_image_content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
        
        # Create temporary files for testing
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as valid_file:
            valid_file.write(test_image_content)
            valid_file_path = valid_file.name
        
        # Create a large file for size validation test (simulate 6MB file)
        large_content = b'x' * (6 * 1024 * 1024)  # 6MB
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as large_file:
            large_file.write(large_content)
            large_file_path = large_file.name
        
        # Create invalid file type
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as invalid_file:
            invalid_file.write(b'This is not an image file')
            invalid_file_path = invalid_file.name
        
        try:
            # Step 4: Test valid file upload
            print("\n4️⃣ Testing valid file upload...")
            
            url = f"{self.base_url}/comprobante-mensualidad"
            headers = {'Authorization': f'Bearer {juan_token}'}
            
            with open(valid_file_path, 'rb') as f:
                files = {'imagen': ('test_comprobante.jpg', f, 'image/jpeg')}
                
                self.tests_run += 1
                print(f"🔍 Testing File Upload - Valid JPEG...")
                print(f"   URL: {url}")
                
                try:
                    response = requests.post(url, files=files, headers=headers)
                    
                    if response.status_code == 200:
                        self.tests_passed += 1
                        results['file_upload_success'] = True
                        print("✅ Valid file upload successful")
                        
                        response_data = response.json()
                        print(f"   Comprobante ID: {response_data.get('comprobante_id')}")
                        print(f"   Image URL: {response_data.get('imagen_url')}")
                        print(f"   Estado: {response_data.get('estado')}")
                        
                        # Test URL accessibility
                        imagen_url = response_data.get('imagen_url')
                        if imagen_url:
                            print("\n   Testing image URL accessibility...")
                            image_full_url = f"https://laundry-mgmt-1.preview.emergentagent.com{imagen_url}"
                            
                            try:
                                img_response = requests.get(image_full_url)
                                if img_response.status_code == 200:
                                    results['url_accessible'] = True
                                    print("✅ Uploaded image is accessible via URL")
                                else:
                                    print(f"❌ Image URL not accessible - Status: {img_response.status_code}")
                            except Exception as e:
                                print(f"❌ Error accessing image URL: {str(e)}")
                        
                        # Verify database was updated
                        print("\n   Verifying database was updated...")
                        verify_success, verify_data = self.run_test(
                            "Verify Database Updated",
                            "GET",
                            "admin/pago-pendiente",
                            200,
                            token=juan_token
                        )
                        
                        if verify_success and verify_data.get('tiene_comprobante'):
                            results['database_updated'] = True
                            print("✅ Database updated - comprobante created")
                        else:
                            print("❌ Database not updated properly")
                            
                    else:
                        print(f"❌ Valid file upload failed - Status: {response.status_code}")
                        print(f"   Response: {response.text}")
                        
                except Exception as e:
                    print(f"❌ File upload error: {str(e)}")
            
            # Step 5: Test file validation - large file
            print("\n5️⃣ Testing file size validation (should fail)...")
            
            with open(large_file_path, 'rb') as f:
                files = {'imagen': ('large_file.jpg', f, 'image/jpeg')}
                
                self.tests_run += 1
                print(f"🔍 Testing File Upload - Large File (should fail)...")
                
                try:
                    response = requests.post(url, files=files, headers=headers)
                    
                    if response.status_code == 400:
                        self.tests_passed += 1
                        print("✅ Large file correctly rejected")
                        print(f"   Error message: {response.json().get('detail', 'No detail')}")
                        results['file_validation_works'] = True
                    else:
                        print(f"❌ Large file validation failed - Status: {response.status_code}")
                        print(f"   Response: {response.text}")
                        
                except Exception as e:
                    print(f"❌ Large file test error: {str(e)}")
            
            # Step 6: Test file type validation
            print("\n6️⃣ Testing file type validation (should fail)...")
            
            with open(invalid_file_path, 'rb') as f:
                files = {'imagen': ('invalid_file.txt', f, 'text/plain')}
                
                self.tests_run += 1
                print(f"🔍 Testing File Upload - Invalid Type (should fail)...")
                
                try:
                    response = requests.post(url, files=files, headers=headers)
                    
                    if response.status_code == 400:
                        self.tests_passed += 1
                        print("✅ Invalid file type correctly rejected")
                        print(f"   Error message: {response.json().get('detail', 'No detail')}")
                        if not results['file_validation_works']:
                            results['file_validation_works'] = True
                    else:
                        print(f"❌ File type validation failed - Status: {response.status_code}")
                        print(f"   Response: {response.text}")
                        
                except Exception as e:
                    print(f"❌ Invalid file test error: {str(e)}")
            
            # Step 7: Check file storage on server
            print("\n7️⃣ Checking file storage on server...")
            try:
                # List files in uploads directory
                import subprocess
                result = subprocess.run(['ls', '-la', '/app/uploads/comprobantes/'], 
                                      capture_output=True, text=True)
                
                if result.returncode == 0:
                    files_list = result.stdout
                    print("✅ Upload directory accessible")
                    print(f"   Directory contents:\n{files_list}")
                    
                    # Check if any files were created
                    if 'comprobante_' in files_list:
                        results['file_stored_correctly'] = True
                        print("✅ Comprobante files found in storage directory")
                    else:
                        print("❌ No comprobante files found in storage directory")
                else:
                    print(f"❌ Cannot access upload directory: {result.stderr}")
                    
            except Exception as e:
                print(f"❌ Error checking file storage: {str(e)}")
        
        finally:
            # Clean up temporary files
            try:
                os.unlink(valid_file_path)
                os.unlink(large_file_path)
                os.unlink(invalid_file_path)
            except:
                pass
        
        return results
    
    # ========== SPECIFIC TASK: TEST IMAGE SERVING FOR COMPROBANTES ==========
    
    def test_image_serving_for_comprobantes(self, super_admin_token):
        """
        SPECIFIC TASK: Test image serving functionality for comprobantes in Super Admin dashboard
        
        Requirements from review request:
        1. Test GET `/api/uploads/comprobantes/{filename}` endpoint
        2. Test GET `/superadmin/comprobantes-pendientes` endpoint  
        3. Verify image URLs are constructed correctly
        4. Test with actual files available on server
        """
        print("\n🎯 TESTING IMAGE SERVING FOR COMPROBANTES IN SUPER ADMIN DASHBOARD...")
        print("=" * 70)
        
        results = {
            'super_admin_login': False,
            'image_endpoint_works': False,
            'comprobantes_pendientes_works': False,
            'image_urls_correct': False,
            'actual_files_accessible': False,
            'content_type_correct': False
        }
        
        # Step 1: Verify Super Admin login
        print("\n1️⃣ Verifying Super Admin login...")
        results['super_admin_login'] = True  # Already logged in
        print("✅ Super Admin already authenticated")
        
        # Step 2: Test specific image serving endpoint with known files
        print("\n2️⃣ Testing image serving endpoint with actual files...")
        
        # Test with the files mentioned in the review request
        test_files = [
            "comprobante_6befb2b5-5fce-49c6-94cc-07a466934484_995cf9f6-2fb7-4b8d-bc1c-38419da2faee.jpg",
            "comprobante_6befb2b5-5fce-49c6-94cc-07a466934484_2899fc71-1c9f-467e-8adb-8e06522263dd.jpg"
        ]
        
        files_accessible = 0
        for filename in test_files:
            print(f"\n   Testing file: {filename}")
            
            success, response_data = self.run_test(
                f"Get Comprobante Image - {filename[:50]}...",
                "GET",
                f"uploads/comprobantes/{filename}",
                200,
                expect_json=False
            )
            
            if success:
                files_accessible += 1
                print(f"✅ File accessible - Size: {len(response_data) if isinstance(response_data, (str, bytes)) else 'Unknown'} bytes")
                
                # Test content type by making a direct request to check headers
                url = f"{self.base_url}/uploads/comprobantes/{filename}"
                try:
                    response = requests.get(url)
                    if response.status_code == 200:
                        content_type = response.headers.get('content-type', '')
                        print(f"   Content-Type: {content_type}")
                        if 'image/' in content_type:
                            results['content_type_correct'] = True
                            print("✅ Correct image content-type header")
                        else:
                            print(f"⚠️  Unexpected content-type: {content_type}")
                except Exception as e:
                    print(f"   Error checking headers: {str(e)}")
            else:
                print(f"❌ File not accessible")
        
        if files_accessible > 0:
            results['image_endpoint_works'] = True
            results['actual_files_accessible'] = True
            print(f"✅ Image serving endpoint working - {files_accessible}/{len(test_files)} files accessible")
        else:
            print("❌ Image serving endpoint not working - no files accessible")
        
        # Step 3: Test comprobantes pendientes endpoint
        print("\n3️⃣ Testing comprobantes pendientes endpoint...")
        
        success, comprobantes_data = self.run_test(
            "Get Comprobantes Pendientes (Super Admin)",
            "GET",
            "superadmin/comprobantes-pendientes",
            200,
            token=super_admin_token
        )
        
        if success and isinstance(comprobantes_data, list):
            results['comprobantes_pendientes_works'] = True
            print(f"✅ Comprobantes pendientes endpoint working - Found {len(comprobantes_data)} comprobantes")
            
            # Step 4: Verify image URLs are constructed correctly
            print("\n4️⃣ Verifying image URL construction...")
            
            urls_correct = 0
            for i, comprobante in enumerate(comprobantes_data[:3]):  # Check first 3
                imagen_url = comprobante.get('imagen_url', '')
                print(f"\n   Comprobante {i+1}:")
                print(f"   Admin: {comprobante.get('admin_nombre')} ({comprobante.get('admin_email')})")
                print(f"   Lavadero: {comprobante.get('lavadero_nombre')}")
                print(f"   Monto: ${comprobante.get('monto')}")
                print(f"   Imagen URL: {imagen_url}")
                
                # Check if URL format is correct
                if imagen_url.startswith('/uploads/comprobantes/'):
                    urls_correct += 1
                    print("✅ URL format correct")
                    
                    # Test if the full URL would work
                    full_url = f"https://laundry-mgmt-1.preview.emergentagent.com/api{imagen_url}"
                    print(f"   Full URL would be: {full_url}")
                    
                    # Extract filename and test direct access
                    filename = imagen_url.split('/')[-1]
                    if filename:
                        print(f"   Testing direct access to: {filename}")
                        direct_success, _ = self.run_test(
                            f"Direct Image Access - {filename[:30]}...",
                            "GET",
                            f"uploads/comprobantes/{filename}",
                            200,
                            expect_json=False
                        )
                        if direct_success:
                            print("✅ Direct image access works")
                        else:
                            print("❌ Direct image access failed")
                else:
                    print(f"❌ URL format incorrect - Expected to start with '/uploads/comprobantes/', got: {imagen_url}")
            
            if urls_correct > 0:
                results['image_urls_correct'] = True
                print(f"✅ Image URLs correctly formatted - {urls_correct}/{len(comprobantes_data[:3])} correct")
            else:
                print("❌ Image URLs not correctly formatted")
                
        else:
            print("❌ Comprobantes pendientes endpoint failed or returned invalid data")
        
        # Step 5: Test frontend URL construction pattern
        print("\n5️⃣ Testing frontend URL construction pattern...")
        print("   Frontend should use: ${API}${comprobante.imagen_url}")
        print("   Where API = 'https://laundry-mgmt-1.preview.emergentagent.com/api'")
        
        if results['comprobantes_pendientes_works'] and len(comprobantes_data) > 0:
            sample_comprobante = comprobantes_data[0]
            imagen_url = sample_comprobante.get('imagen_url', '')
            
            if imagen_url:
                # Simulate frontend URL construction
                api_base = "https://laundry-mgmt-1.preview.emergentagent.com/api"
                constructed_url = f"{api_base}{imagen_url}"
                print(f"   Sample constructed URL: {constructed_url}")
                
                # Test the constructed URL
                try:
                    response = requests.get(constructed_url)
                    if response.status_code == 200:
                        print("✅ Frontend URL construction pattern works")
                        print(f"   Response size: {len(response.content)} bytes")
                        print(f"   Content-Type: {response.headers.get('content-type', 'Unknown')}")
                    else:
                        print(f"❌ Frontend URL construction failed - Status: {response.status_code}")
                except Exception as e:
                    print(f"❌ Error testing constructed URL: {str(e)}")
        
        return results
    
    # ========== SPECIFIC TASK: TEST NEW TOGGLE LAVADERO LOGIC ==========
    
    def test_new_toggle_lavadero_logic(self, super_admin_token):
        """
        SPECIFIC TASK: Test new toggle lavadero logic that creates PENDIENTE payment when deactivating
        
        Requirements from review request:
        1. Login as Super Admin (kearcangel@gmail.com / K@#l1331)
        2. Find admin with ACTIVO lavadero (example: María - maria@lavaderocentro.com)
        3. Use POST /superadmin/toggle-lavadero/{admin_id} on ACTIVO lavadero
        4. Verify lavadero changes to PENDIENTE_APROBACION ✓
        5. Verify new PENDIENTE payment is created ✓
        6. Verify admin can GET /admin/pago-pendiente and get tiene_pago_pendiente: true ✓
        7. Login as deactivated admin and verify they can upload comprobante
        8. Test reactivation functionality
        """
        print("\n🎯 TESTING NEW TOGGLE LAVADERO LOGIC - DEACTIVATION CREATES PENDIENTE PAYMENT...")
        print("=" * 80)
        
        results = {
            'super_admin_login': True,  # Already logged in
            'admin_with_activo_found': False,
            'admin_id': None,
            'admin_email': None,
            'admin_password': None,
            'deactivation_successful': False,
            'pendiente_payment_created': False,
            'admin_can_login': False,
            'admin_has_pending_payment': False,
            'admin_can_upload_comprobante': False,
            'reactivation_successful': False
        }
        
        # Step 1: Get all admins and find one with ACTIVO lavadero
        print("\n1️⃣ Finding admin with ACTIVO lavadero...")
        success_admins, admins_data = self.run_test(
            "Get All Admins - Find ACTIVO lavadero",
            "GET",
            "superadmin/admins",
            200,
            token=super_admin_token
        )
        
        if success_admins and isinstance(admins_data, list):
            activo_admin = None
            for admin in admins_data:
                lavadero_estado = admin.get('lavadero', {}).get('estado_operativo')
                if lavadero_estado == 'ACTIVO':
                    activo_admin = admin
                    break
            
            if activo_admin:
                results['admin_with_activo_found'] = True
                results['admin_id'] = activo_admin.get('admin_id')
                results['admin_email'] = activo_admin.get('email')
                
                print(f"✅ Found ACTIVO admin: {results['admin_email']}")
                print(f"   Admin ID: {results['admin_id']}")
                print(f"   Lavadero: {activo_admin.get('lavadero', {}).get('nombre')}")
                print(f"   Estado actual: {activo_admin.get('lavadero', {}).get('estado_operativo')}")
                
                # Get password from credenciales-testing
                print("\n   Getting admin password from credenciales-testing...")
                cred_success, cred_data = self.run_test(
                    "Get Admin Password",
                    "GET",
                    "superadmin/credenciales-testing",
                    200,
                    token=super_admin_token
                )
                
                if cred_success and isinstance(cred_data, list):
                    for cred in cred_data:
                        if cred.get('email') == results['admin_email']:
                            results['admin_password'] = cred.get('password')
                            print(f"✅ Found password: {results['admin_password']}")
                            break
                    
                    if not results['admin_password']:
                        print("⚠️  Password not found in credenciales-testing, will try common passwords")
                        # Try common passwords based on email
                        if 'maria' in results['admin_email']:
                            results['admin_password'] = 'maria123'
                        elif 'juan' in results['admin_email']:
                            results['admin_password'] = 'juan123'
                        elif 'carlos' in results['admin_email']:
                            results['admin_password'] = 'carlos123'
                        else:
                            results['admin_password'] = 'admin123'
                        print(f"   Trying common password: {results['admin_password']}")
                else:
                    print("❌ Failed to get credenciales-testing")
                    return results
            else:
                print("❌ No admin with ACTIVO lavadero found")
                print("   Available admins and their states:")
                for admin in admins_data:
                    email = admin.get('email')
                    estado = admin.get('lavadero', {}).get('estado_operativo', 'N/A')
                    print(f"   • {email}: {estado}")
                
                # Try to activate one admin for testing
                print("\n   Attempting to activate an admin for testing...")
                if len(admins_data) > 0:
                    test_admin = admins_data[0]
                    test_admin_id = test_admin.get('admin_id')
                    test_admin_email = test_admin.get('email')
                    
                    print(f"   Activating {test_admin_email} for testing...")
                    activate_success, activate_data = self.run_test(
                        f"Activate Admin for Testing - {test_admin_email}",
                        "POST",
                        f"superadmin/toggle-lavadero/{test_admin_id}",
                        200,
                        token=super_admin_token
                    )
                    
                    if activate_success and isinstance(activate_data, dict):
                        nuevo_estado = activate_data.get('estado_nuevo')
                        if nuevo_estado == 'ACTIVO':
                            print(f"✅ Successfully activated {test_admin_email}")
                            results['admin_with_activo_found'] = True
                            results['admin_id'] = test_admin_id
                            results['admin_email'] = test_admin_email
                            
                            # Get password
                            if 'maria' in test_admin_email:
                                results['admin_password'] = 'maria123'
                            elif 'juan' in test_admin_email:
                                results['admin_password'] = 'juan123'
                            elif 'carlos' in test_admin_email:
                                results['admin_password'] = 'carlos123'
                            else:
                                results['admin_password'] = 'admin123'
                        else:
                            print(f"❌ Failed to activate admin - new state: {nuevo_estado}")
                            return results
                    else:
                        print("❌ Failed to activate admin for testing")
                        return results
                else:
                    print("❌ No admins available for testing")
                    return results
        else:
            print("❌ Failed to get admin list")
            return results
        
        # Step 2: Test deactivation (ACTIVO → PENDIENTE_APROBACION)
        print(f"\n2️⃣ Testing deactivation of {results['admin_email']} lavadero...")
        print("   This should:")
        print("   • Change lavadero state from ACTIVO to PENDIENTE_APROBACION")
        print("   • Create a new PENDIENTE payment")
        print("   • Remove fecha_vencimiento")
        
        deactivate_success, deactivate_data = self.run_test(
            f"Deactivate Lavadero - {results['admin_email']}",
            "POST",
            f"superadmin/toggle-lavadero/{results['admin_id']}",
            200,
            token=super_admin_token
        )
        
        if deactivate_success and isinstance(deactivate_data, dict):
            estado_anterior = deactivate_data.get('estado_anterior')
            estado_nuevo = deactivate_data.get('estado_nuevo')
            message = deactivate_data.get('message', '')
            
            print(f"✅ Deactivation successful: {estado_anterior} → {estado_nuevo}")
            print(f"   Message: {message}")
            
            if estado_anterior == 'ACTIVO' and estado_nuevo == 'PENDIENTE_APROBACION':
                results['deactivation_successful'] = True
                print("✅ State change correct: ACTIVO → PENDIENTE_APROBACION")
                
                # Check if message indicates PENDIENTE payment was created
                if 'Nuevo pago PENDIENTE creado' in message:
                    results['pendiente_payment_created'] = True
                    print("✅ New PENDIENTE payment created (confirmed by message)")
                else:
                    print("⚠️  Message doesn't confirm PENDIENTE payment creation")
                    print(f"   Full message: {message}")
            else:
                print(f"❌ Unexpected state change: {estado_anterior} → {estado_nuevo}")
                return results
        else:
            print("❌ Deactivation failed")
            return results
        
        # Step 3: Login as the deactivated admin
        print(f"\n3️⃣ Testing login as deactivated admin ({results['admin_email']})...")
        admin_login_success, admin_token, admin_user = self.test_login(
            results['admin_email'], results['admin_password'], f"Deactivated Admin ({results['admin_email']})"
        )
        
        if admin_login_success and admin_token:
            results['admin_can_login'] = True
            print("✅ Deactivated admin can login successfully")
        else:
            print("❌ Deactivated admin cannot login")
            return results
        
        # Step 4: Check if admin has pending payment
        print("\n4️⃣ Checking if admin has pending payment (GET /admin/pago-pendiente)...")
        pago_success, pago_data = self.run_test(
            "Check Pending Payment (Deactivated Admin)",
            "GET",
            "admin/pago-pendiente",
            200,
            token=admin_token
        )
        
        if pago_success and isinstance(pago_data, dict):
            tiene_pago_pendiente = pago_data.get('tiene_pago_pendiente', False)
            
            if tiene_pago_pendiente:
                results['admin_has_pending_payment'] = True
                print("✅ Admin has pending payment available")
                print(f"   Pago ID: {pago_data.get('pago_id')}")
                print(f"   Monto: ${pago_data.get('monto')}")
                print(f"   Mes/Año: {pago_data.get('mes_año')}")
                print(f"   Vencimiento: {pago_data.get('fecha_vencimiento')}")
                print(f"   Tiene comprobante: {pago_data.get('tiene_comprobante')}")
            else:
                print("❌ Admin does not have pending payment")
                print("   This indicates the new toggle logic is not working correctly")
                print(f"   Response: {pago_data}")
                return results
        else:
            print("❌ Failed to check pending payment")
            return results
        
        # Step 5: Test comprobante upload
        print("\n5️⃣ Testing comprobante upload by deactivated admin...")
        
        # Check if admin already has comprobante
        if not pago_data.get('tiene_comprobante'):
            # Create test image file
            import tempfile
            import os
            
            test_image_content = b'\xff\xd8\xff\xe0\x10JFIF\x01\x01\x01HH\xff\xdbC\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x11\x08\x01\x01\x01\x01\x11\x02\x11\x01\x03\x11\x01\xff\xc4\x14\x01\x08\xff\xc4\x14\x10\x01\xff\xda\x0c\x03\x01\x02\x11\x03\x11\x3f\xaa\xff\xd9'
            
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as test_file:
                test_file.write(test_image_content)
                test_file_path = test_file.name
            
            try:
                url = f"{self.base_url}/comprobante-mensualidad"
                headers = {'Authorization': f'Bearer {admin_token}'}
                
                with open(test_file_path, 'rb') as f:
                    files = {'imagen': ('test_comprobante_toggle.jpg', f, 'image/jpeg')}
                    
                    self.tests_run += 1
                    print("🔍 Testing Comprobante Upload (Deactivated Admin)...")
                    
                    try:
                        response = requests.post(url, files=files, headers=headers)
                        
                        if response.status_code == 200:
                            self.tests_passed += 1
                            results['admin_can_upload_comprobante'] = True
                            print("✅ Comprobante upload successful")
                            
                            response_data = response.json()
                            print(f"   Comprobante ID: {response_data.get('comprobante_id')}")
                            print(f"   Image URL: {response_data.get('imagen_url')}")
                            print(f"   Estado: {response_data.get('estado')}")
                        else:
                            print(f"❌ Comprobante upload failed - Status: {response.status_code}")
                            print(f"   Response: {response.text}")
                    except Exception as e:
                        print(f"❌ Comprobante upload error: {str(e)}")
            finally:
                try:
                    os.unlink(test_file_path)
                except:
                    pass
        else:
            print("✅ Admin already has comprobante uploaded")
            results['admin_can_upload_comprobante'] = True
        
        # Step 6: Test reactivation
        print(f"\n6️⃣ Testing reactivation of {results['admin_email']} lavadero...")
        print("   This should change lavadero state from PENDIENTE_APROBACION back to ACTIVO")
        
        reactivate_success, reactivate_data = self.run_test(
            f"Reactivate Lavadero - {results['admin_email']}",
            "POST",
            f"superadmin/toggle-lavadero/{results['admin_id']}",
            200,
            token=super_admin_token
        )
        
        if reactivate_success and isinstance(reactivate_data, dict):
            estado_anterior = reactivate_data.get('estado_anterior')
            estado_nuevo = reactivate_data.get('estado_nuevo')
            message = reactivate_data.get('message', '')
            
            print(f"✅ Reactivation successful: {estado_anterior} → {estado_nuevo}")
            print(f"   Message: {message}")
            
            if estado_anterior == 'PENDIENTE_APROBACION' and estado_nuevo == 'ACTIVO':
                results['reactivation_successful'] = True
                print("✅ State change correct: PENDIENTE_APROBACION → ACTIVO")
                
                if 'vence' in reactivate_data:
                    print(f"   New expiration date: {reactivate_data.get('vence')}")
            else:
                print(f"❌ Unexpected state change: {estado_anterior} → {estado_nuevo}")
        else:
            print("❌ Reactivation failed")
        
        # Step 7: Final verification - complete cycle test
        print("\n7️⃣ Final verification - Complete cycle summary...")
        print("=" * 60)
        
        cycle_steps = [
            ("Super Admin Login", True),  # Already logged in
            ("Find ACTIVO Admin", results['admin_with_activo_found']),
            ("Deactivate Lavadero", results['deactivation_successful']),
            ("Create PENDIENTE Payment", results['pendiente_payment_created']),
            ("Admin Can Login", results['admin_can_login']),
            ("Admin Has Pending Payment", results['admin_has_pending_payment']),
            ("Admin Can Upload Comprobante", results['admin_can_upload_comprobante']),
            ("Reactivate Lavadero", results['reactivation_successful'])
        ]
        
        all_successful = True
        for step_name, step_result in cycle_steps:
            status = "✅" if step_result else "❌"
            print(f"   {status} {step_name}")
            if not step_result:
                all_successful = False
        
        print("\n" + "=" * 60)
        if all_successful:
            print("🎉 COMPLETE CYCLE SUCCESSFUL - New toggle lavadero logic working perfectly!")
            print("   ✅ ACTIVO → DEACTIVATE (creates PENDIENTE payment)")
            print("   ✅ Admin can upload new comprobante")
            print("   ✅ Super Admin can reactivate lavadero")
        else:
            print("⚠️  CYCLE INCOMPLETE - Some steps failed")
            failed_steps = [name for name, result in cycle_steps if not result]
            print(f"   Failed steps: {', '.join(failed_steps)}")
        
        return results
    
    # ========== SPECIFIC TASK: TEST NEW COMPROBANTES HISTORIAL ENDPOINT ==========
    
    def test_comprobantes_historial_endpoint(self, super_admin_token):
        """
        SPECIFIC TASK: Test new /superadmin/comprobantes-historial endpoint
        
        Requirements from review request:
        1. Login as Super Admin (kearcangel@gmail.com / K@#l1331)
        2. GET /superadmin/comprobantes-historial without parameters
        3. Verify response structure: {comprobantes, total, stats, filters}
        4. Verify stats contain: total, pendientes, aprobados, rechazados
        5. Test filters: estado=PENDIENTE, CONFIRMADO, RECHAZADO
        6. Test pagination: limit and offset
        7. Compare with existing /superadmin/comprobantes-pendientes
        """
        print("\n🎯 TESTING NEW COMPROBANTES HISTORIAL ENDPOINT...")
        print("=" * 70)
        
        results = {
            'basic_endpoint_works': False,
            'correct_structure': False,
            'stats_correct': False,
            'filters_work': False,
            'pagination_works': False,
            'comparison_matches': False,
            'response_data': None
        }
        
        # Step 1: Test basic endpoint without parameters
        print("\n1️⃣ Testing basic endpoint GET /superadmin/comprobantes-historial...")
        
        basic_success, basic_data = self.run_test(
            "Get Comprobantes Historial - Basic",
            "GET",
            "superadmin/comprobantes-historial",
            200,
            token=super_admin_token
        )
        
        if basic_success and isinstance(basic_data, dict):
            results['basic_endpoint_works'] = True
            results['response_data'] = basic_data
            print("✅ Basic endpoint working")
            
            # Verify response structure
            required_keys = ['comprobantes', 'total', 'stats', 'filters']
            structure_correct = all(key in basic_data for key in required_keys)
            
            if structure_correct:
                results['correct_structure'] = True
                print("✅ Response structure correct - contains: comprobantes, total, stats, filters")
                
                # Display basic info
                total = basic_data.get('total', 0)
                comprobantes_count = len(basic_data.get('comprobantes', []))
                print(f"   Total comprobantes: {total}")
                print(f"   Comprobantes returned: {comprobantes_count}")
                
                # Verify stats structure
                stats = basic_data.get('stats', {})
                required_stats = ['total', 'pendientes', 'aprobados', 'rechazados']
                stats_correct = all(key in stats for key in required_stats)
                
                if stats_correct:
                    results['stats_correct'] = True
                    print("✅ Stats structure correct")
                    print(f"   Stats: Total={stats.get('total')}, Pendientes={stats.get('pendientes')}, Aprobados={stats.get('aprobados')}, Rechazados={stats.get('rechazados')}")
                    
                    # Verify stats numbers make sense
                    stats_total = stats.get('pendientes', 0) + stats.get('aprobados', 0) + stats.get('rechazados', 0)
                    if stats_total == stats.get('total', 0):
                        print("✅ Stats numbers are consistent")
                    else:
                        print(f"⚠️  Stats inconsistency: sum={stats_total}, total={stats.get('total')}")
                else:
                    print("❌ Stats structure incorrect - missing keys")
                    print(f"   Available stats keys: {list(stats.keys())}")
            else:
                print("❌ Response structure incorrect")
                print(f"   Available keys: {list(basic_data.keys())}")
                print(f"   Required keys: {required_keys}")
        else:
            print("❌ Basic endpoint failed")
            return results
        
        # Step 2: Test filters
        print("\n2️⃣ Testing filters...")
        
        filter_tests = [
            ("PENDIENTE", "pendientes"),
            ("CONFIRMADO", "aprobados"), 
            ("RECHAZADO", "rechazados")
        ]
        
        filter_results = []
        for estado, stats_key in filter_tests:
            print(f"\n   Testing filter: estado={estado}")
            
            filter_success, filter_data = self.run_test(
                f"Get Comprobantes Historial - Filter {estado}",
                "GET",
                f"superadmin/comprobantes-historial?estado={estado}",
                200,
                token=super_admin_token
            )
            
            if filter_success and isinstance(filter_data, dict):
                comprobantes = filter_data.get('comprobantes', [])
                total = filter_data.get('total', 0)
                filters_applied = filter_data.get('filters', {})
                
                print(f"   ✅ Filter {estado} works - {total} comprobantes found")
                print(f"   Applied filters: {filters_applied}")
                
                # Verify all returned comprobantes have the correct estado
                if comprobantes:
                    estados_found = set(comp.get('estado') for comp in comprobantes)
                    if estados_found == {estado}:
                        print(f"   ✅ All comprobantes have estado={estado}")
                    else:
                        print(f"   ⚠️  Mixed estados found: {estados_found}")
                
                filter_results.append(True)
            else:
                print(f"   ❌ Filter {estado} failed")
                filter_results.append(False)
        
        if all(filter_results):
            results['filters_work'] = True
            print("✅ All filters working correctly")
        else:
            print("❌ Some filters failed")
        
        # Step 3: Test pagination
        print("\n3️⃣ Testing pagination...")
        
        # Test with limit=2, offset=0
        page1_success, page1_data = self.run_test(
            "Get Comprobantes Historial - Page 1 (limit=2, offset=0)",
            "GET",
            "superadmin/comprobantes-historial?limit=2&offset=0",
            200,
            token=super_admin_token
        )
        
        # Test with limit=2, offset=2
        page2_success, page2_data = self.run_test(
            "Get Comprobantes Historial - Page 2 (limit=2, offset=2)",
            "GET",
            "superadmin/comprobantes-historial?limit=2&offset=2",
            200,
            token=super_admin_token
        )
        
        if page1_success and page2_success:
            page1_comprobantes = page1_data.get('comprobantes', [])
            page2_comprobantes = page2_data.get('comprobantes', [])
            
            print(f"✅ Pagination working - Page 1: {len(page1_comprobantes)} items, Page 2: {len(page2_comprobantes)} items")
            
            # Verify no overlap between pages
            if page1_comprobantes and page2_comprobantes:
                page1_ids = set(comp.get('comprobante_id') for comp in page1_comprobantes)
                page2_ids = set(comp.get('comprobante_id') for comp in page2_comprobantes)
                
                if not page1_ids.intersection(page2_ids):
                    results['pagination_works'] = True
                    print("✅ No overlap between pages - pagination working correctly")
                else:
                    print("⚠️  Overlap found between pages")
            else:
                results['pagination_works'] = True
                print("✅ Pagination working (one or both pages empty)")
        else:
            print("❌ Pagination tests failed")
        
        # Step 4: Compare with existing endpoint
        print("\n4️⃣ Comparing with existing /superadmin/comprobantes-pendientes...")
        
        existing_success, existing_data = self.run_test(
            "Get Comprobantes Pendientes - Existing endpoint",
            "GET",
            "superadmin/comprobantes-pendientes",
            200,
            token=super_admin_token
        )
        
        if existing_success and isinstance(existing_data, list):
            existing_count = len(existing_data)
            print(f"✅ Existing endpoint works - {existing_count} pendientes found")
            
            # Compare with filtered new endpoint
            new_pendientes_success, new_pendientes_data = self.run_test(
                "Get Comprobantes Historial - PENDIENTE filter for comparison",
                "GET",
                "superadmin/comprobantes-historial?estado=PENDIENTE",
                200,
                token=super_admin_token
            )
            
            if new_pendientes_success and isinstance(new_pendientes_data, dict):
                new_comprobantes = new_pendientes_data.get('comprobantes', [])
                new_count = len(new_comprobantes)
                
                print(f"   New endpoint PENDIENTE filter: {new_count} comprobantes")
                print(f"   Existing endpoint: {existing_count} comprobantes")
                
                if new_count == existing_count:
                    results['comparison_matches'] = True
                    print("✅ Both endpoints return same number of PENDIENTE comprobantes")
                    
                    # Compare some fields if both have data
                    if existing_data and new_comprobantes:
                        print("   Comparing first comprobante from each endpoint:")
                        existing_first = existing_data[0]
                        new_first = new_comprobantes[0]
                        
                        # Compare common fields
                        common_fields = ['admin_email', 'lavadero_nombre', 'monto']
                        for field in common_fields:
                            existing_val = existing_first.get(field)
                            new_val = new_first.get(field)
                            if existing_val == new_val:
                                print(f"   ✅ {field}: {existing_val}")
                            else:
                                print(f"   ⚠️  {field} differs: existing={existing_val}, new={new_val}")
                else:
                    print(f"⚠️  Count mismatch - existing: {existing_count}, new: {new_count}")
            else:
                print("❌ New endpoint PENDIENTE filter failed")
        else:
            print("❌ Existing endpoint failed")
        
        # Step 5: Test edge cases
        print("\n5️⃣ Testing edge cases...")
        
        # Test invalid estado filter
        invalid_success, invalid_data = self.run_test(
            "Get Comprobantes Historial - Invalid estado filter",
            "GET",
            "superadmin/comprobantes-historial?estado=INVALID",
            200,  # Should still work but return empty or all results
            token=super_admin_token
        )
        
        if invalid_success:
            print("✅ Invalid estado filter handled gracefully")
        
        # Test large limit
        large_limit_success, large_limit_data = self.run_test(
            "Get Comprobantes Historial - Large limit",
            "GET",
            "superadmin/comprobantes-historial?limit=1000",
            200,
            token=super_admin_token
        )
        
        if large_limit_success:
            print("✅ Large limit handled correctly")
        
        # Final summary
        print("\n" + "=" * 70)
        print("📊 COMPROBANTES HISTORIAL ENDPOINT TEST SUMMARY:")
        
        test_results = [
            ("Basic endpoint functionality", results['basic_endpoint_works']),
            ("Response structure correct", results['correct_structure']),
            ("Statistics correct", results['stats_correct']),
            ("Filters working", results['filters_work']),
            ("Pagination working", results['pagination_works']),
            ("Comparison with existing endpoint", results['comparison_matches'])
        ]
        
        all_passed = True
        for test_name, test_result in test_results:
            status = "✅" if test_result else "❌"
            print(f"   {status} {test_name}")
            if not test_result:
                all_passed = False
        
        if all_passed:
            print("\n🎉 ALL TESTS PASSED - New comprobantes historial endpoint working perfectly!")
        else:
            print("\n⚠️  SOME TESTS FAILED - Review issues above")
        
        return results

    # ========== SPECIFIC TASK: CREATE 2 NEW ADMINS FOR TESTING ==========
    
    def test_create_two_new_admins_for_testing(self, super_admin_token):
        """
        SPECIFIC TASK: Create 2 new admin users with their lavaderos for testing
        
        Requirements:
        1. Create Admin 1: maria@lavaderocentro.com with Lavadero Centro
        2. Create Admin 2: juan@lavaderonorte.com with Lavadero Norte  
        3. Verify both admins created correctly
        4. Verify both lavaderos in PENDIENTE_APROBACION state
        5. Verify passwords appear in credenciales-testing
        6. Verify both admins can login
        7. Optionally activate one lavadero using toggle
        """
        print("\n🎯 SPECIFIC TASK: Creating 2 new admins for testing...")
        print("=" * 60)
        
        results = {
            'admin1_created': False,
            'admin2_created': False,
            'admin1_id': None,
            'admin2_id': None,
            'admin1_login': False,
            'admin2_login': False,
            'passwords_in_credentials': False,
            'lavaderos_pending': False,
            'toggle_test': False
        }
        
        # Step 1: Create Admin 1 - María González
        print("\n1️⃣ Creating Admin 1: María González (maria@lavaderocentro.com)...")
        admin1_data = {
            "email": "maria@lavaderocentro.com",
            "password": "maria123",
            "nombre": "María González",
            "lavadero": {
                "nombre": "Lavadero Centro",
                "direccion": "Av. Corrientes 1234, Centro",
                "descripcion": "Lavadero en el centro de la ciudad, servicio express"
            }
        }
        
        success1, response1 = self.run_test(
            "Create Admin 1 - María González",
            "POST",
            "superadmin/crear-admin",
            200,
            data=admin1_data,
            token=super_admin_token
        )
        
        if success1 and isinstance(response1, dict) and 'admin_id' in response1:
            results['admin1_created'] = True
            results['admin1_id'] = response1['admin_id']
            print(f"✅ Admin 1 created successfully - ID: {results['admin1_id']}")
            print(f"   Lavadero ID: {response1.get('lavadero_id')}")
            print(f"   Estado: {response1.get('estado')}")
        else:
            print("❌ Admin 1 creation failed")
            return results
        
        # Step 2: Create Admin 2 - Juan Pérez
        print("\n2️⃣ Creating Admin 2: Juan Pérez (juan@lavaderonorte.com)...")
        admin2_data = {
            "email": "juan@lavaderonorte.com",
            "password": "juan123", 
            "nombre": "Juan Pérez",
            "lavadero": {
                "nombre": "Lavadero Norte",
                "direccion": "Calle Norte 567, Zona Norte",
                "descripcion": "Lavadero familiar en zona norte, atención personalizada"
            }
        }
        
        success2, response2 = self.run_test(
            "Create Admin 2 - Juan Pérez",
            "POST",
            "superadmin/crear-admin",
            200,
            data=admin2_data,
            token=super_admin_token
        )
        
        if success2 and isinstance(response2, dict) and 'admin_id' in response2:
            results['admin2_created'] = True
            results['admin2_id'] = response2['admin_id']
            print(f"✅ Admin 2 created successfully - ID: {results['admin2_id']}")
            print(f"   Lavadero ID: {response2.get('lavadero_id')}")
            print(f"   Estado: {response2.get('estado')}")
        else:
            print("❌ Admin 2 creation failed")
            return results
        
        # Step 3: Verify both admins appear in admin list with PENDIENTE_APROBACION
        print("\n3️⃣ Verifying admins appear in admin list...")
        success_list, admins_data = self.run_test(
            "Get All Admins - Verify new admins",
            "GET",
            "superadmin/admins",
            200,
            token=super_admin_token
        )
        
        if success_list and isinstance(admins_data, list):
            maria_found = False
            juan_found = False
            
            for admin in admins_data:
                if admin.get('email') == 'maria@lavaderocentro.com':
                    maria_found = True
                    lavadero_estado = admin.get('lavadero', {}).get('estado_operativo')
                    print(f"✅ María found - Estado lavadero: {lavadero_estado}")
                    if lavadero_estado == 'PENDIENTE_APROBACION':
                        print("✅ María's lavadero correctly in PENDIENTE_APROBACION state")
                    else:
                        print(f"⚠️  María's lavadero in unexpected state: {lavadero_estado}")
                
                elif admin.get('email') == 'juan@lavaderonorte.com':
                    juan_found = True
                    lavadero_estado = admin.get('lavadero', {}).get('estado_operativo')
                    print(f"✅ Juan found - Estado lavadero: {lavadero_estado}")
                    if lavadero_estado == 'PENDIENTE_APROBACION':
                        print("✅ Juan's lavadero correctly in PENDIENTE_APROBACION state")
                    else:
                        print(f"⚠️  Juan's lavadero in unexpected state: {lavadero_estado}")
            
            if maria_found and juan_found:
                results['lavaderos_pending'] = True
                print("✅ Both admins found in admin list with correct lavadero states")
            else:
                print(f"❌ Admins not found - María: {maria_found}, Juan: {juan_found}")
        else:
            print("❌ Failed to get admin list")
        
        # Step 4: Verify passwords appear in credenciales-testing
        print("\n4️⃣ Verifying passwords appear in credenciales-testing...")
        success_cred, cred_data = self.run_test(
            "Get Credenciales Testing - Verify new passwords",
            "GET",
            "superadmin/credenciales-testing",
            200,
            token=super_admin_token
        )
        
        if success_cred and isinstance(cred_data, list):
            maria_password_found = False
            juan_password_found = False
            
            for cred in cred_data:
                if cred.get('email') == 'maria@lavaderocentro.com':
                    password = cred.get('password')
                    if password == 'maria123':
                        maria_password_found = True
                        print("✅ María's password correctly found: maria123")
                    else:
                        print(f"⚠️  María's password unexpected: {password}")
                
                elif cred.get('email') == 'juan@lavaderonorte.com':
                    password = cred.get('password')
                    if password == 'juan123':
                        juan_password_found = True
                        print("✅ Juan's password correctly found: juan123")
                    else:
                        print(f"⚠️  Juan's password unexpected: {password}")
            
            if maria_password_found and juan_password_found:
                results['passwords_in_credentials'] = True
                print("✅ Both passwords correctly appear in credenciales-testing")
            else:
                print(f"❌ Passwords not found - María: {maria_password_found}, Juan: {juan_password_found}")
        else:
            print("❌ Failed to get credenciales-testing")
        
        # Step 5: Test login for both new admins
        print("\n5️⃣ Testing login for both new admins...")
        
        # Test María's login
        print("\n   Testing María's login...")
        maria_login_success, maria_token, maria_user = self.test_login(
            "maria@lavaderocentro.com", "maria123", "María González"
        )
        
        if maria_login_success:
            results['admin1_login'] = True
            print("✅ María can login successfully")
        else:
            print("❌ María login failed")
        
        # Test Juan's login
        print("\n   Testing Juan's login...")
        juan_login_success, juan_token, juan_user = self.test_login(
            "juan@lavaderonorte.com", "juan123", "Juan Pérez"
        )
        
        if juan_login_success:
            results['admin2_login'] = True
            print("✅ Juan can login successfully")
        else:
            print("❌ Juan login failed")
        
        # Step 6: Optional - Activate one lavadero using toggle for variety
        print("\n6️⃣ Optional: Activating María's lavadero using toggle for testing variety...")
        if results['admin1_id']:
            toggle_success, toggle_data = self.run_test(
                f"Toggle María's Lavadero (Activate for variety)",
                "POST",
                f"superadmin/toggle-lavadero/{results['admin1_id']}",
                200,
                token=super_admin_token
            )
            
            if toggle_success and isinstance(toggle_data, dict):
                estado_anterior = toggle_data.get('estado_anterior')
                estado_nuevo = toggle_data.get('estado_nuevo')
                print(f"✅ Toggle successful: {estado_anterior} -> {estado_nuevo}")
                
                if estado_nuevo == 'ACTIVO':
                    results['toggle_test'] = True
                    print("✅ María's lavadero now ACTIVE for testing variety")
                    print(f"   Vence: {toggle_data.get('vence', 'N/A')}")
                else:
                    print(f"⚠️  Unexpected new state: {estado_nuevo}")
            else:
                print("❌ Toggle failed")
        
        # Step 7: Final verification - count total admins
        print("\n7️⃣ Final verification: Total admin count...")
        if success_list and isinstance(admins_data, list):
            total_admins = len(admins_data)
            print(f"✅ Total admins now: {total_admins}")
            print("   Expected: Carlos (existing) + María + Juan = 3 admins minimum")
            
            # Show admin summary
            print("\n📋 Admin Summary:")
            admin_emails = []
            for admin in admins_data:
                email = admin.get('email')
                lavadero_name = admin.get('lavadero', {}).get('nombre', 'Sin lavadero')
                estado = admin.get('lavadero', {}).get('estado_operativo', 'N/A')
                admin_emails.append(email)
                print(f"   • {email} - {lavadero_name} ({estado})")
            
            # Verify we have the expected admins
            expected_emails = ['carlos@lavaderosur.com', 'maria@lavaderocentro.com', 'juan@lavaderonorte.com']
            all_expected_found = all(email in admin_emails for email in expected_emails)
            
            if all_expected_found:
                print("✅ All expected admins found: Carlos + María + Juan")
            else:
                missing = [email for email in expected_emails if email not in admin_emails]
                print(f"⚠️  Missing expected admins: {missing}")
        
        return results

    def run_comprobantes_historial_tests(self):
        """Run tests specifically for the new comprobantes historial endpoint"""
        print("🚀 Starting Comprobantes Historial Endpoint Testing...")
        print("=" * 60)
        
        # Test Super Admin login first
        super_admin_success, super_admin_token, super_admin_user = self.test_super_admin_login()
        
        if super_admin_success and super_admin_token:
            print(f"✅ Super Admin authenticated: {super_admin_user.get('email')}")
            
            # Test the new comprobantes historial endpoint
            historial_results = self.test_comprobantes_historial_endpoint(super_admin_token)
            print(f"\n📊 Comprobantes Historial Test Results: {historial_results}")
            
        else:
            print("❌ Super Admin login failed - cannot test comprobantes historial endpoint")
            return False
        
        # Final summary
        print("\n" + "=" * 60)
        print("📊 COMPROBANTES HISTORIAL TEST SUMMARY")
        print("=" * 60)
        print(f"Total tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Tests failed: {self.tests_run - self.tests_passed}")
        print(f"Success rate: {(self.tests_passed / self.tests_run * 100):.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL COMPROBANTES HISTORIAL TESTS PASSED!")
            return True
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
            return False

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
    
    # Test 10: Super Admin Specific Tests (New Requirements)
    print("\n📋 SUPER ADMIN SPECIFIC TESTS")
    
    # Login as Super Admin
    super_admin_success, super_admin_token, super_admin_user = tester.test_super_admin_login()
    
    if super_admin_success and super_admin_token:
        print("\n🔧 Testing Super Admin Endpoints...")
        
        # Test 1: Get all admins
        success, admins_data = tester.test_get_all_admins(super_admin_token)
        
        # Test 2: Credenciales testing endpoint
        print("\n🔑 Testing Credenciales Testing Endpoint...")
        cred_success, cred_data = tester.test_credenciales_testing(super_admin_token)
        
        if cred_success and isinstance(cred_data, list):
            print(f"   Found {len(cred_data)} admin credentials")
            # Check if we have real passwords (not "contraseña_no_encontrada")
            real_passwords = [cred for cred in cred_data if cred.get('password') != 'contraseña_no_encontrada']
            print(f"   Real passwords found: {len(real_passwords)}")
            
            if len(real_passwords) > 0:
                print("✅ Credenciales system is working - showing real passwords")
                for cred in real_passwords[:3]:  # Show first 3 as example
                    print(f"      Example: {cred.get('email')} -> {cred.get('password')}")
            else:
                print("❌ Credenciales system issue - only showing 'contraseña_no_encontrada'")
        
        # Test 3: Toggle lavadero functionality
        print("\n🔄 Testing Toggle Lavadero Endpoint...")
        
        # First, create a test admin if we don't have any
        test_admin_id = None
        if success and isinstance(admins_data, list) and len(admins_data) > 0:
            # Use existing admin
            test_admin_id = admins_data[0].get('admin_id')
            print(f"   Using existing admin ID: {test_admin_id}")
        else:
            # Create a new admin for testing
            create_success, create_data = tester.test_create_admin_for_testing(super_admin_token)
            if create_success and 'admin_id' in create_data:
                test_admin_id = create_data['admin_id']
                print(f"   Created new admin ID: {test_admin_id}")
        
        if test_admin_id:
            # Test toggle functionality - first toggle
            print(f"\n   Testing first toggle (should change state)...")
            toggle1_success, toggle1_data = tester.test_toggle_lavadero(super_admin_token, test_admin_id)
            
            if toggle1_success and isinstance(toggle1_data, dict):
                estado_anterior_1 = toggle1_data.get('estado_anterior')
                estado_nuevo_1 = toggle1_data.get('estado_nuevo')
                print(f"   First toggle: {estado_anterior_1} -> {estado_nuevo_1}")
                
                # Test toggle functionality - second toggle (should revert)
                print(f"\n   Testing second toggle (should revert state)...")
                toggle2_success, toggle2_data = tester.test_toggle_lavadero(super_admin_token, test_admin_id)
                
                if toggle2_success and isinstance(toggle2_data, dict):
                    estado_anterior_2 = toggle2_data.get('estado_anterior')
                    estado_nuevo_2 = toggle2_data.get('estado_nuevo')
                    print(f"   Second toggle: {estado_anterior_2} -> {estado_nuevo_2}")
                    
                    # Verify toggle works both ways
                    if estado_anterior_1 == estado_nuevo_2 and estado_nuevo_1 == estado_anterior_2:
                        print("✅ Toggle functionality working correctly - states toggle both ways")
                    else:
                        print("❌ Toggle functionality issue - states not toggling properly")
                else:
                    print("❌ Second toggle failed")
            else:
                print("❌ First toggle failed")
        else:
            print("❌ No admin available for toggle testing")
    else:
        print("❌ Super Admin login failed - cannot test Super Admin endpoints")
    
    # Test 11: NEW CONFIGURATION ENDPOINTS TESTS
    print("\n📋 NEW CONFIGURATION ENDPOINTS TESTS")
    print("🎯 Testing new laundry configuration endpoints as requested...")
    
    # Step 1: Login as regular admin (carlos@lavaderosur.com)
    print("\n1️⃣ Login as regular admin (carlos@lavaderosur.com)...")
    carlos_success, carlos_token, carlos_user = tester.test_admin_login_carlos()
    
    if carlos_success and carlos_token:
        print(f"✅ Carlos login successful - Role: {carlos_user.get('rol')}")
        
        # Verify it's ADMIN role, not SUPER_ADMIN
        if carlos_user.get('rol') == 'ADMIN':
            print("✅ Confirmed: Carlos has ADMIN role (not SUPER_ADMIN)")
            
            # Step 2: Test basic configuration endpoints
            print("\n2️⃣ Testing basic configuration endpoints...")
            
            # GET configuracion (should create default if not exists)
            print("\n   Testing GET /admin/configuracion...")
            config_get_success, config_data = tester.test_get_configuracion_lavadero(carlos_token)
            
            if config_get_success:
                print("✅ GET configuración successful - default config created if needed")
                
                # PUT configuracion with test values
                print("\n   Testing PUT /admin/configuracion...")
                config_put_success, _ = tester.test_update_configuracion_lavadero(carlos_token)
                
                if config_put_success:
                    print("✅ PUT configuración successful - test values applied")
                else:
                    print("❌ PUT configuración failed")
            else:
                print("❌ GET configuración failed")
            
            # Step 3: Test días no laborales endpoints
            print("\n3️⃣ Testing días no laborales endpoints...")
            
            # GET días no laborales (should return empty list initially)
            print("\n   Testing GET /admin/dias-no-laborales...")
            dias_get_success, dias_data = tester.test_get_dias_no_laborales(carlos_token)
            
            if dias_get_success:
                print(f"✅ GET días no laborales successful - found {len(dias_data) if isinstance(dias_data, list) else 0} days")
                
                # POST add día no laboral for tomorrow
                print("\n   Testing POST /admin/dias-no-laborales...")
                dia_add_success, dia_add_data = tester.test_add_dia_no_laboral(carlos_token)
                
                if dia_add_success:
                    print("✅ POST día no laboral successful - tomorrow added")
                    
                    # GET días no laborales again to verify it was added
                    print("\n   Verifying día was added...")
                    dias_verify_success, dias_verify_data = tester.test_get_dias_no_laborales(carlos_token)
                    
                    if dias_verify_success and isinstance(dias_verify_data, list):
                        print(f"✅ Verification successful - now have {len(dias_verify_data)} días no laborales")
                        
                        # DELETE the día we just added
                        if len(dias_verify_data) > 0 and 'id' in dias_verify_data[-1]:
                            dia_id_to_delete = dias_verify_data[-1]['id']
                            print(f"\n   Testing DELETE /admin/dias-no-laborales/{dia_id_to_delete}...")
                            dia_delete_success, _ = tester.test_delete_dia_no_laboral(carlos_token, dia_id_to_delete)
                            
                            if dia_delete_success:
                                print("✅ DELETE día no laboral successful")
                            else:
                                print("❌ DELETE día no laboral failed")
                        else:
                            print("⚠️  No día ID found to delete")
                    else:
                        print("❌ Verification failed - could not get días no laborales")
                else:
                    print("❌ POST día no laboral failed")
            else:
                print("❌ GET días no laborales failed")
            
        else:
            print(f"❌ ERROR: Carlos has role {carlos_user.get('rol')} instead of ADMIN")
    else:
        print("❌ Carlos login failed - cannot test configuration endpoints")
    
    # Step 4: Test that Super Admin CANNOT access /admin/ endpoints
    if super_admin_success and super_admin_token:
        print("\n4️⃣ Testing Super Admin CANNOT access /admin/ endpoints...")
        super_admin_blocked_success = tester.test_super_admin_cannot_access_admin_endpoints(super_admin_token)
        
        if super_admin_blocked_success:
            print("✅ Super Admin correctly blocked from /admin/ endpoints")
        else:
            print("❌ Super Admin access control failed")
    else:
        print("⚠️  Cannot test Super Admin blocking - Super Admin login failed")
    
    # SPECIFIC TASK: Test NEW TOGGLE LAVADERO LOGIC (MAIN FOCUS FROM REVIEW REQUEST)
    print("\n📋 SPECIFIC TASK: NEW TOGGLE LAVADERO LOGIC - DEACTIVATION CREATES PENDIENTE PAYMENT")
    print("🎯 Task: Test new logic where deactivating ACTIVO lavadero creates PENDIENTE payment")
    
    if super_admin_success and super_admin_token:
        toggle_results = tester.test_new_toggle_lavadero_logic(super_admin_token)
        
        # Summary of toggle testing results
        print("\n📊 NEW TOGGLE LOGIC TESTING SUMMARY:")
        print("=" * 60)
        print(f"✅ Admin with ACTIVO Found: {toggle_results['admin_with_activo_found']}")
        print(f"✅ Deactivation Successful: {toggle_results['deactivation_successful']}")
        print(f"✅ PENDIENTE Payment Created: {toggle_results['pendiente_payment_created']}")
        print(f"✅ Admin Can Login: {toggle_results['admin_can_login']}")
        print(f"✅ Admin Has Pending Payment: {toggle_results['admin_has_pending_payment']}")
        print(f"✅ Admin Can Upload Comprobante: {toggle_results['admin_can_upload_comprobante']}")
        print(f"✅ Reactivation Successful: {toggle_results['reactivation_successful']}")
        
        # Calculate toggle test success rate
        toggle_checks = [
            toggle_results['admin_with_activo_found'],
            toggle_results['deactivation_successful'],
            toggle_results['pendiente_payment_created'],
            toggle_results['admin_can_login'],
            toggle_results['admin_has_pending_payment'],
            toggle_results['admin_can_upload_comprobante'],
            toggle_results['reactivation_successful']
        ]
        
        toggle_success_rate = sum(toggle_checks) / len(toggle_checks) * 100
        print(f"\n🎯 NEW TOGGLE LOGIC SUCCESS RATE: {toggle_success_rate:.1f}% ({sum(toggle_checks)}/{len(toggle_checks)})")
        
        if toggle_success_rate >= 85:
            print("🎉 NEW TOGGLE LAVADERO LOGIC IS WORKING CORRECTLY!")
        else:
            print("⚠️  NEW TOGGLE LAVADERO LOGIC NEEDS ATTENTION")
    else:
        print("❌ Cannot test toggle logic - Super Admin login failed")
    
    # SPECIFIC TASK: Test payment voucher functionality for PENDIENTE admins
    print("\n📋 SPECIFIC TASK: PAYMENT VOUCHER FUNCTIONALITY FOR PENDIENTE ADMINS")
    print("🎯 Task: Verify and test payment voucher upload for admins with PENDIENTE_APROBACION status")
    
    if super_admin_success and super_admin_token:
        voucher_results = tester.test_payment_voucher_functionality(super_admin_token)
        
        # Summary of voucher testing results
        print("\n📊 VOUCHER TESTING SUMMARY:")
        print("=" * 50)
        print(f"✅ Test Admins Found: {voucher_results['admins_found']}")
        print(f"✅ Juan Login Works: {voucher_results['juan_login']}")
        print(f"✅ Juan Has Payment: {voucher_results['juan_has_payment']}")
        print(f"✅ Pago Pendiente Endpoint: {voucher_results['pago_pendiente_works']}")
        print(f"✅ Voucher Upload Works: {voucher_results['voucher_upload_works']}")
        
        # Calculate voucher test success rate
        voucher_checks = [
            voucher_results['admins_found'],
            voucher_results['juan_login'],
            voucher_results['juan_has_payment'],
            voucher_results['pago_pendiente_works'],
            voucher_results['voucher_upload_works']
        ]
        
        voucher_success_count = sum(voucher_checks)
        voucher_total = len(voucher_checks)
        voucher_success_rate = (voucher_success_count / voucher_total) * 100
        
        print(f"\n🎯 VOUCHER TEST SUCCESS RATE: {voucher_success_count}/{voucher_total} ({voucher_success_rate:.1f}%)")
        
        if voucher_success_rate == 100:
            print("🎉 VOUCHER FUNCTIONALITY WORKING PERFECTLY!")
            print("   ✅ Juan (PENDIENTE admin) can upload payment vouchers")
            print("   ✅ All payment endpoints working correctly")
            print("   ✅ Fix for /superadmin/crear-admin payment creation is working")
        else:
            print("⚠️  VOUCHER FUNCTIONALITY HAS ISSUES")
            failed_voucher_checks = []
            if not voucher_results['admins_found']: failed_voucher_checks.append("Test admins not found")
            if not voucher_results['juan_login']: failed_voucher_checks.append("Juan login failed")
            if not voucher_results['juan_has_payment']: failed_voucher_checks.append("Juan missing payment")
            if not voucher_results['pago_pendiente_works']: failed_voucher_checks.append("Pago pendiente endpoint")
            if not voucher_results['voucher_upload_works']: failed_voucher_checks.append("Voucher upload")
            print(f"   ❌ Issues: {', '.join(failed_voucher_checks)}")
    else:
        print("❌ Cannot test voucher functionality - Super Admin login failed")

    # SPECIFIC TASK: Test new file upload functionality
    print("\n📋 SPECIFIC TASK: TEST NEW FILE UPLOAD FUNCTIONALITY")
    print("🎯 Task: Test new file upload endpoint for payment vouchers")
    
    if super_admin_success and super_admin_token:
        upload_results = tester.test_file_upload_comprobante_functionality(super_admin_token)
        
        # Summary of file upload testing results
        print("\n📊 FILE UPLOAD TESTING SUMMARY:")
        print("=" * 50)
        print(f"✅ Juan Login Works: {upload_results['juan_login']}")
        print(f"✅ Has Pending Payment: {upload_results['has_pending_payment']}")
        print(f"✅ File Upload Success: {upload_results['file_upload_success']}")
        print(f"✅ File Validation Works: {upload_results['file_validation_works']}")
        print(f"✅ File Stored Correctly: {upload_results['file_stored_correctly']}")
        print(f"✅ URL Accessible: {upload_results['url_accessible']}")
        print(f"✅ Database Updated: {upload_results['database_updated']}")
        
        # Calculate upload test success rate
        upload_checks = [
            upload_results['juan_login'],
            upload_results['has_pending_payment'],
            upload_results['file_upload_success'],
            upload_results['file_validation_works'],
            upload_results['file_stored_correctly'],
            upload_results['url_accessible'],
            upload_results['database_updated']
        ]
        
        upload_success_count = sum(upload_checks)
        upload_total = len(upload_checks)
        upload_success_rate = (upload_success_count / upload_total) * 100
        
        print(f"\n🎯 FILE UPLOAD TEST SUCCESS RATE: {upload_success_count}/{upload_total} ({upload_success_rate:.1f}%)")
        
        if upload_success_rate == 100:
            print("🎉 FILE UPLOAD FUNCTIONALITY WORKING PERFECTLY!")
            print("   ✅ File upload with multipart/form-data works")
            print("   ✅ File validation (size and type) works")
            print("   ✅ Files stored correctly in /app/uploads/comprobantes/")
            print("   ✅ URLs accessible and database updated")
        else:
            print("⚠️  FILE UPLOAD FUNCTIONALITY HAS ISSUES")
            failed_upload_checks = []
            if not upload_results['juan_login']: failed_upload_checks.append("Juan login")
            if not upload_results['has_pending_payment']: failed_upload_checks.append("No pending payment")
            if not upload_results['file_upload_success']: failed_upload_checks.append("File upload failed")
            if not upload_results['file_validation_works']: failed_upload_checks.append("File validation")
            if not upload_results['file_stored_correctly']: failed_upload_checks.append("File storage")
            if not upload_results['url_accessible']: failed_upload_checks.append("URL accessibility")
            if not upload_results['database_updated']: failed_upload_checks.append("Database update")
            print(f"   ❌ Issues: {', '.join(failed_upload_checks)}")
    else:
        print("❌ Cannot test file upload functionality - Super Admin login failed")

    # SPECIFIC TASK: Test image serving for comprobantes
    print("\n📋 SPECIFIC TASK: TEST IMAGE SERVING FOR COMPROBANTES")
    print("🎯 Task: Verify image display functionality in Super Admin dashboard")
    
    if super_admin_success and super_admin_token:
        image_results = tester.test_image_serving_for_comprobantes(super_admin_token)
        
        # Summary of image serving testing results
        print("\n📊 IMAGE SERVING TESTING SUMMARY:")
        print("=" * 50)
        print(f"✅ Super Admin Login: {image_results['super_admin_login']}")
        print(f"✅ Image Endpoint Works: {image_results['image_endpoint_works']}")
        print(f"✅ Comprobantes Pendientes Works: {image_results['comprobantes_pendientes_works']}")
        print(f"✅ Image URLs Correct: {image_results['image_urls_correct']}")
        print(f"✅ Actual Files Accessible: {image_results['actual_files_accessible']}")
        print(f"✅ Content Type Correct: {image_results['content_type_correct']}")
        
        # Calculate image serving test success rate
        image_checks = [
            image_results['super_admin_login'],
            image_results['image_endpoint_works'],
            image_results['comprobantes_pendientes_works'],
            image_results['image_urls_correct'],
            image_results['actual_files_accessible'],
            image_results['content_type_correct']
        ]
        
        image_success_count = sum(image_checks)
        image_total = len(image_checks)
        image_success_rate = (image_success_count / image_total) * 100
        
        print(f"\n🎯 IMAGE SERVING TEST SUCCESS RATE: {image_success_count}/{image_total} ({image_success_rate:.1f}%)")
        
        if image_success_rate == 100:
            print("🎉 IMAGE SERVING FUNCTIONALITY WORKING PERFECTLY!")
            print("   ✅ Image serving endpoint /api/uploads/comprobantes/{filename} works")
            print("   ✅ Comprobantes pendientes endpoint returns correct data")
            print("   ✅ Image URLs are correctly formatted")
            print("   ✅ Actual uploaded files are accessible")
            print("   ✅ Correct content-type headers returned")
            print("   ✅ Frontend URL construction pattern ${API}${imagen_url} works")
        else:
            print("⚠️  IMAGE SERVING FUNCTIONALITY HAS ISSUES")
            failed_image_checks = []
            if not image_results['super_admin_login']: failed_image_checks.append("Super Admin login")
            if not image_results['image_endpoint_works']: failed_image_checks.append("Image endpoint")
            if not image_results['comprobantes_pendientes_works']: failed_image_checks.append("Comprobantes pendientes")
            if not image_results['image_urls_correct']: failed_image_checks.append("Image URL format")
            if not image_results['actual_files_accessible']: failed_image_checks.append("File accessibility")
            if not image_results['content_type_correct']: failed_image_checks.append("Content-type headers")
            print(f"   ❌ Issues: {', '.join(failed_image_checks)}")
    else:
        print("❌ Cannot test image serving functionality - Super Admin login failed")

    # SPECIFIC TASK: Create 2 new admins for testing
    print("\n📋 SPECIFIC TASK: CREATE 2 NEW ADMINS FOR TESTING")
    print("🎯 Task: Create María and Juan with their lavaderos for comprehensive testing")
    
    if super_admin_success and super_admin_token:
        task_results = tester.test_create_two_new_admins_for_testing(super_admin_token)
        
        # Summary of task results
        print("\n📊 TASK COMPLETION SUMMARY:")
        print("=" * 50)
        print(f"✅ Admin 1 (María) Created: {task_results['admin1_created']}")
        print(f"✅ Admin 2 (Juan) Created: {task_results['admin2_created']}")
        print(f"✅ Both Lavaderos PENDIENTE: {task_results['lavaderos_pending']}")
        print(f"✅ Passwords in Credentials: {task_results['passwords_in_credentials']}")
        print(f"✅ Admin 1 Login Works: {task_results['admin1_login']}")
        print(f"✅ Admin 2 Login Works: {task_results['admin2_login']}")
        print(f"✅ Toggle Test (Optional): {task_results['toggle_test']}")
        
        # Calculate task success rate
        task_checks = [
            task_results['admin1_created'],
            task_results['admin2_created'], 
            task_results['lavaderos_pending'],
            task_results['passwords_in_credentials'],
            task_results['admin1_login'],
            task_results['admin2_login']
        ]
        
        task_success_count = sum(task_checks)
        task_total = len(task_checks)
        task_success_rate = (task_success_count / task_total) * 100
        
        print(f"\n🎯 TASK SUCCESS RATE: {task_success_count}/{task_total} ({task_success_rate:.1f}%)")
        
        if task_success_rate == 100:
            print("🎉 TASK COMPLETED SUCCESSFULLY!")
            print("   ✅ Both admins created with correct lavaderos")
            print("   ✅ All verification checks passed")
            print("   ✅ Ready for comprehensive testing with 3 admins total")
        else:
            print("⚠️  TASK PARTIALLY COMPLETED - Some checks failed")
            failed_checks = []
            if not task_results['admin1_created']: failed_checks.append("Admin 1 creation")
            if not task_results['admin2_created']: failed_checks.append("Admin 2 creation") 
            if not task_results['lavaderos_pending']: failed_checks.append("Lavaderos pending state")
            if not task_results['passwords_in_credentials']: failed_checks.append("Passwords in credentials")
            if not task_results['admin1_login']: failed_checks.append("Admin 1 login")
            if not task_results['admin2_login']: failed_checks.append("Admin 2 login")
            print(f"   ❌ Failed: {', '.join(failed_checks)}")
    else:
        print("❌ Cannot execute task - Super Admin login failed")
    
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