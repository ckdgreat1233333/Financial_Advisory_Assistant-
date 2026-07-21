/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from "react";
import { ShieldCheck, LogIn, UserPlus, FileText, ArrowRight, Building, Key, Smartphone } from "lucide-react";
import { motion } from "motion/react";

interface AuthPageProps {
  onLogin: (role: "customer" | "officer", email: string, name: string) => void;
}

export default function AuthPage({ onLogin }: AuthPageProps) {
  const [isLogin, setIsLogin] = useState(true);
  const [portalType, setPortalType] = useState<"customer" | "officer">("customer");
  
  // Form fields
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [error, setError] = useState("");

  const handleDemoLogin = (role: "customer" | "officer") => {
    if (role === "customer") {
      onLogin("customer", "david.miller@gmail.com", "David Miller");
    } else {
      onLogin("officer", "sarah.jenkins@lendintel.com", "Officer Sarah J.");
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError("Please fill in all required fields.");
      return;
    }
    if (!isLogin && !fullName) {
      setError("Please enter your full name.");
      return;
    }
    if (!isLogin && !termsAccepted) {
      setError("You must accept the terms & conditions.");
      return;
    }

    setError("");
    // Use submitted fields or fallbacks
    const name = fullName || (portalType === "officer" ? "Officer Sarah J." : "David Miller");
    onLogin(portalType, email, name);
  };

  return (
    <div id="auth-page-container" className="min-h-screen bg-slate-900 text-slate-100 flex flex-col md:flex-row font-sans">
      {/* LEFT SIDE - BRANDING */}
      <div id="auth-left-banner" className="md:w-1/2 bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 p-8 md:p-16 flex flex-col justify-between relative overflow-hidden border-r border-slate-800">
        <div className="absolute top-0 left-0 w-full h-full opacity-10 pointer-events-none">
          {/* Subtle grid accent */}
          <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>
          <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full bg-indigo-500 blur-3xl"></div>
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 rounded-full bg-emerald-500 blur-3xl"></div>
        </div>

        {/* Brand */}
        <div id="auth-brand-header" className="flex items-center gap-3 relative z-10">
          <div className="p-2.5 bg-emerald-600 rounded-xl text-white shadow-lg shadow-emerald-900/30">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold font-display tracking-tight text-white flex items-center gap-1.5">
              LendSmart <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 font-mono font-medium">AI</span>
            </h1>
            <p className="text-xs text-slate-400">Intelligent Lending Lifecycle</p>
          </div>
        </div>

        {/* Creative Text & Callouts */}
        <div id="auth-left-text" className="my-12 md:my-0 relative z-10 max-w-md">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-500/15 text-indigo-300 text-xs font-medium mb-6 border border-indigo-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse"></span>
            Enterprise Grade AI Underwriting
          </span>
          <h2 className="text-3xl md:text-4xl font-semibold font-display tracking-tight text-white leading-tight">
            Secure Intelligence for Smarter Lending.
          </h2>
          <p className="text-slate-400 mt-4 leading-relaxed">
            Harness real-time OCR extraction, automated compliance validation, and multi-agent consensus risk modeling to accelerate approvals.
          </p>

          <div className="mt-8 space-y-4">
            <div className="flex items-start gap-3 bg-slate-950/40 border border-slate-800/80 p-4 rounded-xl">
              <div className="p-2 bg-indigo-950 text-indigo-400 rounded-lg shrink-0">
                <FileText className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-sm font-medium text-slate-200">Zero-Tamper Document Check</h4>
                <p className="text-xs text-slate-400 mt-0.5">Pixel analysis, metadata validation, and cross-document verification algorithms.</p>
              </div>
            </div>

            <div className="flex items-start gap-3 bg-slate-950/40 border border-slate-800/80 p-4 rounded-xl">
              <div className="p-2 bg-emerald-950 text-emerald-400 rounded-lg shrink-0">
                <Building className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-sm font-medium text-slate-200">Consensus Policy Engine</h4>
                <p className="text-xs text-slate-400 mt-0.5">Decentralized AI evaluation grounded by your precise credit policies and parameters.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Demo Fast Login */}
        <div id="auth-left-footer" className="relative z-10 border-t border-slate-800 pt-6">
          <p className="text-xs text-slate-500 font-medium uppercase tracking-wider mb-3">Quick Demo Authentication</p>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => handleDemoLogin("customer")}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 rounded-lg text-xs font-medium text-slate-200 transition-colors"
            >
              <span>Customer Portal Demo</span>
              <ArrowRight className="h-3 w-3 text-emerald-400" />
            </button>
            <button
              onClick={() => handleDemoLogin("officer")}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-950/40 hover:bg-indigo-900/30 border border-indigo-900/40 rounded-lg text-xs font-medium text-indigo-300 transition-colors"
            >
              <span>Officer Portal Demo</span>
              <ArrowRight className="h-3 w-3 text-indigo-400" />
            </button>
          </div>
        </div>
      </div>

      {/* RIGHT SIDE - FORM */}
      <div id="auth-right-form" className="md:w-1/2 bg-slate-950 flex flex-col justify-center items-center p-8 md:p-16 relative">
        <div className="w-full max-w-md">
          {/* Form Header */}
          <div className="text-center md:text-left mb-8">
            <h3 className="text-2xl font-semibold font-display tracking-tight text-white">
              {isLogin ? "Welcome Back" : "Create your account"}
            </h3>
            <p className="text-sm text-slate-400 mt-1.5">
              {isLogin ? "Sign in to manage applications and credit analytics." : "Register to request credit facilities instantly."}
            </p>
          </div>

          {/* Customer / Staff Tab Selection */}
          <div className="grid grid-cols-2 p-1 bg-slate-900 rounded-xl mb-6 border border-slate-800/80">
            <button
              type="button"
              onClick={() => setPortalType("customer")}
              className={`py-2 text-xs font-medium rounded-lg transition-all ${
                portalType === "customer"
                  ? "bg-slate-800 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Customer Portal
            </button>
            <button
              type="button"
              onClick={() => setPortalType("officer")}
              className={`py-2 text-xs font-medium rounded-lg transition-all ${
                portalType === "officer"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Staff Portal
            </button>
          </div>

          {/* Form container */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs rounded-lg">
                {error}
              </div>
            )}

            {!isLogin && (
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">Full Name</label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-500">
                    <UserPlus className="h-4 w-4" />
                  </span>
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Sarah Jenkins"
                    className="w-full bg-slate-900 border border-slate-800 hover:border-slate-700 focus:border-emerald-500 rounded-xl py-2.5 pl-10 pr-4 text-sm text-white placeholder-slate-500 focus:outline-none transition-colors"
                  />
                </div>
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300">Email Address</label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-500">
                  <LogIn className="h-4 w-4" />
                </span>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={portalType === "officer" ? "sarah.jenkins@lendsmart.com" : "david.miller@gmail.com"}
                  className="w-full bg-slate-900 border border-slate-800 hover:border-slate-700 focus:border-emerald-500 rounded-xl py-2.5 pl-10 pr-4 text-sm text-white placeholder-slate-500 focus:outline-none transition-colors"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <label className="text-xs font-medium text-slate-300">Password</label>
                {isLogin && (
                  <a href="#" className="text-xs text-indigo-400 hover:text-indigo-300">Forgot?</a>
                )}
              </div>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-500">
                  <Key className="h-4 w-4" />
                </span>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full bg-slate-900 border border-slate-800 hover:border-slate-700 focus:border-emerald-500 rounded-xl py-2.5 pl-10 pr-4 text-sm text-white placeholder-slate-500 focus:outline-none transition-colors"
                />
              </div>
            </div>

            {!isLogin && (
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">Mobile Phone (For 2FA)</label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-500">
                    <Smartphone className="h-4 w-4" />
                  </span>
                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+1 (555) 012-3456"
                    className="w-full bg-slate-900 border border-slate-800 hover:border-slate-700 focus:border-emerald-500 rounded-xl py-2.5 pl-10 pr-4 text-sm text-white placeholder-slate-500 focus:outline-none transition-colors"
                  />
                </div>
              </div>
            )}

            {/* Checkbox settings */}
            {isLogin ? (
              <div className="flex items-center">
                <input
                  id="remember-me"
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="h-4 w-4 rounded bg-slate-900 border-slate-800 text-emerald-600 focus:ring-emerald-500/20"
                />
                <label htmlFor="remember-me" className="ml-2 text-xs text-slate-400 select-none">
                  Remember this device for 30 days
                </label>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="p-3 bg-indigo-505/10 bg-slate-900 border border-slate-800/80 rounded-lg text-[11px] text-slate-400">
                  <span className="font-semibold text-slate-300 block mb-0.5">Identity Verification Required</span>
                  Federal regulations require us to collect and verify identification credentials before active facility creation.
                </div>
                <div className="flex items-start">
                  <input
                    id="terms-accept"
                    type="checkbox"
                    required
                    checked={termsAccepted}
                    onChange={(e) => setTermsAccepted(e.target.checked)}
                    className="h-4 w-4 mt-0.5 rounded bg-slate-900 border-slate-800 text-emerald-600 focus:ring-emerald-500/20"
                  />
                  <label htmlFor="terms-accept" className="ml-2 text-xs text-slate-400 select-none">
                    I agree to the <a href="#" className="text-emerald-400 hover:underline">Terms of Service</a> and authorize biometric identity cross-verification.
                  </label>
                </div>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              className={`w-full py-2.5 rounded-xl font-medium text-sm text-white flex items-center justify-center gap-2 cursor-pointer shadow-lg transition-all ${
                portalType === "officer"
                  ? "bg-indigo-600 hover:bg-indigo-500 shadow-indigo-950/40 hover:shadow-indigo-600/10"
                  : "bg-emerald-600 hover:bg-emerald-500 shadow-emerald-950/40 hover:shadow-emerald-600/10"
              }`}
            >
              {isLogin ? "Sign In to Portal" : "Create Account & Register"}
              <ArrowRight className="h-4 w-4" />
            </button>
          </form>

          {/* Toggle between Login and Register */}
          <div className="text-center mt-6 pt-6 border-t border-slate-900 text-xs">
            <span className="text-slate-400">
              {isLogin ? "New to LendSmart?" : "Already have an account?"}
            </span>{" "}
            <button
              type="button"
              onClick={() => {
                setIsLogin(!isLogin);
                setError("");
              }}
              className="font-semibold text-emerald-400 hover:text-emerald-300 transition-colors cursor-pointer"
            >
              {isLogin ? "Create an account" : "Sign in here"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
