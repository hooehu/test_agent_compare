from pathlib import Path
from playwright.sync_api import sync_playwright


DEVICES = [
    {"name": "Mobile S",  "width": 320,  "height": 568},
    {"name": "Mobile L",  "width": 375,  "height": 812},
    {"name": "Tablet",    "width": 768,  "height": 1024},
    {"name": "Laptop",    "width": 1280, "height": 800},
    {"name": "Desktop",   "width": 1440, "height": 900},
]


def check_responsive(url: str, out_dir: Path) -> list:
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--window-size=1440,900"]
        )

        for device in DEVICES:
            print(f"  [responsive] {device['name']} ({device['width']}x{device['height']})...")

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": device["width"], "height": device["height"]}
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            try:
                page.wait_for_function("""
                    () => Array.from(document.images).every(
                        img => img.complete && img.naturalHeight > 0
                    )
                """, timeout=8000)
            except Exception:
                pass

            # Запускаем все проверки
            issues = _run_checks(page, device)

            page.add_style_tag(content="""
                *, *::before, *::after {
                    animation: none !important;
                    transition: none !important;
                    caret-color: transparent !important;
                }
                ::-webkit-scrollbar { display: none !important; }
            """)

            filename = f"responsive_{device['name'].lower().replace(' ', '_')}.png"
            out_path = out_dir / filename
            page.screenshot(path=str(out_path), full_page=True)
            context.close()

            severity = _detect_severity(issues)
            print(f"    severity: {severity} · проблем: {len(issues)}")

            results.append({
                "name":     device["name"],
                "width":    device["width"],
                "height":   device["height"],
                "path":     out_path,
                "issues":   issues,
                "severity": severity,
            })

        browser.close()

    return results


def _run_checks(page, device: dict) -> list:
    issues = []
    w = device["width"]

    # 1. Горизонтальный скролл
    try:
        overflow = page.evaluate("""
            () => document.documentElement.scrollWidth > window.innerWidth + 2
        """)
        if overflow:
            scroll_w = page.evaluate("() => document.documentElement.scrollWidth")
            issues.append({
                "type":    "error",
                "check":   "Горизонтальный скролл",
                "detail":  f"Контент шире экрана: {scroll_w}px вместо {w}px",
            })
    except Exception:
        pass

    # 2. Изображения шире контейнера
    try:
        wide_imgs = page.evaluate("""
            () => Array.from(document.querySelectorAll('img'))
                .filter(img => img.getBoundingClientRect().width > window.innerWidth + 2)
                .map(img => img.src.split('/').pop().slice(0, 60) || 'без имени')
                .slice(0, 5)
        """)
        for img in wide_imgs:
            issues.append({
                "type":   "error",
                "check":  "Картинка вылезает за экран",
                "detail": img,
            })
    except Exception:
        pass

    # 3. Текст обрезан или вылезает за контейнер
    try:
        clipped = page.evaluate("""
            () => Array.from(document.querySelectorAll('p, h1, h2, h3, h4, span, a, button, li'))
                .filter(el => el.scrollWidth > el.clientWidth + 2 && el.clientWidth > 0)
                .map(el => el.innerText.trim().slice(0, 60))
                .filter(t => t.length > 0)
                .slice(0, 5)
        """)
        for text in clipped:
            issues.append({
                "type":   "warning",
                "check":  "Текст обрезан",
                "detail": f'"{text}"',
            })
    except Exception:
        pass

    # 4. Мелкий шрифт (меньше 12px)
    try:
        small_fonts = page.evaluate("""
            () => {
                const seen = new Set();
                return Array.from(document.querySelectorAll('p, span, a, li, td, label'))
                    .filter(el => {
                        const size = parseFloat(window.getComputedStyle(el).fontSize);
                        const text = el.innerText.trim();
                        return size > 0 && size < 12 && text.length > 3;
                    })
                    .map(el => {
                        const size = parseFloat(window.getComputedStyle(el).fontSize);
                        const text = el.innerText.trim().slice(0, 40);
                        const key = `${size}:${text}`;
                        if (seen.has(key)) return null;
                        seen.add(key);
                        return `${size}px — "${text}"`;
                    })
                    .filter(Boolean)
                    .slice(0, 5);
            }
        """)
        for item in small_fonts:
            issues.append({
                "type":   "warning",
                "check":  "Мелкий шрифт (< 12px)",
                "detail": item,
            })
    except Exception:
        pass

    # 5. Кнопки слишком маленькие для тапа (< 44x44px) — только на мобильных
    if w <= 768:
        try:
            small_btns = page.evaluate("""
                () => {
                    const seen = new Set();
                    return Array.from(document.querySelectorAll(
                        'button:not([class*="icon"]):not([class*="logo"]):not([class*="close"]):not([class*="nav"]), ' +
                        'a.btn, a.button, a[class*="cta"], a[class*="primary"], ' +
                        'input[type="submit"], input[type="button"]'
                    ))
                    .filter(el => {
                        // Пропускаем скрытые и элементы внутри nav/header
                        if (el.closest('nav') || el.closest('header')) return false;
                        const r = el.getBoundingClientRect();
                        if (!r.width || !r.height) return false;
                        // Пропускаем иконки (квадратные маленькие элементы без текста)
                        const text = (el.innerText || '').trim();
                        if (!text && r.width < 50 && r.height < 50) return false;
                        return r.width < 44 || r.height < 44;
                    })
                    .map(el => {
                        const r = el.getBoundingClientRect();
                        const label = (el.innerText || el.value || el.getAttribute('aria-label') || '').trim().slice(0, 40);
                        const key = `${Math.round(r.width)}x${Math.round(r.height)}:${label}`;
                        if (seen.has(key)) return null;
                        seen.add(key);
                        return `${Math.round(r.width)}x${Math.round(r.height)}px — "${label}"`;
                    })
                    .filter(Boolean)
                    .slice(0, 5);
                }
            """)
            for btn in small_btns:
                issues.append({
                    "type": "warning",
                    "check": "Маленькая зона тапа (< 44px)",
                    "detail": btn,
                })
        except Exception:
            pass

    # 6. Бургер-меню на мобильном
    if w <= 768:
        try:
            has_burger = page.evaluate("""
                () => {
                    const selectors = [
                        '[class*="burger"]', '[class*="hamburger"]', '[class*="menu-toggle"]',
                        '[class*="nav-toggle"]', '[aria-label*="menu"]', '[aria-label*="Menu"]',
                        '[aria-expanded]'
                    ];
                    return selectors.some(s => {
                        try {
                            const el = document.querySelector(s);
                            if (!el) return false;
                            const r = el.getBoundingClientRect();
                            return r.width > 0 && r.height > 0;
                        } catch { return false; }
                    });
                }
            """)
            if not has_burger:
                issues.append({
                    "type":   "warning",
                    "check":  "Нет бургер-меню",
                    "detail": "На мобильном не обнаружен элемент мобильной навигации",
                })
        except Exception:
            pass


    # 7. CTA-кнопка видна в первом экране (above the fold)
    try:
        cta_visible = page.evaluate("""
            () => {
                const selectors = [
                    'button[class*="cta"]', 'a[class*="cta"]',
                    'button[class*="primary"]', 'a[class*="primary"]',
                    'button[class*="btn"]', '.btn-primary', '.button-primary'
                ];
                for (const s of selectors) {
                    try {
                        const el = document.querySelector(s);
                        if (!el) continue;
                        const r = el.getBoundingClientRect();
                        if (r.width > 0 && r.top >= 0 && r.bottom <= window.innerHeight) return true;
                    } catch {}
                }
                return null;
            }
        """)
        if cta_visible is False:
            issues.append({
                "type":   "warning",
                "check":  "CTA не видна above the fold",
                "detail": "Основная кнопка действия не видна без скролла",
            })
    except Exception:
        pass

    return issues


def _detect_severity(issues: list) -> str:
    if not issues:
        return "ok"
    errors   = [i for i in issues if i["type"] == "error"]
    warnings = [i for i in issues if i["type"] == "warning"]
    if errors:
        return "critical" if len(errors) > 3 else "major"
    if warnings:
        return "minor"
    return "ok"