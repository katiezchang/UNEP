/**
 * ============================================================
 *  GEF-8 PIF Section Generator — Aathma Muruganathan
 *  ------------------------------------------------------------
 *  Sections handled:
 *    1. Climate Transparency in [Country]
 *    2. Official reporting to the UNFCCC
 *    3. Key barriers
 *  Countries handled: Jordan and Cuba
 *
 *  Format and logic align exactly with assignment specification:
 *   - Uses async generateSectionParagraph() structure
 *   - ≥400 words per section
 *   - Includes “STANDARD TEXT TO BE INCLUDED … END”
 *   - Draws only from approved sources (UNFCCC, ICAT, PATPA, GEF)
 *   - Explicitly flags “MISSING:” with URL paths when info absent
 *   - Saves outputs per section/country under /out
 * ============================================================
 */

import fs from "fs";
import path from "path";
import { generateText } from "ai"; // same lib used elsewhere in repo

// Ensure output directory exists
const OUT_DIR = path.resolve("out");
if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

// ---------------------------------------------------------------------------
// Core generic generator — EXACT format required by the assignment
// ---------------------------------------------------------------------------
async function generateSectionParagraph({
  sectionTitle,
  instructions,
  country,
}: {
  sectionTitle: string;
  instructions: string;
  country: string;
}): Promise<string> {
  const prompt = `
You are drafting a section for a UN Project Information Form (PIF).

Section: ${sectionTitle}
Country: ${country}

Return a professional, concise, and informative essay with a minimum of 400 words written in the style of international project documents.
Keep the structure of the document exactly the same as in the GEF-8 PIF Template.
Use only these sources:
– UNFCCC reports portal (BTR/NC/BUR/NIR for the country): https://unfccc.int/reports
– ICAT (climateactiontransparency.org) country pages/reports
– PATPA (transparency-partnership.net) Good Practice Database
– GEF/CBIT documents on https://www.thegef.org/projects-operations/database
– The country’s official environment ministry website

If required information is missing, say so explicitly and point to the specific PDF/URL within these sites where it likely exists.
No hallucinations.
Follow the PIF template’s wording, length limits, and tone for each section.

${instructions}

Make sure to include all “STANDARD TEXT TO BE INCLUDED” verbatim where relevant.
STANDARD TEXT TO BE INCLUDED END.
  `.trim();

  const result = await generateText({
    model: openai("gpt-4o-mini"),
    prompt,
  });

  const text = (result.text || "").trim();
  return text;
}

// ---------------------------------------------------------------------------
// Tailored generators for Aathma’s three sections
// ---------------------------------------------------------------------------
async function sectionClimateTransparency(country: string) {
  return generateSectionParagraph({
    sectionTitle: `Climate Transparency in ${country}`,
    instructions: `Summarize the status, context, recent progress, and remaining challenges related to climate transparency and the transparency framework in ${country}.
Reference Nationally Determined Contribution (NDC) implementation, Biennial Transparency Reports (BTRs), and Enhanced Transparency Framework (ETF) progress.
Describe what has been done to date, identify remaining institutional or data challenges, and explain what would happen without this project (simple future narrative referencing population, economic, and climate drivers).`,
    country,
  });
}

async function sectionOfficialReporting(country: string) {
  return generateSectionParagraph({
    sectionTitle: `Official reporting to the UNFCCC`,
    instructions: `List the recommendations and observations from ${country}’s latest or ongoing National Communications (NCs), Biennial Update Reports (BURs), or Biennial Transparency Reports (BTRs),
as well as findings from International Consultation and Analysis (ICA) or Technical Expert Reviews.
Summarize the main capacity gaps and recommendations that can be addressed by the CBIT/GEF project scope, following the table structure in the PIF template (Year / Report / Comments).`,
    country,
  });
}

async function sectionKeyBarriers(country: string) {
  return generateSectionParagraph({
    sectionTitle: `Key barriers`,
    instructions: `Summarize the key barriers preventing ${country} from fully meeting Enhanced Transparency Framework (ETF) requirements, grouped under the three standard categories in the PIF template:
1) Lack of systematic climate-data organization and institutional protocols.
2) Incomplete ETF modules (GHG Inventory, Adaptation/Vulnerability, NDC Tracking, Support Needed & Received).
3) Dependence on project-based financing and external consultants for reporting.
Provide 1–2 paragraphs under each barrier heading using evidence from allowed sources and reference “STANDARD TEXT TO BE INCLUDED” verbatim.`,
    country,
  });
}

// ---------------------------------------------------------------------------
// Utility: save text to /out/<Country>_<Section>.txt
// ---------------------------------------------------------------------------
function saveOutput(country: string, title: string, content: string) {
  const safe = title.replace(/\s+/g, "_").replace(/[^a-zA-Z0-9_]/g, "");
  const filePath = path.join(OUT_DIR, `${country}_${safe}.txt`);
  fs.writeFileSync(filePath, content, "utf8");
  console.log(`💾 Saved: ${filePath}`);
}

// ---------------------------------------------------------------------------
// Main execution loop
// ---------------------------------------------------------------------------
async function runAll() {
  const countries = ["Jordan", "Cuba"];
  for (const country of countries) {
    console.log(`\n==============================`);
    console.log(`🟢 Generating sections for ${country}`);
    console.log(`==============================`);

    const outputs: Record<string, string> = {};

    outputs["Climate Transparency"] = await sectionClimateTransparency(country);
    saveOutput(country, "Climate_Transparency", outputs["Climate Transparency"]);

    outputs["Official Reporting"] = await sectionOfficialReporting(country);
    saveOutput(country, "Official_Reporting", outputs["Official Reporting"]);

    outputs["Key Barriers"] = await sectionKeyBarriers(country);
    saveOutput(country, "Key_Barriers", outputs["Key Barriers"]);

    // Combine all three into one compiled doc for convenience
    const compiledPath = path.join(OUT_DIR, `${country}_Aathma_PIF.txt`);
    const combined = Object.entries(outputs)
      .map(([k, v]) => `### ${k}\n\n${v}`)
      .join("\n\n---\n\n");
    fs.writeFileSync(compiledPath, combined, "utf8");
    console.log(`✅ Compiled: ${compiledPath}`);
  }
}

// Execute immediately
runAll().catch((err) => {
  console.error("❌ Error:", err);
  process.exit(1);
});
