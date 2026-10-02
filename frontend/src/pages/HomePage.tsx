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
  Award,
  Users,
  Headphones,
  Disc,
  Flame,
  Camera,
  ExternalLink,
  Share2,
  Copy,
  Check,
  Lock
} from 'lucide-react';
import { CountdownTimer } from '../components/CountdownTimer';
import { fetchPublicConfig } from '../services/api';
import { EventConfig } from '../types';
import { playDandiyaClick } from '../utils/audio';

export const HomePage: React.FC = () => {
  const [config, setConfig] = useState<EventConfig | null>(null);
  const [activeFaq, setActiveFaq] = useState<number | null>(null);
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

  const eventName = config?.event_name || 'NAVRANG 2026';
  const eventDate = config?.event_date || 'October 17, 2026';
  const eventTime = config?.event_time || '06:30 PM - 10:00 PM';
  const rawVenueName = (config?.venue_name || 'The Green Acres').trim();
  const venueName = /^the\s+/i.test(rawVenueName) ? rawVenueName : `The ${rawVenueName}`;
  const venueAddress = config?.venue_address || 'The Green Acres, Mysuru';
  const venueCity = config?.venue_city || 'Mysuru';
  const ticketPrice = config?.ticket_price || 599;
  const remaining = config?.remaining_tickets ?? 1460;
  const mapsUrl = 'https://maps.google.com/?q=The+Green+Acres+Mysuru';

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
    },
    {
      title: '🍽️ FOOD',
      badge: 'EVERY PASS',
      desc: 'Complimentary food voucher',
      icon: '🍽️',
      color: 'text-amber-400',
      bg: 'bg-amber-500/15'
    },
    {
      title: '🥤 WELCOME DRINK',
      badge: 'EVERY PASS',
      desc: 'Complimentary welcome drink / mocktail',
      icon: '🥤',
      color: 'text-rose-400',
      bg: 'bg-rose-500/15'
    },
    {
      title: '🪄 DANDIYA STICKS',
      badge: 'EVERY PASS',
      desc: 'Dandiya sticks provided',
      icon: '🪄',
      color: 'text-[#d4af37]',
      bg: 'bg-[#d4af37]/15'
    }
  ];

  const faqs = [
    {
      q: 'What is the mandatory dress code for admission?',
      a: 'To honor the rich cultural elegance of NAVRANG 2026 in collaboration with The Happy Circle, traditional Indian festive attire is strictly encouraged. Women are requested to wear Chaniya Choli, and men in Kurta Pajama or Kediyu. Western casuals (jeans, t-shirts) are restricted.'
    },
    {
      q: 'Will physical tickets be sold at The Green Acres gates?',
      a: 'No, all passes must be secured in advance online to maintain strict venue safety and capacity regulations. Admission is permitted exclusively upon scanning an authentic encrypted digital QR pass.'
    },
    {
      q: 'What is included in the ₹599 Early Bird Pass?',
      a: 'The ₹599 Early Bird Pass grants complete admission to the live concert arena, dance floor, 360° video booth experiences, food pavilion access, and complimentary parking at The Green Acres, Mysuru.'
    },
    {
      q: 'Can I purchase multiple passes in a single booking?',
      a: 'Yes, you may reserve up to 10 passes in a single transaction. Each attendee receives a uniquely hashed cryptographically signed QR code pass for seamless turnstile entry.'
    },
    {
      q: 'How do I locate The Green Acres on the event day?',
      a: 'The Green Acres is easily accessible with expansive access roads and dedicated parking in Mysuru. You can tap the "Open in Google Maps" link on this page or search for The Green Acres, Mysuru.'
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
        {/* Top Badges */}
        <div className="flex flex-wrap items-center justify-center gap-3.5 mb-7">
          <motion.div
            initial={{ opacity: 0, y: -15 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#d4af37]/10 border border-[#d4af37]/30 text-[#f3e4b2] text-xs font-bold uppercase tracking-widest shadow-sm backdrop-blur-md"
          >
            <Sparkles className="w-3.5 h-3.5 text-[#d4af37]" />
            <span>Navratri 2026 • Early Bird Pass ₹{ticketPrice}</span>
          </motion.div>
        </div>

        {/* NAVRANG Primary Identity */}
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6 }}
          className="space-y-4 mb-4"
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-gradient-to-r from-amber-500/15 via-[#d4af37]/20 to-amber-500/15 border border-[#d4af37]/40 text-[#f3e4b2] text-[11px] sm:text-xs font-black uppercase tracking-[0.25em] shadow-md backdrop-blur-md">
            <Sparkles className="w-3.5 h-3.5 text-[#d4af37]" />
            <span>Grand Cultural Celebration • Navratri 2026</span>
          </div>

          <h1 className="hero-clamp-title font-extrabold text-white uppercase font-['Cinzel'] tracking-[0.05em] navrang-hero-title">
            <span className="block bg-gradient-to-b from-[#ffffff] via-[#f7e8c3] to-[#d4af37] bg-clip-text text-transparent drop-shadow-[0_4px_35px_rgba(212,175,55,0.45)]">
              NAVRANG
            </span>
          </h1>

          <p className="text-sm sm:text-lg md:text-xl text-[#f3e4b2] font-semibold tracking-[0.16em] uppercase max-w-xl mx-auto">
            A premium Garba & cultural celebration experience
          </p>

          {/* Official Logos Side by Side */}
          <div className="pt-5 sm:pt-6 pb-2 flex flex-col items-center justify-center">
            {/* Official Logos Side by Side */}
            <div className="flex items-center justify-center gap-4 sm:gap-8">
              {/* Logo 1: Heritage Productions */}
              <div className="flex flex-col items-center group">
                <div className="relative w-24 h-24 sm:w-36 sm:h-36 md:w-44 md:h-44 rounded-full p-1 bg-gradient-to-b from-[#f3e4b2] via-[#d4af37] to-[#1a1528] shadow-[0_0_30px_rgba(212,175,55,0.3)] transition-transform duration-500 group-hover:scale-105 flex items-center justify-center">
                  <div className="w-full h-full rounded-full overflow-hidden bg-black flex items-center justify-center">
                    <img
                      src="/heritage_productions.jpg"
                      alt="Heritage Productions"
                      className="w-full h-full object-cover rounded-full"
                    />
                  </div>
                </div>
                <span className="mt-2.5 text-[10px] sm:text-xs font-black tracking-[0.2em] uppercase text-[#f7e8c3] font-['Outfit']">
                  HERITAGE PRODUCTIONS
                </span>
              </div>

              {/* Collaboration Cross */}
              <div className="flex flex-col items-center justify-center px-1">
                <span className="text-2xl sm:text-4xl font-black text-[#d4af37] drop-shadow-[0_0_15px_rgba(212,175,55,0.8)] font-mono">
                  ×
                </span>
              </div>

              {/* Logo 2: The Happy Circle */}
              <div className="flex flex-col items-center group">
                <div className="relative w-24 h-24 sm:w-36 sm:h-36 md:w-44 md:h-44 rounded-full p-1 bg-gradient-to-b from-[#f3e4b2] via-[#d4af37] to-[#1a1528] shadow-[0_0_30px_rgba(212,175,55,0.3)] transition-transform duration-500 group-hover:scale-105 flex items-center justify-center">
                  <div className="w-full h-full rounded-full overflow-hidden bg-black flex items-center justify-center">
                    <img
                      src="/images/happy-circle-logo.png"
                      alt="The Happy Circle Official Collaboration Logo"
                      className="w-full h-full object-cover rounded-full"
                    />
                  </div>
                </div>
                <span className="mt-2.5 text-[10px] sm:text-xs font-black tracking-[0.2em] uppercase text-[#f7e8c3] font-['Outfit']">
                  THE HAPPY CIRCLE
                </span>
              </div>
            </div>

            <div className="mt-5 flex items-center justify-center gap-3">
              <span className="h-px w-10 sm:w-20 bg-gradient-to-r from-transparent via-[#d4af37] to-transparent" />
              <span className="px-5 py-1.5 rounded-full bg-gradient-to-r from-[#d4af37]/20 via-[#991b1b]/25 to-[#d4af37]/20 border border-[#d4af37]/50 text-base sm:text-lg md:text-xl font-black uppercase tracking-[0.3em] text-[#f7e8c3] font-['Cinzel'] shadow-[0_0_20px_rgba(212,175,55,0.25)]">
                MYSURU
              </span>
              <span className="h-px w-10 sm:w-20 bg-gradient-to-r from-transparent via-[#d4af37] to-transparent" />
            </div>
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
            <div className="text-[11px] text-slate-400 mt-0.5">{venueName || 'The Green Acres'}</div>
          </div>

          <div className="p-4 rounded-2xl glass-card-interactive border border-white/[0.09] shadow-lg shadow-black/40">
            <div className="text-[10px] uppercase font-black tracking-[0.2em] text-[#d4af37] mb-1 flex items-center justify-center gap-1.5 font-['Cinzel']">
              <Clock className="w-3.5 h-3.5" />
              <span>TIME</span>
            </div>
            <div className="text-base sm:text-lg font-black text-white font-['Outfit']">
              {eventTime}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">Gates open at 05:30 PM</div>
          </div>
        </motion.div>

        {/* Countdown Timer */}
        <div className="mt-10 sm:mt-12">
          <div className="text-xs uppercase font-extrabold tracking-[0.25em] text-[#d4af37] mb-4 flex items-center justify-center gap-2 font-['Cinzel']">
            <Sparkles className="w-3.5 h-3.5 text-[#d4af37]" />
            <span>NAVRANG 2026 Begins In</span>
            <Sparkles className="w-3.5 h-3.5 text-[#d4af37]" />
          </div>
          <CountdownTimer eventDate={eventDate} eventTime={eventTime} />
        </div>

        {/* Hero CTA */}
        <div className="mt-10 sm:mt-12 flex items-center justify-center max-w-md mx-auto sm:max-w-none">
          <Link
            to="/book"
            onClick={() => playDandiyaClick()}
            className="festive-button w-full sm:w-auto px-9 py-4 rounded-full text-xs sm:text-sm font-black uppercase tracking-wider flex items-center justify-center gap-3 shadow-2xl touch-target cursor-pointer"
          >
            <Ticket className="w-4 h-4" />
            <span>BOOK YOUR TICKETS</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
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
                      {typeof Icon === 'string' ? (
                        <span className="text-2xl">{Icon}</span>
                      ) : (
                        <Icon className="w-6 h-6" />
                      )}
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

        {/* Supporting Line for Pass Inclusions */}
        <div className="mt-10 text-center">
          <p className="text-xs sm:text-sm text-[#f3e4b2] font-semibold max-w-xl mx-auto leading-relaxed">
            Every pass includes complimentary food voucher, welcome drink and dandiya sticks will be provided.
          </p>
        </div>
      </section>

      {/* Pricing & Ticket Phases Section */}
      <section id="pricing" className="py-16 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <div className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#d4af37] px-3.5 py-1 rounded-full bg-[#d4af37]/10 border border-[#d4af37]/25 mb-3">
          ✦ Official Ticket Phases & Passes ✦
        </div>
        <h2 className="text-3xl sm:text-5xl font-extrabold text-white font-['Outfit']">
          Select Your Admission Pass
        </h2>
        <p className="mt-2 text-sm text-slate-400 max-w-2xl mx-auto">
          Every pass includes full arena admission to NAVRANG 2026, live Gujarati Dhol, 360° video booth experiences, and secure parking.
        </p>

        {/* Phase Progression Timeline */}
        <div className="max-w-2xl mx-auto mt-8 mb-10 flex flex-wrap items-center justify-center gap-2 sm:gap-4 text-xs font-bold uppercase tracking-wider">
          <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#d4af37]/20 border border-[#d4af37]/50 text-[#f3e4b2] shadow-sm">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse inline-block" />
            <span>EARLY BIRD • LIVE</span>
          </div>
          <span className="text-[#d4af37]/50 font-mono">→</span>
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/[0.05] border border-white/10 text-slate-400">
            <Lock className="w-3.5 h-3.5 text-amber-400" />
            <span>PHASE 1 • ₹799 (LOCKED)</span>
          </div>
          <span className="text-[#d4af37]/50 font-mono hidden sm:inline">→</span>
          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/[0.03] border border-white/5 text-slate-500 text-[11px]">
            <Lock className="w-3 h-3 text-slate-500" />
            <span>PHASE 2 & FUTURE</span>
          </div>
        </div>

        {/* 3-Card Ticket Phase Grid (Responsive, stacks vertically on mobile, no horizontal scrolling) */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-7 max-w-6xl mx-auto text-left items-stretch">
          
          {/* Card 1: EARLY BIRD TICKET (CURRENTLY ACTIVE) */}
          <div className="p-7 sm:p-8 rounded-3xl glass-panel-gold border-2 border-[#d4af37] flex flex-col justify-between relative overflow-hidden shadow-[0_0_35px_rgba(212,175,55,0.25)] group">
            {/* Ambient gold glow */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-[#d4af37]/15 rounded-full blur-2xl pointer-events-none" />
            
            <div>
              <div className="flex items-start justify-between">
                <div>
                  <span className="inline-flex items-center gap-1.5 text-[10px] font-black tracking-wider uppercase text-emerald-300 px-3 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 font-['Outfit']">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    LIVE NOW
                  </span>
                  <h3 className="text-2xl sm:text-3xl font-black text-white mt-3 font-['Cinzel'] tracking-wide">
                    EARLY BIRD
                  </h3>
                  <p className="text-[11px] text-[#e5c97b] font-semibold mt-0.5">
                    Phase 1 Early Access Pass
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-3xl sm:text-4xl font-black text-white font-mono">₹{ticketPrice}</div>
                  <div className="text-[11px] text-emerald-400 font-semibold mt-0.5">Official Pass</div>
                </div>
              </div>

              <div className="mt-6 pt-5 border-t border-white/[0.08] space-y-3 text-xs text-slate-300">
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Full admission to NAVRANG 2026 celebration</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Complimentary food voucher</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Complimentary welcome drink / mocktail</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Dandiya sticks provided</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>LIVE Gujarati Dhol, DJ & Dandiya Raas</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Complimentary 360° Video Booth experience</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Instant encrypted QR ticket via Email & PDF pass</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Complimentary parking at The Green Acres, Mysuru</span>
                </div>
              </div>
            </div>

            <div className="mt-8">
              <Link
                to="/book?phase=EARLY_BIRD"
                onClick={() => playDandiyaClick()}
                className="festive-button w-full py-4 rounded-2xl font-black text-xs sm:text-sm uppercase tracking-wider flex items-center justify-center gap-2 shadow-xl shadow-[#d4af37]/30 touch-target cursor-pointer"
              >
                <Ticket className="w-4 h-4" />
                <span>BOOK NOW</span>
              </Link>
            </div>
          </div>

          {/* Card 2: PHASE 1 TICKET (LOCKED / COMING SOON - Requirement 9 & 10) */}
          <div className="p-7 sm:p-8 rounded-3xl bg-[#090b14]/90 border border-white/[0.12] flex flex-col justify-between relative overflow-hidden group select-none transition-all hover:border-white/20">
            {/* Elegant dark overlay */}
            <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#06070c]/60 to-[#06070c]/90 pointer-events-none" />

            <div className="relative z-10">
              <div className="flex items-start justify-between">
                <div>
                  <span className="inline-flex items-center gap-1.5 text-[10px] font-black tracking-wider uppercase text-amber-300 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/25 font-['Outfit']">
                    <Lock className="w-3 h-3 text-amber-400" />
                    COMING SOON
                  </span>
                  <h3 className="text-2xl sm:text-3xl font-black text-slate-200 mt-3 font-['Cinzel'] tracking-wide">
                    PHASE 1
                  </h3>
                  <p className="text-[11px] text-slate-400 font-semibold mt-0.5">
                    Standard Admission Tier
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-3xl sm:text-4xl font-black text-slate-200 font-mono">₹799</div>
                  <div className="text-[11px] text-slate-400 font-semibold mt-0.5">Upcoming Phase</div>
                </div>
              </div>

              <div className="mt-6 pt-5 border-t border-white/[0.08] space-y-3 text-xs text-slate-400">
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-slate-500 shrink-0" />
                  <span>Full admission to NAVRANG 2026 celebration</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-slate-500 shrink-0" />
                  <span>Complimentary food voucher</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-slate-500 shrink-0" />
                  <span>Complimentary welcome drink / mocktail</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-slate-500 shrink-0" />
                  <span>Dandiya sticks provided</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-slate-500 shrink-0" />
                  <span>Standard access tier after Early Bird sells out</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-slate-500 shrink-0" />
                  <span>360° Video Booth & Live Musical Performances</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-slate-500 shrink-0" />
                  <span>Instant encrypted QR ticket delivery</span>
                </div>
              </div>

              <div className="mt-6 p-3.5 rounded-xl bg-amber-500/[0.06] border border-amber-500/20 text-center">
                <p className="text-xs text-amber-200/90 font-medium">
                  🔒 Phase 1 tickets will unlock once Early Bird phase concludes.
                </p>
              </div>
            </div>

            <div className="mt-8 relative z-10">
              <button
                type="button"
                disabled
                className="w-full py-4 rounded-2xl bg-white/[0.05] border border-white/10 text-slate-400 font-bold text-xs sm:text-sm uppercase tracking-wider flex items-center justify-center gap-2 cursor-not-allowed select-none opacity-80"
              >
                <Lock className="w-4 h-4 text-amber-400/80" />
                <span>🔒 LOCKED • COMING SOON</span>
              </button>
            </div>
          </div>

          {/* Card 3: GROUP OFFER (GROUP OF 10) */}
          <div className="p-7 sm:p-8 rounded-3xl glass-panel-gold border-2 border-[#d4af37]/70 flex flex-col justify-between relative overflow-hidden shadow-2xl shadow-[#d4af37]/20 group">
            {/* Badge in top right */}
            <div className="absolute top-4 right-4 flex items-center gap-1.5">
              <span className="text-[11px] font-black uppercase tracking-wider px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm">
                SAVE ₹991
              </span>
            </div>

            <div>
              <div className="text-center pt-2 pb-4 border-b border-white/[0.08]">
                <div className="text-[10px] font-extrabold uppercase tracking-[0.25em] text-[#d4af37] font-['Cinzel']">
                  POPULAR FOR SQUADS
                </div>
                <h3 className="text-2xl sm:text-3xl font-black text-white mt-1 uppercase font-['Cinzel'] tracking-wide">
                  GROUP OF 10
                </h3>
                <div className="mt-2 inline-flex items-center gap-2 text-xs font-bold text-[#f3e4b2] uppercase tracking-[0.2em]">
                  <span className="px-3 py-0.5 rounded-md bg-white/[0.07] border border-white/10">10 PASSES</span>
                  <span>•</span>
                  <span className="px-3 py-0.5 rounded-md bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 font-extrabold">SAVE ₹991</span>
                </div>
              </div>

              {/* Price comparison layout */}
              <div className="py-4 px-3 flex items-center justify-around text-center bg-black/40 rounded-2xl my-4 border border-white/[0.08]">
                <div>
                  <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">REGULAR</div>
                  <div className="text-base sm:text-lg font-bold font-mono text-slate-400 line-through decoration-rose-500 decoration-2 mt-1">
                    ₹5,990
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">10 × ₹599</div>
                </div>

                <div className="text-xl font-black text-[#d4af37]">↓</div>

                <div>
                  <div className="text-[10px] uppercase font-bold text-[#d4af37] tracking-wider">GROUP PASS</div>
                  <div className="text-2xl sm:text-3xl font-black font-mono bg-gradient-to-r from-white via-[#f3e4b2] to-[#d4af37] bg-clip-text text-transparent mt-0.5">
                    ₹4,999
                  </div>
                  <div className="text-[10px] font-bold text-emerald-400 mt-0.5">Save ₹991</div>
                </div>
              </div>

              {/* Value propositions */}
              <div className="space-y-2 text-xs text-slate-300">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Receive <strong>10 unique QR tickets</strong> — all 10 completely valid</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Complimentary <strong>food voucher</strong> for each person</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Complimentary <strong>welcome drink / mocktail</strong> for each person</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span><strong>Dandiya sticks provided</strong> for all 10 attendees</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Save <strong>₹991 instantly</strong> versus individual passes</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Ideal for families, colleagues, and dance groups</span>
                </div>
              </div>
            </div>

            <div className="mt-7 pt-3 border-t border-white/[0.08]">
              <Link
                to="/book?count=10&offer=EARLY_BIRD_GROUP_10"
                onClick={() => playDandiyaClick()}
                className="festive-button w-full py-4 rounded-2xl font-black text-xs sm:text-sm uppercase tracking-wider flex items-center justify-center gap-2 shadow-xl shadow-[#d4af37]/30 touch-target cursor-pointer"
              >
                <Ticket className="w-4 h-4" />
                <span>BOOK GROUP PASS</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>

        {/* Social Sharing Card */}
        <div className="mt-14 p-6 sm:p-8 rounded-3xl glass-panel border border-white/[0.08] max-w-3xl mx-auto text-center relative overflow-hidden">
          <div className="inline-flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wider text-[#d4af37] mb-2">
            <Users className="w-4 h-4 text-[#d4af37]" />
            <span>COMING WITH YOUR FRIENDS?</span>
          </div>
          <h3 className="text-xl sm:text-2xl font-black text-white uppercase font-['Outfit']">
            GROUP OF 10 — SAVE ₹991
          </h3>
          <p className="mt-1 text-xs text-slate-300 max-w-md mx-auto">
            Gather your squad, get the exclusive Group of 10 pass for ₹4,999, and save ₹991 together for NAVRANG 2026!
          </p>

          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <a
              href={`https://api.whatsapp.com/send?text=${encodeURIComponent(
                `🔥 NAVRANG 2026 is here! In collaboration with The Happy Circle.\n\nGet the Group of 10 Pass for ₹4,999 and save ₹991!\n\nLet's go together! 🎉\n` + (typeof window !== 'undefined' ? `${window.location.origin}/book?count=10&offer=EARLY_BIRD_GROUP_10` : '')
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
              <div className="font-bold text-white text-base">The Green Acres Location Pin</div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Located at The Green Acres, Mysuru. Easily navigable with broad access roads, drop-off bays, and dedicated parking for 1,500+ vehicles.
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
          <p className="mt-2 text-sm text-slate-400">Everything you need to know about booking and admission at The Green Acres, Mysuru</p>
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
