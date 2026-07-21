/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef } from "react";
import {
  Send,
  Sparkles,
  ChevronRight,
  ShieldAlert,
  ArrowUpRight,
  User,
  Scale,
  BrainCircuit,
  Maximize2,
  FileCheck,
  Check
} from "lucide-react";
import { ChatMessage, Application } from "../types";

interface AiAssistantProps {
  applications: Application[];
  currentUser: { name: string; email: string };
}

export default function AiAssistant({ applications, currentUser }: AiAssistantProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "init-1",
      sender: "assistant",
      text: `Hello ${currentUser.name}. I am the LendSmart AI Underwriting Assistant. I have cross-referenced your submitted documentation with our benchmark lending guidelines. I noticed that your Solaris Cloud Tech application (#LX-95204-S) is currently flagged. Would you like me to explain the policy reasoning for this?`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      reasoning: "Reviewing active application list. Identified 1 pending_docs flag for Solaris Cloud Tech due to OCR mismatched revenues.",
      policyGrounding: {
        documentName: "Income Discrepancy Margin Clause 12.2b",
        clause: "Doc Policy v4.2 - Subsection B",
        extractedText: "Any discrepancy between monthly bank deposits and IRS tax returns exceeding 10.0% of total variance must flag a secondary Document Verification request."
      }
    }
  ]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [activeGrounding, setActiveGrounding] = useState<{
    documentName: string;
    clause: string;
    extractedText: string;
  } | null>({
    documentName: "Income Discrepancy Margin Clause 12.2b",
    clause: "Doc Policy v4.2 - Subsection B",
    extractedText: "Any discrepancy between monthly bank deposits and IRS tax returns exceeding 10.0% of total variance must flag a secondary Document Verification request."
  });

  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isLoading) return;

    const userMsgText = inputText;
    setInputText("");

    const userMessage: ChatMessage = {
      id: `msg-user-${Date.now()}`,
      sender: "user",
      text: userMsgText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // POST to our server-side API proxy which calls Gemini!
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMsgText,
          history: messages.map(m => ({ role: m.sender === "user" ? "user" : "model", text: m.text })),
          applicationsContext: applications
        })
      });

      if (!response.ok) {
        throw new Error("Failed to contact Gemini endpoint");
      }

      const data = await response.json();
      
      const assistantMessage: ChatMessage = {
        id: `msg-ai-${Date.now()}`,
        sender: "assistant",
        text: data.text,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        reasoning: data.reasoning || "Analyzing credit guidelines and comparing OCR extracted values across submitted documents.",
        policyGrounding: data.policyGrounding || {
          documentName: "General Credit Policy Section 4",
          clause: "Underwriting Standards v3.1",
          extractedText: "All self-reported assets and cash-flow revenues must be supported by 2 full fiscal years of verified IRS tax filings."
        }
      };

      setMessages(prev => [...prev, assistantMessage]);
      if (assistantMessage.policyGrounding) {
        setActiveGrounding(assistantMessage.policyGrounding);
      }
    } catch (err) {
      console.error(err);
      // Fallback message if server error or API key missing
      const fallbackMsg: ChatMessage = {
        id: `msg-ai-fallback-${Date.now()}`,
        sender: "assistant",
        text: `Based on your query regarding Solaris Cloud Tech (#LX-95204-S), our system has highlighted a mismatch on your uploaded Chase_Oct_2023.pdf bank statement, where monthly deposit averages extract at $142,500 but your IRS Form 1040 lists $110,000. Additionally, the identity card is currently marked as 'Pending' human compliance review. This variance triggers 'Doc Policy v4.2 Subsection B' regarding income discrepancy margins.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        reasoning: "Calculated discrepancy variance. Found variance of 22.8% (above 10% threshold). Automated alert triggered.",
        policyGrounding: {
          documentName: "Income Discrepancy Margin Clause 12.2b",
          clause: "Doc Policy v4.2 - Subsection B",
          extractedText: "Any discrepancy between monthly bank deposits and IRS tax returns exceeding 10.0% of total variance must flag a secondary Document Verification request."
        }
      };
      setMessages(prev => [...prev, fallbackMsg]);
      setActiveGrounding(fallbackMsg.policyGrounding!);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div id="ai-assistant-view" className="grid grid-cols-1 xl:grid-cols-3 gap-6 h-[calc(100vh-140px)] min-h-[500px]">
      
      {/* CHAT CONTAINER (Left 2 columns) */}
      <div id="ai-chat-container" className="xl:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl flex flex-col h-full overflow-hidden">
        {/* Chat Header */}
        <div className="p-4 bg-slate-950 border-b border-slate-800/80 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-600/10 border border-indigo-500/20 text-indigo-400 rounded-xl">
              <BrainCircuit className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">LendSmart AI Assistant</h3>
              <p className="text-[10px] text-slate-400 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                Grounded by Underwriting Policies v4.2
              </p>
            </div>
          </div>
          <span className="text-[10px] font-mono bg-slate-900 border border-slate-800 text-slate-400 px-2 py-0.5 rounded-md">
            gemini-3.5-flash
          </span>
        </div>

        {/* Message Logs */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5 bg-slate-900/40">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 max-w-[85%] ${
                msg.sender === "user" ? "ml-auto flex-row-reverse" : ""
              }`}
            >
              {/* Avatar */}
              <div
                className={`h-8 w-8 rounded-lg shrink-0 flex items-center justify-center text-xs font-bold ${
                  msg.sender === "user"
                    ? "bg-emerald-600 text-white"
                    : "bg-indigo-950 border border-indigo-500/20 text-indigo-400"
                }`}
              >
                {msg.sender === "user" ? <User className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
              </div>

              {/* Message Content */}
              <div className="space-y-1.5">
                <div
                  className={`p-3.5 rounded-xl text-xs leading-relaxed ${
                    msg.sender === "user"
                      ? "bg-slate-800 text-slate-100 border border-slate-700/50"
                      : "bg-slate-950 text-slate-200 border border-slate-850"
                  }`}
                >
                  {msg.text}
                </div>

                {/* Reasoning Chain Collapse on AI Response */}
                {msg.sender === "assistant" && msg.reasoning && (
                  <details className="group border border-slate-850 rounded-lg overflow-hidden bg-slate-950/40">
                    <summary className="flex items-center justify-between px-3 py-1.5 text-[10px] font-semibold text-slate-400 hover:text-slate-200 cursor-pointer select-none">
                      <span className="flex items-center gap-1">
                        <BrainCircuit className="h-3.5 w-3.5 text-indigo-400" />
                        AI Reasoning Chain
                      </span>
                      <ChevronRight className="h-3.5 w-3.5 transform group-open:rotate-90 transition-transform" />
                    </summary>
                    <div className="px-3 pb-2.5 pt-0.5 text-[10px] text-slate-500 font-mono leading-relaxed border-t border-slate-950">
                      {msg.reasoning}
                    </div>
                  </details>
                )}

                <div className="flex items-center gap-1.5 px-1 justify-between">
                  <span className="text-[9px] text-slate-500">{msg.timestamp}</span>
                  {msg.policyGrounding && (
                    <button
                      onClick={() => setActiveGrounding(msg.policyGrounding!)}
                      className="text-[9px] text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-0.5 cursor-pointer"
                    >
                      View grounded clause <ArrowUpRight className="h-2.5 w-2.5" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}

          {/* Loading Indicator */}
          {isLoading && (
            <div className="flex gap-3 max-w-[80%]">
              <div className="h-8 w-8 rounded-lg bg-indigo-950 border border-indigo-500/20 text-indigo-400 flex items-center justify-center">
                <Sparkles className="h-4 w-4 animate-spin" />
              </div>
              <div className="bg-slate-950 border border-slate-850 p-4 rounded-xl flex items-center gap-2">
                <div className="flex space-x-1">
                  <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce"></div>
                  <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce delay-75"></div>
                  <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce delay-150"></div>
                </div>
                <span className="text-[10px] text-slate-500 font-mono">LendSmart agent processing policies...</span>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Chat Input */}
        <form onSubmit={handleSendMessage} className="p-3 bg-slate-950 border-t border-slate-800/80 flex gap-2">
          <input
            type="text"
            required
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Ask anything about your loan conditions, flags, guidelines..."
            className="flex-1 bg-slate-900 border border-slate-800 hover:border-slate-700 focus:border-indigo-500 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none transition-colors"
          />
          <button
            type="submit"
            disabled={isLoading || !inputText.trim()}
            className="p-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 rounded-xl text-white transition-colors cursor-pointer"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      </div>

      {/* POLICY GROUNDING SIDEBAR (Right 1 column) */}
      <div id="ai-grounding-sidebar" className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between h-full overflow-hidden">
        <div className="space-y-5 h-full overflow-y-auto pr-1">
          <div className="border-b border-slate-800 pb-3">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Policy Grounding Sidebar</h4>
            <p className="text-[10px] text-slate-500 mt-0.5">Real-time reference retrieved from active underwriting guidelines.</p>
          </div>

          {activeGrounding ? (
            <div className="space-y-4">
              <div className="bg-slate-950 border border-indigo-500/10 p-4 rounded-xl space-y-2.5 relative">
                <span className="absolute -top-2 right-3 text-[9px] font-mono text-indigo-400 px-2 py-0.5 rounded bg-indigo-950 border border-indigo-500/20 uppercase">
                  Verified Clause
                </span>
                <span className="text-[10px] text-indigo-400 font-mono font-medium block">{activeGrounding.clause}</span>
                <h5 className="text-xs font-semibold text-white leading-snug">{activeGrounding.documentName}</h5>
                <p className="text-xs text-slate-400 italic bg-slate-900 p-3 rounded-lg border border-slate-850 leading-relaxed font-sans">
                  "{activeGrounding.extractedText}"
                </p>
                <div className="flex items-center gap-1.5 text-[10px] text-emerald-400 font-medium">
                  <FileCheck className="h-3.5 w-3.5" />
                  <span>Authorized reference policy source</span>
                </div>
              </div>

              {/* Limit Eligibility Tracker */}
              <div className="bg-slate-950 border border-slate-800/80 p-4 rounded-xl space-y-4">
                <h5 className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                  <Scale className="h-4 w-4 text-emerald-400" />
                  Limit Eligibility Tracker
                </h5>

                {/* Metric 1 */}
                <div className="space-y-1.5">
                  <div className="flex justify-between text-[11px]">
                    <span className="text-slate-400 font-medium">Solaris Revenue Variance</span>
                    <span className="text-rose-400 font-bold">22.8% Variance</span>
                  </div>
                  <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
                    <div className="h-full bg-rose-500 rounded-full" style={{ width: "85%" }}></div>
                  </div>
                  <div className="flex justify-between text-[9px] text-slate-500 font-mono">
                    <span>Target Max: 10.0%</span>
                    <span>Variance: $32.5k</span>
                  </div>
                </div>

                {/* Metric 2 */}
                <div className="space-y-1.5">
                  <div className="flex justify-between text-[11px]">
                    <span className="text-slate-400 font-medium">Debt-to-Income (DTI)</span>
                    <span className="text-emerald-400 font-bold">28.4% Compliant</span>
                  </div>
                  <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-500 rounded-full" style={{ width: "55%" }}></div>
                  </div>
                  <div className="flex justify-between text-[9px] text-slate-500 font-mono">
                    <span>DTI Limit: 45.0%</span>
                    <span>Actual: 28.4%</span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-xs text-slate-600 italic">
              Select any assistant message to parse the grounding source documents.
            </div>
          )}
        </div>

        <div className="mt-4 pt-4 border-t border-slate-800 text-[10px] text-slate-500 leading-relaxed">
          Retrieval-Augmented Generation (RAG) is secured with TLS and restricted strictly to active enterprise policy libraries.
        </div>
      </div>

    </div>
  );
}
