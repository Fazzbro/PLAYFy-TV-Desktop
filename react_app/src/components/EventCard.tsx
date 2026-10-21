'use client';
import React, { useState } from 'react';
import { Play, Trophy, Pin, Radio, Server, Clock } from 'lucide-react';
import { Spotlight } from './motion-primitives/spotlight';
import { StreamServer } from './VideoPlayer';

export interface LiveEventItem {
  id: number | string;
  title: string;
  category: 'Football' | 'Cricket';
  image?: string;
  eventInfo: {
    eventName: string;
    teamA: string;
    teamB: string;
    teamAFlag?: string;
    teamBFlag?: string;
    startTime: string;
    endTime: string;
    isPinned: boolean;
    eventBanner?: string;
  };
  status: {
    state: 'LIVE' | 'STARTING_SOON' | 'UPCOMING' | 'ENDED';
    state_priority: number;
    badge_text: string;
    badge_color: string;
    minute_display?: string;
    score_a?: number | string | null;
    score_b?: number | string | null;
    standing?: string;
    period?: string;
    seconds_left: number;
    elapsed_seconds: number;
    result_note?: string;
    source?: string;
  };
  formats_count: number;
  formats_preview: string[];
}

interface EventCardProps {
  event: LiveEventItem;
  onSelect: (event: LiveEventItem, servers: StreamServer[]) => void;
}

export const EventCard = React.memo(function EventCard({ event, onSelect }: EventCardProps) {
  const [isLoadingStreams, setIsLoadingStreams] = useState<boolean>(false);
  const ev = event.eventInfo;
  const isLive = event.status.state === 'LIVE';
  const isStartingSoon = event.status.state === 'STARTING_SOON';
  const isEnded = event.status.state === 'ENDED';
  const isCricket = event.category.toLowerCase() === 'cricket';
  const hasScore = event.status.score_a != null && event.status.score_b != null;

  const handleWatchClick = async (e?: React.MouseEvent) => {
    if (e) {
      e.stopPropagation();
    }
    if (isLoadingStreams) return;

    setIsLoadingStreams(true);
    try {
      const res = await fetch(`/api/streams/${event.id}`);
      const data = await res.json();
      const servers = data.streams || [];
      onSelect(event, servers);
    } catch (err) {
      console.error('Failed to resolve stream links:', err);
      onSelect(event, []);
    } finally {
      setIsLoadingStreams(false);
    }
  };

  return (
    <div 
      onClick={(e) => handleWatchClick(e)}
      className="group relative rounded-2xl bg-[#0a0a0a] border border-[#1e1e1e] hover:border-white/40 transition-all duration-200 overflow-hidden shadow-xl hover:shadow-2xl flex flex-col justify-between cursor-pointer select-none"
    >
      {/* Subtle Spotlight Effect */}
      <Spotlight size={240} className="from-white/10" />

      {/* Top Banner: League & Pinned */}
      <div className="p-5 pb-3">
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#141414] border border-[#222222] text-[11px] font-mono text-zinc-300">
            <Trophy size={12} className="text-zinc-400" />
            <span className="truncate max-w-[190px]">{ev.eventName}</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-white/5 border border-white/10 text-zinc-300">
              {isCricket ? 'Cricket' : 'Football'}
            </span>
            {ev.isPinned && (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-white text-black font-extrabold text-[10px] uppercase tracking-wider">
                <Pin size={10} fill="currentColor" /> Pinned
              </span>
            )}
          </div>
        </div>

        {/* Teams Matchup Row with Live Score Standings & Real Match Minute */}
        <div className="space-y-1.5 py-2">
          {/* Team A Row */}
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              {ev.teamAFlag ? (
                <img 
                  src={ev.teamAFlag} 
                  alt="" 
                  className="w-5 h-5 object-contain rounded-full bg-zinc-800 shrink-0" 
                  onError={(e) => { (e.target as any).style.display = 'none'; }} 
                />
              ) : (
                <div className="w-5 h-5 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-[10px] font-mono text-zinc-300 shrink-0">
                  {ev.teamA.charAt(0)}
                </div>
              )}
              <span className="text-sm sm:text-base font-bold text-white tracking-tight truncate">
                {ev.teamA}
              </span>
            </div>

            {hasScore ? (
              <div className={`px-2.5 py-0.5 min-w-[28px] text-center rounded-lg font-mono font-black text-sm tracking-tight border transition-all shrink-0 ${
                isLive 
                  ? 'bg-white text-black border-white shadow-[0_0_12px_rgba(255,255,255,0.25)]' 
                  : 'bg-zinc-800 text-zinc-100 border-zinc-700'
              }`}>
                {event.status.score_a}
              </div>
            ) : (
              isLive && (
                <span className="text-[11px] font-mono text-zinc-400 shrink-0">In Progress</span>
              )
            )}
          </div>

          {/* VS Divider & Live Minute Tag */}
          <div className="flex items-center justify-between pl-8 pr-1 my-0.5">
            <span className="text-[10px] font-mono text-zinc-600 uppercase tracking-widest">vs</span>
            {isLive && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-white/10 border border-white/20 text-white font-mono text-[11px] font-bold shadow-sm">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span>{event.status.minute_display || 'LIVE'}</span>
              </span>
            )}
            {isEnded && (
              <span className="inline-flex items-center px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-400 font-mono text-[10px] font-bold">
                FT
              </span>
            )}
            {isStartingSoon && (
              <span className="inline-flex items-center px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-300 font-mono text-[10px]">
                {event.status.minute_display || 'Starts Soon'}
              </span>
            )}
          </div>

          {/* Team B Row */}
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              {ev.teamBFlag ? (
                <img 
                  src={ev.teamBFlag} 
                  alt="" 
                  className="w-5 h-5 object-contain rounded-full bg-zinc-800 shrink-0" 
                  onError={(e) => { (e.target as any).style.display = 'none'; }} 
                />
              ) : (
                <div className="w-5 h-5 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-[10px] font-mono text-zinc-300 shrink-0">
                  {ev.teamB.charAt(0)}
                </div>
              )}
              <span className="text-sm sm:text-base font-bold text-white tracking-tight truncate">
                {ev.teamB}
              </span>
            </div>

            {hasScore && (
              <div className={`px-2.5 py-0.5 min-w-[28px] text-center rounded-lg font-mono font-black text-sm tracking-tight border transition-all shrink-0 ${
                isLive 
                  ? 'bg-white text-black border-white shadow-[0_0_12px_rgba(255,255,255,0.25)]' 
                  : 'bg-zinc-800 text-zinc-100 border-zinc-700'
              }`}>
                {event.status.score_b}
              </div>
            )}
          </div>

          {/* Cricket Summary / Overs Ticker */}
          {isCricket && event.status.standing && (
            <div className="mt-2.5 px-3 py-1.5 rounded-xl bg-zinc-900/90 border border-zinc-800 text-[11px] font-mono text-zinc-300 flex items-center justify-between">
              <span className="truncate text-white font-semibold">{event.status.standing}</span>
              {event.status.period && (
                <span className="shrink-0 text-[10px] text-zinc-400 uppercase tracking-wider ml-2">{event.status.period}</span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Card Footer: Live Status & Action Button */}
      <div className="px-5 py-4 border-t border-[#161616] bg-[#080808]/60 flex items-center justify-between gap-3 relative z-10">
        {/* Status Badge */}
        <div>
          {isLive ? (
            <div className="flex items-center gap-2">
              <span className="flex h-2 w-2 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400"></span>
              </span>
              <span className="text-xs font-mono font-black text-white tracking-wider">
                LIVE {event.status.minute_display || ''}
              </span>
              {event.status.standing && !isCricket && (
                <span className="px-2 py-0.5 rounded-md bg-white/10 border border-white/20 text-[11px] font-mono font-black text-white">
                  {event.status.standing}
                </span>
              )}
            </div>
          ) : isStartingSoon ? (
            <div className="flex items-center gap-1.5 text-xs font-mono text-zinc-300">
              <Clock size={12} className="text-zinc-400" />
              <span>{event.status.badge_text}</span>
            </div>
          ) : isEnded ? (
            <div className="flex items-center gap-1.5 text-xs font-mono text-zinc-400">
              <Clock size={12} className="text-zinc-500" />
              <span>Full Time (FT) {event.status.standing && !isCricket ? `• ${event.status.standing}` : ''}</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-xs font-mono text-zinc-500">
              <Clock size={12} />
              <span>{event.status.badge_text}</span>
            </div>
          )}

          <div className="flex items-center gap-1 text-[11px] font-mono text-zinc-500 mt-1">
            <Server size={11} />
            <span>{event.formats_count} Broadcast Servers</span>
          </div>
        </div>

        {/* Watch Button */}
        <button
          onClick={(e) => handleWatchClick(e)}
          disabled={isLoadingStreams}
          className="relative z-20 cursor-pointer pointer-events-auto px-4 py-2 rounded-xl bg-white text-black font-bold text-xs hover:bg-zinc-200 active:scale-95 transition-all flex items-center gap-1.5 shrink-0 shadow-md group-hover:scale-105"
        >
          {isLoadingStreams ? (
            <div className="w-3.5 h-3.5 border-2 border-black border-t-transparent rounded-full animate-spin" />
          ) : (
            <Play size={13} fill="currentColor" />
          )}
          <span>Watch Live</span>
        </button>
      </div>
    </div>
  );
});
