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
  Sparkles,
  Zap
} from 'lucide-react';
import { verifyQR, checkInQR } from '../services/api';
import { QRVerifyResult, CheckInResult } from '../types';
import { useToast } from '../components/Toast';

export const AdminScannerPage: React.FC = () => {
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
  const isVerifyingRef = useRef<boolean>(false);
  const lastVerifiedTokenRef = useRef<string>('');
  const lastVerifiedTimeRef = useRef<number>(0);
  const barcodeDetectorRef = useRef<any>(null);

  // Play crisp audio beep on successful detection
  const playBeep = () => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;
      const audioCtx = new AudioCtx();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.type = 'sine';
      osc.frequency.setValueAtTime(880, audioCtx.currentTime); // 880 Hz
      gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.16);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.16);
    } catch {
      // Audio context blocked
    }
  };

  // Initialize native BarcodeDetector if available in browser
  useEffect(() => {
    if ('BarcodeDetector' in window) {
      try {
        barcodeDetectorRef.current = new (window as any).BarcodeDetector({ formats: ['qr_code'] });
      } catch {
        barcodeDetectorRef.current = null;
      }
    }
  }, []);

  // Enumerate available video inputs
  const refreshDevices = useCallback(async () => {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoInputs = devices.filter((d) => d.kind === 'videoinput');
      setAvailableDevices(videoInputs);
      if (videoInputs.length > 0 && !selectedDeviceId) {
        // Prefer rear/environment camera
        const backCam = videoInputs.find(
          (d) => d.label.toLowerCase().includes('back') || d.label.toLowerCase().includes('rear') || d.label.toLowerCase().includes('environment')
        );
        setSelectedDeviceId(backCam ? backCam.deviceId : videoInputs[0].deviceId);
      }
    } catch (err) {
      console.warn('Unable to enumerate camera devices:', err);
    }
  }, [selectedDeviceId]);

  // Stop camera media tracks
  const stopCamera = useCallback(() => {
    if (animationFrameIdRef.current) {
      cancelAnimationFrame(animationFrameIdRef.current);
      animationFrameIdRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    setCameraActive(false);
    setTorchOn(false);
  }, []);

  // Start camera stream
  const startCamera = useCallback(async () => {
    stopCamera();

    const videoConstraints: MediaTrackConstraints = selectedDeviceId
      ? { deviceId: { exact: selectedDeviceId }, width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 60, min: 30 } }
      : { facingMode: cameraFacing, width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 60, min: 30 } };

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: videoConstraints,
        audio: false,
      });

      mediaStreamRef.current = stream;

      // Check for torch/flashlight capability
      const track = stream.getVideoTracks()[0];
      const capabilities = (track.getCapabilities && track.getCapabilities()) as any;
      setTorchSupported(!!(capabilities && capabilities.torch));

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.setAttribute('playsinline', 'true');
        await videoRef.current.play();
        setCameraActive(true);
        refreshDevices();
      }
    } catch (err: any) {
      console.warn('Failed to start camera with exact constraints, trying generic:', err);
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: cameraFacing },
          audio: false,
        });
        mediaStreamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.setAttribute('playsinline', 'true');
          await videoRef.current.play();
          setCameraActive(true);
        }
      } catch (fallbackErr: any) {
        console.error('Camera access denied or failed:', fallbackErr);
        setCameraActive(false);
      }
    }
  }, [cameraFacing, selectedDeviceId, stopCamera, refreshDevices]);

  // Toggle Torch / Flashlight
  const toggleTorch = async () => {
    if (!mediaStreamRef.current) return;
    const track = mediaStreamRef.current.getVideoTracks()[0];
    try {
      await (track.applyConstraints as any)({
        advanced: [{ torch: !torchOn }],
      });
      setTorchOn(!torchOn);
    } catch (err) {
      console.warn('Torch toggle failed:', err);
    }
  };

  // Flip Camera between environment & user
  const toggleCameraFacing = () => {
    setCameraFacing((prev) => (prev === 'environment' ? 'user' : 'environment'));
    setSelectedDeviceId('');
  };

  // Process a scanned or typed token
  const handleTokenScanned = async (tokenString: string) => {
    let cleanToken = tokenString.trim();
    if (!cleanToken) return;

    // Clean URL prefixes if scanner returns full web address
    if (cleanToken.includes('/ticket/')) {
      cleanToken = cleanToken.split('/ticket/')[1].split('?')[0].split('#')[0];
    } else if (cleanToken.includes('/tickets/view/')) {
      cleanToken = cleanToken.split('/tickets/view/')[1].split('?')[0].split('#')[0];
    } else if (cleanToken.includes('/success/')) {
      cleanToken = cleanToken.split('/success/')[1].split('?')[0].split('#')[0];
    }

    // Debounce duplicate scans with synchronous lock and 3.5s cooldown
    const now = Date.now();
    if (isVerifyingRef.current) {
      return;
    }

    if (cleanToken === lastVerifiedTokenRef.current && now - lastVerifiedTimeRef.current < 3500) {
      return;
    }

    isVerifyingRef.current = true;
    lastVerifiedTokenRef.current = cleanToken;
    lastVerifiedTimeRef.current = now;

    playBeep();
    setVerifying(true);
    setScannedToken(cleanToken);
    setCheckinSuccessInfo(null);

    try {
      const res = await verifyQR(cleanToken);
      setScanResult(res);

      if (res.status === 'VALID') {
        success('Valid Pass Verified', `${res.customer_name} • Booking #${res.booking_id}`);
      } else if (res.status === 'USED') {
        warning('Already Admitted', 'This pass was already checked in earlier!');
      } else if (res.status === 'CANCELLED') {
        error('Cancelled', 'This ticket has been cancelled. Entry denied.');
      } else {
        error('Invalid Pass', res.message || 'No ticket found matching this code.');
      }
    } catch (err: any) {
      error('Verification Error', err.response?.data?.detail || 'Failed to verify pass with server.');
    } finally {
      setVerifying(false);
      setTimeout(() => {
        isVerifyingRef.current = false;
      }, 500);
    }
  };

  // Continuous Camera Frame Scanning Loop (jsQR + BarcodeDetector)
  useEffect(() => {
    if (!cameraActive) return;

    let isScanning = true;

    const scanFrame = async () => {
      if (!isScanning) return;

      const video = videoRef.current;
      const canvas = canvasRef.current;

      if (video && video.readyState === video.HAVE_ENOUGH_DATA && canvas) {
        const width = video.videoWidth;
        const height = video.videoHeight;

        if (width > 0 && height > 0) {
          canvas.width = width;
          canvas.height = height;
          const ctx = canvas.getContext('2d', { willReadFrequently: true });

          if (ctx) {
            ctx.drawImage(video, 0, 0, width, height);

            let detectedText: string | null = null;

            // 1. Try Native Fast BarcodeDetector (GPU accelerated on Chrome / Android)
            if (barcodeDetectorRef.current) {
              try {
                const barcodes = await barcodeDetectorRef.current.detect(canvas);
                if (barcodes && barcodes.length > 0 && barcodes[0].rawValue) {
                  detectedText = barcodes[0].rawValue;
                }
              } catch {
                // Fallback to jsQR
              }
            }

            // 2. High-accuracy jsQR scanner (handles dark mode, reflections, invert)
            if (!detectedText) {
              try {
                const imageData = ctx.getImageData(0, 0, width, height);
                const code = jsQR(imageData.data, imageData.width, imageData.height, {
                  inversionAttempts: 'attemptBoth',
                });
                if (code && code.data) {
                  detectedText = code.data;
                }
              } catch {
                // ignore frame error
              }
            }

            if (detectedText) {
              handleTokenScanned(detectedText);
            }
          }
        }
      }

      if (isScanning) {
        animationFrameIdRef.current = requestAnimationFrame(scanFrame);
      }
    };

    animationFrameIdRef.current = requestAnimationFrame(scanFrame);

    return () => {
      isScanning = false;
      if (animationFrameIdRef.current) {
        cancelAnimationFrame(animationFrameIdRef.current);
      }
    };
  }, [cameraActive]);

  // Start camera on mount & change
  useEffect(() => {
    startCamera();
    return () => {
      stopCamera();
    };
  }, [cameraFacing, selectedDeviceId]);

  // Handle Manual Form Submit
  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualInput.trim()) return;
    setScannedToken('');
    handleTokenScanned(manualInput.trim());
  };

  // Image Upload Scanner (Screenshot / Photo)
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setVerifying(true);
      const img = new Image();
      const objectUrl = URL.createObjectURL(file);

      img.onload = async () => {
        URL.revokeObjectURL(objectUrl);
        const canvas = document.createElement('canvas');
        canvas.width = img.naturalWidth || img.width;
        canvas.height = img.naturalHeight || img.height;
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        if (!ctx) {
          setVerifying(false);
          return;
        }

        ctx.drawImage(img, 0, 0);

        let detectedText: string | null = null;

        // Try BarcodeDetector
        if (barcodeDetectorRef.current) {
          try {
            const barcodes = await barcodeDetectorRef.current.detect(canvas);
            if (barcodes && barcodes.length > 0 && barcodes[0].rawValue) {
              detectedText = barcodes[0].rawValue;
            }
          } catch {
            // fallback
          }
        }

        // Try jsQR with inversion
        if (!detectedText) {
          const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
          const code = jsQR(imageData.data, imageData.width, imageData.height, {
            inversionAttempts: 'attemptBoth',
          });
          if (code && code.data) {
            detectedText = code.data;
          }
        }

        if (detectedText) {
          handleTokenScanned(detectedText);
        } else {
          error('QR Not Detected', 'Could not detect a clear QR code in this photo. Please ensure it is well lit, or enter the Ticket ID manually.');
          setVerifying(false);
        }
      };

      img.onerror = () => {
        error('File Error', 'Failed to read image file.');
        setVerifying(false);
      };

      img.src = objectUrl;
    } catch {
      error('Scan Failed', 'Unable to process image file.');
      setVerifying(false);
    } finally {
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  // Execute Check-in Confirmation
  const executeCheckIn = async () => {
    const tokenToSubmit = scanResult?.qr_token_raw || scannedToken || manualInput.trim();
    if (!tokenToSubmit) return;

    setCheckingIn(true);

    try {
      const res = await checkInQR(tokenToSubmit, 'Turnstile Scanner Pro');
      setCheckinSuccessInfo(res);
      setScanResult((prev) => (prev ? { ...prev, status: 'USED', checkin_status: true } : null));

      // Append to session log
      setSessionHistory((prev) => [
        {
          ticketId: res.ticket_id || scanResult?.ticket_id || 'N/A',
          customerName: res.customer_name || scanResult?.customer_name || 'Attendee',
          result: 'Admitted',
          time: new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        },
        ...prev,
      ]);

      success('Checked In!', `${res.customer_name || scanResult?.customer_name} admitted successfully.`);
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Check-in failed.';
      error('Check-in Rejected', msg);
    } finally {
      setCheckingIn(false);
    }
  };

  const resetScan = () => {
    setScanResult(null);
    setScannedToken('');
    setCheckinSuccessInfo(null);
    setManualInput('');
    isVerifyingRef.current = false;
    lastVerifiedTokenRef.current = '';
    lastVerifiedTimeRef.current = 0;
  };

  return (
    <div className="max-w-xl mx-auto space-y-6">
      {/* Top Banner */}
      <div className="text-center">
        <div className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-amber-400 px-3.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 mb-2">
          <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
          NAVRANG 2026 Turnstile Scanner Pro
        </div>
        <h2 className="text-2xl sm:text-3xl font-black text-white font-['Outfit']">
          QR Entry Verification
        </h2>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Scan attendee's phone screen, paper pass, upload screenshot, or enter Ticket ID manually.
        </p>
      </div>

      {/* Camera Viewfinder Box */}
      <div className="relative rounded-3xl overflow-hidden glass-panel border border-white/10 shadow-2xl p-4">
        {/* Controls bar */}
        <div className="flex items-center justify-between mb-3 px-1">
          <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
            <Camera className="w-4 h-4 text-amber-400" />
            <span>High-Speed Optical Scanner</span>
          </span>

          <div className="flex items-center gap-2">
            {/* Multi-camera selector if available */}
            {availableDevices.length > 1 && (
              <select
                value={selectedDeviceId}
                onChange={(e) => setSelectedDeviceId(e.target.value)}
                className="bg-black/60 border border-white/10 text-slate-300 text-[11px] rounded-lg px-2 py-1 focus:outline-none focus:border-amber-400 max-w-[140px] truncate"
              >
                {availableDevices.map((cam, idx) => (
                  <option key={cam.deviceId || idx} value={cam.deviceId}>
                    {cam.label || `Camera ${idx + 1}`}
                  </option>
                ))}
              </select>
            )}

            {/* Torch toggle */}
            {torchSupported && (
              <button
                onClick={toggleTorch}
                className={`p-1.5 rounded-lg border transition-colors ${
                  torchOn
                    ? 'bg-amber-400 text-black border-amber-400 shadow-md shadow-amber-400/30'
                    : 'bg-white/5 hover:bg-white/10 text-slate-300 border-white/10'
                }`}
                title="Toggle Flashlight / Torch"
              >
                <Flashlight className="w-4 h-4" />
              </button>
            )}

            <button
              onClick={toggleCameraFacing}
              className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white transition-colors border border-white/10"
              title="Flip Camera (Front/Back)"
            >
              <SwitchCamera className="w-4 h-4" />
            </button>
            <button
              onClick={startCamera}
              className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white transition-colors border border-white/10"
              title="Restart Video Stream"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Video feed container with natural aspect ratio */}
        <div className="relative bg-black rounded-2xl overflow-hidden min-h-[300px] flex items-center justify-center border border-white/10">
          <video
            ref={videoRef}
            playsInline
            muted
            autoPlay
            className="w-full h-auto max-h-[420px] object-contain block mx-auto rounded-xl"
          />

          {/* Hidden Canvas for Frame Processing */}
          <canvas ref={canvasRef} className="hidden" />

          {/* Viewfinder animated frame */}
          <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
            <div className="w-64 h-64 border-2 border-amber-400/80 rounded-2xl relative shadow-[0_0_25px_rgba(212,175,55,0.3)]">
              {/* Corner accents */}
              <div className="absolute top-0 left-0 w-6 h-6 border-t-4 border-l-4 border-amber-400 rounded-tl-lg" />
              <div className="absolute top-0 right-0 w-6 h-6 border-t-4 border-r-4 border-amber-400 rounded-tr-lg" />
              <div className="absolute bottom-0 left-0 w-6 h-6 border-b-4 border-l-4 border-amber-400 rounded-bl-lg" />
              <div className="absolute bottom-0 right-0 w-6 h-6 border-b-4 border-r-4 border-amber-400 rounded-br-lg" />

              {/* Laser animation beam */}
              <div className="absolute inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-amber-300 to-transparent shadow-[0_0_12px_#d4af37] animate-bounce" />
            </div>
          </div>
        </div>

        {/* Action toolbar below camera */}
        <div className="flex items-center justify-between mt-3 text-xs text-slate-400 px-1">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Dual-engine scanner (60 FPS) active</span>
          </span>

          {/* Upload file button for photos / screenshots */}
          <div>
            <input
              type="file"
              ref={fileInputRef}
              accept="image/*"
              className="hidden"
              onChange={handleFileUpload}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-amber-300 hover:text-amber-200 transition-colors border border-amber-400/20 font-semibold text-xs"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Scan from Photo / Screenshot</span>
            </button>
          </div>
        </div>
      </div>

      {/* Manual Token / Ticket ID / Booking ID Entry Fallback */}
      <div className="p-4 rounded-2xl glass-panel border border-white/10">
        <form onSubmit={handleManualSubmit} className="space-y-2">
          <div className="text-[11px] text-slate-300 font-semibold flex items-center justify-between">
            <span>Manual Pass Search & Entry</span>
            <span className="text-slate-500 font-normal">Ticket ID • Booking ID • Phone • Email</span>
          </div>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={manualInput}
                onChange={(e) => setManualInput(e.target.value)}
                placeholder="e.g. GN26-TKT-070591-01, GN-2026-70591, or 9876543210..."
                className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-black/50 border border-white/10 text-white placeholder-slate-500 text-xs focus:outline-none focus:border-amber-400"
              />
            </div>
            <button
              type="submit"
              disabled={verifying}
              className="festive-button px-5 py-2.5 rounded-xl text-xs font-bold shrink-0 disabled:opacity-50"
            >
              {verifying ? 'Checking...' : 'Check Ticket'}
            </button>
          </div>
        </form>
      </div>

      {/* Validation Loading Display */}
      {verifying && (
        <div className="p-6 rounded-2xl glass-panel border border-amber-500/30 text-center space-y-2">
          <div className="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <div className="text-sm font-bold text-white">Validating Attendee Pass...</div>
          <div className="text-xs text-slate-400">Resolving cryptographic signature against NAVRANG 2026 database</div>
        </div>
      )}

      {/* Validation Result Display */}
      {scanResult && !verifying && (
        <div
          className={`p-6 rounded-3xl border shadow-2xl space-y-4 ${
            scanResult.status === 'VALID'
              ? 'bg-[#0f1f17] border-emerald-500/40 text-emerald-100'
              : scanResult.status === 'USED'
              ? 'bg-[#261c0d] border-amber-500/40 text-amber-100'
              : 'bg-[#291016] border-rose-500/40 text-rose-100'
          }`}
        >
          {/* Header Badge */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 font-black text-base uppercase tracking-wider">
              {scanResult.status === 'VALID' && (
                <>
                  <CheckCircle2 className="w-6 h-6 text-emerald-400" />
                  <span className="text-emerald-400">VALID ADMISSION PASS</span>
                </>
              )}
              {scanResult.status === 'USED' && (
                <>
                  <AlertTriangle className="w-6 h-6 text-amber-400" />
                  <span className="text-amber-400">⚠️ PASS ALREADY ADMITTED</span>
                </>
              )}
              {scanResult.status === 'CANCELLED' && (
                <>
                  <XCircle className="w-6 h-6 text-rose-400" />
                  <span className="text-rose-400">❌ TICKET CANCELLED</span>
                </>
              )}
              {scanResult.status === 'INVALID' && (
                <>
                  <XCircle className="w-6 h-6 text-rose-400" />
                  <span className="text-rose-400">❌ UNRECOGNIZED PASS</span>
                </>
              )}
            </div>

            <button
              onClick={resetScan}
              className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 transition-colors text-white"
            >
              Scan Next Attendee
            </button>
          </div>

          <p className="text-xs opacity-90">{scanResult.message}</p>

          {/* Ticket Information */}
          {scanResult.ticket_id && (
            <div className="grid grid-cols-2 gap-3 text-xs pt-3 border-t border-white/10">
              <div>
                <div className="text-[10px] opacity-75 uppercase">Attendee Name</div>
                <div className="font-bold text-white text-sm mt-0.5">{scanResult.customer_name}</div>
              </div>
              <div>
                <div className="text-[10px] opacity-75 uppercase">Booking ID</div>
                <div className="font-mono font-bold text-amber-400 mt-0.5">#{scanResult.booking_id}</div>
              </div>
              <div>
                <div className="text-[10px] opacity-75 uppercase">Ticket Number</div>
                <div className="font-mono font-semibold text-white mt-0.5">{scanResult.ticket_id}</div>
              </div>
              <div>
                <div className="text-[10px] opacity-75 uppercase">Status & Event</div>
                <div className="font-bold text-emerald-400 mt-0.5">PAID ✓ • NAVRANG 2026</div>
              </div>
            </div>
          )}

          {/* Previous checkin notice */}
          {scanResult.status === 'USED' && scanResult.checked_in_at && (
            <div className="p-3 rounded-xl bg-black/40 border border-white/10 text-xs text-amber-300">
              Original Admission Timestamp:{' '}
              <strong>
                {new Date(scanResult.checked_in_at).toLocaleTimeString('en-IN', {
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                })}
              </strong>
              . Duplicate entry denied.
            </div>
          )}

          {/* Check-in Action Button (For VALID passes) */}
          {scanResult.status === 'VALID' && !checkinSuccessInfo && (
            <button
              onClick={executeCheckIn}
              disabled={checkingIn}
              className="w-full py-4 rounded-2xl bg-emerald-600 hover:bg-emerald-500 font-extrabold text-white text-sm shadow-xl shadow-emerald-600/30 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
            >
              {checkingIn ? (
                <>
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Recording Admission...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-5 h-5" />
                  <span>CONFIRM GATE ADMISSION ✓</span>
                </>
              )}
            </button>
          )}

          {/* Successful Check-in confirmation */}
          {checkinSuccessInfo && (
            <div className="p-4 rounded-xl bg-emerald-900/60 border border-emerald-500/50 text-emerald-100 text-xs space-y-1">
              <div className="font-bold text-white text-sm flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Admission Granted Successfully!
              </div>
              <div>
                Admitted at:{' '}
                {new Date(checkinSuccessInfo.checked_in_at || Date.now()).toLocaleTimeString('en-IN', {
                  hour: '2-digit',
                  minute: '2-digit',
                })}{' '}
                by {checkinSuccessInfo.staff_name || 'Turnstile Staff'}.
              </div>
            </div>
          )}
        </div>
      )}

      {/* Session History Log */}
      {sessionHistory.length > 0 && (
        <div className="p-5 rounded-2xl glass-panel border border-white/10 space-y-3">
          <div className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-amber-400" />
            <span>This Session's Admitted Guests ({sessionHistory.length})</span>
          </div>

          <div className="divide-y divide-white/5 max-h-48 overflow-y-auto">
            {sessionHistory.map((item, idx) => (
              <div key={idx} className="py-2 flex items-center justify-between text-xs">
                <div>
                  <div className="font-semibold text-white">{item.customerName}</div>
                  <div className="text-[10px] font-mono text-slate-400">{item.ticketId}</div>
                </div>
                <div className="text-right">
                  <span className="text-[10px] font-bold text-emerald-400">Admitted</span>
                  <div className="text-[10px] text-slate-500">{item.time}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
