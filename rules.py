"""
rules.py - CPT bundling/unbundling rules logic
Loads rules from data/cpt_bundles.json and data/cpt_descriptions.json
and formats them as context for the Claude agent.
"""

import json
import os
from typing import Dict, Any

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_cpt_bundles() -> Dict[str, Any]:
    """Load CPT bundling rules from JSON."""
    path = os.path.join(DATA_DIR, "cpt_bundles.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_cpt_descriptions() -> Dict[str, str]:
    """Load CPT code descriptions from JSON."""
    path = os.path.join(DATA_DIR, "cpt_descriptions.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_rules_context() -> str:
    """
    Build a formatted rules context string to inject into the agent prompt.
    Includes bundling violations and CPT code correct descriptions.
    """
    bundles_data = load_cpt_bundles()
    descriptions = load_cpt_descriptions()

    lines = ["=== CMS CPT BUNDLING / UNBUNDLING RULES ==="]
    lines.append(
        "These are NCCI (National Correct Coding Initiative) rules from CMS. "
        "Billing the codes in each rule together on the same date/encounter is a violation.\n"
    )

    for rule in bundles_data.get("bundling_rules", []):
        lines.append(
            f"[{rule['rule_id']}] {rule['description']}\n"
            f"  Codes involved: {', '.join(rule['codes'])}\n"
            f"  Correct billing: {rule['correct_code']}\n"
            f"  CMS Reference: {rule['cms_reference']}\n"
        )

    lines.append("\n=== UPCODING RED FLAGS ===")
    for pattern in bundles_data.get("upcoding_patterns", []):
        lines.append(
            f"[{pattern['pattern_id']}] {pattern['description']}\n"
            f"  Watch for: {', '.join(pattern['flags'])}\n"
        )

    lines.append("\n=== CORRECT CPT CODE DESCRIPTIONS (use to detect upcoding/miscoding) ===")
    lines.append(
        "Compare each billed CPT code against its correct description below. "
        "Flag any mismatch between the billed description and the official description.\n"
    )
    for code, desc in descriptions.items():
        lines.append(f"  {code}: {desc}")

    return "\n".join(lines)
