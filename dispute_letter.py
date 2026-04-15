"""
dispute_letter.py - Generates a formal medical billing dispute letter as a PDF
Uses fpdf2 library.
"""

import os
import unicodedata
from datetime import date
from typing import Any, Dict

from fpdf import FPDF
from fpdf.enums import XPos, YPos

# Replacement map for common Unicode chars not in Latin-1
_UNICODE_REPLACEMENTS = {
    "\u2014": "--",   # em dash
    "\u2013": "-",    # en dash
    "\u2018": "'",    # left single quote
    "\u2019": "'",    # right single quote
    "\u201c": '"',    # left double quote
    "\u201d": '"',    # right double quote
    "\u2022": "*",    # bullet
    "\u2026": "...",  # ellipsis
    "\u00b7": ".",    # middle dot
    "\u2122": "(TM)", # trademark
    "\u00ae": "(R)",  # registered
    "\u00a9": "(C)",  # copyright
}


def _safe(text: str) -> str:
    """Replace or strip characters that Helvetica (Latin-1) cannot encode."""
    for char, replacement in _UNICODE_REPLACEMENTS.items():
        text = text.replace(char, replacement)
    # Drop any remaining non-Latin-1 characters
    return text.encode("latin-1", errors="replace").decode("latin-1")


# ── Color palette ────────────────────────────────────────────────────────────
COLOR_HEADER_BG   = (30,  60, 114)   # deep navy
COLOR_HEADER_TEXT = (255, 255, 255)  # white
COLOR_SECTION_BG  = (235, 242, 252)  # light blue-grey
COLOR_ERROR_BG    = (253, 245, 230)  # warm cream
COLOR_ERROR_TITLE = (180,  30,  30)  # deep red
COLOR_TOTAL_BG    = (220,  50,  50)  # red
COLOR_TOTAL_TEXT  = (255, 255, 255)  # white
COLOR_BODY        = (30,   30,  30)  # near-black
COLOR_MUTED       = (100, 100, 100)  # grey


class _LetterPDF(FPDF):
    """Custom FPDF subclass with header / footer."""

    def __init__(self, patient_name: str, provider_name: str):
        super().__init__()
        self.patient_name  = patient_name
        self.provider_name = provider_name

    def header(self):
        # Navy banner
        self.set_fill_color(*COLOR_HEADER_BG)
        self.rect(0, 0, 210, 22, "F")
        self.set_y(5)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*COLOR_HEADER_TEXT)
        self.cell(0, 12, "FORMAL MEDICAL BILLING DISPUTE LETTER",
                  align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 8)
        self.cell(0, 6, _safe("CONFIDENTIAL -- Prepared by Medical Bill Error Finder Agent"),
                  align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*COLOR_BODY)
        self.ln(6)

    def footer(self):
        self.set_y(-13)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*COLOR_MUTED)
        self.cell(
            0, 10,
            _safe(f"Page {self.page_no()} | Dispute for {self.patient_name} vs {self.provider_name} | CONFIDENTIAL"),
            align="C",
        )
        self.set_text_color(*COLOR_BODY)


# ── Helper drawing helpers ────────────────────────────────────────────────────

def _section_title(pdf: _LetterPDF, title: str) -> None:
    pdf.set_fill_color(*COLOR_SECTION_BG)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*COLOR_HEADER_BG)
    pdf.cell(0, 9, f"  {title}", fill=True,
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*COLOR_BODY)
    pdf.ln(2)


def _kv_row(pdf: _LetterPDF, key: str, value: str, key_w: float = 52) -> None:
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(key_w, 6, key, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, value, new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _body_text(pdf: _LetterPDF, text: str, size: int = 10) -> None:
    pdf.set_font("Helvetica", "", size)
    pdf.multi_cell(0, 6, _safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)


# ── Main public function ──────────────────────────────────────────────────────

def generate_dispute_letter(analysis: Dict[str, Any], output_path: str) -> None:
    """
    Generate a formal dispute letter PDF from the structured analysis dict.

    Args:
        analysis: The JSON dict returned by agent.analyze_medical_bill().
        output_path: Absolute path where the PDF should be written.
    """
    today          = date.today().strftime("%B %d, %Y")
    patient_name   = _safe(analysis.get("patient_name",   "Patient"))
    provider_name  = _safe(analysis.get("provider_name",  "Healthcare Provider"))
    dos            = _safe(analysis.get("date_of_service", "Unknown"))
    total_billed   = analysis.get("total_billed",   0.0)
    overcharge     = analysis.get("total_estimated_overcharge", 0.0)
    errors         = analysis.get("errors_found",   [])
    summary        = _safe(analysis.get("summary",        ""))

    pdf = _LetterPDF(patient_name=patient_name, provider_name=provider_name)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)

    # ── Addresses block ───────────────────────────────────────────────────────
    _section_title(pdf, "PARTIES")

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(90, 6, "FROM (Patient / Sender):", new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(0,  6, "TO (Billing Department):", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 10)
    left_lines  = [patient_name, "[Your Street Address]", "[City, State  ZIP]",
                   "[Your Phone Number]", "[Your Email Address]"]
    right_lines = [f"Billing Dept - {provider_name}", "[Hospital Street Address]",
                   "[City, State  ZIP]", "[Billing Phone]"]

    rows = max(len(left_lines), len(right_lines))
    for i in range(rows):
        l = _safe(left_lines[i])  if i < len(left_lines)  else ""
        r = _safe(right_lines[i]) if i < len(right_lines) else ""
        pdf.cell(90, 6, l, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(0,  6, r, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(4)

    # ── Date + RE line ────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Date: {today}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    pdf.set_fill_color(*COLOR_SECTION_BG)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*COLOR_HEADER_BG)
    pdf.cell(0, 9,
             _safe(f"  RE: FORMAL BILLING DISPUTE -- Date of Service: {dos}  |  "
             f"Total Billed: ${total_billed:,.2f}  |  "
             f"Errors Found: {len(errors)}  |  "
             f"Claimed Overcharge: ${overcharge:,.2f}"),
             fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*COLOR_BODY)
    pdf.ln(5)

    # ── Opening paragraph ─────────────────────────────────────────────────────
    _section_title(pdf, "NOTICE OF DISPUTE")
    opening = (
        f"Dear Billing Department,\n\n"
        f"I am writing to formally dispute billing errors identified on my itemized "
        f"statement for services rendered on {dos}. A thorough audit of my hospital "
        f"bill and Explanation of Benefits (EOB) has revealed {len(errors)} billing "
        f"error(s) resulting in an estimated overcharge of ${overcharge:,.2f}.\n\n"
        f"Each error is documented below with the specific CMS rule, NCCI edit, or "
        f"regulation that has been violated. I request a written response and corrected "
        f"bill within 30 days, as required under the No Surprises Act (Pub. L. 116-260) "
        f"and applicable state consumer protection regulations."
    )
    _body_text(pdf, opening)

    # ── Errors ────────────────────────────────────────────────────────────────
    _section_title(pdf, f"DISPUTED ITEMS  ({len(errors)} error(s) identified)")

    for idx, err in enumerate(errors, start=1):
        error_type  = err.get("error_type", "UNKNOWN").replace("_", " ")
        line_item   = _safe(err.get("line_item",   "N/A"))
        description = _safe(err.get("description", "N/A"))
        amt         = err.get("estimated_overcharge_amount", 0.0)
        regulation  = _safe(err.get("regulation_or_rule_violated", "N/A"))

        # Error card header
        pdf.set_fill_color(*COLOR_ERROR_BG)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*COLOR_ERROR_TITLE)
        pdf.cell(0, 8, _safe(f"  Error #{idx}:  {error_type}  --  Overcharge: ${amt:,.2f}"),
                 fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(*COLOR_BODY)

        _kv_row(pdf, "Line Item:",        line_item)
        _kv_row(pdf, "Description:",      description)
        _kv_row(pdf, "Est. Overcharge:",  f"${amt:,.2f}")
        _kv_row(pdf, "Rule Violated:",    regulation)
        pdf.ln(4)

    # ── Total overcharge box ──────────────────────────────────────────────────
    pdf.set_fill_color(*COLOR_TOTAL_BG)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*COLOR_TOTAL_TEXT)
    pdf.cell(0, 11,
             f"  TOTAL ESTIMATED OVERCHARGE:  ${overcharge:,.2f}",
             fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*COLOR_BODY)
    pdf.ln(5)

    # ── Audit summary ─────────────────────────────────────────────────────────
    _section_title(pdf, "AUDIT SUMMARY")
    _body_text(pdf, summary)

    # ── Demands ───────────────────────────────────────────────────────────────
    _section_title(pdf, "REQUESTED ACTIONS")
    demands = [
        "1.  Immediately suspend any collection activity for disputed amounts.",
        "2.  Provide a fully corrected, itemized bill within 30 days.",
        "3.  Remove all duplicate, unbundled, and improperly coded charges.",
        "4.  Recalculate patient responsibility using the corrected charges only.",
        "5.  If any disputed charge is believed to be valid, provide supporting "
            "documentation (medical records, physician order, operative notes).",
        "6.  Confirm receipt of this dispute in writing within 10 business days.",
    ]
    for d in demands:
        _body_text(pdf, d)

    # ── Legal notice ──────────────────────────────────────────────────────────
    _section_title(pdf, "LEGAL NOTICE")
    legal = (
        "Please be advised that I am prepared to escalate this dispute to: "
        "(a) the Centers for Medicare & Medicaid Services (CMS) via the Medicare "
        "Administrative Contractor; (b) my state's Insurance Commissioner; "
        "(c) the No Surprises Act independent dispute resolution (IDR) process; "
        "and (d) pursue legal remedies under applicable consumer protection statutes "
        "if a satisfactory resolution is not provided within 30 days.\n\n"
        "Relevant statutes and regulations include:\n"
        "  • No Surprises Act, Division BB of the Consolidated Appropriations Act, 2021 "
        "(Pub. L. 116-260)\n"
        "  • 45 CFR Part 149 — Surprise Billing and Transparency Requirements\n"
        "  • CMS NCCI Policy Manual for Medicare Services (current year)\n"
        "  • State balance billing prohibition statutes (as applicable)"
    )
    _body_text(pdf, legal)

    # ── Closing ───────────────────────────────────────────────────────────────
    pdf.ln(3)
    _body_text(pdf,
        "I expect a written response directed to the address listed above.\n\n"
        "Sincerely,\n\n\n"
        f"{patient_name}\n"
        f"Date: {today}"
    )

    # ── Save ──────────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pdf.output(output_path)
