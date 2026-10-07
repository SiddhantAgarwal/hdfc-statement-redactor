# HDFC Statement Redactor

Redact personal information from password-protected HDFC credit card statement
PDFs, producing an unencrypted, share-safe output.

The script opens your statement, marks every match of your configured personal
info (exact strings and regex patterns) as a true PDF redaction — the text is
**removed from the content stream**, not covered with a black box — then saves
the result unencrypted and verifies none of the configured needles survive.

## Requirements

- [uv](https://docs.astral.sh/uv/) (the only prerequisite — it manages Python
  and all dependencies for you; you do **not** need Python installed)

### Installing uv (if you don't have it)

**macOS / Linux:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Or with Homebrew on macOS:

```bash
brew install uv
```

Restart your terminal afterwards so `uv` is on your `PATH`.

## Setup

1. Clone (or copy) this repo and `cd` into it:

   ```bash
   cd hdfc-statement-redactor
   ```

2. Create your personal config (never committed — it's gitignored):

   ```bash
   cp config.json.example config.json
   ```

   Edit `config.json` and fill in the exact strings from **your** statement —
   your name, email, masked phone, and every address line that appears in the
   statement header. These are matched case-sensitively.

3. Sync dependencies. uv downloads a matching Python automatically if none is
   installed, creates `.venv`, and installs everything:

   ```bash
   uv sync
   ```

That's it — no manual Python install, no `pip`, no virtualenv management.

## Usage

```bash
uv run redact.py <input.pdf> <output.pdf> <password>
```

- `<input.pdf>` — your password-protected HDFC statement
- `<output.pdf>` — where to write the redacted, unencrypted copy
- `<password>` — the statement's PDF password (HDFC usually sends this
  separately, often a combination of your birth date and card details)

Example:

```bash
uv run redact.py sample-statement.pdf sample-output.pdf 'MyPassword123'
```

The script prints how many exact-string and regex hits were redacted, then
re-opens the output and verifies none of the configured strings or patterns
survive. If verification fails it prints exactly what leaked and exits
non-zero — **do not share the output in that case**.

## What gets redacted

- Everything in `config.json` → `exact_strings` (your personal details)
- Regex-detected structured data: card numbers (full and masked formats),
  email addresses, `+91` phone numbers, and PAN numbers

## Linting

The repo uses [ruff](https://docs.astral.sh/ruff/):

```bash
uv run ruff check .        # lint
uv run ruff check --fix .  # lint + auto-fix
```

## Security notes

- `config.json` contains your personal data — it is gitignored; **never commit
  it**.
- Input and output PDFs also contain personal data (at minimum the input does);
  `*.pdf` is gitignored for the same reason.
- Redaction removes text from the PDF content stream. Always verify the
  output before sharing (the script does this automatically, but a quick
  visual check of page 1 is a good habit).