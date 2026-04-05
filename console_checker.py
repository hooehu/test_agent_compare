from playwright.sync_api import sync_playwright

# Шум который не относится к багам сайта — фильтруем
NOISE_PATTERNS = [
    "GL Driver Message",
    "GPU stall",
    "WebGL",
    "Tracking OTP",
    "Yandex.Metrica counter",
    "Data Extended",
]


def check_console(url: str) -> dict:
    print(f"  [console] открываю {url}...")
    errors, warnings, failed_requests = _collect_console(url)
    print(f"  [console] ошибок: {len(errors)} · предупреждений: {len(warnings)} · заблокированных запросов: {len(failed_requests)}")

    severity = _detect_severity(errors, warnings, failed_requests)
    analysis = _build_analysis(errors, warnings, failed_requests)

    return {
        "errors":           errors,
        "warnings":         warnings,
        "failed_requests":  failed_requests,
        "severity":         severity,
        "analysis":         analysis,
    }


def _is_noise(text: str) -> bool:
    return any(pattern in text for pattern in NOISE_PATTERNS)


def _collect_console(url: str) -> tuple:
    errors          = []
    warnings        = []
    failed_requests = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--window-size=1280,900"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900}
        )
        page = context.new_page()

        def on_console(msg):
            if _is_noise(msg.text):
                return
            entry = {
                "type":     msg.type,
                "text":     msg.text,
                "location": f"{msg.location.get('url', '')}:{msg.location.get('lineNumber', '')}",
            }
            if msg.type == "error":
                errors.append(entry)
            elif msg.type == "warning":
                warnings.append(entry)

        def on_pageerror(exc):
            if not _is_noise(str(exc)):
                errors.append({"type": "pageerror", "text": str(exc), "location": ""})

        def on_requestfailed(request):
            # Фильтруем рекламные/трекинговые домены — они блокируются намеренно
            skip_domains = ["adriver.ru", "mail.ru", "doubleclick.net", "google-analytics.com"]
            if any(d in request.url for d in skip_domains):
                return
            failed_requests.append({
                "type":     "request_failed",
                "text":     f"{request.method} {request.url}",
                "location": request.failure or "",
            })

        page.on("console",       on_console)
        page.on("pageerror",     on_pageerror)
        page.on("requestfailed", on_requestfailed)

        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1000)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)

        browser.close()

    return errors, warnings, failed_requests


def _detect_severity(errors: list, warnings: list, failed: list) -> str:
    if not errors and not warnings and not failed:
        return "ok"
    if not errors and not failed:
        return "minor"
    if len(errors) + len(failed) <= 3:
        return "major"
    return "critical"


def _build_analysis(errors: list, warnings: list, failed: list) -> str:
    if not errors and not warnings and not failed:
        return "JS-ошибок и предупреждений не обнаружено."

    lines = []

    if errors:
        lines.append(f"Ошибок: {len(errors)}\n")
        for e in errors:
            lines.append(f"  [error] {e['text'][:150]}")
            if e["location"]:
                lines.append(f"          в {e['location'][:100]}")

    if failed:
        lines.append(f"\nЗаблокированных/упавших запросов: {len(failed)}\n")
        for f in failed:
            lines.append(f"  [request] {f['text'][:150]}")
            if f["location"]:
                lines.append(f"            причина: {f['location'][:100]}")

    if warnings:
        lines.append(f"\nПредупреждений: {len(warnings)}\n")
        for w in warnings:
            lines.append(f"  [warn] {w['text'][:150]}")
            if w["location"]:
                lines.append(f"         в {w['location'][:100]}")

    return "\n".join(lines)