from __future__ import annotations
from typing import Dict

def make_titles(country: str) -> Dict[str, str]:
    return {
        "rationale_intro": "A. PROJECT RATIONALE",
        "paris_etf": "The Paris Agreement and the Enhanced Transparency Framework",
        "climate_transparency_country": f"Climate Transparency in {country}",
        "baseline_national_tf_header": "1. National transparency framework",
        "baseline_institutional": "i. Institutional Framework for Climate Action",
        "baseline_policy": "ii. National Policy Framework",
        "baseline_stakeholders": "iii. Other key stakeholders for Climate Action",
        "baseline_unfccc_reporting": "iv. Official reporting to the UNFCCC",
        "module_header": "2. Progress on the four Modules of the Enhanced Transparency Framework",
        "module_ghg": "i. GHG Inventory Module",
        "module_adaptation": "ii. Adaptation and Vulnerability Module",
        "module_ndc_tracking": f"iii. NDC Tracking Module — {country}",
        "module_support": f"iv. Support Needed and Received — {country}",
        "other_baseline_initiatives": "Other baseline initiatives",
        "key_barriers": "Key barriers",
        "barrier1": f"Barrier 1: {country} lacks the capacity to systematically organize climate data",
        "barrier2": f"Barrier 2: {country}'s climate ETF modules for GHG Inventory, adaptation/vulnerability, NDC tracking, and support needed and received are incomplete and not fully aligned with ETF requirements.",
        "barrier3": f"Barrier 3: {country} lacks capacity to consistently use its climate change information for reporting to the UNFCCC and for national planning without project-based financing and external consultants.",
        "appendix_quality": "Appendix — Quality & Confidence Review",
    }
