/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  Search,
  Filter,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Clock,
  ArrowRight,
  TrendingDown,
  Brain,
  Cpu,
  FileCheck,
  Sliders,
  Database,
  Users,
  Activity,
  Maximize2,
  FileText,
  Trash2,
  Lock,
  Plus,
  Play,
  RotateCcw
} from "lucide-react";
import { Application, AuditLog, PolicyDocument } from "../types";

interface OfficerDashboardProps {
  applications: Application[];
  auditLogs: AuditLog[];
  onApproveApplication: (id: string) => void;
  onRejectApplication: (id: string) => void;
  onAddAuditLog: (log: Omit<AuditLog, "id" | "timestamp">) => void;
  onUpdateApplicationDocs: (id: string, docId: string, status: "valid" | "mismatch") => void;
}

export default function OfficerDashboard({
  applications,
  auditLogs,
  onApproveApplication,
  onRejectApplication,
  onAddAuditLog,
  onUpdateApplicationDocs
}: OfficerDashboardProps) {
  // Navigation tabs for Officer Portal
  const [activeTab, setActiveTab] = useState<"queue" | "verification" | "risk" | "logs" | "admin">("queue");
  
  // Selected application in detail view (defaults to LX-94021-B if available)
  const [selectedAppId, setSelectedAppId] = useState<string>("LX-94021-B");
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  // Admin Sliders State
  const [aiThreshold, setAiThreshold] = useState<number>(85);
  const [ragPolicyDocs, setRagPolicyDocs] = useState<PolicyDocument[]>([]);
  const [newDocName, setNewDocName] = useState("");
  const [newDocVersion, setNewDocVersion] = useState("v1.0");

  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/policy-documents")
      .then(r => r.ok ? r.json() : { policyDocuments: [] })
      .then(d => setRagPolicyDocs(d.policyDocuments || []))
      .catch(() => setRagPolicyDocs([]));
  }, []);

  // Selected Log for detail modal
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  const selectedApp = applications.find(a => a.id === selectedAppId) || applications[0];

  const filteredApps = applications.filter(app => {
    const matchesSearch = app.applicantName.toLowerCase().includes(searchQuery.toLowerCase()) || app.id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === "all" || app.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(val);
  };

  // Add new policy document handler
  const handleAddPolicyDoc = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDocName) return;
    try {
      const res = await fetch("http://127.0.0.1:8000/api/policy-documents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newDocName, version: newDocVersion }),
      });
      if (res.ok) {
        const data = await res.json();
        setRagPolicyDocs(prev => [data.policyDocument, ...prev]);
        if (data.auditLog) {
          onAddAuditLog({
            actor: data.auditLog.actor,
            eventType: data.auditLog.eventType,
            riskLevel: data.auditLog.riskLevel as "low" | "medium" | "high",
            details: data.auditLog.details
          });
        }
      }
    } catch (err) {
      console.warn("Failed to create policy doc:", err);
    }
    setNewDocName("");
  };

  const handleActionOnApp = (action: "approve" | "reject") => {
    if (action === "approve") {
      onApproveApplication(selectedApp.id);
      onAddAuditLog({
        actor: "Officer Sarah J.",
        eventType: "Underwriter Final Approval",
        riskLevel: "low",
        details: `Granted unconditional underwriting final approval for application ${selectedApp.id} (${selectedApp.applicantName}).`
      });
    } else {
      onRejectApplication(selectedApp.id);
      onAddAuditLog({
        actor: "Officer Sarah J.",
        eventType: "Underwriter Rejection",
        riskLevel: "high",
        details: `Rejected credit facility request for application ${selectedApp.id} (${selectedApp.applicantName}) due to compliance variances.`
      });
    }
  };

  return (
    <div id="officer-portal-view" className="space-y-6 font-sans">
      
      {/* PORTAL TOP NAVIGATION HEADER */}
      <div id="officer-portal-nav" className="flex flex-col md:flex-row justify-between items-start md:items-center bg-slate-900 border border-slate-800 p-4 rounded-2xl gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-indigo-600 rounded-xl text-white shadow-lg shadow-indigo-900/30">
            <Cpu className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider font-display">LendSmart Ops Center</h2>
            <p className="text-[10px] text-slate-400">Enterprise AI Underwriting and Compliance Audit Terminal</p>
          </div>
        </div>

        {/* Sub tabs nav */}
        <div className="flex flex-wrap gap-1.5 p-1 bg-slate-950 rounded-xl border border-slate-800/80">
          {[
            { id: "queue", title: "Priority Queue", icon: Sliders },
            { id: "verification", title: "OCR Document Check", icon: FileCheck },
            { id: "risk", title: "Risk Analytics", icon: Activity },
            { id: "logs", title: "Compliance Logs", icon: Database },
            { id: "admin", title: "System Controls", icon: Sliders }
          ].map(tab => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition-all ${
                  activeTab === tab.id
                    ? "bg-indigo-600 text-white shadow"
                    : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {tab.title}
              </button>
            );
          })}
        </div>
      </div>

      {/* SUB-VIEW 1: PRIORITY QUEUE + INTENSIVE DETAIL BENTO GRID */}
      {activeTab === "queue" && (
        <div id="officer-queue-bento" className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* PRIORITY QUEUE (Left 5 columns) */}
          <div className="lg:col-span-5 bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col h-[calc(100vh-230px)] overflow-hidden">
            <div className="pb-4 border-b border-slate-800 space-y-3 shrink-0">
              <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider">Priority Application Queue</h3>
              
              {/* Filter Row */}
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <span className="absolute inset-y-0 left-0 flex items-center pl-2.5 text-slate-500">
                    <Search className="h-3.5 w-3.5" />
                  </span>
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search applicant or ID..."
                    className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-lg py-1.5 pl-8 pr-3 text-[11px] text-white focus:outline-none placeholder-slate-500"
                  />
                </div>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="bg-slate-950 border border-slate-800 text-[11px] text-slate-300 rounded-lg px-2.5 py-1.5 focus:outline-none"
                >
                  <option value="all">All statuses</option>
                  <option value="under_review">Under Review</option>
                  <option value="pending_docs">Pending Docs</option>
                  <option value="approved">Approved</option>
                </select>
              </div>
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto mt-4 space-y-2 pr-1">
              {filteredApps.map(app => (
                <button
                  key={app.id}
                  onClick={() => setSelectedAppId(app.id)}
                  className={`w-full text-left p-4 rounded-xl border transition-all cursor-pointer block relative ${
                    selectedAppId === app.id
                      ? "bg-indigo-950/20 border-indigo-500/80 shadow-md"
                      : "bg-slate-950/40 border-slate-800 hover:border-slate-700 hover:bg-slate-900/10"
                  }`}
                >
                  <div className="flex justify-between items-start gap-2">
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] font-mono font-medium text-slate-500">{app.id}</span>
                        <span className="text-[9px] bg-slate-900 text-slate-400 px-1.5 py-0.5 rounded uppercase font-bold tracking-wider">
                          {app.type}
                        </span>
                      </div>
                      <h4 className="text-xs font-bold text-white mt-1.5 leading-snug truncate max-w-[200px]">{app.applicantName}</h4>
                      <span className="text-[11px] font-mono font-semibold text-slate-400 block mt-1">
                        {formatCurrency(app.amount)}
                      </span>
                    </div>

                    <div className="text-right space-y-1.5">
                      {/* Risk Badge */}
                      <span className={`inline-block text-[9px] px-1.5 py-0.5 font-bold uppercase rounded ${
                        app.riskScore < 30
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/15"
                          : app.riskScore < 60
                          ? "bg-amber-500/10 text-amber-400 border border-amber-500/15"
                          : "bg-rose-500/10 text-rose-400 border border-rose-500/15"
                      }`}>
                        Risk: {app.riskScore}
                      </span>

                      {/* Status dot */}
                      <div className="flex items-center justify-end gap-1 text-[10px]">
                        <span className={`h-1.5 w-1.5 rounded-full ${
                          app.status === "approved"
                            ? "bg-emerald-400 animate-pulse"
                            : app.status === "pending_docs"
                            ? "bg-rose-400 animate-pulse"
                            : "bg-amber-400 animate-pulse"
                        }`}></span>
                        <span className="text-slate-400 font-medium whitespace-nowrap">
                          {app.status === "under_review" ? "Under Review" : app.status === "pending_docs" ? "Pending Docs" : "Approved"}
                        </span>
                      </div>
                    </div>
                  </div>
                </button>
              ))}

              {filteredApps.length === 0 && (
                <p className="text-center text-xs text-slate-500 py-12 italic">No applications match your search query.</p>
              )}
            </div>
          </div>

          {/* INTELLIGENT AGENT DETAIL VIEW (Right 7 columns) */}
          <div className="lg:col-span-7 space-y-6 h-[calc(100vh-230px)] overflow-y-auto pr-1">
            
            {/* Top overview card */}
            <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl relative overflow-hidden">
              <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3 border-b border-slate-800 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-slate-500">{selectedApp.id}</span>
                    <span className="text-[10px] bg-slate-800 text-slate-300 font-bold px-2 py-0.5 rounded uppercase">
                      {selectedApp.type} Product
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-white font-display mt-1.5">{selectedApp.applicantName}</h3>
                  <p className="text-[11px] text-slate-400">{selectedApp.applicantEmail} • {selectedApp.applicantPhone}</p>
                </div>

                {/* Underwriter Action Buttons */}
                <div className="flex gap-2">
                  <button
                    disabled={selectedApp.status === "approved"}
                    onClick={() => handleActionOnApp("approve")}
                    className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 disabled:text-slate-500 rounded-lg text-xs font-bold text-white transition-colors cursor-pointer"
                  >
                    Approve Facility
                  </button>
                  <button
                    disabled={selectedApp.status === "rejected"}
                    onClick={() => handleActionOnApp("reject")}
                    className="px-3 py-1.5 bg-rose-600 hover:bg-rose-500 disabled:bg-slate-800 disabled:text-slate-500 rounded-lg text-xs font-bold text-white transition-colors cursor-pointer"
                  >
                    Reject Facility
                  </button>
                </div>
              </div>

              {/* Bento Grid AI Consensus */}
              {selectedApp.agentConsensus && (
                <div className="mt-5 space-y-4">
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Multi-Agent Underwriting Consensus</h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Agent 1 */}
                    <div className="bg-slate-950 p-4 rounded-xl border border-slate-850 space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-[10px] text-indigo-400 font-mono font-medium uppercase tracking-wider">Doc Integrity</span>
                        <span className={`h-2 w-2 rounded-full ${selectedApp.agentConsensus.documentValidation.status === "pass" ? "bg-emerald-400" : "bg-amber-400"}`}></span>
                      </div>
                      <h5 className="text-xs font-semibold text-slate-200">Document Validation</h5>
                      <p className="text-[10px] text-slate-400 leading-relaxed leading-normal">{selectedApp.agentConsensus.documentValidation.details}</p>
                      <div className="flex justify-between text-[10px] pt-1 font-mono text-slate-500">
                        <span>Confidence</span>
                        <span className="text-emerald-400 font-semibold">{selectedApp.agentConsensus.documentValidation.score}%</span>
                      </div>
                    </div>

                    {/* Agent 2 */}
                    <div className="bg-slate-950 p-4 rounded-xl border border-slate-850 space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-[10px] text-indigo-400 font-mono font-medium uppercase tracking-wider">Compliance check</span>
                        <span className={`h-2 w-2 rounded-full ${selectedApp.agentConsensus.policyCompliance.status === "pass" ? "bg-emerald-400" : selectedApp.agentConsensus.policyCompliance.status === "warn" ? "bg-amber-400" : "bg-rose-400"}`}></span>
                      </div>
                      <h5 className="text-xs font-semibold text-slate-200">Policy Compliance</h5>
                      <p className="text-[10px] text-slate-400 leading-relaxed leading-normal">{selectedApp.agentConsensus.policyCompliance.details}</p>
                      <div className="flex justify-between text-[10px] pt-1 font-mono text-slate-500">
                        <span>Score</span>
                        <span className="text-emerald-400 font-semibold">{selectedApp.agentConsensus.policyCompliance.score}%</span>
                      </div>
                    </div>

                    {/* Agent 3 */}
                    <div className="bg-slate-950 p-4 rounded-xl border border-slate-850 space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-[10px] text-indigo-400 font-mono font-medium uppercase tracking-wider">Risk model</span>
                        <span className={`h-2 w-2 rounded-full ${selectedApp.agentConsensus.riskEvaluation.status === "pass" ? "bg-emerald-400" : selectedApp.agentConsensus.riskEvaluation.status === "warn" ? "bg-amber-400" : "bg-rose-400"}`}></span>
                      </div>
                      <h5 className="text-xs font-semibold text-slate-200">Risk Evaluation</h5>
                      <p className="text-[10px] text-slate-400 leading-relaxed leading-normal">{selectedApp.agentConsensus.riskEvaluation.details}</p>
                      <div className="flex justify-between text-[10px] pt-1 font-mono text-slate-500">
                        <span>Grade</span>
                        <span className="text-emerald-400 font-semibold">{selectedApp.agentConsensus.riskEvaluation.score}%</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Document Similarity Heatmap Grid */}
            {selectedApp.similarityHeatmap && (
              <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">OCR Document Similarity Cross-Comparison Heatmap</h4>
                
                <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
                  {/* Heatmap display */}
                  <div className="md:col-span-8 overflow-x-auto pr-1">
                    <div className="min-w-[320px]">
                      {/* Grid header labels */}
                      <div className="grid grid-cols-6 gap-1 mb-1">
                        <div className="col-span-1"></div>
                        {selectedApp.similarityHeatmap.labels.map((lbl, idx) => (
                          <div key={idx} className="col-span-1 text-[9px] text-slate-500 font-mono text-center truncate" title={lbl}>
                            {lbl.replace(".pdf", "")}
                          </div>
                        ))}
                      </div>

                      {/* Heatmap grid rows */}
                      {selectedApp.similarityHeatmap.matrix.map((row, rIdx) => (
                        <div key={rIdx} className="grid grid-cols-6 gap-1 mb-1 items-center">
                          {/* Row label */}
                          <div className="col-span-1 text-[9px] text-slate-500 font-mono truncate" title={selectedApp.similarityHeatmap!.labels[rIdx]}>
                            {selectedApp.similarityHeatmap!.labels[rIdx].replace(".pdf", "")}
                          </div>

                          {/* Matrix columns */}
                          {row.map((cellVal, cIdx) => {
                            // Map cell value to bg color
                            const pct = Math.round(cellVal * 100);
                            let bgClass = "bg-slate-950 text-slate-600";
                            if (pct === 100) bgClass = "bg-indigo-600 text-white";
                            else if (pct > 70) bgClass = "bg-indigo-950/80 text-indigo-300 border border-indigo-500/30";
                            else if (pct > 30) bgClass = "bg-indigo-950/30 text-indigo-400/80";
                            else if (pct > 10) bgClass = "bg-slate-950 text-slate-500";

                            return (
                              <div
                                key={cIdx}
                                className={`col-span-1 h-9 flex items-center justify-center rounded text-[10px] font-semibold font-mono ${bgClass}`}
                                title={`${selectedApp.similarityHeatmap!.labels[rIdx]} vs ${selectedApp.similarityHeatmap!.labels[cIdx]} : ${pct}%`}
                              >
                                {pct}%
                              </div>
                            );
                          })}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Heatmap Insights */}
                  <div className="md:col-span-4 bg-slate-950 p-4 rounded-xl border border-slate-855 text-xs space-y-2">
                    <h5 className="font-bold text-slate-200">Analysis Insights</h5>
                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      A similarity metric of <span className="text-indigo-400 font-semibold">90%+</span> indicates potential duplication, file recycling, or fraudulent invoice templating.
                    </p>
                    <div className="p-2 bg-indigo-950/25 border border-indigo-500/10 rounded text-[10px] text-indigo-300 font-mono">
                      Max Match: {Math.round(selectedApp.similarityHeatmap.matrix[0][1] * 100)}% (Chase_Oct vs IRS_1040)
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Underwriting Audit Trail & HITL console */}
            <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl space-y-4">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Audit Trail & Human-in-the-Loop (HITL) Logs</h4>
              <div className="space-y-3 max-h-56 overflow-y-auto pr-1">
                {auditLogs.map((log, idx) => (
                  <div key={idx} className="flex gap-3 text-xs bg-slate-950 p-3.5 rounded-xl border border-slate-850">
                    <span className="text-[10px] text-slate-500 font-mono shrink-0 mt-0.5">{log.timestamp.split(" ")[1]}</span>
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="font-semibold text-slate-200">{log.actor}</span>
                        <span className="text-slate-500">•</span>
                        <span className="text-[10px] bg-slate-900 text-slate-400 px-1.5 py-0.5 rounded font-mono uppercase">
                          {log.eventType}
                        </span>
                      </div>
                      <p className="text-slate-400 mt-1 leading-relaxed">{log.details}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>
        </div>
      )}

      {/* SUB-VIEW 2: DOCUMENT ANALYSIS OCR COMPARISON */}
      {activeTab === "verification" && (
        <div id="ocr-doc-verification-tab" className="bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-6">
          <div className="border-b border-slate-800 pb-4">
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider">OCR Cross-Document Information Extraction</h3>
            <p className="text-xs text-slate-400 mt-0.5">Automated OCR alignment verifies key fields between bank logs and official tax returns.</p>
          </div>

          {/* Selector of active mismatches */}
          <div className="flex flex-wrap gap-2">
            {applications.map(app => (
              <button
                key={app.id}
                onClick={() => setSelectedAppId(app.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer border transition-all ${
                  selectedAppId === app.id
                    ? "bg-indigo-600 text-white border-indigo-500"
                    : "bg-slate-950 text-slate-400 border-slate-850 hover:border-slate-700"
                }`}
              >
                {app.id} - {app.applicantName.split(" ")[0]}
              </button>
            ))}
          </div>

          {/* OCR Fields Comparison Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Table comparison */}
            <div className="lg:col-span-8 space-y-4">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Field Cross-Check logs</span>
              
              <div className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900 text-slate-400 border-b border-slate-850 font-medium">
                    <tr>
                      <th className="p-4">Extracted Field Attribute</th>
                      <th className="p-4">Chase_Statement.pdf</th>
                      <th className="p-4">IRS_Form_1040.pdf</th>
                      <th className="p-4 text-right">Alignment Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-850 text-slate-300">
                    {selectedApp.documents[0]?.ocrFields ? (
                      selectedApp.documents[0].ocrFields.map((field, idx) => (
                        <tr key={idx} className="hover:bg-slate-900/40 transition-colors">
                          <td className="p-4 font-semibold text-white">{field.label}</td>
                          <td className="p-4 font-mono text-slate-400">{field.doc1Value}</td>
                          <td className="p-4 font-mono text-slate-400">{field.doc2Value}</td>
                          <td className="p-4 text-right">
                            {field.status === "match" ? (
                              <span className="inline-flex items-center gap-1 bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded text-[10px] font-bold">
                                <CheckCircle className="h-3 w-3" /> Align Match
                              </span>
                            ) : field.status === "warning" ? (
                              <span className="inline-flex items-center gap-1 bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded text-[10px] font-bold">
                                <AlertTriangle className="h-3 w-3" /> Warning Match
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 bg-rose-500/10 text-rose-400 px-2 py-0.5 rounded text-[10px] font-bold">
                                <XCircle className="h-3 w-3" /> Mismatch Flag
                              </span>
                            )}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={4} className="p-8 text-center text-slate-500 italic">
                          No specific OCR extracted tables for this application. Documents are marked as verified.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Document Verification checklist */}
            <div className="lg:col-span-4 bg-slate-950 p-5 rounded-xl border border-slate-800 space-y-4 flex flex-col justify-between">
              <div className="space-y-4">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Verification checklist</span>
                
                <div className="space-y-3">
                  <div className="flex items-start gap-3 p-3 bg-slate-900 rounded-lg">
                    <input type="checkbox" defaultChecked className="h-4 w-4 text-indigo-600 border-slate-800 bg-slate-950 rounded mt-0.5" />
                    <div>
                      <span className="text-xs font-semibold text-slate-200 block">Bank Account Holder Match</span>
                      <p className="text-[10px] text-slate-500 mt-0.5">Underwriting logs check applicant against bank records.</p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3 p-3 bg-slate-900 rounded-lg">
                    <input type="checkbox" defaultChecked className="h-4 w-4 text-indigo-600 border-slate-800 bg-slate-950 rounded mt-0.5" />
                    <div>
                      <span className="text-xs font-semibold text-slate-200 block">Tax Filing EIN cross-check</span>
                      <p className="text-[10px] text-slate-500 mt-0.5">Validates corporate filing registrations with local tax offices.</p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3 p-3 bg-slate-900 rounded-lg">
                    <input type="checkbox" className="h-4 w-4 text-indigo-600 border-slate-800 bg-slate-950 rounded mt-0.5" />
                    <div>
                      <span className="text-xs font-semibold text-slate-200 block">Biometric ID facial match</span>
                      <p className="text-[10px] text-slate-500 mt-0.5">Compares selfie captures with government databases (Pending check).</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-900">
                <button
                  onClick={() => {
                    onAddAuditLog({
                      actor: "Officer Sarah J.",
                      eventType: "Manual Override Check",
                      riskLevel: "medium",
                      details: `Completed manual cross-check alignment for application ${selectedApp.id}. Overrode reported revenue mismatch.`
                    });
                  }}
                  className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-xs font-bold text-white transition-colors cursor-pointer"
                >
                  Override Mismatch and Approve Check
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUB-VIEW 3: RISK ASSESSMENT DASHBOARD */}
      {activeTab === "risk" && (
        <div id="risk-assessment-dashboard-tab" className="space-y-6">
          {/* Headline widgets */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">AI Predicted Default Rate</span>
              <div className="flex items-baseline gap-2 mt-2">
                <h3 className="text-2xl font-bold font-display text-emerald-400">2.41%</h3>
                <span className="text-[10px] text-emerald-500 font-medium">-0.14% vs last week</span>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">High Risk Portfolio</span>
              <div className="flex items-baseline gap-2 mt-2">
                <h3 className="text-2xl font-bold font-display text-rose-400">12.5%</h3>
                <span className="text-[10px] text-rose-500 font-medium">+1.2% variance</span>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Avg Underwriting Time</span>
              <div className="flex items-baseline gap-2 mt-2">
                <h3 className="text-2xl font-bold font-display text-indigo-400">14.2 min</h3>
                <span className="text-[10px] text-indigo-500 font-medium">-2.5 min with AI RAG</span>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Automated Pass Rate</span>
              <div className="flex items-baseline gap-2 mt-2">
                <h3 className="text-2xl font-bold font-display text-white">84.2%</h3>
                <span className="text-[10px] text-emerald-500 font-medium">Within target range</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Risk Warnings */}
            <div className="lg:col-span-8 bg-slate-900 border border-slate-800 p-5 rounded-2xl space-y-4">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Live System Risk Alerts</h4>
              
              <div className="space-y-3">
                <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="text-xs font-semibold text-rose-300 block">Critical Discrepancy Flagged</span>
                    <p className="text-[11px] text-slate-400 leading-relaxed mt-0.5">
                      Vanguard Bio-Med (#LX-92305-V) exceeds maximum permitted debt leverage ratio rules. Current: 4.2. Underwriting limit: 3.0. Automated rejection proposed.
                    </p>
                  </div>
                </div>

                <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="text-xs font-semibold text-amber-300 block">Document Signature Variance Flagged</span>
                    <p className="text-[11px] text-slate-400 leading-relaxed mt-0.5">
                      Solaris Cloud Tech (#LX-95204-S) bank statements fail automatic OCR metadata timestamp alignment checks. Manual underwriter verification is mandatory.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Failure factors */}
            <div className="lg:col-span-4 bg-slate-900 border border-slate-800 p-5 rounded-2xl space-y-4">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Common Failure Points</h4>
              
              <div className="space-y-3.5 text-xs">
                <div>
                  <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                    <span>Income / Bank Statement Variance</span>
                    <span className="font-semibold text-white">48% of cases</span>
                  </div>
                  <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden">
                    <div className="bg-rose-500 h-full" style={{ width: "48%" }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                    <span>DTI Ratio Over Limit</span>
                    <span className="font-semibold text-white">28% of cases</span>
                  </div>
                  <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden">
                    <div className="bg-amber-500 h-full" style={{ width: "28%" }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                    <span>Identity biometric fail</span>
                    <span className="font-semibold text-white">14% of cases</span>
                  </div>
                  <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden">
                    <div className="bg-indigo-500 h-full" style={{ width: "14%" }}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUB-VIEW 4: SYSTEM AUDIT LOGS */}
      {activeTab === "logs" && (
        <div id="system-audit-logs-tab" className="bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-4 h-[calc(100vh-230px)] flex flex-col overflow-hidden">
          <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3 border-b border-slate-800 pb-4 shrink-0">
            <div>
              <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider">Immutable Compliance & Audit Ledger</h3>
              <p className="text-xs text-slate-400 mt-0.5">Tracking all automated AI underwriting decisions and underwriter manual override checkpoints.</p>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-[11px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/15 px-3 py-1 rounded-full font-mono font-bold">
                Secured Audit Pipeline Active
              </span>
            </div>
          </div>

          {/* Logs table list */}
          <div className="flex-1 overflow-y-auto space-y-2 pr-1 mt-4">
            {auditLogs.map((log) => (
              <div
                key={log.id}
                onClick={() => setSelectedLog(log)}
                className="bg-slate-950 border border-slate-850 hover:border-slate-700/80 p-4 rounded-xl flex justify-between items-start gap-4 cursor-pointer transition-all"
              >
                <div className="flex items-start gap-3">
                  <div className={`p-1.5 rounded mt-0.5 shrink-0 ${
                    log.riskLevel === "high"
                      ? "bg-rose-500/10 text-rose-400"
                      : log.riskLevel === "medium"
                      ? "bg-amber-500/10 text-amber-400"
                      : "bg-emerald-500/10 text-emerald-400"
                  }`}>
                    <ShieldCheck className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-semibold text-slate-200">{log.actor}</span>
                      <span className="text-slate-600 text-[10px]">•</span>
                      <span className="text-[10px] bg-slate-900 text-slate-400 px-2 py-0.5 rounded font-mono uppercase">
                        {log.eventType}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1.5 leading-relaxed truncate max-w-[280px] sm:max-w-xl md:max-w-2xl">
                      {log.details}
                    </p>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <span className="text-[10px] text-slate-500 font-mono block">{log.timestamp}</span>
                  <span className="text-[10px] text-indigo-400 hover:underline font-semibold block mt-1">View Audit</span>
                </div>
              </div>
            ))}
          </div>

          {/* Detail modal for selected log */}
          {selectedLog && (
            <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
              <div className="bg-slate-900 border border-slate-800 max-w-md w-full rounded-2xl p-6 space-y-5 relative">
                <button
                  type="button"
                  onClick={() => setSelectedLog(null)}
                  className="absolute top-4 right-4 text-slate-400 hover:text-white"
                >
                  <Maximize2 className="h-4 w-4" />
                </button>
                <div className="flex items-center gap-3 border-b border-slate-800 pb-3">
                  <div className="p-2 bg-indigo-600/10 text-indigo-400 rounded-xl">
                    <ShieldCheck className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-white">Ledger Record Verification</h4>
                    <span className="text-[10px] text-slate-500 font-mono">ID: {selectedLog.id}</span>
                  </div>
                </div>

                <div className="space-y-4 text-xs">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <span className="text-slate-500 block">Actor / Agent</span>
                      <span className="text-slate-200 font-semibold">{selectedLog.actor}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Timestamp</span>
                      <span className="text-slate-200 font-mono">{selectedLog.timestamp}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Incident Type</span>
                      <span className="text-slate-200 font-mono font-medium">{selectedLog.eventType}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">System Severity</span>
                      <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        selectedLog.riskLevel === "high" ? "bg-rose-500/10 text-rose-400" : selectedLog.riskLevel === "medium" ? "bg-amber-500/10 text-amber-400" : "bg-emerald-500/10 text-emerald-400"
                      }`}>
                        {selectedLog.riskLevel} Risk
                      </span>
                    </div>
                  </div>

                  <div className="space-y-1.5 pt-3 border-t border-slate-800/80">
                    <span className="text-slate-500 block">Transaction Details</span>
                    <p className="text-xs text-slate-300 leading-relaxed bg-slate-950 p-3 rounded-lg border border-slate-850">
                      {selectedLog.details}
                    </p>
                  </div>
                </div>

                <button
                  onClick={() => setSelectedLog(null)}
                  className="w-full py-2 bg-slate-800 hover:bg-slate-700/85 rounded-xl text-xs font-semibold text-white cursor-pointer"
                >
                  Close Record
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* SUB-VIEW 5: SYSTEM ADMIN CONTROLS */}
      {activeTab === "admin" && (
        <div id="system-admin-controls-tab" className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Controls Sliders (Left 2 columns) */}
          <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
            <div className="border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white font-display">System Underwriting Parameters</h3>
              <p className="text-xs text-slate-400 mt-0.5">Tune core scoring confidence benchmarks and RAG policy retrievers.</p>
            </div>

            {/* AI Reasoning Threshold */}
            <div className="space-y-3">
              <div className="flex justify-between items-center text-xs">
                <div>
                  <span className="font-semibold text-slate-200 block">AI Reasoning Consensus Threshold</span>
                  <p className="text-[10px] text-slate-400 mt-0.5">Minimum confidence metric required for automated direct approvals.</p>
                </div>
                <span className="text-indigo-400 font-bold text-sm font-mono">{aiThreshold}%</span>
              </div>
              <input
                type="range"
                min={50}
                max={98}
                value={aiThreshold}
                onChange={(e) => setAiThreshold(Number(e.target.value))}
                className="w-full h-1.5 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-indigo-500"
              />
              <div className="flex justify-between text-[9px] text-slate-500 font-mono">
                <span>50% (High risk fast approvals)</span>
                <span>85% (Optimal Default)</span>
                <span>98% (Extremely Strict)</span>
              </div>
            </div>

            {/* Pipeline Health stats */}
            <div className="pt-6 border-t border-slate-800 space-y-4">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Document Pipeline Health Status</h4>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-850 flex items-center justify-between">
                  <div className="space-y-1">
                    <span className="text-slate-500 block text-[10px]">OCR Parse Rate</span>
                    <span className="text-sm font-bold text-white">450 docs / min</span>
                  </div>
                  <CheckCircle className="h-5 w-5 text-emerald-400" />
                </div>

                <div className="bg-slate-950 p-4 rounded-xl border border-slate-850 flex items-center justify-between">
                  <div className="space-y-1">
                    <span className="text-slate-500 block text-[10px]">Token Latency</span>
                    <span className="text-sm font-bold text-white">124 ms average</span>
                  </div>
                  <CheckCircle className="h-5 w-5 text-emerald-400" />
                </div>

                <div className="bg-slate-950 p-4 rounded-xl border border-slate-850 flex items-center justify-between">
                  <div className="space-y-1">
                    <span className="text-slate-500 block text-[10px]">RAG Vector Cache</span>
                    <span className="text-sm font-bold text-white">99.81% hits</span>
                  </div>
                  <CheckCircle className="h-5 w-5 text-emerald-400" />
                </div>
              </div>
            </div>
          </div>

          {/* Active RAG policy documents */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col justify-between h-full">
            <div className="space-y-4">
              <div className="border-b border-slate-800 pb-3">
                <h3 className="text-sm font-bold text-white font-display">Active RAG Policy Guidelines</h3>
                <p className="text-xs text-slate-400 mt-0.5">Uploaded books parsed into vector database context.</p>
              </div>

              {/* List of policy docs */}
              <div className="space-y-3 max-h-56 overflow-y-auto pr-1">
                {ragPolicyDocs.map(doc => (
                  <div key={doc.id} className="flex justify-between items-center p-3 bg-slate-950 rounded-xl border border-slate-850 text-xs">
                    <div>
                      <span className="font-semibold text-slate-200 block">{doc.name} ({doc.version})</span>
                      <span className="text-[10px] text-slate-500 font-mono mt-0.5">{doc.activeRules} rules • Uploaded {doc.uploadDate}</span>
                    </div>

                    <button
                      type="button"
                      onClick={async () => {
                        try {
                          const res = await fetch(`http://127.0.0.1:8000/api/policy-documents/${doc.id}`, { method: "DELETE" });
                          if (res.ok) {
                            const data = await res.json();
                            setRagPolicyDocs(prev => prev.filter(d => d.id !== doc.id));
                            if (data.auditLog) {
                              onAddAuditLog({
                                actor: data.auditLog.actor,
                                eventType: data.auditLog.eventType,
                                riskLevel: data.auditLog.riskLevel as "low" | "medium" | "high",
                                details: data.auditLog.details
                              });
                            }
                          }
                        } catch (err) {
                          console.warn("Failed to delete policy doc:", err);
                        }
                      }}
                      className="p-1 text-slate-500 hover:text-rose-400 transition-colors shrink-0 cursor-pointer"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Add new policy form */}
            <form onSubmit={handleAddPolicyDoc} className="space-y-3 pt-5 border-t border-slate-800 mt-5">
              <div className="space-y-1">
                <label className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Guideline Book Name</label>
                <input
                  type="text"
                  required
                  value={newDocName}
                  onChange={(e) => setNewDocName(e.target.value)}
                  placeholder="e.g. Commercial Loan Limits 2024"
                  className="w-full bg-slate-950 border border-slate-850 hover:border-slate-800 focus:border-indigo-500 rounded-lg p-2 text-xs text-white placeholder-slate-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <label className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Version</label>
                  <input
                    type="text"
                    required
                    value={newDocVersion}
                    onChange={(e) => setNewDocVersion(e.target.value)}
                    placeholder="v1.0"
                    className="w-full bg-slate-950 border border-slate-850 hover:border-slate-800 focus:border-indigo-500 rounded-lg p-2 text-xs text-white placeholder-slate-500 focus:outline-none"
                  />
                </div>

                <div className="flex items-end">
                  <button
                    type="submit"
                    className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-xs font-bold text-white flex items-center justify-center gap-1 cursor-pointer transition-colors"
                  >
                    <Plus className="h-4 w-4" /> Upload Book
                  </button>
                </div>
              </div>
            </form>
          </div>

        </div>
      )}

    </div>
  );
}
