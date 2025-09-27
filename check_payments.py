#!/usr/bin/env python3
"""
Quick script to check the payment status for Juan and other admins
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
ROOT_DIR = Path(__file__).parent / "backend"
load_dotenv(ROOT_DIR / '.env')

async def check_payments():
    # MongoDB connection
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    print("🔍 CHECKING PAYMENT STATUS FOR ADMINS")
    print("=" * 50)
    
    # Get all admins
    admins_cursor = db.users.find({"rol": "ADMIN"})
    admins = await admins_cursor.to_list(1000)
    
    print(f"Found {len(admins)} admins:")
    
    for admin in admins:
        print(f"\n👤 Admin: {admin['nombre']} ({admin['email']})")
        print(f"   ID: {admin['id']}")
        
        # Check for payments
        payments_cursor = db.pagos_mensualidad.find({"admin_id": admin['id']})
        payments = await payments_cursor.to_list(100)
        
        print(f"   💰 Payments found: {len(payments)}")
        
        for payment in payments:
            print(f"      - Pago ID: {payment['id']}")
            print(f"        Monto: ${payment['monto']}")
            print(f"        Estado: {payment['estado']}")
            print(f"        Mes/Año: {payment['mes_año']}")
            print(f"        Vencimiento: {payment.get('fecha_vencimiento')}")
        
        # Check for vouchers
        vouchers_cursor = db.comprobantes_pago_mensualidad.find({"admin_id": admin['id']})
        vouchers = await vouchers_cursor.to_list(100)
        
        print(f"   📄 Vouchers found: {len(vouchers)}")
        
        for voucher in vouchers:
            print(f"      - Voucher ID: {voucher['id']}")
            print(f"        Estado: {voucher['estado']}")
            print(f"        Pago ID: {voucher['pago_mensualidad_id']}")
    
    # Check Super Admin configuration
    print(f"\n🔧 SUPER ADMIN CONFIGURATION:")
    config = await db.configuracion_superadmin.find_one({})
    if config:
        print(f"   Alias bancario: {config.get('alias_bancario')}")
        print(f"   Precio mensualidad: ${config.get('precio_mensualidad')}")
    else:
        print("   ❌ No Super Admin configuration found")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_payments())