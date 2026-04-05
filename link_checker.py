import httpx
from pathlib import Path
from playwright.sync_api import sync_playwright


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def check_links(url: str, headless: bool = False) -> dict:
    print(f"  [links] собираю ссылки с {url}...")
    links = _collect_links(url, headless)
    print(f"  [links] найдено: {len(links)} ссылок и ресурсов")

    results = []
    for i, item in enumerate(links, 1):
        status = _check_url(item["href"])
        item["status"] = status
        item["ok"] = status in range(200, 400)
        results.append(item)
        # Показываем только прогресс и сломанные
        if not item["ok"]:
            print(f"    FAIL {status} → {item['href'][:80]}")
        elif i % 20 == 0:
            print(f"    проверено {i}/{len(links)}...")

    broken   = [r for r in results if not r["ok"]]
    ok_count = len(results) - len(broken)
    severity = _detect_severity(len(broken))
    analysis = _build_analysis(results, broken)

    return {
        "results":  results,
        "broken":   broken,
        "ok_count": ok_count,
        "severity": severity,
        "analysis": analysis,
    }


def _collect_links(url: str, headless: bool) -> list:
    items = []
    seen  = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

        anchors = page.eval_on_selector_all("a[href]", """
            els => els.map(el => ({
                href: el.href,
                text: el.innerText.trim().slice(0, 60) || el.getAttribute('href'),
                type: 'link'
            }))
        """)

        images = page.eval_on_selector_all("img[src]", """
            els => els.map(el => ({
                href: el.src,
                text: el.alt || el.src.split('/').pop().slice(0, 60),
                type: 'image'
            }))
        """)

        browser.close()

    for item in anchors + images:
        href = item["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        if href in seen:
            continue
        seen.add(href)
        items.append(item)

    return items


def _check_url(url: str) -> int:
    try:
        r = httpx.head(
            url, follow_redirects=True, timeout=10,
            headers={"User-Agent": USER_AGENT}
        )
        if r.status_code == 405:
            r = httpx.get(
                url, follow_redirects=True, timeout=10,
                headers={"User-Agent": USER_AGENT}
            )
        return r.status_code
    except Exception as e:
        print(f"    ERROR → {url[:60]}: {e}")
        return 0


def _detect_severity(broken_count: int) -> str:
    if broken_count == 0:
        return "ok"
    if broken_count <= 3:
        return "minor"
    if broken_count <= 10:
        return "major"
    return "critical"


def _build_analysis(results: list, broken: list) -> str:
    lines = [f"Проверено: {len(results)} ссылок и ресурсов\n"]
    if not broken:
        lines.append("Все ссылки работают.")
        return "\n".join(lines)

    lines.append(f"Сломано: {len(broken)}\n")
    for r in broken:
        icon = "img" if r["type"] == "image" else "link"
        short_url = r["href"][:100] + ("..." if len(r["href"]) > 100 else "")
        lines.append(f"  [{icon}] {r['status'] or 'ERR'} → {short_url}")
        if r["text"]:
            lines.append(f"           текст: {r['text']}")
    return "\n".join(lines)