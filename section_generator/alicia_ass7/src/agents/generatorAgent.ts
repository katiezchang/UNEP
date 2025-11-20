import OpenAI from "openai";
import { approvedSources } from "../config/constants.js";
import * as dotenv from "dotenv";
dotenv.config();

const openai = new OpenAI({apiKey: process.env.OPENAI_API_KEY,});

export async function generateSection({
  sectionTitle,
  instructions,
  country,
  options,
}: {
  sectionTitle: string;
  instructions: string;
  country: string;
  options?: {
    noNumbering?: boolean;
  };
}): Promise<string> {
  // Base prompt: include caller instructions first, then the original, detailed structure & formatting rules
  let prompt = `
You are drafting a section for a UN Project Identification Form (PIF) under GEF8-CBIT.

Section: ${sectionTitle}
Country: ${country}

${instructions}

Your task:
Generate a polished and factual narrative section written in the formal tone and format of an official GEF8-CBIT PIF, consistent with examples such as “GEF8_PIF_Cuba_DRAFT_23.10.25.docx.” The section must read like a finalized submission, not a numbered report or outline.

Follow these detailed rules:

1. **Structure and Formatting**
  - Write in continuous prose with coherent paragraph transitions.
  - Avoid numbered headings; use bullet points or lists only when the section instructions explicitly allow them.
  - For all sections, use bold text for section titles and maintain consistent formatting similar to official GEF8 PIF examples. Bold any additional text specified in section specific instructions.
 

2. **Content and Sources**
  - Draw ONLY from the authorized and verified sources listed in ${approvedSources}
  - When citing evidence or context, include parenthetical references (e.g., “UNFCCC 2024 BTR1”, “ICAT Country Report 2023”).
  - If information is unavailable or outdated, include a clear placeholder: [Data gap: ...] and note where such data could be found.
  - Avoid speculation or unverifiable claims. Keep statements grounded in these sources.

3. **Tone and Style**
  - Maintain a formal, objective, and institutional tone matching GEF and UNFCCC documentation.
  - Write in the third person, emphasizing factual accuracy and clarity.
  - Use formal transitions between paragraphs; only use bullet lists or outlines if the section instructions explicitly state to use them.
  - Avoid redundancy, ensure consistent voice, and match the length and rhythm of real PIF sections.

4. **Length and Completeness**
  - Each section should be approximately 450–500 words.

5. **Compliance and Verification**
  - Ensure the draft reflects alignment with the Enhanced Transparency Framework (ETF) of the Paris Agreement.
  - Explicitly reference national laws, institutional frameworks, coordination mechanisms, and relevant capacity-building initiatives (e.g., GEF-CBIT, ICAT, or PATPA programs).
  - All information should be presented as final, factually verified text ready for official submission.

Return only the complete, properly formatted section narrative ready for inclusion in a GEF8 PIF.
`;

  // Append dynamic instructions based on options so callers can override structural rules
  let dynamic = "";
  if (options?.noNumbering) {
    dynamic += `\nImportant: Do NOT use numbered sections or numbered paragraphs. Use unnumbered headings and plain paragraphs or bulleted lists instead. Avoid numbering like "1.", "2.", or "1.1" anywhere in the output.`;
  }
  // Note: institutional output should be a concise bulleted "Institution: Role" list per section instructions.

  const res = await openai.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [{ role: "user", content: prompt + dynamic }],
    temperature: 0.4,
  });

  return res.choices[0].message?.content?.trim() ?? "";
}
