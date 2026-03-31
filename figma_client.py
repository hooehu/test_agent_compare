import httpx
from pathlib import Path


class FigmaClient:
    BASE = "https://api.figma.com/v1"

    def __init__(self, token: str):
        self.headers = {"X-Figma-Token": token}

    def get_frame_size(self, file_key: str, node_id: str) -> dict:
        """Возвращает ширину и высоту фрейма из Figma."""
        url = f"{self.BASE}/files/{file_key}/nodes"
        node_id_api = node_id.replace(":", "-")  # 1:720 → 1-720
        r = httpx.get(url, headers=self.headers, params={"ids": node_id_api}, timeout=30)
        r.raise_for_status()
        node = r.json()["nodes"][node_id]["document"]
        size = node["absoluteBoundingBox"]
        return {"width": int(size["width"]), "height": int(size["height"])}

    def get_frame_image(self, file_key: str, node_id: str, scale: int = 1) -> bytes:
        """Экспортирует фрейм как PNG."""
        url = f"{self.BASE}/images/{file_key}"
        params = {"ids": node_id, "format": "png", "scale": scale}
        r = httpx.get(url, headers=self.headers, params=params, timeout=30)
        r.raise_for_status()
        image_url = r.json()["images"][node_id]
        img_response = httpx.get(image_url, timeout=30)
        img_response.raise_for_status()
        return img_response.content

    def save_frame(self, file_key: str, node_id: str, out_path: Path, scale: int = 1):
        data = self.get_frame_image(file_key, node_id, scale)
        out_path.write_bytes(data)
        print(f"  [figma] saved → {out_path}")