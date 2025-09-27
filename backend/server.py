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
    pago_mensualidad_id: str
    imagen_url: str

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
            if lavadero.fecha_vencimiento and lavadero.fecha_vencimiento < datetime.now(timezone.utc):
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
    if current_user.rol == UserRole.ADMIN:
        # Admin sees all stats
        total_users = await db.users.count_documents({})
        total_employees = await db.users.count_documents({"rol": UserRole.EMPLEADO})
        
        return DashboardStats(
            total_users=total_users,
            total_employees=total_employees,
            active_projects=15,  # Simulated data
            pending_tasks=42     # Simulated data
        )
    else:
        # Employee sees limited stats
        return UserStats(
            my_tasks=8,
            completed_tasks=12,
            pending_tasks=5
        )

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
                rol=UserRole.EMPLEADO  # Default role for Google users
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

# Health check
@api_router.get("/health")
async def health_check():
    return {"status": "ok", "message": "Sistema de autenticación funcionando"}

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