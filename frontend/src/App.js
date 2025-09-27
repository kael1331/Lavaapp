import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Link, useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Configure axios to include cookies
axios.defaults.withCredentials = true;

// Create Auth Context
const AuthContext = createContext();

// Auth Provider Component
const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for session_id in URL fragment (Google OAuth callback)
    const fragment = window.location.hash;
    if (fragment.includes('session_id=')) {
      const sessionId = fragment.split('session_id=')[1].split('&')[0];
      processGoogleSession(sessionId);
      return;
    }

    // Check existing session or JWT token
    checkExistingSession();
  }, []);

  const processGoogleSession = async (sessionId) => {
    try {
      setLoading(true);
      
      // Get session data from backend
      const response = await axios.get(`${API}/session-data`, {
        headers: { 'X-Session-ID': sessionId }
      });
      
      const sessionData = response.data;
      
      // Set session cookie
      await axios.post(`${API}/set-session-cookie`, {
        session_token: sessionData.session_token
      });
      
      // Clear URL fragment
      window.history.replaceState(null, null, window.location.pathname);
      
      // Wait a moment for cookie to be set properly
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Get user info directly from the session data and backend
      const userResponse = await axios.get(`${API}/check-session`);
      console.log('Check session after Google OAuth:', userResponse.data);
      
      if (userResponse.data.authenticated) {
        setUser(userResponse.data.user);
        console.log('Google login successful:', userResponse.data.user);
      } else {
        console.error('Failed to authenticate after Google login');
        alert('Error: No se pudo completar el login con Google. Por favor intenta de nuevo.');
      }
      
    } catch (error) {
      console.error('Error processing Google session:', error);
      alert('Error al procesar el login con Google. Por favor intenta de nuevo.');
      setLoading(false);
    } finally {
      setLoading(false);
    }
  };

  const checkExistingSession = async () => {
    try {
      const response = await axios.get(`${API}/check-session`);
      
      if (response.data.authenticated) {
        setUser(response.data.user);
      } else {
        // Fallback to JWT token
        const token = localStorage.getItem('token');
        if (token) {
          axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
          await fetchCurrentUser();
        }
      }
    } catch (error) {
      // Try JWT fallback
      const token = localStorage.getItem('token');
      if (token) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        await fetchCurrentUser();
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchCurrentUser = async () => {
    try {
      const response = await axios.get(`${API}/me`);
      setUser(response.data);
    } catch (error) {
      console.error('Error fetching user:', error);
      logout();
    }
  };

  const login = async (email, password) => {
    try {
      const response = await axios.post(`${API}/login`, { email, password });
      
      const { access_token, user: userData } = response.data;
      
      localStorage.setItem('token', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      setUser(userData);
      
      return { success: true };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Error al iniciar sesión' 
      };
    }
  };

  const register = async (userData) => {
    try {
      await axios.post(`${API}/register`, userData);
      return { success: true };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Error al registrarse' 
      };
    }
  };

  const loginWithGoogle = () => {
    const redirectUrl = encodeURIComponent(`${window.location.origin}/dashboard`);
    // Original URL - unfortunately can't auto-click due to cross-origin restrictions
    window.location.href = `https://auth.emergentagent.com/?redirect=${redirectUrl}`;
  };

  const logout = async () => {
    try {
      // Call logout endpoint to clear session
      await axios.post(`${API}/logout`);
    } catch (error) {
      console.error('Error during logout:', error);
    }
    
    // Clear local storage and axios headers
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loginWithGoogle, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

// Custom hook to use auth context
const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Protected Route Component
const ProtectedRoute = ({ children, requiredRole = null }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Cargando...</div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (requiredRole && user.rol !== requiredRole) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-600">Acceso Denegado</h1>
          <p className="mt-2">No tienes permisos para acceder a esta página</p>
          <Link to="/dashboard" className="mt-4 inline-block bg-blue-500 text-white px-4 py-2 rounded">
            Volver al Dashboard
          </Link>
        </div>
      </div>
    );
  }

  return children;
};

// Navigation Component
const Navigation = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = window.location;

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  // No mostrar navegación en página principal, login de lavaderos, o login de admins
  if (!user || location.pathname === '/' || location.pathname.includes('/lavadero/') || location.pathname === '/admin-login') {
    return null;
  }

  return (
    <nav className="bg-gray-800 text-white p-4">
      <div className="container mx-auto flex justify-between items-center">
        <div className="flex space-x-4">
          <Link to="/dashboard" className="hover:text-gray-300">Dashboard</Link>
          <Link to="/perfil" className="hover:text-gray-300">Mi Perfil</Link>
          
          {user.rol === 'SUPER_ADMIN' && (
            <>
              <Link to="/superadmin/lavaderos" className="hover:text-gray-300">Gestión de Lavaderos</Link>
              <Link to="/superadmin/comprobantes" className="hover:text-gray-300">Revisar Comprobantes</Link>
            </>
          )}
          
          {user.rol === 'ADMIN' && (
            <>
              <Link to="/admin/comprobante-pago" className="hover:text-gray-300">Subir Comprobante</Link>
              <Link to="/admin/configuracion" className="hover:text-gray-300">Configuración</Link>
              <Link to="/admin/turnos" className="hover:text-gray-300">Gestión de Turnos</Link>
            </>
          )}
          
          {user.rol === 'CLIENTE' && (
            <>
              <Link to="/cliente/turnos" className="hover:text-gray-300">Mis Turnos</Link>
              <Link to="/cliente/reservar" className="hover:text-gray-300">Reservar Turno</Link>
            </>
          )}
        </div>
        
        <div className="flex items-center space-x-4">
          {user.picture && (
            <img 
              src={user.picture} 
              alt="Foto de perfil" 
              className="w-8 h-8 rounded-full"
            />
          )}
          <span className="text-sm">
            {user.nombre} ({user.rol})
            {user.google_id && (
              <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                Google
              </span>
            )}
          </span>
          <button 
            onClick={handleLogout}
            className="bg-red-500 hover:bg-red-600 px-3 py-1 rounded text-sm"
          >
            Cerrar Sesión
          </button>
        </div>
      </div>
    </nav>
  );
};

// Login Component
const Login = () => {
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { user, login, loginWithGoogle } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Si ya está logueado, redirigir al dashboard
    if (user) {
      navigate('/dashboard');
    }
  }, [user, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await login(formData.email, formData.password);
    
    if (result.success) {
      navigate('/dashboard');
    } else {
      setError(result.error);
    }
    
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Iniciar Sesión
          </h2>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}
          
          <div>
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <input
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700">Contraseña</label>
            <input
              type="password"
              required
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {loading ? 'Iniciando sesión...' : 'Iniciar Sesión'}
          </button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-gray-50 text-gray-500">O continúa con</span>
            </div>
          </div>

          <button
            type="button"
            onClick={loginWithGoogle}
            className="group relative w-full flex justify-center py-2 px-4 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continuar con Google
          </button>
          
          <div className="text-center">
            <Link to="/register" className="text-blue-600 hover:text-blue-500">
              ¿No tienes cuenta? Regístrate
            </Link>
          </div>
        </form>

        <div className="mt-8 p-4 bg-blue-50 rounded-lg">
          <h3 className="font-semibold text-blue-800">Cuentas de Prueba:</h3>
          <div className="mt-2 text-sm text-blue-700">
            <p><strong>Admin:</strong> admin@demo.com / admin123</p>
            <p><strong>Empleado:</strong> empleado@demo.com / emp123</p>
          </div>
        </div>
      </div>
    </div>
  );
};

// Register Component
const Register = () => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    nombre: '',
    rol: 'CLIENTE'
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const { user, register } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Si ya está logueado, redirigir al dashboard
    if (user) {
      navigate('/dashboard');
    }
  }, [user, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await register(formData);
    
    if (result.success) {
      setSuccess(true);
      setFormData({ email: '', password: '', nombre: '', rol: 'EMPLEADO' });
    } else {
      setError(result.error);
    }
    
    setLoading(false);
  };

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full text-center">
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
            ¡Registro exitoso! Puedes iniciar sesión ahora.
          </div>
          <Link to="/login" className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
            Ir al Login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Registrarse
          </h2>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}
          
          <div>
            <label className="block text-sm font-medium text-gray-700">Nombre</label>
            <input
              type="text"
              required
              value={formData.nombre}
              onChange={(e) => setFormData({...formData, nombre: e.target.value})}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <input
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700">Contraseña</label>
            <input
              type="password"
              required
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700">Rol</label>
            <select
              value={formData.rol}
              onChange={(e) => setFormData({...formData, rol: e.target.value})}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="EMPLEADO">Empleado</option>
              <option value="ADMIN">Administrador</option>
            </select>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
          >
            {loading ? 'Registrando...' : 'Registrarse'}
          </button>
          
          <div className="text-center">
            <Link to="/login" className="text-blue-600 hover:text-blue-500">
              ¿Ya tienes cuenta? Inicia sesión
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
};

// Dashboard Component
const Dashboard = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/dashboard/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-8">Cargando estadísticas...</div>;
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          ¡Bienvenido, {user.nombre}!
        </h1>
        <p className="text-gray-600 mt-2">
          Rol: <span className="font-semibold">{user.rol}</span>
        </p>
      </div>

      {user.rol === 'SUPER_ADMIN' ? (
        // Dashboard Super Admin
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="bg-blue-50 p-6 rounded-lg">
            <h3 className="text-lg font-semibold text-blue-800">Total Lavaderos</h3>
            <p className="text-3xl font-bold text-blue-600">{stats?.total_lavaderos || 0}</p>
          </div>
          
          <div className="bg-green-50 p-6 rounded-lg">
            <h3 className="text-lg font-semibold text-green-800">Lavaderos Activos</h3>
            <p className="text-3xl font-bold text-green-600">{stats?.lavaderos_activos || 0}</p>
          </div>
          
          <div className="bg-yellow-50 p-6 rounded-lg">
            <h3 className="text-lg font-semibold text-yellow-800">Pendientes Aprobación</h3>
            <p className="text-3xl font-bold text-yellow-600">{stats?.lavaderos_pendientes || 0}</p>
          </div>
          
          <div className="bg-red-50 p-6 rounded-lg">
            <h3 className="text-lg font-semibold text-red-800">Comprobantes Pendientes</h3>
            <p className="text-3xl font-bold text-red-600">{stats?.comprobantes_pendientes || 0}</p>
          </div>
        </div>
      ) : user.rol === 'ADMIN' ? (
        // Dashboard Admin de Lavadero
        <div>
          <div className="bg-white p-4 rounded-lg shadow mb-6">
            <h3 className="text-lg font-semibold text-gray-800">Estado del Lavadero</h3>
            <div className="mt-2">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                stats?.estado_operativo === 'ACTIVO' 
                  ? 'bg-green-100 text-green-800' 
                  : stats?.estado_operativo === 'PENDIENTE_APROBACION'
                  ? 'bg-yellow-100 text-yellow-800'
                  : 'bg-red-100 text-red-800'
              }`}>
                {stats?.estado_operativo}
              </span>
              {stats?.dias_restantes !== undefined && (
                <span className="ml-4 text-sm text-gray-600">
                  Días restantes: {stats.dias_restantes}
                </span>
              )}
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-blue-50 p-6 rounded-lg">
              <h3 className="text-lg font-semibold text-blue-800">Total Turnos</h3>
              <p className="text-3xl font-bold text-blue-600">{stats?.total_turnos || 0}</p>
            </div>
            
            <div className="bg-green-50 p-6 rounded-lg">
              <h3 className="text-lg font-semibold text-green-800">Confirmados</h3>
              <p className="text-3xl font-bold text-green-600">{stats?.turnos_confirmados || 0}</p>
            </div>
            
            <div className="bg-yellow-50 p-6 rounded-lg">
              <h3 className="text-lg font-semibold text-yellow-800">Pendientes</h3>
              <p className="text-3xl font-bold text-yellow-600">{stats?.turnos_pendientes || 0}</p>
            </div>
            
            <div className="bg-red-50 p-6 rounded-lg">
              <h3 className="text-lg font-semibold text-red-800">Comprobantes</h3>
              <p className="text-3xl font-bold text-red-600">{stats?.comprobantes_pendientes || 0}</p>
            </div>
          </div>
        </div>
      ) : (
        // Dashboard Cliente
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-blue-50 p-6 rounded-lg">
            <h3 className="text-lg font-semibold text-blue-800">Mis Turnos</h3>
            <p className="text-3xl font-bold text-blue-600">{stats?.mis_turnos || 0}</p>
          </div>
          
          <div className="bg-green-50 p-6 rounded-lg">
            <h3 className="text-lg font-semibold text-green-800">Confirmados</h3>
            <p className="text-3xl font-bold text-green-600">{stats?.confirmados || 0}</p>
          </div>
          
          <div className="bg-yellow-50 p-6 rounded-lg">
            <h3 className="text-lg font-semibold text-yellow-800">Pendientes</h3>
            <p className="text-3xl font-bold text-yellow-600">{stats?.pendientes || 0}</p>
          </div>
        </div>
      )}

      <div className="mt-8 bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4">Acciones Disponibles</h2>
        <div className="space-y-2">
          {user.rol === 'SUPER_ADMIN' ? (
            <>
              <p className="text-green-600">✅ Gestionar todos los lavaderos y administradores</p>
              <p className="text-green-600">✅ Aprobar o rechazar comprobantes de pago</p>
              <p className="text-green-600">✅ Activar/Bloquear lavaderos según pagos</p>
              <p className="text-green-600">✅ Ver estadísticas globales del sistema</p>
              <p className="text-green-600">✅ Control total de operaciones y mensualidades</p>
            </>
          ) : user.rol === 'ADMIN' ? (
            <>
              <p className="text-blue-600">✅ Configurar horarios y precios de mi lavadero</p>
              <p className="text-blue-600">✅ Gestionar turnos y comprobantes de clientes</p>
              <p className="text-blue-600">✅ Ver estadísticas de mi lavadero</p>
              <p className="text-blue-600">✅ Renovar mensualidad cuando sea necesario</p>
              {stats?.estado_operativo === 'PENDIENTE_APROBACION' && (
                <p className="text-red-600">❌ Pendiente de aprobación - debe subir comprobante de pago</p>
              )}
              {stats?.estado_operativo === 'VENCIDO' && (
                <p className="text-red-600">❌ Suscripción vencida - debe renovar mensualidad</p>
              )}
            </>
          ) : (
            <>
              <p className="text-blue-600">✅ Reservar turnos en lavaderos disponibles</p>
              <p className="text-blue-600">✅ Ver mis turnos confirmados y pendientes</p>
              <p className="text-blue-600">✅ Cancelar turnos con anticipación</p>
              <p className="text-blue-600">✅ Subir comprobantes de pago</p>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

// User Profile Component
const UserProfile = () => {
  const { user } = useAuth();

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Mi Perfil</h1>
      
      <div className="bg-white shadow overflow-hidden sm:rounded-lg">
        <div className="px-4 py-5 sm:px-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900">
            Información Personal
          </h3>
          <p className="mt-1 max-w-2xl text-sm text-gray-500">
            Detalles de tu cuenta y rol en el sistema.
          </p>
        </div>
        <div className="border-t border-gray-200">
          <dl>
            <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt className="text-sm font-medium text-gray-500">Nombre completo</dt>
              <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">{user.nombre}</dd>
            </div>
            <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt className="text-sm font-medium text-gray-500">Email</dt>
              <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">{user.email}</dd>
            </div>
            <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt className="text-sm font-medium text-gray-500">Rol</dt>
              <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                  user.rol === 'ADMIN' 
                    ? 'bg-red-100 text-red-800' 
                    : 'bg-blue-100 text-blue-800'
                }`}>
                  {user.rol}
                </span>
              </dd>
            </div>
            <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt className="text-sm font-medium text-gray-500">Estado</dt>
              <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                  Activo
                </span>
              </dd>
            </div>
            {user.picture && (
              <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Foto de perfil</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                  <img src={user.picture} alt="Foto de perfil" className="w-16 h-16 rounded-full" />
                </dd>
              </div>
            )}
            <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt className="text-sm font-medium text-gray-500">Tipo de cuenta</dt>
              <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {user.google_id ? (
                  <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                    Cuenta de Google
                  </span>
                ) : (
                  <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800">
                    Cuenta Local
                  </span>
                )}
              </dd>
            </div>
            <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt className="text-sm font-medium text-gray-500">Fecha de registro</dt>
              <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {new Date(user.created_at).toLocaleDateString()}
              </dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  );
};

// User Management Component (Admin only)
const UserManagement = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await axios.get(`${API}/admin/users`);
      setUsers(response.data);
    } catch (error) {
      console.error('Error fetching users:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleUserStatus = async (userId) => {
    try {
      await axios.put(`${API}/admin/users/${userId}/toggle-status`);
      fetchUsers(); // Refresh the list
    } catch (error) {
      console.error('Error toggling user status:', error);
    }
  };

  const deleteUser = async (userId) => {
    if (window.confirm('¿Estás seguro de que quieres eliminar este usuario?')) {
      try {
        await axios.delete(`${API}/admin/users/${userId}`);
        fetchUsers(); // Refresh the list
      } catch (error) {
        console.error('Error deleting user:', error);
      }
    }
  };

  if (loading) {
    return <div className="p-8">Cargando usuarios...</div>;
  }

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Gestión de Usuarios</h1>
      
      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <ul className="divide-y divide-gray-200">
          {users.map((user) => (
            <li key={user.id}>
              <div className="px-4 py-4 flex items-center justify-between">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="h-10 w-10 rounded-full bg-gray-300 flex items-center justify-center">
                      <span className="text-sm font-medium text-gray-700">
                        {user.nombre.charAt(0).toUpperCase()}
                      </span>
                    </div>
                  </div>
                  <div className="ml-4">
                    <div className="text-sm font-medium text-gray-900">{user.nombre}</div>
                    <div className="text-sm text-gray-500">{user.email}</div>
                  </div>
                  <div className="ml-4">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      user.rol === 'ADMIN' 
                        ? 'bg-red-100 text-red-800' 
                        : 'bg-blue-100 text-blue-800'
                    }`}>
                      {user.rol}
                    </span>
                  </div>
                  <div className="ml-4">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      user.is_active 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {user.is_active ? 'Activo' : 'Inactivo'}
                    </span>
                  </div>
                </div>
                
                <div className="flex space-x-2">
                  <button
                    onClick={() => toggleUserStatus(user.id)}
                    className={`px-3 py-1 rounded text-sm ${
                      user.is_active
                        ? 'bg-yellow-500 text-white hover:bg-yellow-600'
                        : 'bg-green-500 text-white hover:bg-green-600'
                    }`}
                  >
                    {user.is_active ? 'Desactivar' : 'Activar'}
                  </button>
                  
                  <button
                    onClick={() => deleteUser(user.id)}
                    className="px-3 py-1 bg-red-500 text-white rounded text-sm hover:bg-red-600"
                  >
                    Eliminar
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

// Admin Panel Component
const AdminPanel = () => {
  const [adminData, setAdminData] = useState(null);

  useEffect(() => {
    fetchAdminData();
  }, []);

  const fetchAdminData = async () => {
    try {
      const response = await axios.get(`${API}/admin-only`);
      setAdminData(response.data);
    } catch (error) {
      console.error('Error fetching admin data:', error);
    }
  };

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Panel de Administración</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Información Secreta</h2>
          {adminData ? (
            <div>
              <p className="text-gray-600 mb-2">{adminData.message}</p>
              <div className="bg-red-50 p-4 rounded">
                <p className="text-red-800 font-medium">Dato Confidencial:</p>
                <p className="text-red-600">{adminData.secret}</p>
              </div>
            </div>
          ) : (
            <p>Cargando información...</p>
          )}
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Configuraciones del Sistema</h2>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span>Registros automáticos</span>
              <input type="checkbox" className="rounded" defaultChecked />
            </div>
            <div className="flex justify-between items-center">
              <span>Notificaciones por email</span>
              <input type="checkbox" className="rounded" defaultChecked />
            </div>
            <div className="flex justify-between items-center">
              <span>Modo mantenimiento</span>
              <input type="checkbox" className="rounded" />
            </div>
            <button className="w-full bg-blue-500 text-white py-2 rounded hover:bg-blue-600">
              Guardar Configuración
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Página de Inicio (Dual)
const HomePage = () => {
  const [lavaderos, setLavaderos] = useState([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Si ya está logueado, redirigir al dashboard
    if (user) {
      navigate('/dashboard');
      return;
    }
    fetchLavaderos();
  }, [user, navigate]);

  const fetchLavaderos = async () => {
    try {
      const response = await axios.get(`${API}/lavaderos-operativos`);
      setLavaderos(response.data);
    } catch (error) {
      console.error('Error fetching lavaderos:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <div className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <h1 className="text-3xl font-bold text-gray-900">🚿 LavApp</h1>
              <span className="ml-3 text-sm text-gray-500">Sistema de Gestión de Lavaderos</span>
            </div>
            
            {/* Sección mínima para administradores */}
            <div className="flex items-center space-x-4">
              <Link 
                to="/admin-login" 
                className="text-sm bg-gray-800 hover:bg-gray-900 text-white px-4 py-2 rounded-md transition-colors"
              >
                👨‍💼 Administradores
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Contenido Principal */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Sección Principal - Selección de Lavaderos */}
        <div className="text-center mb-12">
          <h2 className="text-4xl font-extrabold text-gray-900 mb-4">
            Reserva tu turno en el lavadero
          </h2>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Selecciona tu lavadero preferido y agenda tu turno de forma rápida y segura
          </p>
        </div>

        {/* Lista de Lavaderos */}
        {loading ? (
          <div className="text-center py-12">
            <div className="text-xl text-gray-600">Cargando lavaderos disponibles...</div>
          </div>
        ) : lavaderos.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-xl text-gray-600 mb-4">
              😔 No hay lavaderos operativos en este momento
            </div>
            <p className="text-gray-500">
              Por favor intenta más tarde o contacta al administrador
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {lavaderos.map((lavadero) => (
              <div key={lavadero.id} className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow overflow-hidden">
                <div className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-xl font-semibold text-gray-900">{lavadero.nombre}</h3>
                    <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-semibold rounded-full">
                      Operativo
                    </span>
                  </div>
                  
                  <p className="text-gray-600 mb-2">
                    📍 {lavadero.direccion}
                  </p>
                  
                  {lavadero.descripcion && (
                    <p className="text-sm text-gray-500 mb-4">
                      {lavadero.descripcion}
                    </p>
                  )}
                  
                  <Link
                    to={`/lavadero/${lavadero.id}/login`}
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors text-center block"
                  >
                    Seleccionar Lavadero
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Información adicional */}
        <div className="mt-16 bg-white rounded-lg shadow-sm p-8">
          <div className="text-center mb-8">
            <h3 className="text-2xl font-bold text-gray-900 mb-4">¿Cómo funciona?</h3>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">🏪</span>
              </div>
              <h4 className="text-lg font-semibold text-gray-900 mb-2">1. Selecciona tu lavadero</h4>
              <p className="text-gray-600">Elige el lavadero más conveniente para ti</p>
            </div>
            
            <div className="text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">📅</span>
              </div>
              <h4 className="text-lg font-semibold text-gray-900 mb-2">2. Agenda tu turno</h4>
              <p className="text-gray-600">Selecciona el día y horario que prefieras</p>
            </div>
            
            <div className="text-center">
              <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">💳</span>
              </div>
              <h4 className="text-lg font-semibold text-gray-900 mb-2">3. Paga y confirma</h4>
              <p className="text-gray-600">Realiza el pago y sube tu comprobante</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Login específico por lavadero
const LavaderoLogin = () => {
  const { lavaderoId } = useParams();
  const [lavadero, setLavadero] = useState(null);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Si ya está logueado, redirigir al dashboard
    if (user) {
      navigate('/dashboard');
      return;
    }

    // Por ahora simulamos obtener datos del lavadero
    // En el futuro implementaremos el endpoint específico
    setLavadero({
      id: lavaderoId,
      nombre: "Lavadero Demo",
      direccion: "Dirección Demo"
    });
    setLoading(false);
  }, [lavaderoId, user, navigate]);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Cargando...</div>;
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <Link to="/" className="text-blue-600 hover:text-blue-500 text-sm">
            ← Volver a selección de lavaderos
          </Link>
          <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
            {lavadero?.nombre}
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Inicia sesión o regístrate como cliente
          </p>
        </div>

        {/* Aquí irá el formulario de login específico del lavadero */}
        <div className="bg-blue-50 p-4 rounded-md">
          <p className="text-sm text-blue-800">
            🚧 Funcionalidad en desarrollo: Login específico por lavadero
          </p>
        </div>
      </div>
    </div>
  );
};

// Componente de Registro de Admin con Lavadero
const RegisterAdminForm = ({ onSuccess }) => {
  const [formData, setFormData] = useState({
    // Datos del admin
    email: '',
    password: '',
    nombre: '',
    // Datos del lavadero
    lavadero_nombre: '',
    lavadero_direccion: '',
    lavadero_descripcion: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [registrationResult, setRegistrationResult] = useState(null);
  const [superAdminConfig, setSuperAdminConfig] = useState(null);

  useEffect(() => {
    fetchSuperAdminConfig();
  }, []);

  const fetchSuperAdminConfig = async () => {
    try {
      const response = await axios.get(`${API}/superadmin-config`);
      setSuperAdminConfig(response.data);
    } catch (error) {
      console.error('Error fetching super admin config:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const requestData = {
        email: formData.email,
        password: formData.password,
        nombre: formData.nombre,
        lavadero: {
          nombre: formData.lavadero_nombre,
          direccion: formData.lavadero_direccion,
          descripcion: formData.lavadero_descripcion
        }
      };

      const response = await axios.post(`${API}/register-admin`, requestData);
      
      setRegistrationResult(response.data);
    } catch (error) {
      console.error('Error en registro:', error);
      setError(error.response?.data?.detail || 'Error al registrar admin y lavadero');
    } finally {
      setLoading(false);
    }
  };

  const handleBackToLogin = () => {
    setRegistrationResult(null);
    onSuccess();
  };

  if (registrationResult) {
    return (
      <div className="mt-8 space-y-6">
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
          <h3 className="font-semibold">¡Registro Exitoso!</h3>
          <p className="mt-2">{registrationResult.message}</p>
        </div>

        <div className="bg-blue-50 p-6 rounded-lg">
          <h3 className="text-lg font-semibold text-blue-800 mb-4">Información de Pago</h3>
          <div className="space-y-2 text-sm">
            <p><strong>Alias Bancario:</strong> {registrationResult.alias_bancario}</p>
            <p><strong>Monto a Pagar:</strong> ${registrationResult.monto_a_pagar}</p>
            <p><strong>Estado:</strong> {registrationResult.estado}</p>
          </div>
        </div>

        <div className="bg-yellow-50 p-4 rounded-md">
          <h4 className="font-semibold text-yellow-800">Próximos Pasos:</h4>
          <ol className="mt-2 text-sm text-yellow-700 list-decimal list-inside space-y-1">
            <li>Realiza la transferencia al alias bancario indicado</li>
            <li>Sube el comprobante de transferencia (próximamente)</li>
            <li>Espera la aprobación del Super Admin</li>
            <li>Una vez aprobado, podrás operar tu lavadero por 30 días</li>
          </ol>
        </div>

        <div className="bg-red-50 p-4 rounded-md">
          <p className="text-sm text-red-800">
            <strong>Importante:</strong> Guarda esta información. Puedes hacer login con tu email y contraseña, 
            pero tu lavadero estará en estado "PENDIENTE_APROBACION" hasta que subas el comprobante y sea aprobado.
          </p>
        </div>

        <button
          onClick={handleBackToLogin}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors"
        >
          Continuar al Login
        </button>
      </div>
    );
  }

  return (
    <div className="mt-8 space-y-6">
      <div className="text-center">
        <h3 className="text-xl font-semibold text-gray-900">Registrar Nuevo Lavadero</h3>
        <p className="mt-2 text-sm text-gray-600">
          Completa la información para registrar tu lavadero en la plataforma
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}

        {/* Información del Administrador */}
        <div className="bg-gray-50 p-4 rounded-lg">
          <h4 className="font-semibold text-gray-800 mb-3">Información del Administrador</h4>
          
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700">Nombre Completo *</label>
              <input
                type="text"
                required
                value={formData.nombre}
                onChange={(e) => setFormData({...formData, nombre: e.target.value})}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="Juan Pérez"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Email *</label>
              <input
                type="email"
                required
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="admin@milavadero.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Contraseña *</label>
              <input
                type="password"
                required
                value={formData.password}
                onChange={(e) => setFormData({...formData, password: e.target.value})}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="Mínimo 6 caracteres"
              />
            </div>
          </div>
        </div>

        {/* Información del Lavadero */}
        <div className="bg-blue-50 p-4 rounded-lg">
          <h4 className="font-semibold text-blue-800 mb-3">Información del Lavadero</h4>
          
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700">Nombre del Lavadero *</label>
              <input
                type="text"
                required
                value={formData.lavadero_nombre}
                onChange={(e) => setFormData({...formData, lavadero_nombre: e.target.value})}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="Lavadero Norte"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Dirección *</label>
              <input
                type="text"
                required
                value={formData.lavadero_direccion}
                onChange={(e) => setFormData({...formData, lavadero_direccion: e.target.value})}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="Av. Principal 123, Ciudad"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Descripción (Opcional)</label>
              <textarea
                value={formData.lavadero_descripcion}
                onChange={(e) => setFormData({...formData, lavadero_descripcion: e.target.value})}
                rows={3}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="Lavadero moderno con equipos de última generación..."
              />
            </div>
          </div>
        </div>

        {/* Información de Pago */}
        {superAdminConfig && (
          <div className="bg-yellow-50 p-4 rounded-lg">
            <h4 className="font-semibold text-yellow-800 mb-3">Información de Mensualidad</h4>
            <div className="space-y-2 text-sm text-yellow-700">
              <p><strong>Costo mensual:</strong> ${superAdminConfig.precio_mensualidad}</p>
              <p><strong>Alias para transferencia:</strong> {superAdminConfig.alias_bancario}</p>
              <p>Después del registro deberás transferir este monto y subir el comprobante para activar tu lavadero.</p>
            </div>
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-md transition-colors disabled:opacity-50"
        >
          {loading ? 'Registrando...' : 'Registrar Lavadero'}
        </button>

        <button
          type="button"
          onClick={onSuccess}
          className="w-full text-center text-gray-600 hover:text-gray-500"
        >
          ← Volver al login
        </button>
      </form>
    </div>
  );
};

// Login para Administradores
const AdminLogin = () => {
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showRegister, setShowRegister] = useState(false);
  const { user, login, loginWithGoogle } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Si ya está logueado, redirigir al dashboard
    if (user) {
      navigate('/dashboard');
    }
  }, [user, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await login(formData.email, formData.password);
    
    if (result.success) {
      navigate('/dashboard');
    } else {
      setError(result.error);
    }
    
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <Link to="/" className="text-blue-600 hover:text-blue-500 text-sm">
            ← Volver al inicio
          </Link>
          <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
            👨‍💼 Administradores
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            {showRegister ? 'Registra tu lavadero' : 'Inicia sesión para gestionar tu lavadero'}
          </p>
        </div>

        {!showRegister ? (
          // Login Form
          <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
            {error && (
              <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                {error}
              </div>
            )}
            
            <div>
              <label className="block text-sm font-medium text-gray-700">Email</label>
              <input
                type="email"
                required
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700">Contraseña</label>
              <input
                type="password"
                required
                value={formData.password}
                onChange={(e) => setFormData({...formData, password: e.target.value})}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {loading ? 'Iniciando sesión...' : 'Iniciar Sesión'}
            </button>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-gray-50 text-gray-500">O continúa con</span>
              </div>
            </div>

            <button
              type="button"
              onClick={loginWithGoogle}
              className="group relative w-full flex justify-center py-2 px-4 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Continuar con Google
            </button>
            
            <div className="text-center">
              <button
                type="button"
                onClick={() => setShowRegister(true)}
                className="text-blue-600 hover:text-blue-500"
              >
                ¿Nuevo lavadero? Regístrate aquí
              </button>
            </div>
          </form>
        ) : (
          // Register Form
          <RegisterAdminForm onSuccess={() => setShowRegister(false)} />
        )}

        {/* Información para Super Admin */}
        <div className="mt-8 p-4 bg-gray-50 rounded-lg">
          <h3 className="font-semibold text-gray-800">Super Administrador:</h3>
          <div className="mt-2 text-sm text-gray-700">
            <p>Email: kearcangel@gmail.com</p>
            <p>Contraseña: K@#l1331</p>
          </div>
        </div>
      </div>
    </div>
  );
};

// Componente para Subir Comprobante de Pago (Admin)
const SubirComprobante = () => {
  const { user } = useAuth();
  const [pagoPendiente, setPagoPendiente] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [imagenUrl, setImagenUrl] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchPagoPendiente();
  }, []);

  const fetchPagoPendiente = async () => {
    try {
      const response = await axios.get(`${API}/admin/pago-pendiente`);
      setPagoPendiente(response.data);
    } catch (error) {
      console.error('Error fetching pago pendiente:', error);
      setError('Error al cargar información de pago');
    } finally {
      setLoading(false);
    }
  };

  const handleSubirComprobante = async (e) => {
    e.preventDefault();
    setUploading(true);
    setError('');
    setSuccess('');

    try {
      const response = await axios.post(`${API}/comprobante-mensualidad`, {
        imagen_url: imagenUrl
      });
      
      setSuccess(response.data.message);
      setImagenUrl('');
      await fetchPagoPendiente(); // Refrescar datos
    } catch (error) {
      setError(error.response?.data?.detail || 'Error al subir comprobante');
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8">
        <div className="text-center">Cargando información de pago...</div>
      </div>
    );
  }

  if (!pagoPendiente?.tiene_pago_pendiente) {
    return (
      <div className="p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Comprobante de Pago</h1>
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
          <p>✅ No tienes pagos pendientes. Tu lavadero está al día.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Subir Comprobante de Pago</h1>

      {/* Información del Pago */}
      <div className="bg-blue-50 p-6 rounded-lg mb-6">
        <h2 className="text-xl font-semibold text-blue-800 mb-4">Información de Pago Pendiente</h2>
        <div className="space-y-2">
          <p><strong>Monto:</strong> ${pagoPendiente.monto}</p>
          <p><strong>Período:</strong> {pagoPendiente.mes_año}</p>
          <p><strong>Fecha límite:</strong> {new Date(pagoPendiente.fecha_vencimiento).toLocaleDateString()}</p>
        </div>
      </div>

      {pagoPendiente.tiene_comprobante ? (
        // Ya tiene comprobante subido
        <div className="bg-yellow-50 p-6 rounded-lg">
          <h3 className="text-lg font-semibold text-yellow-800 mb-2">Estado del Comprobante</h3>
          <div className="flex items-center space-x-2">
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
              pagoPendiente.estado_comprobante === 'PENDIENTE' 
                ? 'bg-yellow-100 text-yellow-800'
                : pagoPendiente.estado_comprobante === 'CONFIRMADO'
                ? 'bg-green-100 text-green-800' 
                : 'bg-red-100 text-red-800'
            }`}>
              {pagoPendiente.estado_comprobante}
            </span>
          </div>
          
          {pagoPendiente.estado_comprobante === 'PENDIENTE' && (
            <p className="mt-2 text-sm text-yellow-700">
              Tu comprobante está siendo revisado por el Super Admin. Te notificaremos cuando sea aprobado.
            </p>
          )}
          
          {pagoPendiente.estado_comprobante === 'CONFIRMADO' && (
            <p className="mt-2 text-sm text-green-700">
              ✅ Tu pago ha sido confirmado. Tu lavadero está activo.
            </p>
          )}
          
          {pagoPendiente.estado_comprobante === 'RECHAZADO' && (
            <p className="mt-2 text-sm text-red-700">
              ❌ Tu comprobante fue rechazado. Por favor sube un nuevo comprobante válido.
            </p>
          )}
        </div>
      ) : (
        // Formulario para subir comprobante
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Subir Comprobante de Transferencia</h3>
          
          <form onSubmit={handleSubirComprobante} className="space-y-4">
            {error && (
              <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                {error}
              </div>
            )}
            
            {success && (
              <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
                {success}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                URL de la Imagen del Comprobante *
              </label>
              <input
                type="url"
                required
                value={imagenUrl}
                onChange={(e) => setImagenUrl(e.target.value)}
                placeholder="https://ejemplo.com/mi-comprobante.jpg"
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
              <p className="mt-1 text-sm text-gray-500">
                Sube tu imagen a un servicio como Imgur, Google Drive (enlace público) o similar, y pega aquí el enlace.
              </p>
            </div>

            {imagenUrl && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Vista Previa:</label>
                <img 
                  src={imagenUrl} 
                  alt="Vista previa del comprobante" 
                  className="max-w-sm max-h-64 object-contain border border-gray-300 rounded"
                  onError={(e) => {
                    e.target.style.display = 'none';
                  }}
                />
              </div>
            )}

            <div className="bg-gray-50 p-4 rounded-md">
              <h4 className="font-semibold text-gray-800 mb-2">Instrucciones:</h4>
              <ul className="text-sm text-gray-600 space-y-1 list-disc list-inside">
                <li>El comprobante debe mostrar claramente el monto transferido</li>
                <li>Debe incluir el alias bancario del destinatario</li>
                <li>La imagen debe ser legible y de buena calidad</li>
                <li>Formatos aceptados: JPG, PNG, PDF</li>
              </ul>
            </div>

            <button
              type="submit"
              disabled={uploading || !imagenUrl}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors disabled:opacity-50"
            >
              {uploading ? 'Subiendo...' : 'Subir Comprobante'}
            </button>
          </form>
        </div>
      )}
    </div>
  );
};

// Componente para Revisar Comprobantes (Super Admin)
const RevisarComprobantes = () => {
  const [comprobantes, setComprobantes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [procesando, setProcesando] = useState(null);

  useEffect(() => {
    fetchComprobantes();
  }, []);

  const fetchComprobantes = async () => {
    try {
      const response = await axios.get(`${API}/superadmin/comprobantes-pendientes`);
      setComprobantes(response.data);
    } catch (error) {
      console.error('Error fetching comprobantes:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAprobar = async (comprobanteId) => {
    setProcesando(comprobanteId);
    try {
      await axios.post(`${API}/superadmin/aprobar-comprobante/${comprobanteId}`);
      await fetchComprobantes(); // Refrescar lista
    } catch (error) {
      console.error('Error aprobando comprobante:', error);
      alert('Error al aprobar comprobante');
    } finally {
      setProcesando(null);
    }
  };

  const handleRechazar = async (comprobanteId) => {
    const comentario = prompt('Ingresa el motivo del rechazo:');
    if (!comentario) return;

    setProcesando(comprobanteId);
    try {
      await axios.post(`${API}/superadmin/rechazar-comprobante/${comprobanteId}`, {
        comentario
      });
      await fetchComprobantes(); // Refrescar lista
    } catch (error) {
      console.error('Error rechazando comprobante:', error);
      alert('Error al rechazar comprobante');
    } finally {
      setProcesando(null);
    }
  };

  if (loading) {
    return (
      <div className="p-8">
        <div className="text-center">Cargando comprobantes...</div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Revisar Comprobantes de Pago</h1>

      {comprobantes.length === 0 ? (
        <div className="bg-gray-50 p-6 rounded-lg text-center">
          <p className="text-gray-600">No hay comprobantes pendientes de revisión.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {comprobantes.map((comprobante) => (
            <div key={comprobante.comprobante_id} className="bg-white p-6 rounded-lg shadow border">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">{comprobante.lavadero_nombre}</h3>
                  <p className="text-sm text-gray-600">Admin: {comprobante.admin_nombre} ({comprobante.admin_email})</p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-green-600">${comprobante.monto}</p>
                  <p className="text-sm text-gray-500">
                    {new Date(comprobante.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">Comprobante:</label>
                <img 
                  src={comprobante.imagen_url} 
                  alt="Comprobante de pago" 
                  className="max-w-md max-h-64 object-contain border border-gray-300 rounded"
                  onError={(e) => {
                    e.target.alt = 'Error al cargar imagen';
                    e.target.className = 'text-red-500 text-sm p-4 border border-red-300 rounded';
                  }}
                />
              </div>

              <div className="flex space-x-4">
                <button
                  onClick={() => handleAprobar(comprobante.comprobante_id)}
                  disabled={procesando === comprobante.comprobante_id}
                  className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-md transition-colors disabled:opacity-50"
                >
                  {procesando === comprobante.comprobante_id ? 'Procesando...' : 'Aprobar'}
                </button>
                
                <button
                  onClick={() => handleRechazar(comprobante.comprobante_id)}
                  disabled={procesando === comprobante.comprobante_id}
                  className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md transition-colors disabled:opacity-50"
                >
                  Rechazar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// Main App Component
function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-100">
          <Navigation />
          
          <Routes>
            {/* Página principal dual */}
            <Route path="/" element={<HomePage />} />
            
            {/* Login específico por lavadero */}
            <Route path="/lavadero/:lavaderoId/login" element={<LavaderoLogin />} />
            
            {/* Login para administradores */}
            <Route path="/admin-login" element={<AdminLogin />} />
            
            {/* Rutas antiguas (mantenidas para compatibilidad) */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } />
            
            <Route path="/perfil" element={
              <ProtectedRoute>
                <UserProfile />
              </ProtectedRoute>
            } />
            
            <Route path="/usuarios" element={
              <ProtectedRoute requiredRole="ADMIN">
                <UserManagement />
              </ProtectedRoute>
            } />
            
            <Route path="/admin" element={
              <ProtectedRoute requiredRole="ADMIN">
                <AdminPanel />
              </ProtectedRoute>
            } />
          </Routes>
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;