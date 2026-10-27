import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AppProvider } from './context/AppContext';
import { AppLayout } from './components/layout/AppLayout';
import { Dashboard } from './pages/Dashboard';
import { GuidelinesPage } from './pages/GuidelinesPage';
import { ReviewStudio } from './pages/ReviewStudio';
import { AuditPage } from './pages/AuditPage';
import { AuthPage } from './pages/AuthPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

/**
 * Route guard that redirects unauthenticated visitors to /auth,
 * while preserving the intended destination in router state.
 */
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-[#FBF9F4] text-[#072730]">
        <div className="flex flex-col items-center gap-3 p-6 rounded-2xl bg-white border border-[#e8e2d5] shadow-sm">
          <div className="w-8 h-8 border-3 border-[#F4A321] border-t-transparent rounded-full animate-spin" />
          <span className="text-xs font-mono text-[#5d7177]">
            Verifying BrandPrint AI Session...
          </span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

/**
 * Auth guard that redirects already-authenticated visitors to home.
 */
const PublicAuthRoute: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();

  if (!isLoading && isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return <AuthPage />;
};

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <AppProvider>
          <BrowserRouter>
            <Routes>
              {/* Authentication Routes */}
              <Route path="/auth" element={<PublicAuthRoute />} />
              <Route path="/login" element={<Navigate to="/auth" replace />} />

              {/* Protected Workspace Routes */}
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <AppLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<Dashboard />} />
                <Route path="guidelines" element={<GuidelinesPage />} />
                <Route path="studio" element={<ReviewStudio />} />
                <Route path="audit" element={<AuditPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </AppProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
};

export default App;
