import React, { useState, useRef, useEffect } from 'react';
import {
  ChevronDown,
  Plus,
  ShieldCheck,
  Check,
  Building2,
  Sparkles,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';

export const TopBar: React.FC = () => {
  const { currentBrand, setCurrentBrand, availableBrands, currentUser, openNewReview } = useApp();
  const [isBrandDropdownOpen, setIsBrandDropdownOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const brandMenuRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // Close menus on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (brandMenuRef.current && !brandMenuRef.current.contains(e.target as Node)) {
        setIsBrandDropdownOpen(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setIsUserMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="h-16 bg-brand-cream border-b border-brand-sand px-6 flex items-center justify-between sticky top-0 z-20 text-brand-charcoal">
      {/* Left: Active Brand Selector */}
      <div className="flex items-center gap-4">
        <div className="relative" ref={brandMenuRef}>
          <button
            onClick={() => setIsBrandDropdownOpen(!isBrandDropdownOpen)}
            className="flex items-center gap-2.5 px-3.5 py-1.5 rounded-xl bg-white border border-brand-sand hover:border-brand-amber/60 text-brand-charcoal text-sm transition-all shadow-card-soft focus:outline-none focus:ring-1 focus:ring-brand-amber"
            title="Switch Active Brand"
          >
            <div className="w-7 h-7 rounded-lg bg-brand-oceanLight/10 border border-brand-ocean/20 flex items-center justify-center">
              <Building2 className="w-4 h-4 text-brand-ocean" />
            </div>
            <div className="flex flex-col text-left">
              <span className="text-xs font-bold leading-tight text-brand-charcoal">
                {currentBrand.name}
              </span>
              <span className="text-[10px] font-mono text-brand-charcoalMuted">
                Brand ID: #{currentBrand.id} • {currentBrand.code}
              </span>
            </div>
            <ChevronDown
              className={`w-3.5 h-3.5 text-brand-charcoalMuted transition-transform duration-200 ${
                isBrandDropdownOpen ? 'rotate-180 text-brand-amber' : ''
              }`}
            />
          </button>

          {/* Brand Dropdown Menu */}
          {isBrandDropdownOpen && (
            <div className="absolute left-0 mt-2 w-72 rounded-2xl bg-white border border-brand-sand shadow-card-elevated py-2 z-50 animate-in fade-in zoom-in-95 duration-150">
              <div className="px-3.5 py-1.5 border-b border-brand-sand/60">
                <span className="text-[10px] font-mono uppercase tracking-wider text-brand-charcoalMuted font-bold">
                  Active Enterprise Brand
                </span>
              </div>
              <div className="py-1">
                {availableBrands.map((brand) => {
                  const isSelected = brand.id === currentBrand.id;
                  return (
                    <button
                      key={brand.id}
                      onClick={() => {
                        setCurrentBrand(brand);
                        setIsBrandDropdownOpen(false);
                      }}
                      className={`w-full flex items-center justify-between px-3.5 py-2 text-left text-xs transition-colors ${
                        isSelected
                          ? 'bg-brand-oceanLight/10 text-brand-ocean font-semibold'
                          : 'text-brand-charcoal hover:bg-brand-cream'
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <div
                          className={`w-6 h-6 rounded-lg flex items-center justify-center font-mono font-bold text-[10px] border ${
                            isSelected
                              ? 'bg-brand-amber text-brand-oceanDark border-brand-amber font-extrabold'
                              : 'bg-brand-cream border-brand-sand text-brand-charcoalMuted'
                          }`}
                        >
                          {brand.code.slice(0, 2)}
                        </div>
                        <div>
                          <div className="font-semibold text-brand-charcoal">{brand.name}</div>
                          <div className="text-[10px] text-brand-charcoalMuted">{brand.industry}</div>
                        </div>
                      </div>
                      {isSelected && <Check className="w-4 h-4 text-brand-amber stroke-[2.5]" />}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Policy Enforcement Tag */}
        <div className="hidden md:flex items-center gap-1.5 px-3 py-1 rounded-xl bg-white border border-brand-sand text-[11px] font-mono text-brand-charcoalMuted shadow-card-soft">
          <ShieldCheck className="w-3.5 h-3.5 text-brand-ocean" />
          <span>Governance Mode:</span>
          <span className="text-brand-ocean font-bold">Strict Active</span>
        </div>
      </div>

      {/* Right: Primary Warm Amber CTA Button & User Profile Chip */}
      <div className="flex items-center gap-4">
        {/* Primary CTA Button: Warm Amber */}
        <button
          onClick={openNewReview}
          className="bg-brand-ocean hover:bg-brand-oceanDark text-white font-medium px-3.5 py-2 rounded-xl shadow-sm transition-all duration-150 flex items-center gap-1.5 active:scale-95 text-xs font-semibold border border-brand-oceanLight/30"
          id="btn-new-review-header"
        >
          <Plus className="w-3.5 h-3.5 text-brand-amber stroke-[2.5]" />
          <span>New Review</span>
        </button>

        {/* Divider */}
        <div className="h-6 w-[1px] bg-brand-sand" />

        {/* User profile chip */}
        <div className="relative" ref={userMenuRef}>
          <button
            onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
            className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-white border border-brand-sand hover:border-brand-amber/50 transition-colors shadow-card-soft focus:outline-none focus:ring-1 focus:ring-brand-amber"
            title="User Profile & Settings"
          >
            {/* Avatar Initials with Warm Amber background */}
            <div className="flex items-center justify-center w-7 h-7 rounded-full bg-brand-ocean text-brand-amber font-mono font-bold text-xs shrink-0 shadow-sm">
              BP
            </div>

            <div className="hidden sm:flex flex-col text-left">
              <span className="text-xs font-semibold text-brand-charcoal leading-tight">
                {currentUser.email}
              </span>
              <span className="text-[10px] font-mono text-brand-amber font-semibold leading-tight">
                {currentUser.role}
              </span>
            </div>

            <ChevronDown className="w-3 h-3 text-brand-charcoalMuted" />
          </button>

          {/* User Menu Dropdown */}
          {isUserMenuOpen && (
            <div className="absolute right-0 mt-2 w-64 rounded-2xl bg-white border border-brand-sand shadow-card-elevated py-2.5 z-50 animate-in fade-in zoom-in-95 duration-150">
              <div className="px-4 py-2 border-b border-brand-sand">
                <p className="text-xs font-bold text-brand-charcoal">{currentUser.name}</p>
                <p className="text-[11px] font-mono text-brand-charcoalMuted">{currentUser.email}</p>
                <span className="inline-block mt-1 px-2 py-0.5 rounded text-[10px] font-mono bg-brand-amberLight text-brand-amberHover font-bold border border-brand-amber/30">
                  Role: {currentUser.role}
                </span>
              </div>
              <div className="py-1 text-xs">
                <div className="px-4 py-1.5 text-brand-charcoalMuted flex items-center justify-between">
                  <span>Engine:</span>
                  <span className="font-mono text-brand-ocean font-bold text-[11px]">FAISS + Gemini</span>
                </div>
                <div className="px-4 py-1.5 text-brand-charcoalMuted flex items-center justify-between">
                  <span>Grounding:</span>
                  <span className="font-mono text-emerald-600 font-bold text-[11px]">Active</span>
                </div>
              </div>
              <div className="pt-1.5 border-t border-brand-sand px-3">
                <div className="px-2 py-1 text-[11px] text-brand-charcoalMuted text-center">
                  Signed in as <span className="text-brand-charcoal font-semibold">Admin</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default TopBar;
