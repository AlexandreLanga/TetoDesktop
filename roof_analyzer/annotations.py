"""Criação de imagens anotadas a partir da resposta da API."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from roof_analyzer.config import ANALYSES_DIRECTORY, ANNOTATION_PALETTE, SEVERITY_COLORS


def create_annotations(image_paths: list[Path], payload: dict) -> list[Path]:
    """Desenha as áreas informadas pela API e retorna os arquivos gerados."""
    output_dir = Path.cwd() / ANALYSES_DIRECTORY / datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    annotations = payload.get("annotation", {}).get("image_annotations", [])
    issues = payload.get("result", {}).get("issues", [])
    by_index = {item.get("image_index"): item.get("areas", []) for item in annotations}
    paths = []

    for index, source in enumerate(image_paths):
        with Image.open(source) as source_image:
            image = ImageOps.exif_transpose(source_image).convert("RGB")
        draw = ImageDraw.Draw(image, "RGBA")
        matched_issues = [
            (issue_number, issue)
            for issue_number, issue in enumerate(issues, 1)
            if issue_matches_image(issue, index, source)
        ]

        if matched_issues:
            _draw_issue_boxes(draw, image, matched_issues)
        else:
            _draw_annotation_polygons(draw, image, by_index.get(index, []), issues)

        target = output_dir / f"anotada_{source.stem}.jpg"
        image.save(target, quality=94)
        paths.append(target)
    return paths


def _draw_issue_boxes(
    draw: ImageDraw.ImageDraw,
    image: Image.Image,
    matched_issues: list[tuple[int, dict]],
) -> None:
    for issue_index, (issue_number, issue) in enumerate(matched_issues, 1):
        bbox = normalize_coordinates(issue.get("coordinates"), image.width, image.height)
        if not bbox:
            continue
        x1, y1, width, height = bbox
        x2, y2 = x1 + width, y1 + height
        if x2 <= x1 or y2 <= y1:
            continue
        color = get_issue_color(issue.get("severity", ""), issue_index, len(matched_issues))
        rgb = tuple(bytes.fromhex(color[1:]))
        draw.rectangle(
            [x1, y1, x2, y2], fill=rgb + (65,), outline=rgb + (255,),
            width=max(3, image.width // 450),
        )
        draw.text(
            (x1 + 5, y1 + 5), str(issue_number), fill=(255, 255, 255, 255),
            stroke_width=2, stroke_fill=rgb + (255,),
        )


def _draw_annotation_polygons(
    draw: ImageDraw.ImageDraw, image: Image.Image, areas: list, issues: list,
) -> None:
    for issue_index, area in enumerate(areas):
        if len(area) < 3:
            continue
        severity = issues[issue_index].get("severity", "") if issue_index < len(issues) else ""
        color = SEVERITY_COLORS.get(str(severity).upper(), "#1976d2")
        rgb = tuple(bytes.fromhex(color[1:]))
        points = [(float(point["x"]) * image.width, float(point["y"]) * image.height) for point in area]
        draw.polygon(
            points, fill=rgb + (65,), outline=rgb + (255,),
            width=max(3, image.width // 450),
        )
        x, y = points[0]
        draw.text(
            (x + 5, y + 5), str(issue_index + 1), fill=(255, 255, 255, 255),
            stroke_width=2, stroke_fill=rgb + (255,),
        )


def get_issue_color(severity: str, issue_index: int, total_issues: int) -> str:
    """Escolhe uma cor que diferencie problemas na mesma imagem."""
    if total_issues > 1:
        palette_index = (issue_index - 1) % len(ANNOTATION_PALETTE)
        return ANNOTATION_PALETTE[palette_index]
    return SEVERITY_COLORS.get(str(severity).upper(), "#1976d2")


def normalize_coordinates(
    coordinates: dict | None, width: int, height: int,
) -> tuple[float, float, float, float] | None:
    """Converte coordenadas normalizadas ou absolutas para pixels."""
    if not isinstance(coordinates, dict):
        return None
    try:
        x = float(coordinates.get("x", 0))
        y = float(coordinates.get("y", 0))
        width_value = float(coordinates.get("width", 0))
        height_value = float(coordinates.get("height", 0))
    except (TypeError, ValueError):
        return None
    if width_value < 0 or height_value < 0:
        return None
    if max(abs(x), abs(y), abs(width_value), abs(height_value)) <= 1:
        x *= width
        y *= height
        width_value *= width
        height_value *= height
    return (x, y, width_value, height_value)


def issue_matches_image(issue: dict, index: int, source: Path) -> bool:
    """Verifica se um problema retornado pela API pertence à imagem de origem."""
    image_name = issue.get("image_name")
    if image_name:
        normalized_image_name = _normalize_image_name(image_name)
        normalized_source_name = _normalize_image_name(source.name)
        normalized_source_stem = _normalize_image_name(source.stem)
        normalized_source_path = _normalize_image_name(str(source))
        return (
            normalized_image_name == normalized_source_name
            or normalized_image_name == normalized_source_stem
            or normalized_image_name == normalized_source_path
            or Path(normalized_image_name).name == normalized_source_name
        )
    image_index = issue.get("image_index")
    if image_index is not None:
        try:
            return int(image_index) == index
        except (TypeError, ValueError):
            return False
    return False


def _normalize_image_name(value: object) -> str:
    return "" if value is None else str(value).strip().lower()
