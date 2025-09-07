import asyncio
import json
import os
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

URL = os.environ.get(
    "POWERBI_URL",
    "https://app.powerbi.com/view?r=eyJrIjoiNTBhMGQ2ZGYtM2EwYS00NjAyLTk2M2UtMDBlYzY1YTdjNTdjIiwidCI6ImRmZmRlOTRmLTcyZmItNDlhZS1hY2IyLTBiOTYxYWJkNWI0MSIsImMiOjN9"
)
OUT_PATH = os.environ.get("OUT_PATH", "dashboard.json")

ARTIFACT_DIR = Path("artifacts")
ARTIFACT_DIR.mkdir(exist_ok=True)

LONG_TIMEOUT = 120_000  # 120s


async def scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/123 Safari/537.36"
        )
        page = await ctx.new_page()
        page.set_default_timeout(LONG_TIMEOUT)

        try:
            # Power BI often has long-running network; don't wait for "networkidle"
            await page.goto(URL, wait_until="domcontentloaded", timeout=LONG_TIMEOUT)

            # The report is inside an iframe — wait for it to appear
            iframe_locator = page.locator("iframe")
            await iframe_locator.first.wait_for(timeout=LONG_TIMEOUT)
            frame = await iframe_locator.first.content_frame()
            if frame is None:
                raise RuntimeError("Power BI iframe not found / not accessible")

            frame.set_default_timeout(LONG_TIMEOUT)

            # Wait for any accessible table in the report (Power BI uses ARIA roles)
            # If your report uses a specific table title, you can narrow the selector.
            await frame.locator('[role="table"]').first.wait_for(timeout=LONG_TIMEOUT)

            # Extract all tables
            all_data = []
            tables = frame.locator('[role="table"]')
            count = await tables.count()
            for i in range(count):
                tbl = tables.nth(i)
                # Headers
                headers = []
                header_cells = tbl.locator('[role="columnheader"]')
                hcount = await header_cells.count()
                for h in range(hcount):
                    headers.append((await header_cells.nth(h).inner_text()).strip())

                # Rows
                rows = tbl.locator('[role="row"]')
                rcount = await rows.count()
                for r in range(rcount):
                    row = rows.nth(r)
                    # skip header rows that also have role=row
                    if await row.locator('[role="columnheader"]').count() > 0:
                        continue
                    cells = row.locator('[role="cell"]')
                    ccount = await cells.count()
                    values = []
                    for c in range(ccount):
                        values.append((await cells.nth(c).inner_text()).strip())

                    if headers and len(values) == len(headers):
                        all_data.append(dict(zip(headers, values)))
                    elif values:
                        all_data.append({f"col_{j}": v for j, v in enumerate(values)})

            with open(OUT_PATH, "w", encoding="utf-8") as f:
                json.dump(all_data, f, indent=2, ensure_ascii=False)

            print(f"Wrote {len(all_data)} records to {OUT_PATH}")

        except Exception as e:
            # Capture artifacts to debug (visible in Actions as uploaded artifacts)
            try:
                await page.screenshot(path=str(ARTIFACT_DIR / "page.png"), full_page=True)
                html = await page.content()
                (ARTIFACT_DIR / "page.html").write_text(html, encoding="utf-8")
                if 'frame' in locals() and frame:
                    fhtml = await frame.content()
                    (ARTIFACT_DIR / "frame.html").write_text(fhtml, encoding="utf-8")
            finally:
                print(f"[ERROR] {type(e).__name__}: {e}")
            raise
        finally:
            await ctx.close()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(scrape())
