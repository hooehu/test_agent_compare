import argparse
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from figma_client import FigmaClient
from page_snapshotter import take_screenshot
from ai_comparator import compare_images
from report_generator import generate_report

load_dotenv()


def run(config_path: str, refresh_figma: bool = False):
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    figma_token = os.environ["FIGMA_TOKEN"]
    out_dir = Path(cfg.get("output_dir", "output"))
    out_dir.mkdir(exist_ok=True)

    figma = FigmaClient(figma_token)
    results = []

    for item in cfg["pages"]:
        name = item["name"]
        print(f"\n── {name}")

        figma_path = out_dir / f"{name}_figma.png"
        page_path  = out_dir / f"{name}_page.png"

        # Figma скачиваем только если файла нет или передан флаг --refresh-figma
        if not figma_path.exists() or refresh_figma:
            print("  [figma] читаю размер фрейма...")
            size = figma.get_frame_size(item["figma_file_key"], item["figma_node_id"])
            print(f"  [figma] размер: {size['width']}x{size['height']}")
            figma.save_frame(
                file_key=item["figma_file_key"],
                node_id=item["figma_node_id"],
                out_path=figma_path,
                scale=1,
            )
        else:
            from PIL import Image
            size_img = Image.open(figma_path)
            size = {"width": size_img.width, "height": size_img.height}
            print(f"  [figma] используем кэш → {figma_path} ({size['width']}x{size['height']})")

        # Страницу снимаем всегда — она меняется
        take_screenshot(
            url=item["url"],
            out_path=page_path,
            width=size["width"],
            height=size["height"],
        )

        print("  [diff] сравниваю...")
        diff = compare_images(figma_path, page_path)
        print(f"  [diff] severity: {diff['severity']} ({diff['changed_percent']}%)")

        results.append({
            "name": name,
            "url": item["url"],
            "figma_path": figma_path,
            "page_path": page_path,
            **diff,
        })

    generate_report(results, out_dir / "report.html")
    print("\nГотово!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--refresh-figma", action="store_true",
                        help="Принудительно перескачать макеты из Figma")
    args = parser.parse_args()
    run(args.config, refresh_figma=args.refresh_figma)