# Power BI Dashboard Scraper

Loads a public Power BI dashboard in headless Chromium (Playwright), extracts ARIA tables, and writes `dashboard.json`.

## Run on GitHub Actions
- Workflow runs **every 8 hours** and on **manual dispatch**.
- On failure, see `Artifacts` in the run for `page.png` / `frame.html`.

## Local run (optional)
```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
playwright install chromium
python scraper.py
