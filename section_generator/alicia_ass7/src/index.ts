import "dotenv/config";
import { generateSection } from "./agents/generatorAgent.js";
import { verifyAndReviseSection } from "./agents/verifierAgent.js";

async function main() {
  const country = "Cuba"; // Replace dynamically when needed

  // -------- Section-Specific Prompts --------

  const institutionalFrameworkInstructions = `
Write the section “Institutional Framework for Climate Action” for \${country} following the official GEF8 PIF format.

Structure and tone requirements:
• Maintain continuous paragraphs and professional language suitable for official reporting.
• **Use bullet points only for listing institutions and their roles — do NOT use Markdown tables or numbering.**
• The section should read as a formal, factual summary appropriate for inclusion in a GEF Project Identification Form.

Include the following content elements:

1. **Introductory paragraph**
   - Describe the national legal and institutional foundation for climate governance and transparency.
   - Mention the principal environmental or climate law that establishes the national climate framework, using the correct name and year where applicable.
   - Identify the lead ministry or agency responsible for coordinating national climate policy and reporting to the UNFCCC (e.g., the ministry of environment, science, or climate change).
   - Explain this institution’s role in preparing National Communications, Biennial Update Reports (BURs), and Biennial Transparency Reports (BTRs).

2. **Institutional roles and coordination**
   - Explain how data collection, verification, and reporting for MRV and transparency are organized.
   - Mention examples of technical or statistical institutions such as national energy agencies, meteorological institutes, or statistical offices, and describe their contributions to transparency and data management.
   - Describe inter-ministerial or technical coordination mechanisms that ensure consistency of data and policy alignment across sectors.

3. **International support and collaboration**
   - Describe how international programs and initiatives—such as the Initiative for Climate Action Transparency (ICAT), the Capacity-Building Initiative for Transparency (CBIT), and the Global Environment Facility (GEF)—support institutional capacity building, MRV systems, and transparency processes.
   - Explain how these programs help align national MRV and reporting with the Enhanced Transparency Framework (ETF) of the Paris Agreement.

4. **List the main institutions and their roles using bullet points in this format:**
   Provide a comprehensive bullet list of institutions and their roles. Aim for multiple institutions (8–15+) with SHORT, CONCISE descriptions (typically 1 sentence per bullet).
   
   • **[Institution Name (Acronym)]** [English translation]: [Brief 1-sentence description of primary role in climate action, MRV, or reporting].
   
   Examples (for Cuba — use appropriate institutions for the target country, with original language names and English translations in brackets):
   • **Ministerio de Ciencia, Tecnología y Medio Ambiente (CITMA)** [Ministry of Science, Technology, and Environment]: Lead ministry responsible for climate policy coordination and UNFCCC reporting.
   • **Ministerio de Agricultura (MINAG)** [Ministry of Agriculture]: Coordinates data collection and analysis for agriculture and LULUCF sectors.
   • **Ministerio de Energía y Minas (MINEM)** [Ministry of Energy and Mines]: Manages energy-related emissions monitoring and renewable energy transition.
   • **Ministerio de Transporte (MITRANS)** [Ministry of Transportation]: Oversees transport sector emissions data collection and mitigation strategies.
   • **Ministerio de Industrias (MINDUS)** [Ministry of Industries]: Coordinates industrial sector MRV and sustainable production practices.
   • **Instituto Nacional de Recursos Hidráulicos (INRH)** [National Institute of Hydraulic Resources]: Manages water resource management and climate adaptation data.
   • **Ministerio de Finanzas y Precios** [Ministry of Finance and Prices]: Oversees climate finance management and resource allocation for climate action.
   • **Ministerio de Salud Pública (MINSAP)** [Ministry of Public Health]: Contributes to health-climate nexus monitoring and adaptation planning.
   • **Ministerio de Construcción (MICONS)** [Ministry of Construction]: Coordinates building sector energy efficiency and climate resilience measures.
   • **Ministerios de Educación y de Educación Superior (MINED/MES)** [Ministries of Education]: Promote climate change awareness and environmental education.
   • Ministerio de Comercio Exterior e Inversión Extranjera (MINCEX) [Ministry of Foreign Trade and Foreign Investment]: Supports climate-related international cooperation and climate finance access.

The tone must be factual, cohesive, and formatted for direct PDF export with clear paragraph breaks and bullet list alignment.
`;


  const nationalPolicyInstructions = `
Write the section "National Policy Framework" for \${country} following the official GEF8 PIF format. This section focuses on specific LAWS, POLICIES, DECREES, and STRATEGIES—not on institutional frameworks or organizational structures.

Formatting and tone:
• Use an explicit bulleted list for the main policy and legal instruments. Each bullet must begin with a dash and a single space (e.g. - ), then the policy or law title in bold followed by a colon, and then a short description of the instrument (maximum 3 sentences per bullet).
  - Example: - **Decree 86 (2019):** One-sentence summary of the decree's objectives. Second sentence on scope/focus areas if needed.
• **CRITICAL: The opening paragraph and concluding paragraph must NEVER be in bullet point format and must NEVER contain any bold text. These are plain flowing paragraphs. Bold formatting should ONLY appear in the policy names within the bullet list items.**
• Maintain a formal, factual tone suitable for inclusion in a GEF Project Identification Form (PIF).
• Information should be as specific as possible and drawn from the allowed sources.
• DO NOT include descriptions of institutional roles or organizational structures in this section; focus ONLY on the content, objectives, and scope of the laws, policies, and strategies themselves.
• After the bullet list, include a short concluding synthesis paragraph (1–2 paragraphs) summarizing the framework and outstanding challenges.

Content structure:

1. **Opening paragraph (plain text paragraphs ONLY, NO BULLETS, NO BOLD)**
   - Write this as continuous flowing prose, NOT as bullet points.
   - DO NOT USE BULLETS HERE.
   - DO NOT BOLD any words or phrases in this paragraph.
   - Begin with one concise paragraph summarizing the country's overall policy and legal framework for climate action and how it aligns with international commitments such as the UNFCCC and the Paris Agreement.
   - End the paragraph with a transition like: "The following key instruments form the foundation of this framework:"

2. **Policy and legal instruments (present as explicit bullets, EACH AS ITS OWN BULLET) — FOCUS ON LAWS AND POLICIES, NOT INSTITUTIONS**
  - CRITICAL: Each law, decree, plan, or strategy MUST be output as a separate bullet line. DO NOT group multiple policies into one bullet.
  - For each law, decree, plan, or strategy, output a single bullet line in the following exact format:
    - **[Full name and year]:** [1–3 sentence description of objectives, focus areas (adaptation, mitigation, MRV, governance), and key provisions.]
  - Aim for 8–12+ policy/law instruments depending on the country.
  - Examples (for illustration only — adapt names and years to the target country):
    - **Law on Environmental Protection (Year):** Establishes environmental protections and mandates for sustainable development. Addresses climate change impacts on key sectors.
    - **National Climate Change Adaptation Plan (Year):** Outlines priority sectors for climate adaptation including agriculture, water, and coastal zones. Sets targets and implementation mechanisms.
    - **National Energy Transition Strategy (Year):** Details targets for renewable energy deployment and energy efficiency improvements. Specifies timelines and sectoral focus areas.
    - **National Determined Contribution (NDC) 3.0 (Year):** Commits to specific greenhouse gas emission reduction targets by a set year. Identifies priority mitigation and adaptation actions.
    - **Decree on Climate Governance (Year):** Establishes institutional coordination mechanisms for climate policy implementation. Mandates integration of climate considerations in national planning.

3. **Concluding synthesis paragraph (plain text paragraphs ONLY, NO BULLETS, NO BOLD)**
   - Write this as continuous flowing prose, NOT as bullet points.
   - Summarize:
     • The overall significance of this policy framework for national sustainability, climate resilience, and transparency.  
     • Persistent challenges such as limited technical capacity, financing gaps, or MRV system limitations.  
     • The need to regularly update policies and laws to ensure consistency with international commitments and the Enhanced Transparency Framework (ETF).
   - DO NOT BOLD any words or phrases in this concluding paragraph.
   - DO NOT FORMAT this as bullet points; use flowing prose.

`;


  // -------- Generate Both Sections Concurrently --------
  const [instFramework, policyFramework] = await Promise.all([
    generateSection({
      sectionTitle: "Institutional Framework for Climate Action",
      instructions: institutionalFrameworkInstructions + "\n\nCRITICAL REQUIREMENT: For the list of main institutions and their roles, you MUST output a comprehensive explicit bullet list. Each line MUST start with '-' followed by a single space. Do NOT embed institutions inline in running paragraphs. The bullet list should contain 8–15+ institutions (depending on the country) with SHORT, concise 1-sentence role descriptions. Format: '- Institution Name [English]: One-sentence description of role.' Aim for breadth of coverage across sectors (agriculture, energy, transport, industry, finance, health, education, water, environment, etc.).",
      country,
    }),
    generateSection({
      sectionTitle: "National Policy Framework",
      instructions: nationalPolicyInstructions + "\n\nCRITICAL REQUIREMENT: For the policy and legal instruments list, you MUST output EACH law, decree, plan, or strategy as a SEPARATE bullet point. Do NOT combine multiple policies into one bullet. Each bullet MUST start with '-' followed by a single space, then the policy name in bold, then a colon, then the description (maximum 3 sentences). Aim for 10–15+ separate policy bullets. Format: '- **Policy Name (Year):** Description. Second sentence. Third sentence.'",
      country,
    }),
  ]);

  // -------- Verify and Revise with Accuracy Agent --------
  const [instVerified, policyVerified] = await Promise.all([
    verifyAndReviseSection(instFramework, "Institutional Framework for Climate Action", country),
    verifyAndReviseSection(policyFramework, "National Policy Framework", country),
  ]);

 
}

main().catch(console.error);
