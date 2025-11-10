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
• Use bullet points only for listing institutions and their roles — do NOT use Markdown tables or numbering.
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

4. **List the main institutions and their roles** using bullet points in this format:
   • [Institution Name]: [Brief description of role, 1–2 sentences].  
   Example:
   • Ministerio de Agricultura (MINAG) [Ministry of Agriculture]: Coordinates the process of collecting, preparing, and analyzing information from Agriculture and LULUCF sectors, including activity data (AD) and other inputs for the inventory, monitoring of national contributions, climate change impact assessment, and management of the support needed and received. It also prepares the corresponding sectoral report.
   • NMinisterios de Educación y de Educación Superior (MINED/MES) [Ministries of Education and of Higher Education]: Contribute technical capacity, knowledge, and research results. Promote environmental education and climate change awareness at all school levels.

The tone must be factual, cohesive, and formatted for direct PDF export with clear paragraph breaks and bullet list alignment.
`;


  const nationalPolicyInstructions = `
Write the section “National Policy Framework” for \${country} following the official GEF8 PIF format and the paragraph structure used in the Cuba example. 

Formatting and tone:
• Use continuous paragraphs, but each policy or law must start with its title and year in bold, followed by a short descriptive paragraph.
• Avoid bullet points, numbered lists, or markdown tables.
• Maintain a formal, factual tone suitable for inclusion in a GEF Project Identification Form (PIF).
• The section should read like a catalog of legal and policy instruments, each described briefly and clearly.

Content structure:

1. **Opening paragraph**
   - Begin with one concise paragraph summarizing the country’s overall policy and legal framework for climate action and how it aligns with international commitments such as the UNFCCC and the Paris Agreement.
   - End the paragraph with a transition like: “The following key instruments form the foundation of this framework:”

2. **Policy and legal instruments (each in its own short paragraph)**
   - For each law, decree, plan, or strategy, provide:
     • The full name and year in bold (e.g., **Law No. 150 on Environmental Protection (2023):**)  
     • A 2–4 sentence explanation describing its objectives, focus areas (adaptation, mitigation, MRV, governance), and responsible institutions.
   - Examples of the expected format (for illustration only, adapt automatically to each country):
     **Constitution of [Country] (Year):** Establishes the state’s duty to protect the environment and respond to climate change as a national priority, aligning with principles of sustainable development and international cooperation.  
     **Law on Natural Resources and the Environment (Year):** Provides the legal foundation for managing natural resources and sets national responsibilities for adaptation and mitigation planning.  
     **Decree on Climate Change (Year):** Defines institutional arrangements, assigns sectoral responsibilities, and mandates integration of climate objectives across ministries and local governments.  
     **National Plan for Climate Change (Year):** A long-term, cross-cutting strategy that guides specific actions to reduce vulnerability, protect ecosystems, and build resilience in key sectors such as agriculture, water, and coastal management.  
     **Nationally Determined Contribution (latest year):** Details national emission reduction targets and adaptation priorities in alignment with the Paris Agreement.  
     **National Energy Transition Strategy (Year):** Establishes pathways toward renewable energy adoption and carbon neutrality by mid-century.  
     **Other relevant acts or programs:** Mention sectoral plans or regional policies that strengthen adaptation, mitigation, or transparency efforts.

3. **Concluding synthesis paragraph**
   - End with one or two paragraphs summarizing:
     • The overall significance of this framework for national sustainability, climate resilience, and transparency.  
     • Persistent challenges such as limited technical capacity, financing, or MRV system gaps.  
     • The need to regularly update policies (e.g., decrees, NDCs, or strategies) to ensure consistency with international commitments and the Enhanced Transparency Framework (ETF).

Style requirements:
• Bold each policy or law name followed by a colon before its description.
• Keep each paragraph short and cohesive (no bullets or headings beyond bold policy titles).
• The final output should closely match the style and structure of the “National Policy Framework” section from the Cuba GEF8 PIF—each instrument clearly delineated, followed by synthesis and conclusion.
`;






  // -------- Generate Both Sections Concurrently --------
  const [instFramework, policyFramework] = await Promise.all([
    generateSection({
      sectionTitle: "Institutional Framework for Climate Action",
      instructions: institutionalFrameworkInstructions,
      country,
    }),
    generateSection({
      sectionTitle: "National Policy Framework",
      instructions: nationalPolicyInstructions,
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
