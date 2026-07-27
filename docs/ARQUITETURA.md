# Arquitetura

O projeto é uma aplicação desktop modular. O arquivo `app.py` é somente o ponto de entrada; os componentes estão no pacote `roof_analyzer`.

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

## Organização do código

| Módulo | Responsabilidade |
| --- | --- |
| `app.py` | Inicializa a aplicação. |
| `roof_analyzer/ui.py` | Janela Tkinter, estado da tela e coordenação das ações do usuário. |
| `roof_analyzer/api_client.py` | Upload multipart, tempo-limite e interpretação de erros HTTP. |
| `roof_analyzer/annotations.py` | Associação de problemas às imagens, conversão de coordenadas e desenhos. |
| `roof_analyzer/formatting.py` | Conversão da resposta da API em texto para a interface. |
| `roof_analyzer/reporting.py` | Montagem do relatório PDF. |
| `roof_analyzer/config.py` | Constantes compartilhadas e parâmetros do aplicativo. |

## Convenções de manutenção

- Não acessar widgets Tkinter a partir da thread de rede; use `self.after(...)`. A thread deve chamar apenas `api_client.analyze_images`.
- Fechar arquivos e imagens abertos. O código usa context managers para imagens e fecha os handles do upload no bloco `finally`.
- Tratar campos da resposta da API como opcionais, pois a interface mostra valores padrão quando estiverem ausentes.
- Coordenadas de problemas podem estar normalizadas entre 0 e 1 ou em pixels; `normalize_coordinates` suporta ambos os formatos.
- Manter `analises/` e PDFs fora do controle de versão: são artefatos gerados pelo usuário.

## Testes

Os testes unitários em `tests/` cobrem as regras sem interface gráfica: conversão de coordenadas, associação de imagens e formatação do resultado. Execute-os com `py -m unittest discover -s tests -v`.
