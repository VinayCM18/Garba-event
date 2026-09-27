import React, { useState, useEffect, useRef, useCallback } from 'react';
import jsQR from 'jsqr';
import {
  Camera,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  SwitchCamera,
  ShieldCheck,
  Search,
  Upload,
  Flashlight,
  Volume2,
  Clock,
  Zap,
  ArrowRight
} from 'lucide-react';
import { staffVerifyTicket, staffCheckInTicket } from '../services/api';
import { QRVerifyResult, CheckInResult } from '../types';
import { useToast } from '../components/Toast';

export const StaffScannerPage: React.FC = () => {
  const { success, error, warning } = useToast();

  const [cameraActive, setCameraActive] = useState(false);
  const [cameraFacing, setCameraFacing] = useState<'environment' | 'user'>('environment');
  const [availableDevices, setAvailableDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('');
  const [torchSupported, setTorchSupported] = useState(false);
  const [torchOn, setTorchOn] = useState(false);
  const [manualInput, setManualInput] = useState('');
  const [verifying, setVerifying] = useState(false);
  const [checkingIn, setCheckingIn] = useState(false);

  // Result state
  const [scanResult, setScanResult] = useState<QRVerifyResult | null>(null);
  const [scannedToken, setScannedToken] = useState<string>('');
  const [checkinSuccessInfo, setCheckinSuccessInfo] = useState<CheckInResult | null>(null);

  // Session check-in history
  const [sessionHistory, setSessionHistory] = useState<
    Array<{
      ticketId: string;
      customerName: string;
      result: string;
      time: string;
    }>
  >([]);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const animationFrameIdRef = useRef<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const lastScannedTimeRef = useRef<number>(0);
  const barcodeDetectorRef = useRef<any>(null);

  // Play crisp audio tone on detection
  const playBeep = (freq = 880, type: OscillatorType = 'sine') => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;
      const audioCtx = new AudioCtx();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.type = type;
      osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
      gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.18);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.2);
    } catch {
      // Audio autoplay permission guard
    }
  };

  const triggerHaptic = (pattern: number | number[] = 70) => {
    if (typeof navigator !== 'undefined' && 'vibrate' in navigator) {
      try {
        navigator.vibrate(pattern);
      } catch {}
    }
  };

  // Hardware BarcodeDetector
  useEffect(() => {
    if ('BarcodeDetector' in window) {
      try {
        barcodeDetectorRef.current = new (window as any).BarcodeDetector({
          formats: ['qr_code']
        });
      } catch {}
    }
  }, []);

  // Enumerate cameras
  useEffect(() => {
    navigator.mediaDevices?.enumerateDevices().then((devices) => {
      const videoDevs = devices.filter((d) => d.kind === 'videoinput');
      setAvailableDevices(videoDevs);
      if (videoDevs.length > 0 && !selectedDeviceId) {
        setSelectedDeviceId(videoDevs[0].deviceId);
      }
    });
  }, [selectedDeviceId]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  // Start Camera Stream
  const startCamera = async () => {
    stopCamera();
    try {
      const constraints: MediaStreamConstraints = {
        video: selectedDeviceId
          ? { deviceId: { exact: selectedDeviceId } }
          : {
              facingMode: cameraFacing,
              width: { ideal: 1920, min: 640 },
              height: { ideal: 1080, min: 480 },
              frameRate: { ideal: 30, max: 60 }
            },
        audio: false
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      mediaStreamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.setAttribute('playsinline', 'true');
        await videoRef.current.play();
      }

      setCameraActive(true);

      const track = stream.getVideoTracks()[0];
      const capabilities: any = track.getCapabilities?.() || {};
      setTorchSupported(!!capabilities.torch);

      requestAnimationFrame(scanVideoFrame);
    } catch (err: any) {
      error('Camera Error', 'Could not start camera. Please ensure camera permissions are allowed.');
      setCameraActive(false);
    }
  };

  const stopCamera = () => {
    if (animationFrameIdRef.current) {
      cancelAnimationFrame(animationFrameIdRef.current);
      animationFrameIdRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setCameraActive(false);
    setTorchOn(false);
  };

  const toggleTorch = async () => {
    if (!mediaStreamRef.current) return;
    const track = mediaStreamRef.current.getVideoTracks()[0];
    if (track && torchSupported) {
      try {
        const next = !torchOn;
        await track.applyConstraints({ advanced: [{ torch: next } as any] });
        setTorchOn(next);
      } catch {}
    }
  };

  const toggleCameraFacing = () => {
    const nextFacing = cameraFacing === 'environment' ? 'user' : 'environment';
    setCameraFacing(nextFacing);
    stopCamera();
    setTimeout(() => {
      startCamera();
    }, 200);
  };

  // Continuous Camera Frame Scanner
  const scanVideoFrame = async () => {
    if (!videoRef.current || videoRef.current.readyState !== videoRef.current.HAVE_ENOUGH_DATA) {
      animationFrameIdRef.current = requestAnimationFrame(scanVideoFrame);
      return;
    }

    const video = videoRef.current;
    const now = Date.now();

    // 250ms throttle between scan attempts
    if (now - lastScannedTimeRef.current > 250) {
      let detectedCode: string | null = null;

      if (barcodeDetectorRef.current) {
        try {
          const barcodes = await barcodeDetectorRef.current.detect(video);
          if (barcodes.length > 0) {
            detectedCode = barcodes[0].rawValue;
          }
        } catch {}
      }

      if (!detectedCode && canvasRef.current) {
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        if (ctx) {
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
          const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
          const qr = jsQR(imageData.data, imageData.width, imageData.height, {
            inversionAttempts: 'attemptBoth'
          });
          if (qr && qr.data) {
            detectedCode = qr.data;
          }
        }
      }

      if (detectedCode && detectedCode.trim() !== '') {
        lastScannedTimeRef.current = now;
        playBeep(1046);
        triggerHaptic([60, 40, 60]);
        handleScannedPayload(detectedCode);
      }
    }

    animationFrameIdRef.current = requestAnimationFrame(scanVideoFrame);
  };

  // Handle scanned QR payload
  const handleScannedPayload = useCallback(
    async (rawCode: string) => {
      let cleaned = rawCode.trim();
      if (cleaned.includes('/ticket/')) {
        cleaned = cleaned.split('/ticket/')[1].split('?')[0].split('#')[0].trim();
      }

      setScannedToken(cleaned);
      setVerifying(true);
      setCheckinSuccessInfo(null);

      try {
        const res: QRVerifyResult = await staffVerifyTicket(cleaned);
        setScanResult(res);

        if (res.valid && res.status === 'VALID') {
          playBeep(980);
          triggerHaptic(100);
          success('Valid Ticket!', `${res.customer_name} (${res.ticket_id})`);
        } else if (res.status === 'USED') {
          playBeep(440, 'triangle');
          triggerHaptic([100, 80, 100]);
          warning('Ticket Already Used', res.message);
        } else {
          playBeep(260, 'sawtooth');
          triggerHaptic([200]);
          error('Invalid Ticket', res.message);
        }
      } catch (err: any) {
        const msg = err.response?.data?.detail || 'Failed to verify ticket with gate backend.';
        setScanResult({
          valid: false,
          status: 'INVALID',
          message: msg
        });
        error('Verification Error', msg);
      } finally {
        setVerifying(false);
      }
    },
    [error, success, warning]
  );

  // Check In attendee atomically
  const handleCheckIn = async () => {
    const tokenToSubmit = scannedToken || scanResult?.qr_token_raw || scanResult?.ticket_id;
    if (!tokenToSubmit) return;

    setCheckingIn(true);
    try {
      const res: CheckInResult = await staffCheckInTicket({
        qr_token: tokenToSubmit,
        device_information: 'Staff Optical Scanner Pro',
        notes: 'Gate entry verified'
      });

      setCheckinSuccessInfo(res);
      playBeep(1318);
      triggerHaptic([80, 50, 80, 50, 120]);
      success('Checked In!', `${res.customer_name} admitted!`);

      // Add to session history
      setSessionHistory((prev) => [
        {
          ticketId: res.ticket_id || tokenToSubmit,
          customerName: res.customer_name || 'Guest',
          result: 'SUCCESS',
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        },
        ...prev.slice(0, 19)
      ]);

      // Update state to show checked in
      setScanResult((prev) =>
        prev
          ? {
              ...prev,
              status: 'USED',
              checkin_status: true,
              message: `⚠️ Ticket Already Checked In at Just now (Ticket: ${res.ticket_id})`
            }
          : null
      );
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Check-in failed or ticket already checked in.';
      error('Check-in Rejected', msg);
      if (err.response?.status === 409) {
        warning('Already Checked In', msg);
        setScanResult((prev) =>
          prev
            ? {
                ...prev,
                status: 'USED',
                checkin_status: true,
                message: msg
              }
            : null
        );
      }
    } finally {
      setCheckingIn(false);
    }
  };

  const resetScannerState = () => {
    setScanResult(null);
    setScannedToken('');
    setCheckinSuccessInfo(null);
    setManualInput('');
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/25 text-emerald-400 text-xs font-bold uppercase tracking-wider mb-2">
            <Zap className="w-3.5 h-3.5" />
            <span>Turnstile Mode • 30 FPS Scanner</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white font-['Outfit']">
            Staff Gate Scanner
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Aim camera at visitor QR pass or enter Ticket ID / phone number below.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {!cameraActive ? (
            <button
              onClick={startCamera}
              className="festive-button px-5 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow-lg shadow-emerald-500/20"
            >
              <Camera className="w-4 h-4" />
              <span>Start Camera</span>
            </button>
          ) : (
            <button
              onClick={stopCamera}
              className="px-4 py-2.5 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 text-rose-300 text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-colors"
            >
              <XCircle className="w-4 h-4" />
              <span>Stop Camera</span>
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Live Camera & Scanner Viewport */}
        <div className="lg:col-span-7 space-y-4">
          <div className="rounded-3xl glass-panel border border-white/[0.08] overflow-hidden relative bg-black shadow-2xl">
            {/* Viewfinder Window */}
            <div className="relative aspect-[4/3] sm:aspect-video flex items-center justify-center overflow-hidden bg-[#05060b]">
              <video
                ref={videoRef}
                className={`w-full h-full object-cover transition-opacity duration-300 ${
                  cameraActive ? 'opacity-100' : 'opacity-0 absolute pointer-events-none'
                }`}
                muted
              />
              <canvas ref={canvasRef} className="hidden" />

              {!cameraActive && (
                <div className="text-center p-8 z-10">
                  <div className="w-16 h-16 rounded-2xl bg-white/[0.04] border border-white/10 flex items-center justify-center mx-auto mb-4 text-emerald-400">
                    <Camera className="w-8 h-8" />
                  </div>
                  <h3 className="text-base font-bold text-white font-['Outfit'] mb-1">
                    Camera Inactive
                  </h3>
                  <p className="text-xs text-slate-400 max-w-xs mx-auto mb-4">
                    Tap below to activate your mobile or tablet camera for optical QR gate scanning.
                  </p>
                  <button
                    onClick={startCamera}
                    className="festive-button px-6 py-3 rounded-xl text-xs font-bold uppercase tracking-wider inline-flex items-center gap-2 shadow-lg shadow-emerald-500/20"
                  >
                    <Camera className="w-4 h-4" />
                    <span>Launch Scanner</span>
                  </button>
                </div>
              )}

              {/* Optical targeting reticle when active */}
              {cameraActive && (
                <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                  <div className="w-64 h-64 sm:w-72 sm:h-72 border-2 border-emerald-400/60 rounded-3xl relative shadow-[0_0_50px_rgba(52,211,153,0.25)] flex items-center justify-center">
                    {/* Corner accents */}
                    <div className="absolute -top-1 -left-1 w-6 h-6 border-t-4 border-l-4 border-emerald-400 rounded-tl-xl" />
                    <div className="absolute -top-1 -right-1 w-6 h-6 border-t-4 border-r-4 border-emerald-400 rounded-tr-xl" />
                    <div className="absolute -bottom-1 -left-1 w-6 h-6 border-b-4 border-l-4 border-emerald-400 rounded-bl-xl" />
                    <div className="absolute -bottom-1 -right-1 w-6 h-6 border-b-4 border-r-4 border-emerald-400 rounded-br-xl" />

                    {/* Animated scanning laser line */}
                    <div className="absolute inset-x-3 h-0.5 bg-gradient-to-r from-transparent via-emerald-400 to-transparent shadow-[0_0_12px_#34d399] animate-pulse" />

                    <div className="absolute bottom-3 text-[10px] uppercase font-bold tracking-widest text-emerald-300 bg-black/60 px-3 py-1 rounded-full backdrop-blur-sm">
                      Align QR Inside Frame
                    </div>
                  </div>
                </div>
              )}

              {/* In-view camera controls */}
              {cameraActive && (
                <div className="absolute top-4 right-4 flex items-center gap-2 z-20">
                  {torchSupported && (
                    <button
                      onClick={toggleTorch}
                      className={`p-2.5 rounded-xl border transition-all ${
                        torchOn
                          ? 'bg-amber-400 text-black border-amber-300 shadow-lg shadow-amber-400/30'
                          : 'bg-black/60 text-white border-white/20 hover:bg-black/80'
                      }`}
                      title="Toggle Flashlight"
                    >
                      <Flashlight className="w-4 h-4" />
                    </button>
                  )}
                  <button
                    onClick={toggleCameraFacing}
                    className="p-2.5 rounded-xl bg-black/60 text-white border border-white/20 hover:bg-black/80 transition-all"
                    title="Switch Camera Facing"
                  >
                    <SwitchCamera className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>

            {/* Quick manual entry bar below camera */}
            <div className="p-4 border-t border-white/[0.08] bg-[#0c0d16]">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (manualInput.trim()) {
                    handleScannedPayload(manualInput.trim());
                  }
                }}
                className="flex items-center gap-2"
              >
                <div className="relative flex-1">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={manualInput}
                    onChange={(e) => setManualInput(e.target.value)}
                    placeholder="Enter Ticket ID, Booking ID, or Phone..."
                    className="w-full pl-10 pr-3 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white placeholder-slate-500 text-xs focus:outline-none focus:border-emerald-400 transition-colors font-mono"
                  />
                </div>
                <button
                  type="submit"
                  disabled={verifying || !manualInput.trim()}
                  className="px-4 py-2.5 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 text-xs font-bold uppercase tracking-wider disabled:opacity-40 transition-all flex items-center gap-1.5"
                >
                  {verifying ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <span>Verify</span>}
                </button>
              </form>
            </div>
          </div>
        </div>

        {/* Right Column: Instant Verification & Check-in Result Card */}
        <div className="lg:col-span-5 space-y-4">
          <div className="p-6 rounded-3xl glass-panel border border-white/[0.08] relative overflow-hidden">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-bold text-white font-['Outfit']">
                Gate Verification Result
              </h2>
              {scanResult && (
                <button
                  onClick={resetScannerState}
                  className="text-xs text-slate-400 hover:text-white transition-colors"
                >
                  Clear Result
                </button>
              )}
            </div>

            {!scanResult ? (
              <div className="py-12 text-center">
                <div className="w-12 h-12 rounded-2xl bg-white/[0.03] border border-white/5 flex items-center justify-center mx-auto mb-3 text-slate-500">
                  <ShieldCheck className="w-6 h-6" />
                </div>
                <div className="text-xs font-bold text-slate-300">Ready to Scan</div>
                <p className="text-[11px] text-slate-500 mt-1 max-w-xs mx-auto">
                  Scan a digital pass or paper ticket to view attendee confirmation and grant entry.
                </p>
              </div>
            ) : (
              <div className="space-y-5">
                {/* Result Status Banner */}
                {scanResult.status === 'VALID' && !scanResult.checkin_status ? (
                  <div className="p-4 rounded-2xl bg-emerald-500/15 border-2 border-emerald-500/40 text-center">
                    <div className="w-12 h-12 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center mx-auto mb-2 text-emerald-400">
                      <CheckCircle2 className="w-6 h-6" />
                    </div>
                    <div className="text-lg font-black text-emerald-300 uppercase tracking-wider font-['Outfit']">
                      ✓ VALID TICKET
                    </div>
                    <div className="text-xs text-emerald-400/90 font-medium mt-0.5">
                      Ready for admission turnstile check-in
                    </div>
                  </div>
                ) : scanResult.status === 'USED' || scanResult.checkin_status ? (
                  <div className="p-4 rounded-2xl bg-amber-500/15 border-2 border-amber-500/40 text-center">
                    <div className="w-12 h-12 rounded-full bg-amber-500/20 border border-amber-500/40 flex items-center justify-center mx-auto mb-2 text-amber-400">
                      <AlertTriangle className="w-6 h-6" />
                    </div>
                    <div className="text-lg font-black text-amber-300 uppercase tracking-wider font-['Outfit']">
                      ⚠️ Ticket Already Checked In
                    </div>
                    <div className="text-xs text-amber-300/90 mt-1 font-mono">
                      {scanResult.checked_in_at
                        ? `Time: ${new Date(scanResult.checked_in_at).toLocaleTimeString()}`
                        : 'Already Scanned'}
                    </div>
                    <div className="text-[11px] text-amber-200/80 mt-1">
                      Duplicate entry strictly prohibited.
                    </div>
                  </div>
                ) : (
                  <div className="p-4 rounded-2xl bg-rose-500/15 border-2 border-rose-500/40 text-center">
                    <div className="w-12 h-12 rounded-full bg-rose-500/20 border border-rose-500/40 flex items-center justify-center mx-auto mb-2 text-rose-400">
                      <XCircle className="w-6 h-6" />
                    </div>
                    <div className="text-lg font-black text-rose-300 uppercase tracking-wider font-['Outfit']">
                      ❌ Invalid Ticket
                    </div>
                    <div className="text-xs text-rose-400 mt-1">
                      {scanResult.message}
                    </div>
                  </div>
                )}

                {/* Attendee Details Card */}
                {scanResult.customer_name && (
                  <div className="p-4 rounded-2xl bg-black/40 border border-white/[0.08] space-y-3">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400 font-bold uppercase text-[10px]">Attendee Name</span>
                      <span className="font-black text-white text-sm">{scanResult.customer_name}</span>
                    </div>

                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400 font-bold uppercase text-[10px]">Ticket ID</span>
                      <span className="font-mono font-bold text-emerald-400">{scanResult.ticket_id}</span>
                    </div>

                    {scanResult.booking_id && (
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-400 font-bold uppercase text-[10px]">Booking Reference</span>
                        <span className="font-mono text-slate-300">{scanResult.booking_id}</span>
                      </div>
                    )}

                    <div className="flex items-center justify-between text-xs pt-2 border-t border-white/[0.06]">
                      <span className="text-slate-400 font-bold uppercase text-[10px]">Event Access</span>
                      <span className="text-xs font-semibold text-slate-200">NAVRANG 2026 • General Arena</span>
                    </div>
                  </div>
                )}

                {/* Check In Action Button */}
                {scanResult.valid && !scanResult.checkin_status && (
                  <button
                    onClick={handleCheckIn}
                    disabled={checkingIn}
                    className="festive-button w-full py-4 rounded-2xl font-black text-sm uppercase tracking-wider flex items-center justify-center gap-2 shadow-xl shadow-emerald-500/25 transition-all"
                  >
                    {checkingIn ? (
                      <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                      <>
                        <CheckCircle2 className="w-5 h-5" />
                        <span>Confirm Check-In & Admit Guest</span>
                        <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>
                )}

                {checkinSuccessInfo && (
                  <div className="p-3.5 rounded-xl bg-emerald-500/20 border border-emerald-400/40 text-emerald-300 text-xs flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                    <span>Gate entry logged by {checkinSuccessInfo.staff_name || 'Staff'}.</span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Session History List */}
          {sessionHistory.length > 0 && (
            <div className="p-5 rounded-2xl glass-panel border border-white/[0.08]">
              <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
                Scans this Session ({sessionHistory.length})
              </div>
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {sessionHistory.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.05] flex items-center justify-between text-xs"
                  >
                    <div>
                      <div className="font-bold text-white">{item.customerName}</div>
                      <div className="text-[10px] text-slate-400 font-mono">{item.ticketId}</div>
                    </div>
                    <div className="text-right">
                      <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                        {item.result}
                      </span>
                      <div className="text-[9px] text-slate-500 mt-0.5">{item.time}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
