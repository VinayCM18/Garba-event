import React, { useMemo } from 'react';
import { motion } from 'framer-motion';

export const AnimatedFestiveBackground: React.FC = () => {
  // Generate subtle, elegant floating golden stardust particles
  const particles = useMemo(() => {
    return Array.from({ length: 30 }).map((_, i) => ({
      id: i,
      x: Math.random() * 100, // percentage
      size: Math.random() * 3 + 1.5, // 1.5px to 4.5px (delicate micro-stardust)
      duration: Math.random() * 10 + 10, // slow, gentle float (10s to 20s)
      delay: Math.random() * 6,
      opacity: Math.random() * 0.45 + 0.2, // soft, never blinding
    }));
  }, []);

  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
      {/* 1. Base Picture Background with Dark Luxury Vignette */}
      <div
        className="absolute inset-0 bg-cover bg-top bg-no-repeat opacity-25 mix-blend-luminosity scale-100 transition-transform duration-1000 ease-out"
        style={{
          backgroundImage: "url('/garba-bg.jpg')",
          backgroundPosition: 'center top',
        }}
      />

      {/* 2. Deep Royal Obsidian Gradient Overlay for high-end legibility */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#06070c]/85 via-[#06070c]/75 to-[#06070c]/98" />

      {/* 3. Subtle Celestial Ambient Halo (Refined Champagne & Royal Sapphire) */}
      <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[850px] h-[550px] bg-gradient-to-b from-[#d4af37]/10 via-[#1e1b4b]/15 to-transparent rounded-full blur-3xl pointer-events-none" />

      {/* 4. Delicate Sacred Geometric Mandala (Subtle Hairline Gold Accent) */}
      <div className="absolute top-12 right-[-60px] w-96 h-96 opacity-[0.08] pointer-events-none animate-[spin_120s_linear_infinite]">
        <svg viewBox="0 0 200 200" className="w-full h-full text-[#d4af37] fill-none stroke-current stroke-[0.6]">
          <circle cx="100" cy="100" r="90" />
          <circle cx="100" cy="100" r="70" strokeDasharray="4 4" />
          <circle cx="100" cy="100" r="50" />
          <path d="M100 10 L100 190 M10 100 L190 100 M36 36 L164 164 M36 164 L164 36" />
          {Array.from({ length: 12 }).map((_, idx) => (
            <circle
              key={idx}
              cx={100 + 60 * Math.cos((idx * Math.PI) / 6)}
              cy={100 + 60 * Math.sin((idx * Math.PI) / 6)}
              r="6"
            />
          ))}
        </svg>
      </div>

      <div className="absolute top-96 left-[-80px] w-80 h-80 opacity-[0.06] pointer-events-none animate-[spin_140s_linear_infinite_reverse]">
        <svg viewBox="0 0 200 200" className="w-full h-full text-[#e5c97b] fill-none stroke-current stroke-[0.6]">
          <circle cx="100" cy="100" r="85" strokeDasharray="6 3" />
          <circle cx="100" cy="100" r="60" />
          <circle cx="100" cy="100" r="35" />
          <path d="M100 15 L100 185 M15 100 L185 100" />
        </svg>
      </div>

      {/* 5. Delicate Floating Stardust (Soft Champagne Embers) */}
      {particles.map((p) => (
        <motion.div
          key={p.id}
          className="absolute rounded-full bg-[#f3e4b2] shadow-[0_0_6px_rgba(212,175,55,0.4)]"
          style={{
            left: `${p.x}%`,
            width: `${p.size}px`,
            height: `${p.size}px`,
            bottom: '-15px',
          }}
          animate={{
            y: ['0vh', '-105vh'],
            x: [0, (p.id % 2 === 0 ? 25 : -25), 0],
            opacity: [0, p.opacity, p.opacity * 0.7, 0],
            scale: [0.7, 1.1, 0.5],
          }}
          transition={{
            duration: p.duration,
            repeat: Infinity,
            delay: p.delay,
            ease: 'easeInOut',
          }}
        />
      ))}

      {/* 6. Subtle Atmospheric Base Floor Glow */}
      <div className="absolute bottom-0 inset-x-0 h-48 bg-gradient-to-t from-[#06070c] via-[#06070c]/70 to-transparent pointer-events-none" />
    </div>
  );
};
