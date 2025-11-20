/**
 *
 * How this file is structured:
 * - generateSectionParagraph(): single generic caller (exact structure you were asked to follow)
 * - Per-section functions with tailored "instructions" (A–N) including precise word targets
 * - "STANDARD TEXT TO BE INCLUDED ... END" preserved wherever the template requires it
 * - Sources restricted to: UNFCCC (NC/BUR/BTR/NIR), ICAT, PATPA, GEF/CBIT, and Cuba’s CITMA site
 * - Tables: we force Markdown tables and forbid reformatting
 * - Missing data: model must mark as MISSING and point to specific URL/path within allowed sources
 * - Saves each section to /out and also compiles a master /out/Cuba_PIF_Aathma_FULL.txt
 */

import fs from "fs";
import path from "path";
import { generateText } from "ai";

// ---------------------- CONFIG ----------------------
const COUNTRY = "Cuba";
const MODEL = "gpt-4o-mini"; // same style as your example
const OUT_DIR = "out";

// Ensure output dir exists
if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

// ---------------------- CORE CALLER (exact format) ----------------------
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

${instructions}

Return a professional, concise, and informative essay with the MINIMUM word count as specified in the instructions for this section. Use the tone and structure of international project documents (UNEP/GEF style) and mirror the exact headings/subheadings requested below. Keep the structure of the document EXACTLY the same as instructed.

STRICT SOURCE RULES — USE ONLY:
- UNFCCC reports portal (BTR/NC/BUR/NIR for ${country}): https://unfccc.int/reports
- ICAT (https://climateactiontransparency.org) ${country} pages/reports
- PATPA (https://transparency-partnership.net) knowledge products / Good Practice DB
- GEF/CBIT documents on https://www.thegef.org/projects-operations/database
- ${country} official environment ministry (CITMA) site (and its linked institutions like INSMET/ONEI)

DO NOT use any other sources.
If required info is missing, write “MISSING:” and point to the specific PDF/URL within the above sites where it likely exists (or exact portal path).
No hallucinations. If uncertain, say “MISSING” with a pointer.

TABLES:
- When asked for a table, output a clean Markdown table with the exact required columns and no added columns.
- Preserve order and headers as specified.

STANDARD TEXT:
- Where instructed, include the exact phrases “STANDARD TEXT TO BE INCLUDED” and “STANDARD TEXT TO BE INCLUDED END” with the appropriate content between them if the template requires standard text. If the exact standard wording is not provided in the prompt, include those two markers with a one-line placeholder: “(Insert standard UNEP/GEF boilerplate text here as per template.)” so the editor can paste the official boilerplate.

Word count discipline:
- Meet or EXCEED the minimum word count specified in the instructions. Do NOT go below.
- Prefer staying within ±10% of the given minimum to manage length.

Return only the final section text (no backticks, no commentary).
  `.trim();

  const result = await generateText({
    model: (globalThis as any).openai ? (globalThis as any).openai(MODEL) : (MODEL as any),
    prompt,
  });

  return (result.text || "").trim();
}

// ---------------------- SECTION PROMPTS (A–N) ----------------------

// A. Project Rationale (~1600 words)
async function sectionA_ProjectRationale(country = COUNTRY) {
  return generateSectionParagraph({
    sectionTitle: "A. Project Rationale",
    country,
    instructions: `
MINIMUM WORDS: 1600 (aim for ~1600–1800).
Headings to include (exactly):
- Context and Vulnerability in ${country}
- Current Transparency Situation and Gaps
- Institutional Landscape (CITMA, INSMET, ONEI; sectoral ministries)
- Lessons from CBIT-1 and Rationale for GEF-8 Support
- Expected Results and Theory of Change (brief)

Insert after the above subsections:
“STANDARD TEXT TO BE INCLUDED
(Insert standard UNEP/GEF boilerplate text here as per template.)
STANDARD TEXT TO BE INCLUDED END”

Source anchors to cite or point readers to:
- UNFCCC BUR1 (year, link/path on UNFCCC portal), NC2 (year), planned BTR page.
- GEF CBIT Cuba project entry on the GEF site.
- PATPA, ICAT country pages (URLs).
If exact quantified values are not publicly verifiable in these sites, use “MISSING: <what> (likely in <URL or portal subpath>)”.
    `,
  });
}

// Paris Agreement & ETF Standard block (exact markers, short)
async function section_Paris_ETF_Standard(country = COUNTRY) {
  return generateSectionParagraph({
    sectionTitle: "Paris Agreement and the Enhanced Transparency Framework (ETF)",
    country,
    instructions: `
MINIMUM WORDS: 150 (concise standard explanation).
Content must be enclosed between the markers below, as the template demands a standard paragraph:
“STANDARD TEXT TO BE INCLUDED
(Insert standard UNEP/GEF boilerplate text here as per template.)
STANDARD TEXT TO BE INCLUDED END”
    `,
  });
}

// B. Climate Transparency in Cuba (~400 words)
async function sectionB_ClimateTransparency(country = COUNTRY) {
  return generateSectionParagraph({
    sectionTitle: "B. Climate Transparency in Cuba",
    country,
    instructions: `
MINIMUM WORDS: 400.
Cover:
- Status of SNTC (national platform) and any provincial integration status.
- Data flows (CITMA lead; INSMET/ONEI roles; sectoral ministries).
- Readiness for BTR-1 (timelines if public; otherwise MISSING with pointer).
- Key gaps: QA/QC institutionalization, adaptation indicators, support MRV.

End with the markers:
“STANDARD TEXT TO BE INCLUDED END”
    `,
  });
}

// C. Baseline (composed of multiple sub-sections)
async function sectionC1i_InstitutionalFramework(country = COUNTRY) {
  return generateSectionParagraph({
    sectionTitle: "C.1.i Institutional Framework for Climate Action",
    country,
    instructions: `
MINIMUM WORDS: 500.
Describe: CITMA’s mandate; National Climate Change Group; INSMET; ONEI; sectoral ministries; provincial coordination.
Specify data submission protocols, frequency, and gaps in legal mandates. Include mention of Decree 281/2019 if verified; otherwise mark MISSING with path.

No table here—plain narrative with subheadings allowed.
    `,
  });
}

async function sectionC1ii_NationalPolicyFramework(country = COUNTRY) {
  return generateSectionParagraph({
    sectionTitle: "C.1.ii National Policy Framework",
    country,
    instructions: `
MINIMUM WORDS: 500.
Explain: Tarea Vida (2017), updated NDC (year), links between mitigation and adaptation, any decree-laws on climate information exchange (cite if verified), and how policies align to ETF requirements.

No table here—plain narrative. Use “MISSING” where data cannot be verified within allowed sources.
    `,
  });
}

async function sectionC1iii_StakeholdersTable(country = COUNTRY) {
  return generateSectionParagraph({
    sectionTitle: "C.1.iii Other Key Stakeholders for Climate Action (Table)",
    country,
    instructions: `
MINIMUM WORDS: 120 (short intro + table).
First: 1 short paragraph (2–4 sentences) introducing stakeholder groups and their potential roles.

Then output EXACTLY this Markdown table (no extra columns):
| Type | Stakeholder(s) | Existing activities/projects with potential to be leveraged |
|------|-----------------|-------------------------------------------------------------|

Include 5–8 rows covering Government, Academia, Civil Society, Private Sector, International Partners. If exact names cannot be verified, write “MISSING: <specific stakeholder> (likely in <CITMA or partner URL>)”.
    `,
  });
}

async function sectionC1iv_OfficialReportingTable(country = COUNTRY) {
  return generateSectionParagraph({
    sectionTitle: "C.1.iv Official reporting to the UNFCCC (Table)",
    country,
    instructions: `
MINIMUM WORDS: 80 (short lead-in + table).
Lead-in: 1–2 sentences noting that ${country} has submitted multiple reports and is preparing BTR-1.

Then output EXACTLY this Markdown table (no extra columns):
| Year | Report | Comments |
|------|--------|----------|

Include NC1, NC2, BUR1, and planned BTR1 with concise comments. If a date is not fully verifiable on UNFCCC portal, mark “MISSING: <item> (see UNFCCC reports portal)”.
End with: “STANDARD TEXT TO BE INCLUDED END”
    `,
  });
}

async function sectionC2i_GHGInventory(country = COUNTRY) {
  return generateSectionParagraph({
    sectionTitle: "C.2.i GHG Inventory Module",
    country,
    instructions: `
MINIMUM WORDS: 400.
Cover: IPCC 2006 Guidelines; sector coverage (Energy, AFOLU, IPPU, Waste); Tier levels; QA/QC status; uncertainty analysis (if any); summary trend (if verifiable).
If values or trends are uncertain, use MISSING with UNFCCC portal pointer.
    `,
  });
}

async function sectionC2ii_Adaptation(country = COUNTRY) {
  return generateSectionParagraph({
    sectionTitle: "C.2.ii Adaptation and Vulnerability Module",
    country,
    instructions: `
MINIMUM WORDS: 400.
Cover: Tarea Vida; status of adaptation MRV; pilot provinces; indicator gaps; need for gender-disaggregated data; links to INSMET hazard data.
If adaptation indicator lists aren't public, mark MISSING with likely source path.
    `,
  });
}

async function sectionC2iii_NDCTracking(country = COUNTRY) {
  return generateSectionParagraph({
    sectionTitle: "C.2.iii NDC Tracking Module",
    country,
    instructions: `
MINIMUM WORDS: 400.
Cover: NDC mitigation/adaptation targets; current tracking approach (manual/digital); examples of indicators (RE capacity MW, forest hectares, etc.); integration with national statistics.
Use MISSING for any non-verifiable indicator baselines/targets and point to sources.
    `,
  });
}

async function sectionC2iv_SupportModule(country = COUNTRY) {
  return generateSectionParagraph({
    sectionTitle: "C.2.iv Support Needed and Received Module",
    country,
    instructions: `
MINIMUM WORDS: 400.
Cover: support needed (USD), received (USD), capacity-building and TA; finance MRV status; Ministry of Economy and Planning role; gaps in aggregation.
If totals differ across reports, acknowledge discrepancy and use MISSING with BUR annex page or UNFCCC link.
    `,
  });
}

async function sectionC_OtherBaselineInitiativesTable(country = COUNTRY) {
  return generateSectionParagraph({
    sectionTitle: "C. Other Baseline Initiatives (Table)",
    country,
    instructions: `
MINIMUM WORDS: 60 (short lead-in + table).
Lead-in 1–2 sentences, then output EXACTLY this Markdown table:

| Program/Project | Lead Entity | Duration | Value (USD) | Relation to ETF |
|-----------------|-------------|----------|-------------|-----------------|

Include CBIT-1, ICAT support, EU Resiliencia, PATPA hub, etc. Mark any unverified values as MISSING with URL pointer.
    `,
  });
}

// D. Key Barriers (~600 words)
async function sectionD_KeyBarriers(country = COUNTRY) {
  return generateSectionParagraph({
    sectionTitle: "D. Key Barriers",
    country,
    instructions: `
MINIMUM WORDS: 600.
Structure with subheadings:
- Institutional Barriers
- Technical/Data Barriers
- Financial Barriers
- Human Capacity & Gender
- Legal and Governance
- Prioritized Solutions (brief)

Insert at the end:
“STANDARD TEXT TO BE INCLUDED END”
    `,
  });
}

// E. Project Components & Outputs (~500)
async function sectionE_Components(country = COUNTRY) {
  return generateSectionParagraph({
    sectionTitle: "E. Project Components and Expected Outputs",
    country,
    instructions: `
MINIMUM WORDS: 500.
Provide a short intro plus a 3–4 component structure (Institutional; MRV system; Capacity Building; Policy Integration).
Then include EXACTLY this Markdown table:

| Component | Expected Outputs | Expected Outcomes / Indicators |
|-----------|------------------|--------------------------------|

Populate 3–5 rows. Make outputs/outcomes realistic for ETF. No extra columns.
End with “STANDARD TEXT TO BE INCLUDED END”.
    `,
  });
}

// F. Indicative Financing (~300)
async function sectionF_Financing(country = COUNTRY) {
  return generateSectionParagraph({
    sectionTitle: "F. Indicative Financing Plan",
    country,
    instructions: `
MINIMUM WORDS: 300.
Short narrative + EXACT Markdown table:

| Source | Type | Amount (USD Million) | Status / Note |
|--------|------|-----------------------|---------------|

Include GEF Trust Fund (grant), Government in-kind, UNDP/EU parallel, ICAT/PATPA TA. If not fully verified, mark MISSING with link.
End with “STANDARD TEXT TO BE INCLUDED END”.
    `,
  });
}

// G. Alignment with GEF-8 (~300)
async function sectionG_Alignment(country = COUNTRY) {
  return generateSectionParagraph({
    sectionTitle: "G. Alignment with GEF-8 Focal-Area Strategies",
    country,
    instructions: `
MINIMUM WORDS: 300.
Align to GEF-8 CCM-ETF objective; mention digital transformation, gender, South–South cooperation with PATPA/ICAT.
End with “STANDARD TEXT TO BE INCLUDED END”.
    `,
  });
}

// H. Innovation/Sustainability/Replicability (~400)
async function sectionH_Innovation(country = COUNTRY) {
  return generateSectionParagraph({
    sectionTitle: "H. Innovation, Sustainability, and Replicability",
    country,
    instructions: `
MINIMUM WORDS: 400.
Cover: integrated MRV modules; open-source stack; sustainability via decree and budget line; replication across Caribbean SIDS; PATPA knowledge sharing.
End with “STANDARD TEXT TO BE INCLUDED END”.
    `,
  });
}

// I. Risk Assessment (~350)
async function sectionI_Risk(country = COUNTRY) {
  return generateSectionParagraph({
    sectionTitle: "I. Risk Assessment and Mitigation",
    country,
    instructions: `
MINIMUM WORDS: 350.
Short narrative + EXACT Markdown table:

| Risk | Likelihood | Impact | Mitigation Measure |
|------|------------|--------|--------------------|

Populate 5–7 rows (connectivity, turnover, mandate overlap, currency, data privacy, disaster risk).
End with “STANDARD TEXT TO BE INCLUDED END”.
    `,
  });
}

// J. Monitoring, Evaluation, Learning (~400)
async function sectionJ_MEL(country = COUNTRY) {
  return generateSectionParagraph({
    sectionTitle: "J. Monitoring, Evaluation, and Learning",
    country,
    instructions: `
MINIMUM WORDS: 400.
Narrative + EXACT Markdown table:

| Indicator | Baseline (Year) | Target (Year) | Source |
|-----------|------------------|---------------|--------|

Include staff trained, ministries connected, inventory frequency, adaptation indicators. Set baseline year explicitly (e.g., 2024 or 2025).
End with “STANDARD TEXT TO BE INCLUDED END”.
    `,
  });
}

// K. Gender & Social Inclusion (~350)
async function sectionK_GESI(country = COUNTRY) {
  return generateSectionParagraph({
    sectionTitle: "K. Gender Equality and Social Inclusion (GESI)",
    country,
    instructions: `
MINIMUM WORDS: 350.
Include:
- Current gender baseline in technical roles (if not verifiable, mark MISSING with pointer).
- Targets (>=40% women in training/decision bodies).
- Intersectionality (Afro-Cuban, rural, youth).
- A mini Gender Action Plan list (activities, indicators, responsibilities).

End with “STANDARD TEXT TO BE INCLUDED END”.
    `,
  });
}

// L. Environmental & Social Safeguards (~250)
async function sectionL_Safeguards(country = COUNTRY) {
  return generateSectionParagraph({
    sectionTitle: "L. Environmental and Social Safeguards",
    country,
    instructions: `
MINIMUM WORDS: 250.
Confirm Category C; note e-waste and energy-use considerations; reference UNEP ESSF.
End with “STANDARD TEXT TO BE INCLUDED END”.
    `,
  });
}

// M. Knowledge Management & Communication (~350)
async function sectionM_KM(country = COUNTRY) {
  return generateSectionParagraph({
    sectionTitle: "M. Knowledge Management and Communication",
    country,
    instructions: `
MINIMUM WORDS: 350.
List knowledge products (handbook, briefs, case studies), channels (CITMA, UNEP, PATPA/ICAT), targets and indicators for dissemination (downloads, views, workshops).
End with “STANDARD TEXT TO BE INCLUDED END”.
    `,
  });
}

// N. Expected Global Environmental Benefits (~300)
async function sectionN_GEB(country = COUNTRY) {
  return generateSectionParagraph({
    sectionTitle: "N. Expected Global Environmental Benefits",
    country,
    instructions: `
MINIMUM WORDS: 300.
Explain how stronger transparency yields better mitigation/adaptation outcomes and finance access; regional spillovers.
End with “STANDARD TEXT TO BE INCLUDED END”.
    `,
  });
}

// ---------------------- SAVE / COMPILE HELPERS ----------------------
function saveSection(title: string, text: string) {
  const safe = title.replace(/\s+/g, "_").replace(/[^a-zA-Z0-9_]/g, "");
  const p = path.join(OUT_DIR, `Cuba_${safe}.txt`);
  fs.writeFileSync(p, text, "utf8");
  console.log(`💾 Saved: ${p}`);
  return p;
}

async function runAll() {
  console.log("⚙️  Generating full Cuba PIF (all sections)…");

  // You can parallelize some calls, but preserve final order in compile.
  const sections: Array<[string, () => Promise<string>]> = [
    ["A. Project Rationale", () => sectionA_ProjectRationale()],
    ["Paris Agreement and ETF (Standard)", () => section_Paris_ETF_Standard()],
    ["B. Climate Transparency in Cuba", () => sectionB_ClimateTransparency()],
    ["C.1.i Institutional Framework", () => sectionC1i_InstitutionalFramework()],
    ["C.1.ii National Policy Framework", () => sectionC1ii_NationalPolicyFramework()],
    ["C.1.iii Other Key Stakeholders (Table)", () => sectionC1iii_StakeholdersTable()],
    ["C.1.iv Official Reporting to the UNFCCC (Table)", () => sectionC1iv_OfficialReportingTable()],
    ["C.2.i GHG Inventory Module", () => sectionC2i_GHGInventory()],
    ["C.2.ii Adaptation and Vulnerability Module", () => sectionC2ii_Adaptation()],
    ["C.2.iii NDC Tracking Module", () => sectionC2iii_NDCTracking()],
    ["C.2.iv Support Needed and Received Module", () => sectionC2iv_SupportModule()],
    ["C. Other Baseline Initiatives (Table)", () => sectionC_OtherBaselineInitiativesTable()],
    ["D. Key Barriers", () => sectionD_KeyBarriers()],
    ["E. Project Components and Outputs", () => sectionE_Components()],
    ["F. Indicative Financing Plan", () => sectionF_Financing()],
    ["G. Alignment with GEF-8 Focal-Area Strategies", () => sectionG_Alignment()],
    ["H. Innovation, Sustainability, and Replicability", () => sectionH_Innovation()],
    ["I. Risk Assessment and Mitigation", () => sectionI_Risk()],
    ["J. Monitoring, Evaluation, and Learning", () => sectionJ_MEL()],
    ["K. Gender Equality and Social Inclusion (GESI)", () => sectionK_GESI()],
    ["L. Environmental and Social Safeguards", () => sectionL_Safeguards()],
    ["M. Knowledge Management and Communication", () => sectionM_KM()],
    ["N. Expected Global Environmental Benefits", () => sectionN_GEB()],
  ];

  const outputs: string[] = [];
  for (const [title, fn] of sections) {
    console.log(`\n🟢 Generating: ${title}`);
    const text = await fn();
    saveSection(title, text);
    outputs.push(`## ${title}\n\n${text}`);
  }

  const compiled = outputs.join("\n\n---\n\n");
  const compiledPath = path.join(OUT_DIR, "Cuba_PIF_Aathma_FULL.txt");
  fs.writeFileSync(compiledPath, compiled, "utf8");
  console.log(`\n✅ Compiled: ${compiledPath}`);
}

runAll().catch((e) => {
  console.error("❌ Generation error:", e);
  process.exit(1);
});
