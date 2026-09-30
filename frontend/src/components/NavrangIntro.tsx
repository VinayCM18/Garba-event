import React, { useEffect, useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface NavrangIntroProps {
  onComplete: () => void;
}

type IntroScene = 'HERITAGE' | 'HAPPY_CIRCLE' | 'NAVRANG' | 'EXIT';

export const NavrangIntro: React.FC<NavrangIntroProps> = ({ onComplete }) => {
  const [scene, setScene] = useState<IntroScene>('HERITAGE');

  // Preload logo assets on mount for immediate, smooth rendering
  useEffect(() => {
    const img1 = new Image();
    img1.src = '/heritage_productions.jpg';
    const img2 = new Image();
    img2.src = '/images/happy-circle-logo.png';
  }, []);

  // Check reduced motion preference
  const prefersReducedMotion = useMemo(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }, []);

  // Scene timing sequence (Total approx 5.5 seconds)
  useEffect(() => {
    if (prefersReducedMotion) {
      // For reduced motion: show brief static intro then exit gently
      const t = setTimeout(() => {
        setScene('EXIT');
      }, 1200);
      return () => clearTimeout(t);
    }

    const t1 = setTimeout(() => {
      setScene('HAPPY_CIRCLE');
    }, 1600); // 0s - 1.6s Scene 1

    const t2 = setTimeout(() => {
      setScene('NAVRANG');
    }, 3400); // 1.6s - 3.4s Scene 2

    const t3 = setTimeout(() => {
      setScene('EXIT');
    }, 5500); // 3.4s - 5.5s Scene 3 -> 5.5s Transition to site

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, [prefersReducedMotion]);

  // Handle immediate skip
  const handleSkip = () => {
    setScene('EXIT');
  };

  // Subtle floating golden stardust particles
  const particles = useMemo(() => {
    return Array.from({ length: 22 }).map((_, i) => ({
      id: i,
      x: (i * 4.5 + Math.random() * 4) % 100,
      size: (i % 3 === 0 ? 3 : 2) + Math.random() * 1.5,
      duration: 5 + (i % 5) * 1.5,
      delay: (i % 4) * 0.4,
      opacity: 0.25 + (i % 4) * 0.12,
    }));
  }, []);

  return (
    <AnimatePresence onExitComplete={onComplete}>
      {scene !== 'EXIT' && (
        <motion.div
          key="navrang-cinematic-intro"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, transition: { duration: 0.65, ease: [0.4, 0, 0.2, 1] } }}
          className="fixed inset-0 z-[99999] w-screen h-[100dvh] bg-[#050308] text-white flex flex-col items-center justify-center overflow-hidden select-none"
          role="dialog"
          aria-modal="true"
          aria-label="NAVRANG 2026 Cinematic Introduction"
        >
          {/* Subtle Ambient Radial Lighting */}
          <div className="absolute inset-0 pointer-events-none">
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] bg-gradient-to-b from-[#d4af37]/12 via-[#7f1d1d]/8 to-transparent rounded-full blur-[120px]" />
            <div className="absolute inset-0 bg-radial from-transparent via-[#050308]/60 to-[#050308]" />
          </div>

          {/* Delicate Floating Golden Particles */}
          <div className="absolute inset-0 pointer-events-none overflow-hidden">
            {particles.map((p) => (
              <motion.div
                key={p.id}
                className="absolute rounded-full bg-[#f3e4b2] shadow-[0_0_6px_rgba(212,175,55,0.6)]"
                style={{
                  left: `${p.x}%`,
                  width: `${p.size}px`,
                  height: `${p.size}px`,
                  bottom: '-10px',
                }}
                animate={{
                  y: ['0vh', '-105vh'],
                  opacity: [0, p.opacity, p.opacity * 0.8, 0],
                }}
                transition={{
                  duration: p.duration,
                  repeat: Infinity,
                  delay: p.delay,
                  ease: 'easeInOut',
                }}
              />
            ))}
          </div>

          {/* Center Cinematic Stage */}
          <div className="relative z-10 w-full max-w-4xl px-6 flex flex-col items-center justify-center min-h-[380px]">
            <AnimatePresence mode="wait">
              {/* ============================================================ */}
              {/* SCENE 1 — HERITAGE PRODUCTIONS                                */}
              {/* ============================================================ */}
              {scene === 'HERITAGE' && (
                <motion.div
                  key="scene-heritage"
                  initial={{ opacity: 0, scale: 0.94 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 1.02, transition: { duration: 0.45, ease: 'easeOut' } }}
                  transition={{ duration: 0.65, ease: [0.16, 1, 0.3, 1] }}
                  className="flex flex-col items-center text-center"
                >
                  {/* Heritage Productions Official Logo */}
                  <div className="relative w-28 h-28 sm:w-36 sm:h-36 md:w-44 md:h-44 rounded-full p-[2.5px] bg-gradient-to-b from-[#f7e8c3] via-[#d4af37] to-[#1a1224] shadow-[0_0_40px_rgba(212,175,55,0.35)] flex items-center justify-center overflow-hidden bg-black">
                    <img
                      src="/heritage_productions.jpg"
                      alt="Heritage Productions"
                      className="w-full h-full object-cover rounded-full"
                    />
                    {/* Soft golden perimeter glow */}
                    <div className="absolute inset-0 rounded-full ring-1 ring-inset ring-[#d4af37]/40 pointer-events-none" />
                  </div>

                  {/* Elegant Heritage Title */}
                  <motion.h2
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.25, duration: 0.55 }}
                    className="mt-4 text-xs sm:text-sm md:text-base font-black tracking-[0.3em] uppercase text-[#f7e8c3] font-['Cinzel']"
                  >
                    HERITAGE PRODUCTIONS
                  </motion.h2>

                  {/* PRESENTS Sub-reveal */}
                  <motion.div
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.55, duration: 0.55 }}
                    className="mt-3 flex items-center gap-3"
                  >
                    <span className="h-px w-8 sm:w-16 bg-gradient-to-r from-transparent to-[#d4af37]/60" />
                    <span className="text-[11px] sm:text-xs font-bold tracking-[0.4em] uppercase text-[#d4af37] font-['Cinzel']">
                      PRESENTS
                    </span>
                    <span className="h-px w-8 sm:w-16 bg-gradient-to-l from-transparent to-[#d4af37]/60" />
                  </motion.div>
                </motion.div>
              )}

              {/* ============================================================ */}
              {/* SCENE 2 — THE HAPPY CIRCLE                                   */}
              {/* ============================================================ */}
              {scene === 'HAPPY_CIRCLE' && (
                <motion.div
                  key="scene-happy-circle"
                  initial={{ opacity: 0, y: 12, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, scale: 1.02, transition: { duration: 0.45, ease: 'easeOut' } }}
                  transition={{ duration: 0.65, ease: [0.16, 1, 0.3, 1] }}
                  className="flex flex-col items-center text-center"
                >
                  {/* Subtle golden backdrop sweep */}
                  <div className="relative">
                    <div className="absolute inset-0 rounded-full bg-gradient-to-b from-[#d4af37]/25 to-transparent blur-2xl scale-125 pointer-events-none" />

                    {/* Actual The Happy Circle Logo Asset */}
                    <div className="relative w-28 h-28 sm:w-36 sm:h-36 md:w-44 md:h-44 rounded-full p-[2.5px] bg-gradient-to-b from-[#f7e8c3] via-[#d4af37] to-[#1a1224] shadow-[0_0_40px_rgba(212,175,55,0.4)] flex items-center justify-center overflow-hidden bg-black">
                      <img
                        src="/images/happy-circle-logo.png"
                        alt="The Happy Circle"
                        className="w-full h-full object-contain rounded-full"
                      />
                      <div className="absolute inset-0 rounded-full ring-1 ring-inset ring-[#d4af37]/40 pointer-events-none" />
                    </div>
                  </div>

                  {/* Brand Name */}
                  <motion.h2
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.25, duration: 0.55 }}
                    className="mt-4 text-xs sm:text-sm md:text-base font-black tracking-[0.25em] uppercase text-[#f7e8c3] font-['Outfit']"
                  >
                    THE HAPPY CIRCLE
                  </motion.h2>

                  {/* IN COLLABORATION WITH */}
                  <motion.div
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.55, duration: 0.55 }}
                    className="mt-3 flex items-center gap-3"
                  >
                    <span className="h-px w-8 sm:w-16 bg-gradient-to-r from-transparent to-[#d4af37]/60" />
                    <span className="text-[10px] sm:text-[11px] font-bold tracking-[0.32em] uppercase text-[#d4af37] font-['Cinzel']">
                      IN COLLABORATION WITH
                    </span>
                    <span className="h-px w-8 sm:w-16 bg-gradient-to-l from-transparent to-[#d4af37]/60" />
                  </motion.div>
                </motion.div>
              )}

              {/* ============================================================ */}
              {/* SCENE 3 — NAVRANG 2026 REVEAL                                */}
              {/* ============================================================ */}
              {scene === 'NAVRANG' && (
                <motion.div
                  key="scene-navrang"
                  initial={{ opacity: 0, scale: 0.94 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 1.03, transition: { duration: 0.5, ease: 'easeOut' } }}
                  transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
                  className="relative flex flex-col items-center text-center"
                >
                  {/* Very Subtle Mandala Pattern Behind the Title */}
                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-72 h-72 sm:w-96 sm:h-96 md:w-[480px] md:h-[480px] pointer-events-none opacity-[0.09] animate-[spin_100s_linear_infinite]">
                    <svg viewBox="0 0 200 200" className="w-full h-full text-[#d4af37] fill-none stroke-current stroke-[0.7]">
                      <circle cx="100" cy="100" r="92" />
                      <circle cx="100" cy="100" r="74" strokeDasharray="4 4" />
                      <circle cx="100" cy="100" r="54" />
                      <path d="M100 8 L100 192 M8 100 L192 100 M35 35 L165 165 M35 165 L165 35" />
                      {Array.from({ length: 8 }).map((_, idx) => (
                        <circle
                          key={idx}
                          cx={100 + 64 * Math.cos((idx * Math.PI) / 4)}
                          cy={100 + 64 * Math.sin((idx * Math.PI) / 4)}
                          r="8"
                        />
                      ))}
                    </svg>
                  </div>

                  {/* Main Event Title: NAVRANG */}
                  <motion.div
                    initial={{ opacity: 0, y: 14 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.15, duration: 0.75, ease: [0.16, 1, 0.3, 1] }}
                    className="relative"
                  >
                    <h1 className="text-5xl sm:text-7xl md:text-8xl lg:text-9xl font-black tracking-[0.14em] uppercase font-['Cinzel'] bg-gradient-to-b from-[#ffffff] via-[#faeed1] to-[#c59a35] bg-clip-text text-transparent drop-shadow-[0_0_40px_rgba(212,175,55,0.45)]">
                      NAVRANG
                    </h1>

                    {/* Subtle Golden Shimmer / Light Sweep Line across Title */}
                    <motion.div
                      initial={{ left: '-20%', opacity: 0 }}
                      animate={{ left: '120%', opacity: [0, 0.75, 0] }}
                      transition={{ delay: 0.6, duration: 1.1, ease: 'easeInOut' }}
                      className="absolute top-0 bottom-0 w-24 bg-gradient-to-r from-transparent via-[#ffffff]/40 to-transparent skew-x-[-25deg] pointer-events-none"
                    />
                  </motion.div>

                  {/* Year: 2026 */}
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5, duration: 0.6 }}
                    className="mt-2 sm:mt-3 flex items-center justify-center gap-3 sm:gap-4"
                  >
                    <span className="text-[#d4af37]/80 text-xs sm:text-sm">✦</span>
                    <span className="text-2xl sm:text-3xl md:text-4xl font-extrabold tracking-[0.35em] text-[#f7e8c3] font-['Cinzel'] drop-shadow-[0_0_20px_rgba(212,175,55,0.35)]">
                      2026
                    </span>
                    <span className="text-[#d4af37]/80 text-xs sm:text-sm">✦</span>
                  </motion.div>

                  {/* Elegant Cultural Subtitle */}
                  <motion.p
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.8, duration: 0.6 }}
                    className="mt-4 sm:mt-5 text-[10px] sm:text-xs md:text-sm tracking-[0.25em] sm:tracking-[0.3em] font-medium uppercase text-[#e2d5bc] font-['Plus_Jakarta_Sans'] max-w-lg"
                  >
                    A Celebration of Culture • Music • Togetherness
                  </motion.p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Minimal Elegant Skip Button (Bottom Right) */}
          <motion.button
            type="button"
            onClick={handleSkip}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.4 }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            aria-label="Skip introduction"
            className="fixed bottom-6 right-6 z-[100000] group flex items-center gap-2 px-4 py-2 rounded-full bg-black/45 hover:bg-[#d4af37]/20 border border-[#d4af37]/35 hover:border-[#d4af37]/70 text-[#f3e4b2] text-[11px] sm:text-xs font-bold tracking-[0.2em] uppercase backdrop-blur-md transition-all duration-300 shadow-[0_4px_24px_rgba(0,0,0,0.6)] cursor-pointer"
          >
            <span>SKIP</span>
            <span className="transition-transform duration-300 group-hover:translate-x-1 text-[#d4af37]">
              →
            </span>
          </motion.button>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default NavrangIntro;
