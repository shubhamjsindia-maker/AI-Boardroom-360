# AI Boardroom 360° — Runnable Level 1 MVP

Six-screen local educational prototype: sample or Excel company data → financial Digital Twin → five-role AI debate → advisory votes → scenario shocks → PDF decision report.

## Setup on Windows

1. Install Python 3.11 or 3.12 from python.org (select **Add Python to PATH**).
2. Extract the ZIP to a folder, open PowerShell in that folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

Open the localhost URL printed in the terminal (normally http://localhost:8501).

## Running the demo

1. Open **Data Studio**, click **Load demo company**, and download the sample workbook if desired.
2. Open **Digital Twin**, review assumptions and choose **Calculate & Save Scenario**.
3. Open **AI Boardroom**, use **Demo / offline** and click **Convene Board Meeting**. This mode is a repeatable rule-based illustration, **not real AI**.
4. Use **Shock Engine** to apply a customer-order cancellation, save the new scenario, then return to **AI Boardroom** to rerun the meeting.
5. Open **Reports**, select the meeting and download PDF.

### Live OpenAI debates

Set the key in the same PowerShell session before starting Streamlit:

```powershell
$env:OPENAI_API_KEY = 'your-own-key'
streamlit run app.py
```

Select **Live OpenAI API** on the Boardroom screen; the default model is `gpt-4.1-mini`. This needs internet/API access and may incur charges. A model with JSON-mode chat completion support is required. Never include API keys in an Excel workbook or share them with others. API responses are validated; a failed agent marks the meeting incomplete rather than fabricating votes. All transcript responses are persisted in the local SQLite database.

## Financial-methodology caveats

- INR lakh throughout; workbook import refuses non-INR-lakh units.
- Synthetic Nova Manufacturing example; not intended as financial advice.
- Simplified three-year model with fixed base EBITDA margin, receivable/inventory/payable day approximations, a basic cash-tax proxy, and annual end-of-period principal repayment. Existing debt interest is charged on the year's opening balance.
- Incremental project DSCR is only a *proxy* and **not** a full corporate or lender covenant DSCR. Year-one capital expenditure occurs at the start of the commissioning year.
- No fixed asset disposal, dividend, VAT/GST, tax losses, deferred tax, covenants, flexible EMI loan structure, or full integrated balance-sheet forecast.
- A customer-cancellation shock reduces expansion sales only. Input-cost inflation affects expansion variable expenses. The interest shock applies to the new loan; fixed existing debt remains unchanged.
- AI directors and votes are simulated advisers, not actual company directors, legally constituted meetings or resolutions. Offline mode is explicitly not LLM-powered.

## Test suite

```powershell
python -m pytest -q
```

The database `boardroom.sqlite3` is created when the application first runs. Local storage has no login or encryption; use only sample or properly authorized non-sensitive data. Do not expose this MVP to the public internet without authentication, encryption, security review and retention controls.

## Enhanced v1.1 — Chairperson's Challenge

The **AI Boardroom** screen now includes **Challenge the Board** after a meeting has completed. Choose one of the five directors, submit a question, and read a response grounded in the exact financial snapshot used for that meeting. Each exchange is saved in the meeting's record and included in the downloadable PDF.

- Live mode uses the configured OpenAI model. The answer must cite known financial metric keys; unrecognized keys are rejected.
- Offline mode is a deterministic **illustration** with a generic response; it does **not** interpret the actual question with AI.
- A chairperson question **never changes the previously saved advisory votes**. To modify financial assumptions, create a new scenario in Shock Engine and reconvene the directors.
- Round 1 of the live board meeting now keeps initial positions independent. Subsequent rounds only receive positions from completed earlier rounds.

### Known v1.1 limitations

The system is a local educational MVP, not a production financial-planning or multi-agent governance system. Director answers are advisory and may still misinterpret data despite structured metric validation. It does not support free-form financial recalculation from a typed chairperson question; use the scenario controls for that. Free-text responses should be reviewed before being shared. PDF reports reproduce the available analysis, not an audited opinion.


## Publish as a website

See **DEPLOY.md**. Hosting requires BOARDROOM_PASSWORD; anonymous users cannot access the shared database. Cloud local SQLite is ephemeral; use synthetic data.
