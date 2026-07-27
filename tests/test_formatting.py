import unittest

from roof_analyzer.formatting import format_result


class FormatResultTests(unittest.TestCase):
    def test_formats_the_main_sections_and_an_issue(self) -> None:
        payload = {
            "result": {
                "roof_condition": {"score": 80, "classification": "Boa", "summary": "Sem danos."},
                "maintenance": {"priority": "Baixa", "inspection_required": False},
                "issues": [{"type": "Telha", "severity": "BAIXA", "confidence": 95}],
                "limitations": ["Imagem noturna"],
            }
        }

        result = format_result(payload)

        self.assertIn("CONDIÇÃO GERAL", result)
        self.assertIn("Pontuação: 80", result)
        self.assertIn("Telha — BAIXA (95% confiança)", result)
        self.assertIn("• Imagem noturna", result)
