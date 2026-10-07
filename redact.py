#!/usr/bin/env python3
"""
Redact personal info from an HDFC credit card statement PDF.

Usage:
    pip install pymupdf
    python3 redact.py <input.pdf> <output.pdf> <password>

What it does:
  1. Opens the password-protected statement.
  2. Marks every hit of your personal info (see CONFIG below) as a redaction.
  3. Applies the redactions — text is removed from the content stream,
     NOT covered with a black box (covered text stays extractable).
  4. Saves the output UNENCRYPTED (no password needed afterwards), which is
     what you want for the parser spike.
  5. Re-opens the output and verifies none of the needles survive.
"""

import json
import re
import sys
from pathlib import Path

import pymupdf  # pip install pymupdf

# ─── CONFIG ────────────────────────────────────────────────────────────────
# Exact strings live in config.json (gitignored — never commit your personal
# data). Copy config.json.example to config.json and fill it in.
CONFIG_PATH = Path(__file__).resolve().parent / "config.json"


def load_exact_strings() -> list[str]:
    """Load personal exact strings from config.json."""
    if not CONFIG_PATH.exists():
        sys.exit(
            f"ERROR: {CONFIG_PATH} not found.\n"
            f"Copy config.json.example to config.json and fill in your "
            f"personal strings (name, email, address lines) first."
        )
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    strings = config.get("exact_strings", [])
    if not strings:
        print("WARNING: config.json has no exact_strings — your name/address "
              "will NOT be redacted. Fill it in before sharing the output.\n")
    return strings

# Regex patterns for structured info. Safe to leave as-is; extend if needed.
REGEX_PATTERNS = [
    r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",      # full card number
    r"\b\d{4}[\s-]?XXX[\s-]?XXXX[\s-]?\d{4}\b",          # 4311-XXXX-XXXX-1234 style
    r"\bXX{2,}\d{2,4}\b|\b\d{2,4}XX{2,}\b",              # XX1234 / 1234XX
    r"[\w.+-]+@[\w-]+\.[\w.]+",                          # email addresses
    r"\+91[\s-]?\d[\d\s-]{8,}\d",                        # +91 phone numbers
    r"\b[A-Z]{5}\d{4}[A-Z]\b",                           # PAN number
]
# ────────────────────────────────────────────────────────────────────────────


def redact_spans(page: "pymupdf.Page", compiled: list[re.Pattern]) -> int:
    """Regex-redact at the span level (keeps bboxes tight to the text)."""
    count = 0
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if any(p.search(span["text"]) for p in compiled):
                    page.add_redact_annot(pymupdf.Rect(span["bbox"]))
                    count += 1
    return count


def main() -> None:
    if len(sys.argv) != 4:
        sys.exit(f"usage: {sys.argv[0]} <input.pdf> <output.pdf> <password>")
    src, dst, password = sys.argv[1], sys.argv[2], sys.argv[3]

    exact_strings = load_exact_strings()

    doc = pymupdf.open(src)
    success = doc.authenticate(password)
    if success:
        print("File opened successfully")
    else:
        print("File not opened successfully")

    compiled = [re.compile(p) for p in REGEX_PATTERNS]
    exact_hits = regex_hits = 0

    for page in doc:
        for needle in exact_strings:
            for rect in page.search_for(needle):
                page.add_redact_annot(rect)
                exact_hits += 1
        regex_hits += redact_spans(page, compiled)
        page.apply_redactions()

    # Save unencrypted: drops the password requirement for the spike.
    doc.save(dst, encryption=pymupdf.PDF_ENCRYPT_NONE)
    doc.close()

    print(f"Redacted {exact_hits} exact-string hits and {regex_hits} regex hits.")

    # ── Verify: re-open and confirm nothing survives ──
    check = pymupdf.open(dst)
    compiled = [re.compile(p) for p in REGEX_PATTERNS]
    leaks: list[str] = []
    for i, page in enumerate(check, start=1):
        text = page.get_text()
        for needle in exact_strings:
            if needle.lower() in text.lower():
                leaks.append(f"page {i}: exact string still present: {needle!r}")
        for p in compiled:
            for m in p.findall(text):
                leaks.append(f"page {i}: pattern {p.pattern} matched: {m!r}")

    if leaks:
        print("FAILED verification — do NOT share this file:")
        for leak in leaks:
            print(f"  - {leak}")
        sys.exit(1)
    print(f"Verified clean: {dst} contains none of the configured needles.")


if __name__ == "__main__":
    main()
