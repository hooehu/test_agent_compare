from pathlib import Path
from playwright.sync_api import sync_playwright


def take_screenshot(url: str, out_path: Path, width: int, height: int):
    """Снимает скриншот строго в размере Figma-фрейма."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(1000)

        # Отключаем всё что мешает стабильному сравнению
        page.add_style_tag(content="""
            *, *::before, *::after {
                animation: none !important;
                transition: none !important;
                caret-color: transparent !important;
            }
            ::-webkit-scrollbar { display: none !important; }
        """)

        # Скриншот строго viewport — не full_page
        page.screenshot(path=str(out_path), full_page=False, clip={
            "x": 0, "y": 0, "width": width, "height": height
        })
        browser.close()
    print(f"  [browser] saved → {out_path} ({width}x{height})")