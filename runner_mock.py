import sys
import os
from pathlib import Path

from ai_comparator import compare_images
from report_generator import generate_report

ASSETS = Path(__file__).parent / "mock_assets"
OUT = Path(__file__).parent / "output"
OUT.mkdir(exist_ok=True)

figma_path = ASSETS / "figma_mock.png"
page_path  = ASSETS / "page_screenshot.png"

print("── login-page (mock)")
print("  [ai] сравниваю...")

diff = compare_images(figma_path, page_path)
print(f"  [ai] severity: {diff['severity']}")
print()
print(diff["analysis"])

generate_report(
    results=[{
        "name": "login-page (mock)",
        "url": "file://mock",
        "figma_path": figma_path,
        "page_path": page_path,
        **diff,
    }],
    out_path=OUT / "report.html",
)