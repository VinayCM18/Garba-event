// Web Audio API Synthesizer for Festive Ambience & Dandiya Click Sounds
let audioCtx: AudioContext | null = null;
let ambientOsc1: OscillatorNode | null = null;
let ambientOsc2: OscillatorNode | null = null;
let ambientGain: GainNode | null = null;
let isPlayingAmbient = false;

function getAudioContext(): AudioContext {
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    audioCtx = new AudioContextClass();
  }
  if (audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
  return audioCtx;
}

/** Play a crisp wooden Dandiya click sound */
export function playDandiyaClick() {
  try {
    const ctx = getAudioContext();
    const now = ctx.currentTime;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    // High woodblock frequency burst
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(800, now);
    osc.frequency.exponentialRampToValueAtTime(1400, now + 0.02);
    osc.frequency.exponentialRampToValueAtTime(300, now + 0.08);

    gain.gain.setValueAtTime(0.3, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.09);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(now);
    osc.stop(now + 0.1);
  } catch (e) {
    // Audio context may not be allowed before user interaction
  }
}

/** Toggle soothing traditional Indian ambient drone (Sa-Pa Tanpura harmony) */
export function toggleAmbientSound(enable?: boolean): boolean {
  try {
    const ctx = getAudioContext();
    const shouldPlay = enable !== undefined ? enable : !isPlayingAmbient;

    if (shouldPlay && !isPlayingAmbient) {
      const now = ctx.currentTime;

      ambientOsc1 = ctx.createOscillator();
      ambientOsc2 = ctx.createOscillator();
      ambientGain = ctx.createGain();

      // Tonic (C#3 / 138.59 Hz) and Fifth (G#3 / 207.65 Hz) harmony
      ambientOsc1.type = 'sine';
      ambientOsc1.frequency.setValueAtTime(138.59, now);

      ambientOsc2.type = 'triangle';
      ambientOsc2.frequency.setValueAtTime(207.65, now);

      ambientGain.gain.setValueAtTime(0.01, now);
      ambientGain.gain.linearRampToValueAtTime(0.05, now + 2); // gentle fade in

      ambientOsc1.connect(ambientGain);
      ambientOsc2.connect(ambientGain);
      ambientGain.connect(ctx.destination);

      ambientOsc1.start(now);
      ambientOsc2.start(now);
      isPlayingAmbient = true;
      return true;
    } else if (!shouldPlay && isPlayingAmbient) {
      if (ambientGain && audioCtx) {
        ambientGain.gain.linearRampToValueAtTime(0.001, audioCtx.currentTime + 1);
        setTimeout(() => {
          try {
            ambientOsc1?.stop();
            ambientOsc2?.stop();
            ambientOsc1?.disconnect();
            ambientOsc2?.disconnect();
          } catch (e) {}
        }, 1100);
      }
      isPlayingAmbient = false;
      return false;
    }
    return isPlayingAmbient;
  } catch (e) {
    return false;
  }
}
