"""Aplicativo desktop para análise visual de telhados."""

from __future__ import annotations

import json
import threading
from datetime import datetime
from html import escape
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

import requests
from PIL import Image, ImageDraw, ImageOps, ImageTk
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image as PdfImage
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


API_DEFAULT = "http://127.0.0.1:8080/api/analyze"
API_TIMEOUT_SECONDS = 180
MAX_IMAGES = 3
PREVIEW_SIZE = (310, 215)
ANALYSES_DIRECTORY = "analises"
SEVERITY_COLORS = {"ALTA": "#e53935", "MÉDIA": "#fb8c00", "MEDIA": "#fb8c00", "BAIXA": "#43a047"}
ANNOTATION_PALETTE = ["#e53935", "#1e88e5", "#43a047", "#fb8c00", "#8e24aa", "#00acc1", "#fdd835", "#6d4c41"]


class RoofAnalyzerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Analisador de Telhados")
        self.geometry("1180x790")
        self.minsize(960, 650)
        self.images: list[Path] = []
        self.response: dict | None = None
        self.annotated_paths: list[Path] = []
        self.preview_refs: list[ImageTk.PhotoImage] = []

        self.url_var = tk.StringVar(value=API_DEFAULT)
        self.prompt_var = tk.StringVar(value="Analise esse telhado")
        self.status_var = tk.StringVar(value="Selecione de uma a três imagens do telhado.")
        self._setup_style()
        self._build_ui()

    def _setup_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Title.TLabel", font=("Segoe UI", 17, "bold"), foreground="#1d3557")
        style.configure("Section.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure("Status.TLabel", foreground="#355070")
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Análise de Telhado", style="Title.TLabel").pack(anchor="w")
        ttk.Label(outer, text="Envie até 3 fotos para obter uma avaliação e relatório técnico.").pack(anchor="w", pady=(2, 12))

        config = ttk.LabelFrame(outer, text="Configuração da API", style="Section.TLabelframe", padding=10)
        config.pack(fill="x")
        ttk.Label(config, text="URL:").grid(row=0, column=0, sticky="w")
        ttk.Entry(config, textvariable=self.url_var).grid(row=0, column=1, sticky="ew", padx=(6, 16))
        ttk.Label(config, text="Solicitação:").grid(row=0, column=2, sticky="w")
        ttk.Entry(config, textvariable=self.prompt_var, width=32).grid(row=0, column=3, sticky="ew", padx=(6, 0))
        config.columnconfigure(1, weight=1)

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=12)
        self.select_button = ttk.Button(actions, text="Selecionar imagens", command=self.select_images)
        self.select_button.pack(side="left")
        self.analyze_button = ttk.Button(actions, text="Analisar telhado", style="Accent.TButton", command=self.analyze, state="disabled")
        self.analyze_button.pack(side="left", padx=8)
        self.report_button = ttk.Button(actions, text="Gerar relatório PDF", command=self.generate_report, state="disabled")
        self.report_button.pack(side="left")
        ttk.Label(actions, textvariable=self.status_var, style="Status.TLabel").pack(side="right")

        body = ttk.PanedWindow(outer, orient="horizontal")
        body.pack(fill="both", expand=True)
        left = ttk.LabelFrame(body, text="Imagens e áreas identificadas", style="Section.TLabelframe", padding=10)
        right = ttk.LabelFrame(body, text="Resultado da análise", style="Section.TLabelframe", padding=10)
        body.add(left, weight=3)
        body.add(right, weight=2)

        self.preview_frame = ttk.Frame(left)
        self.preview_frame.pack(fill="both", expand=True)
        self.result_text = tk.Text(right, wrap="word", font=("Segoe UI", 10), state="disabled", padx=8, pady=8)
        scrollbar = ttk.Scrollbar(right, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.result_text.pack(side="left", fill="both", expand=True)

    def select_images(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Selecione até 3 fotos do telhado",
            filetypes=[("Imagens", "*.jpg *.jpeg *.png *.webp *.bmp"), ("Todos os arquivos", "*.*")],
        )
        if not paths:
            return
        if len(paths) > MAX_IMAGES:
            messagebox.showwarning("Limite de imagens", "Selecione no máximo 3 imagens.")
            return
        self.images = [Path(p) for p in paths]
        self.response = None
        self.annotated_paths = []
        self.report_button.configure(state="disabled")
        self.analyze_button.configure(state="normal")
        self.status_var.set(f"{len(self.images)} imagem(ns) pronta(s) para análise.")
        self._render_previews()
        self._set_result("Imagens selecionadas. Clique em ‘Analisar telhado’ para enviar à API.")

    def analyze(self) -> None:
        if not self.images:
            return
        self._set_busy(True, "Enviando imagens para análise…")
        url = self.url_var.get().strip()
        prompt = self.prompt_var.get().strip()
        threading.Thread(target=self._post_analysis, args=(url, prompt), daemon=True).start()

    def _post_analysis(self, url: str, prompt: str) -> None:
        files = []
        handles = []
        try:
            for path in self.images:
                handle = path.open("rb")
                handles.append(handle)
                # O contrato OpenAPI da TetoAPI exige vários uploads no campo "files".
                files.append(("files", (path.name, handle, self._mime_type(path))))
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
            payload = response.json()
            self.after(0, lambda: self._analysis_succeeded(payload))
        except (OSError, requests.RequestException, ValueError) as exc:
            error_message = str(exc)
            self.after(0, lambda message=error_message: self._analysis_failed(message))
        finally:
            for handle in handles:
                handle.close()

    @staticmethod
    def _mime_type(path: Path) -> str:
        return {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(path.suffix.lower(), "application/octet-stream")

    def _analysis_succeeded(self, payload: dict) -> None:
        self.response = payload
        try:
            self.annotated_paths = self._create_annotations(payload)
            self._render_previews(annotated=True)
            self._set_result(self._format_result(payload))
            self.report_button.configure(state="normal")
            self._set_busy(False, "Análise concluída. Áreas destacadas nas imagens.")
        except Exception as exc:  # the textual report remains usable even if an annotation is malformed
            self._set_result(self._format_result(payload) + f"\n\nAviso: não foi possível desenhar as áreas: {exc}")
            self.report_button.configure(state="normal")
            self._set_busy(False, "Análise concluída, porém uma marcação não pôde ser desenhada.")

    def _analysis_failed(self, error: str) -> None:
        self._set_busy(False, "Falha ao analisar as imagens.")
        messagebox.showerror("Erro na API", f"Não foi possível concluir a análise.\n\n{error}")

    def _set_busy(self, busy: bool, status: str) -> None:
        self.select_button.configure(state="disabled" if busy else "normal")
        self.analyze_button.configure(state="disabled" if busy else ("normal" if self.images else "disabled"))
        self.status_var.set(status)

    def _create_annotations(self, payload: dict) -> list[Path]:
        output_dir = Path.cwd() / ANALYSES_DIRECTORY / datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir.mkdir(parents=True, exist_ok=True)
        annotations = payload.get("annotation", {}).get("image_annotations", [])
        issues = payload.get("result", {}).get("issues", [])
        by_index = {item.get("image_index"): item.get("areas", []) for item in annotations}
        paths = []
        for index, source in enumerate(self.images):
            with Image.open(source) as source_image:
                image = ImageOps.exif_transpose(source_image).convert("RGB")
            draw = ImageDraw.Draw(image, "RGBA")

            matched_issues = []
            for issue_number, issue in enumerate(issues, 1):
                if self._issue_matches_image(issue, index, source):
                    matched_issues.append((issue_number, issue))

            if matched_issues:
                for issue_index, (issue_number, issue) in enumerate(matched_issues, 1):
                    bbox = self._normalize_coordinates(issue.get("coordinates"), image.width, image.height)
                    if not bbox:
                        continue
                    x1, y1, width, height = bbox
                    x2, y2 = x1 + width, y1 + height
                    if x2 <= x1 or y2 <= y1:
                        continue
                    color = self._get_issue_color(issue.get("severity", ""), issue_index, len(matched_issues))
                    rgb = tuple(bytes.fromhex(color[1:]))
                    draw.rectangle([x1, y1, x2, y2], fill=rgb + (65,), outline=rgb + (255,), width=max(3, image.width // 450))
                    draw.text((x1 + 5, y1 + 5), str(issue_number), fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=rgb + (255,))
            else:
                for issue_index, area in enumerate(by_index.get(index, [])):
                    if len(area) < 3:
                        continue
                    severity = issues[issue_index].get("severity", "") if issue_index < len(issues) else ""
                    color = SEVERITY_COLORS.get(str(severity).upper(), "#1976d2")
                    rgb = tuple(bytes.fromhex(color[1:]))
                    points = [(float(p["x"]) * image.width, float(p["y"]) * image.height) for p in area]
                    draw.polygon(points, fill=rgb + (65,), outline=rgb + (255,), width=max(3, image.width // 450))
                    x, y = points[0]
                    draw.text((x + 5, y + 5), str(issue_index + 1), fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=rgb + (255,))

            target = output_dir / f"anotada_{source.stem}.jpg"
            image.save(target, quality=94)
            paths.append(target)
        return paths

    @staticmethod
    def _get_issue_color(severity: str, issue_index: int, total_issues: int) -> str:
        if total_issues > 1:
            palette_index = (issue_index - 1) % len(ANNOTATION_PALETTE)
            return ANNOTATION_PALETTE[palette_index]
        return SEVERITY_COLORS.get(str(severity).upper(), "#1976d2")

    @staticmethod
    def _normalize_coordinates(coordinates: dict | None, width: int, height: int) -> tuple[float, float, float, float] | None:
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

    @staticmethod
    def _normalize_image_name(value: object) -> str:
        if value is None:
            return ""
        return str(value).strip().lower()

    @classmethod
    def _issue_matches_image(cls, issue: dict, index: int, source: Path) -> bool:
        image_name = issue.get("image_name")
        if image_name:
            normalized_image_name = cls._normalize_image_name(image_name)
            normalized_source_name = cls._normalize_image_name(source.name)
            normalized_source_stem = cls._normalize_image_name(source.stem)
            normalized_source_path = cls._normalize_image_name(str(source))
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

    def _render_previews(self, annotated: bool = False) -> None:
        for child in self.preview_frame.winfo_children():
            child.destroy()
        self.preview_refs.clear()
        paths = self.annotated_paths if annotated and self.annotated_paths else self.images
        for index, path in enumerate(paths):
            card = ttk.Frame(self.preview_frame, padding=6)
            card.grid(row=index // 2, column=index % 2, sticky="nsew")
            try:
                with Image.open(path) as source_image:
                    image = ImageOps.exif_transpose(source_image).convert("RGB")
                image.thumbnail(PREVIEW_SIZE)
                photo = ImageTk.PhotoImage(image)
                self.preview_refs.append(photo)
                ttk.Label(card, image=photo).pack()
            except OSError:
                ttk.Label(card, text="Prévia indisponível").pack()
            ttk.Label(card, text=f"Imagem {index + 1}: {path.name}", wraplength=310).pack(pady=(5, 0))
        self.preview_frame.columnconfigure(0, weight=1)
        self.preview_frame.columnconfigure(1, weight=1)

    def _format_result(self, payload: dict) -> str:
        result = payload.get("result", {})
        condition = result.get("roof_condition", {})
        maintenance = result.get("maintenance", {})
        lines = [
            "CONDIÇÃO GERAL",
            f"Pontuação: {condition.get('score', '—')} | Classificação: {condition.get('classification', '—')}",
            condition.get("summary", "Sem resumo disponível."),
            "\nMANUTENÇÃO",
            f"Prioridade: {maintenance.get('priority', '—')}",
            f"Inspeção presencial: {'Sim' if maintenance.get('inspection_required') else 'Não'}",
            f"Risco de vazamento: {maintenance.get('risk_of_leak', '—')}",
            f"Risco estrutural: {maintenance.get('structural_risk', '—')}",
            "\nPROBLEMAS IDENTIFICADOS",
        ]
        for n, issue in enumerate(result.get("issues", []), 1):
            lines += [
                f"\n{n}. {issue.get('type', 'Problema')} — {issue.get('severity', '—')} ({issue.get('confidence', '—')}% confiança)",
                f"Local: {issue.get('location', '—')}",
                f"Descrição: {issue.get('description', '—')}",
                f"Possível causa: {issue.get('possible_cause', '—')}",
                f"Consequência: {issue.get('possible_consequence', '—')}",
                f"Recomendação: {issue.get('recommendation', '—')}",
            ]
        limitations = result.get("limitations", [])
        if limitations:
            lines.append("\nLIMITAÇÕES DA ANÁLISE")
            lines.extend(f"• {item}" for item in limitations)
        return "\n".join(lines)

    def _set_result(self, content: str) -> None:
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", content)
        self.result_text.configure(state="disabled")

    def generate_report(self) -> None:
        if not self.response:
            return
        target = filedialog.asksaveasfilename(
            title="Salvar relatório", defaultextension=".pdf", initialfile="relatorio_telhado.pdf", filetypes=[("PDF", "*.pdf")]
        )
        if not target:
            return
        try:
            self._build_pdf(Path(target))
            messagebox.showinfo("Relatório criado", f"Relatório salvo em:\n{target}")
        except Exception as exc:
            messagebox.showerror("Erro ao gerar PDF", str(exc))

    def _build_pdf(self, target: Path) -> None:
        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(str(target), pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
        result = self.response.get("result", {})
        condition, maintenance = result.get("roof_condition", {}), result.get("maintenance", {})
        story = [Paragraph("Relatório de Análise de Telhado", styles["Title"]), Spacer(1, 0.35*cm)]
        story.append(Paragraph(f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}", styles["Normal"]))
        story += [Spacer(1, 0.3*cm), Paragraph("Condição geral", styles["Heading2"])]
        data = [["Pontuação", str(condition.get("score", "—"))], ["Classificação", str(condition.get("classification", "—"))], ["Prioridade", str(maintenance.get("priority", "—"))], ["Risco de vazamento", str(maintenance.get("risk_of_leak", "—"))], ["Risco estrutural", str(maintenance.get("structural_risk", "—"))]]
        table = Table(data, colWidths=[5*cm, 10*cm])
        table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8eef5")), ("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("PADDING", (0, 0), (-1, -1), 6)]))
        story += [table, Spacer(1, 0.3*cm), Paragraph(escape(str(condition.get("summary", ""))), styles["BodyText"])]
        story += [Spacer(1, 0.35*cm), Paragraph("Problemas identificados", styles["Heading2"])]
        for n, issue in enumerate(result.get("issues", []), 1):
            story.append(Paragraph(f"{n}. {escape(str(issue.get('type', 'Problema')))} ({escape(str(issue.get('severity', '—')))})", styles["Heading3"]))
            for label, key in [("Local", "location"), ("Descrição", "description"), ("Possível causa", "possible_cause"), ("Possível consequência", "possible_consequence"), ("Recomendação", "recommendation")]:
                story.append(Paragraph(f"<b>{label}:</b> {escape(str(issue.get(key, '—')))}", styles["BodyText"]))
            story.append(Spacer(1, 0.18*cm))
        if result.get("limitations"):
            story += [Paragraph("Limitações", styles["Heading2"])]
            story.extend(Paragraph(f"• {escape(str(value))}", styles["BodyText"]) for value in result["limitations"])
        if self.annotated_paths:
            story += [
                PageBreak(),
                Paragraph("Imagens com áreas destacadas", styles["Heading2"]),
                Paragraph(
                    "As áreas coloridas correspondem aos problemas listados neste relatório, "
                    "na mesma ordem em que foram retornados pela análise.",
                    styles["BodyText"],
                ),
                Spacer(1, 0.25*cm),
            ]
            for index, path in enumerate(self.annotated_paths, 1):
                with Image.open(path) as img:
                    ratio = min(16*cm / img.width, 20*cm / img.height)
                story += [
                    Paragraph(f"Imagem {index} — áreas identificadas", styles["Heading3"]),
                    Spacer(1, 0.12*cm),
                    PdfImage(str(path), width=img.width*ratio, height=img.height*ratio),
                    Spacer(1, 0.35*cm),
                ]
        doc.build(story)


def main() -> None:
    """Inicia a interface gráfica do aplicativo."""
    RoofAnalyzerApp().mainloop()


if __name__ == "__main__":
    main()
