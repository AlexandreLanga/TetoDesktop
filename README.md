# Analisador de Telhados

Aplicativo desktop em Python que envia de uma a três imagens à API de análise, desenha os polígonos recebidos e gera um relatório em PDF.

## Instalação e execução

```powershell
py -m pip install -r requirements.txt
py app.py
```

Por padrão, o aplicativo envia `multipart/form-data` para `http://127.0.0.1:8080/api/analyze`, usando campos repetidos `files` e o campo de texto `prompt`, conforme o contrato OpenAPI da TetoAPI. A URL e o prompt podem ser ajustados na própria interface.

Os arquivos marcados são salvos em `analises/<data_hora>/` quando a análise é concluída. As coordenadas da API são interpretadas como valores normalizados de 0 a 1.
