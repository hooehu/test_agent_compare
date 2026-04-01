import httpx
from pathlib import Path


class FigmaClient:
    BASE = "https://api.figma.com/v1"

    def __init__(self, token: str):
        self.headers = {"X-Figma-Token": token}

    def get_frame_size(self, file_key: str, node_id: str) -> dict:
        """Читает размер фрейма из /files/ — не использует /nodes/."""
        r = httpx.get(
            f"{self.BASE}/files/{file_key}",
            headers=self.headers,
            timeout=30
        )
        r.raise_for_status()

        # Ищем нужный фрейм по id во всём дереве
        target = node_id.replace("-", ":")
        frame = self._find_node(r.json()["document"], target)
        if not frame:
            raise ValueError(f"Фрейм {node_id} не найден в файле")

        box = frame["absoluteBoundingBox"]
        return {"width": int(box["width"]), "height": int(box["height"])}

    def _find_node(self, node: dict, target_id: str) -> dict | None:
        if node.get("id") == target_id:
            return node
        for child in node.get("children", []):
            result = self._find_node(child, target_id)
            if result:
                return result
        return None

    def get_frame_image(self, file_key: str, node_id: str, scale: int = 1) -> bytes:
        node_id_url = node_id.replace(":", "-")
        r = httpx.get(
            f"{self.BASE}/images/{file_key}",
            headers=self.headers,
            params={"ids": node_id_url, "format": "png", "scale": scale},
            timeout=30
        )
        r.raise_for_status()
        image_url = r.json()["images"][node_id]
        img = httpx.get(image_url, timeout=30)
        img.raise_for_status()
        return img.content

    def save_frame(self, file_key: str, node_id: str, out_path: Path, scale: int = 1):
        data = self.get_frame_image(file_key, node_id, scale)
        out_path.write_bytes(data)
        print(f"  [figma] saved → {out_path}")