import axios from 'axios';
import {
  EventConfig,
  Booking,
  Ticket,
  AdminDashboardStats,
  DashboardAnalytics,
  CheckInRecord,
  AuditLogRecord,
  AdminUser,
  QRVerifyResult,
  CheckInResult,
  PaymentVerificationItem
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || '';

export const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach bearer token if stored
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Public Event & Booking APIs
export const fetchPublicConfig = async (): Promise<EventConfig> => {
  const res = await api.get('/api/bookings/public-config');
  return res.data;
};

export interface FeeCalculation {
  ticket_price: number;
  ticket_count: number;
  regular_amount?: number;
  group_discount?: number;
  ticket_subtotal: number;
  payment_fee: number;
  gst_amount: number;
  total_amount: number;
  currency: string;
  is_group_offer?: boolean;
  offer_name?: string;
  free_tickets?: number;
}

export const calculatePaymentFee = async (ticketCount: number): Promise<FeeCalculation> => {
  const res = await api.get('/api/payments/calculate', { params: { ticket_count: ticketCount } });
  return res.data;
};

export const createPaymentOrder = async (payload: {
  customer_name: string;
  email: string;
  phone: string;
  ticket_count: number;
  idempotency_key?: string;
}) => {
  const res = await api.post('/api/payments/create-order', payload);
  return res.data;
};

export const verifyPaymentSignature = async (payload: {
  booking_id: string;
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}) => {
  const res = await api.post('/api/payments/verify', payload);
  return res.data;
};

export const fetchBookingDetails = async (bookingId: string): Promise<Booking> => {
  const res = await api.get(`/api/bookings/${bookingId}`);
  return res.data;
};

export const lookupBookingStatus = async (bookingId: string, contact?: string): Promise<Booking> => {
  const res = await api.get('/api/bookings/status/lookup', {
    params: { booking_id: bookingId, contact }
  });
  return res.data;
};

export const retryPaymentOrder = async (bookingId: string) => {
  const res = await api.post(`/api/payments/retry/${bookingId}`);
  return res.data;
};

export const failPaymentOrder = async (bookingId: string, reason?: string) => {
  const res = await api.post(`/api/payments/fail/${bookingId}`, null, {
    params: { reason }
  });
  return res.data;
};

export const resendCustomerBookingEmail = async (bookingId: string): Promise<{ success: boolean; message: string }> => {
  const res = await api.post(`/api/bookings/${bookingId}/resend-email`);
  return res.data;
};

export const fetchTicketByToken = async (qrToken: string): Promise<Ticket> => {
  const res = await api.get(`/api/tickets/view/${qrToken}`);
  return res.data;
};

// QR Verification and Check-in
export const verifyQR = async (qrToken: string): Promise<QRVerifyResult> => {
  const res = await api.post('/api/qr/verify', { qr_token: qrToken });
  return res.data;
};

export const checkInQR = async (
  qrToken: string,
  deviceInfo?: string,
  notes?: string
): Promise<CheckInResult> => {
  const res = await api.post('/api/qr/checkin', {
    qr_token: qrToken,
    device_information: deviceInfo,
    notes,
  });
  return res.data;
};

// Admin Authentication APIs
export const adminLogin = async (payload: { email: string; password: string }) => {
  const res = await api.post('/api/auth/login', payload);
  if (res.data.access_token) {
    localStorage.setItem('admin_token', res.data.access_token);
    localStorage.setItem('admin_user', JSON.stringify({
      name: res.data.name,
      email: res.data.email,
      role: res.data.role
    }));
  }
  return res.data;
};

export const adminLogout = async () => {
  try {
    await api.post('/api/auth/logout');
  } finally {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
  }
};

export const fetchAdminMe = async (): Promise<AdminUser> => {
  const res = await api.get('/api/auth/me');
  return res.data;
};

// Admin Dashboard & Operations
export const fetchDashboardStats = async (): Promise<AdminDashboardStats> => {
  const res = await api.get('/api/admin/dashboard');
  return res.data;
};

export const fetchDashboardAnalytics = async (): Promise<DashboardAnalytics> => {
  const res = await api.get('/api/admin/analytics');
  return res.data;
};

export const fetchAdminBookings = async (params: {
  page?: number;
  per_page?: number;
  search?: string;
  payment_status?: string;
  booking_status?: string;
}) => {
  const res = await api.get('/api/admin/bookings', { params });
  return res.data;
};

export const fetchAdminBookingDetails = async (bookingId: string): Promise<Booking> => {
  const res = await api.get(`/api/admin/bookings/${bookingId}`);
  return res.data;
};

export const resendBookingEmail = async (bookingId: string) => {
  const res = await api.post(`/api/admin/bookings/${bookingId}/resend-email`);
  return res.data;
};

export const cancelBooking = async (bookingId: string) => {
  const res = await api.post(`/api/admin/bookings/${bookingId}/cancel`);
  return res.data;
};

export const fetchAdminCheckins = async (limit = 50): Promise<CheckInRecord[]> => {
  const res = await api.get('/api/admin/checkins', { params: { limit } });
  return res.data;
};

export const fetchAdminAuditLogs = async (limit = 50): Promise<AuditLogRecord[]> => {
  const res = await api.get('/api/admin/audit-logs', { params: { limit } });
  return res.data;
};

export const fetchAdminSettings = async (): Promise<EventConfig> => {
  const res = await api.get('/api/admin/settings');
  return res.data;
};

export const updateAdminSettings = async (settingsData: Partial<EventConfig>): Promise<EventConfig> => {
  const res = await api.put('/api/admin/settings', settingsData);
  return res.data;
};

export const testAdminEmail = async (toEmail?: string) => {
  const res = await api.post('/api/admin/test-email', { to_email: toEmail });
  return res.data;
};

export const resendOwnerAlert = async (bookingId: string) => {
  const res = await api.post(`/api/admin/bookings/${bookingId}/resend-owner-alert`);
  return res.data;
};

export const fetchRecentNotifications = async (limit = 10) => {
  const res = await api.get('/api/admin/notifications/recent', { params: { limit } });
  return res.data;
};

export const getExportCSVUrl = (paymentStatus?: string, bookingStatus?: string) => {
  const params = new URLSearchParams();
  if (paymentStatus) params.append('payment_status', paymentStatus);
  if (bookingStatus) params.append('booking_status', bookingStatus);
  return `${API_BASE}/api/admin/export?${params.toString()}`;
};

// Payment Verification & Manual UPI APIs
export const submitManualPaymentProof = async (formData: FormData) => {
  const res = await api.post('/api/payments/submit-manual-proof', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return res.data;
};

export const fetchPendingPaymentVerifications = async (status: string = 'ALL'): Promise<PaymentVerificationItem[]> => {
  const res = await api.get('/api/admin/payments/verification', { params: { status } });
  return res.data;
};

export const approvePaymentVerification = async (bookingId: string) => {
  const res = await api.post(`/api/admin/payments/${bookingId}/approve`);
  return res.data;
};

export const rejectPaymentVerification = async (bookingId: string, reason: string) => {
  const res = await api.post(`/api/admin/payments/${bookingId}/reject`, { reason });
  return res.data;
};

export const uploadUpiQrImage = async (formData: FormData) => {
  const res = await api.post('/api/admin/settings/upload-qr', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return res.data;
};

export const fetchAdminPaymentScreenshotBlobUrl = async (bookingId: string): Promise<string> => {
  const res = await api.get(`/api/admin/payments/${bookingId}/screenshot`, {
    responseType: 'blob',
  });
  return URL.createObjectURL(res.data);
};

// Staff Portal APIs
export const fetchStaffDashboard = async () => {
  const res = await api.get('/api/staff/dashboard');
  return res.data;
};

export const staffVerifyTicket = async (qrToken: string) => {
  const res = await api.post('/api/staff/ticket/verify', { qr_token: qrToken });
  return res.data;
};

export const staffCheckInTicket = async (payload: {
  qr_token: string;
  device_information?: string;
  notes?: string;
}) => {
  const res = await api.post('/api/staff/checkin', payload);
  return res.data;
};

export const staffSearchTickets = async (query: string) => {
  const res = await api.get('/api/staff/search', { params: { q: query } });
  return res.data;
};

export const fetchStaffCheckins = async (limit = 50) => {
  const res = await api.get('/api/staff/checkins', { params: { limit } });
  return res.data;
};


