# Arquitetura

O projeto é uma aplicação desktop de arquivo único. A classe `RoofAnalyzerApp` coordena a interface Tkinter, a integração HTTP, a criação de anotações e a geração de PDF.

## Fluxo principal

```text
Seleção de imagens
        |
        v
POST multipart para a TetoAPI (em thread de trabalho)
        |
        v
Resposta JSON -> anotações nas imagens -> prévia e texto
        |
        v
Geração opcional do relatório PDF
```

A chamada de rede é executada em uma thread daemon. Qualquer atualização de interface volta à thread do Tkinter por `after`, evitando bloqueio da janela.

## Responsabilidades no código

| Área | Métodos principais |
| --- | --- |
| Interface e estado | `__init__`, `_build_ui`, `_set_busy`, `_set_result` |
| Upload e erros HTTP | `analyze`, `_post_analysis`, `_analysis_failed` |
| Anotações | `_create_annotations`, `_normalize_coordinates`, `_issue_matches_image` |
| Exibição | `_render_previews`, `_format_result` |
| PDF | `generate_report`, `_build_pdf` |

## Convenções de manutenção

- Não acessar widgets Tkinter a partir da thread de rede; use `self.after(...)`.
- Fechar arquivos e imagens abertos. O código usa context managers para imagens e fecha os handles do upload no bloco `finally`.
- Tratar campos da resposta da API como opcionais, pois a interface mostra valores padrão quando estiverem ausentes.
- Coordenadas de problemas podem estar normalizadas entre 0 e 1 ou em pixels; `_normalize_coordinates` suporta ambos os formatos.
- Manter `analises/` e PDFs fora do controle de versão: são artefatos gerados pelo usuário.

## Limites conhecidos

Não há suíte de testes automatizados ainda. Como os componentes de conversão de coordenadas e de associação de imagens são independentes da interface, eles são os melhores primeiros candidatos para testes unitários ao introduzir uma estrutura de testes.
