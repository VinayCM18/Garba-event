import React from 'react';
import { Outlet } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import { AnimatedFestiveBackground } from '../components/AnimatedFestiveBackground';

export const PublicLayout: React.FC = () => {
  return (
    <div className="min-h-screen flex flex-col bg-[#0b0914] text-slate-100 selection:bg-amber-500 selection:text-black font-['Plus_Jakarta_Sans'] relative">
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
