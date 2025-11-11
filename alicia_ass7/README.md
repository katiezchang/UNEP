# Alicia ASS6 — GEF8 PIF Sections

This small project generates two GEF8-style PIF sections (Institutional Framework for Climate Action and National Policy Framework) using an LLM, verifies them, and exports a PDF.

Quick start

1. Install dependencies:

```powershell
npm install
```

2. Set your OpenAI API key in an `.env` file at the project root:

```
OPENAI_API_KEY=your_key_here
```

3. Build:

```powershell
npm run build
```

4. Run (development):

```powershell
npm run dev
```

5. Generate and export PDF (build + render):

```powershell
npm run export:pdf
```

Files of interest

- `src/index.ts` — orchestrates generation and verification of both sections.
- `src/agents/generatorAgent.ts` — constructs the prompt and calls the LLM.
- `src/agents/verifierAgent.ts` — verifies and revises outputs.
- `src/pdfExport.ts` — renders the verified text to a PDF (supports inline **bold** and converts old markdown tables into bullets).

Notes

- The exporter supports rendering saved outputs from `exported_outputs.json` if present.
- The generator instructions request the institutional information as a bulleted list `Institution: Role` (one bullet per institution). The exporter converts older markdown tables into bullets when rendering.

Push checklist

- `npm run build` completes successfully
- `.env` is configured locally (do not commit your API key)
- `exported_sections.pdf` is generated if you run `npm run export:pdf`

If you want me to also create a `.gitignore` entry, or remove any dependency, tell me which dependency to remove and I will update `package.json` and `package-lock.json` accordingly.
