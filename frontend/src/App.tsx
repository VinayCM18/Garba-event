import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ToastProvider } from './components/Toast';
import { PublicLayout } from './layouts/PublicLayout';
import { AdminLayout } from './layouts/AdminLayout';
import { StaffLayout } from './layouts/StaffLayout';

// Public Pages
import { HomePage } from './pages/HomePage';
import { BookingPage } from './pages/BookingPage';
import { SuccessPage } from './pages/SuccessPage';
import { TicketPage } from './pages/TicketPage';
import { TermsPage } from './pages/TermsPage';
import { PrivacyPage } from './pages/PrivacyPage';
import { RefundPage } from './pages/RefundPage';
import { RulesPage } from './pages/RulesPage';

// Management Authentication Page
import { ManagementLoginPage } from './pages/ManagementLoginPage';

// Admin Pages
import { AdminDashboardPage } from './pages/AdminDashboardPage';
import { AdminBookingsPage } from './pages/AdminBookingsPage';
import { AdminBookingDetailPage } from './pages/AdminBookingDetailPage';
import { AdminScannerPage } from './pages/AdminScannerPage';
import { AdminCheckinsPage } from './pages/AdminCheckinsPage';
import { AdminSettingsPage } from './pages/AdminSettingsPage';
import { AdminAuditLogsPage } from './pages/AdminAuditLogsPage';
import { AdminPaymentVerificationPage } from './pages/AdminPaymentVerificationPage';

// Staff Pages
import { StaffDashboardPage } from './pages/StaffDashboardPage';
import { StaffScannerPage } from './pages/StaffScannerPage';
import { StaffSearchPage } from './pages/StaffSearchPage';
import { StaffCheckinsPage } from './pages/StaffCheckinsPage';

export const App: React.FC = () => {
  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Customer Routes */}
          <Route element={<PublicLayout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/book" element={<BookingPage />} />
            <Route path="/success/:bookingId" element={<SuccessPage />} />
            <Route path="/ticket/:token" element={<TicketPage />} />
            <Route path="/terms" element={<TermsPage />} />
            <Route path="/privacy" element={<PrivacyPage />} />
            <Route path="/refund" element={<RefundPage />} />
            <Route path="/rules" element={<RulesPage />} />
          </Route>

          {/* Unified Management Portal Route */}
          <Route path="/management" element={<ManagementLoginPage />} />
          {/* Backwards compatibility redirect */}
          <Route path="/admin/login" element={<Navigate to="/management" replace />} />
          <Route path="/staff/login" element={<Navigate to="/management" replace />} />

          {/* Admin Protected Console */}
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<AdminDashboardPage />} />
            <Route path="dashboard" element={<Navigate to="/admin" replace />} />
            <Route path="verification" element={<AdminPaymentVerificationPage />} />
            <Route path="bookings" element={<AdminBookingsPage />} />
            <Route path="bookings/:id" element={<AdminBookingDetailPage />} />
            <Route path="scanner" element={<AdminScannerPage />} />
            <Route path="checkins" element={<AdminCheckinsPage />} />
            <Route path="settings" element={<AdminSettingsPage />} />
            <Route path="audit-logs" element={<AdminAuditLogsPage />} />
          </Route>

          {/* Staff Protected Console */}
          <Route path="/staff" element={<StaffLayout />}>
            <Route index element={<StaffDashboardPage />} />
            <Route path="dashboard" element={<Navigate to="/staff" replace />} />
            <Route path="scanner" element={<StaffScannerPage />} />
            <Route path="search" element={<StaffSearchPage />} />
            <Route path="checkins" element={<StaffCheckinsPage />} />
          </Route>

          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  );
};

export default App;
