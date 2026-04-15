"""
generate_sample_pdfs.py
Generates sample_bill.pdf and sample_eob.pdf in the sample_bills/ folder.
Uses fpdf2. Deliberately plants 3 billing errors + 1 balance billing discrepancy.
"""

import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "sample_bills")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Colors ────────────────────────────────────────────────────────────────────
NAVY        = (20,  55, 105)
WHITE       = (255, 255, 255)
LIGHT_BLUE  = (230, 240, 252)
DARK_GREY   = (40,  40,  40)
MID_GREY    = (100, 100, 100)
RED         = (180, 30,  30)
LIGHT_RED   = (253, 240, 240)
GREEN_BG    = (230, 248, 230)
ROW_ALT     = (245, 248, 255)
ROW_WHITE   = (255, 255, 255)


def safe(text: str) -> str:
    replacements = {
        "\u2014": "--", "\u2013": "-", "\u2018": "'", "\u2019": "'",
        "\u201c": '"',  "\u201d": '"', "\u2022": "*", "\u2026": "...",
        "\u00b7": ".",  "\u00ae": "(R)",
    }
    for ch, rep in replacements.items():
        text = text.replace(ch, rep)
    return text.encode("latin-1", errors="replace").decode("latin-1")


# ═════════════════════════════════════════════════════════════════════════════
#  BILL PDF
# ═════════════════════════════════════════════════════════════════════════════

class BillPDF(FPDF):
    def header(self):
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 28, "F")
        self.set_y(4)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*WHITE)
        self.cell(0, 8, "DALLAS REGIONAL MEDICAL CENTER", align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, "4200 Medical Pkwy, Dallas, TX 75201   |   Tel: (214) 555-0300   |   NPI: 1098765432", align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 6, "ITEMIZED HOSPITAL BILL  --  PATIENT COPY", align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*DARK_GREY)
        self.ln(8)

    def footer(self):
        self.set_y(-13)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*MID_GREY)
        self.cell(0, 10, safe("Dallas Regional Medical Center  |  Page " + str(self.page_no()) + "  |  CONFIDENTIAL PATIENT BILLING DOCUMENT"), align="C")
        self.set_text_color(*DARK_GREY)


def section_header(pdf, title):
    pdf.set_fill_color(*NAVY)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*WHITE)
    pdf.cell(0, 8, f"  {title}", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*DARK_GREY)
    pdf.ln(1)


def kv_row(pdf, key, val, key_w=58):
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(key_w, 6, key, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, val, new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def generate_bill_pdf(path: str):
    pdf = BillPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_left_margin(12)
    pdf.set_right_margin(12)
    pdf.add_page()

    # ── Patient Info ──────────────────────────────────────────────────────────
    section_header(pdf, "PATIENT INFORMATION")
    left = [
        ("Patient Name:",      "JOHN MARTINEZ"),
        ("Date of Birth:",     "08/22/1975"),
        ("Patient ID:",        "PT-2026-77291"),
        ("Account Number:",    "ACCT-2026-55814"),
        ("Admitting Physician:", "Dr. Kevin L. Nguyen, MD (NPI: 2109876543)"),
    ]
    right = [
        ("Insurance:",         "BlueCross BlueShield of Texas"),
        ("Insurance ID:",      "BCB-TX-4471829"),
        ("Group Number:",      "GRP-88234"),
        ("Primary Diagnosis:", "I21.9 - Acute MI, unspecified"),
        ("Secondary Dx:",      "E11.9 - Type 2 Diabetes, uncomplicated"),
    ]
    rows = max(len(left), len(right))
    for i in range(rows):
        lk, lv = left[i]  if i < len(left)  else ("", "")
        rk, rv = right[i] if i < len(right) else ("", "")
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(29, 6, lk, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(76, 6, lv, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(29, 6, rk, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, rv, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(3)

    # ── Stay Info ─────────────────────────────────────────────────────────────
    section_header(pdf, "ADMISSION DETAILS")
    kv_row(pdf, "Admission Date:",    "April 3, 2026  at 11:42 AM")
    kv_row(pdf, "Discharge Date:",    "April 5, 2026  at 02:15 PM  (2-night stay)")
    kv_row(pdf, "Ward:",              "Cardiac Care Unit  --  Room 412-B")
    kv_row(pdf, "Specialty:",         "Cardiology / Internal Medicine")
    pdf.ln(3)

    # ── Itemized Charges Table ────────────────────────────────────────────────
    section_header(pdf, "ITEMIZED CHARGES")

    # Table header
    pdf.set_fill_color(*NAVY)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*WHITE)
    cols = [10, 24, 18, 80, 14, 22]  # widths
    headers = ["#", "DATE", "CPT CODE", "DESCRIPTION", "QTY", "AMOUNT"]
    for w, h in zip(cols, headers):
        pdf.cell(w, 7, h, border=0, fill=True, align="C" if h in ("QTY","AMOUNT","#") else "L",
                 new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.ln(7)
    pdf.set_text_color(*DARK_GREY)

    # Line items  — errors marked with ***
    items = [
        # (line, date, cpt, description, qty, amount, note)
        ("001", "04/03/2026", "99213", "Office/Outpt Visit, Low-Mod Complexity E/M",         "1",  850.00,  "*** ERROR 1A: see billing note"),
        ("002", "04/03/2026", "99215", "Office/Outpt Visit, High Complexity E/M",             "1", 1250.00,  "*** ERROR 1B: see billing note"),
        ("003", "04/03/2026", "93000", "ECG, Routine 12-Lead with Interpretation",            "1",  210.00,  ""),
        ("004", "04/03/2026", "71046", "ROUTINE BLOOD PANEL - METABOLIC SCREEN",              "1",  480.00,  "*** ERROR 3: CPT/description mismatch"),
        ("005", "04/03/2026", "93454", "Coronary Arteriography, single catheter",             "1", 3200.00, ""),
        ("006", "04/03/2026", "93971", "Duplex Scan of Extremity Veins, unilateral",          "1",  340.00,  ""),
        ("007", "04/03/2026", "96365", "IV Infusion, Therapy, Initial, up to 1 hr",           "1",  280.00,  ""),
        ("008", "04/03/2026", "J3010", "Fentanyl Citrate 0.1 mg injection",                  "4",   60.00,  ""),
        ("009", "04/03/2026", "J1580", "Gentamicin Sulfate 80mg injection",                  "2",   74.00,  ""),
        ("010", "04/03/2026", "J2405", "Ondansetron HCl 1mg injection",                      "6",   96.00,  ""),
        ("011", "04/03/2026", "80053", "Comprehensive Metabolic Panel",                      "1",  145.00,  ""),
        ("012", "04/03/2026", "85025", "CBC with Automated Differential",                    "1",   75.00,  ""),
        ("013", "04/03/2026", "84484", "Troponin, Quantitative",                             "2",  190.00,  ""),
        ("014", "04/03/2026", "84443", "Thyroid Stimulating Hormone (TSH)",                  "1",   88.00,  ""),
        ("015", "04/03/2026", "36556", "Central Venous Catheter Insertion, non-tunneled",    "1",  520.00,  ""),
        ("016", "04/03/2026", "N/A",   "Medical Supplies - Cardiac Monitor Leads/Pads",      "1",  185.00,  ""),
        ("017", "04/03/2026", "N/A",   "Room & Board - Cardiac Care Unit (Night 1)",          "1",  950.00,  "*** ERROR 2A: billed 3x for 2-night stay"),
        ("018", "04/04/2026", "N/A",   "Room & Board - Cardiac Care Unit (Night 2)",          "1",  950.00,  "*** ERROR 2B: see billing note"),
        ("019", "04/05/2026", "N/A",   "Room & Board - Cardiac Care Unit (Night 3)",          "1",  950.00,  "*** ERROR 2C: only 2 nights authorized"),
        ("020", "04/04/2026", "99232", "Subsequent Hospital Care, Moderate Complexity",       "1",  185.00,  ""),
        ("021", "04/04/2026", "93040", "Rhythm ECG with Interpretation",                     "1",  130.00,  ""),
        ("022", "04/05/2026", "99238", "Hospital Discharge Day Management, <= 30 min",       "1",  145.00,  ""),
    ]

    for i, (line, dt, cpt, desc, qty, amt, note) in enumerate(items):
        fill_color = LIGHT_RED if "ERROR" in note else (ROW_ALT if i % 2 else ROW_WHITE)
        pdf.set_fill_color(*fill_color)
        pdf.set_font("Helvetica", "B" if "ERROR" in note else "", 8)

        data = [line, dt, cpt, safe(desc[:46]), qty, f"${amt:,.2f}"]
        aligns = ["C", "C", "C", "L", "C", "R"]
        for w, d, a in zip(cols, data, aligns):
            pdf.cell(w, 6, d, fill=True, align=a,
                     new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.ln(6)

        # Print note on red rows
        if note:
            pdf.set_font("Helvetica", "I", 7)
            pdf.set_text_color(*RED)
            pdf.set_fill_color(*LIGHT_RED)
            pdf.cell(10, 5, "", fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.cell(178, 5, safe(f"    NOTE: {note}"), fill=True,
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(*DARK_GREY)

    pdf.ln(2)

    # Totals row
    total = sum(a for *_, a, _ in items)
    pdf.set_fill_color(*NAVY)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*WHITE)
    pdf.cell(164, 8, "  TOTAL CHARGES:", fill=True, align="L",
             new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(22, 8, f"${total:,.2f}", fill=True, align="R",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*DARK_GREY)
    pdf.ln(5)

    # ── Billing Notes ─────────────────────────────────────────────────────────
    section_header(pdf, "BILLING NOTES")
    notes = [
        ("ERROR 1 (Lines 001-002):",
         "CPT 99213 (Low-Moderate Complexity E/M) and CPT 99215 (High Complexity E/M) "
         "were both billed on 04/03/2026 for the same encounter with the same provider (Dr. K. Nguyen, NPI 2109876543). "
         "Only one E/M code is permissible per encounter per provider per day."),
        ("ERROR 2 (Lines 017-019):",
         "Room & Board (Cardiac Care Unit at $950/night) has been billed for 3 nights. "
         "Per admission/discharge records, patient was admitted 04/03/2026 and discharged 04/05/2026 -- "
         "a 2-night stay. Only 2 nights of Room & Board ($1,900.00) are clinically supported. "
         "The third night charge ($950.00) is erroneous."),
        ("ERROR 3 (Line 004):",
         "CPT 71046 is the code for 'Radiologic examination, chest; 2 views'. However, "
         "this line item is described as 'ROUTINE BLOOD PANEL - METABOLIC SCREEN', which "
         "does not match the CPT code. This is a upcoding/misdescription error. "
         "Either the CPT code or the description is incorrect."),
    ]
    for title, body in notes:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*RED)
        pdf.cell(0, 6, f"  {title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*DARK_GREY)
        pdf.set_x(20)
        pdf.multi_cell(0, 5, safe(body), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

    # ── Charge Summary ────────────────────────────────────────────────────────
    section_header(pdf, "CHARGE SUMMARY")
    kv_row(pdf, "Total Charges:",              f"${total:,.2f}")
    kv_row(pdf, "Amount Billed to Insurance:", f"${total:,.2f}")
    kv_row(pdf, "Amount Billed to Patient:",   "$2,180.00")
    kv_row(pdf, "Payment Due Date:",           "May 10, 2026")
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*MID_GREY)
    pdf.multi_cell(0, 5, safe("For billing inquiries contact: billing@dallasregional.org  |  (214) 555-0399  |  Mon-Fri 8am-5pm CT"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*DARK_GREY)

    pdf.output(path)
    print(f"  [OK] Bill PDF written: {path}")


# ═════════════════════════════════════════════════════════════════════════════
#  EOB PDF
# ═════════════════════════════════════════════════════════════════════════════

class EOBPDF(FPDF):
    def header(self):
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 28, "F")
        self.set_y(4)
        self.set_font("Helvetica", "B", 15)
        self.set_text_color(*WHITE)
        self.cell(0, 8, "BLUECROSS BLUESHIELD OF TEXAS", align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, "1001 Commerce St, Dallas, TX 75201   |   Member Services: 1-800-555-BCBS   |   bcbstx.com", align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 6, "EXPLANATION OF BENEFITS (EOB)  --  THIS IS NOT A BILL", align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*DARK_GREY)
        self.ln(8)

    def footer(self):
        self.set_y(-13)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*MID_GREY)
        self.cell(0, 10, safe("BlueCross BlueShield of Texas  |  Page " + str(self.page_no()) + "  |  Retain this document for your records"), align="C")
        self.set_text_color(*DARK_GREY)


def generate_eob_pdf(path: str):
    pdf = EOBPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_left_margin(12)
    pdf.set_right_margin(12)
    pdf.add_page()

    # ── Member & Claim Info ───────────────────────────────────────────────────
    section_header(pdf, "MEMBER & CLAIM INFORMATION")
    left = [
        ("Member Name:",    "JOHN MARTINEZ"),
        ("Member ID:",      "BCB-TX-4471829"),
        ("Group Number:",   "GRP-88234"),
        ("Group Name:",     "TexasCorp LLC Employee Health Plan"),
        ("Plan Type:",      "PPO Platinum Plan"),
    ]
    right = [
        ("Claim Number:",   "CLM-2026-TX-881047"),
        ("Date Processed:", "April 18, 2026"),
        ("Provider:",       "DALLAS REGIONAL MEDICAL CENTER"),
        ("Provider NPI:",   "1098765432"),
        ("Claim Dates:",    "April 3, 2026 -- April 5, 2026"),
    ]
    for i in range(max(len(left), len(right))):
        lk, lv = left[i]  if i < len(left)  else ("", "")
        rk, rv = right[i] if i < len(right) else ("", "")
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(34, 6, lk, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(70, 6, lv, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(34, 6, rk, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, rv, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(3)

    # ── Line-by-Line Benefits ─────────────────────────────────────────────────
    section_header(pdf, "LINE-BY-LINE BENEFIT EXPLANATION")

    # Table header
    pdf.set_fill_color(*NAVY)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*WHITE)
    # line, cpt, description, billed, allowed, discount, plan_paid, member_resp
    col_w = [8, 16, 56, 20, 20, 18, 22, 24]
    hdrs  = ["#", "CPT", "SERVICE DESCRIPTION", "BILLED", "ALLOWED", "DISCOUNT", "PLAN PAID", "MEMBER RESP"]
    for w, h in zip(col_w, hdrs):
        pdf.cell(w, 7, h, fill=True, align="C", new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.ln(7)
    pdf.set_text_color(*DARK_GREY)

    # EOB rows  — mirrors bill items
    # format: (line, cpt, desc, billed, allowed, discount, plan_paid, member_resp)
    eob_rows = [
        ("001", "99213", "E/M Visit, Low-Mod Complexity",       850.00,  620.00, 230.00, 496.00, 124.00),
        ("002", "99215", "E/M Visit, High Complexity",         1250.00,  910.00, 340.00, 728.00, 182.00),
        ("003", "93000", "ECG 12-Lead w/ Interpretation",       210.00,  155.00,  55.00, 124.00,  31.00),
        ("004", "71046", "Chest X-Ray, 2 Views",                480.00,  350.00, 130.00, 280.00,  70.00),
        ("005", "93454", "Coronary Arteriography",             3200.00, 2400.00, 800.00,1920.00, 480.00),
        ("006", "93971", "Duplex Scan Extremity Veins",         340.00,  250.00,  90.00, 200.00,  50.00),
        ("007", "96365", "IV Infusion Therapy, Initial 1hr",    280.00,  205.00,  75.00, 164.00,  41.00),
        ("008", "J3010", "Fentanyl 0.1mg x4",                   60.00,   48.00,  12.00,  38.40,   9.60),
        ("009", "J1580", "Gentamicin 80mg x2",                  74.00,   56.00,  18.00,  44.80,  11.20),
        ("010", "J2405", "Ondansetron 1mg x6",                  96.00,   76.00,  20.00,  60.80,  15.20),
        ("011", "80053", "Comprehensive Metabolic Panel",       145.00,  110.00,  35.00,  88.00,  22.00),
        ("012", "85025", "CBC w/ Auto Differential",            75.00,   55.00,  20.00,  44.00,  11.00),
        ("013", "84484", "Troponin, Quantitative x2",           190.00,  145.00,  45.00, 116.00,  29.00),
        ("014", "84443", "TSH Assay",                           88.00,   64.00,  24.00,  51.20,  12.80),
        ("015", "36556", "Central Venous Catheter, non-tunnel", 520.00,  385.00, 135.00, 308.00,  77.00),
        ("016", "N/A",   "Medical Supplies",                   185.00,  142.00,  43.00, 113.60,  28.40),
        ("017", "N/A",   "Room & Board - CCU Night 1",          950.00,  720.00, 230.00, 576.00, 144.00),
        ("018", "N/A",   "Room & Board - CCU Night 2",          950.00,  720.00, 230.00, 576.00, 144.00),
        ("019", "N/A",   "Room & Board - CCU Night 3 (BILLED)", 950.00,  720.00, 230.00, 576.00, 144.00),
        ("020", "99232", "Subsequent Hospital Care, Moderate",  185.00,  140.00,  45.00, 112.00,  28.00),
        ("021", "93040", "Rhythm ECG with Interpretation",      130.00,   96.00,  34.00,  76.80,  19.20),
        ("022", "99238", "Hospital Discharge Management",       145.00,  108.00,  37.00,  86.40,  21.60),
    ]

    for i, row in enumerate(eob_rows):
        line, cpt, desc, billed, allowed, discount, plan_paid, member = row
        is_err = line in ("017", "018", "019") and line == "019"
        fill = ROW_ALT if i % 2 else ROW_WHITE
        pdf.set_fill_color(*fill)
        pdf.set_font("Helvetica", "", 7)
        vals = [line, cpt, safe(desc[:36]), f"${billed:,.2f}", f"${allowed:,.2f}",
                f"${discount:,.2f}", f"${plan_paid:,.2f}", f"${member:,.2f}"]
        aligns = ["C","C","L","R","R","R","R","R"]
        for w, v, a in zip(col_w, vals, aligns):
            pdf.cell(w, 6, v, fill=True, align=a, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.ln(6)

    pdf.ln(3)

    # Totals
    total_billed    = sum(r[3] for r in eob_rows)
    total_allowed   = sum(r[4] for r in eob_rows)
    total_discount  = sum(r[5] for r in eob_rows)
    total_plan_paid = sum(r[6] for r in eob_rows)
    total_member    = sum(r[7] for r in eob_rows)

    pdf.set_fill_color(*NAVY)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*WHITE)
    totals_vals = ["", "", "TOTALS", f"${total_billed:,.2f}", f"${total_allowed:,.2f}",
                   f"${total_discount:,.2f}", f"${total_plan_paid:,.2f}", f"${total_member:,.2f}"]
    for w, v, a in zip(col_w, totals_vals, ["C","C","L","R","R","R","R","R"]):
        pdf.cell(w, 8, v, fill=True, align=a, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.ln(8)
    pdf.set_text_color(*DARK_GREY)
    pdf.ln(4)

    # ── Benefit Summary ───────────────────────────────────────────────────────
    section_header(pdf, "BENEFIT SUMMARY")
    kv_row(pdf, "Total Amount Billed by Provider:",             f"${total_billed:,.2f}")
    kv_row(pdf, "Total Contractual Discounts/Adjustments:",     f"-${total_discount:,.2f}")
    kv_row(pdf, "Total Plan Allowed Amount:",                   f"${total_allowed:,.2f}")
    kv_row(pdf, "Total Amount Plan Paid (80% of allowed):",     f"${total_plan_paid:,.2f}  <-- Insurance Paid")
    kv_row(pdf, "EOB-Calculated Member Responsibility (20%):",  f"${total_member:,.2f}  <-- Correct Patient Owes")
    pdf.ln(3)

    # ── Balance Billing Alert ─────────────────────────────────────────────────
    section_header(pdf, "MEMBER BALANCE RECONCILIATION  --  *** DISCREPANCY ALERT ***")

    pdf.set_fill_color(*LIGHT_RED)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*RED)
    pdf.cell(0, 7, "  *** POTENTIAL BALANCE BILLING VIOLATION DETECTED ***",
             fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*DARK_GREY)
    pdf.ln(2)

    kv_row(pdf, "EOB-Calculated Patient Responsibility:", f"${total_member:,.2f}")
    kv_row(pdf, "Amount Provider is Billing Patient:",    "$2,180.00   *** EXCEEDS EOB AMOUNT ***")
    kv_row(pdf, "Discrepancy (Potential Balance Bill):",  f"${2180.00 - total_member:,.2f}")

    pdf.ln(3)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5,
        safe("Dallas Regional Medical Center is an IN-NETWORK provider under your PPO Platinum Plan. "
             "Under the provider's participation agreement with BCBS of Texas, balance billing beyond "
             "your calculated coinsurance is contractually prohibited. The $" + f"{2180.00 - total_member:,.2f}" +
             " difference constitutes a potential balance billing violation under the No Surprises Act "
             "(42 U.S.C. ss 300gg-111, effective Jan 1, 2022) and Texas state law. "
             "If you believe you have been overbilled, contact Member Services at 1-800-555-BCBS."),
        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

    # ── Deductible / OOP ──────────────────────────────────────────────────────
    section_header(pdf, "DEDUCTIBLE & OUT-OF-POCKET STATUS")
    kv_row(pdf, "Annual Deductible:",              "$1,500.00  (MET for plan year)")
    kv_row(pdf, "Out-of-Pocket Maximum:",          "$5,000.00")
    kv_row(pdf, "Out-of-Pocket Applied YTD:",      "$3,842.00")
    kv_row(pdf, "Out-of-Pocket Remaining:",        "$1,158.00")
    kv_row(pdf, "Dispute Deadline:",               "October 1, 2026  (180 days from EOB date)")
    pdf.ln(3)

    # ── Important Notices ─────────────────────────────────────────────────────
    section_header(pdf, "IMPORTANT NOTICES")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5,
        safe("Under the No Surprises Act, you have the right to dispute unexpected or incorrect medical bills. "
             "Contact BCBS of Texas Member Services within 180 days of this EOB to initiate a dispute. "
             "Denial reason codes applied: None (all services processed as submitted). "
             "Secondary review of duplicate E/M codes (Lines 001-002) and third Room & Board night (Line 019) is PENDING."),
        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

    # ── Remittance ────────────────────────────────────────────────────────────
    section_header(pdf, "PROVIDER REMITTANCE SUMMARY")
    kv_row(pdf, "Provider Paid:",       f"${total_plan_paid:,.2f}")
    kv_row(pdf, "EFT/Check Number:",    "EFT-2026-BCB-TX-44821")
    kv_row(pdf, "Payment Date:",        "April 22, 2026")
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*MID_GREY)
    pdf.cell(0, 5, safe("Questions? Call 1-800-555-BCBS (Mon-Fri 8am-8pm CT)  |  bcbstx.com/members"), align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*DARK_GREY)

    pdf.output(path)
    print(f"  [OK] EOB PDF written: {path}")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    bill_path = os.path.join(OUTPUT_DIR, "sample_bill.pdf")
    eob_path  = os.path.join(OUTPUT_DIR, "sample_eob.pdf")
    generate_bill_pdf(bill_path)
    generate_eob_pdf(eob_path)
    print("\nBoth PDFs generated successfully in sample_bills/")
