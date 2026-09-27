import React, { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { AdminSidebar } from '../components/AdminSidebar';
import { AdminHeader } from '../components/AdminHeader';
import { AccessDenied } from '../components/AccessDenied';

export const AdminLayout: React.FC = () => {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [userRole, setUserRole] = useState<string | null>(null);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const token = localStorage.getItem('admin_token');
    const userJson = localStorage.getItem('admin_user');
    if (!token || !userJson) {
      navigate('/management', { replace: true });
      return;
    }
    try {
      const user = JSON.parse(userJson);
      setUserRole(user.role);
    } catch {
      navigate('/management', { replace: true });
    }
  }, [navigate]);

  // If user is Staff, show Access Denied page and redirect to /staff
  if (userRole === 'CHECKIN_STAFF' || userRole === 'STAFF') {
    return (
      <div className="min-h-screen bg-[#090710] flex items-center justify-center p-4">
        <AccessDenied redirectPath="/staff" autoRedirectMs={3500} />
      </div>
    );
  }

  // Derive title from pathname
  const getPageTitle = () => {
    const path = location.pathname;
    if (path === '/admin') return 'Dashboard Overview';
    if (path === '/admin/verification') return 'Payment Verification';
    if (path === '/admin/bookings') return 'Bookings Management';
    if (path.startsWith('/admin/bookings/')) return 'Booking Details';
    if (path === '/admin/scanner') return 'Live QR Gate Scanner';
    if (path === '/admin/checkins') return 'Check-in Audit Logs';
    if (path === '/admin/settings') return 'Event Configuration';
    if (path === '/admin/audit-logs') return 'System Audit Trail';
    return 'Admin Console';
  };

  return (
    <div className="flex h-screen bg-[#090710] text-slate-100 overflow-hidden font-['Plus_Jakarta_Sans']">
      {/* Desktop Sidebar */}
      <div className="hidden lg:block h-full">
        <AdminSidebar />
      </div>

      {/* Mobile Drawer */}
      {mobileSidebarOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div
            className="fixed inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => setMobileSidebarOpen(false)}
          />
          <div className="relative z-10 w-64 h-full bg-[#0f0c1b]">
            <AdminSidebar onCloseMobile={() => setMobileSidebarOpen(false)} />
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <AdminHeader
          title={getPageTitle()}
          onOpenMobileSidebar={() => setMobileSidebarOpen(true)}
        />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 bg-gradient-to-b from-[#0f0c1b]/50 to-[#090710]">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
