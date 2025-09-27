from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Union
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import JWTError, jwt
from dotenv import load_dotenv
from pathlib import Path
import os
import logging
import uuid
import requests
import json

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
SECRET_KEY = "mi-clave-secreta-super-segura-para-demo-12345"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()

# Create FastAPI app
app = FastAPI(title="Demo Authentication API")
api_router = APIRouter(prefix="/api")

# User Models
class UserRole(str):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"  # Dueño de lavadero
    CLIENTE = "CLIENTE"  # Cliente que saca turnos

class UserBase(BaseModel):
    email: EmailStr
    nombre: str
    rol: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: str
    created_at: datetime
    is_active: bool
    google_id: Optional[str] = None
    picture: Optional[str] = None

class User(UserBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    password_hash: Optional[str] = None  # Optional for Google users
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    google_id: Optional[str] = None
    picture: Optional[str] = None

class GoogleUser(BaseModel):
    email: EmailStr
    nombre: str
    google_id: str
    picture: Optional[str] = None
    rol: str = "EMPLEADO"  # Default role for Google users

class GoogleSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SessionDataResponse(BaseModel):
    id: str
    email: str
    name: str
    picture: str
    session_token: str

class DashboardStats(BaseModel):
    total_users: int
    total_employees: int
    active_projects: int
    pending_tasks: int

class UserStats(BaseModel):
    my_tasks: int
    completed_tasks: int
    pending_tasks: int

# ========== MODELOS DEL SISTEMA DE LAVADEROS ==========

class EstadoAdmin(str):
    PENDIENTE_APROBACION = "PENDIENTE_APROBACION"
    ACTIVO = "ACTIVO"
    VENCIDO = "VENCIDO"
    BLOQUEADO = "BLOQUEADO"

class EstadoTurno(str):
    DISPONIBLE = "DISPONIBLE"
    RESERVADO = "RESERVADO"
    CONFIRMADO = "CONFIRMADO"
    CANCELADO = "CANCELADO"

class EstadoPago(str):
    PENDIENTE = "PENDIENTE"
    CONFIRMADO = "CONFIRMADO"
    RECHAZADO = "RECHAZADO"

# Configuración Super Admin
class ConfiguracionSuperAdmin(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    alias_bancario: str
    precio_mensualidad: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Lavadero
class Lavadero(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nombre: str
    direccion: str
    descripcion: Optional[str] = None
    admin_id: str  # ID del usuario admin
    estado_operativo: str = EstadoAdmin.PENDIENTE_APROBACION
    fecha_vencimiento: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

class LavaderoCreate(BaseModel):
    nombre: str
    direccion: str
    descripcion: Optional[str] = None

class LavaderoResponse(BaseModel):
    id: str
    nombre: str
    direccion: str
    descripcion: Optional[str] = None
    estado_operativo: str
    fecha_vencimiento: Optional[datetime] = None
    created_at: datetime

# Configuración de Lavadero
class ConfiguracionLavadero(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lavadero_id: str
    hora_apertura: str  # "08:00"
    hora_cierre: str    # "18:00"
    duracion_turno_minutos: int  # 30
    dias_laborales: List[int]  # [1,2,3,4,5] (1=Lunes, 7=Domingo)
    alias_bancario: str
    precio_turno: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ConfiguracionLavaderoCreate(BaseModel):
    hora_apertura: str
    hora_cierre: str
    duracion_turno_minutos: int
    dias_laborales: List[int]
    alias_bancario: str
    precio_turno: float

# Día No laboral
class DiaNoLaboral(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lavadero_id: str
    fecha: datetime  # Solo la fecha, no la hora
    motivo: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DiaNoLaboralCreate(BaseModel):
    fecha: datetime
    motivo: Optional[str] = None

# Turno
class Turno(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lavadero_id: str
    cliente_id: Optional[str] = None  # None si está disponible
    fecha_hora: datetime
    estado: str = EstadoTurno.DISPONIBLE
    precio: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TurnoCreate(BaseModel):
    fecha_hora: datetime

class TurnoResponse(BaseModel):
    id: str
    lavadero_id: str
    cliente_id: Optional[str] = None
    fecha_hora: datetime
    estado: str
    precio: float
    created_at: datetime

# Comprobante de Pago (Turnos)
class ComprobantePago(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    turno_id: str
    cliente_id: str
    imagen_url: str  # URL o path de la imagen
    estado: str = EstadoPago.PENDIENTE
    comentario_admin: Optional[str] = None
    fecha_revision: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ComprobantePagoCreate(BaseModel):
    turno_id: str
    imagen_url: str

# Pago Mensualidad (Admins al Super Admin)
class PagoMensualidad(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    admin_id: str
    lavadero_id: str
    monto: float
    mes_año: str  # "2024-01"
    estado: str = EstadoPago.PENDIENTE
    fecha_vencimiento: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Comprobante Pago Mensualidad
class ComprobantePagoMensualidad(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pago_mensualidad_id: str
    admin_id: str
    imagen_url: str
    estado: str = EstadoPago.PENDIENTE
    comentario_superadmin: Optional[str] = None
    fecha_revision: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ComprobantePagoMensualidadCreate(BaseModel):
    imagen_url: str

class RechazarComprobanteRequest(BaseModel):
    comentario: str

# Registro de Admin con Lavadero
class AdminLavaderoRegister(BaseModel):
    # Datos del admin
    email: EmailStr
    password: str
    nombre: str
    # Datos del lavadero
    lavadero: LavaderoCreate

# Utility functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_user_by_email(email: str):
    user_doc = await db.users.find_one({"email": email})
    if user_doc:
        return User(**user_doc)
    return None

async def authenticate_user(email: str, password: str):
    # Super Admin hardcodeado
    if email == "kearcangel@gmail.com" and password == "K@#l1331":
        # Crear o obtener usuario Super Admin
        super_admin = await get_user_by_email(email)
        if not super_admin:
            # Crear Super Admin si no existe
            super_admin = User(
                email=email,
                nombre="Super Admin",
                rol=UserRole.SUPER_ADMIN,
                password_hash=get_password_hash(password)
            )
            user_dict = super_admin.dict()
            await db.users.insert_one(user_dict)
        else:
            # Si existe pero no es SUPER_ADMIN, actualizarlo
            if super_admin.rol != UserRole.SUPER_ADMIN:
                await db.users.update_one(
                    {"email": email},
                    {"$set": {"rol": UserRole.SUPER_ADMIN}}
                )
                super_admin.rol = UserRole.SUPER_ADMIN
        return super_admin
    
    # Autenticación normal para otros usuarios
    user = await get_user_by_email(email)
    if not user:
        return False
    if not user.password_hash or not verify_password(password, user.password_hash):
        return False
    return user

async def get_session_user(session_token: str):
    """Get user from session token"""
    session_doc = await db.google_sessions.find_one({"session_token": session_token})
    if not session_doc:
        return None
    
    session = GoogleSession(**session_doc)
    
    # Check if session is expired
    current_time = datetime.now(timezone.utc)
    session_expires = session.expires_at
    
    # Ensure both datetimes are timezone-aware for comparison
    if session_expires.tzinfo is None:
        session_expires = session_expires.replace(tzinfo=timezone.utc)
    
    if session_expires < current_time:
        await db.google_sessions.delete_one({"session_token": session_token})
        return None
    
    # Get user
    user_doc = await db.users.find_one({"id": session.user_id})
    if user_doc:
        return User(**user_doc)
    return None

async def get_current_user(request: Request):
    # First try to get user from session cookie (Google OAuth)
    session_token = request.cookies.get("session_token")
    if session_token:
        user = await get_session_user(session_token)
        if user:
            return user
    
    # Fallback to JWT token (regular login)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            token = auth_header.split(" ")[1]
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("sub")
            if email is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception
        
        user = await get_user_by_email(email)
        if user is None:
            raise credentials_exception
        return user
    
    # No authentication found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No authentication provided",
        headers={"WWW-Authenticate": "Bearer"},
    )

async def get_current_user_optional(request: Request):
    """Get current user without requiring authentication"""
    # Try session cookie first
    session_token = request.cookies.get("session_token")
    if session_token:
        user = await get_session_user(session_token)
        if user:
            return user
    
    # Try JWT from Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ")[1]
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("sub")
            if email:
                user = await get_user_by_email(email)
                return user
        except JWTError:
            pass
    
    return None

async def get_admin_user(request: Request):
    current_user = await get_current_user(request)
    if current_user.rol not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos de administrador"
        )
    return current_user

async def get_super_admin_user(request: Request):
    current_user = await get_current_user(request)
    if current_user.rol != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos de super administrador"
        )
    return current_user

async def get_lavadero_by_id(lavadero_id: str):
    lavadero_doc = await db.lavaderos.find_one({"id": lavadero_id})
    if lavadero_doc:
        return Lavadero(**lavadero_doc)
    return None

async def verify_admin_owns_lavadero(admin_id: str, lavadero_id: str):
    lavadero = await get_lavadero_by_id(lavadero_id)
    if not lavadero or lavadero.admin_id != admin_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a este lavadero"
        )
    return lavadero

# ========== ENDPOINTS DE REGISTRO ==========

# Registro normal (solo para clientes)
@api_router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserCreate):
    # Check if user already exists
    existing_user = await get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    
    # Solo permitir registro de clientes por esta ruta
    if user_data.rol != UserRole.CLIENTE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta ruta es solo para clientes"
        )
    
    # Create user
    password_hash = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        nombre=user_data.nombre,
        rol=user_data.rol,
        password_hash=password_hash
    )
    
    # Insert to database
    user_dict = new_user.dict()
    await db.users.insert_one(user_dict)
    
    return UserResponse(**user_dict)

# Registro de Admin con Lavadero
@api_router.post("/register-admin", response_model=dict)
async def register_admin_with_lavadero(admin_data: AdminLavaderoRegister):
    # Check if user already exists
    existing_user = await get_user_by_email(admin_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    
    # Check if lavadero name already exists (case-insensitive)
    existing_lavadero = await db.lavaderos.find_one({
        "nombre": {"$regex": f"^{admin_data.lavadero.nombre}$", "$options": "i"}
    })
    if existing_lavadero:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un lavadero con ese nombre"
        )
    
    # Create admin user
    password_hash = get_password_hash(admin_data.password)
    new_admin = User(
        email=admin_data.email,
        nombre=admin_data.nombre,
        rol=UserRole.ADMIN,
        password_hash=password_hash
    )
    
    # Insert admin to database
    admin_dict = new_admin.dict()
    await db.users.insert_one(admin_dict)
    
    # Guardar credencial en tabla temporal para testing
    await db.temp_credentials.insert_one({
        "admin_email": admin_data.email,
        "password": admin_data.password,
        "created_at": datetime.now(timezone.utc)
    })
    
    # Create lavadero
    new_lavadero = Lavadero(
        nombre=admin_data.lavadero.nombre,
        direccion=admin_data.lavadero.direccion,
        descripcion=admin_data.lavadero.descripcion,
        admin_id=new_admin.id,
        estado_operativo=EstadoAdmin.PENDIENTE_APROBACION
    )
    
    # Insert lavadero to database
    lavadero_dict = new_lavadero.dict()
    await db.lavaderos.insert_one(lavadero_dict)
    
    # Create pago mensualidad pendiente
    # Obtener configuración super admin
    config_super = await db.configuracion_superadmin.find_one({})
    if not config_super:
        # Crear configuración por defecto si no existe
        default_config = ConfiguracionSuperAdmin(
            alias_bancario="superadmin.alias.mp",
            precio_mensualidad=10000.0
        )
        await db.configuracion_superadmin.insert_one(default_config.dict())
        config_super = default_config.dict()
    
    # Crear pago mensualidad
    from datetime import datetime, timedelta
    fecha_vencimiento = datetime.now(timezone.utc) + timedelta(days=30)
    
    pago_mensualidad = PagoMensualidad(
        admin_id=new_admin.id,
        lavadero_id=new_lavadero.id,
        monto=config_super.get("precio_mensualidad", 10000.0),
        mes_año=datetime.now().strftime("%Y-%m"),
        fecha_vencimiento=fecha_vencimiento
    )
    
    await db.pagos_mensualidad.insert_one(pago_mensualidad.dict())
    
    return {
        "message": "Admin y lavadero registrados correctamente",
        "admin_id": new_admin.id,
        "lavadero_id": new_lavadero.id,
        "pago_id": pago_mensualidad.id,
        "alias_bancario": config_super.get("alias_bancario"),
        "monto_a_pagar": config_super.get("precio_mensualidad", 10000.0),
        "estado": "Debe subir comprobante de pago para activar el lavadero"
    }

@api_router.post("/login", response_model=Token)
async def login(login_data: LoginRequest):
    user = await authenticate_user(login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar estado del admin si no es super admin
    if user.rol == UserRole.ADMIN:
        # Buscar el lavadero del admin
        lavadero_doc = await db.lavaderos.find_one({"admin_id": user.id})
        if lavadero_doc:
            lavadero = Lavadero(**lavadero_doc)
            # Verificar si está vencido
            if lavadero.fecha_vencimiento:
                # Asegurar que ambas fechas tengan timezone para comparar
                fecha_vencimiento = lavadero.fecha_vencimiento
                if fecha_vencimiento.tzinfo is None:
                    fecha_vencimiento = fecha_vencimiento.replace(tzinfo=timezone.utc)
                    
                if fecha_vencimiento < datetime.now(timezone.utc):
                    lavadero.estado_operativo = EstadoAdmin.VENCIDO
                    await db.lavaderos.update_one(
                        {"id": lavadero.id},
                        {"$set": {"estado_operativo": EstadoAdmin.VENCIDO}}
                    )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    user_response = UserResponse(**user.dict())
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )

@api_router.get("/me", response_model=UserResponse)
async def get_current_user_info(request: Request):
    current_user = await get_current_user(request)
    return UserResponse(**current_user.dict())

# Dashboard Routes
@api_router.get("/dashboard/stats")
async def get_dashboard_stats(request: Request):
    current_user = await get_current_user(request)
    
    if current_user.rol == UserRole.SUPER_ADMIN:
        # Super Admin: estadísticas globales
        total_lavaderos = await db.lavaderos.count_documents({})
        lavaderos_activos = await db.lavaderos.count_documents({"estado_operativo": EstadoAdmin.ACTIVO})
        lavaderos_pendientes = await db.lavaderos.count_documents({"estado_operativo": EstadoAdmin.PENDIENTE_APROBACION})
        comprobantes_pendientes = await db.comprobantes_pago_mensualidad.count_documents({"estado": EstadoPago.PENDIENTE})
        
        return {
            "total_lavaderos": total_lavaderos,
            "lavaderos_activos": lavaderos_activos,
            "lavaderos_pendientes": lavaderos_pendientes,
            "comprobantes_pendientes": comprobantes_pendientes
        }
    
    elif current_user.rol == UserRole.ADMIN:
        # Admin: estadísticas de su lavadero
        lavadero_doc = await db.lavaderos.find_one({"admin_id": current_user.id})
        if not lavadero_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lavadero no encontrado"
            )
        
        lavadero = Lavadero(**lavadero_doc)
        
        # Contar turnos
        total_turnos = await db.turnos.count_documents({"lavadero_id": lavadero.id})
        turnos_confirmados = await db.turnos.count_documents({"lavadero_id": lavadero.id, "estado": EstadoTurno.CONFIRMADO})
        turnos_pendientes = await db.turnos.count_documents({"lavadero_id": lavadero.id, "estado": EstadoTurno.RESERVADO})
        comprobantes_pendientes = await db.comprobantes_pago.count_documents({
            "turno_id": {"$in": [turno["id"] async for turno in db.turnos.find({"lavadero_id": lavadero.id})]},
            "estado": EstadoPago.PENDIENTE
        })
        
        # Días restantes de suscripción
        dias_restantes = 0
        if lavadero.fecha_vencimiento:
            diff = lavadero.fecha_vencimiento - datetime.now(timezone.utc)
            dias_restantes = max(0, diff.days)
        
        return {
            "lavadero_nombre": lavadero.nombre,
            "estado_operativo": lavadero.estado_operativo,
            "dias_restantes": dias_restantes,
            "total_turnos": total_turnos,
            "turnos_confirmados": turnos_confirmados,
            "turnos_pendientes": turnos_pendientes,
            "comprobantes_pendientes": comprobantes_pendientes
        }
    
    else:  # CLIENTE
        # Cliente: estadísticas de sus turnos
        mis_turnos = await db.turnos.count_documents({"cliente_id": current_user.id})
        turnos_confirmados = await db.turnos.count_documents({"cliente_id": current_user.id, "estado": EstadoTurno.CONFIRMADO})
        turnos_pendientes = await db.turnos.count_documents({"cliente_id": current_user.id, "estado": EstadoTurno.RESERVADO})
        
        return {
            "mis_turnos": mis_turnos,
            "confirmados": turnos_confirmados,
            "pendientes": turnos_pendientes
        }

# User Management (Admin only)
@api_router.get("/admin/users", response_model=List[UserResponse])
async def get_all_users(request: Request):
    admin_user = await get_admin_user(request)
    users_cursor = db.users.find({})
    users = await users_cursor.to_list(1000)
    return [UserResponse(**user) for user in users]

@api_router.delete("/admin/users/{user_id}")
async def delete_user(user_id: str, request: Request):
    admin_user = await get_admin_user(request)
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    return {"message": "Usuario eliminado correctamente"}

@api_router.put("/admin/users/{user_id}/toggle-status")
async def toggle_user_status(user_id: str, request: Request):
    admin_user = await get_admin_user(request)
    user_doc = await db.users.find_one({"id": user_id})
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    new_status = not user_doc.get("is_active", True)
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_active": new_status}}
    )
    
    return {"message": f"Usuario {'activado' if new_status else 'desactivado'} correctamente"}

# Protected routes examples
@api_router.get("/protected")
async def protected_route(request: Request):
    current_user = await get_current_user(request)
    return {"message": f"Hola {current_user.nombre}, tienes acceso como {current_user.rol}"}

@api_router.get("/admin-only")
async def admin_only_route(request: Request):
    admin_user = await get_admin_user(request)
    return {"message": "Solo los administradores pueden ver esto", "secret": "Información ultra secreta"}

# Google OAuth Session Endpoint
@api_router.get("/session-data", response_model=SessionDataResponse)
async def get_session_data(request: Request):
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session ID requerido"
        )
    
    # Call Emergent Auth API
    try:
        response = requests.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id},
            timeout=10
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session ID inválido"
            )
        
        session_data = response.json()
        
        # Check if user exists, if not create them
        user = await get_user_by_email(session_data["email"])
        
        if not user:
            # Create new Google user with default role
            google_user_data = GoogleUser(
                email=session_data["email"],
                nombre=session_data["name"],
                google_id=session_data["id"],
                picture=session_data.get("picture"),
                rol=UserRole.CLIENTE  # Default role for Google users
            )
            
            new_user = User(
                email=google_user_data.email,
                nombre=google_user_data.nombre,
                rol=google_user_data.rol,
                google_id=google_user_data.google_id,
                picture=google_user_data.picture,
                password_hash=None  # No password for Google users
            )
            
            user_dict = new_user.dict()
            await db.users.insert_one(user_dict)
            user = new_user
        else:
            # Update existing user with Google info if they don't have it
            if not user.google_id:
                await db.users.update_one(
                    {"id": user.id},
                    {"$set": {
                        "google_id": session_data["id"],
                        "picture": session_data.get("picture")
                    }}
                )
                # Update user object
                user.google_id = session_data["id"]
                user.picture = session_data.get("picture")
        
        # Create session in database
        session_token = session_data["session_token"]
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        google_session = GoogleSession(
            user_id=user.id,
            session_token=session_token,
            expires_at=expires_at
        )
        
        await db.google_sessions.insert_one(google_session.dict())
        
        return SessionDataResponse(**session_data)
        
    except requests.RequestException as e:
        logger.error(f"Error calling Emergent Auth API: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error del servidor de autenticación"
        )

class SetSessionCookieRequest(BaseModel):
    session_token: str

@api_router.post("/set-session-cookie")
async def set_session_cookie(response: Response, request_data: SetSessionCookieRequest):
    """Set session cookie after Google OAuth"""
    # Determine if we're in development or production
    is_development = os.environ.get('CORS_ORIGINS', '*') == '*'
    
    response.set_cookie(
        key="session_token",
        value=request_data.session_token,
        max_age=7 * 24 * 60 * 60,  # 7 days
        path="/",
        secure=not is_development,  # Only secure in production
        httponly=True,
        samesite="lax" if is_development else "none"  # Lax for dev, none for prod
    )
    return {"message": "Cookie establecida correctamente"}

@api_router.post("/logout")
async def logout(request: Request, response: Response):
    """Logout user and clear session"""
    # Get session token from cookie
    session_token = request.cookies.get("session_token")
    
    if session_token:
        # Delete session from database
        await db.google_sessions.delete_one({"session_token": session_token})
        
        # Clear cookie
        is_development = os.environ.get('CORS_ORIGINS', '*') == '*'
        response.delete_cookie(
            key="session_token",
            path="/",
            secure=not is_development,
            httponly=True,
            samesite="lax" if is_development else "none"
        )
    
    return {"message": "Sesión cerrada correctamente"}

@api_router.get("/check-session")
async def check_session(request: Request):
    """Check if user has valid session"""
    user = await get_current_user_optional(request)
    if user:
        return {"authenticated": True, "user": UserResponse(**user.dict())}
    return {"authenticated": False}

# Root endpoint
@api_router.get("/")
async def root():
    return {"message": "Hello World", "status": "API funcionando"}

# ========== ENDPOINTS PÚBLICOS ==========

# Obtener lavaderos operativos (para la página inicial)
@api_router.get("/lavaderos-operativos")
async def get_lavaderos_operativos():
    lavaderos_cursor = db.lavaderos.find({
        "estado_operativo": EstadoAdmin.ACTIVO,
        "is_active": True
    })
    lavaderos = await lavaderos_cursor.to_list(1000)
    return [LavaderoResponse(**lavadero) for lavadero in lavaderos]

# Obtener configuración de Super Admin (alias bancario)
@api_router.get("/superadmin-config")
async def get_superadmin_config():
    config = await db.configuracion_superadmin.find_one({})
    if not config:
        # Crear configuración por defecto
        default_config = ConfiguracionSuperAdmin(
            alias_bancario="superadmin.alias.mp",
            precio_mensualidad=10000.0
        )
        await db.configuracion_superadmin.insert_one(default_config.dict())
        config = default_config.dict()
    
    return {
        "alias_bancario": config.get("alias_bancario"),
        "precio_mensualidad": config.get("precio_mensualidad")
    }

# ========== ENDPOINTS SUPER ADMIN ==========

# Ver todos los lavaderos (Super Admin)
@api_router.get("/superadmin/lavaderos")
async def get_all_lavaderos(request: Request):
    await get_super_admin_user(request)
    
    # Join con usuarios para obtener datos del admin
    pipeline = [
        {
            "$lookup": {
                "from": "users",
                "localField": "admin_id",
                "foreignField": "id",
                "as": "admin"
            }
        },
        {"$unwind": "$admin"}
    ]
    
    lavaderos = await db.lavaderos.aggregate(pipeline).to_list(1000)
    
    result = []
    for lavadero in lavaderos:
        result.append({
            "id": lavadero["id"],
            "nombre": lavadero["nombre"],
            "direccion": lavadero["direccion"],
            "admin_nombre": lavadero["admin"]["nombre"],
            "admin_email": lavadero["admin"]["email"],
            "estado_operativo": lavadero["estado_operativo"],
            "fecha_vencimiento": lavadero.get("fecha_vencimiento"),
            "created_at": lavadero["created_at"]
        })
    
    return result

# Obtener comprobantes pendientes (Super Admin)
@api_router.get("/superadmin/comprobantes-pendientes")
async def get_comprobantes_pendientes(request: Request):
    await get_super_admin_user(request)
    
    # Join para obtener información del admin y lavadero
    pipeline = [
        {"$match": {"estado": EstadoPago.PENDIENTE}},
        {
            "$lookup": {
                "from": "pagos_mensualidad",
                "localField": "pago_mensualidad_id",
                "foreignField": "id",
                "as": "pago"
            }
        },
        {"$unwind": "$pago"},
        {
            "$lookup": {
                "from": "users",
                "localField": "admin_id",
                "foreignField": "id",
                "as": "admin"
            }
        },
        {"$unwind": "$admin"},
        {
            "$lookup": {
                "from": "lavaderos",
                "localField": "pago.lavadero_id",
                "foreignField": "id",
                "as": "lavadero"
            }
        },
        {"$unwind": "$lavadero"}
    ]
    
    comprobantes = await db.comprobantes_pago_mensualidad.aggregate(pipeline).to_list(1000)
    
    result = []
    for comp in comprobantes:
        result.append({
            "comprobante_id": comp["id"],
            "admin_nombre": comp["admin"]["nombre"],
            "admin_email": comp["admin"]["email"],
            "lavadero_nombre": comp["lavadero"]["nombre"],
            "monto": comp["pago"]["monto"],
            "imagen_url": comp["imagen_url"],
            "created_at": comp["created_at"]
        })
    
    return result

# ========== ENDPOINTS DE COMPROBANTES ==========

# Subir comprobante de pago mensualidad (Admin)
@api_router.post("/comprobante-mensualidad")
async def upload_comprobante_mensualidad(request: Request, comprobante_data: ComprobantePagoMensualidadCreate):
    current_user = await get_current_user(request)
    
    if current_user.rol != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden subir comprobantes"
        )
    
    # Buscar pago mensualidad pendiente del admin
    pago_pendiente = await db.pagos_mensualidad.find_one({
        "admin_id": current_user.id,
        "estado": EstadoPago.PENDIENTE
    })
    
    if not pago_pendiente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay pagos pendientes para este administrador"
        )
    
    # Verificar si ya existe un comprobante para este pago
    existing_comprobante = await db.comprobantes_pago_mensualidad.find_one({
        "pago_mensualidad_id": pago_pendiente["id"],
        "estado": {"$in": [EstadoPago.PENDIENTE, EstadoPago.CONFIRMADO]}
    })
    
    if existing_comprobante:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un comprobante para este pago"
        )
    
    # Crear comprobante
    nuevo_comprobante = ComprobantePagoMensualidad(
        pago_mensualidad_id=pago_pendiente["id"],
        admin_id=current_user.id,
        imagen_url=comprobante_data.imagen_url
    )
    
    comprobante_dict = nuevo_comprobante.dict()
    await db.comprobantes_pago_mensualidad.insert_one(comprobante_dict)
    
    return {
        "message": "Comprobante subido exitosamente",
        "comprobante_id": nuevo_comprobante.id,
        "estado": "Pendiente de revisión por Super Admin"
    }

# Obtener comprobantes del admin (Admin)
@api_router.get("/admin/mis-comprobantes")
async def get_mis_comprobantes(request: Request):
    current_user = await get_current_user(request)
    
    if current_user.rol != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden ver sus comprobantes"
        )
    
    # Pipeline para obtener comprobantes con información del pago
    pipeline = [
        {"$match": {"admin_id": current_user.id}},
        {
            "$lookup": {
                "from": "pagos_mensualidad",
                "localField": "pago_mensualidad_id",
                "foreignField": "id",  
                "as": "pago"
            }
        },
        {"$unwind": "$pago"},
        {"$sort": {"created_at": -1}}
    ]
    
    comprobantes = await db.comprobantes_pago_mensualidad.aggregate(pipeline).to_list(100)
    
    result = []
    for comp in comprobantes:
        result.append({
            "comprobante_id": comp["id"],
            "monto": comp["pago"]["monto"],
            "mes_año": comp["pago"]["mes_año"],
            "imagen_url": comp["imagen_url"],
            "estado": comp["estado"],
            "comentario_superadmin": comp.get("comentario_superadmin"),
            "fecha_revision": comp.get("fecha_revision"),
            "created_at": comp["created_at"]
        })
    
    return result

# Obtener pago pendiente del admin (Admin)
@api_router.get("/admin/pago-pendiente")
async def get_pago_pendiente(request: Request):
    current_user = await get_current_user(request)
    
    if current_user.rol != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden ver sus pagos"
        )
    
    # Buscar pago pendiente
    pago_pendiente = await db.pagos_mensualidad.find_one({
        "admin_id": current_user.id,
        "estado": EstadoPago.PENDIENTE
    })
    
    if not pago_pendiente:
        return {"tiene_pago_pendiente": False}
    
    # Verificar si ya tiene comprobante
    comprobante = await db.comprobantes_pago_mensualidad.find_one({
        "pago_mensualidad_id": pago_pendiente["id"],
        "estado": {"$in": [EstadoPago.PENDIENTE, EstadoPago.CONFIRMADO]}
    })
    
    return {
        "tiene_pago_pendiente": True,
        "pago_id": pago_pendiente["id"],
        "monto": pago_pendiente["monto"],
        "mes_año": pago_pendiente["mes_año"],
        "fecha_vencimiento": pago_pendiente["fecha_vencimiento"],
        "tiene_comprobante": comprobante is not None,
        "estado_comprobante": comprobante["estado"] if comprobante else None
    }

# Aprobar comprobante (Super Admin)
@api_router.post("/superadmin/aprobar-comprobante/{comprobante_id}")
async def aprobar_comprobante(comprobante_id: str, request: Request):
    await get_super_admin_user(request)
    
    # Buscar comprobante
    comprobante_doc = await db.comprobantes_pago_mensualidad.find_one({"id": comprobante_id})
    if not comprobante_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comprobante no encontrado"
        )
    
    # Actualizar comprobante
    await db.comprobantes_pago_mensualidad.update_one(
        {"id": comprobante_id},
        {
            "$set": {
                "estado": EstadoPago.CONFIRMADO,
                "fecha_revision": datetime.now(timezone.utc),
                "comentario_superadmin": "Pago confirmado"
            }
        }
    )
    
    # Actualizar pago mensualidad
    await db.pagos_mensualidad.update_one(
        {"id": comprobante_doc["pago_mensualidad_id"]},
        {"$set": {"estado": EstadoPago.CONFIRMADO}}
    )
    
    # Buscar y activar lavadero
    pago_doc = await db.pagos_mensualidad.find_one({"id": comprobante_doc["pago_mensualidad_id"]})
    if pago_doc:
        fecha_vencimiento = datetime.now(timezone.utc) + timedelta(days=30)
        await db.lavaderos.update_one(
            {"id": pago_doc["lavadero_id"]},
            {
                "$set": {
                    "estado_operativo": EstadoAdmin.ACTIVO,
                    "fecha_vencimiento": fecha_vencimiento
                }
            }
        )
    
    return {"message": "Comprobante aprobado y lavadero activado"}

# Rechazar comprobante (Super Admin)
@api_router.post("/superadmin/rechazar-comprobante/{comprobante_id}")
async def rechazar_comprobante(comprobante_id: str, rechazo_data: RechazarComprobanteRequest, request: Request):
    await get_super_admin_user(request)
    
    # Buscar comprobante
    comprobante_doc = await db.comprobantes_pago_mensualidad.find_one({"id": comprobante_id})
    if not comprobante_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comprobante no encontrado"
        )
    
    # Actualizar comprobante
    await db.comprobantes_pago_mensualidad.update_one(
        {"id": comprobante_id},
        {
            "$set": {
                "estado": EstadoPago.RECHAZADO,
                "fecha_revision": datetime.now(timezone.utc),
                "comentario_superadmin": rechazo_data.comentario
            }
        }
    )
    
    return {"message": "Comprobante rechazado"}

# ========== ENDPOINTS DE GESTIÓN DE ADMINS (SUPER ADMIN) ==========

# Ver todos los admins (Super Admin)
@api_router.get("/superadmin/admins") 
async def get_all_admins(request: Request):
    await get_super_admin_user(request)
    
    # Pipeline para obtener admins con información de sus lavaderos
    pipeline = [
        {"$match": {"rol": UserRole.ADMIN}},
        {
            "$lookup": {
                "from": "lavaderos",
                "localField": "id",
                "foreignField": "admin_id",
                "as": "lavadero"
            }
        },
        {"$sort": {"created_at": -1}}
    ]
    
    admins = await db.users.aggregate(pipeline).to_list(1000)
    
    result = []
    for admin in admins:
        lavadero_info = admin["lavadero"][0] if admin["lavadero"] else None
        result.append({
            "admin_id": admin["id"],
            "nombre": admin["nombre"],
            "email": admin["email"],
            "password_hash": admin.get("password_hash", "N/A"),
            "created_at": admin["created_at"],
            "is_active": admin["is_active"],
            "google_id": admin.get("google_id"),
            "lavadero": {
                "id": lavadero_info["id"] if lavadero_info else None,
                "nombre": lavadero_info["nombre"] if lavadero_info else "Sin lavadero",
                "estado_operativo": lavadero_info["estado_operativo"] if lavadero_info else "N/A",
                "fecha_vencimiento": lavadero_info.get("fecha_vencimiento") if lavadero_info else None
            }
        })
    
    return result

class AdminUpdateRequest(BaseModel):
    nombre: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

# Actualizar admin (Super Admin)
@api_router.put("/superadmin/admins/{admin_id}")
async def update_admin(admin_id: str, update_data: AdminUpdateRequest, request: Request):
    await get_super_admin_user(request)
    
    # Verificar que el admin existe
    admin_doc = await db.users.find_one({"id": admin_id, "rol": UserRole.ADMIN})
    if not admin_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin no encontrado"
        )
    
    # Preparar datos de actualización
    update_fields = {}
    if update_data.nombre is not None:
        update_fields["nombre"] = update_data.nombre
    if update_data.email is not None:
        # Verificar que el email no esté en uso por otro usuario
        existing_user = await db.users.find_one({"email": update_data.email, "id": {"$ne": admin_id}})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está en uso por otro usuario"
            )
        update_fields["email"] = update_data.email
    if update_data.password is not None:
        update_fields["password_hash"] = get_password_hash(update_data.password)
    if update_data.is_active is not None:
        update_fields["is_active"] = update_data.is_active
    
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay campos para actualizar"
        )
    
    # Actualizar admin
    await db.users.update_one(
        {"id": admin_id},
        {"$set": update_fields}
    )
    
    return {"message": "Admin actualizado correctamente"}

# Eliminar admin (Super Admin)
@api_router.delete("/superadmin/admins/{admin_id}")
async def delete_admin(admin_id: str, request: Request):
    await get_super_admin_user(request)
    
    # Verificar que el admin existe
    admin_doc = await db.users.find_one({"id": admin_id, "rol": UserRole.ADMIN})
    if not admin_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin no encontrado"
        )
    
    # Buscar y eliminar lavadero asociado
    lavadero_doc = await db.lavaderos.find_one({"admin_id": admin_id})
    if lavadero_doc:
        # Eliminar datos relacionados del lavadero
        await db.lavaderos.delete_one({"admin_id": admin_id})
        await db.pagos_mensualidad.delete_many({"admin_id": admin_id})
        await db.comprobantes_pago_mensualidad.delete_many({"admin_id": admin_id})
        await db.configuracion_lavadero.delete_many({"lavadero_id": lavadero_doc["id"]})
        await db.turnos.delete_many({"lavadero_id": lavadero_doc["id"]})
        await db.dias_no_laborales.delete_many({"lavadero_id": lavadero_doc["id"]})
    
    # Eliminar admin
    await db.users.delete_one({"id": admin_id})
    
    return {"message": "Admin y todos sus datos asociados eliminados correctamente"}

# Ver contraseña de admin (Super Admin)
@api_router.get("/superadmin/admins/{admin_id}/password")
async def get_admin_password_info(admin_id: str, request: Request):
    await get_super_admin_user(request)
    
    admin_doc = await db.users.find_one({"id": admin_id, "rol": UserRole.ADMIN})
    if not admin_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin no encontrado"
        )
    
    return {
        "admin_id": admin_id,
        "email": admin_doc["email"],
        "nombre": admin_doc["nombre"],
        "has_password": admin_doc.get("password_hash") is not None,
        "is_google_user": admin_doc.get("google_id") is not None,
        # Por seguridad, no devolvemos el hash completo, solo información
        "password_info": "Contraseña establecida" if admin_doc.get("password_hash") else "Sin contraseña"
    }

# Crear admin desde Super Admin (para testing)
@api_router.post("/superadmin/crear-admin")
async def crear_admin_superadmin(admin_data: AdminLavaderoRegister, request: Request):
    await get_super_admin_user(request)
    
    # Check if user already exists
    existing_user = await get_user_by_email(admin_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    
    # Check if lavadero name already exists (case-insensitive)
    existing_lavadero = await db.lavaderos.find_one({
        "nombre": {"$regex": f"^{admin_data.lavadero.nombre}$", "$options": "i"}
    })
    if existing_lavadero:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un lavadero con ese nombre"
        )
    
    # Create admin user
    password_hash = get_password_hash(admin_data.password)
    new_admin = User(
        email=admin_data.email,
        nombre=admin_data.nombre,
        rol=UserRole.ADMIN,
        password_hash=password_hash
    )
    
    # Insert admin to database
    admin_dict = new_admin.dict()
    await db.users.insert_one(admin_dict)
    
    # Guardar credencial en tabla temporal para testing
    await db.temp_credentials.insert_one({
        "admin_email": admin_data.email,
        "password": admin_data.password,
        "created_at": datetime.now(timezone.utc)
    })
    
    # Create lavadero
    new_lavadero = Lavadero(
        nombre=admin_data.lavadero.nombre,
        direccion=admin_data.lavadero.direccion,
        descripcion=admin_data.lavadero.descripcion,
        admin_id=new_admin.id,
        estado_operativo=EstadoAdmin.PENDIENTE_APROBACION
    )
    
    # Insert lavadero to database
    lavadero_dict = new_lavadero.dict()
    await db.lavaderos.insert_one(lavadero_dict)
    
    return {
        "message": "Admin y lavadero creados exitosamente por Super Admin",
        "admin_id": new_admin.id,
        "lavadero_id": new_lavadero.id,
        "estado": "PENDIENTE_APROBACION - Usar 'Activar Lavadero' para activar sin pago"
    }

# Toggle estado de lavadero (Activar/Desactivar) - Super Admin para testing
@api_router.post("/superadmin/toggle-lavadero/{admin_id}")
async def toggle_lavadero_estado(admin_id: str, request: Request):
    await get_super_admin_user(request)
    
    # Buscar admin
    admin_doc = await db.users.find_one({"id": admin_id, "rol": UserRole.ADMIN})
    if not admin_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin no encontrado"
        )
    
    # Buscar lavadero del admin
    lavadero_doc = await db.lavaderos.find_one({"admin_id": admin_id})
    if not lavadero_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lavadero no encontrado para este admin"
        )
    
    # Determinar nuevo estado
    estado_actual = lavadero_doc.get("estado_operativo", EstadoAdmin.PENDIENTE_APROBACION)
    
    if estado_actual == EstadoAdmin.ACTIVO:
        # Desactivar: cambiar a PENDIENTE_APROBACION
        nuevo_estado = EstadoAdmin.PENDIENTE_APROBACION
        update_data = {
            "$set": {
                "estado_operativo": nuevo_estado
            },
            "$unset": {
                "fecha_vencimiento": ""
            }
        }
        message = "Lavadero desactivado - cambiado a estado pendiente"
        
    else:
        # Activar: cambiar a ACTIVO
        nuevo_estado = EstadoAdmin.ACTIVO
        fecha_vencimiento = datetime.now(timezone.utc) + timedelta(days=30)
        update_data = {
            "$set": {
                "estado_operativo": nuevo_estado,
                "fecha_vencimiento": fecha_vencimiento
            }
        }
        message = "Lavadero activado exitosamente (sin proceso de pago)"
        
        # Crear pago mensualidad como confirmado (simulado) solo al activar
        config_super = await db.configuracion_superadmin.find_one({})
        if config_super:
            # Verificar si ya existe un pago para este mes
            mes_actual = datetime.now().strftime("%Y-%m")
            pago_existente = await db.pagos_mensualidad.find_one({
                "admin_id": admin_id,
                "mes_año": mes_actual
            })
            
            if not pago_existente:
                pago_mensualidad = PagoMensualidad(
                    admin_id=admin_id,
                    lavadero_id=lavadero_doc["id"],
                    monto=config_super.get("precio_mensualidad", 10000.0),
                    mes_año=mes_actual,
                    estado=EstadoPago.CONFIRMADO,
                    fecha_vencimiento=fecha_vencimiento
                )
                await db.pagos_mensualidad.insert_one(pago_mensualidad.dict())
    
    # Actualizar lavadero
    await db.lavaderos.update_one({"admin_id": admin_id}, update_data)
    
    response_data = {
        "message": message,
        "estado_anterior": estado_actual,
        "estado_nuevo": nuevo_estado
    }
    
    if nuevo_estado == EstadoAdmin.ACTIVO:
        response_data["vence"] = fecha_vencimiento.isoformat()
    
    return response_data

# Obtener credenciales para testing (Super Admin)
@api_router.get("/superadmin/credenciales-testing")
async def get_credenciales_testing(request: Request):
    await get_super_admin_user(request)
    
    # Esta es una función especial solo para development/testing
    # En producción debería ser removida por seguridad
    
    # Obtener todos los admins
    admins_cursor = db.users.find({"rol": UserRole.ADMIN})
    admins = await admins_cursor.to_list(1000)
    
    # Lista ampliada de contraseñas comunes para testing
    common_passwords = [
        "admin123", "carlos123", "emp123", "test123", 
        "123456", "password", "admin", "test", 
        "lavadero123", "password123", "admin2023", "demo123",
        "kearcangel123", "superadmin", "1234567890", "qwerty",
        "maria123", "juan123", "ana123", "jose123",
        "K@#l1331",  # Super admin password
        "pass", "pass123", "admin2024", "user123"
    ]
    
    result = []
    for admin in admins:
        # Para cada admin, probar las contraseñas comunes
        plain_password = "contraseña_no_encontrada"
        
        if admin.get("password_hash"):
            for pwd in common_passwords:
                try:
                    if verify_password(pwd, admin["password_hash"]):
                        plain_password = pwd
                        break
                except Exception as e:
                    # Si hay error en la verificación, continuar con la siguiente
                    continue
        
        # También verificar si hay una entrada en la tabla temporal de credenciales
        temp_cred = await db.temp_credentials.find_one({"admin_email": admin["email"]})
        if temp_cred:
            plain_password = temp_cred["password"]
        
        result.append({
            "email": admin["email"],
            "nombre": admin["nombre"],
            "password": plain_password
        })
    
    return result

# Health check
@api_router.get("/health")
async def health_check():
    return {"status": "ok", "message": "Sistema de gestión de lavaderos funcionando"}

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()