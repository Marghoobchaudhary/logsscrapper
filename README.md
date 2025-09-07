# Power BI Dashboard Scraper

Scrapes data from the specified Power BI dashboard into a JSON file using Playwright.

## How to run locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python scraper.py
