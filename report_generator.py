import base64
from pathlib import Path
from datetime import datetime


SEVERITY_COLOR = {
    "ok":       "#1D9E75",
    "minor":    "#BA7517",
    "major":    "#D85A30",
    "critical": "#E24B4A",
}

SEVERITY_LABEL = {
    "ok":       "Ок",
    "minor":    "Minor",
    "major":    "Major",
    "critical": "Critical",
}


def img_to_data_uri(path: Path) -> str:
    data = base64.b64encode(path.read_bytes()).decode()
    return f"data:image/png;base64,{data}"


def generate_report(results: list, out_path: Path):
    cards = ""
    for r in results:
        color = SEVERITY_COLOR.get(r["severity"], "#888")
        label = SEVERITY_LABEL.get(r["severity"], r["severity"])

        # Сохраняем diff-картинку рядом с отчётом
        diff_path = out_path.parent / f"{r['name'].replace(' ', '_')}_diff.png"
        if "diff_visual" in r:
            r["diff_visual"].save(diff_path)

        figma_uri = img_to_data_uri(r["figma_path"])
        page_uri  = img_to_data_uri(r["page_path"])
        diff_uri  = img_to_data_uri(diff_path) if diff_path.exists() else ""

        analysis_html = r["analysis"].replace("\n", "<br>")

        diff_block = f'<div class="img-wrap"><p class="img-label">Diff (красное = расхождение)</p><img src="{diff_uri}" alt="diff"></div>' if diff_uri else ""

        cards += f"""
        <div class="card">
          <div class="card-header">
            <span class="name">{r['name']}</span>
            <span class="badge" style="background:{color}">{label}</span>
          </div>
          <p class="url"><a href="{r['url']}" target="_blank">{r['url']}</a></p>
          <div class="images">
            <div class="img-wrap"><p class="img-label">Макет (Figma)</p><img src="{figma_uri}" alt="figma"></div>
            <div class="img-wrap"><p class="img-label">Реализация</p><img src="{page_uri}" alt="page"></div>
            {diff_block}
          </div>
          <div class="analysis"><pre>{analysis_html}</pre></div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Visual QA Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: system-ui, sans-serif; background: #f5f5f2; color: #2c2c2a; margin: 0; padding: 24px; }}
  h1 {{ font-size: 22px; font-weight: 500; margin-bottom: 4px; }}
  .meta {{ color: #888; font-size: 13px; margin-bottom: 32px; }}
  .card {{ background: #fff; border-radius: 12px; padding: 24px; margin-bottom: 24px; border: 1px solid #e0ddd6; }}
  .card-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }}
  .name {{ font-size: 17px; font-weight: 500; }}
  .badge {{ color: #fff; font-size: 12px; padding: 2px 10px; border-radius: 99px; }}
  .url {{ font-size: 12px; color: #888; margin: 0 0 16px; }}
  .url a {{ color: #185FA5; }}
  .images {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 16px; }}
  .img-label {{ font-size: 12px; color: #888; margin: 0 0 6px; }}
  img {{ width: 100%; border-radius: 6px; border: 1px solid #e0ddd6; }}
  .analysis pre {{ background: #f5f5f2; border-radius: 8px; padding: 14px; font-size: 13px; white-space: pre-wrap; margin: 0; }}
</style>
</head>
<body>
<h1>Visual QA Report</h1>
<p class="meta">Сгенерировано: {datetime.now().strftime('%d.%m.%Y %H:%M')} · {len(results)} страниц проверено</p>
{cards}
</body>
</html>"""

    out_path.write_text(html, encoding="utf-8")
    print(f"\n[report] → {out_path}")