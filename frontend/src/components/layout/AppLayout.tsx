import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { NewReviewModal } from '../reviews/NewReviewModal';

export const AppLayout: React.FC = () => {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-brand-cream text-brand-charcoal font-sans">
      {/* Sidebar in Deep Ocean Teal */}
      <Sidebar />

      {/* Main App Container */}
      <div className="flex-1 flex flex-col h-screen min-w-0 overflow-hidden">
        {/* TopBar with Warm Cream Background & Amber CTA */}
        <TopBar />

        {/* Dynamic Route Content with Warm Cream Background */}
        <main className="flex-1 overflow-y-auto bg-brand-cream p-6 lg:p-8">
          <div className="max-w-7xl mx-auto">
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
