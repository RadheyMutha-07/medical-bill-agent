"""
agent.py - Core Claude-powered medical billing analysis agent
Uses the Anthropic Python SDK to analyze bills and return structured JSON errors.
"""

import json
import re
from typing import Any, Dict, List, Optional

import anthropic

from rules import get_rules_context

# Exact system prompt as specified
SYSTEM_PROMPT = (
    "You are an expert medical billing auditor with 20 years of experience. "
    "You know every CPT code, CMS billing rule, and common hospital billing fraud pattern. "
    "When given the text of a hospital bill and/or EOB, you find every possible billing error. "
    "You are thorough, specific, and always cite the exact rule or regulation being violated. "
    "You respond only in valid JSON."
)

# Response schema description injected into the user prompt
RESPONSE_SCHEMA = """
Return ONLY a valid JSON object with this exact structure (no markdown, no explanation, just JSON):
{
  "patient_name": "full patient name from the bill",
  "provider_name": "hospital or provider name",
  "date_of_service": "date(s) of service",
  "total_billed": 0.00,
  "errors_found": [
    {
      "line_item": "exact description of the line item including CPT code and amount",
      "error_type": "DUPLICATE_CHARGE | UNBUNDLING | UPCODING | BALANCE_BILLING | SERVICE_NOT_RENDERED | INCORRECT_QUANTITY",
      "description": "detailed explanation of exactly why this is an error",
      "estimated_overcharge_amount": 0.00,
      "regulation_or_rule_violated": "specific CMS rule, NCCI edit, AMA guideline, or statute (be exact)"
    }
  ],
  "total_estimated_overcharge": 0.00,
  "summary": "2-3 sentence executive summary of all findings"
}
"""


def _build_user_message(
    bill_text: str,
    eob_text: Optional[str],
    services_not_received: Optional[List[str]],
    rules_context: str,
) -> str:
    """Construct the full analysis prompt."""
    parts = []

    parts.append("Analyze the following medical documents for ALL billing errors.\n")
    parts.append(rules_context)
    parts.append("\n\n=== ITEMIZED HOSPITAL BILL ===\n")
    parts.append(bill_text)

    if eob_text:
        parts.append("\n\n=== EXPLANATION OF BENEFITS (EOB) ===\n")
        parts.append(eob_text)
        parts.append(
            "\n\nIMPORTANT: Cross-reference the EOB with the bill. "
            "Check: (1) Does the amount the provider is billing the patient match "
            "EOB calculation (billed - insurance paid - adjustments)? "
            "Any excess is a BALANCE_BILLING error."
        )

    if services_not_received:
        parts.append("\n\n=== SERVICES PATIENT STATES THEY DID NOT RECEIVE ===\n")
        for svc in services_not_received:
            parts.append(f"  - {svc}")
        parts.append(
            "\n\nFlag any of the above as SERVICE_NOT_RENDERED errors if they appear on the bill."
        )

    parts.append(
        "\n\nCheck for ALL of the following error types:\n"
        "1. DUPLICATE_CHARGE: same CPT code billed more than once on the same day\n"
        "2. UNBUNDLING: CPT codes billed separately that CMS NCCI requires together\n"
        "3. UPCODING: billed CPT code description doesn't match the official CMS description\n"
        "4. BALANCE_BILLING: patient amount billed exceeds EOB-calculated responsibility\n"
        "5. SERVICE_NOT_RENDERED: patient states they didn't receive the service\n"
        "6. INCORRECT_QUANTITY: quantity billed doesn't match the documented service\n"
    )
    parts.append(RESPONSE_SCHEMA)

    return "\n".join(parts)


def _parse_response(content: str) -> Dict[str, Any]:
    """Extract and parse JSON from the Claude response."""
    # Try direct parse first
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences if present
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Last resort: find the outermost {...} block
    brace_match = re.search(r"\{[\s\S]*\}", content)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"Could not parse JSON from Claude response. First 500 chars:\n{content[:500]}"
    )


def analyze_medical_bill(
    bill_text: str,
    eob_text: Optional[str] = None,
    services_not_received: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Send the bill text to Claude for expert medical billing audit.

    Args:
        bill_text: Full extracted text of the itemized hospital bill.
        eob_text: Full extracted text of the EOB, if provided.
        services_not_received: List of services the patient says they didn't receive.

    Returns:
        Structured dict with errors_found, total_estimated_overcharge, etc.

    Raises:
        anthropic.AuthenticationError: If ANTHROPIC_API_KEY is missing or invalid.
        ValueError: If the response cannot be parsed as JSON.
    """
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment
    rules_context = get_rules_context()

    user_message = _build_user_message(
        bill_text=bill_text,
        eob_text=eob_text,
        services_not_received=services_not_received,
        rules_context=rules_context,
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text
    return _parse_response(raw)
