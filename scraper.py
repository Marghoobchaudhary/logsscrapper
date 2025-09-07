import asyncio
import json
import os
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = os.environ.get(
    "LOGS_PAGE_URL",
    "https://www.logs.com/mo-sales-report.html"
)
OUT_PATH = os.environ.get("OUT_PATH", "dashboard.json")

ARTIFACT_DIR = Path("artifacts")
ARTIFACT_DIR.mkdir(exist_ok=True)

async def scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=120000)

        # Wait for iframe and extract src
        iframe_el = page.locator("iframe").first
        await iframe_el.wait_for(timeout=60000)
        iframe_src = await iframe_el.get_attribute("src")
        if not iframe_src:
            raise RuntimeError("Could not find iframe src!")

        # Go to iframe directly
        await page.goto(iframe_src, wait_until="domcontentloaded", timeout=120000)
        await page.wait_for_timeout(10000)  # wait for table render

        rows = page.locator("div.mid-viewport div[role='row']")
        row_count = await rows.count()

        data = []
        keys = [
            "County", "Sale_date", "Sale_time", "FileNo",
            "PropAddress", "PropCity", "OpeningBid",
            "vendor", "status- DROP DOWN", "Foreclosure Status"
        ]

        for i in range(row_count):
            row = rows.nth(i)
            cells = row.locator("div[role='gridcell']")
            cell_count = await cells.count()

            # skip empty rows or header rows
            if cell_count <= 1:
                continue

            record = {
                "Trustee": "LOGS.COM",
                "Sale_date": "",
                "Sale_time": "",
                "FileNo": "",
                "PropAddress": "",
                "PropCity": "",
                "PropZip": "",
                "County": "",
                "OpeningBid": "",
                "vendor": "",
                "status- DROP DOWN": "",
                "Foreclosure Status": "",
            }

            # skip first cell (row index)
            for idx in range(1, cell_count):
                key_idx = idx - 1
                if key_idx < len(keys):
                    record[keys[key_idx]] = (await cells.nth(idx).inner_text()).strip()

            if record["FileNo"]:
                data.append(record)

        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"Wrote {len(data)} records to {OUT_PATH}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape())
