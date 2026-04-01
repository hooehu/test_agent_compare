import numpy as np
from PIL import Image, ImageFilter
from pathlib import Path


def _crop_to_match(figma: Image.Image, page: Image.Image):
    """Обрезаем обе картинки до общего размера — берём минимум по каждой стороне."""
    w = min(figma.width, page.width)
    h = min(figma.height, page.height)
    figma = figma.crop((0, 0, w, h))
    page  = page.crop((0, 0, w, h))
    return figma, page


def compare_images(figma_path: Path, page_path: Path) -> dict:
    figma = Image.open(figma_path).convert("RGB")
    page  = Image.open(page_path).convert("RGB")

    # Если размеры разные — подгоняем страницу под ширину макета
    # и обрезаем по минимальной высоте
    if figma.width != page.width:
        ratio = figma.width / page.width
        new_h = int(page.height * ratio)
        page = page.resize((figma.width, new_h), Image.LANCZOS)

    figma, page = _crop_to_match(figma, page)

    # Размытие 1px — убирает шум от субпиксельного рендеринга
    figma_arr = np.array(figma.filter(ImageFilter.GaussianBlur(1)), dtype=np.float32)
    page_arr  = np.array(page.filter(ImageFilter.GaussianBlur(1)),  dtype=np.float32)

    diff = np.abs(figma_arr - page_arr)

    # Порог 15/255 — игнорирует мелкие различия антиалиасинга и шрифтов UPD: Порог увелчен
    changed_mask = diff.max(axis=2) > 30
    changed_percent = round(changed_mask.mean() * 100, 2)

    # Визуальный diff
    diff_visual = figma.convert("RGBA")
    overlay     = np.array(diff_visual)
    overlay[changed_mask] = [220, 50, 50, 200]
    diff_visual = Image.fromarray(overlay)

    severity = _detect_severity(changed_percent)
    analysis = _build_analysis(changed_percent, changed_mask, figma.size)

    return {
        "analysis":        analysis,
        "severity":        severity,
        "diff_visual":     diff_visual,
        "changed_percent": changed_percent,
    }


def _detect_severity(changed_percent: float) -> str:
    if changed_percent < 2:
        return "ok"
    if changed_percent < 8:
        return "minor"
    if changed_percent < 20:
        return "major"
    return "critical"


def _build_analysis(changed_percent: float, mask: np.ndarray, size: tuple) -> str:
    if changed_percent < 2:
        return "Расхождений не обнаружено."

    h, w  = mask.shape
    lines = [f"Отличается пикселей: {changed_percent}%\n"]

    zones = {
        "Верхняя часть (шапка)":  mask[:h//4, :],
        "Верхний центр":          mask[h//4:h//2, :],
        "Нижний центр (контент)": mask[h//2:3*h//4, :],
        "Нижняя часть (футер)":   mask[3*h//4:, :],
    }

    for zone_name, zone_mask in zones.items():
        pct = round(zone_mask.mean() * 100, 1)
        if pct > 2:
            lines.append(f"  • {zone_name}: ~{pct}% пикселей отличается")

    return "\n".join(lines)