from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class SectionSpec:
    key: str
    title: str
    word_limit: Optional[int] = None
    standard_text: Optional[str] = None
    prompt: Optional[str] = None
    keep_existing_prompt: bool = False

SECTIONS: Dict[str, SectionSpec] = {
    "rationale_intro": SectionSpec(
        key="rationale_intro",
        title="A. PROJECT RATIONALE",
        prompt=('''Write a multi-paragraph narrative (summarize within token budget) covering context, drivers, objective, 
                baseline without project, envisioned outcomes, barriers, stakeholders, investment landscape, alignment with priorities.''')
    ),
    "paris_etf": SectionSpec(
        key="paris_etf",
        title="The Paris Agreement and the Enhanced Transparency Framework",
        standard_text=(
            '''As part of the UNFCCC, the Paris Agreement (2015) strengthened the global response to climate change. 
            Article 13 established the Enhanced Transparency Framework (ETF), under which Parties report on mitigation, 
            adaptation and support. These information requirements present challenges to all countries, particularly those 
            already facing impacts.'''
        )
    ),
    "climate_transparency_country": SectionSpec(
        key="climate_transparency_country",
        title="Climate Transparency in {Country}",
        word_limit=350,
        prompt=(
            '''Explain where {Country} is not yet fully complying with ETF requirements, actions to date, and a 'without project' trajectory. 
                Identify drivers that sustain the status quo and motivate urgency. What are key drivers that would maintain the status quo (or make it worse)? E.g. population growth, economic development, climate change, socio-cultural and political factors, including conflicts, or technological changes. i.e. based on existing trends, the country would continue to not report in accordance with the ETF. Drivers are important as we have to respond to these in the description of the project
                - Create one paragraph using BUR or BTR from https://unfccc.int/reports for {Cuba} under section 'Physical-geographical profile and climate' 
                and 'Population and social development' and other sections within BUR to describe current population and geographical climate. 
                Make sure to include specific numbers directly from these sections describing size, geographic features, inhabitants, and climate.
                - Create another paragraph describing its national framework, current reports (such as NIDs, NCDs, NCs, BURs, BTRs, and MRV system), include dates and other relevant figures.
                - Create another paragraph describing national strategy for energy transition and describe given information from the
                National Greenhouse Gas Inventory of its current emissions and current initiatives made under Paris Agreement to reduce GHG emissions. 
                Make sure to include specific statistics on emissions such as Carbon or Nitrogen, as well as what sectors emit the most GHGs)'''
        )
    ),
    "baseline_national_tf_header": SectionSpec(
        key="baseline_national_tf_header",
        title="1. National transparency framework",
        standard_text=(
            '''{Country} signed the UNFCCC on {UNFCCC_sign_date}, and ratified it on {UNFCCC_rat_date}. 
            It also ratified the Kyoto Protocol on {KP_rat_date}, and the Paris Agreement on {PA_rat_date}, 
            following its adoption in {PA_adopt_date}. The following sections describe {Country}'s institutional framework 
            for climate action, key legislation/policies, stakeholders, and ongoing transparency initiatives.'''
        ),
        prompt = ("Fill in the dates for UNFCCC, Kyoto Protocol, and Paris Agreement ratification/adoption and keep prompt as is.")
    ),
    "baseline_institutional": SectionSpec(
        key="baseline_institutional",
        title="i. Institutional Framework for Climate Action",
        word_limit=500,
        prompt=('''Describe the governmental institutional framework, lead ministry/agency, inter-ministerial coordination, legal mandates, 
                data sharing, and subnational roles."
                First establish insitutional system for climate transparency, mentioning keeping Biennial Update Reports, Biennial Transparency Reports, 
                and other reports agreed upon within the framework of United Nations and Paris Agreement up to date

                - Create another paragrpah describing {Country} state plan for confronting climate change
                - Create another paragraph describing insitutions providing data for reports found from PATPA and GEF CBIT documents
                - Create another paragraph describing several institutions with key roles for data collection, financial aspects, and 
                policies which can be found in BUR1, BTR 'Institutional arrangements and inventory management systems', NC, or ICAT sources for {Country} in https://unfccc.int/reports
                
                \nBe very in depth in the desciptions for institution and role.'''
                )
    ),
    "baseline_policy": SectionSpec(
        key="baseline_policy",
        title="ii. National Policy Framework",
        word_limit=500,
        prompt=(
            '''Describe national climate vision/targets (NDCs, LT-LEDS, climate acts) and ETF alignment/mandates.
            Create one paragraphthe national policy framework using BUR and NC under “National Circumstances” or “Legal and Institutional Framework” 
            as the foundational legal basis for climate and environmental policy referred to in GEF CBIT (Capacity-Building Initiative for Transparency) 
            most recent project documentation as the legal basis for {Country}'s ETF architecture, write in depth description on this. 
            - Add descriptions mentioned in NC (Annex I) and in later PATPA and ICAT materials describing national policy updates if possible
            - Continue adding descriptions from {Country} most updated NDC, and be quite in depth when laying out framework -- take into account 
            laws, decrees, stae plans for confronting climate change, NDCs, and national strategies
            - Create another paragraph outlining next steps for updates or missing gaps wihtin framework policies.'''
                )
    ),
    "baseline_stakeholders": SectionSpec(
        key="baseline_stakeholders",
        title="iii. Other key stakeholders for Climate Action",
        standard_text=("Non-government stakeholders for climate action are presented in Table 1."),
        prompt=(
        "Extract non-government stakeholders and leverageable activities for {Country} from authoritative sources.\n"
        "PRIMARY: UNFCCC reports (NCs, BURs, BTRs) country pages; SECONDARY: PATPA, ICAT, NDC Partnership, GEF CBIT, official MRV/ministry pages.\n"
        "CLASSIFY into these types: Civil Society (CSOs and NGOs), Private sector, Academia and research organizations, Financial institutions / MDBs, International organizations, [Other – to be specified].\n\n"
        "OUTPUT — Return EXACTLY one RFC-8259 JSON object with key 'body' whose value is a STRING containing this STRICT JSON object schema (no prose):\n"
        "{\n"
        "  \"table_data\": [\n"
        "    {\"type\": \"Civil Society (CSOs and NGOs)\", \"entries\": [\n"
        "      {\"name\": \"\", \"existing_activities\": \"\"}\n"
        "    ]},\n"
        "    {\"type\": \"Private sector\", \"entries\": [ {\"name\": \"\", \"existing_activities\": \"\"} ]},\n"
        "    {\"type\": \"Academia and research organizations\", \"entries\": [ {\"name\": \"\", \"existing_activities\": \"\"} ]},\n"
        "    {\"type\": \"Financial institutions / MDBs\", \"entries\": [ {\"name\": \"\", \"existing_activities\": \"\"} ]},\n"
        "    {\"type\": \"International organizations\", \"entries\": [ {\"name\": \"\", \"existing_activities\": \"\"} ]},\n"  
        "    {\"type\": \"[Other – to be specified]\", \"entries\": [ {\"name\": \"\", \"existing_activities\": \"\"} ]}\n"
        "  ]\n"
        "}\n\n"
        "RULES: max 8 entries per type; each 'existing_activities' value ≤200 chars; deduplicate by name; concise and factual (no marketing language). Be pretty descriptive in the activities and its direct relevance."
        )
    ),
    "baseline_unfccc_reporting": SectionSpec(
        key="baseline_unfccc_reporting",
        title="iv. Official reporting to the UNFCCC",
        standard_text=("To meet its obligations under the UNFCCC, the country has submitted several documents related to its socio-economic development objectives (see Table 2)."),
        prompt = (
            "TASK: Compile {Country}'s UNFCCC submissions from the official portal with precise dates and standardized names.\n"
            "SOURCE NAVIGATION (follow in order):\n"
            "  1) Go to https://unfccc.int/reports and filter for {Country} for author.\n"
            "  2) Capture all relevant submission types: National Communications (NC), NDC, IDC, Biennial Update Reports (BUR/BUR1), Biennial Transparency Reports (BTR),"
            "     National Inventory Documents/Reports (NID/NIR), Common Reporting Tables (CRT), Nationally Determined Contributions (NDC), and any formal updates. If contained under Document Name (with other words), make sure to identify and record this\n"
            "  3) For each item, parse the submission (or publication) date shown on the UNFCCC page under Submission Date or within the title of the name itself (Under Document Name); extract YEAR as YYYY.\n"
            "  4) Standardize 'report' names (e.g., 'First BUR', 'Second NDC', 'BTR1', 'NC5', 'NIR') depending on frequency of submission and date\n"
            "  5) Include the exact UNFCCC detail URL for traceability (store it only in the comment if helpful; do not add extra columns).\n"
            "  6) Sort rows by year DESC, deduplicate by (year + report name). There may be multiple entries but separate by year and display ALL. There should at least be up to 2024, so verify you can extract newest dates from the table provided.\n\n"

            "For each entry, extract and normalize the following fields:\n"
            "  1. year — YYYY parsed from the submission (or publication) date displayed on the UNFCCC page. Can also be extracted from Document Name (Usually {Country} YEAR then title of document\n"
            "  2. report — Standardized concise name (e.g., 'First BUR', 'Second NDC', 'BTR1', 'NC5', 'NIR', 'CRT') under Document Name.\n"
            "  3. comment — ≤120 characters summarizing transparency relevance; if possible, include the UNFCCC URL in parentheses.\n"
        
            "OUTPUT FORMAT:\n"
            "Return a single strict RFC-8259 JSON object with the key 'body', whose value is a STRING containing another JSON object with this schema:\n"
            "{\n"
            "  \"table_data\": [\n"
            "    {\"year\": <int>, \"report\": <string>, \"comment\": <string>}\n"
            "  ],\n"
            "  \"summary\": <string>\n"
            "}\n\n"

            "QUALITY RULES:\n"
            "- Prefer the submission (or publication) date shown by UNFCCC; do not infer.\n"
            "- Do not invent rows; if uncertain, omit and mention in summary. Avoid speculative years.\n"
            "- Ensure the latest available year is included if present.\n\n"

            "The 'summary' field must be one concise paragraph (≤150 words) noting coverage, any gaps/uncertainties, and whether all key report types (NC/BUR/BTR/NIR/CRT/NDC) were found.\n\n"

            "If no data is available, return: {\"body\": \"{\\\"table_data\\\": [], \\\"summary\\\": \\\"No reports found.\\\"}\"}."
                )

    ),
    "module_header": SectionSpec(
        key="module_header",
        title="2. Progress on the four Modules of the Enhanced Transparency Framework",
        standard_text=("The sections below outline status, progress, and challenges across the four core ETF modules."),
        prompt=("Just keep standard text as is.")
    ),
    "module_ghg": SectionSpec(
        key="module_ghg",
        title="i. GHG Inventory Module",
        prompt=(
        '''- Describe progress and gaps in GHG inventory (IPCC 2006, tiers, key categories, QA/QC, uncertainty, data systems, institutionalization).
        Summarize chronologically the country’s GHG inventory submissions (National Communications, Biennial Update Reports, 
        National Inventory Reports) with years and data coverage.
        - Describe the institutional arrangement for inventory preparation—lead agency, technical team, and coordination with sectoral ministries and statistical offices.
        - Identify which IPCC Guidelines and methodological tiers are applied per sector (Energy, IPPU, Agriculture, LULUCF, Waste).
        - Highlight improvements achieved (adoption of 2006/2019 Guidelines, QA/QC systems, MRV platforms).
        - Present key challenges: data fragmentation, capacity constraints, absence of country-specific emission factors, staff turnover, and integration into planning.
        - Reference any ongoing capacity-building initiatives (e.g., CBIT, ICAT, PATPA projects).
        - Conclude with recommendations aligned with the Enhanced Transparency Framework (ETF):technical training (Tier 2/3, uncertainty analysis), 
        institutionalization of MRV protocols, linkage with NDC implementation and national plans.'''
        )
    ),
    "module_adaptation": SectionSpec(
        key="module_adaptation",
        title="ii. Adaptation and Vulnerability Module",
        word_limit=400,
        prompt=("State whether an Adaptation Communication has been submitted. Summarize vulnerabilities, MRV status, data gaps, capacity, integration."
                "1. Describe the country’s geography and climatic context (coastal features, temperature, precipitation patterns, key ecosystems)."
                "2. Summarize observed climate trends and future projections (temperature, rainfall, sea level, extremes) using available data from national meteorological agencies or UNFCCC reports."
                "3. Explain how adaptation is integrated into national policy frameworks (e.g., National Adaptation Plan, state programs, NDC adaptation component, sectoral plans)."
                "4. Highlight existing research and knowledge systems on vulnerability and risk (HVR studies, scenario development, academic programs)."
                "5. Describe the status of monitoring and evaluation for adaptation actions and how it aligns with ETF paragraphs 104–117 of Decision 18/CMA.1."
                "6. Identify remaining gaps: lack of tracking indicators, limited local data, fragmented M&E frameworks, dependence on external projects."
                "7. Conclude with recommendations for strengthening adaptation governance, technical capacity, and integration with national planning systems.")
    ),
    "module_ndc_tracking": SectionSpec(
        key="module_ndc_tracking",
        title="iii. NDC Tracking Module",
        word_limit=400,
        prompt=("Use the existing project prompt for NDC tracking baseline, structured like the example: roles, pilots, templates, planning integration, "
                "gaps in mandates/tools/reporting cycles, subnational coverage."
                "Summarize the NDC’s mitigation and adaptation targets (six mitigation actions and 17 priority areas), "
                "the institutional arrangements defining roles across Energy, IPPU, Agriculture, LULUCF, and Waste, and "
                "the integration of these with the State Plan for Confronting Climate Change." 

                "Explain how the MRV system tracks progress, including achievements under the CBIT I Project for Agriculture and LULUCF, "
                "and identify gaps such as the absence of a digital platform, reliance on manual reporting, limited sectoral integration, and insufficient technical and financial capacity." 
                "Conclude with recommendations to automate and standardize reporting, strengthen institutional coordination, "
                "and align MRV processes with the National Development Plan (NDP) and Enhanced Transparency Framework (ETF) provisions."),
    ),
    "module_support": SectionSpec(
        key="module_support",
        title="iv. Support Needed and Received Module",
        word_limit=400,
        prompt=(
            '''Use the existing prompt for Support Needed & Received, structured like the example: finance needs/flows, tracking systems/templates, 
            mandates, gaps (disaggregation, alignment, off-budget), recommendations.
            Describe {Country}'s access to international climate finance, progress in establishing systems to track support needed and received,
            and remaining challenges. Summarize the institutional framework for climate finance (lead ministry or agency, coordination
            with national treasury and sectoral bodies), identify key barriers to accessing international funds 
            (e.g., eligibility constraints, accreditation challenges, or geopolitical/economic restrictions),
            and describe any Measurement, Reporting, and Verification (MRV) mechanisms being developed to monitor financial flows.
            Highlight quantitative information on support received where available (e.g., total financing mobilized, number of projects, 
            main sources or funds), and outline estimated financial needs for NDC implementation. "
            Discuss the role of multilateral climate funds (GCF, GEF, Adaptation Fund) and bilateral or private finance, 
            noting capacity gaps in data collection, tracking methodologies, or sectoral needs assessments. 
            Conclude with recommendations for finalizing and institutionalizing a comprehensive climate-finance MRV system, 
            strengthening transparency and reporting, and aligning financial-flow monitoring with national development planning 
            and the Enhanced Transparency Framework.'''
            ),
    ),
    "other_baseline_initiatives": SectionSpec(
        key="other_baseline_initiatives",
        title="Other baseline initiatives",
        standard_text=("This CBIT project is aligned with and complements other initiatives supported by the GEF and development partners in the Country, as outlined in Table below"),
        prompt = (
        "Build a country-specific table of transparency initiatives linked to the Enhanced Transparency Framework (ETF), "
        "covering programs from GEF, GCF, ICAT, the NDC Partnership, PMI, REDD+, and SDG-aligned initiatives. "
        "Use ONLY allowed sources; do not invent data. Populate up to 25 rows; if nothing is found, produce an empty table.\n\n"

        "Populate these fields per row:\n"
        "  1. program_project — Full official project/initiative name.\n"
        "  2. leading_entities — Implementing/coordinating ministries/agencies and key partners; join with '; '.\n"
        "  3. description — ≤300 characters; concise, factual objectives/components/outcomes.\n"
        "  4. duration — 'YYYY–YYYY' or 'YYYY–ongoing'.\n"
        "  5. value_usd — A plain number in USD with no commas/symbols (e.g., 12500000) or 'N/A' if unknown.\n"
        "  6. relation_to_etf — ≤200 characters on how it supports ETF/MRV (e.g., inventory, tracking NDCs, QA/QC).\n\n"

        "OUTPUT FORMAT (very important): Return EXACTLY one RFC-8259 JSON object with a single key 'body'. "
        "The value of 'body' must be a STRING containing a STRICT RFC-8259 JSON object with this schema:\n"
        "  {\"table_data\": [\n"
        "    {\n"
        "      \"program_project\": \"\",\n"
        "      \"leading_entities\": \"\",\n"
        "      \"description\": \"\",\n"
        "      \"duration\": \"\",\n"
        "      \"value_usd\": \"\",\n"
        "      \"relation_to_etf\": \"\"\n"
        "    }\n"
        "  ]}\n\n"
        "If no rows are found, return: {\"body\": \"{\\\"table_data\\\": []}\"}.\n"
        )
    ),
    "key_barriers": SectionSpec(
        key="key_barriers",
        title="Key barriers",
        prompt=(
            '''Summarize barriers around organizing climate data (Component 1), incomplete ETF modules/capacity (Component 2), 
            and reliance on projects/external consultants with limited use in planning (Components 1 & 3).'''
            )
    ),
    "barrier1": SectionSpec(
        key="Barrier1",
        word_limit=200,
        title="Barrier 1: {Country} lacks the capacity to systematically organize climate data",
        prompt=(
            '''This barrier corresponds to the project’s component 1. (1-2 paragraphs)
            Describe {Country}'s lack of a national (or strong) climate transparency system and insufficient institutional arrangements, 
            procedures, and protocols to allow for the collection of required data.'''
                )
    ),
    "barrier2": SectionSpec(
        key="barrier2",
        word_limit=200,
        title="Barrier 2: {Country}'s climate ETF modules for GHG Inventory, adaptation/vulnerability, NDC tracking, and support needed and received are incomplete and not fully aligned with ETF requirements.",
        prompt=(
            '''This barrier corresponds to the project’s component 2. (1-2 paragraphs)
            Describe {Country}'s limited technical content and related capacity on the four ETF chapters
            (mitigation/inventory, adaptation/vulnerability modelling, NDC tracking (both mitigation and adaptation),
             tracking of support needed and received'''
                )
    ),
    "barrier3": SectionSpec(
        key="barrier3",
        word_limit=200,
        title="Barrier 3: {Country} lacks capacity to consistently use its climate change information for reporting to the UNFCCC and for national planning without project-based financing and external consultants.",
        standard_text=('''
        While {Country} has demonstrated strong commitment by submitting multiple NCs, BURs, [and most recently its first BTR1], 
        the country’s reporting system relies heavily on project-based support and external expertise. 
        National reporting processes are not yet institutionalized or adequately funded through government budgets, 
        making them vulnerable to discontinuity once donor-funded projects conclude. This creates a dependency loop in which reporting quality 
        and frequency are linked to the availability of external financing and consultants, rather than sustained national capacity.
        Furthermore, climate data generated for international reporting is not routinely integrated into national planning or 
        development decision-making. Ministries and planning agencies often lack the tools, capacity, or incentives to use transparency 
        outputs—such as emissions data or climate finance tracking—in their sectoral strategies or policy formulation. 
        This weakens the feedback loop between transparency and implementation, reducing the impact of climate information on real-world outcomes.
        The lack of institutional ownership and mainstreamed use of transparency findings across the policy landscape undermines 
        {Country}’s ability to align its national development priorities with its climate commitments. 
        Strengthening internal capacity, operationalizing the national transparency platform for dual reporting and planning functions,
         and embedding transparency workflows into regular government systems are therefore essential for long-term sustainability and 
        compliance with ETF obligations.''' 
        )
    ),
}
