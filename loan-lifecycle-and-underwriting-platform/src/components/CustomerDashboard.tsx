/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from "react";
import {
  FileText,
  Clock,
  CheckCircle,
  AlertTriangle,
  ArrowRight,
  TrendingUp,
  HelpCircle,
  Search,
  ChevronDown,
  ChevronUp,
  User,
  Settings as SettingsIcon,
  Bell,
  Lock,
  UploadCloud,
  X,
  CreditCard,
  Building,
  DollarSign,
  Briefcase
} from "lucide-react";
import { Application, LoanType } from "../types";

interface CustomerDashboardProps {
  applications: Application[];
  onApplyLoan: (appData: Partial<Application>) => void;
  onUpdateProfile: (name: string, email: string, phone: string) => void;
  currentUser: { name: string; email: string; phone?: string };
  onNavigateToChat: () => void;
}

export default function CustomerDashboard({
  applications,
  onApplyLoan,
  onUpdateProfile,
  currentUser,
  onNavigateToChat
}: CustomerDashboardProps) {
  const [activeSubTab, setActiveSubTab] = useState<"overview" | "apply" | "help" | "settings">("overview");

  // Multi-step Apply Form State
  const [applyStep, setApplyStep] = useState(1);
  const [selectedLoanType, setSelectedLoanType] = useState<LoanType>("home");
  const [loanAmount, setLoanAmount] = useState<number>(350000);
  const [loanTerm, setLoanTerm] = useState<number>(360); // in months
  const [purpose, setPurpose] = useState("");
  const [uploadedFiles, setUploadedFiles] = useState<{ name: string; type: string; size: string }[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  // FAQ Accordion State
  const [expandedFaqIndex, setExpandedFaqIndex] = useState<number | null>(null);
  const [faqSearch, setFaqSearch] = useState("");
  const [faqData, setFaqData] = useState<{question: string; answer: string}[]>([]);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/faq")
      .then(r => r.ok ? r.json() : { faqs: [] })
      .then(d => setFaqData(d.faqs || []))
      .catch(() => setFaqData([]));
  }, []);

  // Settings State
  const [profileName, setProfileName] = useState(currentUser.name);
  const [profileEmail, setProfileEmail] = useState(currentUser.email);
  const [profilePhone, setProfilePhone] = useState(currentUser.phone || "+1 (555) 431-8844");
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Filter applications for current user
  const customerApps = applications; // For demo, we display all default applications as the logged-in portfolio

  // Metrics
  const activeCount = customerApps.filter(a => a.status === "under_review" || a.status === "pending_docs").length;
  const approvedCount = customerApps.filter(a => a.status === "approved").length;
  const totalApprovedCredit = customerApps
    .filter(a => a.status === "approved")
    .reduce((sum, a) => sum + a.amount, 0);

  // Dynamic Payment Calculation Formula (Interest assumed at nominal 6.5% APR)
  const monthlyRate = 0.065 / 12;
  const paymentFactor = Math.pow(1 + monthlyRate, loanTerm);
  const estimatedMonthlyPayment = loanAmount * ((monthlyRate * paymentFactor) / (paymentFactor - 1));

  // Handle mock file uploads
  const handleFileUpload = (files: FileList | null) => {
    if (!files) return;
    const newFiles = Array.from(files).map(f => ({
      name: f.name,
      type: f.type || "Document",
      size: (f.size / (1024 * 1024)).toFixed(2) + " MB"
    }));
    setUploadedFiles(prev => [...prev, ...newFiles]);
  };

  const handleApplySubmit = () => {
    // Generate new application
    const newApp: Partial<Application> = {
      applicantName: currentUser.name,
      applicantEmail: currentUser.email,
      applicantPhone: profilePhone,
      type: selectedLoanType,
      status: "under_review",
      amount: loanAmount,
      termMonths: loanTerm,
      progress: 25,
      submittedDate: new Date().toISOString().split("T")[0],
      interestRate: 6.5,
      riskScore: 25,
      defaultRate: 1.8,
      complianceStatus: "compliant",
      documents: uploadedFiles.map((f, idx) => ({
        id: `doc-new-${idx}`,
        name: f.name,
        type: f.type.includes("pdf") ? "Bank Statement" : "ID & Licensing",
        status: "valid"
      }))
    };

    onApplyLoan(newApp);
    setApplyStep(1);
    setUploadedFiles([]);
    setSelectedLoanType("home");
    setLoanAmount(350000);
    setLoanTerm(360);
    setPurpose("");
    setActiveSubTab("overview");
  };

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault();
    onUpdateProfile(profileName, profileEmail, profilePhone);
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(val);
  };

  return (
    <div id="customer-dashboard-container" className="grid grid-cols-1 lg:grid-cols-4 gap-8">
      {/* LEFT SIDEBAR NAVIGATION */}
      <div id="customer-navigation-sidebar" className="lg:col-span-1 bg-slate-900 border border-slate-800 p-6 rounded-2xl flex flex-col justify-between h-fit">
        <div className="space-y-6">
          <div className="flex items-center gap-3 pb-5 border-b border-slate-800">
            <div className="h-10 w-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 font-bold">
              {currentUser.name.charAt(0)}
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white">{currentUser.name}</h4>
              <p className="text-xs text-slate-400">Customer Account</p>
            </div>
          </div>

          <nav className="space-y-1">
            <button
              onClick={() => setActiveSubTab("overview")}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-medium transition-all ${
                activeSubTab === "overview"
                  ? "bg-emerald-600 text-white shadow-lg shadow-emerald-950/40"
                  : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
              }`}
            >
              <CreditCard className="h-4 w-4" />
              My Applications
            </button>
            <button
              onClick={() => setActiveSubTab("apply")}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-medium transition-all ${
                activeSubTab === "apply"
                  ? "bg-emerald-600 text-white shadow-lg shadow-emerald-950/40"
                  : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
              }`}
            >
              <Briefcase className="h-4 w-4" />
              Apply for New Loan
            </button>
            <button
              onClick={() => setActiveSubTab("help")}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-medium transition-all ${
                activeSubTab === "help"
                  ? "bg-emerald-600 text-white shadow-lg shadow-emerald-950/40"
                  : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
              }`}
            >
              <HelpCircle className="h-4 w-4" />
              Help Center
            </button>
            <button
              onClick={() => setActiveSubTab("settings")}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-medium transition-all ${
                activeSubTab === "settings"
                  ? "bg-emerald-600 text-white shadow-lg shadow-emerald-950/40"
                  : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
              }`}
            >
              <SettingsIcon className="h-4 w-4" />
              Portal Settings
            </button>
          </nav>
        </div>

        {/* AI Callout Banner */}
        <div className="mt-8 bg-gradient-to-br from-indigo-950/80 to-slate-900 border border-indigo-500/20 p-4 rounded-xl relative overflow-hidden">
          <div className="absolute top-0 right-0 w-20 h-20 bg-indigo-500/10 rounded-full blur-xl"></div>
          <span className="text-[10px] font-mono font-medium text-indigo-400 uppercase tracking-wider bg-indigo-950 px-2 py-0.5 rounded border border-indigo-500/30">
            LendSmart Assistant
          </span>
          <h5 className="text-xs font-semibold text-white mt-2">Need help with your application?</h5>
          <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
            Our AI assistant can analyze document requirements or query policies instantly.
          </p>
          <button
            onClick={onNavigateToChat}
            className="mt-3 w-full flex items-center justify-center gap-1.5 py-1.5 px-3 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-[11px] font-semibold text-white transition-colors cursor-pointer"
          >
            <span>Launch AI Assistant</span>
            <ArrowRight className="h-3 w-3" />
          </button>
        </div>
      </div>

      {/* SUB-TAB CONTENTS */}
      <div id="customer-main-content" className="lg:col-span-3 space-y-6">
        
        {/* VIEW 1: MY APPLICATIONS PORTFOLIO */}
        {activeSubTab === "overview" && (
          <div className="space-y-6">
            {/* Summary Statistics */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl flex items-center gap-4">
                <div className="p-3 bg-indigo-500/10 text-indigo-400 rounded-xl">
                  <Clock className="h-6 w-6" />
                </div>
                <div>
                  <p className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Active Applications</p>
                  <h3 className="text-2xl font-bold text-white font-display mt-0.5">
                    {activeCount < 10 ? `0${activeCount}` : activeCount}
                  </h3>
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl flex items-center gap-4">
                <div className="p-3 bg-emerald-500/10 text-emerald-400 rounded-xl">
                  <CheckCircle className="h-6 w-6" />
                </div>
                <div>
                  <p className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Approved Loans</p>
                  <h3 className="text-2xl font-bold text-white font-display mt-0.5">
                    {approvedCount < 10 ? `0${approvedCount}` : approvedCount}
                  </h3>
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl flex items-center gap-4">
                <div className="p-3 bg-teal-500/10 text-teal-400 rounded-xl">
                  <TrendingUp className="h-6 w-6" />
                </div>
                <div>
                  <p className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Total Credit Line</p>
                  <h3 className="text-2xl font-bold text-white font-display mt-0.5">
                    {formatCurrency(totalApprovedCredit)}
                  </h3>
                </div>
              </div>
            </div>

            {/* Active Applications Section */}
            <div className="space-y-4">
              <h3 className="text-base font-semibold text-white font-display">Active Applications</h3>
              
              {customerApps.filter(a => a.status === "under_review" || a.status === "pending_docs").length === 0 ? (
                <div className="bg-slate-900 border border-slate-800/80 p-8 rounded-2xl text-center">
                  <FileText className="h-8 w-8 text-slate-600 mx-auto mb-2" />
                  <p className="text-slate-400 text-xs">No active applications found. Create a new application below.</p>
                  <button
                    onClick={() => setActiveSubTab("apply")}
                    className="mt-3 inline-flex items-center gap-1 bg-emerald-600 hover:bg-emerald-500 px-4 py-2 rounded-lg text-xs font-semibold text-white transition-colors cursor-pointer"
                  >
                    Apply for a Loan
                  </button>
                </div>
              ) : (
                customerApps
                  .filter(a => a.status === "under_review" || a.status === "pending_docs")
                  .map(app => (
                    <div key={app.id} className="bg-slate-900 border border-slate-800 p-6 rounded-2xl relative overflow-hidden">
                      {/* Top Row */}
                      <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono font-medium text-slate-500">{app.id}</span>
                            <span className="text-xs font-semibold text-white uppercase tracking-wider bg-slate-800 px-2 py-0.5 rounded">
                              {app.type === "home" ? "🏠 Residential Mortgage" : app.type === "auto" ? "🚗 Auto Loan" : app.type === "business" ? "🏢 Business Credit Line" : "👤 Personal Loan"}
                            </span>
                          </div>
                          <h4 className="text-base font-semibold text-white mt-1.5">{formatCurrency(app.amount)} over {app.termMonths / 12} Years</h4>
                        </div>

                        {/* Status badge */}
                        <div>
                          {app.status === "under_review" ? (
                            <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-amber-500/10 text-amber-400 text-xs font-medium rounded-full border border-amber-500/20">
                              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>
                              Under Review
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-rose-500/10 text-rose-400 text-xs font-medium rounded-full border border-rose-500/20">
                              <AlertTriangle className="h-3 w-3" />
                              Pending Docs
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Progress bar */}
                      <div className="mt-5">
                        <div className="flex justify-between items-center text-xs mb-1.5">
                          <span className="text-slate-400 font-medium">Application Progress</span>
                          <span className="text-white font-semibold font-mono">{app.progress}%</span>
                        </div>
                        <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-500 ${
                              app.status === "pending_docs" ? "bg-rose-500" : "bg-emerald-500"
                            }`}
                            style={{ width: `${app.progress}%` }}
                          ></div>
                        </div>
                      </div>

                      {/* Warnings or actions if Pending Docs */}
                      {app.status === "pending_docs" && (
                        <div className="mt-5 p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-start gap-3">
                          <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
                          <div className="space-y-1">
                            <span className="text-xs font-semibold text-rose-300 block">Missing or Mismatched Documents</span>
                            <p className="text-xs text-slate-400 leading-relaxed">
                              Our OCR automated compliance scan detected mismatched details on your uploaded Bank Statements (Revenue discrepancy vs 1040). An Identity Card is also required.
                            </p>
                            <button
                              onClick={() => {
                                onNavigateToChat();
                              }}
                              className="text-xs font-medium text-emerald-400 hover:text-emerald-300 flex items-center gap-1 mt-1 cursor-pointer"
                            >
                              Consult AI Assistant regarding flags
                              <ArrowRight className="h-3 w-3" />
                            </button>
                          </div>
                        </div>
                      )}

                      {/* Documents Checklist */}
                      <div className="mt-5 pt-5 border-t border-slate-800/80">
                        <span className="text-xs font-medium text-slate-400">Submitted Verification Documents</span>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3">
                          {app.documents.map(doc => (
                            <div key={doc.id} className="flex items-center justify-between p-3 bg-slate-950 rounded-xl border border-slate-800">
                              <div className="flex items-center gap-2.5 overflow-hidden">
                                <FileText className="h-4 w-4 text-slate-400 shrink-0" />
                                <div className="overflow-hidden">
                                  <span className="text-xs text-white font-medium block truncate">{doc.name}</span>
                                  <span className="text-[10px] text-slate-500 block truncate">{doc.type}</span>
                                </div>
                              </div>
                              <div>
                                {doc.status === "valid" ? (
                                  <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded font-medium shrink-0">
                                    Verified
                                  </span>
                                ) : doc.status === "mismatch" ? (
                                  <span className="text-[10px] bg-rose-500/10 text-rose-400 px-2 py-0.5 rounded font-medium shrink-0">
                                    Mismatch
                                  </span>
                                ) : (
                                  <span className="text-[10px] bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded font-medium shrink-0">
                                    Pending
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))
              )}
            </div>

            {/* Application History */}
            <div className="space-y-4">
              <h3 className="text-base font-semibold text-white font-display">Application History</h3>
              <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950 border-b border-slate-800 text-slate-400 font-medium">
                      <tr>
                        <th className="p-4">Application ID</th>
                        <th className="p-4">Type</th>
                        <th className="p-4">Amount</th>
                        <th className="p-4">Rate (APR)</th>
                        <th className="p-4">Submitted Date</th>
                        <th className="p-4 text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 text-slate-300">
                      {customerApps
                        .filter(a => a.status === "approved" || a.status === "rejected")
                        .map(app => (
                          <tr key={app.id} className="hover:bg-slate-800/30 transition-colors">
                            <td className="p-4 font-mono font-medium text-slate-400">{app.id}</td>
                            <td className="p-4 font-semibold text-white">
                              {app.type === "home" ? "Residential Mortgage" : app.type === "auto" ? "Auto Loan" : app.type === "business" ? "Business Credit Line" : "Personal Loan"}
                            </td>
                            <td className="p-4 font-semibold">{formatCurrency(app.amount)}</td>
                            <td className="p-4 font-mono">{app.interestRate}%</td>
                            <td className="p-4 text-slate-400">{app.submittedDate}</td>
                            <td className="p-4 text-right">
                              {app.status === "approved" ? (
                                <span className="inline-flex items-center gap-1 bg-emerald-500/10 text-emerald-400 px-2.5 py-0.5 rounded text-[11px] font-medium border border-emerald-500/10">
                                  <CheckCircle className="h-3 w-3" />
                                  Approved
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 bg-rose-500/10 text-rose-400 px-2.5 py-0.5 rounded text-[11px] font-medium border border-rose-500/10">
                                  <X className="h-3 w-3" />
                                  Rejected
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* VIEW 2: NEW LOAN APPLICATION MULTI-STEP */}
        {activeSubTab === "apply" && (
          <div className="bg-slate-900 border border-slate-800 p-6 md:p-8 rounded-2xl space-y-6">
            <div className="flex justify-between items-center pb-5 border-b border-slate-800">
              <div>
                <h3 className="text-lg font-semibold text-white font-display">Start Your Loan Application</h3>
                <p className="text-xs text-slate-400 mt-0.5">Automated document analysis will evaluate your package upon submission.</p>
              </div>
              <span className="text-xs font-medium text-slate-400 font-mono">
                Step <span className="text-emerald-400 font-bold">{applyStep}</span> of 4
              </span>
            </div>

            {/* Stepper Progress Bar */}
            <div className="flex gap-2">
              {[1, 2, 3, 4].map(s => (
                <div
                  key={s}
                  className={`h-1.5 flex-1 rounded-full transition-all ${
                    s <= applyStep ? "bg-emerald-500" : "bg-slate-800"
                  }`}
                ></div>
              ))}
            </div>

            {/* STEP 1: SELECT TYPE */}
            {applyStep === 1 && (
              <div className="space-y-4">
                <h4 className="text-sm font-semibold text-slate-300">Select Loan Type</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {[
                    { key: "home", title: "Home Loan / Mortgage", desc: "For purchasing residential property or mortgage refinancing.", icon: Building },
                    { key: "auto", title: "Auto / Fleet Finance", desc: "Purchase private vehicles or fleet expansions.", icon: CreditCard },
                    { key: "personal", title: "Personal Facility", desc: "For general expenses, debt consolidations, or education.", icon: User },
                    { key: "business", title: "Business Credit", desc: "Working capital, inventory financing, or business lines.", icon: DollarSign }
                  ].map(item => {
                    const Icon = item.icon;
                    return (
                      <button
                        key={item.key}
                        type="button"
                        onClick={() => setSelectedLoanType(item.key as LoanType)}
                        className={`p-5 rounded-2xl border text-left flex flex-col justify-between h-44 cursor-pointer transition-all ${
                          selectedLoanType === item.key
                            ? "bg-emerald-950/20 border-emerald-500 shadow-md shadow-emerald-900/10"
                            : "bg-slate-950/40 border-slate-800 hover:border-slate-700 hover:bg-slate-900/20"
                        }`}
                      >
                        <div className={`p-2.5 rounded-xl ${selectedLoanType === item.key ? "bg-emerald-600 text-white" : "bg-slate-900 text-slate-400"}`}>
                          <Icon className="h-5 w-5" />
                        </div>
                        <div>
                          <h5 className="text-sm font-semibold text-white mt-3">{item.title}</h5>
                          <p className="text-xs text-slate-400 mt-1">{item.desc}</p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* STEP 2: DETAILS, SLIDERS & PAYMENT CALCULATOR */}
            {applyStep === 2 && (
              <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
                {/* Sliders Input */}
                <div className="lg:col-span-3 space-y-6">
                  <h4 className="text-sm font-semibold text-slate-300">Loan Parameters</h4>
                  
                  {/* Amount Slider */}
                  <div className="space-y-2">
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-slate-400 font-medium">Desired Loan Amount</span>
                      <span className="text-white font-bold text-sm font-mono">{formatCurrency(loanAmount)}</span>
                    </div>
                    <input
                      type="range"
                      min={10000}
                      max={1000000}
                      step={5000}
                      value={loanAmount}
                      onChange={(e) => setLoanAmount(Number(e.target.value))}
                      className="w-full h-1.5 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-emerald-500"
                    />
                    <div className="flex justify-between text-[10px] text-slate-500">
                      <span>$10k</span>
                      <span>$500k</span>
                      <span>$1M</span>
                    </div>
                  </div>

                  {/* Term Slider */}
                  <div className="space-y-2">
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-slate-400 font-medium">Loan Amortization Term</span>
                      <span className="text-white font-bold text-sm font-mono">{loanTerm / 12} Years ({loanTerm} mos)</span>
                    </div>
                    <input
                      type="range"
                      min={12}
                      max={360}
                      step={12}
                      value={loanTerm}
                      onChange={(e) => setLoanTerm(Number(e.target.value))}
                      className="w-full h-1.5 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-emerald-500"
                    />
                    <div className="flex justify-between text-[10px] text-slate-500">
                      <span>1 Year</span>
                      <span>15 Years</span>
                      <span>30 Years</span>
                    </div>
                  </div>

                  {/* Loan Purpose */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-slate-300">Purpose of Loan / Remarks</label>
                    <textarea
                      rows={3}
                      value={purpose}
                      onChange={(e) => setPurpose(e.target.value)}
                      placeholder="e.g. Purchasing primary residence home, expanding warehousing operational workspace, debt restructuring..."
                      className="w-full bg-slate-950 border border-slate-800 hover:border-slate-700 focus:border-emerald-500 rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none transition-colors"
                    />
                  </div>
                </div>

                {/* dynamic payment calculation summary */}
                <div className="lg:col-span-2 bg-slate-950 p-5 rounded-2xl border border-slate-800 flex flex-col justify-between">
                  <div>
                    <h5 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Estimated Monthly Payment</h5>
                    <div className="text-center py-4 bg-slate-900 rounded-xl border border-slate-800/60">
                      <span className="text-3xl font-extrabold font-display text-white">{formatCurrency(estimatedMonthlyPayment)}</span>
                      <span className="text-xs text-slate-500 block mt-1">/ month</span>
                    </div>

                    <div className="mt-6 space-y-3 text-xs">
                      <div className="flex justify-between py-1.5 border-b border-slate-900">
                        <span className="text-slate-500">Principal Facility</span>
                        <span className="text-slate-200 font-mono font-medium">{formatCurrency(loanAmount)}</span>
                      </div>
                      <div className="flex justify-between py-1.5 border-b border-slate-900">
                        <span className="text-slate-500">Benchmark Interest Rate</span>
                        <span className="text-emerald-400 font-mono font-bold">6.50% APR</span>
                      </div>
                      <div className="flex justify-between py-1.5 border-b border-slate-900">
                        <span className="text-slate-500">Total Payments (Term)</span>
                        <span className="text-slate-200 font-mono">{loanTerm} Payments</span>
                      </div>
                      <div className="flex justify-between py-1.5">
                        <span className="text-slate-500">Est. Total Interest</span>
                        <span className="text-slate-200 font-mono">{formatCurrency((estimatedMonthlyPayment * loanTerm) - loanAmount)}</span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-6 p-3 bg-indigo-950/20 border border-indigo-500/10 rounded-xl text-[10px] text-slate-400">
                    <span className="font-semibold text-indigo-300 block mb-0.5">AI Risk Scoring Notice</span>
                    Our consensus underwriters utilize real-time risk scores. Maintain a debt-to-income (DTI) ratio below 40% for expedited routing.
                  </div>
                </div>
              </div>
            )}

            {/* STEP 3: DOCUMENT UPLOADS */}
            {applyStep === 3 && (
              <div className="space-y-6">
                <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-2">
                  <div>
                    <h4 className="text-sm font-semibold text-slate-300">Document Upload Portal</h4>
                    <p className="text-xs text-slate-400 mt-0.5">Upload bank statements, tax returns, and government-issued ID credentials.</p>
                  </div>
                  <span className="text-[11px] bg-slate-950 text-slate-400 border border-slate-800 px-3 py-1 rounded-full font-medium">
                    Accepted: PDF, PNG, JPG (Max 15MB)
                  </span>
                </div>

                {/* Drag and drop zone */}
                <div
                  onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={(e) => { e.preventDefault(); setIsDragging(false); handleFileUpload(e.dataTransfer.files); }}
                  className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all ${
                    isDragging ? "border-emerald-500 bg-emerald-950/10" : "border-slate-800 bg-slate-950/20 hover:border-slate-700"
                  }`}
                >
                  <UploadCloud className="h-10 w-10 text-slate-500 mx-auto mb-3" />
                  <span className="text-xs font-semibold text-white block">Drag and drop documents here</span>
                  <span className="text-[11px] text-slate-500 block mt-1">or click to browse local folders</span>
                  <input
                    type="file"
                    multiple
                    onChange={(e) => handleFileUpload(e.target.files)}
                    className="hidden"
                    id="file-input-apply"
                  />
                  <label
                    htmlFor="file-input-apply"
                    className="mt-4 inline-flex px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700/60 rounded-xl text-xs font-semibold text-slate-200 transition-colors cursor-pointer"
                  >
                    Select File
                  </label>
                </div>

                {/* Uploaded files list */}
                {uploadedFiles.length > 0 && (
                  <div className="space-y-3">
                    <h5 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Uploaded Package Files ({uploadedFiles.length})</h5>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {uploadedFiles.map((file, idx) => (
                        <div key={idx} className="flex items-center justify-between p-3.5 bg-slate-950 rounded-xl border border-slate-800/80">
                          <div className="flex items-center gap-3 overflow-hidden">
                            <FileText className="h-5 w-5 text-emerald-400 shrink-0" />
                            <div className="overflow-hidden">
                              <span className="text-xs font-medium text-white block truncate">{file.name}</span>
                              <span className="text-[10px] text-slate-500 block">{file.size} • {file.type}</span>
                            </div>
                          </div>
                          <button
                            type="button"
                            onClick={() => setUploadedFiles(prev => prev.filter((_, i) => i !== idx))}
                            className="p-1 text-slate-500 hover:text-slate-300 transition-colors shrink-0 cursor-pointer"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {uploadedFiles.length === 0 && (
                  <div className="p-4 bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs rounded-xl flex items-start gap-2.5">
                    <AlertTriangle className="h-5 w-5 shrink-0" />
                    <div>
                      <span className="font-semibold block">Prerequisite Warning</span>
                      Applications submitted without complete bank statement logs or tax forms may face compliance delays. Upload files to verify.
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* STEP 4: REVIEW & SUBMIT */}
            {applyStep === 4 && (
              <div className="space-y-6">
                <div>
                  <h4 className="text-sm font-semibold text-slate-300">Final Verification Review</h4>
                  <p className="text-xs text-slate-400 mt-0.5">Please confirm all information is correct before submitting to AI screening.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Left Side: Loan Details */}
                  <div className="bg-slate-950 p-5 rounded-xl border border-slate-800 space-y-4 text-xs">
                    <h5 className="text-xs font-bold text-slate-400 uppercase tracking-wider border-b border-slate-900 pb-2">Loan Summary</h5>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Applicant Name</span>
                      <span className="text-white font-medium">{currentUser.name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Loan Product</span>
                      <span className="text-white font-semibold">
                        {selectedLoanType === "home" ? "Residential Mortgage" : selectedLoanType === "auto" ? "Auto & Fleet Financing" : selectedLoanType === "business" ? "Business Credit Line" : "Personal Facility"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Principal Facility</span>
                      <span className="text-emerald-400 font-mono font-bold">{formatCurrency(loanAmount)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Term Amortization</span>
                      <span className="text-slate-200 font-mono font-medium">{loanTerm / 12} Years ({loanTerm} months)</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Estimated Payment</span>
                      <span className="text-white font-mono font-semibold">{formatCurrency(estimatedMonthlyPayment)} / month</span>
                    </div>
                  </div>

                  {/* Right Side: Package Verification */}
                  <div className="bg-slate-950 p-5 rounded-xl border border-slate-800 space-y-4 text-xs">
                    <h5 className="text-xs font-bold text-slate-400 uppercase tracking-wider border-b border-slate-900 pb-2">Package Contents</h5>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Documents Attached</span>
                      <span className="text-white font-bold">{uploadedFiles.length} files</span>
                    </div>

                    <div className="space-y-1.5 max-h-32 overflow-y-auto pr-1">
                      {uploadedFiles.map((f, i) => (
                        <div key={i} className="flex justify-between text-[11px] text-slate-400">
                          <span className="truncate max-w-[180px]">{f.name}</span>
                          <span className="font-mono">{f.size}</span>
                        </div>
                      ))}
                      {uploadedFiles.length === 0 && (
                        <span className="text-rose-400 italic">No files attached. Manual upload will be requested later.</span>
                      )}
                    </div>

                    <div className="p-3 bg-emerald-950/20 border border-emerald-500/10 rounded-lg text-[10px] text-slate-400">
                      <span className="font-semibold text-emerald-300 block mb-0.5">Instant Underwriting consensus</span>
                      Our automated neural network checks documents for tampering or metadata modifications immediately upon submission.
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Form Footer Navigation buttons */}
            <div className="flex justify-between items-center pt-5 border-t border-slate-800 mt-6">
              <button
                type="button"
                onClick={() => {
                  if (applyStep > 1) {
                    setApplyStep(applyStep - 1);
                  } else {
                    setActiveSubTab("overview");
                  }
                }}
                className="px-5 py-2 bg-slate-800 hover:bg-slate-700/80 rounded-xl text-xs font-semibold text-slate-300 transition-colors cursor-pointer"
              >
                {applyStep === 1 ? "Cancel" : "Back"}
              </button>

              <button
                type="button"
                onClick={() => {
                  if (applyStep < 4) {
                    setApplyStep(applyStep + 1);
                  } else {
                    handleApplySubmit();
                  }
                }}
                className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-xl text-xs font-bold text-white flex items-center gap-1.5 cursor-pointer shadow-md shadow-emerald-950/25"
              >
                <span>{applyStep === 4 ? "Submit Application" : "Continue"}</span>
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        {/* VIEW 3: HELP CENTER */}
        {activeSubTab === "help" && (
          <div className="space-y-6">
            {/* Help Search Header */}
            <div className="bg-gradient-to-br from-slate-900 via-slate-900 to-indigo-950 border border-slate-800 p-8 rounded-3xl relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/5 rounded-full blur-2xl"></div>
              <div className="relative z-10 max-w-xl text-center md:text-left">
                <h3 className="text-xl font-bold font-display text-white">How can we help you today?</h3>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                  Search policies, document eligibility rules, or review common application exceptions.
                </p>

                <div className="relative mt-5">
                  <span className="absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-500">
                    <Search className="h-4.5 w-4.5" />
                  </span>
                  <input
                    type="text"
                    value={faqSearch}
                    onChange={(e) => setFaqSearch(e.target.value)}
                    placeholder="Search by keywords (e.g. income, matching documents, DTI, timelines)..."
                    className="w-full bg-slate-950 border border-slate-800 hover:border-slate-700 focus:border-emerald-500 rounded-xl py-3 pl-11 pr-4 text-xs text-white placeholder-slate-500 focus:outline-none transition-colors"
                  />
                </div>
              </div>
            </div>

            {/* Quick Categories */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                { title: "Eligibility Rules", desc: "Benchmark criteria, DTI formulas, credit rating scales.", icon: CheckCircle },
                { title: "Document Uploads", desc: "OCR compliance checklists, formatting, and resolution guides.", icon: FileText },
                { title: "Loan Status Explained", desc: "Understand Underwriting flags, consensus reviews, and schedules.", icon: Clock }
              ].map((cat, i) => {
                const Icon = cat.icon;
                return (
                  <div key={i} className="bg-slate-900 border border-slate-800 p-5 rounded-2xl hover:border-slate-700/60 transition-colors">
                    <div className="p-2 bg-indigo-950/60 border border-indigo-500/10 text-indigo-400 rounded-xl w-fit">
                      <Icon className="h-5 w-5" />
                    </div>
                    <h4 className="text-sm font-semibold text-white mt-3.5">{cat.title}</h4>
                    <p className="text-xs text-slate-400 mt-1 leading-relaxed">{cat.desc}</p>
                  </div>
                );
              })}
            </div>

            {/* Frequently Asked Questions Accordion */}
            <div className="space-y-4">
              <h3 className="text-base font-semibold text-white font-display">Frequently Asked Questions</h3>
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-2 divide-y divide-slate-800/60">
                {faqData
                  .filter(
                    f =>
                      f.question.toLowerCase().includes(faqSearch.toLowerCase()) ||
                      f.answer.toLowerCase().includes(faqSearch.toLowerCase())
                  )
                  .map((faq, idx) => {
                    const isExpanded = expandedFaqIndex === idx;
                    return (
                      <div key={idx} className="p-3">
                        <button
                          type="button"
                          onClick={() => setExpandedFaqIndex(isExpanded ? null : idx)}
                          className="w-full flex items-center justify-between text-left py-2 hover:text-white cursor-pointer"
                        >
                          <span className="text-xs font-semibold text-slate-200">{faq.question}</span>
                          {isExpanded ? (
                            <ChevronUp className="h-4 w-4 text-slate-500 shrink-0" />
                          ) : (
                            <ChevronDown className="h-4 w-4 text-slate-500 shrink-0" />
                          )}
                        </button>
                        {isExpanded && (
                          <div className="text-xs text-slate-400 leading-relaxed mt-2.5 pl-0.5 pb-2">
                            {faq.answer}
                          </div>
                        )}
                      </div>
                    );
                  })}
                {faqData.filter(
                  f =>
                    f.question.toLowerCase().includes(faqSearch.toLowerCase()) ||
                    f.answer.toLowerCase().includes(faqSearch.toLowerCase())
                ).length === 0 && (
                  <div className="text-center p-8 text-xs text-slate-500">
                    No matching questions found for your query. Try searching simple words.
                  </div>
                )}
              </div>
            </div>

            {/* Still have questions */}
            <div className="bg-slate-950 border border-slate-800 p-6 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="text-center sm:text-left">
                <h4 className="text-sm font-semibold text-white">Still have questions?</h4>
                <p className="text-xs text-slate-400 mt-1">Our customer experience agents and RAG-integrated AI chatbot are standing by.</p>
              </div>
              <button
                onClick={onNavigateToChat}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-xl text-xs font-semibold text-white transition-colors cursor-pointer"
              >
                Launch AI Assistant Chat
              </button>
            </div>
          </div>
        )}

        {/* VIEW 4: PORTAL SETTINGS */}
        {activeSubTab === "settings" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Profile details */}
              <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-6">
                <h3 className="text-sm font-semibold text-white font-display border-b border-slate-800 pb-3">Profile Settings</h3>
                
                <form onSubmit={handleSaveProfile} className="space-y-4 mt-5">
                  {saveSuccess && (
                    <div className="p-3 bg-emerald-500/15 border border-emerald-500/20 text-emerald-300 text-xs rounded-lg">
                      Settings updated successfully!
                    </div>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-slate-400">Full Name</label>
                      <input
                        type="text"
                        value={profileName}
                        onChange={(e) => setProfileName(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 hover:border-slate-700 focus:border-emerald-500 rounded-xl p-3 text-xs text-white focus:outline-none"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-slate-400">Email Address</label>
                      <input
                        type="email"
                        value={profileEmail}
                        onChange={(e) => setProfileEmail(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 hover:border-slate-700 focus:border-emerald-500 rounded-xl p-3 text-xs text-white focus:outline-none"
                      />
                    </div>

                    <div className="space-y-1.5 md:col-span-2">
                      <label className="text-xs font-medium text-slate-400">Contact Phone</label>
                      <input
                        type="text"
                        value={profilePhone}
                        onChange={(e) => setProfilePhone(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 hover:border-slate-700 focus:border-emerald-500 rounded-xl p-3 text-xs text-white focus:outline-none"
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-xl text-xs font-semibold text-white transition-colors cursor-pointer"
                  >
                    Save Changes
                  </button>
                </form>
              </div>

              {/* Security & Multi-factor */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
                <h3 className="text-sm font-semibold text-white font-display border-b border-slate-800 pb-3 flex items-center gap-1.5">
                  <Lock className="h-4 w-4 text-emerald-400" />
                  Security Controls
                </h3>

                <div className="space-y-4 text-xs">
                  <div className="flex justify-between items-center py-2 border-b border-slate-800">
                    <div>
                      <span className="font-semibold text-slate-200 block">Two-Factor Auth (2FA)</span>
                      <p className="text-[10px] text-slate-400 mt-0.5">Secure logins via mobile authenticator codes.</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" defaultChecked className="sr-only peer" />
                      <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-slate-400 after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-600 peer-checked:after:bg-white"></div>
                    </label>
                  </div>

                  <div className="flex justify-between items-center py-2">
                    <div>
                      <span className="font-semibold text-slate-200 block">Biometric OCR Verification</span>
                      <p className="text-[10px] text-slate-400 mt-0.5">Authorizes automated camera matches on ID files.</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" className="sr-only peer" />
                      <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-slate-400 after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-600 peer-checked:after:bg-white"></div>
                    </label>
                  </div>
                </div>
              </div>
            </div>

            {/* Notification settings panel */}
            <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
              <h3 className="text-sm font-semibold text-white font-display border-b border-slate-800 pb-3 flex items-center gap-1.5">
                <Bell className="h-4 w-4 text-emerald-400" />
                Notification Channels
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-5 text-xs">
                {[
                  { title: "Email Notifications", desc: "Underwriter feedback reports and monthly statements.", active: true },
                  { title: "SMS Messaging Alerts", desc: "Compliance flags and missing document notifications.", active: true },
                  { title: "Live Push Notifications", desc: "Real-time automated status transitions.", active: false }
                ].map((notif, i) => (
                  <div key={i} className="flex justify-between items-start p-4 bg-slate-950 rounded-xl border border-slate-850">
                    <div className="space-y-1 pr-4">
                      <span className="font-semibold text-slate-200 block">{notif.title}</span>
                      <p className="text-[10px] text-slate-500 leading-relaxed">{notif.desc}</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer mt-0.5 shrink-0">
                      <input type="checkbox" defaultChecked={notif.active} className="sr-only peer" />
                      <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-slate-400 after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-600 peer-checked:after:bg-white"></div>
                    </label>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
