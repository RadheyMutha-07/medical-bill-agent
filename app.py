#!/usr/bin/env python3
"""
app.py — Streamlit frontend for Medical Bill Error Finder Agent
"""

import os
import sys
import tempfile
import json
import html as _html
from pathlib import Path
from datetime import date

from dotenv import load_dotenv
load_dotenv()  # loads ANTHROPIC_API_KEY from .env

import streamlit as st
import streamlit.components.v1 as components

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="Medical Bill Error Finder",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def build_letter_text(analysis: dict) -> str:
    today    = date.today().strftime("%B %d, %Y")
    patient  = analysis.get("patient_name",  "Patient")
    provider = analysis.get("provider_name", "Healthcare Provider")
    dos      = analysis.get("date_of_service", "Unknown")
    total    = analysis.get("total_billed", 0.0)
    over     = analysis.get("total_estimated_overcharge", 0.0)
    errors   = analysis.get("errors_found", [])
    summary  = analysis.get("summary", "")

    lines = [
        "FORMAL MEDICAL BILLING DISPUTE LETTER",
        "=" * 64,
        f"Date: {today}",
        f"RE: Formal Billing Dispute — Date of Service: {dos}",
        f"    Total Billed: ${total:,.2f}  |  Errors: {len(errors)}  |  Est. Overcharge: ${over:,.2f}",
        "",
        f"FROM: {patient}",
        "      [Your Street Address]",
        "      [City, State ZIP]",
        "      [Your Phone]",
        "",
        f"TO:   Billing Department — {provider}",
        "      [Hospital Street Address]",
        "      [City, State ZIP]",
        "",
        "Dear Billing Department,",
        "",
        f"I am writing to formally dispute billing errors on my itemized statement for",
        f"services rendered on {dos}. My audit revealed {len(errors)} billing error(s)",
        f"resulting in an estimated overcharge of ${over:,.2f}.",
        "",
        "I request a written response and corrected bill within 30 days, per the",
        "No Surprises Act (Pub. L. 116-260) and applicable state consumer protection law.",
        "",
        f"DISPUTED ITEMS  ({len(errors)} error(s))",
        "-" * 64,
    ]

    for i, err in enumerate(errors, 1):
        etype = err.get("error_type", "UNKNOWN").replace("_", " ")
        item  = err.get("line_item", "N/A")
        desc  = err.get("description", "N/A")
        amt   = err.get("estimated_overcharge_amount", 0.0)
        rule  = err.get("regulation_or_rule_violated", "N/A")
        lines += [
            "",
            f"Error #{i}: {etype}  —  Overcharge: ${amt:,.2f}",
            f"  Line Item:   {item}",
            f"  Description: {desc}",
            f"  Rule:        {rule}",
        ]

    lines += [
        "",
        "-" * 64,
        f"TOTAL ESTIMATED OVERCHARGE: ${over:,.2f}",
        "",
        "AUDIT SUMMARY",
        "-" * 64,
        summary,
        "",
        "REQUESTED ACTIONS",
        "-" * 64,
        "1.  Suspend collection activity for all disputed amounts immediately.",
        "2.  Provide a fully corrected, itemized bill within 30 days.",
        "3.  Remove all duplicate, unbundled, and improperly coded charges.",
        "4.  Recalculate patient responsibility using corrected charges only.",
        "5.  If any disputed charge is believed valid, provide supporting documentation.",
        "6.  Confirm receipt of this dispute in writing within 10 business days.",
        "",
        "Sincerely,",
        "",
        "",
        patient,
        f"Date: {today}",
    ]
    return "\n".join(lines)


ERROR_STYLE = {
    "DUPLICATE_CHARGE":     {"color": "#ef4444", "label": "Duplicate Charge",  "bg": "#fee2e2"},
    "UNBUNDLING":           {"color": "#f97316", "label": "Unbundling",         "bg": "#ffedd5"},
    "UPCODING":             {"color": "#a855f7", "label": "Upcoding",           "bg": "#f3e8ff"},
    "BALANCE_BILLING":      {"color": "#3b82f6", "label": "Balance Billing",    "bg": "#dbeafe"},
    "SERVICE_NOT_RENDERED": {"color": "#ec4899", "label": "Phantom Service",    "bg": "#fce7f3"},
    "INCORRECT_QUANTITY":   {"color": "#f59e0b", "label": "Wrong Quantity",     "bg": "#fef3c7"},
}


def get_risk_level(n: int):
    if n == 0: return "NONE",   "#6b7280", "#f3f4f6"
    if n <= 2: return "LOW",    "#065f46", "#d1fae5"
    if n <= 4: return "MEDIUM", "#92400e", "#fef3c7"
    return         "HIGH",      "#991b1b", "#fee2e2"


def extract_from_upload(uploaded_file) -> str:
    from extractor import extract_text
    suffix = Path(uploaded_file.name).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    try:
        return extract_text(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def run_analysis(bill_text: str, eob_text=None, services=None):
    from agent import analyze_medical_bill
    from dispute_letter import generate_dispute_letter

    analysis = analyze_medical_bill(
        bill_text=bill_text,
        eob_text=eob_text,
        services_not_received=services if services else None,
    )
    output_dir = os.path.join(BASE_DIR, "output")
    os.makedirs(output_dir, exist_ok=True)
    pdf_path = os.path.join(output_dir, "dispute_letter_web.pdf")
    generate_dispute_letter(analysis, pdf_path)

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    st.session_state.analysis    = analysis
    st.session_state.pdf_bytes   = pdf_bytes
    st.session_state.analyzed    = True
    st.session_state.letter_text = build_letter_text(analysis)


# ── Session state defaults ────────────────────────────────────────────────────
for _k, _v in {"analysis": None, "pdf_bytes": None, "letter_text": None, "analyzed": False}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Load sample bill ──────────────────────────────────────────────────────────
SAMPLE_BILL_PATH = os.path.join(BASE_DIR, "sample_bills", "sample_bill.txt")
_sample_text = ""
if os.path.exists(SAMPLE_BILL_PATH):
    with open(SAMPLE_BILL_PATH, "r", encoding="utf-8") as _f:
        _sample_text = _f.read()


# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif; }

.main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1400px;
}

.section-hdr {
    font-size: 1.35rem;
    font-weight: 700;
    color: #021F3A;
    display: inline-block;
    border-bottom: 3px solid #02C39A;
    padding-bottom: 4px;
    margin-bottom: 1rem;
}

.step-card {
    background: white;
    border-radius: 10px;
    padding: 20px 14px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    border: 1px solid #e5e7eb;
}
.step-icon  { font-size: 1.9rem; margin-bottom: 7px; }
.step-num   { font-size: 0.67rem; font-weight: 700; text-transform: uppercase;
              letter-spacing: 0.1em; color: #1C7293; margin-bottom: 3px; }
.step-title { font-size: 0.9rem; font-weight: 600; color: #021F3A; }
.step-desc  { font-size: 0.74rem; color: #6b7280; margin-top: 5px; line-height: 1.4; }

div.stButton > button {
    background-color: #1C7293 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.6rem 1.5rem !important;
    font-weight: 600 !important;
    font-size: 0.93rem !important;
    transition: background-color 0.2s ease !important;
}
div.stButton > button:hover {
    background-color: #02C39A !important;
    color: white !important;
}
div.stDownloadButton > button {
    background-color: #02C39A !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
div.stDownloadButton > button:hover {
    background-color: #021F3A !important;
}

.sample-preview {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 14px;
    font-family: 'Courier New', monospace;
    font-size: 0.71rem;
    line-height: 1.5;
    max-height: 250px;
    overflow-y: auto;
    color: #374151;
    white-space: pre;
}

.letter-preview {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 20px 22px;
    font-family: 'Courier New', monospace;
    font-size: 0.8rem;
    line-height: 1.75;
    max-height: 430px;
    overflow-y: auto;
    color: #1f2937;
    white-space: pre-wrap;
}

.sidebar-stat {
    background: linear-gradient(135deg, #e0f2fe, #f0fdf4);
    border-radius: 10px;
    padding: 14px 16px;
    text-align: center;
    margin: 10px 0;
    border: 1px solid #bae6fd;
}

.disclaimer {
    background: #fef3c7;
    border: 1px solid #fde68a;
    border-radius: 8px;
    padding: 12px 14px;
    font-size: 0.77rem;
    color: #78350f;
    line-height: 1.55;
}

.metric-mini {
    background: white;
    border-radius: 12px;
    padding: 18px 14px;
    text-align: center;
    box-shadow: 0 2px 10px rgba(0,0,0,0.07);
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏥 MedBill Finder")
    st.markdown("---")
    st.markdown("### About This Tool")
    st.markdown(
        "AI-powered medical bill auditor that detects billing errors "
        "in hospital itemized bills and generates ready-to-send dispute letters "
        "backed by CMS rules and federal law."
    )
    st.markdown("---")
    st.markdown(
        '<div class="sidebar-stat">'
        '<div style="font-size:2rem;font-weight:700;color:#021F3A;">127</div>'
        '<div style="font-size:0.78rem;color:#1C7293;font-weight:600;'
        'text-transform:uppercase;letter-spacing:0.05em;">Bills Analyzed</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.markdown("### How to Use")
    st.markdown(
        "1. Upload your itemized hospital bill\n"
        "2. Add your EOB / insurance statement _(optional)_\n"
        "3. List services you didn't receive _(optional)_\n"
        "4. Click **Analyze My Bill**\n"
        "5. Review errors & download your dispute letter"
    )
    st.markdown("---")
    st.markdown(
        '<div class="disclaimer"><strong>Disclaimer:</strong> This tool provides '
        "analysis for informational purposes only and does not constitute legal or "
        "medical advice. Consult a qualified professional for your specific situation."
        "</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — Animated Stats Ticker
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-hdr">Did You Know?</div>', unsafe_allow_html=True)

components.html("""<!DOCTYPE html>
<html>
<head>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: transparent; font-family: 'Segoe UI', system-ui, sans-serif; }
  .row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; padding: 4px 2px 10px; }
  .card { background: white; border-radius: 12px; padding: 20px 14px 16px;
          text-align: center; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
  .c1 { border-top: 4px solid #ef4444; }
  .c2 { border-top: 4px solid #f59e0b; }
  .c3 { border-top: 4px solid #3b82f6; }
  .c4 { border-top: 4px solid #10b981; }
  .num { font-size: 2.5rem; font-weight: 700; color: #021F3A; line-height: 1.05; min-height: 3rem; }
  .sub { font-size: 0.82rem; color: #374151; margin-top: 6px; }
  .lbl { font-size: 0.7rem; color: #9ca3af; margin-top: 3px; font-weight: 600;
         text-transform: uppercase; letter-spacing: 0.06em; }
</style>
</head>
<body>
  <div class="row">
    <div class="card c1">
      <div class="num" id="s1">0%</div>
      <div class="sub">of hospital bills contain errors</div>
      <div class="lbl">Error Rate</div>
    </div>
    <div class="card c2">
      <div class="num" id="s2">$0</div>
      <div class="sub">average patient overcharge</div>
      <div class="lbl">Avg. Overcharge</div>
    </div>
    <div class="card c3">
      <div class="num" id="s3">0%</div>
      <div class="sub">of patients ever file a dispute</div>
      <div class="lbl">Dispute Rate</div>
    </div>
    <div class="card c4">
      <div class="num" id="s4">$0B</div>
      <div class="sub">in unclaimed overcharges annually</div>
      <div class="lbl">Unclaimed Annually</div>
    </div>
  </div>
<script>
function ease(t) { return 1 - Math.pow(1 - t, 3); }
function counter(id, end, dur, fmt) {
  const el = document.getElementById(id);
  const steps = Math.ceil(dur / 16);
  let step = 0;
  const iv = setInterval(() => {
    step++;
    const val = end * ease(Math.min(step / steps, 1));
    el.textContent = fmt(val);
    if (step >= steps) { clearInterval(iv); el.textContent = fmt(end); }
  }, 16);
}
window.addEventListener('load', () => {
  setTimeout(() => {
    counter('s1', 80,   1800, v => Math.round(v) + '%');
    counter('s2', 1300, 2000, v => '$' + Math.round(v).toLocaleString());
    counter('s3', 0.1,  2200, v => v.toFixed(1) + '%');
    counter('s4', 3.75, 2400, v => '$' + v.toFixed(2) + 'B');
  }, 250);
});
</script>
</body>
</html>""", height=148)

st.markdown("<br>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — How It Works
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-hdr">How It Works</div>', unsafe_allow_html=True)

STEPS = [
    ("📄", "Step 1", "Upload Bill",    "Upload your itemized bill — PDF, image, or text"),
    ("🔍", "Step 2", "Extract Text",   "AI-powered OCR extracts all line items & CPT codes"),
    ("🤖", "Step 3", "AI Analysis",    "Claude AI audits every charge against CMS rules"),
    ("🚨", "Step 4", "Flag Errors",    "Billing errors flagged with exact regulation citations"),
    ("📬", "Step 5", "Dispute Letter", "Professional PDF dispute letter generated instantly"),
]

flow_cols = st.columns([5, 1, 5, 1, 5, 1, 5, 1, 5])
for i, (icon, num, title, desc) in enumerate(STEPS):
    with flow_cols[i * 2]:
        st.markdown(
            f'<div class="step-card">'
            f'<div class="step-icon">{icon}</div>'
            f'<div class="step-num">{num}</div>'
            f'<div class="step-title">{title}</div>'
            f'<div class="step-desc">{desc}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
for arrow_pos in [1, 3, 5, 7]:
    with flow_cols[arrow_pos]:
        st.markdown(
            '<div style="display:flex;align-items:center;justify-content:center;'
            'font-size:1.5rem;color:#1C7293;padding-top:26px;">→</div>',
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — Upload Interface
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-hdr">Analyze Your Bill</div>', unsafe_allow_html=True)

left_col, right_col = st.columns([1.1, 0.9], gap="large")
analysis_error = None

with left_col:
    bill_file = st.file_uploader(
        "📄 Hospital Itemized Bill **(required)**",
        type=["pdf", "png", "jpg", "jpeg", "txt"],
        help="Upload your itemized hospital bill in PDF, image, or text format",
    )
    eob_file = st.file_uploader(
        "📋 EOB / Insurance Statement _(optional)_",
        type=["pdf", "png", "jpg", "jpeg", "txt"],
        help="Upload your Explanation of Benefits to detect balance billing errors",
    )
    services_input = st.text_area(
        "🚫 Services you did **NOT** receive _(one per line, optional)_",
        placeholder="Example:\nHolter Monitor\nPhysical Therapy Session",
        height=100,
    )
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_clicked = st.button("🔍  Analyze My Bill →", use_container_width=True)

    if analyze_clicked:
        if bill_file is None:
            st.error("⚠️  Please upload a hospital bill to analyze.")
        else:
            services = [s.strip() for s in services_input.strip().splitlines() if s.strip()]
            with st.spinner("Analyzing your bill with Claude AI… (15–40 seconds)"):
                try:
                    bill_text = extract_from_upload(bill_file)
                    eob_text  = extract_from_upload(eob_file) if eob_file else None
                    run_analysis(bill_text, eob_text, services or None)
                except Exception as exc:
                    analysis_error = str(exc)

with right_col:
    if not st.session_state.analyzed:
        preview_text = (_sample_text[:680] + "\n…") if len(_sample_text) > 680 else _sample_text
        st.markdown(
            '<div style="background:white;border-radius:12px;padding:18px 16px;'
            'box-shadow:0 2px 10px rgba(0,0,0,0.07);border:1px solid #e5e7eb;">'
            '<div style="font-size:0.93rem;font-weight:600;color:#021F3A;margin-bottom:10px;">'
            '📄 Sample Itemized Bill</div>'
            f'<div class="sample-preview">{_html.escape(preview_text)}</div>'
            '<div style="font-size:0.8rem;color:#374151;margin-top:12px;line-height:1.55;">'
            '<strong>What are CPT codes?</strong> 5-digit numbers describing every medical '
            'procedure. Hospitals use them to bill insurers — and they\'re frequently '
            'duplicated, upcoded, or unbundled to inflate your bill.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)
        sample_clicked = st.button("🧪  Try with Sample Bill", use_container_width=True)
        if sample_clicked:
            with st.spinner("Analyzing sample bill with Claude AI… (15–40 seconds)"):
                try:
                    run_analysis(_sample_text)
                except Exception as exc:
                    analysis_error = str(exc)
    else:
        st.markdown(
            '<div style="background:#d1fae5;border:1px solid #6ee7b7;border-radius:10px;'
            'padding:20px;text-align:center;">'
            '<div style="font-size:1.8rem;">✅</div>'
            '<div style="font-weight:600;color:#065f46;margin-top:6px;font-size:1rem;">Analysis Complete</div>'
            '<div style="font-size:0.8rem;color:#047857;margin-top:4px;">Scroll down to see your results</div>'
            '</div>',
            unsafe_allow_html=True,
        )

if analysis_error:
    st.error(
        f"**Analysis failed:** {analysis_error}\n\n"
        "Ensure `ANTHROPIC_API_KEY` is set in your environment."
    )

st.markdown("<br>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — Results Display
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.analyzed and st.session_state.analysis:
    import plotly.graph_objects as go

    analysis   = st.session_state.analysis
    errors     = analysis.get("errors_found", [])
    overcharge = analysis.get("total_estimated_overcharge", 0.0)
    total      = analysis.get("total_billed", 0.0)
    n_errors   = len(errors)
    risk_label, risk_fg, risk_bg = get_risk_level(n_errors)

    st.markdown("---")
    st.markdown('<div class="section-hdr">Audit Results</div>', unsafe_allow_html=True)

    # ── A) Summary Banner ─────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    pct = (overcharge / total * 100) if total > 0 else 0

    def _metric_card(col, big_val, label, border_color, text_color):
        col.markdown(
            f'<div class="metric-mini" style="border-top:4px solid {border_color};">'
            f'<div style="font-size:2.6rem;font-weight:700;color:{text_color};line-height:1;">{big_val}</div>'
            f'<div style="font-size:0.78rem;color:#6b7280;text-transform:uppercase;'
            f'letter-spacing:0.06em;margin-top:5px;">{label}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    _metric_card(c1, str(n_errors),          "Errors Found",    "#ef4444", "#dc2626")
    _metric_card(c2, f"${overcharge:,.0f}",  "Est. Overcharge", "#f59e0b", "#d97706")
    _metric_card(c3, f"${total:,.0f}",       "Total Billed",    "#3b82f6", "#1d4ed8")
    c4.markdown(
        f'<div class="metric-mini" style="border-top:4px solid {risk_fg};">'
        f'<div style="font-size:2.6rem;font-weight:700;color:{risk_fg};line-height:1;">{pct:.1f}%</div>'
        f'<div style="font-size:0.78rem;color:#6b7280;text-transform:uppercase;'
        f'letter-spacing:0.06em;margin-top:5px;">Overcharge %</div>'
        f'<div style="margin-top:8px;">'
        f'<span style="background:{risk_bg};color:{risk_fg};padding:4px 14px;'
        f'border-radius:20px;font-size:0.8rem;font-weight:700;">{risk_label} RISK</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    if not errors:
        st.success("🎉 No billing errors detected — your bill appears correct!")
    else:
        # ── B) Error cards  +  C/D Charts ─────────────────────────────────────
        err_col, chart_col = st.columns([1.05, 0.95], gap="large")

        with err_col:
            st.markdown(f"**{n_errors} Billing Error(s) Detected**")
            for i, err in enumerate(errors, 1):
                etype  = err.get("error_type", "UNKNOWN")
                style  = ERROR_STYLE.get(etype, {"color": "#6b7280", "label": etype, "bg": "#f3f4f6"})
                item   = err.get("line_item", "N/A")
                desc   = err.get("description", "N/A")
                amt    = err.get("estimated_overcharge_amount", 0.0)
                rule   = err.get("regulation_or_rule_violated", "N/A")
                color  = style["color"]
                bg     = style["bg"]
                label  = style["label"]
                title  = f"#{i} {label} — ${amt:,.2f} | {item[:55]}{'…' if len(item)>55 else ''}"

                with st.expander(title, expanded=(i == 1)):
                    st.markdown(
                        f'<div style="border-left:4px solid {color};padding-left:14px;">'
                        f'<span style="background:{bg};color:{color};padding:3px 10px;'
                        f'border-radius:14px;font-size:0.76rem;font-weight:700;">'
                        f'{label.upper()}</span>'
                        f'<div style="margin-top:10px;font-size:0.87rem;line-height:1.6;">'
                        f'<strong>Line item:</strong> {_html.escape(item)}<br>'
                        f'<strong>What\'s wrong:</strong> {_html.escape(desc)}<br>'
                        f'<strong>Est. overcharge:</strong> '
                        f'<span style="color:{color};font-weight:700;">${amt:,.2f}</span><br>'
                        f'<span style="color:#6b7280;font-size:0.8rem;">'
                        f'<strong>Rule violated:</strong> {_html.escape(rule)}</span>'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )

        with chart_col:
            # Aggregate by type
            type_totals: dict = {}
            for err in errors:
                k = err.get("error_type", "OTHER")
                type_totals[k] = type_totals.get(k, 0) + err.get("estimated_overcharge_amount", 0.0)

            labels  = [ERROR_STYLE.get(k, {"label": k})["label"]  for k in type_totals]
            amounts = list(type_totals.values())
            colors  = [ERROR_STYLE.get(k, {"color": "#6b7280"})["color"] for k in type_totals]

            # Bar chart
            bar = go.Figure(go.Bar(
                x=labels, y=amounts,
                marker_color=colors,
                text=[f"${a:,.0f}" for a in amounts],
                textposition="outside",
            ))
            bar.update_layout(
                title="Overcharges by Category",
                xaxis_title="Error Type", yaxis_title="Overcharge ($)",
                plot_bgcolor="white", paper_bgcolor="white",
                font=dict(family="Inter, system-ui, sans-serif", size=11),
                margin=dict(t=48, b=36, l=36, r=16),
                height=270, showlegend=False,
            )
            bar.update_xaxes(showgrid=False)
            bar.update_yaxes(gridcolor="#f0f0f0")
            st.plotly_chart(bar, use_container_width=True)

            # Pie chart
            pie = go.Figure(go.Pie(
                labels=labels, values=amounts,
                marker_colors=colors,
                hole=0.4,
                textinfo="percent+label",
                textfont_size=11,
            ))
            pie.update_layout(
                title="Overcharge Breakdown",
                plot_bgcolor="white", paper_bgcolor="white",
                font=dict(family="Inter, system-ui, sans-serif", size=11),
                margin=dict(t=48, b=16, l=16, r=16),
                height=270, showlegend=False,
            )
            st.plotly_chart(pie, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — Dispute Letter
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.analyzed and st.session_state.pdf_bytes:
    st.markdown("---")
    st.markdown('<div class="section-hdr">Your Dispute Letter</div>', unsafe_allow_html=True)

    letter_col, action_col = st.columns([1.4, 0.6], gap="large")
    letter_txt = st.session_state.letter_text or ""

    with letter_col:
        st.markdown("**Preview**")
        st.markdown(
            f'<div class="letter-preview">{_html.escape(letter_txt)}</div>',
            unsafe_allow_html=True,
        )

    with action_col:
        st.markdown("**Download & Share**")
        patient_name = (st.session_state.analysis or {}).get("patient_name", "patient")
        safe_name = "".join(c if c.isalnum() else "_" for c in patient_name.lower())[:20]

        st.download_button(
            label="⬇️  Download Dispute Letter PDF",
            data=st.session_state.pdf_bytes,
            file_name=f"dispute_letter_{safe_name}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # JS copy-to-clipboard button
        letter_js = json.dumps(letter_txt)
        components.html(
            f"""<button onclick="copyText()" id="cpbtn"
  style="background:#1C7293;color:white;border:none;border-radius:8px;
         padding:10px 0;font-size:0.92rem;font-weight:600;cursor:pointer;
         width:100%;transition:background 0.2s;">
  📋 Copy Letter Text
</button>
<div id="cpmsg" style="color:#065f46;font-size:0.8rem;margin-top:7px;
     display:none;text-align:center;">✅ Copied to clipboard!</div>
<script>
const t = {letter_js};
function copyText() {{
  navigator.clipboard.writeText(t).then(() => {{
    const b = document.getElementById('cpbtn');
    const m = document.getElementById('cpmsg');
    b.style.background = '#02C39A';
    b.textContent = '✅ Copied!';
    m.style.display = 'block';
    setTimeout(() => {{
      b.style.background = '#1C7293';
      b.textContent = '📋 Copy Letter Text';
      m.style.display = 'none';
    }}, 2500);
  }}).catch(() => alert('Copy failed — select and copy manually.'));
}}
</script>""",
            height=72,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        if st.session_state.analysis:
            summary = st.session_state.analysis.get("summary", "")
            if summary:
                st.markdown(
                    f'<div style="background:#f0fdf4;border:1px solid #bbf7d0;'
                    f'border-radius:10px;padding:14px;font-size:0.83rem;'
                    f'color:#065f46;line-height:1.6;">'
                    f'<strong>AI Summary</strong><br><br>{_html.escape(summary)}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    st.markdown("<br><br>", unsafe_allow_html=True)
