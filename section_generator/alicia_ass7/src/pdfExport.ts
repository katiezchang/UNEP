import "dotenv/config";
import fs from "fs";
import PDFDocument from "pdfkit";
import { generateSection } from "./agents/generatorAgent.js";
import { verifyAndReviseSection } from "./agents/verifierAgent.js";

const OUT_JSON = "exported_outputs.json";
const OUT_PDF = "exported_sections.pdf";

type Outputs = {
  country: string;
  instVerified: string;
  policyVerified: string;
  generatedAt: string;
};

async function regenerate(country: string): Promise<Outputs> {
  const institutionalFrameworkInstructions = `
Write the section "Institutional Framework for Climate Action" for \${country} following the official GEF8 PIF format.

Structure and tone requirements:
• The section should consist of: (1) an introduction paragraph, (2) a bulleted list of institutions and their roles, and (3) a conclusion paragraph.
• **Use bullet points only for listing institutions and their roles — do NOT use Markdown tables or numbering.**
• The section should read as a formal, factual summary appropriate for inclusion in a GEF Project Identification Form.

Content structure:

1. **Introductory paragraph (plain prose, no bullets)**
   - Describe the national legal and institutional foundation for climate governance and transparency.
   - Identify the lead ministry or agency responsible for coordinating national climate policy and reporting to the UNFCCC.
   - Explain this institution's role in preparing National Communications, Biennial Update Reports (BURs), and Biennial Transparency Reports (BTRs).
   - End with a transition statement like: "The following institutions play key roles in this framework:" or "Key institutions supporting this framework include:"

2. **Bulleted list of institutions and their roles (MUST BE EXPLICIT BULLET POINTS)**
   - Present institutions as a clear bulleted list covering the country's institutional framework for climate action.
   - Each bullet must start with '- ' or '• ' followed by **bolded institution name** in original language with acronym and English translation in brackets.
   - Format: '- **Institution Name (Acronym)** [English translation]: One-sentence description of primary role in climate action, MRV, or reporting.'
   - Each institution description should be concise (1 sentence per institution).
   - Cover multiple sectors as relevant to the country: agriculture, energy, transport, industry, finance, health, education, water, environment, etc.

3. **Concluding paragraph (plain prose, no bullets)**
   - Summarize the overall significance of this institutional framework for national sustainability, climate resilience, and transparency.
   - Highlight how these institutions work together to support the country's compliance with international reporting obligations under the UNFCCC and Paris Agreement.
   - Mention the importance of inter-ministerial coordination and data quality assurance.
`;

  const nationalPolicyInstructions = `
Write the section "National Policy Framework" for \${country} following the official GEF8 PIF format. This section focuses on specific LAWS, POLICIES, DECREES, and STRATEGIES—not on institutional frameworks or organizational structures.

SOURCE AND RECENCY REQUIREMENTS:
• Include policies and laws from the APPROVED SOURCES:
  - UNFCCC (unfccc.int)
  - ICAT (Initiative for Climate Action Transparency)
  - PATPA (Partnership for Transparency in the Paris Agreement)
  - GEF/CBIT (Global Environment Facility / Capacity-Building Initiative for Transparency)
  - The target country's official national climate, environment, or energy ministry website
• Prioritize recent policies (2020-2025 where possible), but policies from approved sources that are foundational to the country's climate framework may be included if they are still in force.
• Only include policies you can verify from these sources. If you cannot verify a policy, do not include it.

Formatting and tone:
• Use an explicit bulleted list for the main policy and legal instruments. Each bullet must begin with a dash and a single space (e.g. - ), then the policy or law title in bold followed by a colon, and then a short description of the instrument (maximum 3 sentences per bullet).
  - Example: - **Decree 86 (2019):** One-sentence summary of the decree's objectives. Second sentence on scope/focus areas if needed.
• **CRITICAL: The opening paragraph and concluding paragraph must NEVER be in bullet point format and must NEVER contain any bold text. These are plain flowing paragraphs. Bold formatting should ONLY appear in the policy names within the bullet list items.**
• Maintain a formal, factual tone suitable for inclusion in a GEF Project Identification Form (PIF).
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
  - Include the country's key foundational climate policies and laws from approved sources that are still in force.
  - Aim for a comprehensive list of the country's climate policy instruments (8–12+ where available, but include all that are verifiable and relevant).

3. **Concluding synthesis paragraph (plain text paragraphs ONLY, NO BULLETS, NO BOLD)**
   - Write this as continuous flowing prose, NOT as bullet points.
   - Summarize:
     • The overall significance of this policy framework for national sustainability, climate resilience, and transparency.  
     • Persistent challenges such as limited technical capacity, financing gaps, or MRV system limitations.  
     • The need to regularly update policies and laws to ensure consistency with international commitments and the Enhanced Transparency Framework (ETF).
   - DO NOT BOLD any words or phrases in this concluding paragraph.
   - DO NOT FORMAT this as bullet points; use flowing prose.
`;

  const [instFramework, policyFramework] = await Promise.all([
    generateSection({
      sectionTitle: "Institutional Framework for Climate Action",
      instructions: institutionalFrameworkInstructions,
      country,
    }),
    generateSection({
      sectionTitle: "National Policy Framework",
      instructions: nationalPolicyInstructions + "\n\nCRITICAL: For Cuba, MUST include the following foundational policies from approved sources: (1) Cuban Nationally Determined Contribution (NDC) with year, (2) Tarea Vida (2016 or later updates) as the national framework for climate action, and (3) Decree 86 on climate change governance. These are core to Cuba's climate framework and are verifiable from UNFCCC and approved sources. Include these along with other verifiable recent policies.",
      country,
    }),
  ]);

  const [instVerified, policyVerified] = await Promise.all([
    verifyAndReviseSection(instFramework, "Institutional Framework for Climate Action", country),
    verifyAndReviseSection(policyFramework, "National Policy Framework", country),
  ]);

  return {
    country,
    instVerified,
    policyVerified,
    generatedAt: new Date().toISOString(),
  };
}

function saveOutputs(outputs: Outputs) {
  fs.writeFileSync(OUT_JSON, JSON.stringify(outputs, null, 2), { encoding: "utf8" });
}

function loadOutputs(): Outputs {
  const raw = fs.readFileSync(OUT_JSON, { encoding: "utf8" });
  return JSON.parse(raw) as Outputs;
}

async function renderPdf(outputs: Outputs) {
  const doc = new PDFDocument({ size: "A4", margins: { top: 40, bottom: 40, left: 48, right: 48 } });
  const stream = fs.createWriteStream(OUT_PDF);
  doc.pipe(stream);

  doc.fontSize(18).font("Helvetica-Bold").text("Verified Sections (export)", { align: "left" });
  doc.moveDown();

  doc.fontSize(14).font("Helvetica-Bold").text("Institutional Framework for Climate Action");
  doc.moveDown(0.25);
  // Helper: render simple markdown inline (supports **bold**) and preserves paragraphs
  function renderMarkdownPreservingBold(doc: any, text: string) {
    if (!text) return;
    const pageWidth = doc.page.width - doc.page.margins.left - doc.page.margins.right;
    // Preserve single-line breaks so bullets and line-separated items remain on separate lines.
    const paragraphs = text.split(/\n\s*\n/);
    const bodyFont = "Helvetica";
    const boldFont = "Helvetica-Bold";
    const fontSize = 10;
    const bulletIndent = 14; // pixels to indent bullet content

    for (const p of paragraphs) {
      const lines = p.split(/\r?\n/);
      for (const line of lines) {
        const trimmed = line.replace(/\r?\n/, '').trim();
        if (!trimmed) {
          doc.moveDown(0.2);
          continue;
        }

        // Detect bullet lines (• or -)
        const bulletMatch = trimmed.match(/^\s*(?:•|-|\*)\s+(.*)$/);
        let contentLine = trimmed;
        let isBullet = false;
        if (bulletMatch) {
          isBullet = true;
          contentLine = bulletMatch[1];
        }

        // Split the line into segments of plain and bold text
        const segments: Array<{ text: string; bold: boolean }> = [];
        let cursor = 0;
        const boldRe = /\*\*(.+?)\*\*/g;
        let m: RegExpExecArray | null;
        while ((m = boldRe.exec(contentLine)) !== null) {
          const pre = contentLine.slice(cursor, m.index);
          if (pre) segments.push({ text: pre, bold: false });
          segments.push({ text: m[1], bold: true });
          cursor = m.index + m[0].length;
        }
        const tail = contentLine.slice(cursor);
        if (tail) segments.push({ text: tail, bold: false });

        // Prepare initial x offset for bullets
        const startX = doc.x;
        if (isBullet) {
          // Draw bullet glyph at startX
          doc.font(bodyFont).fontSize(fontSize).text('•', startX, undefined, { continued: true });
          // Move to indented position for the rest of the line
          const textX = startX + bulletIndent;
          // write first segment at textX
          if (segments.length === 0) {
            doc.text('', { continued: false });
          } else {
            // write segments sequentially, using continued except for last
            for (let i = 0; i < segments.length; i++) {
              const seg = segments[i];
              const font = seg.bold ? boldFont : bodyFont;
              const isLast = i === segments.length - 1;
              if (i === 0) {
                // position this segment at textX
                doc.font(font).fontSize(fontSize).text(seg.text, textX, undefined, { continued: !isLast, width: pageWidth - bulletIndent });
              } else {
                // continue from previous position
                doc.font(font).fontSize(fontSize).text(seg.text, { continued: !isLast, width: pageWidth - bulletIndent });
              }
            }
          }
        } else {
          // Non-bullet line: write segments sequentially at normal x
          for (let i = 0; i < segments.length; i++) {
            const seg = segments[i];
            const font = seg.bold ? boldFont : bodyFont;
            const isLast = i === segments.length - 1;
            if (i === 0) {
              doc.font(font).fontSize(fontSize).text(seg.text, { continued: !isLast, width: pageWidth });
            } else {
              doc.font(font).fontSize(fontSize).text(seg.text, { continued: !isLast, width: pageWidth });
            }
          }
        }

        // ensure we are at the next line
        doc.moveDown(0.25);
      }
      // paragraph gap
      doc.moveDown(0.5);
    }
  }

  // Render institutional section. The generator produces intro paragraph, bulleted institutions, and conclusion.
  // Normalize any markdown list markers (- or *) to bullet glyphs for rendering.
  let instText = outputs.instVerified ?? "";
  // strip a leading bolded title if present
  const titleMarker = "**Institutional Framework for Climate Action**";
  if (instText.trim().startsWith(titleMarker)) {
    instText = instText.trim().slice(titleMarker.length).trimStart();
  }
  // convert markdown list markers (- or *) at line starts to a bullet glyph
  instText = instText.replace(/^\s*-\s+/gm, '• ').replace(/^\s*\*\s+/gm, '• ');
  // render using markdown-aware helper so **bold** is shown in bold
  renderMarkdownPreservingBold(doc, instText);
  // separate sections: add page before the next section
  doc.addPage();

  doc.fontSize(14).font("Helvetica-Bold").text("National Policy Framework");
  doc.moveDown(0.25);
  // Ensure the policy section contains explicit bullets for each law/policy. If the verifier
  // produced running paragraphs with bolded instrument names (e.g., **Decree 86**), extract
  // those and convert to explicit '-' bullets where each bullet is max 3 sentences.
  let policyText = outputs.policyVerified ?? "";
  // If it already contains explicit bullets, leave as-is
  if (!/^\s*(?:-|\*|•)\s+/m.test(policyText)) {
    const bullets: string[] = [];
    const boldRe = /\*\*(.+?)\*\*/g;
    const policyPattern = /\b(Decree|Decreto|Law|Ley|NDC|Tarea|Tarea Vida|Plan|Strategy|Program|Policy|Resolution|Act)\b/i;

    const sentences = policyText.split(/(?<=[.!?])\s+/).map(s => s.trim()).filter(Boolean);
    const candidateIndexes: number[] = [];
    for (let i = 0; i < sentences.length; i++) {
      const s = sentences[i];
      if (boldRe.test(s) || policyPattern.test(s)) {
        candidateIndexes.push(i);
      }
      // reset lastIndex for global regex reuse
      boldRe.lastIndex = 0;
    }

    const used = new Set<number>();
    for (const idx of candidateIndexes) {
      if (used.has(idx)) continue;
      // take up to 3 contiguous sentences starting at idx
      const end = Math.min(sentences.length - 1, idx + 2);
      const group: string[] = [];
      for (let j = idx; j <= end; j++) {
        if (used.has(j)) break;
        group.push(sentences[j]);
      }
      // mark used
      for (let j = idx; j <= Math.min(end, idx + group.length - 1); j++) used.add(j);

      const groupText = group.join(' ');
      // find bold name if present
      const boldMatch = /\*\*(.+?)\*\*/.exec(groupText);
      let name = '';
      if (boldMatch) {
        name = boldMatch[1].trim();
      } else {
        // fallback: take first phrase up to comma or 'which' or 'that'
        const commaIdx = groupText.search(/[,:\-]/);
        const clause = commaIdx !== -1 ? groupText.slice(0, commaIdx) : groupText.split(/\bwhich\b|\bthat\b/i)[0];
        name = clause.split('\n')[0].split(' ').slice(0, 6).join(' ').replace(/\.$/, '').trim();
      }

      // skip if name doesn't look like a policy/instrument (very short)
      if (!policyPattern.test(name) && name.split(' ').length < 2) continue;

      // description: remove bold markers and the name from groupText
      const desc = groupText.replace(/\*\*(.+?)\*\*/g, '').replace(new RegExp(name, 'g'), '').replace(/^[,:;\-\s]+/, '').trim();
      bullets.push(`- **${name}:** ${desc}`);
    }

    if (bullets.length > 0) {
      // intro = sentences before first used index
      const usedIndexes = Array.from(used).sort((a, b) => a - b);
      const intro = sentences.slice(0, usedIndexes[0] ?? 0).join(' ').trim();
      const rest = sentences.slice((usedIndexes[usedIndexes.length - 1] ?? -1) + 1).join(' ').trim();
      policyText = [intro, bullets.join('\n'), rest].filter(Boolean).join('\n\n');
    }
  }
  // render with markdown bold support
  renderMarkdownPreservingBold(doc, policyText);

  doc.end();

  await new Promise<void>((resolve, reject) => {
    stream.on("finish", () => {
      console.log(`PDF written to ${OUT_PDF}`);
      resolve();
    });
    stream.on("error", (err) => reject(err));
  });
}

async function main() {
  const args = process.argv.slice(2);
  const saveOnly = args.includes("--save-only");
  const renderOnly = args.includes("--render-only");
  const countryArg = args.find((a) => !a.startsWith("--")) as string | undefined;
  const country = countryArg ?? "Cuba";

  if (renderOnly) {
    if (!fs.existsSync(OUT_JSON)) {
      console.error(`No saved outputs found at ${OUT_JSON}. Run with --save-only first.`);
      process.exit(1);
    }
    const outputs = loadOutputs();
    await renderPdf(outputs);
    return;
  }

  // regenerate
  const outputs = await regenerate(country);
  // print to console
  console.log("\n=== Institutional Framework (VERIFIED) ===\n");
  console.log(outputs.instVerified);
  console.log("\n=== National Policy Framework (VERIFIED) ===\n");
  console.log(outputs.policyVerified);

  // save
  saveOutputs(outputs);
  console.log(`Saved outputs to ${OUT_JSON}`);

  if (!saveOnly) {
    await renderPdf(outputs);
  }
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
