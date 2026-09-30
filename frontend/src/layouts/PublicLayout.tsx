import React, { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import { AnimatedFestiveBackground } from '../components/AnimatedFestiveBackground';
import { NavrangIntro } from '../components/NavrangIntro';

export const PublicLayout: React.FC = () => {
  const location = useLocation();

  // Show intro only on first visit (or when forced via ?intro=true in URL for testing)
  const [showIntro, setShowIntro] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    try {
      const params = new URLSearchParams(window.location.search);
      const forceIntro = params.get('intro') === 'true' || params.get('intro') === '1';
      if (forceIntro) return true;

      const hasSeen = localStorage.getItem('navrang_intro_seen');
      // Show on first visit when landing on the site/home page
      return !hasSeen && location.pathname === '/';
    } catch {
      return false;
    }
  });

  const handleIntroComplete = () => {
    setShowIntro(false);
    try {
      localStorage.setItem('navrang_intro_seen', 'true');
    } catch {
      // Ignore localStorage quota / private browsing errors
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#0b0914] text-slate-100 selection:bg-amber-500 selection:text-black font-['Plus_Jakarta_Sans'] relative">
      {/* Cinematic Splash Intro Overlay (First Visit or ?intro=true) */}
      {showIntro && <NavrangIntro onComplete={handleIntroComplete} />}

      {/* Animated Festive Background Layer */}
      <AnimatedFestiveBackground />

      {/* Content Layer */}
      <div className="relative z-10 flex flex-col min-h-screen">
        <Navbar />
        <div className="flex-1">
          <Outlet />
        </div>
        <Footer />
      </div>
    </div>
  );
};

