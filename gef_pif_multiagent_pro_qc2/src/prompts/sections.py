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
        prompt=("Write a multi-paragraph narrative (summarize within token budget) covering context, drivers, objective, "
                "baseline without project, envisioned outcomes, barriers, stakeholders, investment landscape, alignment with priorities.")
    ),
    "paris_etf": SectionSpec(
        key="paris_etf",
        title="The Paris Agreement and the Enhanced Transparency Framework",
        standard_text=(
            "As part of the UNFCCC, the Paris Agreement (2015) strengthened the global response to climate change. "
            "Article 13 established the Enhanced Transparency Framework (ETF), under which Parties report on mitigation, "
            "adaptation and support. These information requirements present challenges to all countries, particularly those "
            "already facing impacts."
        )
    ),
    "climate_transparency_country": SectionSpec(
        key="climate_transparency_country",
        title="Climate Transparency in {Country}",
        word_limit=350,
        prompt=("Explain where {Country} is not yet fully complying with ETF requirements, actions to date, and a 'without project' trajectory. "
                "Identify drivers that sustain the status quo and motivate urgency.")
    ),
    "baseline_national_tf_header": SectionSpec(
        key="baseline_national_tf_header",
        title="1. National transparency framework",
        standard_text=(
            "This is the baseline of Components 1 and 3 and corresponds to Barriers 1 and 3. "
            "{Country} signed the UNFCCC on {UNFCCC_sign_date}, and ratified it on {UNFCCC_rat_date}. "
            "It also ratified the Kyoto Protocol on {KP_rat_date}, and the Paris Agreement on {PA_rat_date}, "
            "following its adoption in {PA_adopt_date}. The following sections describe {Country}'s institutional framework "
            "for climate action, key legislation/policies, stakeholders, and ongoing transparency initiatives."
        )
    ),
    "baseline_institutional": SectionSpec(
        key="baseline_institutional",
        title="i. Institutional Framework for Climate Action",
        word_limit=500,
        prompt=("Describe the governmental institutional framework, lead ministry/agency, inter-ministerial coordination, legal mandates, "
                "data sharing, and subnational roles.")
    ),
    "baseline_policy": SectionSpec(
        key="baseline_policy",
        title="ii. National Policy Framework",
        word_limit=500,
        prompt=("Describe national climate vision/targets (NDCs, LT-LEDS, climate acts) and ETF alignment/mandates.")
    ),
    "baseline_stakeholders": SectionSpec(
        key="baseline_stakeholders",
        title="iii. Other key stakeholders for Climate Action",
        standard_text=("Non-government stakeholders for climate action are presented in Table 1."),
        prompt=("Provide a short narrative on CSOs/NGOs, private sector, academia, MDBs, international orgs, and leverage points.")
    ),
    "baseline_unfccc_reporting": SectionSpec(
        key="baseline_unfccc_reporting",
        title="iv. Official reporting to the UNFCCC",
        standard_text=("To fulfill its obligations under the UNFCCC, the country has submitted several documents..."),
        prompt=("Summarize major submissions (NCs, BURs/BTRs, NAP, NDCs) and highlight gaps relevant to CBIT scope.")
    ),
    "module_header": SectionSpec(
        key="module_header",
        title="2. Progress on the four Modules of the Enhanced Transparency Framework",
        standard_text=("The sections below outline status, progress, and challenges across the four core ETF modules.")
    ),
    "module_ghg": SectionSpec(
        key="module_ghg",
        title="i. GHG Inventory Module",
        prompt=("Describe progress and gaps in GHG inventory (IPCC 2006, tiers, key categories, QA/QC, uncertainty, data systems, institutionalization).")
    ),
    "module_adaptation": SectionSpec(
        key="module_adaptation",
        title="ii. Adaptation and Vulnerability Module",
        word_limit=400,
        prompt=("State whether an Adaptation Communication has been submitted. Summarize vulnerabilities, MRV status, data gaps, capacity, integration.")
    ),
    "module_ndc_tracking": SectionSpec(
        key="module_ndc_tracking",
        title="iii. NDC Tracking Module",
        word_limit=400,
        prompt=("Use the existing project prompt for NDC tracking baseline, structured like the example: roles, pilots, templates, planning integration, "
                "gaps in mandates/tools/reporting cycles, subnational coverage."),
        keep_existing_prompt=True
    ),
    "module_support": SectionSpec(
        key="module_support",
        title="iv. Support Needed and Received Module",
        word_limit=400,
        prompt=("Use the existing prompt for Support Needed & Received, structured like the example: finance needs/flows, tracking systems/templates, "
                "mandates, gaps (disaggregation, alignment, off-budget), recommendations."),
        keep_existing_prompt=True
    ),
    "other_baseline_initiatives": SectionSpec(
        key="other_baseline_initiatives",
        title="Other baseline initiatives",
        prompt=("Summarize relevant transparency initiatives (GEF, GCF, ICAT, NDC Partnership, PMI, REDD+, SDGs) and ETF linkage.")
    ),
    "key_barriers": SectionSpec(
        key="key_barriers",
        title="Key barriers",
        prompt=("Summarize barriers around organizing climate data (Component 1), incomplete ETF modules/capacity (Component 2), "
                "and reliance on projects/external consultants with limited use in planning (Components 1 & 3).")
    ),
}
