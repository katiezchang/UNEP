import OpenAI from "openai";
import { approvedSources } from "../config/constants.js";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

export async function verifyAndReviseSection(
  sectionDraft: string,
  sectionTitle: string,
  country: string
): Promise<string> {
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
4. Preserve all “STANDARD TEXT TO BE INCLUDED” segments exactly.
5. Output corrected text + short "Fact-Check Summary:" at end.

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
