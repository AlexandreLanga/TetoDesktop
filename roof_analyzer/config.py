"""Configurações e constantes compartilhadas pelo aplicativo."""

API_DEFAULT = "http://127.0.0.1:8080/api/analyze"
API_TIMEOUT_SECONDS = 180
MAX_IMAGES = 3
PREVIEW_SIZE = (310, 215)
ANALYSES_DIRECTORY = "analises"

SEVERITY_COLORS = {
    "ALTA": "#e53935",
    "MÉDIA": "#fb8c00",
    "MEDIA": "#fb8c00",
    "BAIXA": "#43a047",
}
ANNOTATION_PALETTE = [
    "#e53935", "#1e88e5", "#43a047", "#fb8c00",
    "#8e24aa", "#00acc1", "#fdd835", "#6d4c41",
]
