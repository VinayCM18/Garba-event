import React, { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { StaffSidebar } from '../components/StaffSidebar';
import { StaffHeader } from '../components/StaffHeader';

export const StaffLayout: React.FC = () => {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const token = localStorage.getItem('admin_token');
    const userJson = localStorage.getItem('admin_user');
    if (!token || !userJson) {
      navigate('/management', { replace: true });
    }
  }, [navigate]);

  const getPageTitle = () => {
    const path = location.pathname;
    if (path === '/staff') return 'Staff Gate Overview';
    if (path === '/staff/scanner') return 'Live Optical QR Scanner';
    if (path === '/staff/search') return 'Attendee & Booking Lookup';
    if (path === '/staff/checkins') return 'Check-in Activity Stream';
    return 'Staff Console';
  };

  return (
    <div className="flex h-screen bg-[#07080f] text-slate-100 overflow-hidden font-['Plus_Jakarta_Sans']">
      {/* Desktop Sidebar */}
      <div className="hidden lg:block h-full">
        <StaffSidebar />
      </div>

      {/* Mobile Drawer */}
      {mobileSidebarOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div
            className="fixed inset-0 bg-black/75 backdrop-blur-sm"
            onClick={() => setMobileSidebarOpen(false)}
          />
          <div className="relative z-10 w-64 h-full bg-[#0c0d16]">
            <StaffSidebar onCloseMobile={() => setMobileSidebarOpen(false)} />
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <StaffHeader
          title={getPageTitle()}
          onOpenMobileSidebar={() => setMobileSidebarOpen(true)}
        />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 bg-gradient-to-b from-[#0e0f1a]/60 to-[#07080f]">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
