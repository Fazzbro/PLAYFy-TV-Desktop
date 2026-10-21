'use client';
import React, { useState, useEffect } from 'react';
import { Tv, Play, Radio, Search, Server, Sparkles } from 'lucide-react';
import { Spotlight } from './motion-primitives/spotlight';
import { InView } from './motion-primitives/in-view';
import { StreamServer } from './VideoPlayer';

interface ChannelItem {
  id: string | number;
  title: string;
  image?: string;
  sport: 'Cricket' | 'Football';
  formats_count: number;
  formats_preview: string[];
}

interface ChannelsViewProps {
  onPlayStream: (title: string, subtitle: string, servers: StreamServer[]) => void;
}

export function ChannelsView({ onPlayStream }: ChannelsViewProps) {
  const [channels, setChannels] = useState<ChannelItem[]>([]);
  const [sportFilter, setSportFilter] = useState<'All' | 'Football' | 'Cricket'>('All');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [loadingChannelId, setLoadingChannelId] = useState<string | number | null>(null);

  useEffect(() => {
    fetchChannels();
  }, [sportFilter]);

  const fetchChannels = async () => {
    setIsLoading(true);
    try {
      const sportParam = sportFilter === 'All' ? '' : `?sport=${sportFilter}`;
      const res = await fetch(`/api/channels${sportParam}`);
      const data = await res.json();
      setChannels(data.channels || []);
    } catch (e) {
      console.error('Failed to fetch channels:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleWatchChannel = async (ch: ChannelItem) => {
    setLoadingChannelId(ch.id);
    try {
      const res = await fetch(`/api/streams/${ch.id}`);
      const data = await res.json();
      const servers = data.streams || [];
      onPlayStream(
        ch.title,
        `Live 24/7 ${ch.sport} TV Channel • ${servers.length} Broadcast Servers`,
        servers
      );
    } catch (e) {
      console.error('Failed to resolve channel streams:', e);
      onPlayStream(ch.title, `Live ${ch.sport} Channel`, []);
    } finally {
      setLoadingChannelId(null);
    }
  };

  const filteredChannels = channels.filter(ch => {
    if (!searchQuery.trim()) return true;
    return ch.title.toLowerCase().includes(searchQuery.toLowerCase().trim());
  });

  return (
    <div className="space-y-8 animate-fade-in py-4">
      {/* Top Header & Filters */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[#1c1c1c] pb-6">
        <div>
          <h2 className="text-2xl font-black font-display tracking-tight text-white flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-white/10 border border-white/20 flex items-center justify-center shadow-inner">
              <Tv className="text-white" size={20} />
            </div>
            <span className="tracking-tight bg-gradient-to-b from-white via-zinc-100 to-zinc-400 bg-clip-text text-transparent">
              Dedicated Sports TV Channels
            </span>
          </h2>
          <p className="text-xs font-mono text-zinc-400 mt-1 flex items-center gap-2">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>24/7 Cricket & Football Satellite Feeds • Decrypted Direct Streams</span>
          </p>
        </div>

        {/* Filter Pills & Search */}
        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
          <div className="flex items-center p-1 rounded-xl bg-[#0e0e0e] border border-[#222222]">
            {(['All', 'Football', 'Cricket'] as const).map((sp) => (
              <button
                key={sp}
                onClick={() => setSportFilter(sp)}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono transition ${
                  sportFilter === sp
                    ? 'bg-white text-black font-bold shadow'
                    : 'text-zinc-400 hover:text-white'
                }`}
              >
                {sp === 'Football' ? 'Football' : sp === 'Cricket' ? 'Cricket' : 'All Channels'}
              </button>
            ))}
          </div>

          <div className="relative flex-1 sm:flex-initial">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" size={14} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter channels..."
              className="bg-[#0e0e0e] border border-[#222222] rounded-xl pl-9 pr-3 py-1.5 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-white transition w-full sm:w-48 font-mono"
            />
          </div>
        </div>
      </div>

      {/* Grid of Channels */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-32 rounded-2xl bg-[#0a0a0a] border border-[#1a1a1a] animate-pulse" />
          ))}
        </div>
      ) : filteredChannels.length === 0 ? (
        <div className="text-center py-20 text-zinc-500 font-mono text-sm">
          No channels match your query.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredChannels.map((ch) => (
            <div 
              key={ch.id}
              onClick={() => handleWatchChannel(ch)}
              className="group relative rounded-2xl bg-[#0a0a0a] border border-[#1e1e1e] hover:border-white/40 transition-all duration-200 p-5 flex flex-col justify-between h-40 shadow-lg hover:shadow-xl cursor-pointer select-none"
            >
              <Spotlight size={200} className="from-white/10" />

              <div className="flex items-start justify-between gap-3 relative z-10">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-[#141414] border border-[#262626] flex items-center justify-center text-white shrink-0 font-mono text-sm font-bold">
                    {ch.image ? (
                      <img src={ch.image} alt="" className="w-7 h-7 object-contain rounded" onError={(e) => { (e.target as any).style.display = 'none'; }} />
                    ) : (
                      ch.title.charAt(0)
                    )}
                  </div>
                  <div>
                    <h3 className="font-bold text-white text-base tracking-tight leading-snug">
                      {ch.title}
                    </h3>
                    <span className="text-[11px] font-mono text-zinc-400">
                      {ch.sport} Network
                    </span>
                  </div>
                </div>

                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-white/5 border border-white/10 text-zinc-300">
                  {ch.sport}
                </span>
              </div>

              <div className="flex items-center justify-between border-t border-[#161616] pt-3 relative z-10">
                <div className="flex items-center gap-1.5 text-[11px] font-mono text-zinc-500">
                  <Radio size={12} className="text-emerald-400" />
                  <span>24/7 Live Feed</span>
                </div>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleWatchChannel(ch);
                  }}
                  disabled={loadingChannelId === ch.id}
                  className="relative z-20 cursor-pointer pointer-events-auto px-3.5 py-1.5 rounded-xl bg-white text-black font-bold text-xs hover:bg-zinc-200 active:scale-95 transition flex items-center gap-1.5 shadow"
                >
                  {loadingChannelId === ch.id ? (
                    <div className="w-3.5 h-3.5 border-2 border-black border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <Play size={12} fill="currentColor" />
                  )}
                  <span>Watch Channel</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
