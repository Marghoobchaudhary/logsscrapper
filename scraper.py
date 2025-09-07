import asyncio
import json
import os
import pandas as pd
from playwright.async_api import async_playwright

URL = os.environ.get(
    "POWERBI_URL",
    "https://app.powerbi.com/view?r=eyJrIjoiNTBhMGQ2ZGYtM2EwYS00NjAyLTk2M2UtMDBlYzY1YTdjNTdjIiwidCI6ImRmZmRlOTRmLTcyZmItNDlhZS1hY2IyLTBiOTYxYWJkNWI0MSIsImMiOjN9"
)
OUT_PATH = os.environ.get("OUT_PATH", "dashboard.json")


async def scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(URL, wait_until="networkidle")

        # Wait for Power BI report to load
        await page.wait_for_timeout(5000)

        # Extract all table data from the DOM
        tables = await page.query_selector_all("table")
        all_data = []

        for t_idx, t in enumerate(tables):
            headers = await t.query_selector_all("thead tr th")
            header_text = [await h.inner_text() for h in headers] if headers else []

            rows = await t.query_selector_all("tbody tr")
            for r in rows:
                cells = await r.query_selector_all("td")
                row_text = [await c.inner_text() for c in cells]
                if header_text and len(row_text) == len(header_text):
                    record = dict(zip(header_text, row_text))
                else:
                    record = {"col_" + str(i): v for i, v in enumerate(row_text)}
                all_data.append(record)

        await browser.close()

        # Save JSON
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)

        print(f"Wrote {len(all_data)} records to {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(scrape())
