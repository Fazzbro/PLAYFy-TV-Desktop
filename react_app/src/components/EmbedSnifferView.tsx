'use client';
import React, { useState } from 'react';
import { 
  Globe, Zap, Play, Check, AlertCircle, Copy, Radio, 
  ExternalLink, Code2, Sparkles, Layers, RefreshCw
} from 'lucide-react';
import { TextEffect } from './motion-primitives/text-effect';
import { InView } from './motion-primitives/in-view';
import { StreamServer } from './VideoPlayer';

interface EmbedSnifferViewProps {
  onPlayStream: (title: string, subtitle: string, servers: StreamServer[]) => void;
}

export function EmbedSnifferView({ onPlayStream }: EmbedSnifferViewProps) {
  const [targetUrl, setTargetUrl] = useState<string>('');
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [result, setResult] = useState<any | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null);

  // Preset major sports embed test URLs
  const samplePresets = [
    { name: "FC Juárez vs Atlante (FOX DEPORTES)", url: "https://vorasp.online/channels/20078.json" },
    { name: "Stuttgart vs Atlético (SonyLiv Feed)", url: "https://vorasp.online/channels/20041.json" },
    { name: "Sky Cricket Live Broadcast", url: "https://vorasp.online/channels/384.json" },
    { name: "Pakistan vs England Live Event", url: "https://vorasp.online/channels/19733.json" },
  ];

  const handleSniff = async (urlToScan?: string) => {
    const url = urlToScan || targetUrl.trim();
    if (!url) return;

    setIsScanning(true);
    setErrorMsg(null);
    setResult(null);

    try {
      // If user inputs a channel JSON or ID directly
      if (url.includes('channels/') && url.endsWith('.json')) {
        const parts = url.split('channels/')[1].split('.json')[0];
        const res = await fetch(`/api/streams/${parts}`);
        const data = await res.json();
        if (data.streams && data.streams.length > 0) {
          setResult({
            success: true,
            stream_url: data.streams[0].link,
            all_streams: data.streams.map((s: any) => s.link),
            streams_detailed: data.streams,
            depth: 0,
            source_type: "APK Decrypted Dynamic Backlink Channel Endpoint"
          });
          setIsScanning(false);
          return;
        }
      }

      // Execute the 5-phase sniffer crawler via backend
      const res = await fetch('/api/capture-stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();

      if (data.success) {
        setResult(data);
      } else {
        setErrorMsg(data.error || 'No live streaming backlinks found in this embed.');
      }
    } catch (err: any) {
      setErrorMsg(`Sniffer error: ${err.message || 'Connection failure'}`);
    } finally {
      setIsScanning(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedUrl(text);
    setTimeout(() => setCopiedUrl(null), 2000);
  };

  const launchPlayer = () => {
    if (!result) return;
    const servers: StreamServer[] = (result.streams_detailed || [
      {
        id: 1,
        title: "Captured Live Feed",
        link: result.stream_url,
        is_hls: result.is_hls || result.stream_url.includes('.m3u8'),
        is_dash: result.is_dash || result.stream_url.includes('.mpd'),
        has_drm: Boolean(result.has_drm),
        clearkey: result.clearkey || {},
        headers: result.headers || {}
      }
    ]);

    onPlayStream(
      "Captured Live Stream",
      `Source: ${targetUrl || 'Major Sports Embed Crawler'}`,
      servers
    );
  };

  return (
    <div className="space-y-10 animate-fade-in max-w-5xl mx-auto py-6">
      {/* Hero Header */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-mono text-zinc-300">
          <Zap size={13} className="text-white" />
          <span>APK jd.z / jd.b0 Embedded Sniffer Engine</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
          <TextEffect per="word" preset="fade">
            Live Stream Capture & Embed Engine
          </TextEffect>
        </h1>
        <p className="text-sm text-zinc-400 max-w-2xl mx-auto font-sans leading-relaxed">
          Clean-room implementation of PLAYFy TV's 5-phase stream extractor: scans HTML5 video buffers,
          resolves regex patterns, walks player APIs, decodes Base64 payloads, and traverses nested iframes.
        </p>
      </div>

      {/* Input Box Card */}
      <InView
        variants={{
          hidden: { opacity: 0, y: 20 },
          visible: { opacity: 1, y: 0 }
        }}
        transition={{ duration: 0.4 }}
      >
        <div className="p-6 rounded-2xl bg-[#0c0c0c] border border-[#222222] shadow-2xl space-y-5">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Globe className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500" size={18} />
              <input
                type="text"
                value={targetUrl}
                onChange={(e) => setTargetUrl(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSniff()}
                placeholder="Enter sports stream URL, embed iframe source, or channels/{id}.json..."
                className="w-full bg-[#121212] border border-[#262626] rounded-xl pl-12 pr-4 py-3.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-white focus:ring-1 focus:ring-white transition font-mono"
              />
            </div>
            <button
              onClick={() => handleSniff()}
              disabled={isScanning || !targetUrl.trim()}
              className="px-6 py-3.5 rounded-xl bg-white text-black font-semibold text-sm hover:bg-zinc-200 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center justify-center gap-2 shrink-0 shadow-lg"
            >
              {isScanning ? (
                <>
                  <RefreshCw size={16} className="animate-spin" />
                  <span>Scanning...</span>
                </>
              ) : (
                <>
                  <Sparkles size={16} />
                  <span>Capture Stream</span>
                </>
              )}
            </button>
          </div>

          {/* Quick Presets */}
          <div className="space-y-2">
            <span className="text-[11px] font-mono text-zinc-500 uppercase tracking-wider block">
              Quick Test Presets from Clean-Room Analysis:
            </span>
            <div className="flex flex-wrap gap-2">
              {samplePresets.map((preset, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setTargetUrl(preset.url);
                    handleSniff(preset.url);
                  }}
                  className="px-3 py-1.5 rounded-lg border border-[#222222] bg-[#141414] hover:bg-[#1f1f1f] text-xs font-mono text-zinc-300 hover:text-white transition flex items-center gap-1.5"
                >
                  <Radio size={12} className="text-zinc-400" />
                  <span>{preset.name}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </InView>

      {/* Error View */}
      {errorMsg && (
        <div className="p-4 rounded-xl bg-red-950/60 border border-red-800 text-red-200 text-sm flex items-center gap-3 backdrop-blur-md">
          <AlertCircle size={18} className="text-red-400 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Result Display */}
      {result && (
        <InView
          variants={{
            hidden: { opacity: 0, scale: 0.98 },
            visible: { opacity: 1, scale: 1 }
          }}
          transition={{ duration: 0.3 }}
        >
          <div className="p-6 rounded-2xl bg-[#0a0a0a] border border-white/20 shadow-2xl space-y-6">
            <div className="flex items-center justify-between pb-4 border-b border-[#222222]">
              <div className="flex items-center gap-2">
                <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-400"></span>
                <h3 className="font-semibold text-white text-base">
                  Stream Successfully Intercepted
                </h3>
              </div>
              <button
                onClick={launchPlayer}
                className="px-4 py-2 rounded-xl bg-white text-black font-bold text-xs hover:bg-zinc-200 transition flex items-center gap-2 shadow-lg"
              >
                <Play size={14} fill="currentColor" />
                <span>Play Now In Built-In Player</span>
              </button>
            </div>

            {/* Stream URL Row */}
            <div className="space-y-2">
              <span className="text-xs font-mono text-zinc-400 uppercase tracking-wider block">
                Primary Captured Live Endpoint ({result.is_dash ? 'MPEG-DASH' : 'HLS (.m3u8)'}):
              </span>
              <div className="flex items-center gap-2 bg-[#141414] border border-[#222222] p-3 rounded-xl">
                <code className="text-xs font-mono text-zinc-200 flex-1 break-all select-all">
                  {result.stream_url}
                </code>
                <button
                  onClick={() => copyToClipboard(result.stream_url)}
                  className="p-2 rounded-lg bg-[#222222] hover:bg-[#333333] text-zinc-300 hover:text-white transition"
                  title="Copy Stream URL"
                >
                  {copiedUrl === result.stream_url ? <Check size={14} /> : <Copy size={14} />}
                </button>
              </div>
            </div>

            {/* Additional Discovered Feeds */}
            {result.all_streams && result.all_streams.length > 1 && (
              <div className="space-y-2">
                <span className="text-xs font-mono text-zinc-400 uppercase tracking-wider block">
                  Alternate Candidate Stream Feeds ({result.all_streams.length - 1}):
                </span>
                <div className="space-y-1.5">
                  {result.all_streams.slice(1).map((s: string, idx: number) => (
                    <div key={idx} className="flex items-center justify-between p-2.5 rounded-lg bg-[#121212] border border-[#1e1e1e] text-xs font-mono">
                      <span className="text-zinc-300 truncate max-w-xl">{s}</span>
                      <button
                        onClick={() => copyToClipboard(s)}
                        className="text-zinc-500 hover:text-white transition px-2"
                      >
                        {copiedUrl === s ? 'Copied' : 'Copy'}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Sniffer Phase Checklist */}
            <div className="pt-2 border-t border-[#1a1a1a]">
              <span className="text-xs font-mono text-zinc-500 uppercase tracking-wider block mb-2">
                Executed Sniffer Subsystems:
              </span>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
                <div className="p-2 rounded bg-[#111111] text-zinc-300 border border-[#202020] flex items-center gap-1.5">
                  <Check size={12} className="text-white" /> HTML5 Media Probe
                </div>
                <div className="p-2 rounded bg-[#111111] text-zinc-300 border border-[#202020] flex items-center gap-1.5">
                  <Check size={12} className="text-white" /> Regex Parser
                </div>
                <div className="p-2 rounded bg-[#111111] text-zinc-300 border border-[#202020] flex items-center gap-1.5">
                  <Check size={12} className="text-white" /> Player Global Hooks
                </div>
                <div className="p-2 rounded bg-[#111111] text-zinc-300 border border-[#202020] flex items-center gap-1.5">
                  <Check size={12} className="text-white" /> Base64 & Frame Walk
                </div>
              </div>
            </div>
          </div>
        </InView>
      )}
    </div>
  );
}
