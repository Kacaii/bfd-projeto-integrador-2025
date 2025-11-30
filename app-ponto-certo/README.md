
# App Ponto Certo (PDV)

Aplicativo de ponto de venda (PDV) em Python + Flet, com controle de estoque, caixa, estoque, fornecedores e relatórios.

## Requisitos

- Windows (recomendado, por causa de dependências como `pywin32` e `pyzbar`)
- Python 3.12.x instalado
- `uv` instalado globalmente:

```pwsh
pip install uv
```

## Como rodar o projeto com uv (Windows)

1. Clone ou copie a pasta do projeto para sua máquina.
2. Abra um terminal na pasta do projeto, por exemplo:

```pwsh
cd C:\caminho\para\app-ponto-certo
```

3. Crie o ambiente e instale as dependências usando o `pyproject.toml`:

```pwsh
uv sync
```

4. Rode o aplicativo:

```pwsh
uv run app.py
```

O Flet abrirá a janela com as telas de login, caixa, estoque, etc.

## Como rodar o projeto com uv (Linux)

1. Instale o Python 3.12 (por gerenciador de pacotes ou pyenv) e o `uv`:

```bash
python3 --version
python3 -m pip install uv
```

2. Abra um terminal na pasta do projeto, por exemplo:

```bash
cd /caminho/para/app-ponto-certo
```

3. Crie o ambiente e instale as dependências usando o `pyproject.toml`:

```bash
uv sync
```

4. Rode o aplicativo:

```bash
uv run app.py
```

Em Linux, algumas integrações específicas de Windows (como `pywin32` ou impressoras USB/Windows) podem não funcionar sem ajustes, mas o app principal (UI Flet, banco, lógica) roda normalmente.

## Estrutura importante

- `app.py`: ponto de entrada da aplicação (configura Flet e rotas).
- `models/`: modelos do banco de dados (SQLAlchemy) e configuração da base.
- `alembic/`: migrações de banco de dados.
- `caixa/`: lógica e interface da tela de caixa.
- `estoque/`: tela de controle de estoque (cadastro, edição, importação/exportação de CSV/PDF).
- `data/produtos.json`: arquivo JSON com lista de produtos (cache/backup simples usado por caixa e estoque).
- `exports/`: arquivos gerados (relatórios, exportações de estoque, etc.).

## Tecnologias usadas

- **Python**: 3.12 (definido em `pyproject.toml`).
- **Flet**: 0.11.0 (UI de desktop/web).
- **ORM**: SQLAlchemy 2.x.
- **Banco atual**: SQLite (arquivo, via `models/db_models.py`).
- **Migração planejada**: trocar o backend de dados para **MariaDB**, mantendo SQLAlchemy.

## Levar o projeto para outra máquina

Para rodar em outro computador:

- Copie toda a pasta do projeto **exceto** a pasta `.venv`.
- Se quiser levar os dados atuais:
  - Copie o arquivo de banco de dados SQLite (por exemplo `app.db`, se existir na raiz ou em `models/`).
  - Copie `data/produtos.json` se quiser manter a mesma lista inicial de produtos.
- Na nova máquina, siga a seção **Como rodar o projeto com uv**.

## Importar produtos via CSV

Na tela de **Estoque**:

- Use o botão **"Importar CSV"** para selecionar um arquivo `.csv` com colunas como:

```csv
ID,Nome,Categoria,Validade,Quantidade,Preço,Código de Barras
```

- Os produtos importados são salvos em `data/produtos.json` e passam a ser reconhecidos pelo leitor de código de barras na tela do **Caixa**.

---

Se alguém tiver dúvidas para rodar, basta seguir: `uv sync` e depois `uv run app.py` na pasta do projeto.

App Ponto Certo
