# Analisador de Telhados

Aplicativo desktop em Python para enviar de uma a três fotos de telhados à TetoAPI, exibir as áreas identificadas e gerar um relatório em PDF.

## Requisitos

- Python 3.10 ou superior
- Uma instância da TetoAPI disponível (por padrão, em `http://127.0.0.1:8080`)

## Instalação e execução

```powershell
py -m pip install -r requirements.txt
py app.py
```

Se o comando `py` não estiver disponível no seu sistema, instale o Python pelo site oficial e habilite a opção de adicioná-lo ao `PATH`.

## Como usar

1. Inicie a TetoAPI.
2. Abra o aplicativo e, se necessário, ajuste a URL e o texto da solicitação.
3. Selecione entre uma e três imagens (`.jpg`, `.jpeg`, `.png`, `.webp` ou `.bmp`).
4. Clique em **Analisar telhado**.
5. Revise o resultado e as imagens anotadas. Para salvar o resultado, clique em **Gerar relatório PDF**.

As imagens anotadas são gravadas em `analises/<data_hora>/`. Essa pasta e os PDFs gerados são locais e não são versionados pelo Git.

## Contrato esperado da API

A requisição é `multipart/form-data`, com campos repetidos chamados `files` e um campo de texto chamado `prompt`. O tempo-limite da chamada é de 180 segundos.

O aplicativo espera um JSON que contenha, ao menos, os objetos `result` e opcionalmente `annotation`. Consulte a documentação detalhada do formato em [docs/API.md](docs/API.md).

## Desenvolvimento

O projeto adota UTF-8, finais de linha LF e indentação de quatro espaços, definidos em `.editorconfig`.

Antes de enviar alterações, execute:

```powershell
py -m compileall -q app.py
```

As mudanças devem preservar o contrato da API e o comportamento da interface. A arquitetura e os pontos de manutenção estão em [docs/ARQUITETURA.md](docs/ARQUITETURA.md).
