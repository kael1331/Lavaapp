#!/usr/bin/env python3
"""
Script to create a pending payment for Juan so he can upload vouchers
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timedelta, timezone
import uuid

# Load environment variables
ROOT_DIR = Path(__file__).parent / "backend"
load_dotenv(ROOT_DIR / '.env')

async def fix_juan_payment():
    # MongoDB connection
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    print("🔧 FIXING JUAN'S PAYMENT STATUS")
    print("=" * 40)
    
    # Find Juan
    juan = await db.users.find_one({"email": "juan@lavaderonorte.com"})
    if not juan:
        print("❌ Juan not found")
        return
    
    print(f"✅ Found Juan: {juan['nombre']} (ID: {juan['id']})")
    
    # Find Juan's lavadero
    lavadero = await db.lavaderos.find_one({"admin_id": juan['id']})
    if not lavadero:
        print("❌ Juan's lavadero not found")
        return
    
    print(f"✅ Found lavadero: {lavadero['nombre']} (Estado: {lavadero['estado_operativo']})")
    
    # Check current payments
    payments = await db.pagos_mensualidad.find({"admin_id": juan['id']}).to_list(100)
    print(f"📊 Current payments: {len(payments)}")
    
    for payment in payments:
        print(f"   - {payment['estado']} payment for {payment['mes_año']} (${payment['monto']})")
    
    # Check if there's already a PENDIENTE payment for current month
    current_month = datetime.now().strftime("%Y-%m")
    pending_payment = await db.pagos_mensualidad.find_one({
        "admin_id": juan['id'],
        "estado": "PENDIENTE",
        "mes_año": current_month
    })
    
    if pending_payment:
        print(f"✅ Juan already has a PENDIENTE payment for {current_month}")
        return
    
    # Get Super Admin configuration
    config = await db.configuracion_superadmin.find_one({})
    if not config:
        print("❌ Super Admin configuration not found")
        return
    
    # Create new PENDIENTE payment for Juan
    print(f"\n🆕 Creating new PENDIENTE payment for Juan...")
    
    new_payment = {
        "id": str(uuid.uuid4()),
        "admin_id": juan['id'],
        "lavadero_id": lavadero['id'],
        "monto": config['precio_mensualidad'],
        "mes_año": current_month,
        "estado": "PENDIENTE",
        "fecha_vencimiento": datetime.now(timezone.utc) + timedelta(days=30),
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.pagos_mensualidad.insert_one(new_payment)
    
    print(f"✅ Created PENDIENTE payment:")
    print(f"   - Payment ID: {new_payment['id']}")
    print(f"   - Amount: ${new_payment['monto']}")
    print(f"   - Month: {new_payment['mes_año']}")
    print(f"   - Due: {new_payment['fecha_vencimiento']}")
    
    print(f"\n🎯 Juan should now be able to upload payment vouchers!")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(fix_juan_payment())