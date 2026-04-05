"""
Проверка адаптивности страницы.
Использование:
  python run_responsive.py --url https://your-site.com
"""
import argparse
import base64
from pathlib import Path
from datetime import datetime
from responsive_checker import check_responsive


SEVERITY_COLOR = {
    "ok":       "#1D9E75",
    "minor":    "#BA7517",
    "major":    "#D85A30",
    "critical": "#E24B4A",
}
SEVERITY_LABEL = {
    "ok": "Ок", "minor": "Minor", "major": "Major", "critical": "Critical",
}


def img_to_data_uri(path: Path) -> str:
    data = base64.b64encode(path.read_bytes()).decode()
    return f"data:image/png;base64,{data}"


def build_issues_list(issues: list) -> str:
    if not issues:
        return '<p class="no-issues">Проблем не обнаружено</p>'

    rows = ""
    for issue in issues:
        color = "#E24B4A" if issue["type"] == "error" else "#BA7517"
        rows += f"""
        <div class="issue">
          <span class="issue-badge" style="background:{color}">{issue['type']}</span>
          <span class="issue-check">{issue['check']}</span>
          <span class="issue-detail">{issue['detail']}</span>
        </div>"""
    return rows


def generate_report(url: str, results: list, out_path: Path):
    cards = ""
    for r in results:
        img_uri    = img_to_data_uri(r["path"])
        color      = SEVERITY_COLOR[r["severity"]]
        label      = SEVERITY_LABEL[r["severity"]]
        issues_html = build_issues_list(r["issues"])
        issue_count = len(r["issues"])
        stat = "проблем нет" if issue_count == 0 else f"проблем: {issue_count}"

        cards += f"""
        <div class="device-card">
          <div class="device-header">
            <span class="device-name">{r['name']}</span>
            <span class="device-size">{r['width']} × {r['height']}</span>
            <span class="badge" style="background:{color}">{label}</span>
            <span class="stat">{stat}</span>
          </div>
          <div class="card-body">
            <div class="issues-block">{issues_html}</div>
            <div class="img-wrap">
              <img src="{img_uri}" alt="{r['name']}">
            </div>
          </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Responsive Check — {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, sans-serif; background: #f5f5f2; color: #2c2c2a; padding: 24px; }}
  h1 {{ font-size: 22px; font-weight: 500; margin-bottom: 4px; }}
  .meta {{ color: #888; font-size: 13px; margin-bottom: 32px; margin-top: 4px; }}
  .meta a {{ color: #185FA5; text-decoration: none; }}
  .device-card {{ background: #fff; border-radius: 12px; border: 1px solid #e0ddd6; margin-bottom: 24px; overflow: hidden; }}
  .device-header {{ display: flex; align-items: center; gap: 12px; padding: 14px 20px; border-bottom: 1px solid #e0ddd6; flex-wrap: wrap; }}
  .device-name {{ font-size: 16px; font-weight: 500; }}
  .device-size {{ font-size: 12px; color: #888; background: #f5f5f2; padding: 2px 8px; border-radius: 99px; }}
  .badge {{ color: #fff; font-size: 12px; padding: 2px 10px; border-radius: 99px; }}
  .stat {{ font-size: 13px; color: #888; margin-left: auto; }}
  .card-body {{ display: grid; grid-template-columns: 1fr 320px; gap: 0; }}
  .issues-block {{ padding: 16px 20px; border-right: 1px solid #e0ddd6; }}
  .no-issues {{ color: #1D9E75; font-size: 13px; }}
  .issue {{ display: grid; grid-template-columns: 70px 1fr; gap: 8px; align-items: start; padding: 8px 0; border-bottom: 1px solid #f0ede6; font-size: 13px; }}
  .issue:last-child {{ border-bottom: none; }}
  .issue-badge {{ color: #fff; font-size: 11px; padding: 2px 6px; border-radius: 4px; text-align: center; white-space: nowrap; }}
  .issue-check {{ font-weight: 500; color: #2c2c2a; }}
  .issue-detail {{ color: #888; font-size: 12px; margin-top: 2px; word-break: break-word; }}
  .img-wrap {{ overflow: hidden; max-height: 600px; }}
  .img-wrap img {{ width: 100%; display: block; object-fit: cover; object-position: top; }}
  @media (max-width: 800px) {{
    .card-body {{ grid-template-columns: 1fr; }}
    .issues-block {{ border-right: none; border-bottom: 1px solid #e0ddd6; }}
  }}
</style>
</head>
<body>
<h1>Responsive Check</h1>
<p class="meta">
  Сгенерировано: {datetime.now().strftime('%d.%m.%Y %H:%M')} ·
  <a href="{url}" target="_blank">{url}</a>
</p>
{cards}
</body>
</html>"""

    out_path.write_text(html, encoding="utf-8")
    print(f"  [report] → {out_path}")


def run(url: str):
    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)

    print(f"\n── Проверка адаптивности: {url}")
    results = check_responsive(url, out_dir)

    generate_report(url, results, out_dir / "report_responsive.html")
    print("\nГотово!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="URL страницы")
    args = parser.parse_args()
    run(args.url)