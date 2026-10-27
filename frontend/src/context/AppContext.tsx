import React, { createContext, useContext, useState, useEffect } from 'react';
import { dashboardApi } from '../api/dashboard';
import { useAuth } from './AuthContext';

export interface BrandInfo {
  id: number | string;
  name: string;
  code: string;
  industry: string;
}

export const AVAILABLE_BRANDS: BrandInfo[] = [
  { id: 1, name: 'AstraForge Demo Brand', code: 'ASTRA', industry: 'Enterprise SaaS' },
  { id: 2, name: 'NovaPay Global', code: 'NVPA', industry: 'Fintech & Payments' },
  { id: 3, name: 'Apex BioTech Labs', code: 'APEX', industry: 'Health & Science' },
];

export interface AppUser {
  id: number | string;
  email: string;
  name: string;
  role: string;
}

interface AppContextType {
  currentBrand: BrandInfo;
  setCurrentBrand: (brand: BrandInfo) => void;
  availableBrands: BrandInfo[];
  currentUser: AppUser;
  isNewReviewOpen: boolean;
  openNewReview: () => void;
  closeNewReview: () => void;
  backendConnected: boolean;
  isCheckingHealth: boolean;
  refreshHealth: () => Promise<void>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentBrand, setCurrentBrand] = useState<BrandInfo>(AVAILABLE_BRANDS[0]);
  const [isNewReviewOpen, setIsNewReviewOpen] = useState(false);
  const [backendConnected, setBackendConnected] = useState(true);
  const [isCheckingHealth, setIsCheckingHealth] = useState(false);

  let authUser: any = null;
  try {
    const auth = useAuth();
    authUser = auth?.user;
  } catch {
    authUser = null;
  }

  const currentUser: AppUser = {
    id: authUser?.id || 1,
    email: authUser?.email || 'tester@brandprint.ai',
    name: authUser?.name || authUser?.full_name || 'Compliance Lead',
    role: authUser?.role || 'Brand Safety Admin',
  };

  const checkHealth = async () => {
    setIsCheckingHealth(true);
    try {
      const res = await dashboardApi.getHealth();
      setBackendConnected(res?.status === 'healthy');
    } catch {
      // Backend may be currently warming up or not yet started
      setBackendConnected(false);
    } finally {
      setIsCheckingHealth(false);
    }
  };

  const bootstrapAuth = async () => {
    const existing = localStorage.getItem('token') || localStorage.getItem('access_token');
    if (!existing) {
      try {
        const { default: apiClient } = await import('../api/client');
        const res = await apiClient.post('/api/auth/login', {
          email: 'tester@brandprint.ai',
          password: 'Password123!',
        });
        if (res.data?.access_token) {
          localStorage.setItem('token', res.data.access_token);
          localStorage.setItem('access_token', res.data.access_token);
        }
      } catch (e) {
        console.debug('Dev auto-login bypassed:', e);
      }
    }
  };

  useEffect(() => {
    bootstrapAuth();
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <AppContext.Provider
      value={{
        currentBrand,
        setCurrentBrand,
        availableBrands: AVAILABLE_BRANDS,
        currentUser,
        isNewReviewOpen,
        openNewReview: () => setIsNewReviewOpen(true),
        closeNewReview: () => setIsNewReviewOpen(false),
        backendConnected,
        isCheckingHealth,
        refreshHealth: checkHealth,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
