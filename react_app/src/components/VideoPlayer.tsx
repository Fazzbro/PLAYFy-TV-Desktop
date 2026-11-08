'use client';
import React, { useEffect, useRef, useState } from 'react';
import Hls from 'hls.js';
import { 
  Play, Pause, Volume2, VolumeX, Maximize, Minimize, 
  Copy, ExternalLink, ShieldCheck, Radio, Server, Check, AlertCircle, RefreshCw, Sliders, X
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
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Dynamic Quality Selection (Recovered from REA: DefaultTrackSelector / TrackSelectionView)
  const [qualityTracks, setQualityTracks] = useState<QualityTrack[]>([
    { id: 'auto', label: 'Auto (ABR)', isAuto: true }
  ]);
  const [selectedQuality, setSelectedQuality] = useState<string>('auto');
  const [isQualityMenuOpen, setIsQualityMenuOpen] = useState<boolean>(false);

  const activeServer = servers[activeServerIdx] || servers[0];
  const hlsInstanceRef = useRef<Hls | null>(null);
  const shakaPlayerRef = useRef<any>(null);

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

  // Fullscreen toggle with robust CSS & OS fallback
  const toggleFullscreen = async () => {
    const el = videoWrapperRef.current;

    if (!isFullscreen) {
      setIsFullscreen(true);
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
          // Native fullscreen denied/unsupported; CSS fullscreen remains active
        }
      }
    } else {
      setIsFullscreen(false);
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
        // Ignored
      }
    }
  };

  // Keyboard controls & fullscreen change sync
  useEffect(() => {
    const handleFsChange = () => {
      const fs = Boolean(
        document.fullscreenElement || 
        (document as any).webkitFullscreenElement || 
        (document as any).mozFullScreenElement || 
        (document as any).msFullscreenElement
      );
      setIsFullscreen(fs);
    };

    document.addEventListener('fullscreenchange', handleFsChange);
    document.addEventListener('webkitfullscreenchange', handleFsChange);

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (isFullscreen) {
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
      }
    };
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('fullscreenchange', handleFsChange);
      document.removeEventListener('webkitfullscreenchange', handleFsChange);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isFullscreen, onClose]);

  // Initialize or switch stream playback
  useEffect(() => {
    if (!videoRef.current || !activeServer) return;

    setErrorMsg(null);
    setIsLoading(true);
    setQualityTracks([{ id: 'auto', label: 'Auto (ABR)', isAuto: true }]);
    setSelectedQuality('auto');
    setIsQualityMenuOpen(false);

    const video = videoRef.current;
    // Prefer direct link first for high speed and direct CDN chunk resolution.
    // Fall back to proxy if direct playback fails or if custom headers require it.
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

    // Scenario A: MPEG-DASH with ClearKey DRM (e.g. TNT Sports, FC Juárez, Willow, FanCode FHD)
    if (isDash || activeServer.has_drm) {
      try {
        shaka.polyfill.installAll();
        if (shaka.Player.isBrowserSupported()) {
          const player = new shaka.Player(video);
          shakaPlayerRef.current = player;

          // Configure ClearKey DRM if keys are present
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
                console.error('Proxy fallback also failed:', e);
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

            // Extract variant quality tracks from Shaka
            try {
              const variantTracks = player.getVariantTracks();
              const tracks: QualityTrack[] = [{ id: 'auto', label: 'Auto (ABR)', isAuto: true }];
              const seenHeights = new Set<number>();

              const sorted = variantTracks
                .filter((t: any) => t.type === 'variant' && typeof t.height === 'number' && t.height > 0)
                .sort((a: any, b: any) => (b.height || 0) - (a.height || 0));

              for (const t of sorted) {
                const h = t.height as number;
                if (!seenHeights.has(h)) {
                  seenHeights.add(h);
                  const label = h >= 1080 ? `${h}p FHD` : h >= 720 ? `${h}p HD` : `${h}p SD`;
                  tracks.push({
                    id: String(t.id),
                    label,
                    height: h,
                    bitrate: t.bandwidth || undefined
                  });
                }
              }

              if (tracks.length > 1) {
                setQualityTracks(tracks);
              } else {
                setQualityTracks([
                  { id: 'auto', label: 'Auto (ABR)', isAuto: true },
                  { id: '1080', label: '1080p FHD' },
                  { id: '720', label: '720p HD' }
                ]);
              }
            } catch (err) {
              console.warn('Track extraction failed:', err);
            }
          }).catch((err: any) => {
            console.error('Shaka Load Error:', err);
            handleShakaError(err.code, err.message);
          });
          return;
        }
      } catch (e: any) {
        console.warn('Shaka init error, falling back:', e);
      }
    }

    // Scenario B: HLS stream (.m3u8) via Hls.js
    if (isHls && Hls.isSupported()) {
      const hls = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
        backBufferLength: 90,
      });
      hlsInstanceRef.current = hls;

      let hasAttemptedHlsFallback = false;

      hls.loadSource(currentUrl);
      hls.attachMedia(video);

      hls.on(Hls.Events.MANIFEST_PARSED, (_event, data) => {
        setIsLoading(false);
        video.play().catch(() => setIsPlaying(false));

        // Extract HLS resolution levels
        const tracks: QualityTrack[] = [{ id: 'auto', label: 'Auto (ABR)', isAuto: true }];
        if (data.levels && data.levels.length > 0) {
          data.levels.forEach((lvl, index) => {
            const h = lvl.height || 720;
            const label = h >= 1080 ? `${h}p FHD` : h >= 720 ? `${h}p HD` : `${h}p SD`;
            tracks.push({
              id: String(index),
              label,
              height: h,
              bitrate: lvl.bitrate
            });
          });
          setQualityTracks(tracks);
        } else {
          setQualityTracks([
            { id: 'auto', label: 'Auto (ABR)', isAuto: true },
            { id: '1080', label: '1080p FHD' },
            { id: '720', label: '720p HD' }
          ]);
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

    // Scenario C: Native browser HLS (Safari/iOS/Edge direct)
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

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current.play();
      setIsPlaying(true);
    } else {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  };

  const toggleMute = () => {
    if (!videoRef.current) return;
    videoRef.current.muted = !videoRef.current.muted;
    setIsMuted(videoRef.current.muted);
  };

  const copyStreamUrl = () => {
    if (!activeServer?.link) return;
    navigator.clipboard.writeText(activeServer.link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const openExternal = () => {
    if (!activeServer?.link) return;
    window.open(activeServer.link, '_blank');
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/95 backdrop-blur-xl p-2 sm:p-6 flex flex-col items-center justify-start sm:justify-center min-h-screen py-4 sm:py-8 animate-fade-in selection:bg-white selection:text-black">
      <div 
        ref={containerRef}
        className={cn(
          "relative w-full max-w-5xl bg-[#0a0a0a] border border-[#222222] rounded-2xl shadow-2xl flex flex-col my-auto transition-all",
          isFullscreen 
            ? "fixed inset-0 z-[100] w-screen h-screen max-w-none rounded-none border-none p-0 m-0 overflow-hidden bg-black" 
            : "overflow-hidden"
        )}
      >
        {/* Header Bar (Hidden in Fullscreen for immersive experience) */}
        {!isFullscreen && (
          <div className="flex items-center justify-between px-6 py-3.5 border-b border-[#1c1c1c] bg-[#0c0c0c]/90 backdrop-blur-md shrink-0">
            <div className="flex items-center gap-3">
              <span className="flex h-3 w-3 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-white"></span>
              </span>
              <div>
                <h2 className="text-white font-bold text-base sm:text-lg tracking-tight leading-none font-display">
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
              <button
                onClick={copyStreamUrl}
                className="px-3 py-1.5 text-xs font-mono rounded-lg border border-[#262626] bg-[#141414] hover:bg-[#1f1f1f] text-zinc-300 hover:text-white transition flex items-center gap-1.5 cursor-pointer"
                title="Copy Stream URL"
              >
                {copied ? <Check size={14} className="text-white" /> : <Copy size={14} />}
                <span>{copied ? 'Copied' : 'Copy URL'}</span>
              </button>

              <button
                onClick={openExternal}
                className="px-3 py-1.5 text-xs font-mono rounded-lg border border-[#262626] bg-[#141414] hover:bg-[#1f1f1f] text-zinc-300 hover:text-white transition flex items-center gap-1.5 cursor-pointer"
                title="Open in Browser / External VLC"
              >
                <ExternalLink size={14} />
                <span className="hidden sm:inline">External</span>
              </button>

              <button
                onClick={onClose}
                className="px-3 py-1.5 text-xs font-bold rounded-lg bg-white text-black hover:bg-zinc-200 transition ml-2 cursor-pointer shadow-md flex items-center gap-1.5"
              >
                <X size={14} />
                <span>Close</span>
              </button>
            </div>
          </div>
        )}

        {/* Video Canvas Area */}
        <div 
          ref={videoWrapperRef}
          className={cn(
            "relative bg-black flex items-center justify-center overflow-hidden group select-none transition-all",
            isFullscreen 
              ? "w-screen h-screen flex-1" 
              : "w-full aspect-video max-h-[52vh]"
          )}
          onDoubleClick={toggleFullscreen}
        >
          <video
            ref={videoRef}
            className="w-full h-full object-contain cursor-pointer"
            onClick={togglePlay}
            playsInline
          />

          {/* Loading Indicator */}
          {isLoading && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/60 backdrop-blur-sm z-20 pointer-events-none">
              <RefreshCw className="animate-spin text-white mb-3" size={36} />
              <p className="text-xs font-mono uppercase tracking-widest text-zinc-300">
                Connecting To Server {activeServerIdx + 1} ({activeServer.title})...
              </p>
            </div>
          )}

          {/* Error Banner with Server Recovery */}
          {errorMsg && (
            <div className="absolute inset-x-6 top-6 z-30 p-4 rounded-xl bg-red-950/80 border border-red-800 text-red-200 flex items-start gap-3 backdrop-blur-md shadow-2xl">
              <AlertCircle className="text-red-400 shrink-0 mt-0.5" size={18} />
              <div className="flex-1 text-sm">
                <p className="font-medium text-white">{errorMsg}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {servers.map((s, idx) => (
                    idx !== activeServerIdx && (
                      <button
                        key={`err-srv-${s.id}-${idx}`}
                        onClick={() => setActiveServerIdx(idx)}
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

          {/* Overlaid Play/Pause controls (auto-hiding in fullscreen) */}
          <div className={cn(
            "absolute bottom-4 left-4 right-4 flex items-center justify-between bg-black/80 backdrop-blur-md border border-white/10 px-4 py-2.5 rounded-xl z-20 transition-opacity duration-200",
            isFullscreen ? "opacity-0 group-hover:opacity-100" : "opacity-0 group-hover:opacity-100"
          )}>
            <div className="flex items-center gap-3">
              <button onClick={togglePlay} className="text-white hover:text-zinc-300 transition cursor-pointer">
                {isPlaying ? <Pause size={20} /> : <Play size={20} />}
              </button>
              <button onClick={toggleMute} className="text-white hover:text-zinc-300 transition cursor-pointer">
                {isMuted ? <VolumeX size={20} /> : <Volume2 size={20} />}
              </button>
              <span className="text-xs font-mono text-zinc-300 font-medium truncate max-w-[200px] sm:max-w-none">
                {activeServer.title} • {activeServer.is_dash ? 'DASH' : 'HLS'}
              </span>
            </div>

            <div className="flex items-center gap-3">
              {/* Dynamic Quality Track Selection Menu (REA: DefaultTrackSelector) */}
              <div className="relative">
                <button
                  onClick={() => setIsQualityMenuOpen(!isQualityMenuOpen)}
                  className="px-2.5 py-1 text-xs font-mono rounded-lg bg-white/10 hover:bg-white/20 text-white border border-white/20 transition flex items-center gap-1.5 cursor-pointer shadow-sm"
                  title="Select Stream Quality / Resolution"
                >
                  <Sliders size={13} className="text-zinc-300" />
                  <span>{qualityTracks.find(t => t.id === selectedQuality)?.label || 'Quality: Auto'}</span>
                </button>

                {/* Quality Options Dropdown */}
                {isQualityMenuOpen && (
                  <div className="absolute bottom-full mb-2 right-0 w-44 bg-[#0e0e0e] border border-[#2a2a2a] rounded-xl shadow-2xl overflow-hidden py-1 z-30">
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

              {activeServer.has_drm && (
                <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-emerald-950/70 text-emerald-300 border border-emerald-800/60 hidden sm:flex items-center gap-1">
                  <ShieldCheck size={12} /> ClearKey Active
                </span>
              )}
              <button 
                onClick={toggleFullscreen} 
                className="text-white hover:text-zinc-300 transition cursor-pointer p-1"
                title={isFullscreen ? "Exit Fullscreen (Esc or F)" : "Fullscreen (F)"}
              >
                {isFullscreen ? <Minimize size={20} /> : <Maximize size={20} />}
              </button>
            </div>
          </div>
        </div>

        {/* Server Selection Strip (Hidden in Fullscreen) */}
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
