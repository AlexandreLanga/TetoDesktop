"""Interface gráfica do Analisador de Telhados."""

from __future__ import annotations

import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import requests
from PIL import Image, ImageOps, ImageTk

from roof_analyzer.annotations import create_annotations
from roof_analyzer.api_client import analyze_images
from roof_analyzer.config import API_DEFAULT, MAX_IMAGES, PREVIEW_SIZE
from roof_analyzer.formatting import format_result
from roof_analyzer.reporting import build_pdf


class RoofAnalyzerApp(tk.Tk):
    """Janela principal e coordenadora do fluxo de interação do usuário."""

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
        self.images = [Path(path) for path in paths]
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
        threading.Thread(
            target=self._post_analysis,
            args=(self.url_var.get().strip(), self.prompt_var.get().strip()),
            daemon=True,
        ).start()

    def _post_analysis(self, url: str, prompt: str) -> None:
        try:
            payload = analyze_images(url, prompt, self.images)
            self.after(0, lambda: self._analysis_succeeded(payload))
        except (OSError, requests.RequestException, ValueError) as exc:
            self.after(0, lambda message=str(exc): self._analysis_failed(message))

    def _analysis_succeeded(self, payload: dict) -> None:
        self.response = payload
        try:
            self.annotated_paths = create_annotations(self.images, payload)
            self._render_previews(annotated=True)
            self._set_result(format_result(payload))
            self.report_button.configure(state="normal")
            self._set_busy(False, "Análise concluída. Áreas destacadas nas imagens.")
        except Exception as exc:  # O relatório textual continua utilizável se uma anotação falhar.
            self._set_result(format_result(payload) + f"\n\nAviso: não foi possível desenhar as áreas: {exc}")
            self.report_button.configure(state="normal")
            self._set_busy(False, "Análise concluída, porém uma marcação não pôde ser desenhada.")

    def _analysis_failed(self, error: str) -> None:
        self._set_busy(False, "Falha ao analisar as imagens.")
        messagebox.showerror("Erro na API", f"Não foi possível concluir a análise.\n\n{error}")

    def _set_busy(self, busy: bool, status: str) -> None:
        self.select_button.configure(state="disabled" if busy else "normal")
        self.analyze_button.configure(state="disabled" if busy else ("normal" if self.images else "disabled"))
        self.status_var.set(status)

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

    def _set_result(self, content: str) -> None:
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", content)
        self.result_text.configure(state="disabled")

    def generate_report(self) -> None:
        if not self.response:
            return
        target = filedialog.asksaveasfilename(
            title="Salvar relatório", defaultextension=".pdf", initialfile="relatorio_telhado.pdf", filetypes=[("PDF", "*.pdf")],
        )
        if not target:
            return
        try:
            build_pdf(Path(target), self.response, self.annotated_paths)
            messagebox.showinfo("Relatório criado", f"Relatório salvo em:\n{target}")
        except Exception as exc:
            messagebox.showerror("Erro ao gerar PDF", str(exc))


def main() -> None:
    """Inicia a interface gráfica do aplicativo."""
    RoofAnalyzerApp().mainloop()
