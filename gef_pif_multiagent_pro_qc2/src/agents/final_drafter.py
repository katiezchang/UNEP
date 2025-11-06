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
        "appendix_quality": "Appendix — Quality & Confidence Review",
    }
