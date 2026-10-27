import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  ShieldAlert,
  ShieldCheck,
  Zap,
  Layers,
  Sparkles,
  Lock,
  Mail,
  User as UserIcon,
  Building,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Eye,
  EyeOff,
  ArrowRight,
  ArrowLeft,
  Check,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

type AuthMode = 'signin' | 'signup' | 'forgot_password';

export const AuthPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, register, forgotPassword, loginAsGuestDemo } = useAuth();

  // Mode state: 'signin' | 'signup' | 'forgot_password'
  const [mode, setMode] = useState<AuthMode>('signin');

  // Form Fields
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [company, setCompany] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [showPassword, setShowPassword] = useState(false);

  // Status & Feedback
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Where to navigate after successful auth
  const from = (location.state as any)?.from?.pathname || '/';

  const resetFormState = (newMode: AuthMode) => {
    setMode(newMode);
    setErrorMessage(null);
    setSuccessMessage(null);
  };

  const validateEmail = (val: string) => {
    return /\S+@\S+\.\S+/.test(val);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    // Validation
    if (!validateEmail(email)) {
      setErrorMessage('Please enter a valid work email address (e.g. name@company.com).');
      return;
    }

    if (mode !== 'forgot_password' && password.length < 6) {
      setErrorMessage('Password must be at least 6 characters in length.');
      return;
    }

    if (mode === 'signup' && confirmPassword && password !== confirmPassword) {
      setErrorMessage('Passwords do not match. Please verify your password entry.');
      return;
    }

    setIsSubmitting(true);

    try {
      if (mode === 'signin') {
        await login(email, password, rememberMe);
        navigate(from, { replace: true });
      } else if (mode === 'signup') {
        await register({
          email,
          password,
          full_name: fullName.trim() || undefined,
          company: company.trim() || undefined,
          role: 'Creator',
        });
        navigate(from, { replace: true });
      } else if (mode === 'forgot_password') {
        const res = await forgotPassword(email);
        setSuccessMessage(res.message || 'Password reset instructions sent to your email address.');
      }
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Authentication failed. Please verify credentials.';
      setErrorMessage(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDemoAccess = () => {
    loginAsGuestDemo();
    navigate(from, { replace: true });
  };

  return (
    <div className="min-h-screen w-screen flex flex-col lg:flex-row bg-[#FBF9F4] font-sans text-[#072730] selection:bg-[#F4A321]/30 select-text overflow-x-hidden">
      {/* ========================================================= */}
      {/* LEFT PANE: Desktop Showcase & Enterprise Brand Authority  */}
      {/* ========================================================= */}
      <div className="lg:w-1/2 bg-[#0B3C49] relative p-8 lg:p-14 flex flex-col justify-between overflow-hidden text-white border-b lg:border-b-0 lg:border-r border-[#144f60]/40 shadow-2xl">
        {/* Subtle Background Glows & Accent Grids */}
        <div className="absolute -top-32 -left-32 w-96 h-96 bg-[#F4A321]/15 rounded-full blur-3xl pointer-events-none animate-pulse duration-1000" />
        <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-[#144f60]/30 rounded-full blur-3xl pointer-events-none" />

        {/* Brand Header */}
        <div className="relative z-10">
          <div className="flex items-center gap-3">
            <div className="relative flex items-center justify-center w-11 h-11 rounded-2xl bg-[#F4A321] text-[#072730] shadow-[0_0_25px_rgba(244,163,33,0.4)] font-extrabold shrink-0 transform transition-transform hover:scale-105">
              <ShieldAlert className="w-6 h-6 text-[#072730] stroke-[2.5]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-2xl tracking-tight text-white font-sans">
                  BrandPrint
                </span>
                <span className="text-xs font-mono font-bold tracking-wider px-2 py-0.5 rounded-full bg-[#F4A321]/20 text-[#F4A321] border border-[#F4A321]/40">
                  AI
                </span>
              </div>
              <p className="text-xs font-mono text-[#8fa8af] uppercase tracking-wider">
                Enterprise Content Governance
              </p>
            </div>
          </div>
        </div>

        {/* Center Tagline & Feature Showcase */}
        <div className="my-12 lg:my-auto relative z-10 max-w-xl">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#144f60]/40 border border-[#F4A321]/30 text-xs font-mono text-[#F4A321] mb-6 shadow-sm backdrop-blur-sm">
            <Sparkles className="w-3.5 h-3.5 text-[#F4A321]" />
            <span>Semantic Brand Safety & Verification Architecture</span>
          </div>

          <h1 className="text-3xl lg:text-5xl font-extrabold tracking-tight leading-tight lg:leading-tight text-white">
            Enterprise Content Governance & Semantic Brand Safety.
          </h1>

          <p className="mt-4 text-sm lg:text-base text-[#c7d5d8] leading-relaxed">
            Autonomous multi-modal parsing, deterministic guideline cross-checking, and real-time contradiction mitigation for high-stakes enterprise compliance.
          </p>

          {/* Feature Bullet Points */}
          <div className="mt-8 space-y-4">
            <div className="flex items-start gap-3.5 p-3.5 rounded-2xl bg-[#072730]/60 border border-[#144f60]/50 backdrop-blur-md shadow-sm hover:border-[#F4A321]/40 transition-colors">
              <div className="w-9 h-9 rounded-xl bg-[#F4A321]/15 border border-[#F4A321]/30 flex items-center justify-center shrink-0">
                <Zap className="w-5 h-5 text-[#F4A321]" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white flex items-center gap-2">
                  Multi-Modal Document & PPTX Parsing
                </h4>
                <p className="text-xs text-[#8fa8af] mt-0.5">
                  High-fidelity PDF, DOCX, and slide-deck extraction with structure, table, and metadata isolation.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3.5 p-3.5 rounded-2xl bg-[#072730]/60 border border-[#144f60]/50 backdrop-blur-md shadow-sm hover:border-[#F4A321]/40 transition-colors">
              <div className="w-9 h-9 rounded-xl bg-[#F4A321]/15 border border-[#F4A321]/30 flex items-center justify-center shrink-0">
                <ShieldCheck className="w-5 h-5 text-[#F4A321]" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white flex items-center gap-2">
                  Autonomous Contradiction Detection
                </h4>
                <p className="text-xs text-[#8fa8af] mt-0.5">
                  Dual-layer deterministic logic and vector embeddings flag semantic guideline paradoxes before publication.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3.5 p-3.5 rounded-2xl bg-[#072730]/60 border border-[#144f60]/50 backdrop-blur-md shadow-sm hover:border-[#F4A321]/40 transition-colors">
              <div className="w-9 h-9 rounded-xl bg-[#F4A321]/15 border border-[#F4A321]/30 flex items-center justify-center shrink-0">
                <Layers className="w-5 h-5 text-[#F4A321]" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white flex items-center gap-2">
                  Voice, Tone & A11y Verification Sandbox
                </h4>
                <p className="text-xs text-[#8fa8af] mt-0.5">
                  Simulated sandbox diffs, readability indexing, and WCAG accessibility guardrails in real-time.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Authority Pill */}
        <div className="relative z-10 pt-6 border-t border-[#144f60]/50 flex items-center justify-between text-xs text-[#8fa8af] font-mono">
          <span>Enterprise Grade • SOC2 Type II Certified</span>
          <span className="text-[#F4A321] font-semibold">Strict Grounding</span>
        </div>
      </div>

      {/* ========================================================= */}
      {/* RIGHT PANE: Interactive Auth Card & Form States          */}
      {/* ========================================================= */}
      <div className="lg:w-1/2 flex items-center justify-center p-6 sm:p-12 lg:p-16 bg-[#FBF9F4]">
        <div className="w-full max-w-md bg-white rounded-3xl border border-[#e8e2d5] shadow-[0_10px_30px_rgba(11,60,73,0.06)] p-8 sm:p-10 transition-all duration-300">
          {/* Top Mode Header */}
          <div className="mb-6 text-left">
            {mode === 'forgot_password' ? (
              <div>
                <button
                  type="button"
                  onClick={() => resetFormState('signin')}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#0B3C49] hover:text-[#F4A321] transition-colors mb-3 group"
                >
                  <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" />
                  <span>Back to Sign In</span>
                </button>
                <h2 className="text-2xl font-bold tracking-tight text-[#072730]">
                  Reset your password
                </h2>
                <p className="text-xs text-[#5d7177] mt-1.5 leading-relaxed">
                  Enter your registered work email and we'll send a recovery link.
                </p>
              </div>
            ) : mode === 'signup' ? (
              <div>
                <div className="inline-block px-2.5 py-0.5 rounded-full bg-[#fef3e2] text-[#de9018] border border-[#f4a321]/30 text-[11px] font-mono font-bold mb-2">
                  New Workspace
                </div>
                <h2 className="text-2xl font-bold tracking-tight text-[#072730]">
                  Create Enterprise Account
                </h2>
                <p className="text-xs text-[#5d7177] mt-1.5">
                  Deploy BrandPrint AI governance across your organization.
                </p>
              </div>
            ) : (
              <div>
                <div className="inline-block px-2.5 py-0.5 rounded-full bg-[#144f60]/10 text-[#0B3C49] border border-[#0B3C49]/20 text-[11px] font-mono font-bold mb-2">
                  Enterprise Access
                </div>
                <h2 className="text-2xl font-bold tracking-tight text-[#072730]">
                  Sign In to Workspace
                </h2>
                <p className="text-xs text-[#5d7177] mt-1.5">
                  Enter your enterprise credentials to access brand governance portals.
                </p>
              </div>
            )}
          </div>

          {/* Feedback Banners */}
          {errorMessage && (
            <div className="mb-5 p-3.5 rounded-2xl bg-red-50 border border-red-200 text-xs text-red-800 flex items-start gap-2.5 animate-in fade-in duration-150">
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
              <div className="leading-relaxed font-medium">{errorMessage}</div>
            </div>
          )}

          {successMessage && (
            <div className="mb-5 p-3.5 rounded-2xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-start gap-2.5 animate-in fade-in duration-150">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <div className="leading-relaxed font-medium">{successMessage}</div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Full Name & Company (Sign Up Mode Only) */}
            {mode === 'signup' && (
              <>
                <div>
                  <label className="block text-xs font-semibold text-[#072730] mb-1.5">
                    Full Name <span className="text-[#F4A321]">*</span>
                  </label>
                  <div className="relative">
                    <UserIcon className="w-4 h-4 text-[#8fa8af] absolute left-3.5 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      required
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="e.g. Jane Doe"
                      className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-[#e8e2d5] bg-[#FBF9F4]/50 focus:bg-white text-xs text-[#072730] placeholder-[#8fa8af] focus:outline-none focus:ring-2 focus:ring-[#F4A321] focus:border-transparent transition-all"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[#072730] mb-1.5">
                    Company / Organization
                  </label>
                  <div className="relative">
                    <Building className="w-4 h-4 text-[#8fa8af] absolute left-3.5 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      value={company}
                      onChange={(e) => setCompany(e.target.value)}
                      placeholder="e.g. Acme Corporation"
                      className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-[#e8e2d5] bg-[#FBF9F4]/50 focus:bg-white text-xs text-[#072730] placeholder-[#8fa8af] focus:outline-none focus:ring-2 focus:ring-[#F4A321] focus:border-transparent transition-all"
                    />
                  </div>
                </div>
              </>
            )}

            {/* Work Email Field */}
            <div>
              <label className="block text-xs font-semibold text-[#072730] mb-1.5">
                Work Email <span className="text-[#F4A321]">*</span>
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-[#8fa8af] absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-[#e8e2d5] bg-[#FBF9F4]/50 focus:bg-white text-xs text-[#072730] placeholder-[#8fa8af] focus:outline-none focus:ring-2 focus:ring-[#F4A321] focus:border-transparent transition-all"
                />
              </div>
            </div>

            {/* Password Field (Sign In & Sign Up Modes) */}
            {mode !== 'forgot_password' && (
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-semibold text-[#072730]">
                    Password <span className="text-[#F4A321]">*</span>
                  </label>
                  {mode === 'signin' && (
                    <button
                      type="button"
                      onClick={() => resetFormState('forgot_password')}
                      className="text-[11px] font-semibold text-[#0B3C49] hover:text-[#F4A321] transition-colors"
                    >
                      Forgot password?
                    </button>
                  )}
                </div>
                <div className="relative">
                  <Lock className="w-4 h-4 text-[#8fa8af] absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-10 pr-10 py-2.5 rounded-xl border border-[#e8e2d5] bg-[#FBF9F4]/50 focus:bg-white text-xs text-[#072730] placeholder-[#8fa8af] focus:outline-none focus:ring-2 focus:ring-[#F4A321] focus:border-transparent transition-all font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#8fa8af] hover:text-[#072730] transition-colors"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            )}

            {/* Password Confirmation (Sign Up Mode Only) */}
            {mode === 'signup' && (
              <div>
                <label className="block text-xs font-semibold text-[#072730] mb-1.5">
                  Confirm Password <span className="text-[#F4A321]">*</span>
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-[#8fa8af] absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-[#e8e2d5] bg-[#FBF9F4]/50 focus:bg-white text-xs text-[#072730] placeholder-[#8fa8af] focus:outline-none focus:ring-2 focus:ring-[#F4A321] focus:border-transparent transition-all font-mono"
                  />
                </div>
              </div>
            )}

            {/* Remember Me Checkbox (Sign In Mode) */}
            {mode === 'signin' && (
              <div className="flex items-center justify-between pt-1">
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-4 h-4 rounded text-[#F4A321] focus:ring-[#F4A321] border-[#e8e2d5] cursor-pointer"
                  />
                  <span className="text-xs text-[#5d7177] font-medium">Remember me for 30 days</span>
                </label>
              </div>
            )}

            {/* Primary Submit Button (Warm Amber #F4A321) */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-2 py-3 px-4 rounded-xl bg-[#F4A321] hover:bg-[#de9018] active:scale-[0.99] text-[#072730] font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 shadow-[0_4px_14px_rgba(244,163,33,0.35)] transition-all disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-[#072730]" />
                  <span>Processing...</span>
                </>
              ) : mode === 'signin' ? (
                <>
                  <span>Sign In to Workspace</span>
                  <ArrowRight className="w-4 h-4 stroke-[2.5]" />
                </>
              ) : mode === 'signup' ? (
                <>
                  <span>Create Enterprise Account</span>
                  <ArrowRight className="w-4 h-4 stroke-[2.5]" />
                </>
              ) : (
                <>
                  <span>Send Reset Link</span>
                  <ArrowRight className="w-4 h-4 stroke-[2.5]" />
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Access Bypass Button */}
          {mode === 'signin' && (
            <div className="mt-4 pt-4 border-t border-[#e8e2d5]">
              <button
                type="button"
                onClick={handleDemoAccess}
                className="w-full py-2.5 px-4 rounded-xl bg-[#0B3C49]/5 hover:bg-[#0B3C49]/10 border border-[#0B3C49]/20 text-[#0B3C49] font-semibold text-xs flex items-center justify-center gap-2 transition-colors cursor-pointer"
              >
                <Sparkles className="w-3.5 h-3.5 text-[#F4A321]" />
                <span>Instant Demo Access (tester@brandprint.ai)</span>
              </button>
            </div>
          )}

          {/* Footer State Toggle Links */}
          <div className="mt-6 text-center text-xs text-[#5d7177]">
            {mode === 'signin' ? (
              <p>
                Don't have an account?{' '}
                <button
                  type="button"
                  onClick={() => resetFormState('signup')}
                  className="font-bold text-[#0B3C49] hover:text-[#F4A321] transition-colors ml-1"
                >
                  Sign up
                </button>
              </p>
            ) : mode === 'signup' ? (
              <p>
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => resetFormState('signin')}
                  className="font-bold text-[#0B3C49] hover:text-[#F4A321] transition-colors ml-1"
                >
                  Sign in
                </button>
              </p>
            ) : (
              <p>
                Remembered your password?{' '}
                <button
                  type="button"
                  onClick={() => resetFormState('signin')}
                  className="font-bold text-[#0B3C49] hover:text-[#F4A321] transition-colors ml-1"
                >
                  Back to Sign in
                </button>
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuthPage;

