"""Comunicação HTTP com a TetoAPI."""

from __future__ import annotations

import json
from pathlib import Path

import requests

from roof_analyzer.config import API_TIMEOUT_SECONDS


def analyze_images(url: str, prompt: str, image_paths: list[Path]) -> dict:
    """Envia imagens à API e retorna a resposta JSON.

    Erros de rede, leitura ou resposta inválida são propagados para a camada de
    interface, que é responsável por apresentá-los ao usuário.
    """
    files = []
    handles = []
    try:
        for path in image_paths:
            handle = path.open("rb")
            handles.append(handle)
            # O contrato OpenAPI da TetoAPI exige vários uploads no campo "files".
            files.append(("files", (path.name, handle, _mime_type(path))))

        response = requests.post(
            url, data={"prompt": prompt}, files=files, timeout=API_TIMEOUT_SECONDS
        )
        if not response.ok:
            try:
                detail = json.dumps(response.json(), ensure_ascii=False, indent=2)
            except ValueError:
                detail = response.text
            raise requests.HTTPError(
                f"{response.status_code} {response.reason} para {response.url}\n\n"
                f"Resposta do servidor:\n{detail[:2500]}",
                response=response,
            )
        return response.json()
    finally:
        for handle in handles:
            handle.close()


def _mime_type(path: Path) -> str:
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(path.suffix.lower(), "application/octet-stream")
