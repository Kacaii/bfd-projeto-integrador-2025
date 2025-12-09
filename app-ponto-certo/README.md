# Ponto Certo - Sistema de Gestão PDV

Sistema completo de gestão de ponto de venda (PDV) desenvolvido em Python com interface gráfica usando Flet.

## 📋 Requisitos

- **Python 3.12+** instalado no seu computador
- **pip** (gerenciador de pacotes Python)
- **Git** (opcional, para clonar o repositório)

## 🚀 Instalação e Execução

### Windows

#### 1. Clone o repositório (ou baixe o projeto)

```powershell
git clone <url-do-repositorio>
cd app-ponto-certo
```

#### 2. Crie o ambiente virtual

```powershell
python -m venv .venv
```

#### 3. Ative o ambiente virtual

```powershell
.\.venv\Scripts\Activate.ps1
```

**Nota:** Se você receber um erro de política de execução, execute:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### 4. Atualize pip, setuptools e wheel

```powershell
python -m pip install --upgrade pip setuptools wheel
```

#### 5. Instale as dependências

```powershell
pip install -r requirements.txt
```

#### 6. Execute o projeto

```powershell
python app.py
```

---

### Linux (Ubuntu/Debian)

#### 1. Clone o repositório (ou baixe o projeto)

```bash
git clone <url-do-repositorio>
cd apppontocerto
```

#### 2. Instale as dependências do sistema (se necessário)

```bash
sudo apt-get update
sudo apt-get install python3 python3-pip python3-venv
```

#### 3. Crie o ambiente virtual

```bash
python3 -m venv .venv
```

#### 4. Ative o ambiente virtual

```bash
source .venv/bin/activate
```

#### 5. Atualize pip, setuptools e wheel

```bash
python -m pip install --upgrade pip setuptools wheel
```

#### 6. Instale as dependências

```bash
pip install -r requirements.txt
```

#### 7. Execute o projeto

```bash
python app.py
```

---

## 📦 Dependências Principais

- **Flet** - Framework para interface gráfica multiplataforma
- **Flask** - Framework web (backend)
- **SQLAlchemy** - ORM para banco de dados
- **Pandas** - Processamento e análise de dados
- **PyInstaller** - Gerar executável da aplicação
- **Pytest** - Framework de testes

Para ver a lista completa de dependências, consulte `requirements.txt`.

## ✅ Verificar Instalação

Para verificar se tudo foi instalado corretamente, execute:

```powershell
# Windows
pip list

# Linux
pip list
```

Você deve ver todas as dependências listadas.

## 🛠️ Estrutura do Projeto

```
apppontocerto/
├── app.py                 # Arquivo principal da aplicação
├── requirements.txt       # Dependências do projeto
├── alembic/              # Migrations do banco de dados
├── core/                 # Lógica central da aplicação
├── models/               # Modelos de banco de dados
├── vendas/               # Módulo de vendas
├── caixa/                # Módulo de caixa
├── estoque/              # Módulo de estoque
├── financeiro/           # Módulo financeiro
├── usuarios/             # Gerenciamento de usuários
├── login/                # Autenticação
├── produtos/             # Gerenciamento de produtos
├── fornecedores/         # Gerenciamento de fornecedores
├── devolucoes/           # Gerenciamento de devoluções
├── configuracoes/        # Configurações da aplicação
└── data/                 # Dados armazenados (JSON)
```

## ⚙️ Configuração

As configurações da aplicação são gerenciadas através de variáveis de ambiente. Crie um arquivo `.env` na raiz do projeto se necessário:

```
# Exemplo de .env
DEBUG=False
DATABASE_URL=sqlite:///app.db
```

## 🧪 Executar Testes

Para executar os testes:

```powershell
# Windows
pytest

# Linux
pytest
```

## 📦 Gerar Executável (Windows)

Para criar um executável standalone:

```powershell
pyinstaller --onefile --windowed app.py
```

O executável será gerado na pasta `dist/`.

## 🐛 Solução de Problemas

### Erro: "python command not found"

**Windows:** Certifique-se de que Python está adicionado ao PATH durante a instalação.

**Linux:** Use `python3` em vez de `python`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 app.py
```

### Erro: "Módulo não encontrado"

Certifique-se de que o ambiente virtual está ativado e instale as dependências novamente:

```bash
# Windows
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Linux
source .venv/bin/activate
pip install -r requirements.txt
```

### Erro de permissão no PowerShell (Windows)

Se receber erro de execução do script:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Erro ao instalar PyMuPDF ou outras bibliotecas

Algumas bibliotecas podem requerer ferramentas de build. Instale:

**Windows:**

```powershell
python -m pip install --upgrade setuptools wheel
```

**Linux:**

```bash
sudo apt-get install build-essential python3-dev
```

## 📄 Licença

[]

## 👥 Contribuidores

[]

## 📧 Suporte

Para relatar problemas ou sugestões, entre em contato através de [email/issue tracker].

---

**Última atualização:** Dezembro de 2025
