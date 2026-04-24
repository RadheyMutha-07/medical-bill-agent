# medical-bill-agent
# 🧾 MedBill Finder
### AI agent that reads your hospital bill, finds the errors, and writes your dispute letter.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Claude API](https://img.shields.io/badge/Built%20with-Claude%20API-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

## The Problem

**80% of medical bills contain at least one error.**  
The average overcharge is **$1,300**.  
Almost nobody disputes it — because the bills are deliberately unreadable.

MedBill Finder fixes that.

---

## What It Does

1. Upload your hospital itemized bill and/or EOB (Explanation of Benefits) as a PDF or image
2. The AI agent reads and cross-references every line item
3. Detects billing errors including:
   - Duplicate charges
   - Unbundling violations (CPT codes billed separately that must be billed together)
   - Upcoded procedures (description doesn't match the code billed)
   - Balance billing errors (math doesn't add up)
   - Services never received
   - Incorrect quantities
4. Generates a **formal dispute letter PDF** — ready to send to the hospital

---

## Demo

> Agent input: Hospital bill PDF  
> Agent output: "Line 14 — CPT 99213 + 99215 billed same day, same provider.  
> These cannot be billed separately. Estimated overcharge: $340."

<img width="1332" height="675" alt="image" src="https://github.com/user-attachments/assets/ea5021ce-e11a-4cb9-b55a-f8b87ffc0303" />
<img width="1332" height="675" alt="image" src="https://github.com/user-attachments/assets/e7bf8b95-d634-4ec8-bb87-03d708e67109" />
<img width="1332" height="675" alt="image" src="https://github.com/user-attachments/assets/cf2d8be8-1175-47f0-ab08-ee56b9fb9f84" />



---

## How to Run

```bash
# Clone the repo
git clone https://github.com/RadheyMutha-07/medical-bill-agent
cd medical-bill-agent

# Install dependencies
pip install -r requirements.txt

# Add your Anthropic API key
echo "ANTHROPIC_API_KEY=your_key_here" > .env

# Run the agent
python main.py
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| AI Agent Brain | Anthropic Claude API |
| PDF Extraction | PyMuPDF (fitz) |
| OCR for images | pytesseract |
| Dispute Letter | fpdf2 |
| Language | Python 3.10+ |

---

## Why This Matters

> 6.5 million Americans receive a wrong medical bill every single day.  
> Less than 0.1% ever dispute it.  
> MedBill Finder gives everyone the expert they never had.

---

## Built By

**Radhey Mutha**  **Nikhil Gajula** **Mohammed Munneb**
MS Student — Agentic AI, UT Dallas  
[GitHub](https://github.com/RadheyMutha-07)
