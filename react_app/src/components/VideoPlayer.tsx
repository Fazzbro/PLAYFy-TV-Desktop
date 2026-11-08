'use client';
import React, { useEffect, useRef, useState, useCallback } from 'react';
import Hls from 'hls.js';
import { 
  Play, Pause, Volume2, Volume1, VolumeX, Maximize2, Minimize2, 
  Copy, ExternalLink, ShieldCheck, Server, Check, AlertCircle, 
  RefreshCw, Sliders, X, Tv, Scaling, Pipette, Zap
} from 'lucide-react';
import { cn } from '../lib/utils';

// Dynamically import shaka-player to handle client-side rendering
// @ts-ignore
import shaka from 'shaka-player/dist/shaka-player.ui.js';

export interface StreamServer {
  id: number | string;
  server_index?: number;
  title: string;
  link: string;
  proxy_link?: string;
  quality?: string;
  is_hls?: boolean;
  is_dash?: boolean;
  has_drm?: boolean;
  clearkey?: Record<string, string>;
  headers?: Record<string, string>;
  direct_playable?: boolean;
}

export interface QualityTrack {
  id: string;
  label: string;
  height?: number;
  bitrate?: number;
  isAuto?: boolean;
}

type AspectMode = 'contain' | 'cover' | 'fill';

interface VideoPlayerProps {
  title: string;
  subtitle?: string;
  servers: StreamServer[];
  onClose: () => void;
}

export function VideoPlayer({ title, subtitle, servers, onClose }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const videoWrapperRef = useRef<HTMLDivElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const [activeServerIdx, setActiveServerIdx] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [volume, setVolume] = useState<number>(1.0);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Auto-hide controls in cinema/fullscreen mode
  const [controlsVisible, setControlsVisible] = useState<boolean>(true);
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Aspect ratio scaling mode
  const [aspectRatio, setAspectRatio] = useState<AspectMode>('contain');
  const [isAspectMenuOpen, setIsAspectMenuOpen] = useState<boolean>(false);

  // Side quick-switcher drawer for broadcast servers
  const [isServerDrawerOpen, setIsServerDrawerOpen] = useState<boolean>(false);

  // HUD notification badge (Volume, Aspect Ratio, Stream Switch)
  const [hudMessage, setHudMessage] = useState<string | null>(null);
  const hudTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Animated center play/pause ripple
  const [centerIconState, setCenterIconState] = useState<'play' | 'pause' | null>(null);
  const centerIconTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const clickDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Dynamic Quality Selection (Recovered from REA: DefaultTrackSelector / TrackSelectionView)
  const [qualityTracks, setQualityTracks] = useState<QualityTrack[]>([
    { id: 'auto', label: 'Auto (ABR)', isAuto: true }
  ]);
  const [selectedQuality, setSelectedQuality] = useState<string>('auto');
  const [isQualityMenuOpen, setIsQualityMenuOpen] = useState<boolean>(false);

  const activeServer = servers[activeServerIdx] || servers[0];
  const hlsInstanceRef = useRef<Hls | null>(null);
  const shakaPlayerRef = useRef<any>(null);

  // HUD notifier
  const showHud = useCallback((msg: string) => {
    setHudMessage(msg);
    if (hudTimeoutRef.current) clearTimeout(hudTimeoutRef.current);
    hudTimeoutRef.current = setTimeout(() => setHudMessage(null), 1600);
  }, []);

  // Controls auto-hide timer
  const onUserActivity = useCallback(() => {
    setControlsVisible(true);
    if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
    if (isPlaying && !isQualityMenuOpen && !isServerDrawerOpen && !isAspectMenuOpen) {
      hideTimerRef.current = setTimeout(() => {
        setControlsVisible(false);
      }, 2800);
    }
  }, [isPlaying, isQualityMenuOpen, isServerDrawerOpen, isAspectMenuOpen]);

  // Volume handler
  const handleVolumeChange = (newVol: number) => {
    const clamped = Math.max(0, Math.min(1, newVol));
    setVolume(clamped);
    if (videoRef.current) {
      videoRef.current.volume = clamped;
      if (clamped > 0 && videoRef.current.muted) {
        videoRef.current.muted = false;
        setIsMuted(false);
      } else if (clamped === 0) {
        videoRef.current.muted = true;
        setIsMuted(true);
      }
    }
    showHud(`Volume: ${Math.round(clamped * 100)}%`);
  };

  const toggleMute = () => {
    if (!videoRef.current) return;
    const nextMuted = !videoRef.current.muted;
    videoRef.current.muted = nextMuted;
    setIsMuted(nextMuted);
    showHud(nextMuted ? 'Muted' : `Volume: ${Math.round(volume * 100)}%`);
  };

  // Aspect ratio cycling
  const cycleAspectRatio = (mode?: AspectMode) => {
    const modes: AspectMode[] = ['contain', 'cover', 'fill'];
    const nextMode = mode || modes[(modes.indexOf(aspectRatio) + 1) % modes.length];
    setAspectRatio(nextMode);
    setIsAspectMenuOpen(false);
    const label = nextMode === 'contain' ? 'Fit (16:9 Standard)' : nextMode === 'cover' ? 'Zoom (Fill Screen)' : 'Stretch';
    showHud(`Aspect: ${label}`);
  };

  // Synchronize fullscreen state with native desktop host window & hide Windows Taskbar
  const syncDesktopFullscreen = async (targetFs: boolean) => {
    try {
      if ((window as any).pywebview?.api?.set_fullscreen) {
        await (window as any).pywebview.api.set_fullscreen(targetFs);
      }
    } catch (e) {
      // Ignore
    }
    try {
      await fetch('/api/window/fullscreen', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state: targetFs })
      });
    } catch (e) {
      // Ignore
    }
  };

  // Fullscreen toggle with dual-layer DOM & Native WinForms Taskbar concealment
  const toggleFullscreen = async () => {
    const el = videoWrapperRef.current;

    if (!isFullscreen) {
      setIsFullscreen(true);
      await syncDesktopFullscreen(true);
      if (el) {
        try {
          if (el.requestFullscreen) {
            await el.requestFullscreen();
          } else if ((el as any).webkitRequestFullscreen) {
            await (el as any).webkitRequestFullscreen();
          } else if ((el as any).msRequestFullscreen) {
            await (el as any).msRequestFullscreen();
          }
        } catch (err) {
          // Native fullscreen fallback
        }
      }
    } else {
      setIsFullscreen(false);
      await syncDesktopFullscreen(false);
      try {
        if (document.fullscreenElement || (document as any).webkitFullscreenElement) {
          if (document.exitFullscreen) {
            await document.exitFullscreen();
          } else if ((document as any).webkitExitFullscreen) {
            await (document as any).webkitExitFullscreen();
          } else if ((document as any).msExitFullscreen) {
            await (document as any).msExitFullscreen();
          }
        }
      } catch (err) {
        // Ignore
      }
    }
  };

  // Picture in Picture
  const togglePiP = async () => {
    if (!videoRef.current) return;
    try {
      if (document.pictureInPictureElement) {
        await document.exitPictureInPicture();
      } else if (document.pictureInPictureEnabled) {
        await videoRef.current.requestPictureInPicture();
      }
    } catch (err) {
      console.warn('PiP not supported or denied', err);
    }
  };

  // Play/Pause with visual feedback
  const animateCenterIcon = (type: 'play' | 'pause') => {
    setCenterIconState(type);
    if (centerIconTimeoutRef.current) clearTimeout(centerIconTimeoutRef.current);
    centerIconTimeoutRef.current = setTimeout(() => setCenterIconState(null), 450);
  };

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current.play().then(() => {
        setIsPlaying(true);
        animateCenterIcon('play');
      }).catch(() => {});
    } else {
      videoRef.current.pause();
      setIsPlaying(false);
      animateCenterIcon('pause');
    }
    onUserActivity();
  };

  // Distinguish single click (play/pause) from double click (fullscreen)
  const handleVideoCanvasClick = () => {
    if (clickDebounceRef.current) {
      clearTimeout(clickDebounceRef.current);
      clickDebounceRef.current = null;
      toggleFullscreen();
    } else {
      clickDebounceRef.current = setTimeout(() => {
        clickDebounceRef.current = null;
        togglePlay();
      }, 240);
    }
  };

  // Mouse wheel volume scrolling
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    onUserActivity();
    const delta = e.deltaY < 0 ? 0.05 : -0.05;
    handleVolumeChange(volume + delta);
  };

  // Quality switch handler (ABR vs Fixed Resolution)
  const handleSelectQuality = (trackId: string) => {
    setSelectedQuality(trackId);
    setIsQualityMenuOpen(false);

    // 1. HLS Quality Selection
    if (hlsInstanceRef.current) {
      if (trackId === 'auto') {
        hlsInstanceRef.current.currentLevel = -1; // Auto ABR
      } else {
        const lvlIdx = parseInt(trackId, 10);
        if (!isNaN(lvlIdx)) {
          hlsInstanceRef.current.currentLevel = lvlIdx;
        }
      }
      return;
    }

    // 2. Shaka Player Quality Selection (DASH / ClearKey)
    if (shakaPlayerRef.current) {
      const player = shakaPlayerRef.current;
      if (trackId === 'auto') {
        player.configure({ abr: { enabled: true } });
      } else {
        player.configure({ abr: { enabled: false } });
        const tracks = player.getVariantTracks();
        const target = tracks.find((t: any) => String(t.id) === trackId);
        if (target) {
          player.selectVariantTrack(target, /* clearBuffer= */ true);
        }
      }
    }
  };

  // Sync keyboard shortcuts and OS fullscreen change
  useEffect(() => {
    const handleFsChange = () => {
      const fs = Boolean(
        document.fullscreenElement || 
        (document as any).webkitFullscreenElement || 
        (document as any).mozFullScreenElement || 
        (document as any).msFullscreenElement
      );
      setIsFullscreen(fs);
      if (!fs) {
        syncDesktopFullscreen(false);
      }
    };

    document.addEventListener('fullscreenchange', handleFsChange);
    document.addEventListener('webkitfullscreenchange', handleFsChange);

    const handleKeyDown = (e: KeyboardEvent) => {
      onUserActivity();
      if (e.key === 'Escape') {
        if (isServerDrawerOpen) {
          setIsServerDrawerOpen(false);
        } else if (isQualityMenuOpen) {
          setIsQualityMenuOpen(false);
        } else if (isAspectMenuOpen) {
          setIsAspectMenuOpen(false);
        } else if (isFullscreen) {
          toggleFullscreen();
        } else {
          onClose();
        }
      } else if (e.key === 'f' || e.key === 'F') {
        toggleFullscreen();
      } else if (e.key === ' ') {
        e.preventDefault();
        togglePlay();
      } else if (e.key === 'm' || e.key === 'M') {
        toggleMute();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        handleVolumeChange(volume + 0.05);
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        handleVolumeChange(volume - 0.05);
      } else if (e.key === 's' || e.key === 'S') {
        setIsServerDrawerOpen(prev => !prev);
      } else if (e.key === 'a' || e.key === 'A') {
        cycleAspectRatio();
      } else if (e.key === 'q' || e.key === 'Q') {
        setIsQualityMenuOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('fullscreenchange', handleFsChange);
      document.removeEventListener('webkitfullscreenchange', handleFsChange);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isFullscreen, isServerDrawerOpen, isQualityMenuOpen, isAspectMenuOpen, volume, onClose, onUserActivity]);

  // Clean-up on unmount: ensure native window exits fullscreen
  useEffect(() => {
    return () => {
      syncDesktopFullscreen(false);
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
      if (hudTimeoutRef.current) clearTimeout(hudTimeoutRef.current);
    };
  }, []);

  // Initialize or switch stream playback
  useEffect(() => {
    if (!videoRef.current || !activeServer) return;

    setIsLoading(true);
    setErrorMsg(null);
    setSelectedQuality('auto');
    setIsQualityMenuOpen(false);

    const video = videoRef.current;
    const currentUrl: string = activeServer.link || activeServer.proxy_link || '';
    if (!currentUrl) {
      setErrorMsg('No valid stream address found for this server. Please select another server.');
      setIsLoading(false);
      return;
    }
    const backupUrl: string | null = activeServer.proxy_link && activeServer.proxy_link !== currentUrl ? activeServer.proxy_link : null;

    // Cleanup previous player instances
    if (hlsInstanceRef.current) {
      hlsInstanceRef.current.destroy();
      hlsInstanceRef.current = null;
    }
    if (shakaPlayerRef.current) {
      shakaPlayerRef.current.destroy();
      shakaPlayerRef.current = null;
    }

    const isDash = activeServer.is_dash || currentUrl.includes('.mpd');
    const isHls = activeServer.is_hls || currentUrl.includes('.m3u8');

    // Scenario A: MPEG-DASH with ClearKey DRM
    if (isDash || activeServer.has_drm) {
      try {
        shaka.polyfill.installAll();
        if (shaka.Player.isBrowserSupported()) {
          const player = new shaka.Player(video);
          shakaPlayerRef.current = player;

          // Configure ClearKey DRM credentials
          if (activeServer.clearkey && Object.keys(activeServer.clearkey).length > 0) {
            player.configure({
              drm: {
                clearKeys: activeServer.clearkey
              }
            });
          }

          let hasAttemptedFallback = false;

          const handleShakaError = (code?: number, msg?: string) => {
            if (backupUrl && !hasAttemptedFallback) {
              hasAttemptedFallback = true;
              console.log('Direct DASH playback failed, attempting proxy fallback:', backupUrl);
              player.load(backupUrl).then(() => {
                setIsLoading(false);
                video.play().catch(() => setIsPlaying(false));
              }).catch((e: any) => {
                console.error('Proxy fallback failed:', e);
                setErrorMsg(`Playback error: Shaka Error ${e.code || code || '1001'}. Try another server.`);
                setIsLoading(false);
              });
              return;
            }
            setErrorMsg(`Playback error: Shaka Error ${code || '1001'}. Try another server.`);
            setIsLoading(false);
          };

          player.addEventListener('error', (event: any) => {
            console.warn('Shaka Player Error:', event.detail);
            handleShakaError(event.detail?.code, event.detail?.message);
          });

          player.load(currentUrl).then(() => {
            setIsLoading(false);
            video.play().catch(() => setIsPlaying(false));

            // Populate Shaka variant tracks
            try {
              const tracks = player.getVariantTracks();
              const uniqueHeights = new Map<number, any>();
              tracks.forEach((t: any) => {
                if (t.height && !uniqueHeights.has(t.height)) {
                  uniqueHeights.set(t.height, t);
                }
              });

              const parsedTracks: QualityTrack[] = [
                { id: 'auto', label: 'Auto (ABR)', isAuto: true }
              ];
              Array.from(uniqueHeights.values())
                .sort((a, b) => b.height - a.height)
                .forEach((t) => {
                  parsedTracks.push({
                    id: String(t.id),
                    label: `${t.height}p`,
                    height: t.height,
                    bitrate: t.bandwidth
                  });
                });

              if (parsedTracks.length > 1) {
                setQualityTracks(parsedTracks);
              }
            } catch (e) {
              // Ignore track parse errors
            }
          }).catch((err: any) => {
            console.error('Shaka Load Error:', err);
            handleShakaError(err.code, err.message);
          });
          return;
        }
      } catch (err) {
        console.warn('Shaka initialization failed:', err);
      }
    }

    // Scenario B: HLS.js streaming
    if (Hls.isSupported() && (isHls || !isDash)) {
      const hls = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
        backBufferLength: 60
      });
      hlsInstanceRef.current = hls;

      let hasAttemptedHlsFallback = false;

      hls.loadSource(currentUrl);
      hls.attachMedia(video);

      hls.on(Hls.Events.MANIFEST_PARSED, (_event, data) => {
        setIsLoading(false);
        video.play().catch(() => setIsPlaying(false));

        if (data.levels && data.levels.length > 1) {
          const parsedTracks: QualityTrack[] = [
            { id: 'auto', label: 'Auto (ABR)', isAuto: true }
          ];
          data.levels.forEach((lvl, idx) => {
            const h = lvl.height || Math.round((lvl.bitrate || 0) / 3000);
            parsedTracks.push({
              id: String(idx),
              label: h ? `${h}p` : `Track ${idx + 1}`,
              height: lvl.height,
              bitrate: lvl.bitrate
            });
          });
          setQualityTracks(parsedTracks);
        }
      });

      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal) {
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              if (backupUrl && !hasAttemptedHlsFallback) {
                hasAttemptedHlsFallback = true;
                console.log('HLS direct network error, falling back to proxy:', backupUrl);
                hls.loadSource(backupUrl);
                hls.startLoad();
                return;
              }
              hls.startLoad();
              break;
            case Hls.ErrorTypes.MEDIA_ERROR:
              hls.recoverMediaError();
              break;
            default:
              hls.destroy();
              setErrorMsg('Stream connection interrupted. Please select an alternate broadcast server.');
              setIsLoading(false);
              break;
          }
        }
      });
      return;
    }

    // Scenario C: Native browser HLS
    if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = currentUrl;
      video.addEventListener('loadedmetadata', () => {
        setIsLoading(false);
        video.play().catch(() => setIsPlaying(false));
      });
      video.addEventListener('error', () => {
        if (backupUrl) {
          video.src = backupUrl;
          return;
        }
        setErrorMsg('Native player encountered a playback fault. Click an alternate server.');
        setIsLoading(false);
      });
      return;
    }

    // Fallback: direct src
    video.src = currentUrl;
    setIsLoading(false);
  }, [activeServerIdx, activeServer]);

  const copyStreamUrl = () => {
    if (!activeServer?.link) return;
    navigator.clipboard.writeText(activeServer.link);
    setCopied(true);
    showHud('Stream URL Copied');
    setTimeout(() => setCopied(false), 2000);
  };

  const openExternal = () => {
    if (!activeServer?.link) return;
    window.open(activeServer.link, '_blank');
  };

  const videoObjectFitClass = 
    aspectRatio === 'cover' ? 'object-cover' :
    aspectRatio === 'fill' ? 'object-fill' : 'object-contain';

  return (
    <div 
      className={cn(
        "fixed inset-0 z-50 flex flex-col items-center justify-center transition-colors duration-300 selection:bg-white selection:text-black",
        isFullscreen ? "bg-black p-0 m-0 w-screen h-screen overflow-hidden" : "bg-black/95 backdrop-blur-2xl p-2 sm:p-6 overflow-y-auto"
      )}
      onMouseMove={onUserActivity}
    >
      <div 
        ref={containerRef}
        className={cn(
          "relative bg-[#080808] border border-[#222222] shadow-2xl flex flex-col transition-all duration-300",
          isFullscreen 
            ? "fixed inset-0 z-[100] w-screen h-screen max-w-none rounded-none border-none p-0 m-0 overflow-hidden bg-black" 
            : "w-full max-w-5xl rounded-2xl overflow-hidden my-auto"
        )}
      >
        {/* Top Header Bar (Shown in normal mode, or smoothly in fullscreen on hover/movement) */}
        <div className={cn(
          "flex items-center justify-between px-6 py-3.5 border-b border-[#1c1c1c] bg-[#0c0c0c]/90 backdrop-blur-md shrink-0 z-30 transition-all duration-300",
          isFullscreen 
            ? (controlsVisible ? "absolute top-0 inset-x-0 opacity-100 translate-y-0" : "absolute top-0 inset-x-0 opacity-0 -translate-y-4 pointer-events-none") 
            : "relative"
        )}>
          <div className="flex items-center gap-3">
            <span className="flex h-3 w-3 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-white"></span>
            </span>
            <div>
              <h2 className="text-white font-bold text-base sm:text-lg tracking-tight leading-none font-display truncate max-w-[280px] sm:max-w-md md:max-w-xl">
                {title}
              </h2>
              {subtitle && (
                <p className="text-xs text-zinc-400 font-mono mt-1">
                  {subtitle}
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Server Drawer Toggle Button */}
            <button
              onClick={() => setIsServerDrawerOpen(prev => !prev)}
              className={cn(
                "px-3 py-1.5 text-xs font-mono rounded-lg border transition flex items-center gap-1.5 cursor-pointer shadow-sm",
                isServerDrawerOpen 
                  ? "bg-white text-black border-white font-bold" 
                  : "bg-[#141414] hover:bg-[#1f1f1f] text-zinc-300 hover:text-white border-[#262626]"
              )}
              title="Toggle Server Switcher Drawer (Hotkey: S)"
            >
              <Server size={14} />
              <span>Servers ({servers.length})</span>
            </button>

            <button
              onClick={copyStreamUrl}
              className="px-3 py-1.5 text-xs font-mono rounded-lg border border-[#262626] bg-[#141414] hover:bg-[#1f1f1f] text-zinc-300 hover:text-white transition flex items-center gap-1.5 cursor-pointer"
              title="Copy Direct Stream URL"
            >
              {copied ? <Check size={14} className="text-white" /> : <Copy size={14} />}
              <span className="hidden sm:inline">{copied ? 'Copied' : 'Copy URL'}</span>
            </button>

            <button
              onClick={openExternal}
              className="px-3 py-1.5 text-xs font-mono rounded-lg border border-[#262626] bg-[#141414] hover:bg-[#1f1f1f] text-zinc-300 hover:text-white transition flex items-center gap-1.5 cursor-pointer"
              title="Open in External VLC / Player"
            >
              <ExternalLink size={14} />
              <span className="hidden sm:inline">External</span>
            </button>

            <button
              onClick={isFullscreen ? toggleFullscreen : onClose}
              className="px-3 py-1.5 text-xs font-bold rounded-lg bg-white text-black hover:bg-zinc-200 transition ml-2 cursor-pointer shadow-md flex items-center gap-1.5"
              title={isFullscreen ? "Exit Fullscreen (Esc)" : "Close Player"}
            >
              {isFullscreen ? <Minimize2 size={14} /> : <X size={14} />}
              <span>{isFullscreen ? 'Exit Full' : 'Close'}</span>
            </button>
          </div>
        </div>

        {/* Video Canvas Container */}
        <div 
          ref={videoWrapperRef}
          className={cn(
            "relative bg-black flex items-center justify-center overflow-hidden select-none transition-all duration-300",
            isFullscreen 
              ? "w-screen h-screen flex-1" 
              : "w-full aspect-video max-h-[58vh]",
            isFullscreen && !controlsVisible && isPlaying ? "cursor-none" : "cursor-default"
          )}
          onClick={handleVideoCanvasClick}
          onWheel={handleWheel}
        >
          <video
            ref={videoRef}
            className={cn("w-full h-full transition-all duration-200", videoObjectFitClass)}
            playsInline
          />

          {/* Animated Center Ripple Indicator for Play / Pause */}
          {centerIconState && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-30">
              <div className="w-20 h-20 rounded-full bg-black/70 backdrop-blur-md border border-white/20 flex items-center justify-center text-white shadow-2xl animate-ping-once">
                {centerIconState === 'play' ? <Play size={36} className="ml-1" /> : <Pause size={36} />}
              </div>
            </div>
          )}

          {/* HUD Toast Overlay (e.g. Volume, Aspect Ratio, Stream Changed) */}
          {hudMessage && (
            <div className="absolute top-20 right-8 z-40 bg-black/85 backdrop-blur-md border border-white/20 text-white text-xs font-mono px-4 py-2 rounded-xl shadow-2xl pointer-events-none transition-all animate-fade-in flex items-center gap-2">
              <Zap size={14} className="text-zinc-400" />
              <span>{hudMessage}</span>
            </div>
          )}

          {/* Loading Indicator */}
          {isLoading && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/75 backdrop-blur-md z-20 pointer-events-none">
              <RefreshCw className="animate-spin text-white mb-3" size={38} />
              <p className="text-xs font-mono uppercase tracking-widest text-zinc-300">
                Connecting To Server {activeServerIdx + 1} ({activeServer.title})...
              </p>
            </div>
          )}

          {/* Error Banner with In-Video Server Recovery */}
          {errorMsg && (
            <div className="absolute inset-x-6 top-6 z-30 p-4 rounded-xl bg-red-950/85 border border-red-800 text-red-200 flex items-start gap-3 backdrop-blur-md shadow-2xl">
              <AlertCircle className="text-red-400 shrink-0 mt-0.5" size={18} />
              <div className="flex-1 text-sm">
                <p className="font-medium text-white">{errorMsg}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {servers.map((s, idx) => (
                    idx !== activeServerIdx && (
                      <button
                        key={`err-srv-${s.id}-${idx}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveServerIdx(idx);
                        }}
                        className="px-2.5 py-1 text-xs font-mono rounded bg-red-900/60 hover:bg-red-800 text-white border border-red-700 transition cursor-pointer"
                      >
                        Try Server {idx + 1} ({s.title})
                      </button>
                    )
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Slide-In Server Switcher Drawer (Available during Fullscreen & Normal Playback) */}
          {isServerDrawerOpen && (
            <div 
              className="absolute right-0 inset-y-0 w-80 bg-[#0a0a0a]/95 backdrop-blur-xl border-l border-[#222222] z-40 p-5 flex flex-col shadow-2xl animate-slide-left"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between pb-3 border-b border-[#1c1c1c] mb-4">
                <div className="flex items-center gap-2">
                  <Server size={16} className="text-white" />
                  <span className="text-sm font-bold text-white tracking-wide">Broadcast Feeds</span>
                </div>
                <button
                  onClick={() => setIsServerDrawerOpen(false)}
                  className="p-1 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10 transition cursor-pointer"
                >
                  <X size={16} />
                </button>
              </div>

              <p className="text-xs font-mono text-zinc-400 mb-3">
                Switch live server without exiting viewer:
              </p>

              <div className="flex-1 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
                {servers.map((srv, idx) => {
                  const isActive = idx === activeServerIdx;
                  return (
                    <button
                      key={`drawer-srv-${srv.id}-${idx}`}
                      onClick={() => {
                        setActiveServerIdx(idx);
                        setIsServerDrawerOpen(false);
                        showHud(`Switched to Server ${idx + 1}: ${srv.title}`);
                      }}
                      className={cn(
                        "w-full p-3 rounded-xl border text-left transition flex items-center justify-between cursor-pointer group",
                        isActive 
                          ? "bg-white text-black border-white shadow-lg" 
                          : "bg-[#121212] hover:bg-[#1c1c1c] text-zinc-300 hover:text-white border-[#222222]"
                      )}
                    >
                      <div className="flex flex-col">
                        <span className="text-xs font-bold leading-tight flex items-center gap-2">
                          {srv.title}
                          {isActive && <Check size={13} className="text-black" />}
                        </span>
                        <span className={cn(
                          "text-[10px] font-mono mt-1",
                          isActive ? "text-zinc-700" : "text-zinc-500"
                        )}>
                          {srv.is_dash ? 'DASH + ClearKey DRM' : 'Direct HLS Stream'}
                        </span>
                      </div>
                      <span className={cn(
                        "text-[10px] font-bold px-2 py-0.5 rounded",
                        isActive ? "bg-black text-white" : "bg-zinc-800 text-zinc-300 group-hover:bg-zinc-700"
                      )}>
                        {srv.quality || 'HD'}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Bottom Controls Bar (with Smart Cinema Inactivity Auto-Hide) */}
          <div 
            className={cn(
              "absolute bottom-4 left-4 right-4 flex items-center justify-between bg-black/85 backdrop-blur-xl border border-white/15 px-4 py-2.5 rounded-2xl z-30 transition-all duration-300 shadow-2xl",
              controlsVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4 pointer-events-none"
            )}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Left Controls: Play/Pause, Volume Slider, Stream Tag */}
            <div className="flex items-center gap-3">
              <button 
                onClick={togglePlay} 
                className="text-white hover:text-zinc-300 transition cursor-pointer p-1"
                title={isPlaying ? "Pause (Space)" : "Play (Space)"}
              >
                {isPlaying ? <Pause size={20} /> : <Play size={20} />}
              </button>

              {/* Interactive Volume Slider */}
              <div className="flex items-center gap-2 group/volume relative">
                <button 
                  onClick={toggleMute} 
                  className="text-white hover:text-zinc-300 transition cursor-pointer p-1"
                  title={isMuted ? "Unmute (M)" : "Mute (M)"}
                >
                  {isMuted || volume === 0 ? (
                    <VolumeX size={20} />
                  ) : volume < 0.5 ? (
                    <Volume1 size={20} />
                  ) : (
                    <Volume2 size={20} />
                  )}
                </button>

                <input 
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={isMuted ? 0 : volume}
                  onChange={(e) => handleVolumeChange(parseFloat(e.target.value))}
                  className="w-16 sm:w-20 h-1.5 bg-zinc-700 accent-white rounded-lg cursor-pointer transition-all hover:w-24"
                  title={`Volume: ${Math.round(volume * 100)}%`}
                />
              </div>

              <span className="text-xs font-mono text-zinc-300 font-medium truncate max-w-[120px] sm:max-w-none hidden sm:inline">
                {activeServer.title} • {activeServer.is_dash ? 'DASH' : 'HLS'}
              </span>
            </div>

            {/* Right Controls: Quality, Aspect Ratio, Server Quick Button, PiP, Fullscreen */}
            <div className="flex items-center gap-2 sm:gap-3">
              {/* Aspect Ratio Menu */}
              <div className="relative">
                <button
                  onClick={() => setIsAspectMenuOpen(prev => !prev)}
                  className="px-2.5 py-1 text-xs font-mono rounded-lg bg-white/10 hover:bg-white/20 text-white border border-white/20 transition flex items-center gap-1.5 cursor-pointer shadow-sm"
                  title="Aspect Ratio Scaling (Hotkey: A)"
                >
                  <Scaling size={13} className="text-zinc-300" />
                  <span className="capitalize">{aspectRatio === 'contain' ? 'Fit' : aspectRatio === 'cover' ? 'Zoom' : 'Stretch'}</span>
                </button>

                {isAspectMenuOpen && (
                  <div className="absolute bottom-full mb-2 right-0 w-36 bg-[#0e0e0e] border border-[#2a2a2a] rounded-xl shadow-2xl overflow-hidden py-1 z-40">
                    <div className="px-3 py-1.5 text-[10px] font-mono text-zinc-400 uppercase tracking-wider border-b border-[#1f1f1f]">
                      Aspect Ratio
                    </div>
                    {(['contain', 'cover', 'fill'] as AspectMode[]).map((mode) => (
                      <button
                        key={mode}
                        onClick={() => cycleAspectRatio(mode)}
                        className={cn(
                          "w-full px-3 py-2 text-xs font-mono text-left flex items-center justify-between transition cursor-pointer",
                          aspectRatio === mode 
                            ? "bg-white text-black font-bold" 
                            : "text-zinc-300 hover:bg-[#1a1a1a] hover:text-white"
                        )}
                      >
                        <span className="capitalize">{mode === 'contain' ? 'Fit (16:9)' : mode === 'cover' ? 'Zoom (Fill)' : 'Stretch'}</span>
                        {aspectRatio === mode && <Check size={13} />}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Dynamic Quality Track Selection Menu (REA: DefaultTrackSelector) */}
              <div className="relative">
                <button
                  onClick={() => setIsQualityMenuOpen(!isQualityMenuOpen)}
                  className="px-2.5 py-1 text-xs font-mono rounded-lg bg-white/10 hover:bg-white/20 text-white border border-white/20 transition flex items-center gap-1.5 cursor-pointer shadow-sm"
                  title="Stream Quality / Resolution (Hotkey: Q)"
                >
                  <Sliders size={13} className="text-zinc-300" />
                  <span>{qualityTracks.find(t => t.id === selectedQuality)?.label || 'Quality: Auto'}</span>
                </button>

                {isQualityMenuOpen && (
                  <div className="absolute bottom-full mb-2 right-0 w-44 bg-[#0e0e0e] border border-[#2a2a2a] rounded-xl shadow-2xl overflow-hidden py-1 z-40">
                    <div className="px-3 py-1.5 text-[10px] font-mono text-zinc-400 uppercase tracking-wider border-b border-[#1f1f1f] flex items-center justify-between">
                      <span>Stream Quality</span>
                      <span className="text-[9px] text-zinc-500">EXOPLAYER ABR</span>
                    </div>
                    {qualityTracks.map((track) => {
                      const isSelected = track.id === selectedQuality;
                      return (
                        <button
                          key={track.id}
                          onClick={() => handleSelectQuality(track.id)}
                          className={`w-full px-3 py-2 text-xs font-mono text-left flex items-center justify-between transition cursor-pointer ${
                            isSelected 
                              ? 'bg-white text-black font-bold' 
                              : 'text-zinc-300 hover:bg-[#1a1a1a] hover:text-white'
                          }`}
                        >
                          <span>{track.label}</span>
                          {isSelected && <Check size={13} />}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* PiP button */}
              <button
                onClick={togglePiP}
                className="text-white hover:text-zinc-300 transition cursor-pointer p-1 hidden md:block"
                title="Picture in Picture Mode"
              >
                <Tv size={18} />
              </button>

              {/* DRM Protection Pill */}
              {activeServer.has_drm && (
                <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-emerald-950/70 text-emerald-300 border border-emerald-800/60 hidden lg:flex items-center gap-1">
                  <ShieldCheck size={12} /> ClearKey Active
                </span>
              )}

              {/* Native Borderless Fullscreen Button */}
              <button 
                onClick={toggleFullscreen} 
                className="text-white hover:text-zinc-300 transition cursor-pointer p-1"
                title={isFullscreen ? "Exit Fullscreen (Esc or F)" : "Borderless Fullscreen (F)"}
              >
                {isFullscreen ? <Minimize2 size={20} /> : <Maximize2 size={20} />}
              </button>
            </div>
          </div>
        </div>

        {/* Server Selection Strip (Displayed below player in Normal Window Mode) */}
        {!isFullscreen && (
          <div className="px-6 py-4 bg-[#0a0a0a] border-t border-[#1a1a1a] flex flex-col shrink-0">
            <div className="flex items-center justify-between mb-3 shrink-0">
              <div className="flex items-center gap-2">
                <Server size={14} className="text-zinc-400" />
                <span className="text-xs font-mono uppercase tracking-wider text-zinc-400">
                  Available Broadcast Servers ({servers.length})
                </span>
              </div>
              <span className="text-[11px] font-mono text-zinc-500 hidden sm:inline">
                Preserved exact APK broadcast order • Click to switch feed dynamically
              </span>
            </div>

            <div className="flex flex-wrap gap-2 max-h-56 overflow-y-auto p-1 custom-scrollbar">
              {servers.map((srv, idx) => {
                const isActive = idx === activeServerIdx;
                return (
                  <button
                    key={`server-${srv.id || 'srv'}-${idx}`}
                    onClick={() => {
                      setActiveServerIdx(idx);
                      setIsQualityMenuOpen(false);
                      showHud(`Switched to Server ${idx + 1}`);
                    }}
                    className={`px-3 py-2 rounded-xl border text-left transition flex items-center gap-2.5 cursor-pointer ${
                      isActive 
                        ? 'bg-white text-black border-white shadow-lg scale-[1.02]' 
                        : 'bg-[#121212] hover:bg-[#1a1a1a] text-zinc-300 hover:text-white border-[#222222]'
                    }`}
                  >
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                      isActive ? 'bg-black text-white' : 'bg-zinc-800 text-zinc-300'
                    }`}>
                      {srv.quality || 'HD'}
                    </span>
                    <div className="flex flex-col">
                      <span className="text-xs font-semibold leading-none">
                        {srv.title}
                      </span>
                      <span className={`text-[10px] font-mono mt-0.5 ${isActive ? 'text-zinc-700' : 'text-zinc-500'}`}>
                        {srv.is_dash ? 'DASH + ClearKey' : 'Direct HLS'}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
