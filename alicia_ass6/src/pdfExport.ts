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
  const [instFramework, policyFramework] = await Promise.all([
    generateSection({
      sectionTitle: "Institutional Framework for Climate Action",
      instructions:
        "Describe national institutions responsible for climate transparency, MRV, and coordination (CITMA, CUBAENERGIA, ICAT, GEF).",
      country,
    }),
    generateSection({
      sectionTitle: "National Policy Framework",
      instructions:
        "Summarize national climate laws, plans, and strategies (Tarea Vida, NDC 3.0, Decree 86, etc.).",
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
    const paragraphs = text.split(/\n\s*\n/);
    for (const p of paragraphs) {
      // handle bold markers **...** within the paragraph
      let lastIndex = 0;
      const boldRe = /\*\*(.+?)\*\*/g;
      let match: RegExpExecArray | null;
      let isFirstSegment = true;
      while ((match = boldRe.exec(p)) !== null) {
        const prefix = p.slice(lastIndex, match.index);
        const boldText = match[1];
        if (prefix) {
          doc.font("Helvetica").fontSize(10).text(prefix, { continued: true, width: pageWidth });
        }
        doc.font("Helvetica-Bold").fontSize(10).text(boldText, { continued: true, width: pageWidth });
        lastIndex = match.index + match[0].length;
        isFirstSegment = false;
      }
      const tail = p.slice(lastIndex);
      if (tail) {
        // finish the line (no continued) so wrapping works normally
        doc.font("Helvetica").fontSize(10).text(tail, { continued: false, width: pageWidth });
      } else if (isFirstSegment) {
        // no matches and not tail -> just write paragraph
        doc.font("Helvetica").fontSize(10).text(p, { continued: false, width: pageWidth });
      } else {
        // matched something but no tail; need to end continuation
        doc.text('', { continued: false, width: pageWidth });
      }
      doc.moveDown(0.5);
    }
  }

  // Render institutional section as plain text. The generator now produces a concise
  // bulleted list (e.g., "- Institution: Role"). Convert any pipe-table into bullets
  // and normalize markdown list markers.
  let instText = outputs.instVerified ?? "";
  // strip a leading bolded title if present
  const titleMarker = "**Institutional Framework for Climate Action**";
  if (instText.trim().startsWith(titleMarker)) {
    instText = instText.trim().slice(titleMarker.length).trimStart();
  }
  // convert markdown list markers (- or *) at line starts to a bullet glyph
  // If the generator left a Markdown pipe table, convert it into a bulleted "Institution: Role" list
  const instLines = instText.split(/\r?\n/);
  const tableHeaderIndex = instLines.findIndex((l) => /^\s*\|\s*Institution\s*\|\s*Role\s*\|/i.test(l));
  if (tableHeaderIndex !== -1) {
    // collect contiguous table lines starting from header
    const tableLines: string[] = [];
    let end = tableHeaderIndex;
    for (let i = tableHeaderIndex; i < instLines.length; i++) {
      if (/^\s*\|/.test(instLines[i])) {
        tableLines.push(instLines[i].trim());
        end = i;
      } else {
        break;
      }
    }
    // drop separator line like |---|---|
    const rows = tableLines.filter((l) => !/^\s*\|\s*-+/.test(l));
    // first row is header; subsequent rows are data
    const dataRows = rows.slice(1).map((r) => r.split("|").map((c) => c.trim()).filter(Boolean));
    // build bullet lines
    const bullets = dataRows.map((cols) => {
      const inst = cols[0] ?? "";
      const role = cols.slice(1).join("; ") ?? "";
      return `• ${inst}: ${role}`.trim();
    });
    // replace the table block in the original text with the bullets
    const pre = instLines.slice(0, tableHeaderIndex).join("\n");
    const post = instLines.slice(end + 1).join("\n");
      instText = [pre.trim(), bullets.join("\n"), post.trim()].filter(Boolean).join("\n\n");
  }

  // convert markdown list markers (- or *) at line starts to a bullet glyph
  instText = instText.replace(/^\s*-\s+/gm, '• ').replace(/^\s*\*\s+/gm, '• ');
  // render using markdown-aware helper so **bold** is shown in bold
  renderMarkdownPreservingBold(doc, instText);
  // separate sections: add page before the next section
  doc.addPage();

  doc.fontSize(14).font("Helvetica-Bold").text("National Policy Framework");
  doc.moveDown(0.25);
  // render policy section using same helper so policy/law titles in **bold** are rendered
  renderMarkdownPreservingBold(doc, outputs.policyVerified ?? "");

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
