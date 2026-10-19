# Invoice Extractor Agent

Turns messy, free-text invoices into clean, **validated** JSON.

Real documents are inconsistent — different layouts, missing fields, odd date formats. This agent
uses an LLM to extract a fixed schema, then runs arithmetic and format checks so bad data never
passes silently. Extraction that you can actually trust on real-world inputs.

```
raw invoice text ──► LLM (structured extraction) ──► validation checks ──► clean JSON
```

## What it does

- Extracts a consistent schema (invoice number, supplier, dates, line items, totals)
- Forces valid JSON back from the model and uses `null` for anything missing — **never invents values**
- Validates the result:
  - dates parse as real `YYYY-MM-DD`
  - line items actually sum to the subtotal
  - subtotal + tax equals the total
- Flags every mismatch as a warning instead of trusting the model blindly

## Quick start

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...        # Windows: set OPENAI_API_KEY=sk-...

python extractor.py samples/invoice1.txt
python extractor.py samples/invoice1.txt --out result.json
```

## Example

Input (`samples/invoice1.txt`) is a messily formatted invoice. Output:

```json
{
  "invoice_number": "INV-2041",
  "supplier_name": "Brightwave Supplies Ltd",
  "invoice_date": "2026-03-14",
  "due_date": "2026-04-13",
  "currency": "GBP",
  "line_items": [
    { "description": "A4 paper (box)", "quantity": 10, "unit_price": 4.50 },
    { "description": "Printer toner", "quantity": 2, "unit_price": 38.00 }
  ],
  "subtotal": 121.00,
  "tax": 24.20,
  "total": 145.20
}
```

## Why the validation layer matters

LLMs extract well but occasionally miscopy a number or hallucinate a missing field. The validation
step catches exactly those failures — a total that doesn't add up, a date that won't parse — so a
human only reviews the invoices that actually need it. That "trust, but verify" pattern is what
makes LLM extraction safe to use on financial data.

## Possible extensions

- Read PDFs directly (add a text-extraction step)
- Batch a whole folder and write one CSV
- Post clean records into an accounting system via its API
