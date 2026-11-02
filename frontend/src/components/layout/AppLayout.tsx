import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { NewReviewModal } from '../reviews/NewReviewModal';

export const AppLayout: React.FC = () => {
  const location = useLocation();
  const isStudio = location.pathname.startsWith('/studio') || location.pathname.startsWith('/review');

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-brand-cream text-brand-charcoal font-sans">
      {/* Sidebar in Deep Ocean Teal */}
      <Sidebar />

      {/* Main App Container */}
      <div className="flex-1 flex flex-col h-screen min-w-0 overflow-hidden">
        {/* TopBar with Warm Cream Background & Amber CTA */}
        <TopBar />

        {/* Dynamic Route Content with Warm Cream Background */}
        <main
          className={`flex-1 min-w-0 bg-brand-cream ${
            isStudio ? 'overflow-hidden p-3 lg:p-4' : 'overflow-y-auto p-6 lg:p-8'
          }`}
        >
          <div className={isStudio ? 'h-full max-w-7xl mx-auto flex flex-col min-h-0' : 'max-w-7xl mx-auto'}>
            <Outlet />
          </div>
        </main>
      </div>

      {/* Global New Review Modal */}
      <NewReviewModal />
    </div>
  );
};

export default AppLayout;
