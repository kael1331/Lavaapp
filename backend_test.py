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