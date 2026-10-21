'use client';
import React, { useState, useEffect, useCallback } from 'react';
import { 
  Trophy, Tv, Zap, Radio, Search, Clock, ShieldCheck, 
  RefreshCw, Play, Filter, Flame, Layers
} from 'lucide-react';
import { AnimatedBackground } from './components/motion-primitives/animated-background';
import { EventCard, LiveEventItem } from './components/EventCard';
import { VideoPlayer, StreamServer } from './components/VideoPlayer';
import { ChannelsView } from './components/ChannelsView';
import { EmbedSnifferView } from './components/EmbedSnifferView';

// Isolated Clock Component to prevent App re-renders every 1000ms
function UtcClock() {
  const [time, setTime] = useState<string>('');
  useEffect(() => {
    const update = () => {
      const now = new Date();
      setTime(now.toUTCString().replace('GMT', 'UTC'));
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#0e0e0e] border border-[#222222] text-[11px] font-mono text-zinc-400">
      <Clock size={12} />
      <span>{time || 'UTC CLOCK'}</span>
    </div>
  );
}

export function App() {
  const [activeTab, setActiveTab] = useState<'events' | 'channels' | 'sniffer'>('events');
  const [events, setEvents] = useState<LiveEventItem[]>([]);
  const [counts, setCounts] = useState({ all: 0, football: 0, cricket: 0 });
  const [categoryFilter, setCategoryFilter] = useState<'All' | 'Football' | 'Cricket'>('All');
  const [timelineFilter, setTimelineFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Active Video Player state
  const [playerModal, setPlayerModal] = useState<{
    isOpen: boolean;
    title: string;
    subtitle?: string;
    servers: StreamServer[];
  }>({
    isOpen: false,
    title: '',
    servers: []
  });

  // Fetch events
  useEffect(() => {
    fetchEvents();
  }, [categoryFilter, timelineFilter]);

  const fetchEvents = async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      if (categoryFilter !== 'All') params.append('category', categoryFilter);
      if (timelineFilter !== 'all') params.append('timeline', timelineFilter);
      if (searchQuery.trim()) params.append('search', searchQuery.trim());

      const res = await fetch(`/api/events?${params.toString()}`);
      const data = await res.json();
      setEvents(data.events || []);
      if (data.counts) {
        setCounts(data.counts);
      }
    } catch (e) {
      console.error('Failed to fetch live events:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLaunchPlayer = useCallback((title: string, subtitle: string, servers: StreamServer[]) => {
    setPlayerModal({
      isOpen: true,
      title,
      subtitle,
      servers
    });
  }, []);

  const handleEventCardSelect = useCallback((event: LiveEventItem, servers: StreamServer[]) => {
    const scoreSummary = event.status.standing && event.status.standing !== 'vs' 
      ? `[ ${event.status.minute_display || ''} • ${event.status.standing} ]  ` 
      : '';
    const subtitle = `${scoreSummary}${event.eventInfo.eventName} • ${servers.length} Broadcast Servers Available`;
    handleLaunchPlayer(
      `${event.eventInfo.teamA} vs ${event.eventInfo.teamB}`,
      subtitle,
      servers
    );
  }, [handleLaunchPlayer]);

  return (
    <div className="min-h-screen bg-[#050505] text-white flex flex-col selection:bg-white selection:text-black">
      {/* Top Navbar */}
      <header className="sticky top-0 z-40 bg-[#050505]/80 backdrop-blur-xl border-b border-[#1a1a1a]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
          {/* Logo & Status */}
          <div className="flex items-center gap-3">
            <img 
              src="/logo.png" 
              alt="PLAYFy TV Logo" 
              className="w-9 h-9 rounded-xl object-contain shadow-md border border-white/20 bg-black/50 p-0.5 shrink-0" 
            />
            <div className="flex flex-col">
              <span className="font-black text-sm font-display tracking-wider uppercase bg-gradient-to-r from-white via-zinc-200 to-zinc-400 bg-clip-text text-transparent">
                PLAYFY // TV
              </span>
              <div className="flex items-center gap-1.5 text-[10px] font-mono text-zinc-400">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span>REAL-TIME FEEDS</span>
              </div>
            </div>
          </div>

          {/* Center Navigation Tabs with Animated Background */}
          <nav className="hidden md:flex items-center p-1 rounded-xl bg-[#0e0e0e] border border-[#222222]">
            <AnimatedBackground
              defaultValue={activeTab}
              onValueChange={(id) => id && setActiveTab(id as any)}
              className="bg-white rounded-lg shadow-sm"
              transition={{ type: 'spring', bounce: 0.15, duration: 0.3 }}
            >
              <button
                data-id="events"
                className={`px-4 py-1.5 text-xs font-mono font-medium transition ${
                  activeTab === 'events' ? 'text-black font-bold' : 'text-zinc-400 hover:text-white'
                }`}
              >
                Live Matches
              </button>
              <button
                data-id="channels"
                className={`px-4 py-1.5 text-xs font-mono font-medium transition ${
                  activeTab === 'channels' ? 'text-black font-bold' : 'text-zinc-400 hover:text-white'
                }`}
              >
                TV Channels
              </button>
              <button
                data-id="sniffer"
                className={`px-4 py-1.5 text-xs font-mono font-medium transition ${
                  activeTab === 'sniffer' ? 'text-black font-bold' : 'text-zinc-400 hover:text-white'
                }`}
              >
                Embed Sniffer
              </button>
            </AnimatedBackground>
          </nav>

          {/* Right Clock & Refresh */}
          <div className="flex items-center gap-3">
            <UtcClock />

            <button
              onClick={() => fetchEvents()}
              disabled={isLoading}
              className="p-2 rounded-lg border border-[#222222] bg-[#0e0e0e] hover:bg-[#161616] text-zinc-300 hover:text-white transition"
              title="Refresh Feeds"
            >
              <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        {/* Mobile Tab Switcher */}
        <div className="md:hidden flex items-center justify-around border-t border-[#1a1a1a] p-1 bg-[#0a0a0a]">
          <button
            onClick={() => setActiveTab('events')}
            className={`px-3 py-1.5 text-xs font-mono ${activeTab === 'events' ? 'text-white font-bold' : 'text-zinc-500'}`}
          >
            Live Matches
          </button>
          <button
            onClick={() => setActiveTab('channels')}
            className={`px-3 py-1.5 text-xs font-mono ${activeTab === 'channels' ? 'text-white font-bold' : 'text-zinc-500'}`}
          >
            Channels
          </button>
          <button
            onClick={() => setActiveTab('sniffer')}
            className={`px-3 py-1.5 text-xs font-mono ${activeTab === 'sniffer' ? 'text-white font-bold' : 'text-zinc-500'}`}
          >
            Embed Sniffer
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6">
        {/* VIEW 1: Live Matches & Events */}
        {activeTab === 'events' && (
          <div className="space-y-6 animate-fade-in">
            {/* Hero Subtitle Banner */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-[#1a1a1a]">
              <div>
                <h1 className="text-2xl sm:text-3xl font-black font-display tracking-tight text-white flex items-center gap-3">
                  <div className="p-1.5 rounded-lg bg-white/10 border border-white/20 flex items-center justify-center shadow-inner">
                    <Flame className="text-white shrink-0" size={20} />
                  </div>
                  <span className="tracking-tight bg-gradient-to-b from-white via-zinc-100 to-zinc-400 bg-clip-text text-transparent">
                    Real Live Sports Events
                  </span>
                </h1>
                <p className="text-xs font-mono text-zinc-400 mt-1 flex items-center gap-2">
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span>Strictly Cricket & Football • Direct Multi-Server HLS & ClearKey Decrypted Streams</span>
                </p>
              </div>

              {/* Search Box */}
              <div className="relative w-full md:w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" size={14} />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && fetchEvents()}
                  placeholder="Search clubs, teams..."
                  className="w-full bg-[#0d0d0d] border border-[#222222] rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-white transition font-mono"
                />
              </div>
            </div>

            {/* Filter Toolbar: Category Chips & Timeline Sub-Filters */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              {/* Category Chips: All, Football, Cricket */}
              <div className="flex items-center p-1 rounded-xl bg-[#0c0c0c] border border-[#202020]">
                <AnimatedBackground
                  defaultValue={categoryFilter}
                  onValueChange={(id) => id && setCategoryFilter(id as any)}
                  className="bg-white rounded-lg shadow"
                  transition={{ type: 'spring', bounce: 0.15, duration: 0.3 }}
                >
                  <button
                    data-id="All"
                    className={`px-3 py-1.5 text-xs font-mono transition ${
                      categoryFilter === 'All' ? 'text-black font-bold' : 'text-zinc-400 hover:text-white'
                    }`}
                  >
                    All Sports ({counts.all})
                  </button>
                  <button
                    data-id="Football"
                    className={`px-3 py-1.5 text-xs font-mono transition ${
                      categoryFilter === 'Football' ? 'text-black font-bold' : 'text-zinc-400 hover:text-white'
                    }`}
                  >
                    Football ({counts.football})
                  </button>
                  <button
                    data-id="Cricket"
                    className={`px-3 py-1.5 text-xs font-mono transition ${
                      categoryFilter === 'Cricket' ? 'text-black font-bold' : 'text-zinc-400 hover:text-white'
                    }`}
                  >
                    Cricket ({counts.cricket})
                  </button>
                </AnimatedBackground>
              </div>

              {/* Timeline Sub-filters (od.s.k) */}
              <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
                {[
                  { id: 'all', label: 'All' },
                  { id: 'live', label: 'Live Now' },
                  { id: 'today', label: 'Today' },
                  { id: 'upcoming', label: 'Upcoming' },
                  { id: 'finished', label: 'Finished' },
                ].map((tf) => (
                  <button
                    key={tf.id}
                    onClick={() => setTimelineFilter(tf.id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-mono border transition ${
                      timelineFilter === tf.id
                        ? 'bg-zinc-800 text-white border-white/30'
                        : 'bg-transparent text-zinc-400 border-transparent hover:border-[#222222] hover:text-zinc-200'
                    }`}
                  >
                    {tf.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Event Cards Grid */}
            {isLoading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {[...Array(6)].map((_, i) => (
                  <div key={i} className="h-56 rounded-2xl bg-[#0a0a0a] border border-[#1a1a1a] animate-pulse" />
                ))}
              </div>
            ) : events.length === 0 ? (
              <div className="p-16 rounded-2xl bg-[#0a0a0a] border border-[#1a1a1a] text-center space-y-3">
                <Radio className="mx-auto text-zinc-600" size={32} />
                <h3 className="font-bold text-white text-base">No Matches Found</h3>
                <p className="text-xs font-mono text-zinc-500 max-w-sm mx-auto">
                  No active events currently match '{timelineFilter}' / '{categoryFilter}'. Try switching filters or refreshing.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {events.map((ev) => (
                  <EventCard
                    key={ev.id}
                    event={ev}
                    onSelect={handleEventCardSelect}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* VIEW 2: TV Channels */}
        {activeTab === 'channels' && (
          <ChannelsView onPlayStream={handleLaunchPlayer} />
        )}

        {/* VIEW 3: Embed Sniffer */}
        {activeTab === 'sniffer' && (
          <EmbedSnifferView onPlayStream={handleLaunchPlayer} />
        )}
      </main>

      {/* Video Player Modal */}
      {playerModal.isOpen && (
        <VideoPlayer
          title={playerModal.title}
          subtitle={playerModal.subtitle}
          servers={playerModal.servers}
          onClose={() => setPlayerModal(prev => ({ ...prev, isOpen: false }))}
        />
      )}
    </div>
  );
}

export default App;
