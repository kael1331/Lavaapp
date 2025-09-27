#!/usr/bin/env python3
"""
Quick test to verify Juan can now upload vouchers
"""
import requests
import json

def test_juan_voucher():
    base_url = "https://laundry-mgmt-1.preview.emergentagent.com/api"
    
    print("🧪 TESTING JUAN'S VOUCHER FUNCTIONALITY")
    print("=" * 45)
    
    # Step 1: Login as Juan
    print("\n1️⃣ Logging in as Juan...")
    login_response = requests.post(f"{base_url}/login", json={
        "email": "juan@lavaderonorte.com",
        "password": "juan123"
    })
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.text}")
        return
    
    login_data = login_response.json()
    token = login_data['access_token']
    print(f"✅ Login successful - Token: {token[:20]}...")
    
    # Step 2: Check pago pendiente
    print("\n2️⃣ Checking pago pendiente...")
    headers = {'Authorization': f'Bearer {token}'}
    pago_response = requests.get(f"{base_url}/admin/pago-pendiente", headers=headers)
    
    if pago_response.status_code != 200:
        print(f"❌ Pago pendiente failed: {pago_response.text}")
        return
    
    pago_data = pago_response.json()
    print(f"✅ Pago pendiente response:")
    print(json.dumps(pago_data, indent=2))
    
    if not pago_data.get('tiene_pago_pendiente'):
        print("❌ Juan still doesn't have pending payment")
        return
    
    # Step 3: Upload voucher
    print("\n3️⃣ Uploading payment voucher...")
    voucher_data = {
        "imagen_url": "https://example.com/comprobante-juan-test-fixed.jpg"
    }
    
    voucher_response = requests.post(
        f"{base_url}/comprobante-mensualidad", 
        json=voucher_data, 
        headers=headers
    )
    
    if voucher_response.status_code != 200:
        print(f"❌ Voucher upload failed: {voucher_response.text}")
        return
    
    voucher_result = voucher_response.json()
    print(f"✅ Voucher upload successful:")
    print(json.dumps(voucher_result, indent=2))
    
    # Step 4: Verify voucher was created
    print("\n4️⃣ Verifying voucher was created...")
    verify_response = requests.get(f"{base_url}/admin/pago-pendiente", headers=headers)
    
    if verify_response.status_code == 200:
        verify_data = verify_response.json()
        if verify_data.get('tiene_comprobante'):
            print("✅ Voucher creation verified - tiene_comprobante is now true")
            print(f"   Estado comprobante: {verify_data.get('estado_comprobante')}")
        else:
            print("⚠️  Voucher creation not reflected in pago-pendiente")
    
    # Step 5: Check voucher history
    print("\n5️⃣ Checking voucher history...")
    history_response = requests.get(f"{base_url}/admin/mis-comprobantes", headers=headers)
    
    if history_response.status_code == 200:
        history_data = history_response.json()
        print(f"✅ Voucher history: {len(history_data)} comprobantes found")
        for i, comp in enumerate(history_data):
            print(f"   {i+1}. Estado: {comp.get('estado')}, Monto: ${comp.get('monto')}")
    
    print("\n🎉 JUAN'S VOUCHER FUNCTIONALITY TEST COMPLETE!")

if __name__ == "__main__":
    test_juan_voucher()