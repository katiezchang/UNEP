import OpenAI from "openai";
import { approvedSources } from "../config/constants.js";
import * as dotenv from "dotenv";
import path from "path";
import { fileURLToPath } from "url";

// Get the directory of the current file
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load .env file from the project root (two levels up from dist/agents/)
dotenv.config({ path: path.resolve(__dirname, "../../.env") });

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
export async function verifyAndReviseSection(sectionDraft, sectionTitle, country) {
    const verifyPrompt = `
You are an accuracy and compliance reviewer for GEF8-CBIT Project Identification Forms.

Task: Review and fact-check the draft section below.

Section: ${sectionTitle}
Country: ${country}

Sources allowed:
${approvedSources}

Instructions:
1. Check that all claims can be verified from these sources and are recent (<5 years).
2. Mark unverifiable parts with [Data gap: …] or [Verify: …].
3. Revise the section for factual accuracy and clarity.
4. **For the "Institutional Framework for Climate Action" section ONLY:** Ensure the section consists of three parts: (a) an introductory paragraph describing the national legal and institutional foundation for climate governance, identifying the lead ministry/agency responsible for UNFCCC reporting, and ending with a transition statement; (b) an explicit bulleted list of institutions with their roles, where each bullet starts with '- ' followed by **bolded institution name (Acronym)** [English translation]: one-sentence role description; (c) a concluding paragraph summarizing the significance of this institutional framework for national sustainability, climate resilience, and transparency. REMOVE any references to laws or institutions that are older than 5 years (e.g., Ley No. 81 from 1997). Keep all recent and verifiable institutions. If the draft contains institutions embedded in running paragraphs rather than as explicit bullets, extract them and convert into the bulleted format. Ensure each institution gets its own separate bullet line with a concise 1-sentence description.
5. **For the "National Policy Framework" section ONLY:** Ensure that each law, decree, plan, or strategy is presented as a SEPARATE, DISTINCT bullet point. Do NOT combine multiple policies into one bullet. Do NOT embed policies in paragraphs. Each bullet MUST start with '- ' followed by **bolded policy name with year** and a colon, then 1–3 sentence description of objectives and focus areas. Focus ONLY on the laws, policies, decrees, and strategies themselves—NOT on institutional roles or organizational structures. Include policies from approved sources (UNFCCC, ICAT, PATPA, GEF/CBIT, country's national website). Prioritize recent policies (2020-2025) but include foundational climate policies from approved sources that are still in force (such as NDCs, foundational decrees, or strategic plans). If the draft contains policies embedded in running paragraphs or combined bullets, extract them and convert each to its own separate bullet line. Maintain the format: '- **Policy Name (Year):** Description.' Include the country's key climate policy instruments that can be verified from approved sources.
6. Preserve formatting requested in the section instructions: if the section calls for a bullet list, keep that exact bullet formatting.
7. Preserve inline Markdown bold markers (e.g., **Law Name**) when present.
8. Preserve all "STANDARD TEXT TO BE INCLUDED" segments exactly.
9. Output corrected text + short "Fact-Check Summary:" at end.

Draft Section:
---
${sectionDraft}
---
`;
    const res = await openai.chat.completions.create({
        model: "gpt-4o-mini",
        messages: [{ role: "user", content: verifyPrompt }],
        temperature: 0.2,
    });
    return res.choices[0].message?.content?.trim() ?? "";
}
