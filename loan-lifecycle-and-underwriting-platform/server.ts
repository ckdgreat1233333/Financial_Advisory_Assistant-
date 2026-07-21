/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import express from "express";
import path from "path";
import dotenv from "dotenv";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI } from "@google/genai";

dotenv.config();

// Initialize the GoogleGenAI client using the correct named parameter style.
// API key is sourced server-side from process.env.GEMINI_API_KEY.
const getAiClient = () => {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    console.warn("WARNING: GEMINI_API_KEY is not defined. AI features will fallback to offline responses.");
    return null;
  }
  return new GoogleGenAI({
    apiKey: apiKey,
    httpOptions: {
      headers: {
        "User-Agent": "aistudio-build"
      }
    }
  });
};

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json());

  // API 1: Healthcheck
  app.get("/api/health", (req, res) => {
    res.json({ status: "healthy", timestamp: new Date() });
  });

  // API 2: RAG AI Assistant Chatbot Proxy
  app.post("/api/chat", async (req, res) => {
    try {
      const { message, history, applicationsContext } = req.body;
      
      const ai = getAiClient();
      if (!ai) {
        // Fallback offline response if no API key is specified
        return res.json({
          text: `[OFFLINE FALLBACK] Your query: "${message}". I noticed that you are asking about your loan applications. Under 'Doc Policy v4.2 Subsection B' regarding income discrepancy margins, any variance exceeding 10.0% between bank statements and tax filings triggers a verification request. Currently, Solaris Cloud Tech exhibits a $32,500 revenue mismatch ($142,500 vs $110,000). Please upload a corrected IRS 1040 form or contact support.`,
          reasoning: "No server-side GEMINI_API_KEY detected. Dispatched offline rule-based compliance match.",
          policyGrounding: {
            documentName: "Income Discrepancy Margin Clause 12.2b",
            clause: "Doc Policy v4.2 - Subsection B",
            extractedText: "Any discrepancy between monthly bank deposits and IRS tax returns exceeding 10.0% of total variance must flag a secondary Document Verification request."
          }
        });
      }

      const appsContextStr = JSON.stringify(applicationsContext, null, 2);

      const systemInstruction = `
You are the LendSmart AI Underwriting Assistant, an expert corporate and retail lending credit analyst chatbot.
Your tone is highly professional, compliant, objective, and clear. Avoid casual slang or emojis.

CREDIT ELIGIBILITY RULES CONTEXT:
1. Residential Mortgage:
   - Max Debt-to-Income (DTI) ratio allowed: 45%.
   - Required docs: bank statements, tax returns (Form 1040), W-2, signed Purchase Agreement.
2. Commercial/Business Loans:
   - Max Debt-to-Equity leverage ratio: 3.0.
   - Required docs: commercial bank statements, corporate tax returns.
3. Income Discrepancy Margin Clause 12.2b (Doc Policy v4.2 - Subsection B):
   - "Any discrepancy between monthly bank deposits and IRS tax returns exceeding 10.0% of total variance must flag a secondary Document Verification request."

CURRENT USER'S REAL-TIME APPLICATIONS CONTEXT:
${appsContextStr}

YOUR INSTRUCTIONS:
- Search the user's application context to find matches.
- If the user asks about why a loan is flagged, pending docs, or under review, perform a direct calculation and explain the exact mismatch or policy violation.
- For example, if they ask about Solaris Cloud Tech (#LX-95204-S), explain that their bank statement reports monthly averages of $142,500 but their tax returns list $110,000. Highlight that this 22.8% variance exceeds the 10.0% tolerance threshold, triggering a pending docs warning.
- Always conclude with the precise regulatory or policy document grounded.
`;

      const contents = [
        { role: "user", parts: [{ text: `System Instruction: ${systemInstruction}` }] }
      ];

      if (history && Array.isArray(history)) {
        history.forEach(h => {
          contents.push({
            role: h.role === "user" ? "user" : "model",
            parts: [{ text: h.text }]
          });
        });
      }

      contents.push({
        role: "user",
        parts: [{ text: message }]
      });

      const response = await ai.models.generateContent({
        model: "gemini-3.5-flash",
        contents: contents,
        config: {
          temperature: 0.2,
          responseMimeType: "application/json",
          responseSchema: {
            type: "OBJECT",
            properties: {
              text: { type: "STRING", description: "The professional, detailed response." },
              reasoning: { type: "STRING", description: "A short, 1-sentence description of the AI agent's internal analysis steps." },
              policyGrounding: {
                type: "OBJECT",
                properties: {
                  documentName: { type: "STRING" },
                  clause: { type: "STRING" },
                  extractedText: { type: "STRING" }
                },
                required: ["documentName", "clause", "extractedText"]
              }
            },
            required: ["text", "reasoning", "policyGrounding"]
          }
        }
      });

      const responseText = response.text || "{}";
      const parsedData = JSON.parse(responseText.trim());

      res.json(parsedData);
    } catch (err: any) {
      console.error("Gemini API Error in Server:", err);
      res.status(500).json({ error: "Underwriting API processing failure: " + err.message });
    }
  });

  // Serve static UI assets
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa"
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`LendSmart custom Express + Vite server active on port ${PORT}`);
  });
}

startServer();
