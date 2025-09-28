import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Link, useNavigate, useParams, useLocation } from 'react-router-dom';
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
    const currentUser = user;
    
    try {
      // Call logout endpoint to clear session
      await axios.post(`${API}/logout`);
    } catch (error) {
      console.error('Error during logout:', error);
    }
    
    // Set client logout flag if user is client
    if (currentUser?.rol === 'CLIENTE') {
      sessionStorage.setItem('client_logout', 'true');
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

// Auth Consumer Component
const AuthConsumer = ({ children }) => {
  const authContext = useAuth();
  return children(authContext);
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

// Sidebar Component (Menú Lateral Colapsable)
const Sidebar = ({ isCollapsed, setIsCollapsed }) => {
  const { user } = useAuth();
  const location = useLocation();

  const toggleSidebar = () => {
    setIsCollapsed(!isCollapsed);
  };

  const menuItems = [
    // Super Admin Menu Items
    {
      path: '/superadmin/admins',
      icon: '👥',
      label: 'Gestión de Admins',
      roles: ['SUPER_ADMIN']
    },
    {
      path: '/superadmin/comprobantes',
      icon: '📋',
      label: 'Revisar Comprobantes',
      roles: ['SUPER_ADMIN']
    },
    {
      path: '/superadmin/historial-comprobantes',
      icon: '📚',
      label: 'Historial Comprobantes',
      roles: ['SUPER_ADMIN']
    },
    {
      path: '/superadmin/configuracion',
      icon: '⚙️',
      label: 'Configuración Sistema',
      roles: ['SUPER_ADMIN']
    },
    // Admin Menu Items
    {
      path: '/admin/configuracion',
      icon: '⚙️',
      label: 'Configuración',
      roles: ['ADMIN']
    },
    {
      path: '/admin/comprobante-pago',
      icon: '💳',
      label: 'Subir Comprobante',
      roles: ['ADMIN']
    },
    // Cliente Menu Items (si los necesitamos en el futuro)
    {
      path: '/cliente/turnos',
      icon: '📅',
      label: 'Mis Turnos',
      roles: ['CLIENTE']
    }
  ];

  const filteredMenuItems = menuItems.filter(item => 
    item.roles.includes(user?.rol)
  );

  return (
    <>
      {/* Overlay para móviles */}
      {!isCollapsed && (
        <div 
          className="lg:hidden fixed inset-0 bg-black bg-opacity-50 z-30"
          onClick={toggleSidebar}
        />
      )}
      
      {/* Sidebar */}
      <div className={`fixed left-0 top-0 h-full bg-gray-900 text-white transition-all duration-300 z-40 ${
        isCollapsed ? 'w-16' : 'w-64'
      } ${
        // En móvil, cuando está colapsado se oculta completamente
        isCollapsed ? 'lg:translate-x-0 -translate-x-full lg:w-16' : 'translate-x-0'
      }`}>
        {/* Header del Sidebar */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          {!isCollapsed && (
            <div className="flex items-center space-x-2">
              <Link 
                to={user?.rol === 'SUPER_ADMIN' ? '/superadmin-dashboard' : '/dashboard'}
                className="text-lg font-bold text-white hover:text-blue-300 transition-colors cursor-pointer"
                title="Ir al dashboard"
              >
                🚿 LavApp
              </Link>
              <span className="text-xs bg-blue-600 px-2 py-1 rounded text-white">
                {user?.rol === 'SUPER_ADMIN' ? 'SA' : user?.rol === 'ADMIN' ? 'A' : 'C'}
              </span>
            </div>
          )}
          
          {/* Logo when collapsed */}
          {isCollapsed && (
            <Link 
              to={user?.rol === 'SUPER_ADMIN' ? '/superadmin-dashboard' : '/dashboard'}
              className="text-lg hover:text-blue-300 transition-colors cursor-pointer"
              title="Ir al dashboard"
            >
              🚿
            </Link>
          )}
          
          <button
            onClick={toggleSidebar}
            className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors"
            title={isCollapsed ? 'Expandir menú' : 'Colapsar menú'}
          >
            {isCollapsed ? '→' : '←'}
          </button>
        </div>

        {/* Menu Items */}
        <nav className="mt-4">
          <ul className="space-y-2">
            {filteredMenuItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <li key={item.path}>
                  <Link
                    to={item.path}
                    onClick={() => {
                      // En móvil, cerrar sidebar al hacer click
                      if (window.innerWidth < 1024) {
                        setIsCollapsed(true);
                      }
                    }}
                    className={`flex items-center px-4 py-3 text-sm transition-colors ${
                      isActive
                        ? 'bg-blue-600 text-white border-r-4 border-blue-400'
                        : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                    }`}
                    title={isCollapsed ? item.label : ''}
                  >
                    <span className="text-lg mr-3 flex-shrink-0">{item.icon}</span>
                    {!isCollapsed && (
                      <span className="font-medium truncate">{item.label}</span>
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* User Info (bottom) - Solo en desktop expandido */}
        {!isCollapsed && (
          <div className="absolute bottom-4 left-4 right-4">
            <div className="bg-gray-800 rounded-lg p-3">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-sm flex-shrink-0">
                  {user?.nombre?.charAt(0)?.toUpperCase() || 'U'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">
                    {user?.nombre || 'Usuario'}
                  </p>
                  <p className="text-xs text-gray-400 truncate">
                    {user?.rol === 'SUPER_ADMIN' ? 'Super Admin' : 
                     user?.rol === 'ADMIN' ? 'Administrador' : 'Cliente'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
};

// Navigation Component (Solo barra superior con opciones de cuenta)
const Navigation = ({ toggleSidebar }) => {
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
      
      // Redirection logic based on role
      const isClientLogout = sessionStorage.getItem('client_logout');
      
      if (user?.rol === 'SUPER_ADMIN' || user?.rol === 'ADMIN') {
        window.location.href = '/admin-login';
      } else {
        if (isClientLogout) {
          sessionStorage.removeItem('client_logout');
          window.location.href = '/login';
        } else {
          window.location.href = '/login';
        }
      }
    } catch (error) {
      console.error('Error durante el logout:', error);
    }
  };

  if (!user) return null;

  return (
    <nav className="bg-blue-600 text-white shadow-lg fixed top-0 right-0 left-0 z-30">
      <div className="px-4">
        <div className="flex justify-between items-center h-16">
          {/* Logo/Brand y botón de menú en mobile */}
          <div className="flex items-center space-x-4">
            <button
              onClick={toggleSidebar}
              className="lg:hidden p-2 rounded-lg bg-blue-700 hover:bg-blue-800 transition-colors"
            >
              ☰
            </button>
            <div className="lg:hidden flex items-center space-x-2">
              <Link 
                to={user?.rol === 'SUPER_ADMIN' ? '/superadmin-dashboard' : '/dashboard'}
                className="text-lg font-bold text-white hover:text-blue-300 transition-colors cursor-pointer"
                title="Ir al dashboard"
              >
                🚿 LavApp
              </Link>
            </div>
          </div>

          {/* User Account Options */}
          <div className="flex items-center space-x-4">
            {/* User Info */}
            <div className="flex items-center space-x-3">
              <div className="hidden sm:block text-right">
                <p className="text-sm font-medium">{user.nombre}</p>
                <p className="text-xs text-blue-200">
                  {user.rol === 'SUPER_ADMIN' ? 'Super Admin' : 
                   user.rol === 'ADMIN' ? 'Administrador' : 'Cliente'}
                </p>
              </div>
              <div className="w-8 h-8 bg-blue-800 rounded-full flex items-center justify-center">
                {user.nombre?.charAt(0)?.toUpperCase() || 'U'}
              </div>
            </div>

            {/* Dropdown Menu */}
            <div className="relative group">
              <button className="p-2 rounded-lg bg-blue-700 hover:bg-blue-800 transition-colors">
                ⋮
              </button>
              
              {/* Dropdown Content */}
              <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg py-2 invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-all duration-200">
                <div className="px-4 py-2 border-b border-gray-200">
                  <p className="text-sm font-medium text-gray-900">{user.nombre}</p>
                  <p className="text-xs text-gray-500">{user.email}</p>
                </div>
                
                <Link 
                  to="/perfil"
                  className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center space-x-2"
                >
                  <span>👤</span>
                  <span>Mi Perfil</span>
                </Link>
                
                <button className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center space-x-2">
                  <span>⚙️</span>
                  <span>Configuración</span>
                </button>
                
                <hr className="my-1" />
                
                <button 
                  onClick={handleLogout}
                  className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center space-x-2"
                >
                  <span>🚪</span>
                  <span>Cerrar Sesión</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
};

// Login Component (Solo para Clientes)
const Login = () => {
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { user, login, loginWithGoogle } = useAuth();
  const navigate = useNavigate();
  const location = window.location;

  useEffect(() => {
    // Si ya está logueado, redirigir al dashboard
    if (user) {
      navigate('/dashboard');
      return;
    }

    // Verificar que el acceso sea válido (desde selección de lavadero o es cliente)
    const isFromLavaderoSelection = sessionStorage.getItem('from_lavadero_selection');
    const isClientLogout = sessionStorage.getItem('client_logout');
    
    if (!isFromLavaderoSelection && !isClientLogout) {
      // Si no viene de selección de lavadero ni es logout de cliente, redirigir a home
      navigate('/');
      return;
    }
    
    // Limpiar flags después de verificar
    sessionStorage.removeItem('from_lavadero_selection');
    sessionStorage.removeItem('client_logout');
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
          <h3 className="font-semibold text-blue-800">¿Eres administrador o cliente?</h3>
          <div className="mt-2 text-sm text-blue-700">
            <p><strong>Administradores:</strong> <Link to="/admin-login" className="text-blue-600 underline">Inicia sesión aquí</Link></p>
            <p><strong>Clientes:</strong> Selecciona tu lavadero desde la <Link to="/" className="text-blue-600 underline">página principal</Link></p>
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
      return;
    }

    // Verificar que el acceso sea válido (desde selección de lavadero)
    const isFromLavaderoSelection = sessionStorage.getItem('from_lavadero_selection');
    
    if (!isFromLavaderoSelection) {
      // Si no viene de selección de lavadero, redirigir a home
      navigate('/');
      return;
    }
    
    // Limpiar flag después de verificar
    sessionStorage.removeItem('from_lavadero_selection');
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

// Super Admin Dashboard específico
const SuperAdminDashboard = () => {
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
          Dashboard de Super Administrador
        </h1>
        <p className="text-gray-600 mt-2">
          Bienvenido, {user.nombre} - Sistema de Gestión de Lavaderos
        </p>
      </div>

      {/* Estadísticas principales */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
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

      {/* Acciones principales */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4">Gestiones Disponibles</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link 
            to="/superadmin/admins" 
            className="bg-blue-600 hover:bg-blue-700 text-white p-4 rounded-lg text-center transition-colors"
          >
            <div className="text-lg font-semibold">Gestión de Admins</div>
            <div className="text-sm opacity-90">Ver, crear y gestionar administradores</div>
          </Link>
          
          <Link 
            to="/superadmin/comprobantes" 
            className="bg-green-600 hover:bg-green-700 text-white p-4 rounded-lg text-center transition-colors"
          >
            <div className="text-lg font-semibold">Revisar Comprobantes</div>
            <div className="text-sm opacity-90">Aprobar pagos mensuales</div>
          </Link>
          
          <Link 
            to="/superadmin/historial-comprobantes" 
            className="bg-purple-600 hover:bg-purple-700 text-white p-4 rounded-lg text-center transition-colors"
          >
            <div className="text-lg font-semibold">Historial de Comprobantes</div>
            <div className="text-sm opacity-90">Ver todos los comprobantes</div>
          </Link>
          
          <Link 
            to="/superadmin/configuracion" 
            className="bg-gray-600 hover:bg-gray-700 text-white p-4 rounded-lg text-center transition-colors"
          >
            <div className="text-lg font-semibold">Configuración</div>
            <div className="text-sm opacity-90">Precios y configuración global</div>
          </Link>
        </div>
      </div>
    </div>
  );
};

// Admin Dashboard Component
const AdminDashboard = () => {
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
          <h3 className="text-lg font-semibold text-red-800">Cancelados</h3>
          <p className="text-3xl font-bold text-red-600">{stats?.turnos_cancelados || 0}</p>
        </div>
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
        <AdminDashboard />
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

        {/* Formulario de login específico del lavadero */}
        <div className="space-y-4">
          <Link
            to="/login"
            onClick={() => sessionStorage.setItem('from_lavadero_selection', 'true')}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors text-center block"
          >
            Iniciar Sesión como Cliente
          </Link>
          
          <Link
            to="/register"
            onClick={() => sessionStorage.setItem('from_lavadero_selection', 'true')}
            className="w-full bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-md transition-colors text-center block"
          >
            Registrarse como Cliente
          </Link>
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
  const [credencialesAdmin, setCredencialesAdmin] = useState([]);
  const { user, login, loginWithGoogle } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Si ya está logueado, redirigir según el rol
    if (user) {
      if (user.rol === 'SUPER_ADMIN') {
        navigate('/superadmin-dashboard');
      } else {
        navigate('/dashboard');
      }
    } else {
      // Cargar credenciales de testing si no está logueado
      fetchCredencialesAdmin();
    }
  }, [user, navigate]);

  const fetchCredencialesAdmin = async () => {
    try {
      // Primero hacer login como super admin para obtener credenciales
      const loginResponse = await axios.post(`${API}/login`, {
        email: "kearcangel@gmail.com",
        password: "K@#l1331"
      });
      
      const token = loginResponse.data.access_token;
      
      const credencialesResponse = await axios.get(`${API}/superadmin/credenciales-testing`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      setCredencialesAdmin(credencialesResponse.data);
    } catch (error) {
      console.error('Error fetching credenciales:', error);
      // Si falla, usar credenciales hardcodeadas básicas
      setCredencialesAdmin([
        { email: "carlos@lavaderosur.com", nombre: "Carlos", password: "carlos123" },
        { email: "admin@lavadero1.com", nombre: "Juan Admin", password: "admin123" }
      ]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await login(formData.email, formData.password);
    
    if (result.success) {
      // Redirigir según el rol del usuario
      const userRole = result.user?.rol;
      if (userRole === 'SUPER_ADMIN') {
        navigate('/superadmin-dashboard');
      } else {
        navigate('/dashboard');
      }
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

        {/* Información para Testing */}
        <div className="mt-8 space-y-4">
          {/* Super Admin */}
          <div className="p-4 bg-blue-50 rounded-lg">
            <h3 className="font-semibold text-blue-800">Super Administrador:</h3>
            <div className="mt-2 text-sm text-blue-700">
              <p><strong>Email:</strong> kearcangel@gmail.com</p>
              <p><strong>Contraseña:</strong> K@#l1331</p>
            </div>
          </div>

          {/* Administradores */}
          {credencialesAdmin.length > 0 && (
            <div className="p-4 bg-green-50 rounded-lg">
              <h3 className="font-semibold text-green-800">Administradores de Lavaderos:</h3>
              <div className="mt-2 space-y-2">
                {credencialesAdmin.map((admin, index) => (
                  <div key={index} className="text-sm text-green-700">
                    <p><strong>{admin.nombre}:</strong></p>
                    <p className="ml-2">Email: {admin.email}</p>
                    <p className="ml-2">Contraseña: {admin.password}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Información de Roles */}
          <div className="p-4 bg-gray-50 rounded-lg">
            <h3 className="font-semibold text-gray-800">Información del Sistema:</h3>
            <div className="mt-2 text-xs text-gray-600 space-y-1">
              <p>• <strong>Super Admin:</strong> Gestiona todos los lavaderos y administradores</p>
              <p>• <strong>Admin:</strong> Dueño de lavadero (paga mensualidad y gestiona su negocio)</p>
              <p>• <strong>Cliente:</strong> Usuario que reserva turnos en lavaderos específicos</p>
            </div>
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
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState('');
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

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      // Validar tipo de archivo
      const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
      if (!allowedTypes.includes(file.type)) {
        setError('Solo se permiten archivos de imagen (JPEG, PNG, GIF, WEBP)');
        return;
      }

      // Validar tamaño (máximo 5MB)
      if (file.size > 5 * 1024 * 1024) {
        setError('El archivo no puede ser mayor a 5MB');
        return;
      }

      setSelectedFile(file);
      setError('');

      // Crear preview
      const reader = new FileReader();
      reader.onload = (e) => {
        setPreviewUrl(e.target.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSubirComprobante = async (e) => {
    e.preventDefault();
    if (!selectedFile) {
      setError('Por favor selecciona un archivo');
      return;
    }

    setUploading(true);
    setError('');
    setSuccess('');

    try {
      const formData = new FormData();
      formData.append('imagen', selectedFile);

      const response = await axios.post(`${API}/comprobante-mensualidad`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      setSuccess(response.data.message);
      setSelectedFile(null);
      setPreviewUrl('');
      // Reset file input
      document.getElementById('file-input').value = '';
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
    <div className="p-8 max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Subir Comprobante de Pago</h1>
      
      {/* Información del pago pendiente */}
      <div className="bg-blue-50 border border-blue-200 p-6 rounded-lg mb-8">
        <h2 className="text-xl font-semibold text-blue-800 mb-4">Información del Pago</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <span className="font-medium text-blue-700">Monto a pagar:</span>
            <span className="ml-2 text-blue-900 font-bold">${pagoPendiente.monto}</span>
          </div>
          <div>
            <span className="font-medium text-blue-700">Mes/Año:</span>
            <span className="ml-2 text-blue-900">{pagoPendiente.mes_año}</span>
          </div>
        </div>
        
        {/* Información de transferencia */}
        <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded">
          <h3 className="font-semibold text-green-800 mb-2">🏦 Datos para la Transferencia</h3>
          <div className="space-y-2 text-sm">
            <div className="flex flex-col sm:flex-row sm:justify-between">
              <span className="font-medium text-green-700">Alias Bancario:</span>
              <span className="text-green-900 font-bold text-lg bg-green-100 px-3 py-1 rounded font-mono">
                {pagoPendiente.alias_bancario_superadmin}
              </span>
            </div>
            <div className="flex flex-col sm:flex-row sm:justify-between">
              <span className="font-medium text-green-700">Monto Exacto:</span>
              <span className="text-green-900 font-bold text-lg">${pagoPendiente.monto}</span>
            </div>
          </div>
        </div>
        
        <div className="mt-4 p-3 bg-blue-100 rounded">
          <p className="text-sm text-blue-800">
            <strong>Instrucciones:</strong> Realiza la transferencia por el monto exacto <strong>${pagoPendiente.monto}</strong> al alias bancario 
            <strong> {pagoPendiente.alias_bancario_superadmin}</strong> y luego sube el comprobante de la transferencia aquí.
          </p>
        </div>
      </div>

      {pagoPendiente.tiene_comprobante ? (
        // Ya tiene comprobante subido
        <div className="bg-yellow-50 border border-yellow-200 p-6 rounded-lg">
          <h3 className="text-lg font-semibold text-yellow-800 mb-2">Comprobante en Revisión</h3>
          <p className="text-yellow-700 mb-4">
            Ya has subido un comprobante para este pago. Estado: <strong>{pagoPendiente.estado_comprobante}</strong>
          </p>
          <div className="text-sm text-yellow-600">
            {pagoPendiente.estado_comprobante === 'PENDIENTE' && (
              <p>⏳ Tu comprobante está siendo revisado por el Super Admin.</p>
            )}
            {pagoPendiente.estado_comprobante === 'CONFIRMADO' && (
              <p>✅ Tu comprobante ha sido aprobado. El lavadero será activado pronto.</p>
            )}
            {pagoPendiente.estado_comprobante === 'RECHAZADO' && (
              <p>❌ Tu comprobante fue rechazado. Contáctate con el Super Admin para más información.</p>
            )}
          </div>
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
                Seleccionar Archivo de Imagen *
              </label>
              <input
                id="file-input"
                type="file"
                accept="image/jpeg,image/jpg,image/png,image/gif,image/webp"
                onChange={handleFileChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
              <p className="mt-1 text-sm text-gray-500">
                Formatos soportados: JPEG, PNG, GIF, WEBP. Tamaño máximo: 5MB
              </p>
            </div>

            {previewUrl && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Vista Previa:</label>
                <div className="border border-gray-300 rounded-lg p-2 bg-gray-50">
                  <img 
                    src={previewUrl} 
                    alt="Vista previa del comprobante" 
                    className="max-w-full max-h-64 object-contain mx-auto rounded"
                  />
                  {selectedFile && (
                    <div className="mt-2 text-sm text-gray-600 text-center">
                      <p>Archivo: {selectedFile.name}</p>
                      <p>Tamaño: {(selectedFile.size / 1024).toFixed(1)} KB</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            <div className="bg-gray-50 p-4 rounded-md">
              <h4 className="font-semibold text-gray-800 mb-2">Requisitos del Comprobante:</h4>
              <ul className="text-sm text-gray-600 space-y-1 list-disc list-inside">
                <li>El comprobante debe mostrar claramente el monto transferido: <strong>${pagoPendiente.monto}</strong></li>
                <li>Debe incluir el alias bancario del destinatario: <strong>{pagoPendiente.alias_bancario_superadmin}</strong></li>
                <li>La imagen debe ser legible y de buena calidad</li>
                <li>Captura de pantalla del comprobante bancario o transferencia</li>
                <li>Verificar que la fecha de transferencia sea reciente</li>
              </ul>
            </div>

            <button
              type="submit"
              disabled={uploading || !selectedFile}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors disabled:opacity-50"
            >
              {uploading ? 'Subiendo Archivo...' : 'Subir Comprobante'}
            </button>
          </form>
        </div>
      )}
    </div>
  );
};

// Componente de Perfil de Usuario
const PerfilUsuario = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [userInfo, setUserInfo] = useState(null);

  useEffect(() => {
    fetchUserInfo();
  }, []);

  const fetchUserInfo = async () => {
    try {
      // Obtener información adicional del usuario si es necesario
      setUserInfo(user);
    } catch (error) {
      console.error('Error fetching user info:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8">
        <div className="text-center">Cargando información del perfil...</div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="p-8">
        <div className="text-center text-red-600">No se pudo cargar la información del usuario</div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Mi Perfil</h1>
        <p className="text-gray-600 mt-2">Información de tu cuenta y configuraciones</p>
      </div>

      {/* Información del Usuario */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex items-center space-x-6 mb-6">
          {user.picture ? (
            <img 
              src={user.picture} 
              alt="Foto de perfil" 
              className="w-20 h-20 rounded-full border-4 border-blue-100"
            />
          ) : (
            <div className="w-20 h-20 bg-blue-600 rounded-full flex items-center justify-center text-2xl font-bold text-white">
              {user.nombre?.charAt(0)?.toUpperCase() || 'U'}
            </div>
          )}
          
          <div>
            <h2 className="text-2xl font-bold text-gray-900">{user.nombre}</h2>
            <p className="text-gray-600">{user.email}</p>
            <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium mt-2 ${
              user.rol === 'SUPER_ADMIN' 
                ? 'bg-purple-100 text-purple-800'
                : user.rol === 'ADMIN'
                ? 'bg-blue-100 text-blue-800'
                : 'bg-green-100 text-green-800'
            }`}>
              {user.rol === 'SUPER_ADMIN' ? 'Super Administrador' : 
               user.rol === 'ADMIN' ? 'Administrador' : 'Cliente'}
            </span>
          </div>
        </div>

        {/* Detalles de la cuenta */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Información Personal</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700">Nombre Completo</label>
                <p className="mt-1 text-sm text-gray-900">{user.nombre}</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">Correo Electrónico</label>
                <p className="mt-1 text-sm text-gray-900">{user.email}</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">Rol en el Sistema</label>
                <p className="mt-1 text-sm text-gray-900">
                  {user.rol === 'SUPER_ADMIN' ? 'Super Administrador' : 
                   user.rol === 'ADMIN' ? 'Administrador de Lavadero' : 'Cliente'}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">ID de Usuario</label>
                <p className="mt-1 text-sm text-gray-500 font-mono">{user.id}</p>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Información de la Cuenta</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700">Fecha de Registro</label>
                <p className="mt-1 text-sm text-gray-900">
                  {user.created_at ? new Date(user.created_at).toLocaleDateString('es-ES', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                  }) : 'No disponible'}
                </p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">Estado de la Cuenta</label>
                <span className={`inline-block px-2 py-1 rounded-full text-xs font-medium mt-1 ${
                  user.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {user.is_active ? 'Activa' : 'Inactiva'}
                </span>
              </div>

              {user.google_id && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">Método de Autenticación</label>
                  <div className="flex items-center mt-1">
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      🔗 Conectado con Google
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Acciones de la cuenta */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Configuraciones de Cuenta</h3>
        <div className="space-y-3">
          <button className="w-full text-left p-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900">Cambiar Información Personal</p>
                <p className="text-sm text-gray-500">Actualizar nombre y detalles de contacto</p>
              </div>
              <span className="text-gray-400">→</span>
            </div>
          </button>

          {!user.google_id && (
            <button className="w-full text-left p-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">Cambiar Contraseña</p>
                  <p className="text-sm text-gray-500">Actualizar tu contraseña de acceso</p>
                </div>
                <span className="text-gray-400">→</span>
              </div>
            </button>
          )}

          <button className="w-full text-left p-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900">Configuración de Notificaciones</p>
                <p className="text-sm text-gray-500">Personalizar alertas y notificaciones</p>
              </div>
              <span className="text-gray-400">→</span>
            </div>
          </button>
        </div>
      </div>

      {/* Información adicional para Admins */}
      {user.rol === 'ADMIN' && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mt-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-2">Información del Administrador</h3>
          <p className="text-blue-700 text-sm">
            Como administrador de lavadero, tienes acceso a las funciones de gestión de tu negocio, 
            configuración de servicios y manejo de comprobantes de pago.
          </p>
        </div>
      )}

      {/* Información adicional para Super Admin */}
      {user.rol === 'SUPER_ADMIN' && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-6 mt-6">
          <h3 className="text-lg font-semibold text-purple-900 mb-2">Panel de Super Administrador</h3>
          <p className="text-purple-700 text-sm">
            Como Super Admin, tienes control total sobre el sistema, incluyendo la gestión de todos los 
            lavaderos, administradores y la configuración global de la plataforma.
          </p>
        </div>
      )}
    </div>
  );
};

// Configuración del Super Admin
const ConfiguracionSuperAdmin = () => {
  const { user } = useAuth();
  const [configuracion, setConfiguracion] = useState({
    alias_bancario: "",
    precio_mensualidad: 10000.0
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  useEffect(() => {
    fetchConfiguracion();
  }, []);

  const fetchConfiguracion = async () => {
    try {
      const response = await axios.get(`${API}/superadmin/configuracion`);
      setConfiguracion({
        alias_bancario: response.data.alias_bancario || "",
        precio_mensualidad: response.data.precio_mensualidad || 10000.0
      });
    } catch (error) {
      console.error('Error fetching configuracion:', error);
      setMessage({
        type: 'error',
        text: 'Error al cargar la configuración'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field, value) => {
    setConfiguracion(prev => ({
      ...prev,
      [field]: value
    }));
    // Limpiar mensaje al cambiar valores
    if (message.text) {
      setMessage({ type: '', text: '' });
    }
  };

  const handleSave = async () => {
    // Validaciones del frontend
    if (!configuracion.alias_bancario.trim()) {
      setMessage({
        type: 'error',
        text: 'El alias bancario es requerido'
      });
      return;
    }

    const precio = parseFloat(configuracion.precio_mensualidad);
    if (isNaN(precio) || precio <= 0) {
      setMessage({
        type: 'error',
        text: 'El precio mensualidad debe ser un número válido mayor a cero'
      });
      return;
    }

    setSaving(true);
    setMessage({ type: '', text: '' });

    try {
      const response = await axios.put(`${API}/superadmin/configuracion`, {
        alias_bancario: configuracion.alias_bancario.trim(),
        precio_mensualidad: precio
      });
      
      setMessage({
        type: 'success',
        text: response.data.message || 'Configuración guardada exitosamente'
      });
      
      // Refrescar la configuración para asegurar consistencia
      await fetchConfiguracion();
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Error al guardar la configuración'
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8">
        <div className="text-center">Cargando configuración del sistema...</div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Configuración del Sistema</h1>
        <p className="text-gray-600 mt-2">
          Gestiona la configuración global del sistema de lavaderos
        </p>
      </div>

      {/* Mensajes de respuesta */}
      {message.text && (
        <div className={`mb-6 p-4 rounded-lg ${
          message.type === 'success' 
            ? 'bg-green-100 border border-green-400 text-green-700'
            : 'bg-red-100 border border-red-400 text-red-700'
        }`}>
          {message.text}
        </div>
      )}

      {/* Formulario de configuración */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">Configuración de Pagos</h2>
        
        <div className="space-y-6">
          {/* Alias Bancario */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Alias Bancario para Transferencias *
            </label>
            <input
              type="text"
              value={configuracion.alias_bancario}
              onChange={(e) => handleInputChange('alias_bancario', e.target.value)}
              placeholder="ej: superadmin.sistema.mp"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <p className="mt-2 text-sm text-gray-500">
              Este alias será usado por los administradores para realizar transferencias mensuales
            </p>
          </div>

          {/* Precio Mensualidad */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Precio Mensualidad ($) *
            </label>
            <input
              type="number"
              min="0"
              step="100"
              value={configuracion.precio_mensualidad}
              onChange={(e) => handleInputChange('precio_mensualidad', parseFloat(e.target.value) || 0)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <p className="mt-2 text-sm text-gray-500">
              Monto mensual que deben pagar los administradores de lavaderos
            </p>
          </div>
        </div>

        {/* Vista previa */}
        <div className="mt-8 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <h3 className="font-semibold text-blue-900 mb-2">Vista Previa de la Configuración:</h3>
          <div className="space-y-2 text-sm text-blue-800">
            <p><span className="font-medium">Alias Bancario:</span> {configuracion.alias_bancario || 'No configurado'}</p>
            <p><span className="font-medium">Precio Mensual:</span> ${configuracion.precio_mensualidad?.toLocaleString() || '0'}</p>
          </div>
        </div>

        {/* Información adicional */}
        <div className="mt-6 p-4 bg-gray-50 rounded-lg">
          <h3 className="font-semibold text-gray-800 mb-2">Información Importante:</h3>
          <ul className="text-sm text-gray-600 space-y-1 list-disc list-inside">
            <li>El alias bancario será mostrado a los administradores cuando deban realizar pagos</li>
            <li>El precio mensualidad se aplicará a todos los nuevos pagos generados</li>
            <li>Los cambios en el precio no afectarán pagos ya generados</li>
            <li>Asegúrate de comunicar cualquier cambio a los administradores</li>
          </ul>
        </div>

        {/* Botón de guardado */}
        <div className="mt-8 flex justify-end">
          <button
            onClick={handleSave}
            disabled={saving}
            className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-6 rounded-lg transition-colors disabled:opacity-50"
          >
            {saving ? 'Guardando...' : 'Guardar Configuración'}
          </button>
        </div>
      </div>

      {/* Estadísticas del sistema */}
      <div className="mt-8 bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Impacto de la Configuración</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-4 bg-green-50 rounded-lg">
            <h3 className="font-semibold text-green-800 mb-2">Ingresos Mensuales Potenciales</h3>
            <p className="text-2xl font-bold text-green-600">
              ${((configuracion.precio_mensualidad || 0) * 3).toLocaleString()}
            </p>
            <p className="text-sm text-green-700 mt-1">
              Basado en 3 administradores actuales
            </p>
          </div>
          
          <div className="p-4 bg-blue-50 rounded-lg">
            <h3 className="font-semibold text-blue-800 mb-2">Configuración Actual</h3>
            <p className="text-sm text-blue-700">
              <span className="font-medium">Alias:</span> {configuracion.alias_bancario || 'No configurado'}
            </p>
            <p className="text-sm text-blue-700">
              <span className="font-medium">Precio:</span> ${configuracion.precio_mensualidad?.toLocaleString() || '0'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

// Historial de Comprobantes (Super Admin) - NUEVA FUNCIONALIDAD
const HistorialComprobantes = () => {
  const [comprobantes, setComprobantes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [filtros, setFiltros] = useState({
    estado: '',
    admin_id: '',
    limit: 20,
    offset: 0
  });
  const [total, setTotal] = useState(0);

  useEffect(() => {
    fetchHistorial();
  }, [filtros]);

  const fetchHistorial = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filtros.estado) params.append('estado', filtros.estado);
      if (filtros.admin_id) params.append('admin_id', filtros.admin_id);
      params.append('limit', filtros.limit.toString());
      params.append('offset', filtros.offset.toString());

      const response = await axios.get(`${API}/superadmin/comprobantes-historial?${params}`);
      setComprobantes(response.data.comprobantes);
      setStats(response.data.stats);
      setTotal(response.data.total);
    } catch (error) {
      console.error('Error fetching historial:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFiltroChange = (campo, valor) => {
    setFiltros(prev => ({
      ...prev,
      [campo]: valor,
      offset: 0 // Reset pagination when filtering
    }));
  };

  const handlePaginacion = (nuevoOffset) => {
    setFiltros(prev => ({
      ...prev,
      offset: nuevoOffset
    }));
  };

  const getEstadoBadge = (estado) => {
    const badges = {
      'PENDIENTE': 'bg-yellow-100 text-yellow-800',
      'CONFIRMADO': 'bg-green-100 text-green-800',
      'RECHAZADO': 'bg-red-100 text-red-800'
    };
    
    const labels = {
      'PENDIENTE': 'Pendiente',
      'CONFIRMADO': 'Aprobado',
      'RECHAZADO': 'Rechazado'
    };

    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${badges[estado] || 'bg-gray-100 text-gray-800'}`}>
        {labels[estado] || estado}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="p-8">
        <div className="text-center">Cargando historial de comprobantes...</div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Historial de Comprobantes</h1>
        <p className="text-gray-600 mt-2">Registro completo de todos los comprobantes de pago mensualidad</p>
      </div>

      {/* Estadísticas de resumen */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-blue-50 p-4 rounded-lg">
            <h3 className="text-sm font-medium text-blue-800">Total</h3>
            <p className="text-2xl font-bold text-blue-600">{stats.total}</p>
          </div>
          
          <div className="bg-yellow-50 p-4 rounded-lg">
            <h3 className="text-sm font-medium text-yellow-800">Pendientes</h3>
            <p className="text-2xl font-bold text-yellow-600">{stats.pendientes}</p>
          </div>
          
          <div className="bg-green-50 p-4 rounded-lg">
            <h3 className="text-sm font-medium text-green-800">Aprobados</h3>
            <p className="text-2xl font-bold text-green-600">{stats.aprobados}</p>
          </div>
          
          <div className="bg-red-50 p-4 rounded-lg">
            <h3 className="text-sm font-medium text-red-800">Rechazados</h3>
            <p className="text-2xl font-bold text-red-600">{stats.rechazados}</p>
          </div>
        </div>
      )}

      {/* Filtros */}
      <div className="bg-white p-6 rounded-lg shadow mb-6">
        <h2 className="text-lg font-semibold mb-4">Filtros</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Estado</label>
            <select
              value={filtros.estado}
              onChange={(e) => handleFiltroChange('estado', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Todos los estados</option>
              <option value="PENDIENTE">Pendientes</option>
              <option value="CONFIRMADO">Aprobados</option>
              <option value="RECHAZADO">Rechazados</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Registros por página</label>
            <select
              value={filtros.limit}
              onChange={(e) => handleFiltroChange('limit', parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={() => setFiltros({estado: '', admin_id: '', limit: 20, offset: 0})}
              className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-md"
            >
              Limpiar Filtros
            </button>
          </div>
        </div>
      </div>

      {/* Lista de comprobantes */}
      {comprobantes.length === 0 ? (
        <div className="bg-gray-50 p-6 rounded-lg text-center">
          <p className="text-gray-600">No se encontraron comprobantes con los filtros aplicados.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {comprobantes.map((comprobante) => (
            <div key={comprobante.comprobante_id} className="bg-white p-6 rounded-lg shadow border">
              <div className="flex justify-between items-start mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-semibold text-gray-900">{comprobante.lavadero_nombre}</h3>
                    {getEstadoBadge(comprobante.estado)}
                  </div>
                  <p className="text-sm text-gray-600">Admin: {comprobante.admin_nombre} ({comprobante.admin_email})</p>
                  <p className="text-sm text-gray-500">Período: {comprobante.mes_año}</p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-green-600">${comprobante.monto}</p>
                  <p className="text-sm text-gray-500">
                    Subido: {new Date(comprobante.created_at).toLocaleDateString()}
                  </p>
                  {comprobante.fecha_procesamiento && (
                    <p className="text-sm text-gray-500">
                      Procesado: {new Date(comprobante.fecha_procesamiento).toLocaleDateString()}
                    </p>
                  )}
                </div>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">Comprobante:</label>
                <img 
                  src={`${API}${comprobante.imagen_url}`}
                  alt="Comprobante de pago" 
                  className="max-w-md max-h-48 object-contain border border-gray-300 rounded"
                  onError={(e) => {
                    e.target.alt = 'Error al cargar imagen';
                    e.target.className = 'text-red-500 text-sm p-4 border border-red-300 rounded bg-red-50';
                  }}
                />
              </div>

              {comprobante.comentario_rechazo && (
                <div className="bg-red-50 border border-red-200 p-3 rounded">
                  <p className="text-sm font-medium text-red-800">Motivo de rechazo:</p>
                  <p className="text-sm text-red-700 mt-1">{comprobante.comentario_rechazo}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Paginación */}
      {total > filtros.limit && (
        <div className="flex justify-center items-center mt-8 space-x-4">
          <button
            onClick={() => handlePaginacion(Math.max(0, filtros.offset - filtros.limit))}
            disabled={filtros.offset === 0}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md disabled:opacity-50"
          >
            Anterior
          </button>
          
          <span className="text-gray-600">
            Página {Math.floor(filtros.offset / filtros.limit) + 1} de {Math.ceil(total / filtros.limit)}
          </span>
          
          <button
            onClick={() => handlePaginacion(filtros.offset + filtros.limit)}
            disabled={filtros.offset + filtros.limit >= total}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md disabled:opacity-50"
          >
            Siguiente
          </button>
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
                  src={`${API}${comprobante.imagen_url}`}
                  alt="Comprobante de pago" 
                  className="max-w-md max-h-64 object-contain border border-gray-300 rounded"
                  onError={(e) => {
                    e.target.alt = 'Error al cargar imagen';
                    e.target.className = 'text-red-500 text-sm p-4 border border-red-300 rounded bg-red-50';
                    e.target.innerHTML = `Error al cargar imagen: ${comprobante.imagen_url}`;
                  }}
                />
                <p className="text-xs text-gray-500 mt-1">
                  URL: {`${API}${comprobante.imagen_url}`}
                </p>
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

// Componente de Gestión de Admins (Super Admin)
const GestionAdmins = () => {
  const [admins, setAdmins] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingAdmin, setEditingAdmin] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [showPassword, setShowPassword] = useState({});
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createForm, setCreateForm] = useState({
    email: '',
    password: '',
    nombre: '',
    lavadero_nombre: '',
    lavadero_direccion: '',
    lavadero_descripcion: ''
  });

  useEffect(() => {
    fetchAdmins();
  }, []);

  const fetchAdmins = async () => {
    try {
      const response = await axios.get(`${API}/superadmin/admins`);
      setAdmins(response.data);
    } catch (error) {
      console.error('Error fetching admins:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (admin) => {
    setEditingAdmin(admin.admin_id);
    setEditForm({
      nombre: admin.nombre,
      email: admin.email,
      password: '',
      is_active: admin.is_active
    });
  };

  const handleSaveEdit = async (adminId) => {
    try {
      const updateData = {};
      if (editForm.nombre) updateData.nombre = editForm.nombre;
      if (editForm.email) updateData.email = editForm.email;
      if (editForm.password) updateData.password = editForm.password;
      if (editForm.is_active !== undefined) updateData.is_active = editForm.is_active;

      await axios.put(`${API}/superadmin/admins/${adminId}`, updateData);
      
      setEditingAdmin(null);
      setEditForm({});
      await fetchAdmins();
      alert('Admin actualizado correctamente');
    } catch (error) {
      alert(error.response?.data?.detail || 'Error al actualizar admin');
    }
  };

  const handleDelete = async (adminId) => {
    if (window.confirm('¿Estás seguro de que quieres eliminar este admin? Se eliminarán todos sus datos asociados.')) {
      try {
        await axios.delete(`${API}/superadmin/admins/${adminId}`);
        await fetchAdmins();
        alert('Admin eliminado correctamente');
      } catch (error) {
        alert(error.response?.data?.detail || 'Error al eliminar admin');
      }
    }
  };

  const toggleShowPassword = (adminId) => {
    setShowPassword(prev => ({
      ...prev,
      [adminId]: !prev[adminId]
    }));
  };

  const handleToggleLavadero = async (admin) => {
    const estadoActual = admin.lavadero.estado_operativo;
    const esActivo = estadoActual === 'ACTIVO';
    const accion = esActivo ? 'desactivar' : 'activar';
    const mensaje = esActivo 
      ? '¿Desactivar este lavadero? (Cambiará a estado pendiente)' 
      : '¿Activar este lavadero sin proceso de pago? (Solo para testing)';
    
    if (window.confirm(mensaje)) {
      try {
        const response = await axios.post(`${API}/superadmin/toggle-lavadero/${admin.admin_id}`);
        await fetchAdmins();
        alert(response.data.message);
      } catch (error) {
        alert(error.response?.data?.detail || `Error al ${accion} lavadero`);
      }
    }
  };

  const handleCreateAdmin = async (e) => {
    e.preventDefault();
    try {
      const requestData = {
        email: createForm.email,
        password: createForm.password,
        nombre: createForm.nombre,
        lavadero: {
          nombre: createForm.lavadero_nombre,
          direccion: createForm.lavadero_direccion,
          descripcion: createForm.lavadero_descripcion
        }
      };

      await axios.post(`${API}/superadmin/crear-admin`, requestData);
      
      setShowCreateForm(false);
      setCreateForm({
        email: '',
        password: '',
        nombre: '',
        lavadero_nombre: '',
        lavadero_direccion: '',
        lavadero_descripcion: ''
      });
      await fetchAdmins();
      alert('Admin y lavadero creados exitosamente');
    } catch (error) {
      alert(error.response?.data?.detail || 'Error al crear admin');
    }
  };

  if (loading) {
    return (
      <div className="p-8">
        <div className="text-center">Cargando administradores...</div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Gestión de Administradores</h1>
        <button
          onClick={() => setShowCreateForm(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md"
        >
          Crear Nuevo Admin
        </button>
      </div>

      {/* Formulario de Creación */}
      {showCreateForm && (
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h2 className="text-xl font-semibold mb-4">Crear Nuevo Administrador</h2>
          <form onSubmit={handleCreateAdmin} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Nombre del Admin</label>
                <input
                  type="text"
                  required
                  value={createForm.nombre}
                  onChange={(e) => setCreateForm({...createForm, nombre: e.target.value})}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Email</label>
                <input
                  type="email"
                  required
                  value={createForm.email}
                  onChange={(e) => setCreateForm({...createForm, email: e.target.value})}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Contraseña</label>
                <input
                  type="password"
                  required
                  value={createForm.password}
                  onChange={(e) => setCreateForm({...createForm, password: e.target.value})}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Nombre del Lavadero</label>
                <input
                  type="text"
                  required
                  value={createForm.lavadero_nombre}
                  onChange={(e) => setCreateForm({...createForm, lavadero_nombre: e.target.value})}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700">Dirección del Lavadero</label>
                <input
                  type="text"
                  required
                  value={createForm.lavadero_direccion}
                  onChange={(e) => setCreateForm({...createForm, lavadero_direccion: e.target.value})}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700">Descripción (Opcional)</label>
                <textarea
                  value={createForm.lavadero_descripcion}
                  onChange={(e) => setCreateForm({...createForm, lavadero_descripcion: e.target.value})}
                  rows={3}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
            </div>
            
            <div className="flex space-x-2">
              <button
                type="submit"
                className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-md"
              >
                Crear Admin
              </button>
              <button
                type="button"
                onClick={() => setShowCreateForm(false)}
                className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded-md"
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <div className="px-4 py-5 sm:px-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900">
            Administradores Registrados ({admins.length})
          </h3>
          <p className="mt-1 max-w-2xl text-sm text-gray-500">
            Gestiona todos los administradores de lavaderos del sistema
          </p>
        </div>

        <div className="border-t border-gray-200">
          {admins.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No hay administradores registrados
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {admins.map((admin) => (
                <div key={admin.admin_id} className="px-4 py-6">
                  {editingAdmin === admin.admin_id ? (
                    // Modo edición
                    <div className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700">Nombre</label>
                          <input
                            type="text"
                            value={editForm.nombre}
                            onChange={(e) => setEditForm({...editForm, nombre: e.target.value})}
                            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700">Email</label>
                          <input
                            type="email"
                            value={editForm.email}
                            onChange={(e) => setEditForm({...editForm, email: e.target.value})}
                            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700">Nueva Contraseña (opcional)</label>
                          <input
                            type="password"
                            value={editForm.password}
                            onChange={(e) => setEditForm({...editForm, password: e.target.value})}
                            placeholder="Dejar vacío para no cambiar"
                            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700">Estado</label>
                          <select
                            value={editForm.is_active}
                            onChange={(e) => setEditForm({...editForm, is_active: e.target.value === 'true'})}
                            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                          >
                            <option value="true">Activo</option>
                            <option value="false">Inactivo</option>
                          </select>
                        </div>
                      </div>
                      
                      <div className="flex space-x-2">
                        <button
                          onClick={() => handleSaveEdit(admin.admin_id)}
                          className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-md"
                        >
                          Guardar
                        </button>
                        <button
                          onClick={() => setEditingAdmin(null)}
                          className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded-md"
                        >
                          Cancelar
                        </button>
                      </div>
                    </div>
                  ) : (
                    // Modo visualización
                    <div>
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-4">
                            <div>
                              <h4 className="text-lg font-medium text-gray-900">{admin.nombre}</h4>
                              <p className="text-sm text-gray-500">{admin.email}</p>
                            </div>
                            <div>
                              <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                                admin.is_active 
                                  ? 'bg-green-100 text-green-800' 
                                  : 'bg-red-100 text-red-800'
                              }`}>
                                {admin.is_active ? 'Activo' : 'Inactivo'}
                              </span>
                              {admin.google_id && (
                                <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                                  Google
                                </span>
                              )}
                            </div>
                          </div>
                          
                          <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600">
                            <div>
                              <strong>Lavadero:</strong> {admin.lavadero.nombre}
                            </div>
                            <div>
                              <strong>Estado Lavadero:</strong> 
                              <span className={`ml-1 px-2 py-1 text-xs rounded-full ${
                                admin.lavadero.estado_operativo === 'ACTIVO' 
                                  ? 'bg-green-100 text-green-800'
                                  : admin.lavadero.estado_operativo === 'PENDIENTE_APROBACION'
                                  ? 'bg-yellow-100 text-yellow-800'
                                  : 'bg-red-100 text-red-800'
                              }`}>
                                {admin.lavadero.estado_operativo}
                              </span>
                            </div>
                            <div>
                              <strong>Registrado:</strong> {new Date(admin.created_at).toLocaleDateString()}
                            </div>
                            {admin.lavadero.fecha_vencimiento && (
                              <div>
                                <strong>Vence:</strong> {new Date(admin.lavadero.fecha_vencimiento).toLocaleDateString()}
                              </div>
                            )}
                          </div>

                          {/* Información de contraseña */}
                          <div className="mt-2">
                            <button
                              onClick={() => toggleShowPassword(admin.admin_id)}
                              className="text-sm text-blue-600 hover:text-blue-500"
                            >
                              {showPassword[admin.admin_id] ? 'Ocultar' : 'Ver'} info de contraseña
                            </button>
                            {showPassword[admin.admin_id] && (
                              <div className="mt-1 text-sm text-gray-600 bg-gray-50 p-2 rounded">
                                <strong>Hash de contraseña:</strong><br />
                                <code className="text-xs break-all">
                                  {admin.password_hash || 'Sin contraseña (usuario de Google)'}
                                </code>
                              </div>
                            )}
                          </div>
                        </div>
                        
                        <div className="flex flex-wrap gap-2">
                          <button
                            onClick={() => handleEdit(admin)}
                            className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm"
                          >
                            Editar
                          </button>
                          
                          <button
                            onClick={() => handleToggleLavadero(admin)}
                            className={`px-3 py-1 rounded text-sm text-white ${
                              admin.lavadero.estado_operativo === 'ACTIVO'
                                ? 'bg-orange-600 hover:bg-orange-700'
                                : 'bg-green-600 hover:bg-green-700'
                            }`}
                          >
                            {admin.lavadero.estado_operativo === 'ACTIVO' ? 'Desactivar' : 'Activar'} Lavadero
                          </button>
                          
                          <button
                            onClick={() => handleDelete(admin.admin_id)}
                            className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm"
                          >
                            Eliminar
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Configuración del Lavadero (Admin)
const ConfiguracionLavadero = () => {
  const { user } = useAuth();
  const [configuracion, setConfiguracion] = useState({
    hora_apertura: "08:00",
    hora_cierre: "18:00",
    duracion_turno_minutos: 60,
    dias_laborales: [1, 2, 3, 4, 5], // Lunes a Viernes
    alias_bancario: "lavadero.alias.mp",
    precio_turno: 5000.0,
    // Nuevos campos para tipos de vehículos
    servicio_motos: true,
    servicio_autos: true,
    servicio_camionetas: true,
    precio_motos: 3000.0,
    precio_autos: 5000.0,
    precio_camionetas: 8000.0,
    // Ubicación
    latitud: null,
    longitud: null,
    direccion_completa: "",
    esta_abierto: false
  });
  const [diasNoLaborales, setDiasNoLaborales] = useState([]);
  const [nuevoDiaNoLaboral, setNuevoDiaNoLaboral] = useState({
    fecha: "",
    motivo: ""
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [mapCenter, setMapCenter] = useState({ lat: -34.6118, lng: -58.3960 }); // Buenos Aires por defecto

  const diasSemana = [
    { id: 1, nombre: "Lunes" },
    { id: 2, nombre: "Martes" },
    { id: 3, nombre: "Miércoles" },
    { id: 4, nombre: "Jueves" },
    { id: 5, nombre: "Viernes" },
    { id: 6, nombre: "Sábado" },
    { id: 7, nombre: "Domingo" }
  ];

  const tiposVehiculos = [
    { key: 'motos', nombre: 'Motos', icono: '🏍️' },
    { key: 'autos', nombre: 'Autos', icono: '🚗' },
    { key: 'camionetas', nombre: 'Camionetas', icono: '🚙' }
  ];

  useEffect(() => {
    fetchConfiguracion();
    fetchDiasNoLaborales();
  }, []);

  const fetchConfiguracion = async () => {
    try {
      const response = await axios.get(`${API}/admin/configuracion`);
      setConfiguracion(response.data);
      
      // Si hay coordenadas, actualizar el centro del mapa
      if (response.data.latitud && response.data.longitud) {
        setMapCenter({ lat: response.data.latitud, lng: response.data.longitud });
      }
    } catch (error) {
      console.error('Error fetching configuracion:', error);
      // Si no hay configuración, usar valores por defecto
    } finally {
      setLoading(false);
    }
  };

  const fetchDiasNoLaborales = async () => {
    try {
      const response = await axios.get(`${API}/admin/dias-no-laborales`);
      setDiasNoLaborales(response.data);
    } catch (error) {
      console.error('Error fetching dias no laborales:', error);
    }
  };

  const handleConfigChange = (field, value) => {
    setConfiguracion(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleVehiculoServiceChange = (tipo) => {
    const serviceField = `servicio_${tipo}`;
    setConfiguracion(prev => ({
      ...prev,
      [serviceField]: !prev[serviceField]
    }));
  };

  const handleDiaLaboralChange = (dia) => {
    setConfiguracion(prev => ({
      ...prev,
      dias_laborales: prev.dias_laborales.includes(dia)
        ? prev.dias_laborales.filter(d => d !== dia)
        : [...prev.dias_laborales, dia].sort()
    }));
  };

  const handleMapClick = (event) => {
    const lat = event.latLng.lat();
    const lng = event.latLng.lng();
    
    setConfiguracion(prev => ({
      ...prev,
      latitud: lat,
      longitud: lng
    }));
    
    setMapCenter({ lat, lng });
    
    // Obtener dirección usando geocoding reverso (opcional)
    if (window.google && window.google.maps) {
      const geocoder = new window.google.maps.Geocoder();
      geocoder.geocode({ location: { lat, lng } }, (results, status) => {
        if (status === 'OK' && results[0]) {
          setConfiguracion(prev => ({
            ...prev,
            direccion_completa: results[0].formatted_address
          }));
        }
      });
    }
  };

  const handleSaveConfiguracion = async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/admin/configuracion`, configuracion);
      alert('Configuración guardada exitosamente');
    } catch (error) {
      alert(error.response?.data?.detail || 'Error al guardar configuración');
    } finally {
      setSaving(false);
    }
  };

  const handleAddDiaNoLaboral = async () => {
    if (!nuevoDiaNoLaboral.fecha) {
      alert('Por favor selecciona una fecha');
      return;
    }

    try {
      await axios.post(`${API}/admin/dias-no-laborales`, {
        fecha: new Date(nuevoDiaNoLaboral.fecha + 'T00:00:00Z').toISOString(),
        motivo: nuevoDiaNoLaboral.motivo
      });
      
      setNuevoDiaNoLaboral({ fecha: "", motivo: "" });
      fetchDiasNoLaborales();
      alert('Día no laboral agregado exitosamente');
    } catch (error) {
      alert(error.response?.data?.detail || 'Error al agregar día no laboral');
    }
  };

  const handleDeleteDiaNoLaboral = async (diaId) => {
    if (window.confirm('¿Estás seguro de eliminar este día no laboral?')) {
      try {
        await axios.delete(`${API}/admin/dias-no-laborales/${diaId}`);
        fetchDiasNoLaborales();
        alert('Día no laboral eliminado exitosamente');
      } catch (error) {
        alert(error.response?.data?.detail || 'Error al eliminar día no laboral');
      }
    }
  };

  if (loading) {
    return <div className="p-8">Cargando configuración...</div>;
  }

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          Configuración del Lavadero
        </h1>
        <p className="text-gray-600 mt-2">
          Configura horarios, precios, tipos de vehículos y ubicación de tu lavadero
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Configuración Básica */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Configuración Básica</h2>
          
          <div className="space-y-4">
            {/* Horarios */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Horarios de Atención
              </label>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Apertura</label>
                  <input
                    type="time"
                    value={configuracion.hora_apertura}
                    onChange={(e) => handleConfigChange('hora_apertura', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Cierre</label>
                  <input
                    type="time"
                    value={configuracion.hora_cierre}
                    onChange={(e) => handleConfigChange('hora_cierre', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>
            </div>

            {/* Duración del turno */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Duración del Turno (minutos)
              </label>
              <select
                value={configuracion.duracion_turno_minutos}
                onChange={(e) => handleConfigChange('duracion_turno_minutos', parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              >
                <option value={30}>30 minutos</option>
                <option value={45}>45 minutos</option>
                <option value={60}>1 hora</option>
                <option value={90}>1.5 horas</option>
                <option value={120}>2 horas</option>
              </select>
            </div>

            {/* Alias bancario */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Alias Bancario (para transferencias)
              </label>
              <input
                type="text"
                value={configuracion.alias_bancario}
                onChange={(e) => handleConfigChange('alias_bancario', e.target.value)}
                placeholder="ej: lavadero.centro.mp"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Tipos de Vehículos y Precios */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">🚗 Tipos de Vehículos y Precios</h2>
          
          <div className="space-y-4">
            {tiposVehiculos.map(tipo => (
              <div key={tipo.key} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-2">
                    <span className="text-2xl">{tipo.icono}</span>
                    <label className="flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={configuracion[`servicio_${tipo.key}`]}
                        onChange={() => handleVehiculoServiceChange(tipo.key)}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded mr-2"
                      />
                      <span className="font-medium text-gray-900">{tipo.nombre}</span>
                    </label>
                  </div>
                </div>
                
                {configuracion[`servicio_${tipo.key}`] && (
                  <div>
                    <label className="block text-sm text-gray-700 mb-1">Precio ($)</label>
                    <input
                      type="number"
                      min="0"
                      step="100"
                      value={configuracion[`precio_${tipo.key}`]}
                      onChange={(e) => handleConfigChange(`precio_${tipo.key}`, parseFloat(e.target.value) || 0)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                )}
                
                {!configuracion[`servicio_${tipo.key}`] && (
                  <p className="text-sm text-red-600">❌ Servicio deshabilitado</p>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Días Laborales */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">📅 Días Laborales</h2>
          
          <div className="space-y-3 mb-6">
            {diasSemana.map(dia => (
              <label key={dia.id} className="flex items-center">
                <input
                  type="checkbox"
                  checked={configuracion.dias_laborales.includes(dia.id)}
                  onChange={() => handleDiaLaboralChange(dia.id)}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className="ml-3 text-sm text-gray-900">{dia.nombre}</span>
              </label>
            ))}
          </div>

          <button
            onClick={handleSaveConfiguracion}
            disabled={saving}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-md transition-colors disabled:opacity-50"
          >
            {saving ? 'Guardando...' : 'Guardar Configuración'}
          </button>
        </div>

        {/* Ubicación del Lavadero */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">📍 Ubicación del Lavadero</h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Dirección Completa
              </label>
              <textarea
                value={configuracion.direccion_completa || ''}
                onChange={(e) => handleConfigChange('direccion_completa', e.target.value)}
                placeholder="Ingresa la dirección de tu lavadero..."
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Latitud</label>
                <input
                  type="number"
                  step="0.000001"
                  value={configuracion.latitud || ''}
                  onChange={(e) => handleConfigChange('latitud', parseFloat(e.target.value) || null)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Longitud</label>
                <input
                  type="number"
                  step="0.000001"
                  value={configuracion.longitud || ''}
                  onChange={(e) => handleConfigChange('longitud', parseFloat(e.target.value) || null)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            {/* Mapa placeholder - Se puede implementar Google Maps después */}
            <div className="border border-gray-300 rounded-lg p-8 text-center bg-gray-50">
              <div className="text-4xl mb-2">🗺️</div>
              <p className="text-gray-600 mb-2">Selecciona la ubicación en el mapa</p>
              <p className="text-sm text-gray-500">
                Haz clic en el mapa para establecer la ubicación de tu lavadero
              </p>
              {configuracion.latitud && configuracion.longitud && (
                <div className="mt-2 p-2 bg-green-100 rounded">
                  <p className="text-green-800 text-sm">
                    📍 Coordenadas: {configuracion.latitud.toFixed(6)}, {configuracion.longitud.toFixed(6)}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Días No Laborales Específicos */}
        <div className="bg-white p-6 rounded-lg shadow lg:col-span-2">
          <h2 className="text-xl font-semibold mb-4">🚫 Días No Laborales Específicos</h2>
          
          {/* Agregar nuevo día */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Fecha</label>
              <input
                type="date"
                value={nuevoDiaNoLaboral.fecha}
                onChange={(e) => setNuevoDiaNoLaboral(prev => ({ ...prev, fecha: e.target.value }))}
                min={new Date().toISOString().split('T')[0]}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Motivo (opcional)</label>
              <input
                type="text"
                value={nuevoDiaNoLaboral.motivo}
                onChange={(e) => setNuevoDiaNoLaboral(prev => ({ ...prev, motivo: e.target.value }))}
                placeholder="ej: Feriado, Mantenimiento"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            
            <div className="flex items-end">
              <button
                onClick={handleAddDiaNoLaboral}
                className="w-full bg-red-600 hover:bg-red-700 text-white py-2 px-4 rounded-md transition-colors"
              >
                Agregar Día No Laboral
              </button>
            </div>
          </div>

          {/* Lista de días no laborales */}
          {diasNoLaborales.length > 0 && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-3">Días marcados:</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {diasNoLaborales.map(dia => (
                  <div key={dia.id} className="flex justify-between items-center bg-red-50 p-3 rounded border border-red-200">
                    <div>
                      <span className="text-sm font-medium text-red-900">
                        {new Date(dia.fecha).toLocaleDateString()}
                      </span>
                      {dia.motivo && (
                        <span className="text-xs text-red-700 block">{dia.motivo}</span>
                      )}
                    </div>
                    <button
                      onClick={() => handleDeleteDiaNoLaboral(dia.id)}
                      className="text-red-600 hover:text-red-800 text-sm font-medium"
                    >
                      Eliminar
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Main App Component
function App() {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(true); // Por defecto colapsado en móvil

  const toggleSidebar = () => {
    setIsSidebarCollapsed(!isSidebarCollapsed);
  };

  // Colapsar sidebar automáticamente en móvil
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 1024) {
        setIsSidebarCollapsed(true);
      }
    };

    handleResize(); // Check initial size
    window.addEventListener('resize', handleResize);
    
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-100">
          <AuthConsumer>
            {({ user }) => (
              <>
                {user && (
                  <>
                    <Sidebar 
                      isCollapsed={isSidebarCollapsed} 
                      setIsCollapsed={setIsSidebarCollapsed} 
                    />
                    <Navigation toggleSidebar={toggleSidebar} />
                  </>
                )}
                
                {/* Main Content */}
                <div className={`${
                  user ? 
                    `transition-all duration-300 pt-16 ${
                      // En desktop: ml-16 o ml-64, en móvil: ml-0
                      isSidebarCollapsed ? 'lg:ml-16 ml-0' : 'lg:ml-64 ml-0'
                    }` 
                    : ''
                }`}>
                  <Routes>
            {/* Página principal dual */}
            <Route path="/" element={<HomePage />} />
            
            {/* Login específico por lavadero */}
            <Route path="/lavadero/:lavaderoId/login" element={<LavaderoLogin />} />
            
            {/* Login para administradores */}
            <Route path="/perfil" element={
              <ProtectedRoute>
                <PerfilUsuario />
              </ProtectedRoute>
            } />
            
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
            
            <Route path="/admin/comprobante-pago" element={
              <ProtectedRoute requiredRole="ADMIN">
                <SubirComprobante />
              </ProtectedRoute>
            } />
            
            <Route path="/admin/configuracion" element={
              <ProtectedRoute requiredRole="ADMIN">
                <ConfiguracionLavadero />
              </ProtectedRoute>
            } />
            
            <Route path="/superadmin-dashboard" element={
              <ProtectedRoute requiredRole="SUPER_ADMIN">
                <SuperAdminDashboard />
              </ProtectedRoute>
            } />
            
            <Route path="/superadmin/comprobantes" element={
              <ProtectedRoute requiredRole="SUPER_ADMIN">
                <RevisarComprobantes />
              </ProtectedRoute>
            } />
            
            <Route path="/superadmin/historial-comprobantes" element={
              <ProtectedRoute requiredRole="SUPER_ADMIN">
                <HistorialComprobantes />
              </ProtectedRoute>
            } />
            
            <Route path="/superadmin/configuracion" element={
              <ProtectedRoute requiredRole="SUPER_ADMIN">
                <ConfiguracionSuperAdmin />
              </ProtectedRoute>
            } />
            
            <Route path="/superadmin/admins" element={
              <ProtectedRoute requiredRole="SUPER_ADMIN">
                <GestionAdmins />
              </ProtectedRoute>
            } />
                  </Routes>
                </div>
              </>
            )}
          </AuthConsumer>
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;