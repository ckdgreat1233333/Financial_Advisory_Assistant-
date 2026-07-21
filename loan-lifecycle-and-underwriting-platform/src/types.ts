/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export type LoanType = "home" | "auto" | "personal" | "business";

export type ApplicationStatus = "under_review" | "pending_docs" | "approved" | "rejected" | "draft";

export interface OCRField {
  label: string;
  doc1Value: string;
  doc2Value: string;
  status: "match" | "mismatch" | "warning";
}

export interface DocumentVerification {
  id: string;
  name: string;
  type: string;
  status: "valid" | "mismatch" | "pending" | "missing";
  uploadedAt?: string;
  ocrFields?: OCRField[];
}

export interface Application {
  id: string;
  applicantName: string;
  applicantEmail: string;
  applicantPhone?: string;
  type: LoanType;
  status: ApplicationStatus;
  amount: number;
  termMonths: number;
  progress: number; // 0 to 100
  submittedDate: string;
  interestRate: number;
  riskScore: number; // 0 to 100
  defaultRate: number; // 0 to 100 (percentage)
  complianceStatus: "compliant" | "warning" | "failed";
  documents: DocumentVerification[];
  reasoningNotes?: string;
  agentConsensus?: {
    documentValidation: { status: "pass" | "warn" | "fail"; score: number; details: string };
    policyCompliance: { status: "pass" | "warn" | "fail"; score: number; details: string };
    riskEvaluation: { status: "pass" | "warn" | "fail"; score: number; details: string };
  };
  similarityHeatmap?: {
    labels: string[];
    matrix: number[][]; // N x N values
  };
}

export interface AuditLog {
  id: string;
  timestamp: string;
  actor: string;
  eventType: string;
  riskLevel: "low" | "medium" | "high";
  details: string;
}

export interface PolicyDocument {
  id: string;
  name: string;
  version: string;
  status: "active" | "archived";
  uploadDate: string;
  activeRules: number;
}

export interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  timestamp: string;
  reasoning?: string;
  policyGrounding?: {
    documentName: string;
    clause: string;
    extractedText: string;
  };
}
