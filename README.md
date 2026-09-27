# 🪔 GARBA NIGHT 2026 — Real-Time Event Ticketing & QR Turnstile Verification Platform

A complete, production-grade full-stack web application designed for real-world Navratri Garba event ticket booking, Razorpay payment processing, cryptographically secure digital QR pass issuance, and gate entry check-in with atomic race condition protection.

---

## 🌟 Key Features

### 1. Customer Experience & Booking Flow
- **Navratri Aesthetic with Animated Artwork**: Immersive visual design with Goddess Durga's radiant aura, swirling traditional Garba dancers, floating diya embers, rotating mandalas, and synthesized classical Indian tanpura ambiance.
- **Dynamic Live Inventory**: Live ticket countdown counter (`Only XXX tickets left`) linked directly to server-side capacity checks.
- **Live Event Countdown**: Animated days, hours, minutes, and seconds flip counters.
- **Server-Authoritative Pricing**: Ticket calculations (₹300/ticket, convenience fees, subtotal) are computed on the backend—client-side price tampering is completely prevented.
- **Seamless Razorpay Checkout**: Real Razorpay standard payment gateway with built-in test sandbox simulation mode for instant zero-config testing.
- **HMAC SHA-256 Payment Verification**: Strict cryptographic signature verification before booking confirmation.

### 2. QR Code Cryptographic Security
- **No Predictable Database IDs**: QR passes contain high-entropy, cryptographically secure random tokens (`GN26_xxxxxxxx`).
- **One-Way Salting & Hashing**: The database stores only a salted SHA-256 hash of the token (`qr_token_hash`). A database leak cannot compromise valid QR codes.
- **Individual Passes**: A booking of 4 tickets produces 4 unique ticket IDs (`GN26-TKT-XXXXXX-01` to `04`) with individual QR passes.

### 3. Turnstile QR Scanner & Gate Check-in
- **Device Camera Scanner**: Real-time camera viewfinder with animated laser guide, camera switcher, and manual token backup.
- **Atomic Concurrency Protection**: Database row-locking (`with_for_update`) guarantees that two gatekeepers scanning identical passes simultaneously can never produce duplicate admissions.
- **Instant Visual & Audio Feedback**:
  - `✓ VALID TICKET`: Green admission card with attendee details and "CHECK IN" trigger.
  - `⚠️ TICKET ALREADY USED`: Orange alarm displaying the exact previous check-in time and staff identifier.
  - `❌ INVALID TICKET`: Red rejection alert for unknown or tampered codes.
  - `❌ TICKET CANCELLED`: Denied access for refunded passes.

### 4. Enterprise Admin Console
- **Real-Time KPIs**: Tickets Sold, Gross Revenue (₹), Total Bookings, Turnstile Checked-in Count, Remaining Capacity, and Attendance Rate (%).
- **Interactive Recharts Analytics**: 7-day revenue progression area chart, daily tickets sold bar chart, and hourly check-in distribution.
- **Bookings Management**: Instant search by Booking ID, customer name, email, phone, or ticket ID; filters by payment & booking status; pagination; CSV export.
- **Resend Confirmation Emails**: One-click manual email resend for customer support.
- **Event Settings**: Super-Admin configuration of event dates, timings, arena venue, ticket prices, and booking open/close switches.
- **Immutable Audit Trail**: Security log recording logins, cancellations, settings changes, and check-in scan events.

---

## 🏗️ Project Architecture

```
garba-night-2026/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI application entrypoint & middleware
│   │   ├── config.py                   # Pydantic environment configuration
│   │   ├── database.py                 # SQLAlchemy engine & session factory
│   │   ├── models/
│   │   │   ├── user.py                 # Admin & staff user accounts
│   │   │   ├── booking.py              # Customer bookings & payment tracking
│   │   │   ├── ticket.py               # Individual tickets & QR token hashes
│   │   │   ├── payment.py              # Razorpay transaction orders & signatures
│   │   │   ├── checkin.py              # Gate entry audit logs & scan results
│   │   │   ├── audit_log.py            # Security & administration event log
│   │   │   └── event_setting.py        # Configurable event settings & capacity
│   │   ├── schemas/
│   │   │   ├── auth.py                 # Login & token schemas
│   │   │   ├── booking.py              # Booking creation & query schemas
│   │   │   ├── payment.py              # Order initialization & signature schemas
│   │   │   ├── ticket.py               # QR validation & check-in schemas
│   │   │   └── admin.py                # Dashboard stats & analytics schemas
│   │   ├── routes/
│   │   │   ├── auth.py                 # Admin login, logout, me
│   │   │   ├── booking.py              # Public config & booking retrieval
│   │   │   ├── payment.py              # Razorpay order, verification & webhook
│   │   │   ├── ticket.py               # Digital ticket view, QR verify & check-in
│   │   │   └── admin.py                # Dashboard, bookings, check-ins, CSV export
│   │   ├── services/
│   │   │   ├── payment_service.py      # Razorpay client & HMAC verification
│   │   │   ├── qr_service.py           # High-resolution QR code generator
│   │   │   ├── ticket_service.py       # ReportLab PDF ticket generator
│   │   │   ├── email_service.py        # HTML email delivery & PDF attachment
│   │   │   └── booking_service.py      # Atomic inventory & booking state machine
│   │   ├── middleware/
│   │   │   ├── auth.py                 # JWT & role authorization dependencies
│   │   │   └── rate_limit.py           # In-memory IP rate limiter
│   │   └── utils/
│   │       ├── security.py             # bcrypt hashing, token generation, HMAC
│   │       ├── validators.py           # Indian phone number & email regex
│   │       └── logger.py               # UTF-8 formatted structured logger
│   ├── migrations/                     # Alembic database migration scripts
│   ├── tests/
│   │   └── test_backend.py             # Pytest automated test suite
│   ├── requirements.txt                # Python backend dependencies
│   └── seed.py                         # Development database seed script
│
├── frontend/
│   ├── public/
│   │   ├── garba-bg.jpg                # Artwork background asset
│   │   └── favicon.svg
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.tsx              # Public header navigation
│   │   │   ├── Footer.tsx              # Public footer & links
│   │   │   ├── CountdownTimer.tsx      # Live animated event countdown
│   │   │   ├── AnimatedFestiveBackground.tsx # Festive animations & particles
│   │   │   ├── Toast.tsx               # Context-driven toast notifications
│   │   │   ├── RazorpayModalSimulator.tsx # Test checkout simulation modal
│   │   │   ├── AdminSidebar.tsx        # SaaS admin navigation sidebar
│   │   │   └── AdminHeader.tsx         # Admin top bar with live clock
│   │   ├── layouts/
│   │   │   ├── PublicLayout.tsx        # Customer site layout
│   │   │   └── AdminLayout.tsx         # Authenticated admin layout
│   │   ├── pages/
│   │   │   ├── HomePage.tsx            # Landing page with artwork showcase
│   │   │   ├── BookingPage.tsx         # Ticket reservation & payment checkout
│   │   │   ├── SuccessPage.tsx         # Confetti celebration & ticket passes
│   │   │   ├── TicketPage.tsx          # Digital admission pass view (/ticket/:token)
│   │   │   ├── AdminLoginPage.tsx      # Admin & staff sign-in
│   │   │   ├── AdminDashboardPage.tsx  # Metrics & Recharts analytics
│   │   │   ├── AdminBookingsPage.tsx   # Search, filters, pagination, CSV export
│   │   │   ├── AdminBookingDetailPage.tsx # Booking details & tickets list
│   │   │   ├── AdminScannerPage.tsx    # Live camera QR scanner turnstile
│   │   │   ├── AdminCheckinsPage.tsx   # Turnstile scan logs
│   │   │   ├── AdminSettingsPage.tsx   # Capacity & price configuration
│   │   │   ├── AdminAuditLogsPage.tsx  # Security audit trail
│   │   │   ├── TermsPage.tsx           # Terms & conditions
│   │   │   ├── PrivacyPage.tsx         # Privacy policy
│   │   │   ├── RefundPage.tsx          # Refund policy
│   │   │   └── RulesPage.tsx           # Venue entry guidelines
│   │   ├── services/
│   │   │   └── api.ts                  # Axios API client with bearer interceptor
│   │   ├── types/
│   │   │   └── index.ts                # TypeScript interfaces
│   │   ├── utils/
│   │   │   └── audio.ts                # Web Audio API festive synthesizer
│   │   ├── App.tsx                     # React Router tree
│   │   ├── main.tsx                    # React DOM entry
│   │   └── index.css                   # Tailwind v4 styles & festive classes
│   ├── package.json
│   └── vite.config.ts
│
├── .env.example                        # Environment variable documentation
├── .gitignore                          # Git ignore definitions
└── README.md
```

---

## 🚀 Getting Started (No Docker Required)

### Prerequisites
- **Node.js**: v18+ (tested on Node v22)
- **Python**: v3.10+ (tested on Python 3.11)
- **PostgreSQL** (optional for production; SQLite works out-of-the-box for local testing)

---

### Step 1: Backend Setup

1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - **Windows PowerShell**:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - **Linux/macOS**:
     ```bash
     source venv/bin/activate
     ```

4. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Seed the database with sample bookings, tickets, and default admin accounts:
   ```bash
   python seed.py
   ```

6. Start the FastAPI backend server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   Backend will be running at `http://localhost:8000`
   Open API documentation available at `http://localhost:8000/docs`

---

### Step 2: Frontend Setup

1. Open a second terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install Node dependencies:
   ```bash
   npm install
   ```

3. Start the Vite React development server:
   ```bash
   npm run dev
   ```
   Frontend will be running at `http://localhost:5173`

---

## 🔑 Default Credentials

The seed script creates the following accounts:

| Role | Email | Password |
|---|---|---|
| **Super Admin** | `admin@garbanight.in` or `admin@garbanight.local` | `GarbaNight@2026` |
| **Check-in Staff** | `staff@garbanight.in` or `staff@garbanight.local` | `StaffEntry@2026` |

> *Tip: On the `/admin/login` page, click the "Super Admin" or "Scanner Staff" quick-fill buttons to populate credentials automatically!*

---

## 🧪 Running Automated Tests

Run the comprehensive pytest suite verifying authentication, booking calculations, inventory limits, QR generation, and atomic duplicate check-in prevention:

```bash
cd backend
pytest tests/test_backend.py -v
```

All 9 test suites will run and pass:
- `test_health_check`: Verifies system uptime API
- `test_admin_login_success`: Validates bcrypt verification & JWT issuance
- `test_admin_login_invalid_password`: Confirms 401 Unauthorized on invalid passwords
- `test_public_event_config`: Verifies public pricing and remaining ticket count
- `test_create_order_pricing_calculation`: Verifies server-authoritative calculation
- `test_inventory_capacity_exceeded`: Prevents overselling beyond capacity
- `test_payment_verification_and_ticket_generation`: Verifies HMAC & issues tickets
- `test_qr_validation_and_duplicate_checkin_protection`: Atomic check-in and 409 rejection
- `test_invalid_qr_token_rejected`: Rejects unknown or forged QR tokens

---

## 💳 Razorpay Payment Configuration

### Development / Sandbox Testing Mode
The application comes preconfigured with realistic sandbox simulation mode. When `RAZORPAY_KEY_ID` contains `placeholder`, the interactive checkout modal allows you to test:
- Instant UPI simulation (Google Pay, PhonePe, Paytm)
- Credit/Debit Cards simulation
- Netbanking simulation
- Test Payment Failure simulation

### Production Mode
1. Register on [Razorpay Dashboard](https://dashboard.razorpay.com)
2. Generate API Keys under **Settings > API Keys**
3. Create a `.env` file in the project root based on `.env.example`:
   ```ini
   RAZORPAY_KEY_ID=rzp_live_your_actual_key_id
   RAZORPAY_KEY_SECRET=your_actual_key_secret
   RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
   ```
4. Set up webhook endpoint in Razorpay Dashboard pointing to:
   `https://your-domain.com/api/payments/webhook`

---

## 📧 Email Service Configuration

### SMTP (Gmail, Amazon SES, SendGrid)
Set the following variables in `.env`:
```ini
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_specific_password
FROM_EMAIL=tickets@garbanight.in
FROM_NAME=GARBA NIGHT 2026
```

### Resend API
```ini
EMAIL_PROVIDER=resend
RESEND_API_KEY=re_your_api_key
```

*Note: If no email credentials are provided, confirmation emails are safely logged to the console/logger without interrupting the customer booking flow.*

---

## 🛡️ Security Architecture

1. **Anti-Tampering Pricing**: Price calculation occurs strictly server-side using current `EventSetting`.
2. **HMAC Signature Verification**: Razorpay transactions must pass cryptographic SHA-256 HMAC verification before bookings are confirmed.
3. **Atomic Turnstile Row-Locking**: `with_for_update` row locks on the ticket record ensure that concurrent scans across multiple turnstiles cannot result in duplicate entries.
4. **Token Hash Storage**: Only salted SHA-256 hashes of QR tokens are persisted in the database.
5. **Rate Limiting**: In-memory token bucket limits prevent brute-force attacks on login, QR scan, and payment endpoints.
6. **Input Sanitization**: Pydantic v2 and Zod strictly validate all customer inputs, phone formats, and emails.
7. **HTTP-Only Cookies & Bearer Tokens**: Session tokens are protected against client-side script tampering.

---

## 🌐 Production Deployment

### Frontend (Vercel / Netlify / Cloudflare Pages)
```bash
cd frontend
npm run build
```
Deploy the generated `dist/` directory. Set environment variable:
`VITE_API_URL=https://your-backend-api.com`

### Backend (Render / Railway / AWS / DigitalOcean)
Run using Gunicorn with Uvicorn workers:
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```
Ensure PostgreSQL `DATABASE_URL` is set:
```bash
DATABASE_URL=postgresql://user:password@hostname:5432/garba_night
alembic upgrade head
```

---

© 2026 Garba Night Official Platform. Built for real Navratri celebration.
