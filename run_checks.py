"""
Запуск QA-чекеров.
Использование:
  python run_checks.py --url https://your-site.com                  # все чекеры
  python run_checks.py --url https://your-site.com --check links    # только ссылки
  python run_checks.py --url https://your-site.com --check console  # только консоль
"""
import argparse
from pathlib import Path
from datetime import datetime
from link_checker import check_links
from console_checker import check_console


SEVERITY_COLOR = {
    "ok":       "#1D9E75",
    "minor":    "#BA7517",
    "major":    "#D85A30",
    "critical": "#E24B4A",
}
SEVERITY_LABEL = {
    "ok": "Ок", "minor": "Minor", "major": "Major", "critical": "Critical",
}


def build_link_card(url: str, data: dict) -> str:
    color = SEVERITY_COLOR[data["severity"]]
    label = SEVERITY_LABEL[data["severity"]]
    analysis_html = data["analysis"].replace("\n", "<br>")

    rows = ""
    for r in data["results"]:
        status_color = "#1D9E75" if r["ok"] else "#E24B4A"
        icon = "img" if r["type"] == "image" else "lnk"
        short_url  = r["href"][:80] + ("..." if len(r["href"]) > 80 else "")
        short_text = r["text"][:40] + ("..." if len(r["text"]) > 40 else "")
        rows += f"""
        <tr>
          <td class="col-status" style="color:{status_color}">{r['status'] or 'ERR'}</td>
          <td class="col-type">[{icon}]</td>
          <td class="col-url" title="{r['href']}">{short_url}</td>
          <td class="col-text">{short_text}</td>
        </tr>"""

    return f"""
    <div class="card">
      <div class="card-header">
        <span class="name">Проверка ссылок</span>
        <span class="badge" style="background:{color}">{label}</span>
        <span class="stat">всего: {len(data['results'])} · сломано: {len(data['broken'])} · ок: {data['ok_count']}</span>
      </div>
      <p class="url"><a href="{url}" target="_blank">{url}</a></p>
      <div class="analysis"><pre>{analysis_html}</pre></div>
      <div class="table-wrap">
        <table class="link-table">
          <thead>
            <tr>
              <th class="col-status">Статус</th>
              <th class="col-type">Тип</th>
              <th class="col-url">URL</th>
              <th class="col-text">Текст</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </div>"""


def build_console_card(url: str, data: dict) -> str:
    color = SEVERITY_COLOR[data["severity"]]
    label = SEVERITY_LABEL[data["severity"]]
    analysis_html = data["analysis"].replace("\n", "<br>")

    all_items = data["errors"] + data.get("failed_requests", []) + data["warnings"]
    rows = ""
    for e in all_items:
        if e["type"] in ("error", "pageerror", "request_failed"):
            status_color = "#E24B4A"
        else:
            status_color = "#BA7517"
        short_text = e["text"][:200] + ("..." if len(e["text"]) > 200 else "")
        short_loc  = e["location"][:80] + ("..." if len(e["location"]) > 80 else "") if e["location"] else "—"
        rows += f"""
        <tr>
          <td class="col-status" style="color:{status_color}">{e['type']}</td>
          <td class="col-url">{short_text}</td>
          <td class="col-text">{short_loc}</td>
        </tr>"""

    table = f"""
      <div class="table-wrap">
        <table class="link-table">
          <thead>
            <tr>
              <th class="col-status">Тип</th>
              <th class="col-url">Сообщение</th>
              <th class="col-text">Расположение</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </div>""" if rows else ""

    failed_count = len(data.get("failed_requests", []))
    return f"""
    <div class="card">
      <div class="card-header">
        <span class="name">Проверка консоли</span>
        <span class="badge" style="background:{color}">{label}</span>
        <span class="stat">ошибок: {len(data['errors'])} · запросов упало: {failed_count} · предупреждений: {len(data['warnings'])}</span>
      </div>
      <p class="url"><a href="{url}" target="_blank">{url}</a></p>
      <div class="analysis"><pre>{analysis_html}</pre></div>
      {table}
    </div>"""


def generate_report(title: str, url: str, cards: list, out_path: Path):
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>{title} — {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, sans-serif; background: #f5f5f2; color: #2c2c2a; padding: 24px; }}
  h1 {{ font-size: 22px; font-weight: 500; margin-bottom: 4px; }}
  .meta {{ color: #888; font-size: 13px; margin-bottom: 32px; margin-top: 4px; }}
  .card {{ background: #fff; border-radius: 12px; padding: 24px; margin-bottom: 24px; border: 1px solid #e0ddd6; }}
  .card-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 8px; flex-wrap: wrap; }}
  .name {{ font-size: 17px; font-weight: 500; }}
  .stat {{ font-size: 13px; color: #888; margin-left: auto; }}
  .badge {{ color: #fff; font-size: 12px; padding: 2px 10px; border-radius: 99px; white-space: nowrap; }}
  .url {{ font-size: 12px; color: #888; margin-bottom: 16px; margin-top: 2px; }}
  .url a {{ color: #185FA5; text-decoration: none; }}
  .url a:hover {{ text-decoration: underline; }}
  .analysis pre {{ background: #f5f5f2; border-radius: 8px; padding: 14px; font-size: 13px; white-space: pre-wrap; margin-bottom: 16px; }}
  .table-wrap {{ overflow-x: auto; }}
  .link-table {{ width: 100%; border-collapse: collapse; font-size: 12px; table-layout: fixed; }}
  .link-table th {{ text-align: left; padding: 6px 10px; background: #f5f5f2; color: #888; font-weight: 500; }}
  .link-table td {{ padding: 5px 10px; border-top: 1px solid #f0ede6; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .link-table tr:hover td {{ background: #fafaf8; }}
  .col-status {{ width: 70px; font-weight: 500; }}
  .col-type   {{ width: 45px; color: #888; }}
  .col-url    {{ width: 55%; }}
  .col-text   {{ width: 25%; color: #888; }}
</style>
</head>
<body>
<h1>{title}</h1>
<p class="meta">Сгенерировано: {datetime.now().strftime('%d.%m.%Y %H:%M')} · {url}</p>
{''.join(cards)}
</body>
</html>"""
    out_path.write_text(html, encoding="utf-8")
    print(f"  [report] → {out_path}")


def run(url: str, check: str):
    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)

    if check in ("links", "all"):
        print("\n── Проверка ссылок")
        link_data = check_links(url)
        generate_report(
            title="Отчёт: ссылки",
            url=url,
            cards=[build_link_card(url, link_data)],
            out_path=out_dir / "report_links.html",
        )

    if check in ("console", "all"):
        print("\n── Проверка консоли")
        console_data = check_console(url)
        generate_report(
            title="Отчёт: консоль",
            url=url,
            cards=[build_console_card(url, console_data)],
            out_path=out_dir / "report_console.html",
        )

    print("\nГотово!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url",   required=True, help="URL страницы")
    parser.add_argument("--check", default="all",
                        choices=["all", "links", "console"],
                        help="Что проверять: all / links / console")
    args = parser.parse_args()
    run(args.url, args.check)