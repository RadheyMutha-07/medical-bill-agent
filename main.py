#!/usr/bin/env python3
"""
main.py - Medical Bill Error Finder Agent
Entry point: CLI interface for the medical billing audit workflow.
"""

import json
import os
import sys

# ── Ensure output directory exists ────────────────────────────────────────────
OUTPUT_DIR  = os.path.join(os.path.dirname(__file__), "output")
OUTPUT_PDF  = os.path.join(OUTPUT_DIR, "dispute_letter.pdf")
OUTPUT_JSON = os.path.join(OUTPUT_DIR, "analysis.json")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── Banner ────────────────────────────────────────────────────────────────────
BANNER = """
+--------------------------------------------------------------+
|        MEDICAL BILL ERROR FINDER AGENT  v1.0                |
|      Powered by Claude AI  |  Expert Billing Auditor         |
+--------------------------------------------------------------+
"""


def print_banner() -> None:
    # Force UTF-8 output on Windows so box chars survive; fall back gracefully
    import io
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    print(BANNER)


def print_divider(char: str = "─", width: int = 66) -> None:
    print(char * width)


# ── Input helpers ─────────────────────────────────────────────────────────────

def prompt_file(prompt: str, required: bool = True) -> str:
    """Ask for a file path; validate it exists. Returns "" if skipped."""
    while True:
        raw = input(prompt).strip()
        # Strip surrounding quotes that shells / Windows Explorer add
        path = raw.strip('"').strip("'")

        if not path:
            if required:
                print("  [!] This field is required. Please enter a valid file path.")
                continue
            return ""

        if not os.path.isfile(path):
            print(f"  [!] File not found: {path!r}")
            if not required:
                retry = input("  Skip this file and continue? (y/n): ").strip().lower()
                if retry == "y":
                    return ""
            continue

        return path


def prompt_services_not_received() -> list:
    """Collect a list of services the patient says they did not receive."""
    print("  Enter one service per line. Press Enter on a blank line when done.")
    print("  Example: Holter Monitor, Physical Therapy Session")
    services = []
    while True:
        line = input("  Service not received (or blank to finish): ").strip()
        if not line:
            break
        services.append(line)
    return services


# ── Pretty-print results ──────────────────────────────────────────────────────

def print_results(analysis: dict) -> None:
    print_divider("═")
    print("  AUDIT RESULTS")
    print_divider("═")
    print(f"  Patient:           {analysis.get('patient_name', 'N/A')}")
    print(f"  Provider:          {analysis.get('provider_name', 'N/A')}")
    print(f"  Date of Service:   {analysis.get('date_of_service', 'N/A')}")
    print(f"  Total Billed:      ${analysis.get('total_billed', 0):,.2f}")
    errors = analysis.get("errors_found", [])
    print(f"  Errors Found:      {len(errors)}")
    overcharge = analysis.get("total_estimated_overcharge", 0)
    print(f"  Est. Overcharge:   ${overcharge:,.2f}")
    print_divider()

    if not errors:
        print("  No billing errors detected. Your bill appears to be correct.")
        return

    for i, err in enumerate(errors, 1):
        etype = err.get("error_type", "UNKNOWN").replace("_", " ")
        print(f"\n  [{i}] {etype}")
        print(f"       Line Item:   {err.get('line_item', 'N/A')}")
        # Truncate long descriptions in CLI output
        desc = err.get("description", "N/A")
        if len(desc) > 120:
            desc = desc[:117] + "..."
        print(f"       Issue:       {desc}")
        print(f"       Overcharge:  ${err.get('estimated_overcharge_amount', 0):,.2f}")
        print(f"       Rule:        {err.get('regulation_or_rule_violated', 'N/A')[:90]}")

    print()
    print_divider()
    print(f"\n  SUMMARY: {analysis.get('summary', '')}")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print_banner()

    # Step 1 — Bill
    print_divider()
    print("  STEP 1: Itemized Hospital Bill (required)")
    print_divider()
    bill_path = prompt_file(
        "  Enter path to bill (PDF, image, or .txt file): ",
        required=True,
    )

    # Step 2 — EOB
    print()
    print_divider()
    print("  STEP 2: Explanation of Benefits / EOB (optional — press Enter to skip)")
    print_divider()
    eob_path = prompt_file(
        "  Enter path to EOB (PDF, image, or .txt), or press Enter to skip: ",
        required=False,
    )

    # Step 3 — Services not received
    print()
    print_divider()
    print("  STEP 3: Services You Did NOT Receive (optional — press Enter to skip)")
    print_divider()
    services_not_received = prompt_services_not_received()

    # Extract text
    print()
    print_divider()
    print("  Extracting text from document(s)...")
    print_divider()

    try:
        from extractor import extract_text
        bill_text = extract_text(bill_path)
        print(f"  ✓ Bill text extracted  ({len(bill_text):,} characters)")
    except Exception as exc:
        print(f"  [ERROR] Could not read bill: {exc}")
        sys.exit(1)

    eob_text = None
    if eob_path:
        try:
            from extractor import extract_text
            eob_text = extract_text(eob_path)
            print(f"  ✓ EOB text extracted   ({len(eob_text):,} characters)")
        except Exception as exc:
            print(f"  [WARNING] Could not read EOB: {exc}")
            eob_text = None

    # Analyse with Claude
    print()
    print_divider()
    print("  Sending to Claude AI for expert billing audit...")
    print("  (This typically takes 15–40 seconds)")
    print_divider()

    try:
        from agent import analyze_medical_bill
        analysis = analyze_medical_bill(
            bill_text=bill_text,
            eob_text=eob_text,
            services_not_received=services_not_received if services_not_received else None,
        )
    except Exception as exc:
        print(f"\n  [ERROR] Analysis failed: {exc}")
        print("  Make sure ANTHROPIC_API_KEY is set in your environment.")
        sys.exit(1)

    # Save raw JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2)

    # Print CLI summary
    print_results(analysis)

    # Generate PDF dispute letter
    print_divider()
    print("  Generating PDF dispute letter...")
    print_divider()

    try:
        from dispute_letter import generate_dispute_letter
        generate_dispute_letter(analysis, OUTPUT_PDF)
        print(f"\n  ✓ Dispute letter saved to:")
        print(f"    {OUTPUT_PDF}")
        print(f"\n  ✓ Raw analysis JSON saved to:")
        print(f"    {OUTPUT_JSON}")
    except Exception as exc:
        print(f"\n  [WARNING] Could not generate PDF dispute letter: {exc}")
        print(f"  Analysis saved as JSON: {OUTPUT_JSON}")

    print()
    print_divider("═")
    print("  All done! Review your dispute letter and send it to the hospital billing dept.")
    print_divider("═")
    print()


if __name__ == "__main__":
    main()
