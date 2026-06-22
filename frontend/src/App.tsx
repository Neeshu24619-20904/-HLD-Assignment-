import { useState, useCallback } from 'react';
import { Search, BarChart2, Sparkles, Command, CheckCircle2 } from 'lucide-react';
import { SearchBox } from './components/SearchBox';
import { TrendingList } from './components/TrendingList';
import { AnalyticsDashboard } from './components/AnalyticsDashboard';

function App() {
  const [activeTab, setActiveTab] = useState<'search' | 'admin'>('search');
  const [routingLogs, setRoutingLogs] = useState<string[]>([]);
  const [searchAlert, setSearchAlert] = useState<string | null>(null);
  const [trendingRefresh, setTrendingRefresh] = useState(0);

  // Callback to append routing information logs
  const handleLogRoute = useCallback((message: string) => {
    setRoutingLogs(prev => [...prev.slice(-99), message]); // Keep last 100 log lines
  }, []);

  const handleSearchExecuted = (query: string) => {
    // Show success banner
    setSearchAlert(query);
    
    // Force refresh trending tags listing
    setTrendingRefresh(prev => prev + 1);

    // Auto dismiss search alert after 3 seconds
    setTimeout(() => {
      setSearchAlert(null);
    }, 3000);
  };

  const handleClearLogs = () => {
    setRoutingLogs([]);
  };

  // Helper to click trending tag and submit search
  const handleExecuteTrendingSearch = (tagQuery: string) => {
    handleSearchExecuted(tagQuery);
  };

  return (
    <div className="flex flex-col min-h-screen bg-slate-950 text-slate-100 pb-16 selection:bg-brand-500 selection:text-white">
      {/* Navigation Header */}
      <header className="sticky top-0 z-40 bg-slate-950/80 backdrop-blur-md border-b border-slate-900/60">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 cursor-pointer" onClick={() => setActiveTab('search')}>
            <div className="p-1.5 rounded-xl bg-gradient-to-br from-brand-400 to-purple-600">
              <Command className="w-5 h-5 text-white" />
            </div>
            <span className="font-extrabold text-xl font-sans tracking-tight text-white">
              Nexus<span className="bg-gradient-to-r from-brand-400 to-purple-400 bg-clip-text text-transparent">Search</span>
            </span>
          </div>

          <nav className="flex items-center gap-1">
            <button
              onClick={() => setActiveTab('search')}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-xl transition-all ${
                activeTab === 'search'
                  ? 'bg-slate-900 text-white border border-slate-800'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Search className="w-4 h-4" />
              Search Engine
            </button>
            <button
              onClick={() => setActiveTab('admin')}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-xl transition-all ${
                activeTab === 'admin'
                  ? 'bg-slate-900 text-white border border-slate-800'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <BarChart2 className="w-4 h-4" />
              Dashboard
            </button>
          </nav>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-grow max-w-6xl w-full mx-auto px-6 pt-12 flex flex-col items-center">
        
        {/* Search Success Modal Overlay */}
        {searchAlert && (
          <div className="fixed top-20 right-6 z-50 flex items-center gap-3 px-5 py-3.5 bg-slate-900 border border-emerald-500/30 rounded-2xl shadow-2xl backdrop-blur-lg animate-in slide-in-from-right duration-300">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <div>
              <div className="text-xs text-slate-500 font-sans font-semibold uppercase">Search Submitted</div>
              <div className="text-sm font-bold text-slate-100 font-sans">
                "Searched" for <span className="text-brand-300">"{searchAlert}"</span>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'search' ? (
          /* Search Experience View */
          <div className="w-full flex flex-col items-center justify-center pt-10 pb-20 space-y-12">
            
            {/* Title / Hero */}
            <div className="text-center space-y-4 max-w-xl">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-brand-950/40 text-brand-300 border border-brand-800/30">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Consistent Hashing & Caching Simulation</span>
              </div>
              <h1 className="text-5xl font-black font-sans tracking-tight text-white md:text-6xl leading-tight">
                Search the Web
              </h1>
              <p className="text-slate-400 text-base md:text-lg">
                Type in the search bar below. Autosuggestions are generated instantly via a Trie and distributed across logical Redis cache nodes.
              </p>
            </div>

            {/* Core Search Component */}
            <SearchBox 
              onSearchExecuted={handleSearchExecuted} 
              onLogRoute={handleLogRoute} 
            />

            {/* Trending tags section */}
            <TrendingList 
              onTagClick={handleExecuteTrendingSearch} 
              refreshTrigger={trendingRefresh} 
            />

          </div>
        ) : (
          /* Dashboard Analytics View */
          <div className="w-full flex flex-col items-center pt-2 pb-16">
            <AnalyticsDashboard 
              routingLogs={routingLogs} 
              onClearLogs={handleClearLogs} 
            />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="w-full mt-auto border-t border-slate-900 py-6 text-center text-xs text-slate-600 font-sans">
        NexusSearch Search Autocomplete Typeahead System Assignment &copy; 2026. Made with React, FastAPI, Postgres, and Redis.
      </footer>
    </div>
  );
}


export default App;
