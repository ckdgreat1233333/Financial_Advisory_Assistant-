/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { Application, AuditLog, PolicyDocument } from "./types";

export const initialApplications: Application[] = [
  {
    id: "LX-94021-B",
    applicantName: "Nexus Logistics Inc. (Sarah Jenkins)",
    applicantEmail: "sjenkins@nexuslogistics.com",
    applicantPhone: "+1 (555) 342-9901",
    type: "business",
    status: "under_review",
    amount: 125000,
    termMonths: 36,
    progress: 75,
    submittedDate: "2023-10-18",
    interestRate: 6.8,
    riskScore: 14,
    defaultRate: 1.2,
    complianceStatus: "compliant",
    documents: [
      {
        id: "doc-1",
        name: "Chase_Oct_2023.pdf",
        type: "Bank Statement",
        status: "valid",
        uploadedAt: "2023-10-18 09:12",
        ocrFields: [
          { label: "Account Holder", doc1Value: "Sarah Jenkins", doc2Value: "Sarah Jenkins", status: "match" },
          { label: "Employer Name", doc1Value: "Nexus Logistics Inc.", doc2Value: "Nexus Logistics Inc.", status: "match" },
          { label: "Monthly Deposit Average", doc1Value: "$41,500", doc2Value: "$41,500", status: "match" },
          { label: "Tax Filing ID", doc1Value: "XX-XXX4910", doc2Value: "XX-XXX4910", status: "match" }
        ]
      },
      {
        id: "doc-2",
        name: "IRS_Form_1040_2022.pdf",
        type: "Tax Return",
        status: "valid",
        uploadedAt: "2023-10-18 09:14"
      },
      {
        id: "doc-3",
        name: "Business_License_2023.pdf",
        type: "ID & Licensing",
        status: "valid",
        uploadedAt: "2023-10-18 09:15"
      }
    ],
    reasoningNotes: "Low leverage ratio. Solid operating cash flow over the last 12 months. Tax returns correspond precisely to reported corporate earnings. Recommended for consensus approval.",
    agentConsensus: {
      documentValidation: { status: "pass", score: 98, details: "OCR extraction verified. No pixel alterations or timestamp modifications detected." },
      policyCompliance: { status: "pass", score: 100, details: "Debt-to-income (DTI) ratio is 21.4%, which is well below the threshold of 45.0%." },
      riskEvaluation: { status: "pass", score: 92, details: "Risk Score 14/100 represents extremely low defaults in Logistics sector." }
    },
    similarityHeatmap: {
      labels: ["Chase_Oct_2023.pdf", "IRS_1040_2022.pdf", "Business_Lic.pdf", "ID_Card.pdf", "Rent_Agreement.pdf"],
      matrix: [
        [1.00, 0.12, 0.08, 0.02, 0.05],
        [0.12, 1.00, 0.15, 0.01, 0.04],
        [0.08, 0.15, 1.00, 0.09, 0.11],
        [0.02, 0.01, 0.09, 1.00, 0.03],
        [0.05, 0.04, 0.11, 0.03, 1.00]
      ]
    }
  },
  {
    id: "LX-95204-S",
    applicantName: "Solaris Cloud Tech (John S. Doe)",
    applicantEmail: "jdoe@solariscloud.io",
    applicantPhone: "+1 (555) 712-4040",
    type: "business",
    status: "pending_docs",
    amount: 350000,
    termMonths: 48,
    progress: 40,
    submittedDate: "2023-10-19",
    interestRate: 7.4,
    riskScore: 48,
    defaultRate: 4.8,
    complianceStatus: "warning",
    documents: [
      {
        id: "doc-4",
        name: "Chase_Oct_2023.pdf",
        type: "Bank Statement",
        status: "mismatch",
        uploadedAt: "2023-10-19 14:22",
        ocrFields: [
          { label: "Account Holder", doc1Value: "John S. Doe", doc2Value: "Johnathan Doe", status: "warning" },
          { label: "Reported Revenue", doc1Value: "$142,500", doc2Value: "$110,000", status: "mismatch" },
          { label: "Company Name", doc1Value: "Solaris Cloud Tech", doc2Value: "Solaris Tech Corp", status: "warning" },
          { label: "EIN Reference", doc1Value: "EI-9983-X", doc2Value: "EI-9983-Y", status: "mismatch" }
        ]
      },
      {
        id: "doc-5",
        name: "IRS_Form_1040_2022.pdf",
        type: "Tax Return",
        status: "valid",
        uploadedAt: "2023-10-19 14:24"
      },
      {
        id: "doc-6",
        name: "ID_Card.pdf",
        type: "ID & Licensing",
        status: "pending",
        uploadedAt: "2023-10-19 14:25"
      }
    ],
    reasoningNotes: "Significant discrepancy detected between monthly deposits in Chase Statement and reported IRS revenues. Account name mismatch ('John S. Doe' vs 'Johnathan Doe'). Identity document requires manual review.",
    agentConsensus: {
      documentValidation: { status: "warn", score: 62, details: "Discrepancy detected in Name Spellings and Reported Revenues (Variance > 20%)." },
      policyCompliance: { status: "warn", score: 75, details: "Required Identity Card is uploaded but not verified by automated biometric check." },
      riskEvaluation: { status: "warn", score: 58, details: "Medium Risk. Volatile industry (SaaS/Tech startups) combined with documentation variances." }
    },
    similarityHeatmap: {
      labels: ["Chase_Oct_2023.pdf", "IRS_1040_2022.pdf", "ID_Card.pdf", "Co_Profile.pdf", "Tax_Schedule.pdf"],
      matrix: [
        [1.00, 0.45, 0.05, 0.18, 0.32],
        [0.45, 1.00, 0.08, 0.12, 0.40],
        [0.05, 0.08, 1.00, 0.03, 0.04],
        [0.18, 0.12, 0.03, 1.00, 0.15],
        [0.32, 0.40, 0.04, 0.15, 1.00]
      ]
    }
  },
  {
    id: "LX-92305-V",
    applicantName: "Vanguard Bio-Med",
    applicantEmail: "funding@vanguardbiomed.com",
    applicantPhone: "+1 (555) 231-1049",
    type: "business",
    status: "under_review",
    amount: 500000,
    termMonths: 60,
    progress: 90,
    submittedDate: "2023-10-15",
    interestRate: 8.5,
    riskScore: 72,
    defaultRate: 11.4,
    complianceStatus: "failed",
    documents: [
      { id: "doc-7", name: "Q3_Financial_Statement.pdf", type: "Bank Statement", status: "valid", uploadedAt: "2023-10-15 11:00" },
      { id: "doc-8", name: "Corporate_Tax_2022.pdf", type: "Tax Return", status: "mismatch", uploadedAt: "2023-10-15 11:02" }
    ],
    reasoningNotes: "High debt-to-equity leverage ratio (4.2). Industry sector exhibits a systemic slowdown. Compliance audit flagged a mismatch in corporate entity registrations.",
    agentConsensus: {
      documentValidation: { status: "warn", score: 70, details: "Corporate taxes match local files, but missing verified audited signatures." },
      policyCompliance: { status: "fail", score: 45, details: "Debt-to-equity leverage exceeds the maximum policy allowance of 3.0." },
      riskEvaluation: { status: "fail", score: 28, details: "Risk Score 72 indicates high leverage default risks." }
    }
  },
  {
    id: "LX-91148-T",
    applicantName: "Terra Maritime (Captain Marcus)",
    applicantEmail: "m.vance@terramaritime.com",
    applicantPhone: "+1 (555) 998-1111",
    type: "business",
    status: "approved",
    amount: 850000,
    termMonths: 72,
    progress: 100,
    submittedDate: "2023-10-10",
    interestRate: 5.9,
    riskScore: 31,
    defaultRate: 2.1,
    complianceStatus: "compliant",
    documents: [
      { id: "doc-9", name: "Fleet_Valuation_Report.pdf", type: "Bank Statement", status: "valid", uploadedAt: "2023-10-10 08:30" },
      { id: "doc-10", name: "IRS_Form_1120_2022.pdf", type: "Tax Return", status: "valid", uploadedAt: "2023-10-10 08:35" }
    ],
    reasoningNotes: "Outstanding asset collateralization with multi-vessel coverage. Long-term cargo contracts secure reliable cash flows. Underwriter approved unconditionally.",
    agentConsensus: {
      documentValidation: { status: "pass", score: 95, details: "Asset registries checked and cross-verified with marine transport databases." },
      policyCompliance: { status: "pass", score: 98, details: "Interest coverage ratios satisfy and surpass baseline parameters." },
      riskEvaluation: { status: "pass", score: 85, details: "Excellent tier business score. Lowest default quadrant." }
    }
  },
  {
    id: "LX-11048-A",
    applicantName: "Residential Mortgage (David & Emma Miller)",
    applicantEmail: "david.miller@gmail.com",
    applicantPhone: "+1 (555) 431-8844",
    type: "home",
    status: "under_review",
    amount: 450000,
    termMonths: 360,
    progress: 75,
    submittedDate: "2023-10-20",
    interestRate: 6.25,
    riskScore: 18,
    defaultRate: 0.9,
    complianceStatus: "compliant",
    documents: [
      { id: "doc-11", name: "Paystubs_Sept_Oct.pdf", type: "Bank Statement", status: "valid", uploadedAt: "2023-10-20 10:45" },
      { id: "doc-12", name: "W2_Form_2022.pdf", type: "Tax Return", status: "valid", uploadedAt: "2023-10-20 10:47" },
      { id: "doc-13", name: "Purchase_Agreement_Signed.pdf", type: "ID & Licensing", status: "valid", uploadedAt: "2023-10-20 10:50" }
    ],
    reasoningNotes: "Applicants possess excellent credit rating (795). Debt-to-income (DTI) ratio is 28%. Primary residence purchase. Clean appraisal documentation received.",
    agentConsensus: {
      documentValidation: { status: "pass", score: 99, details: "Employment verification confirmed electronically with Equifax WorkNumber." },
      policyCompliance: { status: "pass", score: 100, details: "Conforms strictly to Fannie Mae eligibility standards." },
      riskEvaluation: { status: "pass", score: 96, details: "Prime customer segment. Extremely low risk of delinquency." }
    }
  },
  {
    id: "LX-70412-D",
    applicantName: "Student Loan Refi (Jordan Taylor)",
    applicantEmail: "jTaylor@alumni.edu",
    applicantPhone: "+1 (555) 883-2211",
    type: "personal",
    status: "approved",
    amount: 48000,
    termMonths: 120,
    progress: 100,
    submittedDate: "2023-10-05",
    interestRate: 4.5,
    riskScore: 22,
    defaultRate: 1.5,
    complianceStatus: "compliant",
    documents: [
      { id: "doc-14", name: "Diploma_Verification.pdf", type: "ID & Licensing", status: "valid", uploadedAt: "2023-10-05 13:10" },
      { id: "doc-15", name: "Statement_Sofi_Current.pdf", type: "Bank Statement", status: "valid", uploadedAt: "2023-10-05 13:12" }
    ]
  }
];

export const initialAuditLogs: AuditLog[] = [
  {
    id: "LOG-001",
    timestamp: "2023-10-19 14:26:12",
    actor: "AI Engine v4.2",
    eventType: "OCR Document Cross-Check",
    riskLevel: "medium",
    details: "Discrepancy identified for #LX-95204-S: Revenue mismatch of $32,500 between Chase Bank Statement and 1040 Tax filings."
  },
  {
    id: "LOG-002",
    timestamp: "2023-10-19 15:30:45",
    actor: "Officer Sarah J.",
    eventType: "Manual Document Tagging",
    riskLevel: "low",
    details: "Manually flags Solaris ID document as 'Pending Biometric Verification' and sent automated SMS alert to Johnathan Doe."
  },
  {
    id: "LOG-003",
    timestamp: "2023-10-18 09:20:00",
    actor: "AI Engine v4.2",
    eventType: "Automated Policy Check",
    riskLevel: "low",
    details: "Policy engine run completed for #LX-94021-B. All thresholds (DTI, Credit, Assets) passed successfully."
  },
  {
    id: "LOG-004",
    timestamp: "2023-10-15 11:15:00",
    actor: "AI Engine v4.2",
    eventType: "automated_policy_fail",
    riskLevel: "high",
    details: "Application #LX-92305-V failed Debt-to-Equity limit check. Current: 4.2, Max Allowable: 3.0."
  },
  {
    id: "LOG-005",
    timestamp: "2023-10-10 10:00:00",
    actor: "Officer Sarah J.",
    eventType: "Underwriter Approval",
    riskLevel: "low",
    details: "Final manual sign-off for Terra Maritime loan #LX-91148-T after collateral appraisal verified."
  }
];

export const initialPolicyDocuments: PolicyDocument[] = [
  { id: "pol-1", name: "Mortgage Underwriting Guidelines", version: "v4.2", status: "active", uploadDate: "2023-08-15", activeRules: 48 },
  { id: "pol-2", name: "Commercial Loan Credit Risk Limits", version: "v3.0", status: "active", uploadDate: "2023-09-01", activeRules: 32 },
  { id: "pol-3", name: "Retail & Consumer Lending Eligibility", version: "v2.5", status: "active", uploadDate: "2023-07-20", activeRules: 24 },
  { id: "pol-4", name: "Automated Identity & Fraud Detection", version: "v1.9", status: "archived", uploadDate: "2022-12-10", activeRules: 15 }
];

export const faqData = [
  {
    question: "What documents do I need to submit to verify my income?",
    answer: "You typically need to submit your two most recent paystubs, the previous year's W-2 forms, and your IRS Form 1040 tax returns. For business loans, we require audited corporate tax records and consolidated bank statements."
  },
  {
    question: "How long does the AI Underwriting review typically take?",
    answer: "Our automated pipeline screens documents in real-time. Within 15 minutes, OCR extraction and initial policy verification are complete. A final underwriter confirmation usually takes between 12 to 24 business hours."
  },
  {
    question: "What does the status 'Pending Docs' indicate?",
    answer: "This indicates our compliance engine or loan officer identified a mismatch, missing page, or unreadable upload. Check the alerts on your dashboard or look out for an email requesting specific files."
  },
  {
    question: "Is my personal financial information stored securely?",
    answer: "Absolutely. All documents are encrypted in transit and at rest. Access is controlled through military-grade multi-role authentication systems and audited strictly via immutable system ledgers."
  },
  {
    question: "Can I apply for multiple loans simultaneously?",
    answer: "Yes, you can track multiple loans of different categories (e.g. mortgage and business credit line) within your single Customer Portal."
  }
];
