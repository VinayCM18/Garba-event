export interface EventConfig {
  event_name: string;
  event_tagline: string;
  event_date: string;
  event_time: string;
  venue_name: string;
  venue_address: string;
  venue_city: string;
  ticket_price: number;
  convenience_fee: number;
  total_capacity: number;
  remaining_tickets: number;
  sold_tickets: number;
  max_per_booking: number;
  booking_open: boolean;
  contact_email: string;
  contact_phone: string;
  rules_text: string;
  
  // Group Offer Configuration
  group_offer_enabled?: boolean;
  group_offer_size?: number;
  group_offer_free_tickets?: number;
  group_offer_discount?: number;
  group_offer_regular_total?: number;
  group_offer_subtotal?: number;

  // Payment Method & Manual UPI Configuration
  payment_method?: 'UPI_MANUAL' | 'RAZORPAY' | string;
  upi_id?: string;
  upi_qr_image?: string;
  upi_qr_image_url?: string;
  upi_payment_instructions?: string;

  // Email Delivery & Notification Configuration
  email_provider?: 'smtp' | 'resend' | string;
  resend_api_key?: string;
  resend_api_key_set?: boolean;
  owner_notification_email?: string;
  owner_notification_phone?: string;
  owner_notification_enabled?: boolean;
  owner_webhook_url?: string;
  smtp_host?: string;
  smtp_port?: number;
  smtp_username?: string;
  smtp_password?: string;
  smtp_password_set?: boolean;
  smtp_from_email?: string;
  smtp_from_name?: string;
  smtp_use_tls?: boolean;

  // Razorpay Payment Gateway
  razorpay_key_id?: string;
  razorpay_key_secret?: string;
  razorpay_webhook_secret?: string;
  razorpay_key_secret_set?: boolean;
  razorpay_webhook_secret_set?: boolean;

  // Collaboration & Phases
  collaboration_name?: string;
  collaboration_logo_url?: string;
  active_phase_code?: string;
  ticket_phases?: TicketPhaseItem[];
  offers?: TicketOffer[];
}

export interface TicketOffer {
  id: string;
  phase_code: string;
  phase_name: string;
  phase_status: 'ACTIVE' | 'LOCKED' | 'COMING_SOON';
  type: 'STAG' | 'GROUP' | 'COUPLE' | 'KIDS';
  title: string;
  price: number;
  per_unit_passes: number;
  description: string;
  badge: string;
  is_purchasable: boolean;
  requires_id_proof?: boolean;
  min_age?: number;
  max_age?: number;
}

export interface TicketPhaseItem {
  id?: number;
  phase_code: string;
  name: string;
  price: number;
  tax_included: boolean;
  status: 'ACTIVE' | 'LOCKED' | 'SOLD_OUT' | 'UPCOMING';
  total_inventory: number;
  sold_count: number;
  remaining_inventory?: number;
  remaining_tickets?: number;
  display_order: number;
  badge_text?: string;
  description?: string;
  group_offer_eligible?: boolean;
}

export interface Ticket {
  ticket_id: string;
  booking_id: string;
  customer_name: string;
  event_name: string;
  ticket_type?: string;
  ticket_status: 'VALID' | 'USED' | 'CANCELLED' | 'REFUNDED';
  checkin_status: boolean;
  checked_in_at: string | null;
  created_at: string;
  qr_token_raw?: string;
  qr_code_base64?: string;
  ticket_url?: string;
}

export interface Booking {
  id: number;
  booking_id: string;
  customer_name: string;
  email: string;
  phone: string;
  ticket_count: number;
  ticket_price: number;
  regular_amount?: number;
  group_discount?: number;
  ticket_subtotal?: number;
  convenience_fee: number;
  payment_fee?: number;
  gst_amount?: number;
  amount: number;
  currency: string;
  is_group_offer?: boolean;
  offer_name?: string;
  offer_id?: string;
  offer_title?: string;
  child_name?: string;
  child_age?: number;
  ticket_phase?: string;
  payment_method?: string;
  utr_number?: string;
  payment_screenshot?: string;
  verified_by?: string;
  verified_at?: string;
  rejection_reason?: string;
  razorpay_order_id?: string | null;
  razorpay_payment_id?: string | null;
  payment_status: 'PENDING' | 'VERIFICATION_PENDING' | 'AUTHORIZED' | 'PAID' | 'FAILED' | 'REJECTED' | 'REFUNDED' | 'CANCELLED' | string;
  booking_status: 'PAYMENT_PENDING' | 'PAYMENT_VERIFICATION_PENDING' | 'CONFIRMED' | 'PAYMENT_FAILED' | 'CANCELLED' | 'PENDING' | string;
  email_status: 'PENDING' | 'SENT' | 'FAILED' | 'NOT_CONFIGURED';
  email_sent_at: string | null;
  email_error?: string | null;
  owner_notified?: boolean;
  owner_notified_at?: string | null;
  owner_notify_error?: string | null;
  created_at: string;
  tickets: Ticket[];
}

export interface PaymentVerificationItem {
  id: number;
  booking_id: string;
  customer_name: string;
  phone: string;
  email: string;
  ticket_count: number;
  amount: number;
  currency: string;
  payment_method: string;
  utr_number?: string;
  has_screenshot: boolean;
  payment_screenshot?: string;
  screenshot_url?: string;
  payment_status: string;
  booking_status: string;
  submitted_at?: string;
  verified_by?: string;
  verified_at?: string;
  rejection_reason?: string;
  created_at: string;
}

export interface CreateOrderResponse {
  payment_method: 'UPI_MANUAL' | 'RAZORPAY' | string;
  payment_id?: string;
  booking_id: string;
  amount: number;
  currency: string;
  ticket_price: number;
  ticket_count: number;
  regular_amount: number;
  group_discount: number;
  ticket_subtotal: number;
  payment_fee: number;
  gst_amount: number;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  is_group_offer: boolean;
  offer_name?: string;
  offer_id?: string;
  offer_title?: string;
  passes_count?: number;
  child_name?: string;
  child_age?: number;
  free_tickets: number;
  upi_id?: string;
  upi_qr_image_url?: string;
  upi_payment_instructions?: string;
  razorpay_order_id?: string;
  key_id?: string;
  is_simulation?: boolean;
}

export interface RecentNotification {
  id: number;
  booking_id: string;
  customer_name: string;
  email: string;
  phone: string;
  ticket_count: number;
  amount: number;
  payment_status: string;
  booking_status: string;
  email_status: string;
  owner_notified: boolean;
  created_at: string;
}

export interface AdminDashboardStats {
  tickets_sold: number;
  revenue: number;
  total_bookings: number;
  checked_in: number;
  remaining_tickets: number;
  total_capacity: number;
  checkin_rate_percentage: number;
}

export interface DailyStatItem {
  date: string;
  revenue: number;
  tickets: number;
  bookings: number;
}

export interface HourlyCheckInItem {
  hour: string;
  count: number;
}

export interface DashboardAnalytics {
  stats: AdminDashboardStats;
  sales_trend: DailyStatItem[];
  checkin_trend: HourlyCheckInItem[];
}

export interface CheckInRecord {
  id: number;
  ticket_id: string;
  booking_id: string;
  customer_name: string;
  staff_name?: string;
  result: 'SUCCESS' | 'ALREADY_USED' | 'INVALID' | 'CANCELLED';
  checked_in_at: string;
  ip_address?: string;
  device_information?: string;
}

export interface AuditLogRecord {
  id: number;
  user_email?: string;
  action: string;
  entity_type: string;
  entity_id?: string;
  ip_address?: string;
  user_agent?: string;
  details?: string;
  timestamp: string;
}

export interface AdminUser {
  id: number;
  email: string;
  name: string;
  role: 'SUPER_ADMIN' | 'ADMIN' | 'CHECKIN_STAFF';
  is_active: boolean;
  created_at: string;
}

export interface QRVerifyResult {
  valid: boolean;
  status: 'VALID' | 'USED' | 'INVALID' | 'CANCELLED';
  message: string;
  ticket_id?: string;
  booking_id?: string;
  customer_name?: string;
  event_name?: string;
  ticket_status?: string;
  checkin_status?: boolean;
  checked_in_at?: string;
  qr_token?: string;
  qr_token_raw?: string;
}

export interface CheckInResult {
  success: boolean;
  status: 'SUCCESS' | 'ALREADY_USED' | 'INVALID' | 'CANCELLED';
  message: string;
  ticket_id?: string;
  booking_id?: string;
  customer_name?: string;
  checked_in_at?: string;
  staff_name?: string;
}

export interface StaffRecentCheckIn {
  id: number;
  ticket_id: string;
  customer_name: string;
  checked_in_at: string | null;
  result: string;
  device_information?: string;
}

export interface StaffDashboardStats {
  tickets_expected: number;
  tickets_checked_in: number;
  tickets_remaining: number;
  duplicate_attempts: number;
  checkin_rate_percent: number;
  staff_name: string;
  staff_role: string;
  recent_checkins: StaffRecentCheckIn[];
}

export interface StaffSearchItem {
  ticket_id: string;
  booking_id: string;
  customer_name: string;
  phone?: string;
  ticket_status: string;
  checkin_status: boolean;
  checked_in_at: string | null;
}

