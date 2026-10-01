import React, { useState, useEffect } from 'react';
import {
  Sliders,
  Save,
  RefreshCw,
  AlertCircle,
  ShieldCheck,
  Mail,
  Bell,
  Send,
  CheckCircle2,
  Key,
  Phone,
  Server,
  HelpCircle,
  Eye,
  EyeOff,
  CreditCard,
  Lock,
  QrCode,
  Upload,
  Image as ImageIcon,
  Sparkles,
  Layers
} from 'lucide-react';
import { fetchAdminSettings, updateAdminSettings, testAdminEmail, uploadUpiQrImage } from '../services/api';
import { EventConfig } from '../types';
import { useToast } from '../components/Toast';
import { AdminTicketPhasesCard } from '../components/AdminTicketPhasesCard';

export const AdminSettingsPage: React.FC = () => {
  const { success, error } = useToast();

  const [activeTab, setActiveTab] = useState<'event' | 'notifications' | 'payment' | 'phases'>('phases');
  const [settings, setSettings] = useState<EventConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Password visibility & SMTP Password state
  const [showPassword, setShowPassword] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [showResendKey, setShowResendKey] = useState(false);
  const [newResendKey, setNewResendKey] = useState('');

  // Razorpay credentials state
  const [showRazorpaySecret, setShowRazorpaySecret] = useState(false);
  const [newRazorpaySecret, setNewRazorpaySecret] = useState('');
  const [newRazorpayWebhookSecret, setNewRazorpayWebhookSecret] = useState('');

  // Test Email state
  const [testEmailAddress, setTestEmailAddress] = useState('');
  const [testingEmail, setTestingEmail] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
    details?: string;
  } | null>(null);

  // UPI QR Code Upload state
  const [uploadingQr, setUploadingQr] = useState(false);

  const handleQrUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('qr_file', file);

    setUploadingQr(true);
    try {
      const res = await uploadUpiQrImage(formData);
      if (res.success) {
        success('QR Uploaded', 'New UPI QR code has been saved successfully.');
        handleChange('upi_qr_image', res.qr_image_url);
      } else {
        error('Upload Failed', res.message || 'Could not upload QR code.');
      }
    } catch (err: any) {
      error('Upload Error', err.response?.data?.detail || err.message || 'Failed to upload QR code.');
    } finally {
      setUploadingQr(false);
    }
  };

  const loadSettings = () => {
    setLoading(true);
    fetchAdminSettings()
      .then((data) => {
        setSettings(data);
        setTestEmailAddress(data.owner_notification_email || '');
        setLoading(false);
      })
      .catch((err) => {
        console.error('Error fetching settings:', err);
        setLoading(false);
        error('Fetch Error', 'Failed to retrieve event configuration.');
      });
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const handleChange = (field: keyof EventConfig, value: any) => {
    if (!settings) return;
    setSettings({ ...settings, [field]: value });
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!settings) return;
    setSaving(true);

    try {
      const payload: Partial<EventConfig> = {
        event_name: settings.event_name,
        event_tagline: settings.event_tagline,
        event_date: settings.event_date,
        event_time: settings.event_time,
        venue_name: settings.venue_name,
        venue_address: settings.venue_address,
        venue_city: settings.venue_city,
        ticket_price: Number(settings.ticket_price),
        convenience_fee: Number(settings.convenience_fee),
        total_capacity: Number(settings.total_capacity),
        max_per_booking: Number(settings.max_per_booking),
        booking_open: settings.booking_open,
        contact_email: settings.contact_email,
        contact_phone: settings.contact_phone,
        rules_text: settings.rules_text,

        // Group Offer Promotion Settings
        group_offer_enabled: settings.group_offer_enabled ?? true,
        group_offer_size: Number(settings.group_offer_size) || 10,
        group_offer_free_tickets: Number(settings.group_offer_free_tickets) || 1,

        // Email Delivery & Notification Settings
        email_provider: settings.email_provider || 'resend',
        owner_notification_email: settings.owner_notification_email,
        owner_notification_phone: settings.owner_notification_phone,
        owner_notification_enabled: settings.owner_notification_enabled,
        owner_webhook_url: settings.owner_webhook_url,
        smtp_host: settings.smtp_host,
        smtp_port: Number(settings.smtp_port) || 587,
        smtp_username: settings.smtp_username,
        smtp_from_email: settings.smtp_from_email,
        smtp_from_name: settings.smtp_from_name,
        smtp_use_tls: settings.smtp_use_tls,

        // Payment Architecture & Pluggable Provider
        payment_method: settings.payment_method || 'UPI_MANUAL',
        upi_id: settings.upi_id || '',
        upi_qr_image: settings.upi_qr_image || '/api/payments/qr-image',
        upi_payment_instructions: settings.upi_payment_instructions || 'Scan the QR code using Google Pay, PhonePe, Paytm, or any UPI app. After completing payment, enter your 12-digit UTR number and optionally upload payment screenshot.',

        // Razorpay Payment Gateway
        razorpay_key_id: settings.razorpay_key_id,
      };

      // Only pass password if user typed a new one
      if (newPassword.trim()) {
        payload.smtp_password = newPassword.trim();
      }
      if (newResendKey.trim()) {
        payload.resend_api_key = newResendKey.trim();
      }
      if (newRazorpaySecret.trim()) {
        payload.razorpay_key_secret = newRazorpaySecret.trim();
      }
      if (newRazorpayWebhookSecret.trim()) {
        payload.razorpay_webhook_secret = newRazorpayWebhookSecret.trim();
      }

      const updated = await updateAdminSettings(payload);
      setSettings(updated);
      setNewPassword('');
      setNewResendKey('');
      setNewRazorpaySecret('');
      setNewRazorpayWebhookSecret('');
      success('Settings Updated', 'Event configuration, credentials, and notification rules successfully saved.');
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to update settings. Super admin privileges required.';
      error('Save Failed', msg);
    } finally {
      setSaving(false);
    }
  };

  const handleSendTestEmail = async () => {
    if (!testEmailAddress.trim()) {
      error('Input Required', 'Please enter a recipient email address for testing.');
      return;
    }

    setTestingEmail(true);
    setTestResult(null);

    try {
      const res = await testAdminEmail(testEmailAddress.trim());
      setTestResult({
        success: res.success,
        message: res.message,
        details: res.details,
      });

      if (res.success) {
        success('Test Email Sent', `Verification email dispatched to ${testEmailAddress}!`);
      } else {
        error('SMTP Error', res.message || 'SMTP transmission failed. Please review credentials.');
      }
    } catch (err: any) {
      const msg = err.response?.data?.message || err.response?.data?.detail || err.message || 'Failed to dispatch test email.';
      setTestResult({
        success: false,
        message: msg,
      });
      error('Delivery Error', msg);
    } finally {
      setTestingEmail(false);
    }
  };

  if (loading || !settings) {
    return (
      <div className="py-24 text-center">
        <div className="w-10 h-10 border-3 border-amber-500/30 border-t-amber-400 rounded-full animate-spin mx-auto mb-4" />
        <p className="text-xs text-slate-400">Loading settings...</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-black text-white tracking-wide font-['Outfit'] flex items-center gap-2">
            <Sliders className="w-6 h-6 text-amber-400" />
            <span>Settings & Dispatch Controls</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Configure event parameters, ticket pricing, customer email delivery, and instant owner notifications.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex p-1 rounded-2xl bg-white/[0.05] border border-white/10 self-start sm:self-auto flex-wrap gap-1">
          <button
            type="button"
            onClick={() => setActiveTab('phases')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
              activeTab === 'phases'
                ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Ticket Phases</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('notifications')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
              activeTab === 'notifications'
                ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Bell className="w-3.5 h-3.5" />
            <span>Email & Owner Alerts</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('payment')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
              activeTab === 'payment'
                ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <CreditCard className="w-3.5 h-3.5" />
            <span>Payment Methods &amp; Architecture</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('event')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
              activeTab === 'event'
                ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>Event & Inventory</span>
          </button>
        </div>
      </div>

      {/* Ticket Phases Tab Content */}
      {activeTab === 'phases' && (
        <div className="space-y-6">
          <AdminTicketPhasesCard />
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* ========================================================================= */}
        {/* TAB 1: EMAIL & OWNER ALERTS                                              */}
        {/* ========================================================================= */}
        {activeTab === 'notifications' && (
          <div className="space-y-6">
            {/* Owner Instant Alerts Card */}
            <div className="p-6 sm:p-8 rounded-3xl glass-panel border border-amber-500/20 space-y-5 bg-gradient-to-b from-amber-500/[0.04] to-transparent">
              <div className="flex items-center justify-between border-b border-white/10 pb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                    <Bell className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                      <span>Owner Instant Booking Alerts</span>
                      <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full font-mono font-bold">
                        ACTIVE
                      </span>
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      The owner receives an instant notification message & email whenever any ticket is booked with full details and ticket count.
                    </p>
                  </div>
                </div>

                {/* Toggle switch */}
                <button
                  type="button"
                  onClick={() => handleChange('owner_notification_enabled', !settings.owner_notification_enabled)}
                  className={`w-12 h-7 rounded-full p-1 transition-colors ${
                    settings.owner_notification_enabled ? 'bg-emerald-600' : 'bg-slate-700'
                  }`}
                  title="Toggle instant notifications to owner"
                >
                  <div
                    className={`w-5 h-5 rounded-full bg-white transition-transform ${
                      settings.owner_notification_enabled ? 'translate-x-5' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <Mail className="w-3.5 h-3.5 text-amber-400" />
                    <span>Owner Notification Email</span>
                  </label>
                  <input
                    type="text"
                    value={settings.owner_notification_email || ''}
                    onChange={(e) => handleChange('owner_notification_email', e.target.value)}
                    placeholder="owner@example.com, manager@example.com"
                    className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-xs focus:outline-none focus:border-amber-400"
                  />
                  <p className="text-[11px] text-slate-400 mt-1">
                    Instant alerts for bookings and payment verification are dispatched here. Multiple emails can be comma-separated.
                  </p>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <Phone className="w-3.5 h-3.5 text-amber-400" />
                    <span>Owner Mobile / WhatsApp Number</span>
                  </label>
                  <input
                    type="text"
                    value={settings.owner_notification_phone || ''}
                    onChange={(e) => handleChange('owner_notification_phone', e.target.value)}
                    placeholder="+91 98765 43210"
                    className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-xs focus:outline-none focus:border-amber-400"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">
                    Used for SMS/WhatsApp gateway logs and rapid turnstile support inquiries.
                  </p>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Optional Webhook URL (Discord / Slack / Telegram)
                </label>
                <input
                  type="url"
                  value={settings.owner_webhook_url || ''}
                  onChange={(e) => handleChange('owner_webhook_url', e.target.value)}
                  placeholder="https://discord.com/api/webhooks/... or Slack Incoming Webhook"
                  className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-xs focus:outline-none focus:border-amber-400"
                />
                <p className="text-[11px] text-slate-500 mt-1">
                  Optional: Paste a Discord or Slack channel webhook to receive live ping notifications in your team chat.
                </p>
              </div>
            </div>

            {/* Mail Server & Notification Configuration */}
            <div className="p-6 sm:p-8 rounded-3xl glass-panel border border-white/10 space-y-6">
              <div className="flex items-center gap-3 border-b border-white/10 pb-4">
                <div className="w-10 h-10 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                  <Server className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    Email Delivery & Notification Engine
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Configure Resend API (HTTPS Port 443 — Recommended for Railway) or custom SMTP so tickets, PDF passes, and owner alerts reach inboxes reliably.
                  </p>
                </div>
              </div>

              {/* Provider Selector Tabs */}
              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Select Email Dispatch Provider
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => handleChange('email_provider', 'resend')}
                    className={`p-3.5 rounded-2xl border text-left transition-all cursor-pointer flex flex-col justify-between ${
                      (settings.email_provider || 'resend') === 'resend'
                        ? 'bg-amber-500/10 border-amber-500/50 shadow-lg shadow-amber-500/10 ring-1 ring-amber-500/30'
                        : 'bg-black/30 border-white/10 hover:border-white/20'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Sparkles className={`w-4 h-4 ${(settings.email_provider || 'resend') === 'resend' ? 'text-amber-400' : 'text-slate-400'}`} />
                        <span className="text-xs font-bold text-white">Resend API</span>
                      </div>
                      <span className="text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 rounded-full font-bold">
                        Cloud / Railway Ready
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-2">
                      Operates over HTTPS (Port 443). Bypasses Railway's SMTP port 587 block completely. Free 100 emails/day.
                    </p>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleChange('email_provider', 'smtp')}
                    className={`p-3.5 rounded-2xl border text-left transition-all cursor-pointer flex flex-col justify-between ${
                      settings.email_provider === 'smtp'
                        ? 'bg-amber-500/10 border-amber-500/50 shadow-lg shadow-amber-500/10 ring-1 ring-amber-500/30'
                        : 'bg-black/30 border-white/10 hover:border-white/20'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Server className={`w-4 h-4 ${settings.email_provider === 'smtp' ? 'text-amber-400' : 'text-slate-400'}`} />
                        <span className="text-xs font-bold text-white">Standard SMTP / Gmail</span>
                      </div>
                      <span className="text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded-full font-bold">
                        Port 587 / 465 / 2525
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-2">
                      Connect your Gmail or SMTP relay. Note: Railway blocks outbound ports 587/465 to prevent spam.
                    </p>
                  </button>
                </div>
              </div>

              {/* Status Indicator */}
              <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span
                    className={`w-3 h-3 rounded-full ${
                      (settings.email_provider || 'resend') === 'resend'
                        ? (settings.resend_api_key_set || newResendKey)
                          ? 'bg-emerald-400 animate-pulse'
                          : 'bg-amber-400'
                        : settings.smtp_username && (settings.smtp_password_set || newPassword)
                          ? 'bg-emerald-400 animate-pulse'
                          : 'bg-amber-400'
                    }`}
                  />
                  <div className="text-xs font-semibold text-slate-200">
                    {(settings.email_provider || 'resend') === 'resend' ? (
                      settings.resend_api_key_set || newResendKey ? (
                        <span className="text-emerald-400">
                          Resend API Configured & Ready (Bypasses Railway SMTP Restrictions via Port 443 HTTPS)
                        </span>
                      ) : (
                        <span className="text-amber-400">
                          Resend API Key Missing — Enter your free key below to enable reliable cloud email delivery.
                        </span>
                      )
                    ) : settings.smtp_username && (settings.smtp_password_set || newPassword) ? (
                      <span className="text-emerald-400">
                        SMTP Configured (Sender: {settings.smtp_username})
                      </span>
                    ) : (
                      <span className="text-amber-400">
                        SMTP Credentials Incomplete — Please configure Gmail App Password below.
                      </span>
                    )}
                  </div>
                </div>

                {((settings.email_provider || 'resend') === 'resend' ? settings.resend_api_key_set : settings.smtp_password_set) && (
                  <span className="text-[11px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2.5 py-1 rounded-full font-mono">
                    ✓ Key Encrypted & Stored
                  </span>
                )}
              </div>

              {/* RESEND API CONFIGURATION FIELDS */}
              {(settings.email_provider || 'resend') === 'resend' ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="sm:col-span-2">
                      <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center justify-between">
                        <span className="flex items-center gap-1.5">
                          <Key className="w-3.5 h-3.5 text-amber-400" />
                          <span>Resend API Key (re_...)</span>
                        </span>
                        {settings.resend_api_key_set && (
                          <span className="text-[10px] text-emerald-400 font-normal">
                            (Leave empty to keep existing key)
                          </span>
                        )}
                      </label>
                      <div className="relative">
                        <input
                          type={showResendKey ? 'text' : 'password'}
                          value={newResendKey}
                          onChange={(e) => setNewResendKey(e.target.value)}
                          placeholder={settings.resend_api_key_set ? '•••••••••••••••••••••••• (saved)' : 're_xxxxxxxxxxxxxxxxxxxx'}
                          className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-xs focus:outline-none focus:border-amber-400 font-mono tracking-wider pr-10"
                        />
                        <button
                          type="button"
                          onClick={() => setShowResendKey(!showResendKey)}
                          className="absolute right-3 top-2.5 text-slate-400 hover:text-white"
                        >
                          {showResendKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                      <p className="text-[11px] text-amber-400/80 mt-1">
                        Get your free API key at <a href="https://resend.com" target="_blank" rel="noopener noreferrer" className="underline font-bold">resend.com</a> (100 free emails/day, no credit card required).
                      </p>
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                        Sender From Name
                      </label>
                      <input
                        type="text"
                        value={settings.smtp_from_name || 'NAVRANG 2026'}
                        onChange={(e) => handleChange('smtp_from_name', e.target.value)}
                        placeholder="NAVRANG 2026"
                        className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-xs focus:outline-none focus:border-amber-400"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                        Sender From Email Address
                      </label>
                      <input
                        type="email"
                        value={settings.smtp_from_email || 'onboarding@resend.dev'}
                        onChange={(e) => handleChange('smtp_from_email', e.target.value)}
                        placeholder="onboarding@resend.dev"
                        className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-xs focus:outline-none focus:border-amber-400"
                      />
                      <p className="text-[11px] text-slate-500 mt-1">
                        Use <code className="text-amber-300 font-mono">onboarding@resend.dev</code> for testing or enter your verified Resend domain address.
                      </p>
                    </div>
                  </div>

                  {/* Resend Setup Instructions Guide */}
                  <div className="p-4 rounded-2xl bg-amber-500/[0.05] border border-amber-500/20 text-xs text-slate-300 space-y-2">
                    <div className="font-bold text-amber-400 flex items-center gap-1.5">
                      <HelpCircle className="w-4 h-4" />
                      <span>How to setup Resend in 30 seconds (Bypasses Railway Errno 101):</span>
                    </div>
                    <ol className="list-decimal list-inside space-y-1 text-slate-300 text-[11px] pl-1 leading-relaxed">
                      <li>Open <a href="https://resend.com" target="_blank" rel="noopener noreferrer" className="text-amber-400 underline font-semibold">resend.com</a> and sign up for a free account.</li>
                      <li>In the dashboard, click <strong>API Keys</strong> &rarr; <strong>Create API Key</strong>.</li>
                      <li>Copy the key (starts with <code className="text-amber-300 font-mono">re_</code>) and paste it into the <strong>Resend API Key</strong> field above.</li>
                      <li>Click <strong>&ldquo;Save Event Settings&rdquo;</strong> below, then click <strong>&ldquo;Send Test Email Now&rdquo;</strong> to verify!</li>
                      <li>(Optional) Add and verify your custom domain in Resend to send from your own domain email address.</li>
                    </ol>
                  </div>
                </div>
              ) : (
                /* SMTP CONFIGURATION FIELDS */
                <div className="space-y-4">
                  {/* Railway Port Block Notice */}
                  <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 space-y-1">
                    <div className="font-bold text-rose-400 flex items-center gap-1.5">
                      <AlertCircle className="w-4 h-4" />
                      <span>Important Railway Cloud Notice:</span>
                    </div>
                    <p className="text-[11px] text-rose-200 leading-relaxed">
                      Railway and other cloud container platforms block outbound TCP connections on ports <strong>587</strong> and <strong>465</strong> at the network firewall level to prevent spam. This produces <em>[Errno 101] Network is unreachable</em> when connecting to Gmail. To deliver emails on Railway without restrictions, switch to <strong>Resend API</strong> above!
                    </p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                        SMTP Server Host
                      </label>
                      <input
                        type="text"
                        value={settings.smtp_host || 'smtp.gmail.com'}
                        onChange={(e) => handleChange('smtp_host', e.target.value)}
                        placeholder="smtp.gmail.com"
                        className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-xs focus:outline-none focus:border-amber-400"
                      />
                      <p className="text-[11px] text-slate-500 mt-1">Default for Gmail: smtp.gmail.com</p>
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                        SMTP Port
                      </label>
                      <input
                        type="number"
                        value={settings.smtp_port || 587}
                        onChange={(e) => handleChange('smtp_port', Number(e.target.value))}
                        placeholder="587"
                        className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-xs focus:outline-none focus:border-amber-400 font-mono"
                      />
                      <p className="text-[11px] text-slate-500 mt-1">Port 587 for TLS, 465 for SSL, or 2525 for relays.</p>
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                        SMTP Username / Email
                      </label>
                      <input
                        type="text"
                        value={settings.smtp_username || ''}
                        onChange={(e) => handleChange('smtp_username', e.target.value)}
                        placeholder="your-email@gmail.com"
                        className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-xs focus:outline-none focus:border-amber-400"
                      />
                      <p className="text-[11px] text-slate-500 mt-1">Your full Gmail address or SMTP login.</p>
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center justify-between">
                        <span className="flex items-center gap-1.5">
                          <Key className="w-3.5 h-3.5 text-amber-400" />
                          <span>SMTP Password / App Password</span>
                        </span>
                        {settings.smtp_password_set && (
                          <span className="text-[10px] text-emerald-400 font-normal">
                            (Leave empty to keep existing password)
                          </span>
                        )}
                      </label>
                      <div className="relative">
                        <input
                          type={showPassword ? 'text' : 'password'}
                          value={newPassword}
                          onChange={(e) => setNewPassword(e.target.value)}
                          placeholder={settings.smtp_password_set ? '•••••••••••••••• (saved)' : '16-character App Password'}
                          className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-xs focus:outline-none focus:border-amber-400 font-mono tracking-wider pr-10"
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute right-3 top-2.5 text-slate-400 hover:text-white"
                        >
                          {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                      <p className="text-[11px] text-amber-400/80 mt-1">
                        For Gmail, use a 16-character Google App Password (not your standard password).
                      </p>
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                        Sender From Name
                      </label>
                      <input
                        type="text"
                        value={settings.smtp_from_name || 'NAVRANG 2026'}
                        onChange={(e) => handleChange('smtp_from_name', e.target.value)}
                        placeholder="NAVRANG 2026"
                        className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-xs focus:outline-none focus:border-amber-400"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                        Sender From Email Address
                      </label>
                      <input
                        type="email"
                        value={settings.smtp_from_email || 'tickets@navrang.in'}
                        onChange={(e) => handleChange('smtp_from_email', e.target.value)}
                        placeholder="tickets@navrang.in"
                        className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-xs focus:outline-none focus:border-amber-400"
                      />
                    </div>
                  </div>

                  {/* Gmail App Password Guide */}
                  <div className="p-4 rounded-2xl bg-amber-500/[0.05] border border-amber-500/20 text-xs text-slate-300 space-y-2">
                    <div className="font-bold text-amber-400 flex items-center gap-1.5">
                      <HelpCircle className="w-4 h-4" />
                      <span>How to generate a Gmail App Password (Takes 60 seconds):</span>
                    </div>
                    <ol className="list-decimal list-inside space-y-1 text-slate-300 text-[11px] pl-1 leading-relaxed">
                      <li>
                        Open your Google Account at{' '}
                        <a
                          href="https://myaccount.google.com/security"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-amber-400 underline font-semibold"
                        >
                          myaccount.google.com/security
                        </a>
                      </li>
                      <li>Ensure <strong>2-Step Verification</strong> is switched ON.</li>
                      <li>In the top search bar, type <strong>&ldquo;App passwords&rdquo;</strong> and select it.</li>
                      <li>Enter an app name (e.g. <em>&ldquo;NAVRANG&rdquo;</em>) and click <strong>Create</strong>.</li>
                      <li>Copy the 16-character code (without spaces) and paste it into the <strong>SMTP Password</strong> field above.</li>
                      <li>Click <strong>&ldquo;Save Event Settings&rdquo;</strong> below, then test below!</li>
                    </ol>
                  </div>
                </div>
              )}

              {/* Test Email Dispatch Section */}
              <div className="pt-4 border-t border-white/10">
                <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <Send className="w-3.5 h-3.5 text-amber-400" />
                  <span>Send Test Verification Email</span>
                </h4>
                <p className="text-[11px] text-slate-400 mb-3">
                  Dispatches a live verification test email from the server right now to confirm your inbox receives messages.
                </p>

                <div className="flex flex-col sm:flex-row items-center gap-3">
                  <input
                    type="email"
                    value={testEmailAddress}
                    onChange={(e) => setTestEmailAddress(e.target.value)}
                    placeholder="Enter recipient email address"
                    className="w-full sm:flex-1 px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-xs focus:outline-none focus:border-amber-400 font-mono"
                  />
                  <button
                    type="button"
                    onClick={handleSendTestEmail}
                    className="festive-button w-full sm:w-auto px-5 py-2.5 rounded-xl font-bold text-xs flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer shadow-md shadow-[#d4af37]/20"
                  >
                    {testingEmail ? (
                      <>
                        <div className="w-3.5 h-3.5 border-2 border-slate-950/30 border-t-slate-950 rounded-full animate-spin" />
                        <span>Transmitting...</span>
                      </>
                    ) : (
                      <>
                        <Send className="w-3.5 h-3.5" />
                        <span>Send Test Email Now</span>
                      </>
                    )}
                  </button>
                </div>

                {/* Test Result Message Box */}
                {testResult && (
                  <div
                    className={`mt-4 p-4 rounded-xl border text-xs leading-relaxed ${
                      testResult.success
                        ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                        : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      {testResult.success ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                      )}
                      <div>
                        <div className="font-bold whitespace-pre-line leading-relaxed">{testResult.message}</div>
                        {testResult.details && (
                          <div className="text-[11px] font-mono mt-1 opacity-80 break-all">
                            {testResult.details}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 2: EVENT DETAILS & INVENTORY                                          */}
        {/* ========================================================================= */}
        {activeTab === 'event' && (
          <div className="p-6 sm:p-8 rounded-3xl glass-panel border border-white/10 space-y-6">
            {/* Booking Open / Closed Switch */}
            <div className="p-4 rounded-2xl bg-white/[0.03] border border-white/5 flex items-center justify-between">
              <div>
                <div className="text-sm font-bold text-white">Public Ticket Booking Portal</div>
                <div className="text-xs text-slate-400 mt-0.5">
                  Toggle whether customers can initiate new ticket bookings online.
                </div>
              </div>
              <button
                type="button"
                onClick={() => handleChange('booking_open', !settings.booking_open)}
                className={`w-14 h-8 rounded-full p-1 transition-colors ${
                  settings.booking_open ? 'bg-emerald-600' : 'bg-slate-700'
                }`}
              >
                <div
                  className={`w-6 h-6 rounded-full bg-white transition-transform ${
                    settings.booking_open ? 'translate-x-6' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>

            {/* Basic Event Info */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Event Title
                </label>
                <input
                  type="text"
                  value={settings.event_name}
                  onChange={(e) => handleChange('event_name', e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-xs focus:outline-none focus:border-amber-400"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Event Tagline
                </label>
                <input
                  type="text"
                  value={settings.event_tagline}
                  onChange={(e) => handleChange('event_tagline', e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-xs focus:outline-none focus:border-amber-400"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Event Date
                </label>
                <input
                  type="text"
                  value={settings.event_date}
                  onChange={(e) => handleChange('event_date', e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-xs focus:outline-none focus:border-amber-400"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Event Timing
                </label>
                <input
                  type="text"
                  value={settings.event_time}
                  onChange={(e) => handleChange('event_time', e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-xs focus:outline-none focus:border-amber-400"
                />
              </div>
            </div>

            {/* Pricing & Capacity Safeguards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-white/5">
              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Ticket Price (₹ INR)
                </label>
                <input
                  type="number"
                  min="0"
                  value={settings.ticket_price}
                  onChange={(e) => handleChange('ticket_price', e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-amber-400 font-mono font-bold text-xs focus:outline-none focus:border-amber-400"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Total Ticket Capacity
                </label>
                <input
                  type="number"
                  min="10"
                  value={settings.total_capacity}
                  onChange={(e) => handleChange('total_capacity', e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white font-mono text-xs focus:outline-none focus:border-amber-400"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Max Tickets Per Booking
                </label>
                <input
                  type="number"
                  min="1"
                  max="50"
                  value={settings.max_per_booking}
                  onChange={(e) => handleChange('max_per_booking', e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white font-mono text-xs focus:outline-none focus:border-amber-400"
                />
              </div>
            </div>

            {/* Promotional Group Offer Configuration (BUY X, PAY FOR Y) */}
            <div className="p-5 sm:p-6 rounded-2xl bg-gradient-to-br from-amber-500/[0.07] via-[#1a1429] to-purple-900/[0.05] border border-amber-500/30 space-y-4">
              <div className="flex items-center justify-between border-b border-amber-500/20 pb-3">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-300">
                    <Sparkles className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                      <span>Promotional Group Offer Settings</span>
                      <span className="text-[10px] bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded-full font-mono font-bold">
                        BUY {settings.group_offer_size || 10}, PAY FOR {(settings.group_offer_size || 10) - (settings.group_offer_free_tickets || 1)}
                      </span>
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Configure group promotion rules. Customers booking this exact squad size get free tickets automatically.
                    </p>
                  </div>
                </div>

                {/* Group Offer Toggle Switch */}
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-300 hidden sm:inline">
                    {settings.group_offer_enabled ? 'OFFER ON' : 'OFFER OFF'}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleChange('group_offer_enabled', !settings.group_offer_enabled)}
                    className={`w-12 h-7 rounded-full p-1 transition-colors ${
                      settings.group_offer_enabled ? 'bg-amber-500' : 'bg-slate-700'
                    }`}
                    title="Toggle Group Offer"
                  >
                    <div
                      className={`w-5 h-5 rounded-full bg-white transition-transform ${
                        settings.group_offer_enabled ? 'translate-x-5' : 'translate-x-0'
                      }`}
                    />
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                    Group Size (Tickets)
                  </label>
                  <input
                    type="number"
                    min="2"
                    max="50"
                    value={settings.group_offer_size ?? 10}
                    onChange={(e) => handleChange('group_offer_size', Number(e.target.value))}
                    className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white font-mono font-bold text-xs focus:outline-none focus:border-amber-400"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">Exact quantity required to unlock the offer (default: 10).</p>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                    Free Tickets
                  </label>
                  <input
                    type="number"
                    min="1"
                    max={Math.max(1, (settings.group_offer_size || 10) - 1)}
                    value={settings.group_offer_free_tickets ?? 1}
                    onChange={(e) => handleChange('group_offer_free_tickets', Number(e.target.value))}
                    className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-emerald-400 font-mono font-bold text-xs focus:outline-none focus:border-amber-400"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">Number of tickets given free of cost (default: 1).</p>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                    Regular Ticket Price
                  </label>
                  <div className="w-full px-4 py-2.5 rounded-xl bg-black/60 border border-white/10 text-slate-300 font-mono text-xs flex items-center justify-between">
                    <span>₹{Number(settings.ticket_price || 599).toLocaleString('en-IN')}</span>
                    <span className="text-[10px] text-amber-400 font-sans">Synced with Base Price</span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1">Edit in "Ticket Price" above to update globally.</p>
                </div>
              </div>

              {/* Automatically Calculated Breakdown Banner */}
              {(() => {
                const groupSize = Number(settings.group_offer_size) || 10;
                const freeCount = Number(settings.group_offer_free_tickets) || 1;
                const price = Number(settings.ticket_price) || 599;
                const regTotal = groupSize * price;
                const discount = freeCount * price;
                const subtotal = Math.max(0, regTotal - discount);
                const paidCount = Math.max(0, groupSize - freeCount);

                return (
                  <div className="p-3.5 rounded-xl bg-black/50 border border-amber-500/20 text-xs">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-bold text-amber-400 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                        Live Automatic Calculation
                      </span>
                      <span className="text-[10px] font-mono uppercase bg-amber-500/10 text-amber-300 px-2 py-0.5 rounded border border-amber-500/20">
                        {settings.group_offer_enabled ? 'Active Promotion' : 'Promotion Disabled'}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-slate-300 font-mono">
                      <div className="p-2 rounded-lg bg-white/[0.02]">
                        <div className="text-[10px] font-sans text-slate-500 uppercase">Offer Formula</div>
                        <div className="font-bold text-white mt-0.5">BUY {groupSize}, PAY {paidCount}</div>
                      </div>
                      <div className="p-2 rounded-lg bg-white/[0.02]">
                        <div className="text-[10px] font-sans text-slate-500 uppercase">Regular ({groupSize} × ₹{price})</div>
                        <div className="text-slate-400 line-through mt-0.5">₹{regTotal.toLocaleString('en-IN')}</div>
                      </div>
                      <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                        <div className="text-[10px] font-sans text-emerald-400 uppercase font-bold">Offer Discount ({freeCount} Free)</div>
                        <div className="text-emerald-300 font-bold mt-0.5">-₹{discount.toLocaleString('en-IN')}</div>
                      </div>
                      <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20">
                        <div className="text-[10px] font-sans text-amber-400 uppercase font-bold">Customer Subtotal</div>
                        <div className="text-amber-300 font-bold mt-0.5">₹{subtotal.toLocaleString('en-IN')}</div>
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>

            {/* Venue Information */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-white/5">
              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Venue Name
                </label>
                <input
                  type="text"
                  value={settings.venue_name || ''}
                  onChange={(e) => handleChange('venue_name', e.target.value)}
                  placeholder="The Green Acres"
                  className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-xs focus:outline-none focus:border-amber-400"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Venue City
                </label>
                <input
                  type="text"
                  value={settings.venue_city || ''}
                  onChange={(e) => handleChange('venue_city', e.target.value)}
                  placeholder="Mysuru"
                  className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-xs focus:outline-none focus:border-amber-400"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Venue Address
                </label>
                <input
                  type="text"
                  value={settings.venue_address || ''}
                  onChange={(e) => handleChange('venue_address', e.target.value)}
                  placeholder="The Green Acres, Mysuru"
                  className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-xs focus:outline-none focus:border-amber-400"
                />
              </div>
            </div>

            {/* Contact info */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-white/5">
              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Support Email
                </label>
                <input
                  type="email"
                  value={settings.contact_email}
                  onChange={(e) => handleChange('contact_email', e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-xs focus:outline-none focus:border-amber-400"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Helpline Phone
                </label>
                <input
                  type="text"
                  value={settings.contact_phone}
                  onChange={(e) => handleChange('contact_phone', e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-xs focus:outline-none focus:border-amber-400"
                />
              </div>
            </div>

            {/* Rules text */}
            <div className="pt-4 border-t border-white/5">
              <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                Event Rules & Entry Guidelines Text
              </label>
              <textarea
                rows={4}
                value={settings.rules_text}
                onChange={(e) => handleChange('rules_text', e.target.value)}
                className="w-full p-3 rounded-xl bg-black/40 border border-white/10 text-white text-xs leading-relaxed focus:outline-none focus:border-amber-400"
              />
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 3: PAYMENT ARCHITECTURE & GATEWAYS                                    */}
        {/* ========================================================================= */}
        {activeTab === 'payment' && (
          <div className="space-y-6">
            {/* Payment Method Selector Card */}
            <div className="p-6 sm:p-8 rounded-3xl glass-panel border border-white/10 space-y-6">
              <div className="border-b border-white/10 pb-4">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <CreditCard className="w-5 h-5 text-amber-400" />
                  <span>Active Payment Provider Architecture</span>
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  Choose the active payment method. The booking engine, ticket generator, and QR verification remain decoupled and work seamlessly with either provider.
                </p>
              </div>

              {/* Provider Selection Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Option 1: Manual UPI */}
                <div
                  onClick={() => handleChange('payment_method', 'UPI_MANUAL')}
                  className={`p-5 rounded-2xl border transition-all cursor-pointer relative overflow-hidden ${
                    (settings.payment_method || 'UPI_MANUAL') === 'UPI_MANUAL'
                      ? 'bg-amber-500/10 border-amber-500/50 shadow-lg shadow-amber-500/10'
                      : 'bg-white/[0.02] border-white/10 hover:border-white/20'
                  }`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2.5">
                      <div className="w-9 h-9 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center font-bold">
                        <QrCode className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="text-sm font-bold text-white">UPI Manual (QR Code)</div>
                        <div className="text-[10px] text-amber-400 font-semibold">INITIAL VERSION (CURRENT)</div>
                      </div>
                    </div>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold ${
                      (settings.payment_method || 'UPI_MANUAL') === 'UPI_MANUAL'
                        ? 'bg-amber-500 text-slate-950'
                        : 'bg-white/10 text-slate-400'
                    }`}>
                      {(settings.payment_method || 'UPI_MANUAL') === 'UPI_MANUAL' ? 'ACTIVE' : 'SELECT'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Customer scans your personalized UPI QR code via GPay / PhonePe / Paytm, submits UTR &amp; screenshot. Admin verifies and approves. 0% gateway fee.
                  </p>
                </div>

                {/* Option 2: Razorpay */}
                <div
                  onClick={() => handleChange('payment_method', 'RAZORPAY')}
                  className={`p-5 rounded-2xl border transition-all cursor-pointer relative overflow-hidden ${
                    settings.payment_method === 'RAZORPAY'
                      ? 'bg-blue-500/10 border-blue-500/50 shadow-lg shadow-blue-500/10'
                      : 'bg-white/[0.02] border-white/10 hover:border-white/20'
                  }`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2.5">
                      <div className="w-9 h-9 rounded-xl bg-blue-500/20 text-blue-400 flex items-center justify-center font-bold">
                        <CreditCard className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="text-sm font-bold text-white">Razorpay Gateway</div>
                        <div className="text-[10px] text-blue-400 font-semibold">AUTOMATED CHECKOUT</div>
                      </div>
                    </div>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold ${
                      settings.payment_method === 'RAZORPAY'
                        ? 'bg-blue-500 text-white'
                        : 'bg-white/10 text-slate-400'
                    }`}>
                      {settings.payment_method === 'RAZORPAY' ? 'ACTIVE' : 'SWITCH'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Automated credit/debit card, netbanking, and UPI gateway. Instant webhook verification without manual admin approval required.
                  </p>
                </div>
              </div>
            </div>

            {/* UPI Manual Configuration */}
            {(settings.payment_method || 'UPI_MANUAL') === 'UPI_MANUAL' && (
              <div className="p-6 sm:p-8 rounded-3xl glass-panel border border-amber-500/20 space-y-6 bg-gradient-to-b from-amber-500/[0.03] to-transparent">
                <div className="flex items-center justify-between border-b border-white/10 pb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                      <QrCode className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                        <span>Manual UPI QR Code &amp; Checkout Settings</span>
                        <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full font-mono font-bold">
                          CONFIGURED
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Set your receiving UPI ID, upload QR code image, and specify customer payment instructions.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  {/* UPI ID */}
                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                        Receiving UPI ID
                      </label>
                      <input
                        type="text"
                        value={settings.upi_id || ''}
                        onChange={(e) => handleChange('upi_id', e.target.value)}
                        placeholder="e.g. yourname@upi"
                        className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white font-mono text-xs focus:outline-none focus:border-amber-400"
                      />
                      <p className="text-[11px] text-slate-500 mt-1">
                        Displayed to customers so they can copy and pay directly in GPay, PhonePe, Paytm, or BHIM.
                      </p>
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                        Customer Payment Instructions
                      </label>
                      <textarea
                        rows={4}
                        value={settings.upi_payment_instructions || ''}
                        onChange={(e) => handleChange('upi_payment_instructions', e.target.value)}
                        placeholder="Enter instructions shown to customer at checkout..."
                        className="w-full p-3 rounded-xl bg-black/40 border border-white/10 text-white text-xs leading-relaxed focus:outline-none focus:border-amber-400"
                      />
                    </div>
                  </div>

                  {/* QR Image Preview & Uploader */}
                  <div className="space-y-4">
                    <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                      UPI QR Code Image
                    </label>

                    <div className="flex flex-col sm:flex-row items-center gap-4 p-4 rounded-2xl bg-black/50 border border-white/10">
                      <div className="w-32 h-32 rounded-xl bg-white p-2 shrink-0 shadow-lg flex items-center justify-center overflow-hidden">
                        <img
                          src={settings.upi_qr_image || '/api/payments/qr-image'}
                          alt="UPI QR Code"
                          className="w-full h-full object-contain"
                          onError={(e) => {
                            (e.target as HTMLImageElement).src = '/upi_qr_code.jpg';
                          }}
                        />
                      </div>

                      <div className="space-y-2 flex-1 text-center sm:text-left">
                        <div className="text-xs font-bold text-white">Active QR Code Image</div>
                        <div className="text-[11px] font-mono text-slate-400 break-all">
                          {settings.upi_qr_image || '/api/payments/qr-image'}
                        </div>

                        <label className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs cursor-pointer shadow-md transition-all">
                          {uploadingQr ? (
                            <div className="w-3.5 h-3.5 border-2 border-slate-950/30 border-t-slate-950 rounded-full animate-spin" />
                          ) : (
                            <Upload className="w-3.5 h-3.5" />
                          )}
                          <span>Upload New QR Image</span>
                          <input
                            type="file"
                            accept="image/png,image/jpeg,image/webp"
                            onChange={handleQrUpload}
                            disabled={uploadingQr}
                            className="hidden"
                          />
                        </label>
                        <p className="text-[10px] text-slate-500">
                          Supports PNG, JPG, WebP up to 5MB.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Razorpay Gateway Configuration */}
            <div className={`p-6 sm:p-8 rounded-3xl glass-panel border border-white/10 space-y-6 ${
              settings.payment_method === 'RAZORPAY' ? 'bg-gradient-to-b from-blue-500/[0.03] to-transparent' : 'opacity-80'
            }`}>
              <div className="flex items-center justify-between border-b border-white/10 pb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                    <CreditCard className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                      <span>Razorpay Payment Gateway Credentials</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-bold ${
                        settings.razorpay_key_id && !settings.razorpay_key_id.includes('placeholder')
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                      }`}>
                        {settings.razorpay_key_id && !settings.razorpay_key_id.includes('placeholder') ? 'LIVE / REALTIME' : 'SIMULATION / TEST'}
                      </span>
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Configure your Razorpay API keys for future automated switch.
                    </p>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <Key className="w-3.5 h-3.5 text-amber-400" />
                    <span>Razorpay Key ID</span>
                  </label>
                  <input
                    type="text"
                    value={settings.razorpay_key_id || ''}
                    onChange={(e) => handleChange('razorpay_key_id', e.target.value)}
                    placeholder="rzp_live_... or rzp_test_..."
                    className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-xs font-mono focus:outline-none focus:border-amber-400"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">
                    Public Key ID from your Razorpay Dashboard (API Keys &gt; Generate Key).
                  </p>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <Lock className="w-3.5 h-3.5 text-amber-400" />
                      <span>Razorpay Key Secret</span>
                    </span>
                    {settings.razorpay_key_secret_set && (
                      <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                        ✓ Configured in DB/Env
                      </span>
                    )}
                  </label>
                  <div className="relative">
                    <input
                      type={showRazorpaySecret ? 'text' : 'password'}
                      value={newRazorpaySecret}
                      onChange={(e) => setNewRazorpaySecret(e.target.value)}
                      placeholder={settings.razorpay_key_secret_set ? '•••••••••••••••• (Leave blank to keep existing)' : 'Enter Razorpay Key Secret'}
                      className="w-full px-4 py-2.5 pr-10 rounded-xl bg-black/40 border border-white/10 text-white text-xs font-mono focus:outline-none focus:border-amber-400"
                    />
                    <button
                      type="button"
                      onClick={() => setShowRazorpaySecret(!showRazorpaySecret)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
                    >
                      {showRazorpaySecret ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Keep your Key Secret private. Used for cryptographically signing and verifying transactions.
                  </p>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
                    <span>Razorpay Webhook Secret (Optional)</span>
                  </span>
                  {settings.razorpay_webhook_secret_set && (
                    <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                      ✓ Configured
                    </span>
                  )}
                </label>
                <input
                  type="password"
                  value={newRazorpayWebhookSecret}
                  onChange={(e) => setNewRazorpayWebhookSecret(e.target.value)}
                  placeholder={settings.razorpay_webhook_secret_set ? '•••••••••••••••• (Leave blank to keep existing)' : 'Enter Webhook Secret'}
                  className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white text-xs font-mono focus:outline-none focus:border-amber-400"
                />
                <p className="text-[11px] text-slate-500 mt-1">
                  Webhook URL to register in Razorpay: <code className="text-amber-400">https://yourdomain.com/api/payments/webhook</code>
                </p>
              </div>
                <div className="p-4 rounded-2xl bg-amber-500/[0.05] border border-amber-500/20 text-xs text-slate-300 space-y-2 mt-4">
                  <div className="font-bold text-amber-400 flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4" />
                    <span>Razorpay Live &amp; Test Simulator Compatibility</span>
                  </div>
                  <p className="text-[11px] leading-relaxed text-slate-400">
                    • When switched to Razorpay, real API credentials trigger the official Razorpay checkout modal for UPI, Cards, and Netbanking.
                    <br />
                    • When using test keys, the system provides a simulation mode for test bookings.
                  </p>
                </div>
              </div>
            </div>
          )}

        {/* Global Save Button */}
        <div className="flex items-center justify-between p-4 rounded-2xl glass-panel border border-white/10">
          <div className="text-xs text-slate-400">
            Changes take effect immediately across all booking flows and notification dispatchers.
          </div>

          <button
            type="submit"
            disabled={saving}
            className="festive-button px-6 py-3 rounded-xl font-bold text-xs flex items-center gap-2 shadow-lg shadow-orange-500/20 disabled:opacity-50 cursor-pointer"
          >
            {saving ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Saving...</span>
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                <span>Save All Settings</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
