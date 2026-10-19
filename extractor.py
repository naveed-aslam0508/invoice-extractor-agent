"""
Invoice Extractor Agent
-----------------------
Turns messy, free-text invoices into clean, structured JSON you can trust.

Real-world documents are inconsistent: different layouts, missing fields, odd
date formats. This agent uses an LLM to extract a fixed schema, then validates
the result so bad data never passes silently.

Flow:
    raw invoice text ──► LLM (structured extraction) ──► validate ──► clean JSON

Usage:
    export OPENAI_API_KEY=sk-...
    python extractor.py samples/invoice1.txt
    python extractor.py samples/invoice1.txt --out result.json
"""

import argparse
import json
import sys
from datetime import datetime

from openai import OpenAI

MODEL = "gpt-4o-mini"

client = OpenAI()  # reads OPENAI_API_KEY from the environment

# The exact shape we want back, every time.
SCHEMA = {
    "invoice_number": "string or null",
    "supplier_name": "string or null",
    "invoice_date": "YYYY-MM-DD or null",
    "due_date": "YYYY-MM-DD or null",
    "currency": "3-letter code like GBP, or null",
    "line_items": [{"description": "string", "quantity": "number", "unit_price": "number"}],
    "subtotal": "number or null",
    "tax": "number or null",
    "total": "number or null",
}


def extract(raw_text: str) -> dict:
    """Ask the LLM to pull the schema out of the raw invoice text."""
    prompt = (
        "Extract the following fields from this invoice as JSON. "
        "Use null for anything missing — never invent a value. "
        "Dates must be YYYY-MM-DD. Numbers must be plain numbers (no currency symbols).\n\n"
        f"Target schema:\n{json.dumps(SCHEMA, indent=2)}\n\n"
        f"Invoice text:\n{raw_text}"
    )
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},  # force valid JSON back
    )
    return json.loads(resp.choices[0].message.content)


def validate(data: dict) -> list[str]:
    """Return a list of human-readable warnings. Empty list = looks clean."""
    warnings = []

    # Dates should parse
    for field in ("invoice_date", "due_date"):
        value = data.get(field)
        if value:
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                warnings.append(f"{field} is not a valid YYYY-MM-DD date: {value!r}")

    # Line items should add up to the subtotal (within a small rounding margin)
    items = data.get("line_items") or []
    computed = sum(
        (i.get("quantity") or 0) * (i.get("unit_price") or 0) for i in items
    )
    subtotal = data.get("subtotal")
    if subtotal is not None and items and abs(computed - subtotal) > 0.01:
        warnings.append(
            f"Line items sum to {computed:.2f} but subtotal says {subtotal:.2f}"
        )

    # Subtotal + tax should equal total
    sub, tax, total = data.get("subtotal"), data.get("tax"), data.get("total")
    if None not in (sub, tax, total) and abs((sub + tax) - total) > 0.01:
        warnings.append(f"subtotal ({sub}) + tax ({tax}) != total ({total})")

    return warnings


def main():
    parser = argparse.ArgumentParser(description="Extract structured data from an invoice.")
    parser.add_argument("file", help="Path to a plain-text invoice")
    parser.add_argument("--out", help="Write the JSON result to this file")
    args = parser.parse_args()

    with open(args.file, "r", encoding="utf-8", errors="ignore") as f:
        raw_text = f.read()

    if not raw_text.strip():
        sys.exit("The input file is empty.")

    data = extract(raw_text)
    warnings = validate(data)

    print(json.dumps(data, indent=2))

    if warnings:
        print("\n⚠️  Validation warnings:", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)
    else:
        print("\n✅ Passed validation checks.", file=sys.stderr)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\nSaved to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
