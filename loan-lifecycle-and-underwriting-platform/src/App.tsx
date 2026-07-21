import { useState, useEffect } from "react";
import { ShieldCheck, LogOut, Sparkles } from "lucide-react";
import AuthPage from "./components/AuthPage";
import CustomerDashboard from "./components/CustomerDashboard";
import OfficerDashboard from "./components/OfficerDashboard";
import AiAssistant from "./components/AiAssistant";
import { Application, AuditLog } from "./types";

const API_BASE = "http://127.0.0.1:8000";

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [currentUser, setCurrentUser] = useState<{
    role: "customer" | "officer";
    email: string;
    name: string;
    phone?: string;
  } | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [customerActiveView, setCustomerActiveView] = useState<"dashboard" | "ai_assistant">("dashboard");

  const fetchData = async () => {
    setLoading(true);
    try {
      const [appsRes, logsRes] = await Promise.all([
        fetch(`${API_BASE}/api/applications`),
        fetch(`${API_BASE}/api/audit-logs`),
      ]);
      if (appsRes.ok) {
        const appsData = await appsRes.json();
        setApplications(appsData.applications || []);
      }
      if (logsRes.ok) {
        const logsData = await logsRes.json();
        setAuditLogs(logsData.logs || []);
      }
    } catch (err) {
      console.warn("Backend unavailable, using empty state:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isLoggedIn) {
      fetchData();
    }
  }, [isLoggedIn]);

  const handleLogin = (role: "customer" | "officer", email: string, name: string) => {
    setCurrentUser({ role, email, name });
    setIsLoggedIn(true);
    setCustomerActiveView("dashboard");
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setCurrentUser(null);
    setApplications([]);
    setAuditLogs([]);
  };

  const handleApplyNewLoan = async (newAppData: Partial<Application>) => {
    try {
      const res = await fetch(`${API_BASE}/api/applications`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          applicantName: newAppData.applicantName || "Applicant",
          applicantEmail: newAppData.applicantEmail || "applicant@email.com",
          applicantPhone: newAppData.applicantPhone || "",
          type: newAppData.type || "home",
          amount: newAppData.amount || 150000,
          termMonths: newAppData.termMonths || 360,
          interestRate: newAppData.interestRate || 6.5,
          documents: newAppData.documents || [],
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setApplications((prev) => [data.application, ...prev]);
        if (data.auditLog) {
          setAuditLogs((prev) => [data.auditLog, ...prev]);
        }
      }
    } catch (err) {
      console.warn("Failed to create application:", err);
    }
  };

  const handleUpdateProfile = async (name: string, email: string, phone: string) => {
    if (currentUser) {
      try {
        await fetch(`${API_BASE}/api/users/profile`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, email, phone }),
        });
      } catch (err) {
        console.warn("Failed to update profile:", err);
      }
      setCurrentUser({ ...currentUser, name, email, phone });
    }
  };

  const handleApproveApp = async (id: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/applications/${id}/approve`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ actor: currentUser?.name || "Officer", reason: "" }),
      });
      if (res.ok) {
        const data = await res.json();
        setApplications((prev) => prev.map((app) => (app.id === id ? data.application : app)));
        if (data.auditLog) {
          setAuditLogs((prev) => [data.auditLog, ...prev]);
        }
      }
    } catch (err) {
      console.warn("Failed to approve application:", err);
    }
  };

  const handleRejectApp = async (id: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/applications/${id}/reject`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ actor: currentUser?.name || "Officer", reason: "Rejected by officer" }),
      });
      if (res.ok) {
        const data = await res.json();
        setApplications((prev) => prev.map((app) => (app.id === id ? data.application : app)));
        if (data.auditLog) {
          setAuditLogs((prev) => [data.auditLog, ...prev]);
        }
      }
    } catch (err) {
      console.warn("Failed to reject application:", err);
    }
  };

  const handleAddAuditLog = async (logData: Omit<AuditLog, "id" | "timestamp">) => {
    try {
      const res = await fetch(`${API_BASE}/api/audit-logs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(logData),
      });
      if (res.ok) {
        const newLog = await res.json();
        setAuditLogs((prev) => [newLog, ...prev]);
      }
    } catch (err) {
      console.warn("Failed to create audit log:", err);
    }
  };

  const handleUpdateAppDocs = async (appId: string, docId: string, status: "valid" | "mismatch") => {
    try {
      const res = await fetch(`${API_BASE}/api/applications/${appId}/documents/${docId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (res.ok) {
        const updated = await res.json();
        setApplications((prev) => prev.map((app) => (app.id === appId ? updated : app)));
      }
    } catch (err) {
      console.warn("Failed to update document status:", err);
    }
  };

  if (!isLoggedIn || !currentUser) {
    return <AuthPage onLogin={handleLogin} />;
  }

  return (
    <div id="app-root-shell" className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <header id="global-header" className="bg-slate-900 border-b border-slate-800/80 sticky top-0 z-40 shrink-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-600 rounded-xl text-white shadow shadow-emerald-950/40">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-sm font-extrabold font-display tracking-tight text-white flex items-center gap-1.5 leading-none">
                LendSmart <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 font-mono font-medium">AI</span>
              </h1>
              <p className="text-[9px] text-slate-400 mt-0.5 leading-none">Secure Smarter Underwriting</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden sm:flex items-center gap-2.5 bg-slate-950 border border-slate-800/60 px-3 py-1.5 rounded-xl">
              <span className={`h-2 w-2 rounded-full ${currentUser.role === "officer" ? "bg-indigo-400" : "bg-emerald-400"}`}></span>
              <div className="text-left leading-none">
                <span className="text-xs font-semibold text-white block">{currentUser.name}</span>
                <span className="text-[9px] text-slate-500 block mt-0.5 uppercase tracking-wider font-mono">
                  {currentUser.role === "officer" ? "Underwriter Officer" : "Customer Portal"}
                </span>
              </div>
            </div>

            {currentUser.role === "customer" && (
              <div className="flex bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
                <button
                  onClick={() => setCustomerActiveView("dashboard")}
                  className={`px-3 py-1 rounded-lg font-medium transition-colors cursor-pointer ${
                    customerActiveView === "dashboard" ? "bg-slate-850 text-white" : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Dashboard
                </button>
                <button
                  onClick={() => setCustomerActiveView("ai_assistant")}
                  className={`px-3 py-1 rounded-lg font-medium flex items-center gap-1 transition-colors cursor-pointer ${
                    customerActiveView === "ai_assistant" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <Sparkles className="h-3 w-3" />
                  Ask AI
                </button>
              </div>
            )}

            <button
              onClick={handleLogout}
              className="p-2 bg-slate-850 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white rounded-xl transition-colors cursor-pointer"
              title="Sign Out of Portal"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </header>

      <main id="global-main-container" className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-slate-400 text-sm">Loading data from backend...</div>
          </div>
        ) : currentUser.role === "customer" ? (
          customerActiveView === "dashboard" ? (
            <CustomerDashboard
              applications={applications}
              onApplyLoan={handleApplyNewLoan}
              onUpdateProfile={handleUpdateProfile}
              currentUser={currentUser}
              onNavigateToChat={() => setCustomerActiveView("ai_assistant")}
            />
          ) : (
            <AiAssistant applications={applications} currentUser={currentUser} />
          )
        ) : (
          <OfficerDashboard
            applications={applications}
            auditLogs={auditLogs}
            onApproveApplication={handleApproveApp}
            onRejectApplication={handleRejectApp}
            onAddAuditLog={handleAddAuditLog}
            onUpdateApplicationDocs={handleUpdateAppDocs}
          />
        )}
      </main>

      <footer id="global-footer" className="bg-slate-950 border-t border-slate-900 py-4 px-8 text-center text-[10px] text-slate-600 shrink-0">
        <p>2026 LendSmart AI Corp. All Rights Reserved. SOC-2 Certified  Federal Reserve compliant system ledger.</p>
      </footer>
    </div>
  );
}
