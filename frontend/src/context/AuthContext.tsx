import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { User, AuthResponse } from '../types';
import { authApi, RegisterPayload, ForgotPasswordResponse } from '../api/auth';

export interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string, rememberMe?: boolean) => Promise<AuthResponse>;
  register: (payload: RegisterPayload) => Promise<AuthResponse>;
  logout: () => void;
  forgotPassword: (email: string) => Promise<ForgotPasswordResponse>;
  loginAsGuestDemo: () => void;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = 'brandprint_auth_token';
const USER_KEY = 'brandprint_user';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    return authApi.getCurrentUser();
  });
  const [token, setToken] = useState<string | null>(() => {
    return authApi.getToken();
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Initialize and verify authentication on mount
  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = authApi.getToken();
      if (!storedToken) {
        setIsLoading(false);
        return;
      }

      setToken(storedToken);

      try {
        const profile = await authApi.getMe();
        setUser(profile);
      } catch (err: any) {
        // If 401 unauthorized, clear expired session
        if (err?.response?.status === 401) {
          console.warn('[BrandPrint AI Auth] Stored token expired or invalid, clearing credentials.');
          authApi.logout();
          setToken(null);
          setUser(null);
        } else {
          // If network error / offline, retain cached user
          const cachedUser = authApi.getCurrentUser();
          if (cachedUser) {
            setUser(cachedUser);
          }
        }
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const login = useCallback(async (email: string, password: string, rememberMe: boolean = true): Promise<AuthResponse> => {
    setIsLoading(true);
    try {
      const response = await authApi.login(email, password);
      setToken(response.access_token);
      setUser(response.user);

      if (!rememberMe) {
        // If user unchecked remember me, session storage can be used or kept in memory
        sessionStorage.setItem(TOKEN_KEY, response.access_token);
      }
      return response;
    } catch (error: any) {
      // Fallback demo account if backend is unreachable or offline
      if (email === 'tester@brandprint.ai' && (error?.message?.includes('Network Error') || error?.message?.includes('unreachable'))) {
        const demoUser: User = {
          id: 1,
          email: 'tester@brandprint.ai',
          name: 'Enterprise Auditor',
          full_name: 'Enterprise Auditor',
          company: 'BrandPrint Enterprise Systems',
          role: 'BrandManager',
          created_at: new Date().toISOString(),
        };
        const mockToken = 'mock_demo_jwt_token_brandprint_ai_' + Date.now();
        localStorage.setItem(TOKEN_KEY, mockToken);
        localStorage.setItem(USER_KEY, JSON.stringify(demoUser));
        localStorage.setItem('token', mockToken);
        localStorage.setItem('user', JSON.stringify(demoUser));
        setToken(mockToken);
        setUser(demoUser);
        return {
          access_token: mockToken,
          token_type: 'bearer',
          user: demoUser,
        };
      }
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const register = useCallback(async (payload: RegisterPayload): Promise<AuthResponse> => {
    setIsLoading(true);
    try {
      const response = await authApi.register(payload);
      setToken(response.access_token);
      setUser(response.user);
      return response;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    authApi.logout();
    sessionStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const forgotPassword = useCallback(async (email: string): Promise<ForgotPasswordResponse> => {
    return await authApi.forgotPassword(email);
  }, []);

  const loginAsGuestDemo = useCallback(() => {
    const demoUser: User = {
      id: 999,
      email: 'tester@brandprint.ai',
      name: 'Executive Auditor',
      full_name: 'Executive Auditor',
      company: 'BrandPrint AI Global',
      role: 'BrandManager',
      created_at: new Date().toISOString(),
    };
    const mockToken = 'demo_guest_bearer_token_' + Date.now();
    localStorage.setItem(TOKEN_KEY, mockToken);
    localStorage.setItem(USER_KEY, JSON.stringify(demoUser));
    localStorage.setItem('token', mockToken);
    localStorage.setItem('user', JSON.stringify(demoUser));
    setToken(mockToken);
    setUser(demoUser);
  }, []);

  const refreshProfile = useCallback(async () => {
    try {
      const profile = await authApi.getMe();
      setUser(profile);
    } catch (err) {
      console.warn('[BrandPrint AI Auth] Failed to refresh profile:', err);
    }
  }, []);

  const isAuthenticated = Boolean(token && user);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated,
        isLoading,
        login,
        register,
        logout,
        forgotPassword,
        loginAsGuestDemo,
        refreshProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;

