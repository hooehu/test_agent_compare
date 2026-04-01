from pathlib import Path
from playwright.sync_api import sync_playwright


def take_screenshot(url: str, out_path: Path, width: int, height: int):
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--disable-web-security"])
        page = browser.new_page(viewport={"width": width, "height": height})

        page.goto(url, wait_until="networkidle", timeout=30000)

        # Ждём пока все img загрузятся
        page.wait_for_function("""
            () => Array.from(document.images).every(
                img => img.complete && img.naturalHeight > 0
            )
        """, timeout=15000)

        # Скроллим по шагам чтобы триггернуть lazy-load
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(800)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        page.wait_for_timeout(800)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(800)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)

        # Ещё раз ждём после скролла
        page.wait_for_function("""
            () => Array.from(document.images).every(
                img => img.complete && img.naturalHeight > 0
            )
        """, timeout=10000)

        page.add_style_tag(content="""
            *, *::before, *::after {
                animation: none !important;
                transition: none !important;
                caret-color: transparent !important;
            }
            ::-webkit-scrollbar { display: none !important; }
        """)

        page.screenshot(path=str(out_path), full_page=True)
        browser.close()
    print(f"  [browser] saved → {out_path} ({width}x{height})")