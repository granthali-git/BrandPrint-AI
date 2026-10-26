import React, { useState, useEffect, useCallback } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  ScanSearch,
  BookOpenCheck,
  Scale,
  ShieldAlert,
  Database,
  ExternalLink,
  Cpu,
  Sparkles,
  RefreshCw,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';

let rawBaseUrl = import.meta.env.VITE_API_BASE_URL || 'https://brandprint-ai-backend.onrender.com';
let baseUrl = rawBaseUrl.replace(/\/+$/, '');
if (typeof window !== 'undefined' && window.location.protocol === 'https:' && baseUrl.startsWith('http://') && !baseUrl.includes('localhost')) {
  baseUrl = baseUrl.replace('http://', 'https://');
}

export const Sidebar: React.FC = () => {
  const { backendConnected: appConnected, isCheckingHealth: appChecking, refreshHealth: appRefresh } = useApp();

  // Active Health Monitor Hook polling /health on baseUrl every 10 seconds
  const [isHealthy, setIsHealthy] = useState<boolean>(true);
  const [isChecking, setIsChecking] = useState<boolean>(false);

  const checkHealth = useCallback(async () => {
    setIsChecking(true);
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 6000);
      const res = await fetch(`${baseUrl}/health`, {
        method: 'GET',
        headers: { Accept: 'application/json' },
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      if (!res.ok) {
        setIsHealthy(false);
      } else {
        const data = await res.json();
        setIsHealthy(data?.status === 'healthy');
      }
    } catch {
      setIsHealthy(false);
    } finally {
      setIsChecking(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, [checkHealth]);

  const handleManualRefresh = async () => {
    await Promise.allSettled([checkHealth(), appRefresh()]);
  };

  const isConnected = isHealthy || appConnected;
  const checking = isChecking || appChecking;

  const navItems = [
    {
      name: 'Dashboard',
      path: '/',
      icon: LayoutDashboard,
      badge: 'Live',
    },
    {
      name: 'Review Studio',
      path: '/studio',
      icon: ScanSearch,
      badge: 'AI Core',
    },
    {
      name: 'Guidelines',
      path: '/guidelines',
      icon: BookOpenCheck,
      badge: null,
    },
    {
      name: 'Audit & Contradictions',
      path: '/audit',
      icon: Scale,
      badge: 'Audit',
    },
  ];

  return (
    <aside className="w-64 bg-brand-oceanDark border-r border-brand-ocean flex flex-col h-screen sticky top-0 select-none z-30 text-[#e8e2d5]">
      {/* BrandPrint AI Logo with Amber Circle Badge */}
      <div className="h-16 px-5 border-b border-brand-ocean/80 flex items-center gap-3">
        {/* Amber circle badge */}
        <div className="relative flex items-center justify-center w-9 h-9 rounded-full bg-brand-amber text-brand-oceanDark shadow-amber-glow font-extrabold text-sm shrink-0">
          <ShieldAlert className="w-5 h-5 text-brand-oceanDark stroke-[2.5]" />
        </div>

        <div className="flex flex-col">
          <div className="flex items-center gap-1.5">
            <span className="font-bold text-base tracking-tight text-white">
              BrandPrint
            </span>
            <span className="text-[10px] font-mono font-bold tracking-wider px-1.5 py-0.5 rounded-full bg-brand-amber/20 text-brand-amber border border-brand-amber/40">
              AI
            </span>
          </div>
          <span className="text-[10px] font-mono text-[#8fa8af] uppercase tracking-wider">
            Enterprise Safety
          </span>
        </div>
      </div>

      {/* Backend & AI Connection Live Indicator */}
      <div className="p-3 mx-3 my-3 rounded-xl bg-brand-ocean/50 border border-brand-oceanLight/40 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            {isConnected ? (
              <span
                className="relative flex h-2.5 w-2.5 shrink-0"
                title={`Backend connected at ${baseUrl}`}
                id="indicator-healthy-dot"
              >
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500 shadow-sm" />
              </span>
            ) : (
              <span
                className="relative flex h-2.5 w-2.5 shrink-0"
                title={`Reconnecting to backend at ${baseUrl}...`}
                id="indicator-reconnecting-dot"
              >
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-amber opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-brand-amber" />
              </span>
            )}
            <span className="text-white font-medium text-[11px] select-text">
              {isConnected ? 'Connected' : 'Reconnecting...'}
            </span>
          </div>

          <button
            type="button"
            onClick={handleManualRefresh}
            disabled={checking}
            title="Instant manual re-check connectivity"
            className="p-1 rounded-md text-[#8fa8af] hover:text-brand-amber hover:bg-brand-oceanLight/40 transition-colors disabled:opacity-50 cursor-pointer"
            id="btn-sidebar-refresh-health"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 ${checking ? 'animate-spin text-brand-amber' : ''}`}
            />
          </button>
        </div>

        <div className="flex items-center justify-between text-xs pt-1.5 border-t border-brand-oceanLight/30">
          <div className="flex items-center gap-1.5">
            <Database className="w-3 h-3 text-brand-amber" />
            <span className="text-[#c2d3d8] text-[11px] font-medium">Supabase & AI Active</span>
          </div>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
        </div>
      </div>

      {/* Navigation items */}
      <nav className="flex-1 px-3 space-y-1.5 overflow-y-auto">
        <div className="px-3 pb-1 pt-2 text-[10px] font-mono uppercase tracking-wider text-[#8fa8af]">
          Platform Navigation
        </div>
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              `group flex items-center justify-between px-3 py-2.5 text-xs font-medium transition-all duration-150 ${
                isActive
                  ? 'border-l-4 border-brand-amber bg-brand-oceanLight/70 text-white font-semibold rounded-r-xl rounded-l-sm shadow-sm backdrop-blur-sm'
                  : 'text-[#a3b8be] hover:text-white hover:bg-brand-ocean/40 rounded-xl'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <div className="flex items-center gap-2.5">
                  <item.icon
                    className={`w-4 h-4 transition-colors ${
                      isActive ? 'text-brand-amber' : 'text-[#8fa8af] group-hover:text-white'
                    }`}
                  />
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <span
                    className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${
                      isActive
                        ? 'bg-brand-amber/20 text-brand-amber border-brand-amber/40 font-bold'
                        : 'bg-brand-oceanDark/80 text-[#8fa8af] border-brand-oceanLight/30'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Engine Info Footer */}
      <div className="p-3 m-3 rounded-xl bg-brand-ocean/40 border border-brand-oceanLight/30 text-xs space-y-2 text-[#a3b8be]">
        <div className="flex items-center justify-between text-[11px]">
          <span className="flex items-center gap-1.5 text-white font-medium">
            <Cpu className="w-3.5 h-3.5 text-brand-amber" />
            <span>FAISS + Gemini</span>
          </span>
          <span className="text-[10px] font-mono text-brand-amber">Strict Grounding</span>
        </div>
        <a
          href={`${baseUrl}/docs`}
          target="_blank"
          rel="noreferrer"
          className="flex items-center justify-between pt-1.5 text-[10px] font-mono text-[#8fa8af] hover:text-brand-amber transition-colors border-t border-brand-oceanLight/20"
        >
          <span>FastAPI Documentation</span>
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>

      {/* Footer Version Info */}
      <div className="px-5 py-3 border-t border-brand-ocean/80 flex items-center justify-between text-[11px] font-mono text-[#8fa8af]">
        <span>v1.0-editorial</span>
        <span>AstraForge Core</span>
      </div>
    </aside>
  );
};

export default Sidebar;
