# Contrato de integração com a TetoAPI

## Requisição

| Item | Valor |
| --- | --- |
| Método | `POST` |
| URL padrão | `http://127.0.0.1:8080/api/analyze` |
| Content type | `multipart/form-data` |
| Campo de imagens | `files` (repetido, de 1 a 3 vezes) |
| Campo textual | `prompt` |
| Tempo-limite | 180 segundos |

Os tipos MIME enviados explicitamente são JPEG, PNG e WebP. Outros formatos aceitos pelo seletor são encaminhados como `application/octet-stream`.

## Resposta utilizada

O aplicativo consome a estrutura abaixo de forma tolerante: campos ausentes aparecem como valores padrão na tela e no PDF.

```json
{
  "result": {
    "roof_condition": {
      "score": 0,
      "classification": "",
      "summary": ""
    },
    "maintenance": {
      "priority": "",
      "inspection_required": false,
      "risk_of_leak": "",
      "structural_risk": ""
    },
    "issues": [
      {
        "type": "",
        "severity": "ALTA",
        "confidence": 0,
        "location": "",
        "description": "",
        "possible_cause": "",
        "possible_consequence": "",
        "recommendation": "",
        "image_name": "foto.jpg",
        "image_index": 0,
        "coordinates": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.2}
      }
    ],
    "limitations": []
  },
  "annotation": {
    "image_annotations": [
      {"image_index": 0, "areas": [[{"x": 0.1, "y": 0.2}, {"x": 0.4, "y": 0.2}, {"x": 0.4, "y": 0.4}]]}
    ]
  }
}
```

Para cada problema, a associação da imagem prioriza `image_name`; se ele não estiver presente, usa `image_index`, iniciado em zero. As coordenadas de `issues` podem ser normalizadas (0 a 1) ou em pixels. As áreas de `annotation.image_annotations` usam coordenadas normalizadas.
