import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Sparkles,
  Ticket,
  Calendar,
  Clock,
  MapPin,
  Music,
  ShieldCheck,
  ChevronDown,
  ArrowRight,
  CheckCircle2,
  Volume2,
  VolumeX,
  Award,
  Users,
  Headphones,
  Disc,
  Flame,
  Camera,
  ExternalLink,
  Share2,
  Copy,
  Check
} from 'lucide-react';
import { CountdownTimer } from '../components/CountdownTimer';
import { fetchPublicConfig } from '../services/api';
import { EventConfig } from '../types';
import { playDandiyaClick, toggleAmbientSound } from '../utils/audio';

export const HomePage: React.FC = () => {
  const [config, setConfig] = useState<EventConfig | null>(null);
  const [activeFaq, setActiveFaq] = useState<number | null>(null);
  const [ambientActive, setAmbientActive] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);

  useEffect(() => {
    fetchPublicConfig()
      .then(setConfig)
      .catch((err) => console.error('Failed to load event config:', err));
  }, []);

  const handleCopyOfferLink = () => {
    if (typeof window !== 'undefined') {
      const shareUrl = `${window.location.origin}/book?count=10`;
      navigator.clipboard.writeText(shareUrl);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2500);
    }
  };

  const eventName = config?.event_name || 'GARBA NIGHT 2026';
  const eventDate = config?.event_date || 'October 16, 2026';
  const eventTime = config?.event_time || '06:00 PM - 10:00 PM';
  const venueName = config?.venue_name || 'The Serenity Grove';
  const venueAddress = config?.venue_address || 'The Serenity Grove, Mysuru';
  const venueCity = config?.venue_city || 'Mysuru';
  const ticketPrice = config?.ticket_price || 599;
  const remaining = config?.remaining_tickets ?? 1460;
  const mapsUrl = 'https://maps.google.com/?q=The+Serenity+Grove+Mysuru';

  const handleToggleAmbient = () => {
    const nextState = toggleAmbientSound();
    setAmbientActive(nextState);
    playDandiyaClick();
  };

  const highlights = [
    {
      title: 'Professional Garba Dancers',
      badge: 'Choreography',
      desc: 'Witness mesmerizing formations and traditional synchrony by acclaimed professional folk dance troupes.',
      icon: Users,
      color: 'text-[#d4af37]',
      bg: 'bg-[#d4af37]/15'
    },
    {
      title: '🥁 LIVE Gujarati Dhol',
      badge: 'Acoustic Folk',
      desc: 'Thunderous, authentic Gujarati dholaks and master percussionists driving relentless, electrifying dance circles.',
      icon: Music,
      color: 'text-[#f3e4b2]',
      bg: 'bg-[#f3e4b2]/15'
    },
    {
      title: '🎧 Insane DJ • Non-Stop Garba Beats',
      badge: 'High Voltage',
      desc: 'World-class electronic folk fusion seamlessly blending traditional anthems with bass-heavy party energy.',
      icon: Headphones,
      color: 'text-[#e5c97b]',
      bg: 'bg-[#e5c97b]/15'
    },
    {
      title: '🪩 LIVE Garba Experience',
      badge: 'Open Arena',
      desc: 'An opulent open-air dance amphitheater under the stars for thousands of passionate Garba revelers.',
      icon: Disc,
      color: 'text-[#d4af37]',
      bg: 'bg-[#d4af37]/15'
    },
    {
      title: '🕺 Dandiya Raas',
      badge: 'Traditional',
      desc: 'Spirited Dandiya Raas sessions with premium rosewood and illuminated LED sticks available at the concierge.',
      icon: Flame,
      color: 'text-amber-400',
      bg: 'bg-amber-500/15'
    },
    {
      title: '✨ Crazy Lights & Visuals',
      badge: 'Production',
      desc: 'Concert-grade intelligent laser arrays, atmospheric haze, digital LED backdrops, and synchronized stage SFX.',
      icon: Sparkles,
      color: 'text-[#f3e4b2]',
      bg: 'bg-[#d4af37]/20'
    },
    {
      title: '📸 360° Video + Photo Booth',
      badge: 'Memories',
      desc: 'Cinematic 360-degree slow-motion video glam cams and luxury royal photo booth installations to capture memories.',
      icon: Camera,
      color: 'text-emerald-400',
      bg: 'bg-emerald-500/15'
    }
  ];

  const faqs = [
    {
      q: 'What is the mandatory dress code for admission?',
      a: 'To honor the rich cultural elegance of GARBA NIGHT 2026, traditional Indian festive attire is strictly encouraged. Women are requested to wear Chaniya Choli, and men in Kurta Pajama or Kediyu. Western casuals (jeans, t-shirts) are restricted.'
    },
    {
      q: 'Will physical tickets be sold at The Serenity Grove gates?',
      a: 'No, all passes must be secured in advance online to maintain strict venue safety and capacity regulations. Admission is permitted exclusively upon scanning an authentic encrypted digital QR pass.'
    },
    {
      q: 'What is included in the ₹599 Early Bird Pass?',
      a: 'The ₹599 Early Bird Pass grants complete admission to the live concert arena, dance floor, 360° video booth experiences, food pavilion access, and complimentary parking at The Serenity Grove, Mysuru.'
    },
    {
      q: 'Can I purchase multiple passes in a single booking?',
      a: 'Yes, you may reserve up to 10 passes in a single transaction. Each attendee receives a uniquely hashed cryptographically signed QR code pass for seamless turnstile entry.'
    },
    {
      q: 'How do I locate The Serenity Grove on the event day?',
      a: 'The Serenity Grove is easily accessible with expansive access roads and dedicated parking in Mysuru. You can tap the "Open in Google Maps" link on this page or search for The Serenity Grove, Mysuru.'
    },
    {
      q: 'What is the cancellation and refund policy?',
      a: 'In accordance with luxury live event standards, passes are strictly non-refundable and non-transferable. If the event is officially rescheduled, passes remain fully valid for the new date.'
    }
  ];

  return (
    <div className="relative overflow-hidden">
      {/* Hero Section */}
      <section className="relative pt-12 pb-20 md:pt-20 md:pb-32 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto text-center">
        {/* Top Badges & Audio Switch */}
        <div className="flex flex-wrap items-center justify-center gap-3.5 mb-7">
          <motion.div
            initial={{ opacity: 0, y: -15 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#d4af37]/10 border border-[#d4af37]/30 text-[#f3e4b2] text-xs font-bold uppercase tracking-widest shadow-sm backdrop-blur-md"
          >
            <Sparkles className="w-3.5 h-3.5 text-[#d4af37]" />
            <span>Navratri 2026 • Early Bird Pass ₹{ticketPrice}</span>
          </motion.div>

          <button
            onClick={handleToggleAmbient}
            className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold transition-all border ${
              ambientActive
                ? 'bg-[#d4af37]/20 text-[#f3e4b2] border-[#d4af37]/50 shadow-md shadow-[#d4af37]/20 animate-pulse'
                : 'bg-white/[0.04] text-slate-300 border-white/[0.1] hover:text-white hover:bg-white/[0.08]'
            }`}
            title="Toggle festive ambient music drone"
          >
            {ambientActive ? <Volume2 className="w-3.5 h-3.5 text-[#d4af37]" /> : <VolumeX className="w-3.5 h-3.5 text-slate-400" />}
            <span>{ambientActive ? 'Ambiance Live 🎵' : 'Play Music 🎶'}</span>
          </button>
        </div>

        {/* Heritage Productions Presenter Crest */}
        <motion.div
          initial={{ opacity: 0, scale: 0.85, y: -10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.7 }}
          className="flex flex-col items-center justify-center mb-6"
        >
          <div className="relative group">
            {/* Ambient radial gold glow behind the emblem */}
            <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-[#d4af37]/30 via-[#f3e4b2]/20 to-transparent blur-2xl scale-125 pointer-events-none group-hover:scale-150 transition-transform duration-700" />
            <div className="relative w-28 h-28 sm:w-36 sm:h-36 md:w-40 md:h-40 rounded-full p-1 bg-gradient-to-b from-[#f3e4b2] via-[#d4af37] to-[#806017] shadow-[0_0_35px_rgba(212,175,55,0.4)] transition-transform duration-500 group-hover:scale-105">
              <img
                src="/heritage_productions.jpg"
                alt="Heritage Productions Logo"
                className="w-full h-full object-cover rounded-full shadow-inner"
              />
            </div>
          </div>
          <div className="mt-3.5 flex items-center gap-2.5">
            <span className="h-px w-8 sm:w-16 bg-gradient-to-r from-transparent to-[#d4af37]/70" />
            <span className="text-[11px] sm:text-xs font-black uppercase tracking-[0.35em] text-[#e5c97b] font-['Outfit'] drop-shadow-[0_2px_10px_rgba(212,175,55,0.5)]">
              Heritage Productions Presents
            </span>
            <span className="h-px w-8 sm:w-16 bg-gradient-to-l from-transparent to-[#d4af37]/70" />
          </div>
        </motion.div>

        {/* Main Headline with Royal Cinzel Serif Style & Fluid Clamp Typography */}
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6 }}
          className="space-y-3"
        >
          <h1 className="hero-clamp-title font-extrabold text-white uppercase font-['Cinzel'] tracking-[0.05em] navrang-hero-title">
            <span className="block bg-gradient-to-b from-[#ffffff] via-[#f7e8c3] to-[#d4af37] bg-clip-text text-transparent drop-shadow-[0_4px_35px_rgba(212,175,55,0.4)]">
              {eventName}
            </span>
          </h1>

          {/* MYSURU Badge & Festive Subtitle */}
          <div className="flex items-center justify-center gap-3">
            <span className="h-px w-10 sm:w-20 bg-gradient-to-r from-transparent via-[#d4af37] to-transparent" />
            <span className="px-5 py-1.5 rounded-full bg-gradient-to-r from-[#d4af37]/20 via-[#991b1b]/25 to-[#d4af37]/20 border border-[#d4af37]/50 text-xl sm:text-2xl md:text-3xl font-black uppercase tracking-[0.3em] text-[#f7e8c3] font-['Cinzel'] shadow-[0_0_20px_rgba(212,175,55,0.25)]">
              MYSURU
            </span>
            <span className="h-px w-10 sm:w-20 bg-gradient-to-r from-transparent via-[#d4af37] to-transparent" />
          </div>
        </motion.div>

        {/* Tagline */}
        <motion.p
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="mt-5 text-sm sm:text-lg text-[#f3e4b2] font-bold tracking-[0.25em] uppercase"
        >
          ENERGY • FESTIVAL • DANCE • TRADITION • CELEBRATION
        </motion.p>
        <p className="mt-3 text-xs sm:text-base text-slate-300 max-w-2xl mx-auto leading-relaxed">
          The defining royal Navratri cultural celebration at Mysuru. An unforgettable evening of LIVE Gujarati Dhol, premier DJs, traditional Dandiya Raas, and instant digital QR entry passes.
        </p>

        {/* Event Logistics Cards (Section 10 Requirement) */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="mt-9 grid grid-cols-1 sm:grid-cols-3 gap-3.5 sm:gap-4 max-w-3xl mx-auto text-center"
        >
          <div className="p-4 rounded-2xl glass-card-interactive border border-white/[0.09] shadow-lg shadow-black/40">
            <div className="text-[10px] uppercase font-black tracking-[0.2em] text-[#d4af37] mb-1 flex items-center justify-center gap-1.5 font-['Cinzel']">
              <Calendar className="w-3.5 h-3.5" />
              <span>DATE</span>
            </div>
            <div className="text-base sm:text-lg font-black text-white font-['Outfit']">
              {eventDate}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">Grand Navratri Gala</div>
          </div>

          <div className="p-4 rounded-2xl glass-card-interactive border border-white/[0.09] shadow-lg shadow-black/40">
            <div className="text-[10px] uppercase font-black tracking-[0.2em] text-[#d4af37] mb-1 flex items-center justify-center gap-1.5 font-['Cinzel']">
              <MapPin className="w-3.5 h-3.5" />
              <span>VENUE</span>
            </div>
            <div className="text-base sm:text-lg font-black text-white font-['Outfit']">
              {venueCity}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">{venueName}</div>
          </div>

          <div className="p-4 rounded-2xl glass-card-interactive border border-white/[0.09] shadow-lg shadow-black/40">
            <div className="text-[10px] uppercase font-black tracking-[0.2em] text-[#d4af37] mb-1 flex items-center justify-center gap-1.5 font-['Cinzel']">
              <Clock className="w-3.5 h-3.5" />
              <span>TIME</span>
            </div>
            <div className="text-base sm:text-lg font-black text-white font-['Outfit']">
              {eventTime}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">Entry starts at 05:30 PM</div>
          </div>
        </motion.div>

        {/* Countdown Timer */}
        <div className="mt-10 sm:mt-12">
          <div className="text-xs uppercase font-extrabold tracking-[0.25em] text-[#d4af37] mb-4 flex items-center justify-center gap-2 font-['Cinzel']">
            <Sparkles className="w-3.5 h-3.5 text-[#d4af37]" />
            <span>Garba Night 2026 Begins In</span>
            <Sparkles className="w-3.5 h-3.5 text-[#d4af37]" />
          </div>
          <CountdownTimer eventDate={eventDate} eventTime={eventTime} />
        </div>

        {/* Hero CTAs (Section 4 Requirement: Primary "BOOK YOUR TICKETS", Secondary "EXPLORE EVENT") */}
        <div className="mt-10 sm:mt-12 flex flex-col sm:flex-row items-center justify-center gap-4 max-w-md mx-auto sm:max-w-none">
          <Link
            to="/book"
            onClick={() => playDandiyaClick()}
            className="festive-button w-full sm:w-auto px-9 py-4 rounded-full text-xs sm:text-sm font-black uppercase tracking-wider flex items-center justify-center gap-3 shadow-2xl touch-target cursor-pointer"
          >
            <Ticket className="w-4 h-4" />
            <span>BOOK YOUR TICKETS</span>
            <ArrowRight className="w-4 h-4" />
          </Link>

          <a
            href="#about"
            className="luxury-outline-button w-full sm:w-auto px-8 py-4 rounded-full text-xs sm:text-sm font-bold uppercase tracking-wider flex items-center justify-center gap-2 touch-target cursor-pointer"
          >
            <Sparkles className="w-4 h-4 text-[#d4af37]" />
            <span>EXPLORE EVENT</span>
          </a>
        </div>

        {/* Requirement 1 & 14: Promotional Hero Banner */}
        <motion.div
          initial={{ opacity: 0, y: 25 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.25 }}
          className="mt-12 max-w-2xl mx-auto rounded-3xl p-6 sm:p-7 glass-panel-gold border-2 border-[#d4af37]/60 shadow-[0_0_40px_rgba(212,175,55,0.22)] relative overflow-hidden text-center group"
        >
          {/* Subtle festive background illumination */}
          <div className="absolute -top-14 -right-14 w-44 h-44 bg-[#d4af37]/20 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute -bottom-14 -left-14 w-44 h-44 bg-emerald-500/15 rounded-full blur-3xl pointer-events-none" />

          {/* Badge */}
          <div className="inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full bg-gradient-to-r from-amber-500/20 to-emerald-500/20 border border-[#d4af37]/40 text-[#f3e4b2] text-[11px] font-black uppercase tracking-widest shadow-sm">
            <Flame className="w-3.5 h-3.5 text-amber-400 animate-pulse" />
            <span>EXCLUSIVE GROUP OFFER</span>
          </div>

          {/* Prominent Header */}
          <h2 className="mt-3 text-2xl sm:text-4xl font-black text-white uppercase tracking-tight font-['Outfit']">
            🔥 BUY 10, PAY FOR 9
          </h2>

          <div className="mt-1.5 inline-flex items-center gap-2 text-xs sm:text-sm font-extrabold text-[#f3e4b2] uppercase tracking-[0.2em]">
            <span>10 TICKETS</span>
            <span>•</span>
            <span className="text-emerald-300">1 FREE</span>
          </div>

          {/* Desktop & Mobile Price Calculation */}
          <div className="mt-4 flex flex-wrap items-center justify-center gap-2.5 sm:gap-4">
            <span className="text-base sm:text-xl text-slate-400 font-mono line-through decoration-rose-500 decoration-2">
              ₹{(ticketPrice * 10).toLocaleString('en-IN')}
            </span>
            <span className="text-slate-400 font-bold text-sm sm:text-lg">→</span>
            <span className="text-3xl sm:text-5xl font-black bg-gradient-to-r from-white via-[#f3e4b2] to-[#d4af37] bg-clip-text text-transparent font-mono">
              ₹{(ticketPrice * 9).toLocaleString('en-IN')}
            </span>
            <span className="px-3 py-1 rounded-full bg-emerald-500/20 border border-emerald-400/50 text-emerald-300 text-xs sm:text-sm font-black uppercase tracking-wider shadow-sm">
              SAVE ₹{ticketPrice.toLocaleString('en-IN')}
            </span>
          </div>

          {/* Supporting Text */}
          <p className="mt-3 text-xs sm:text-sm text-slate-300 font-medium max-w-lg mx-auto leading-relaxed">
            Bring your whole Garba squad. More friends. More Garba. One ticket FREE.
          </p>

          {/* Mobile concise summary chips (Requirement 14) */}
          <div className="mt-4 flex sm:hidden items-center justify-center gap-2 text-[11px] font-bold">
            <span className="px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-slate-200">🎟 10 TICKETS</span>
            <span className="px-2.5 py-1 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-300">🎟 1 FREE</span>
            <span className="px-2.5 py-1 rounded-lg bg-amber-500/15 border border-amber-500/30 text-amber-300">₹{ticketPrice} OFF</span>
          </div>

          {/* Action CTA */}
          <div className="mt-5 flex justify-center">
            <Link
              to="/book?count=10"
              onClick={() => playDandiyaClick()}
              className="festive-button w-full sm:w-auto px-8 py-3.5 rounded-full text-xs font-black uppercase tracking-wider flex items-center justify-center gap-2.5 shadow-xl shadow-[#d4af37]/30 hover:scale-105 transition-all"
            >
              <Ticket className="w-4 h-4" />
              <span>BOOK GROUP TICKETS</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </motion.div>
      </section>

      {/* Curated Highlights Section (Featuring User-Specified Attractions) */}
      <section id="highlights" className="py-16 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <div className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#d4af37] px-3.5 py-1 rounded-full bg-[#d4af37]/10 border border-[#d4af37]/25 mb-3">
            ✦ Event Highlights & Ambiance ✦
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white font-['Outfit']">
            Curated Festival Experiences
          </h2>
          <p className="mt-3 text-sm text-slate-400">
            Engineered to deliver an unforgettable cultural and musical experience with state-of-the-art production.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {highlights.map((item, idx) => {
            const Icon = item.icon;
            return (
              <div
                key={idx}
                className="p-6 rounded-2xl glass-card-interactive group flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className={`w-12 h-12 rounded-xl ${item.bg} flex items-center justify-center ${item.color} group-hover:scale-105 transition-transform`}>
                      <Icon className="w-6 h-6" />
                    </div>
                    <span className="text-[10px] font-black uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-white/[0.05] border border-white/[0.08] text-slate-300">
                      {item.badge}
                    </span>
                  </div>
                  <h3 className="text-lg font-bold text-white mb-2 font-['Outfit']">
                    {item.title}
                  </h3>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    {item.desc}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-16 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <div className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#d4af37] px-3.5 py-1 rounded-full bg-[#d4af37]/10 border border-[#d4af37]/25 mb-3">
          ✦ Passes & Special Offers ✦
        </div>
        <h2 className="text-3xl sm:text-5xl font-extrabold text-white font-['Outfit']">
          Select Your Admission Pass
        </h2>
        <p className="mt-2 text-sm text-slate-400 max-w-2xl mx-auto">
          Every pass includes full arena admission, live concert experience, 360° video glam cam, and secure parking.
        </p>

        {/* 2-Card Layout: Individual & Group Offer */}
        <div className="mt-10 grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-5xl mx-auto text-left items-stretch">
          {/* Individual General Ticket Card */}
          <div className="p-7 sm:p-8 rounded-3xl glass-panel border border-white/[0.08] flex flex-col justify-between relative overflow-hidden group">
            <div>
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-[10px] font-black tracking-wider uppercase text-slate-300 px-3 py-1 rounded-full bg-white/[0.06] border border-white/10 font-['Cinzel']">
                    ADMISSION PASS
                  </span>
                  <h3 className="text-2xl sm:text-3xl font-black text-white mt-3 font-['Cinzel'] tracking-wide">
                    GENERAL TICKET
                  </h3>
                </div>
                <div className="text-right">
                  <div className="text-3xl sm:text-4xl font-black text-white font-mono">₹{ticketPrice}</div>
                  <div className="text-xs text-slate-400 mt-0.5">per person</div>
                </div>
              </div>

              <div className="mt-6 pt-6 border-t border-white/[0.08] space-y-3.5 text-xs text-slate-300">
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Full admission to {venueCity} arena from 7 PM to Late</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>LIVE Gujarati Dhol & Insane DJ Non-Stop Garba Beats</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Complimentary access to 360° Video Booth installations</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Instant encrypted digital QR pass delivered via Email & PDF ticket</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Complimentary secure parking at venue</span>
                </div>
              </div>
            </div>

            <div className="mt-8">
              <Link
                to="/book?count=1"
                onClick={() => playDandiyaClick()}
                className="festive-button w-full py-4 rounded-2xl font-black text-xs sm:text-sm uppercase tracking-wider flex items-center justify-center gap-2 shadow-lg touch-target cursor-pointer"
              >
                <Ticket className="w-4 h-4" />
                <span>BOOK NOW</span>
              </Link>
            </div>
          </div>

          {/* Group Offer Card (BUY 10, PAY FOR 9) */}
          <div className="p-7 sm:p-8 rounded-3xl glass-panel-gold border-2 border-[#d4af37]/70 flex flex-col justify-between relative overflow-hidden shadow-2xl shadow-[#d4af37]/25 group">
            {/* Badges in top right */}
            <div className="absolute top-4 right-4 flex items-center gap-1.5">
              <span className="text-[11px] font-black uppercase tracking-wider px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm">
                SAVE ₹{ticketPrice}
              </span>
            </div>

            <div>
              <div className="text-center pt-2 pb-4 border-b border-white/[0.08]">
                <div className="text-[10px] font-extrabold uppercase tracking-[0.25em] text-[#d4af37] font-['Cinzel']">
                  EXCLUSIVE FESTIVE PROMOTION
                </div>
                <h3 className="text-2xl sm:text-3xl font-black text-white mt-1 uppercase font-['Cinzel'] tracking-wide">
                  BUY 10, PAY FOR 9
                </h3>
                <div className="mt-2 inline-flex items-center gap-2 text-xs font-bold text-[#f3e4b2] uppercase tracking-[0.2em]">
                  <span className="px-3 py-0.5 rounded-md bg-white/[0.07] border border-white/10">10 TICKETS</span>
                  <span>•</span>
                  <span className="px-3 py-0.5 rounded-md bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 font-extrabold">1 TICKET FREE</span>
                </div>
              </div>

              {/* Price comparison layout matching specification */}
              <div className="py-5 px-3 flex items-center justify-around text-center bg-black/40 rounded-2xl my-5 border border-white/[0.08]">
                <div>
                  <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">REGULAR</div>
                  <div className="text-lg sm:text-xl font-bold font-mono text-slate-400 line-through decoration-rose-500 decoration-2 mt-1">
                    ₹{(ticketPrice * 10).toLocaleString('en-IN')}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">10 × ₹{ticketPrice}</div>
                </div>

                <div className="text-2xl font-black text-[#d4af37]">↓</div>

                <div>
                  <div className="text-[10px] uppercase font-bold text-[#d4af37] tracking-wider">GROUP PASS</div>
                  <div className="text-3xl sm:text-4xl font-black font-mono bg-gradient-to-r from-white via-[#f3e4b2] to-[#d4af37] bg-clip-text text-transparent mt-0.5">
                    ₹{(ticketPrice * 9).toLocaleString('en-IN')}
                  </div>
                  <div className="text-[10px] font-bold text-emerald-400 mt-0.5">Pay for 9 Only</div>
                </div>
              </div>

              {/* Value propositions */}
              <div className="space-y-2.5 text-xs text-slate-300">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Receive <strong>10 unique QR tickets</strong> — all 10 are completely valid passes</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Save <strong>₹{ticketPrice} instantly</strong> (1 ticket 100% FREE)</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Perfect for friends, family, dance groups & Garba squads</span>
                </div>
              </div>
            </div>

            <div className="mt-8 pt-4 border-t border-white/[0.08]">
              <div className="text-center text-xs font-black uppercase tracking-widest text-emerald-400 mb-3">
                SAVE ₹{ticketPrice.toLocaleString('en-IN')}
              </div>
              <Link
                to="/book?count=10"
                onClick={() => playDandiyaClick()}
                className="festive-button w-full py-4 rounded-2xl font-black text-xs sm:text-sm uppercase tracking-wider flex items-center justify-center gap-2 shadow-xl shadow-[#d4af37]/30 touch-target cursor-pointer"
              >
                <Ticket className="w-4 h-4" />
                <span>BOOK NOW</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>

        {/* Requirement 13: Social Sharing Card */}
        <div className="mt-14 p-6 sm:p-8 rounded-3xl glass-panel border border-white/[0.08] max-w-3xl mx-auto text-center relative overflow-hidden">
          <div className="inline-flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wider text-[#d4af37] mb-2">
            <Users className="w-4 h-4 text-[#d4af37]" />
            <span>COMING WITH YOUR FRIENDS?</span>
          </div>
          <h3 className="text-xl sm:text-2xl font-black text-white uppercase font-['Outfit']">
            BUY 10, PAY FOR 9
          </h3>
          <p className="mt-1 text-xs text-slate-300 max-w-md mx-auto">
            Gather your squad, share the exclusive group offer, and save ₹{ticketPrice} together!
          </p>

          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <a
              href={`https://api.whatsapp.com/send?text=${encodeURIComponent(
                `🔥 Garba Night 2026 is here!\n\nBuy 10 tickets and pay for only 9!\n\n₹${ticketPrice} OFF\n\nLet's go together! 🎉\n` + (typeof window !== 'undefined' ? `${window.location.origin}/book?count=10` : '')
              )}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold uppercase tracking-wider shadow-lg shadow-emerald-600/30 transition-all hover:scale-105"
            >
              <Share2 className="w-4 h-4" />
              <span>Share on WhatsApp</span>
            </a>

            <button
              type="button"
              onClick={handleCopyOfferLink}
              className="luxury-outline-button inline-flex items-center gap-2 px-6 py-3 rounded-full text-xs font-bold uppercase tracking-wider text-slate-200 hover:text-white"
            >
              {copiedLink ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 text-[#d4af37]" />}
              <span>{copiedLink ? 'Link Copied!' : 'Copy Link'}</span>
            </button>
          </div>
        </div>
      </section>

      {/* Venue Section with Maps Deep Link */}
      <section id="venue" className="py-16 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="p-8 sm:p-12 rounded-3xl glass-panel border border-white/[0.08] relative overflow-hidden">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
            <div>
              <div className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-[#d4af37] mb-3">
                <MapPin className="w-4 h-4" />
                Venue & Location
              </div>
              <h2 className="text-2xl sm:text-4xl font-extrabold text-white font-['Outfit']">
                {venueName}
              </h2>
              <p className="mt-2 text-sm text-slate-300">
                {venueAddress}, {venueCity}
              </p>
              <div className="mt-6 space-y-3 text-xs text-slate-400">
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-[#d4af37]" />
                  <span>Date: {eventDate} (Friday)</span>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-[#d4af37]" />
                  <span>Entry starts at 05:30 PM | Show: 06:00 PM - 10:00 PM</span>
                </div>
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <span>Dedicated parking, security frisking, and bag check at Entrance Gates.</span>
                </div>
              </div>
            </div>

            <div className="rounded-2xl overflow-hidden border border-white/[0.08] bg-[#06070c]/70 p-7 text-center space-y-4">
              <div className="w-14 h-14 mx-auto rounded-full bg-[#d4af37]/10 flex items-center justify-center text-[#d4af37]">
                <MapPin className="w-7 h-7" />
              </div>
              <div className="font-bold text-white text-base">The Serenity Grove Location Pin</div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Located at The Serenity Grove, Mysuru. Easily navigable with broad access roads, drop-off bays, and dedicated parking for 1,500+ vehicles.
              </p>
              <a
                href={mapsUrl}
                target="_blank"
                rel="noreferrer"
                className="luxury-outline-button inline-flex items-center gap-2 px-6 py-3 rounded-xl text-xs font-bold text-[#f3e4b2] uppercase tracking-wider"
              >
                <MapPin className="w-4 h-4 text-[#d4af37]" />
                <span>Open in Google Maps</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section id="faq" className="py-16 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#d4af37] px-3 py-1 rounded-full bg-[#d4af37]/10 border border-[#d4af37]/20 mb-3">
            Knowledge Base
          </div>
          <h2 className="text-3xl font-extrabold text-white font-['Outfit']">Frequently Asked Questions</h2>
          <p className="mt-2 text-sm text-slate-400">Everything you need to know about booking and admission at The Serenity Grove, Mysuru</p>
        </div>

        <div className="space-y-3.5">
          {faqs.map((faq, i) => (
            <div
              key={i}
              className="rounded-2xl border border-white/[0.07] bg-[#0e111d]/75 overflow-hidden transition-all"
            >
              <button
                type="button"
                onClick={() => setActiveFaq(activeFaq === i ? null : i)}
                className="w-full p-5 text-left flex items-center justify-between text-sm font-bold text-slate-200 hover:text-[#f3e4b2] transition-colors"
              >
                <span>{faq.q}</span>
                <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${activeFaq === i ? 'rotate-180 text-[#d4af37]' : ''}`} />
              </button>
              {activeFaq === i && (
                <div className="px-5 pb-5 text-xs text-slate-400 leading-relaxed border-t border-white/[0.05] pt-3">
                  {faq.a}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};
