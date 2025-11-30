"""Módulo principal de regras de negócio do sistema (PDV / SGV).

Aqui fica a classe `PDVCore`, responsável por concentrar o acesso
ao banco via SQLAlchemy e implementar a lógica de negócio usada
pelas telas (login, caixa, estoque, fornecedores, financeiro, etc.).
"""

from sqlalchemy.orm import Session, relationship
from sqlalchemy import func
from datetime import datetime, date
from models.db_models import (
    User,
    Produto,
    Fornecedor,
    Venda,
    ItemVenda,
    MovimentoFinanceiro,
    CaixaSession,
    Expense,
    Receivable,
)

# Hash de senha com passlib (bcrypt é preferido, pbkdf2_sha256 como alternativa).
try:
    from passlib.hash import bcrypt
except Exception:
    bcrypt = None

# Tentar alternativa segura caso bcrypt não tenha backend (ex.: falta pacote 'bcrypt')
try:
    from passlib.hash import pbkdf2_sha256
except Exception:
    pbkdf2_sha256 = None


class PDVCore:
    """Classe principal de lógica de negócios para o SGV.

    Responsabilidades principais:
    - Autenticação e gerenciamento de usuários
    - Registro de vendas (PDV) e atualização de estoque
    - Relatórios de vendas e produtos
    - Controle financeiro (despesas/receitas) e sessões de caixa
    - Cadastros e operações com fornecedores
    """

    def __init__(self, session: Session):
        self.session = session

    # ====================================================================
    # MÉTODOS DE USUÁRIO
    # ====================================================================

    def authenticate_user(self, username, password):
        """Autentica um usuário a partir de username e senha.

        Suporta hashes gerados com bcrypt, pbkdf2_sha256 e, como
        fallback, senhas em texto plano (para legado). Se encontrar
        senha em texto plano válida, tenta regravar já com hash.
        """
        # Busca usuário pelo username e verifica hash da senha
        user = self.session.query(User).filter_by(username=username).first()
        if not user:
            return None

        stored = getattr(user, "password", "") or ""
        try:
            # Verifica com bcrypt (se disponível e se o hash aparenta ser bcrypt)
            if stored.startswith("$2") and bcrypt:
                if bcrypt.verify(password, stored):
                    return user
                return None

            # Verifica com pbkdf2_sha256 (se disponível)
            if stored.startswith("$pbkdf2-sha256$") and pbkdf2_sha256:
                if pbkdf2_sha256.verify(password, stored):
                    return user
                return None

            # Fallback: senha em texto plano (legado)
            if password == stored:
                # Re-hash a senha para segurança usando o melhor disponível
                try:
                    if bcrypt:
                        user.password = bcrypt.hash(password)
                    elif pbkdf2_sha256:
                        user.password = pbkdf2_sha256.hash(password)
                    else:
                        user.password = password
                    self.session.commit()
                except Exception:
                    self.session.rollback()
                return user
            return None
        except Exception:
            return None

    def get_user_by_id(self, user_id):
        return self.session.query(User).filter_by(id=user_id).first()

    def get_all_users(self):
        """Retorna todos os usuários, ordenados por username."""
        self.session.expire_all()
        return self.session.query(User).order_by(User.username).all()

    def update_user_settings(self, user_id, full_name, new_password):
        """Atualiza nome completo e/ou senha de um usuário existente."""
        try:
            user = self.session.query(User).filter_by(id=user_id).first()
            if not user:
                return False, "Usuário não encontrado."

            user.full_name = full_name
            if new_password:
                # Armazenar senha com hash, preferindo bcrypt, cair para pbkdf2_sha256 se necessário
                try:
                    if bcrypt:
                        user.password = bcrypt.hash(new_password)
                    elif pbkdf2_sha256:
                        user.password = pbkdf2_sha256.hash(new_password)
                    else:
                        user.password = new_password
                except Exception:
                    # Em caso de falha de backend do bcrypt, tentar pbkdf2
                    try:
                        if pbkdf2_sha256:
                            user.password = pbkdf2_sha256.hash(new_password)
                        else:
                            user.password = new_password
                    except Exception:
                        user.password = new_password

            self.session.commit()
            return True, "Configurações atualizadas com sucesso!"
        except Exception as e:
            self.session.rollback()
            return False, f"Erro ao atualizar: {e}"

    def create_user(
        self, username: str, password: str, role: str, full_name: str = None
    ):
        """Cria um novo usuário no banco.

        Retorna (True, user_obj) em sucesso ou (False, mensagem) em erro.
        Faz validações simples (campos obrigatórios, unicidade) e
        grava a senha com hash, se possível.
        """
        try:
            if not username or not password or not role:
                return False, "Username, senha e role são obrigatórios."

            # Verifica unicidade
            existing = self.session.query(User).filter_by(username=username).first()
            if existing:
                return False, "Nome de usuário já existe."

            # Hash da senha se disponível
            # Tentar usar bcrypt, se falhar usar pbkdf2_sha256 como fallback mais portátil
            try:
                if bcrypt:
                    stored_password = bcrypt.hash(password)
                elif pbkdf2_sha256:
                    stored_password = pbkdf2_sha256.hash(password)
                else:
                    stored_password = password
            except Exception:
                # Se bcrypt lançar erro de backend, tentar pbkdf2_sha256
                try:
                    if pbkdf2_sha256:
                        stored_password = pbkdf2_sha256.hash(password)
                    else:
                        stored_password = password
                except Exception:
                    stored_password = password

            user = User(
                username=username,
                password=stored_password,
                role=role,
                full_name=full_name,
            )
            self.session.add(user)
            self.session.commit()
            return True, user
        except Exception as e:
            self.session.rollback()
            return False, f"Erro ao criar usuário: {e}"

    def delete_user(self, user_id: int):
        """Remove um usuário do banco.

        Faz uma proteção extra para não remover o último gerente.
        Retorna (True, mensagem) ou (False, mensagem).
        """
        try:
            user = self.session.query(User).filter_by(id=user_id).first()
            if not user:
                return False, "Usuário não encontrado."

            # Proteção simples: não permitir remover último gerente
            if user.role == "gerente":
                total_gerentes = (
                    self.session.query(User).filter_by(role="gerente").count()
                )
                if total_gerentes <= 1:
                    return False, "Não é permitido remover o último gerente."

            self.session.delete(user)
            self.session.commit()
            return True, "Usuário removido com sucesso."
        except Exception as e:
            self.session.rollback()
            return False, f"Erro ao remover usuário: {e}"

    # ====================================================================
    # MÉTODOS DE VENDA (PDV)
    # ====================================================================

    def buscar_produto(self, codigo_barras):
        """Busca um produto pelo código de barras no banco."""
        return (
            self.session.query(Produto).filter_by(codigo_barras=codigo_barras).first()
        )

    def finalizar_venda(self, carrinho, forma_pagamento, valor_pago, usuario_id):
        """Finaliza uma venda a partir do carrinho usado no PDV.

        - Verifica se o caixa do dia não está fechado
        - Cria registro de `Venda` e seus `ItemVenda`
        - Atualiza estoque de cada produto
        - Calcula troco com base em `valor_pago`
        """
        if self.verificar_status_caixa_hoje():
            return (
                False,
                "O caixa já foi FECHADO hoje. Não é possível registrar novas vendas.",
                0.0,
            )

        total_venda = 0.0
        try:
            # trata caso usuario_id venha None ou usuário não seja encontrado
            usuario = self.get_user_by_id(usuario_id) if usuario_id else None
            usuario_responsavel = usuario.username if usuario is not None else "caixa"

            venda = Venda(
                total=0.0,
                usuario_responsavel=usuario_responsavel,
                forma_pagamento=forma_pagamento,
                valor_pago=valor_pago,
                status="CONCLUIDA",
            )
            self.session.add(venda)
            self.session.flush()

            for item in carrinho:
                # Usa first() em vez de one() para não explodir se não existir no banco
                produto = (
                    self.session.query(Produto)
                    .filter_by(codigo_barras=item["cod"])
                    .first()
                )
                qtd = item["qtd"]

                # Se o produto não existir no banco, registra a venda mesmo assim,
                # apenas sem vínculo com tabela Produto (produto_id None)
                if not produto:
                    item_venda = ItemVenda(
                        venda_id=venda.id,
                        produto_id=None,
                        quantidade=qtd,
                        preco_unitario=0.0,
                    )
                    self.session.add(item_venda)
                    continue

                if (produto.estoque_atual or 0) < qtd:
                    raise Exception(f"Estoque insuficiente para {produto.nome}")
                produto.estoque_atual = (produto.estoque_atual or 0) - qtd

                item_venda = ItemVenda(
                    venda_id=venda.id,
                    produto_id=produto.id,
                    quantidade=qtd,
                    preco_unitario=produto.preco_venda,
                )
                self.session.add(item_venda)
                total_venda += produto.preco_venda * qtd

            venda.total = total_venda
            self.session.commit()
            troco = max(0.0, valor_pago - total_venda)
            return True, total_venda, troco
        except Exception as e:
            self.session.rollback()
            print(f"[ERRO FINALIZAR_VENDA] {e}")
            return False, str(e), 0.0

    # ====================================================================
    # MÉTODOS DE INVENTÁRIO/PRODUTO
    # ====================================================================

    def cadastrar_ou_atualizar_produto(self, dados_produto):
        """Cadastra um novo produto ou registra entrada de estoque.

        Se o código de barras já existir, atualiza campos e soma quantidade
        ao estoque atual. Caso contrário, cria um novo registro.
        """
        cod = dados_produto["codigo_barras"]
        produto = self.session.query(Produto).filter_by(codigo_barras=cod).first()
        try:
            if produto:
                produto.nome = dados_produto["nome"]
                produto.preco_custo = dados_produto["preco_custo"]
                produto.preco_venda = dados_produto["preco_venda"]
                produto.validade = dados_produto["validade"]
                produto.estoque_atual += dados_produto["quantidade"]
                acao = "atualizado (Entrada de estoque)"
            else:
                produto = Produto(
                    codigo_barras=cod,
                    nome=dados_produto["nome"],
                    preco_custo=dados_produto["preco_custo"],
                    preco_venda=dados_produto["preco_venda"],
                    estoque_atual=dados_produto["quantidade"],
                    validade=dados_produto["validade"],
                )
                self.session.add(produto)
                acao = "cadastrado"

            self.session.commit()
            return True, f"Produto '{produto.nome}' {acao} com sucesso!"
        except Exception as e:
            self.session.rollback()
            if "UNIQUE constraint failed: produtos.codigo_barras" in str(e):
                return False, "Erro: Código de Barras já cadastrado."
            return False, f"Erro ao {acao}: {e}"

    def get_produtos_list(self):
        """Retorna lista de produtos ordenada pelo nome."""
        return self.session.query(Produto).order_by(Produto.nome).all()

    def gerar_relatorio_produtos(self):
        """Gera lista com dados resumidos dos produtos.

        Cada item contém estoque, preços e margem de lucro estimada.
        """
        self.session.expire_all()
        produtos = self.session.query(Produto).all()
        relatorio = []
        for p in produtos:
            margem_lucro = p.preco_venda - p.preco_custo if p.preco_custo > 0 else 0
            relatorio.append(
                {
                    "id": p.id,
                    "nome": p.nome,
                    "estoque": p.estoque_atual,
                    "custo": p.preco_custo,
                    "venda": p.preco_venda,
                    "margem": margem_lucro,
                }
            )
        return relatorio

    def buscar_vendas_detalhadas(self):
        """Retorna vendas com informações resumidas para relatórios.

        Inclui data formatada, usuário responsável, total, forma de
        pagamento e uma descrição breve (primeiro item).
        """
        self.session.expire_all()
        vendas = self.session.query(Venda).order_by(Venda.data_venda.desc()).all()
        relatorio = []
        for v in vendas:
            if v.itens and v.itens[0].produto:
                primeiro_item_nome = v.itens[0].produto.nome
            else:
                primeiro_item_nome = "Venda Vazia/Não Finalizada"

            usuario_nome = (
                self.session.query(User)
                .filter_by(username=v.usuario_responsavel)
                .first()
            )
            usuario_str = (
                usuario_nome.full_name if usuario_nome else v.usuario_responsavel
            )

            relatorio.append(
                {
                    "id": v.id,
                    "data": v.data_venda.strftime("%d/%m/%Y %H:%M"),
                    "usuario": usuario_str,
                    "total": v.total,
                    "pagamento": v.forma_pagamento,
                    "status": v.status,
                    "descricao_breve": f"Venda {v.id}: {primeiro_item_nome}...",
                }
            )

        return relatorio

    def buscar_vendas_por_intervalo(self, start_dt: datetime, end_dt: datetime):
        """Retorna vendas cujo `data_venda` esteja entre `start_dt` e `end_dt` (inclusive).

        Cada venda retorna um dicionário com chave `itens` contendo lista de itens:
        [{"produto": nome, "quantidade": qtd, "preco_unitario": preco}, ...]
        """
        try:
            self.session.expire_all()
            vendas = (
                self.session.query(Venda)
                .filter(Venda.data_venda >= start_dt, Venda.data_venda <= end_dt)
                .order_by(Venda.data_venda.desc())
                .all()
            )
            relatorio = []
            for v in vendas:
                itens_list = []
                for it in v.itens:
                    produto_obj = getattr(it, "produto", None)
                    nome = getattr(produto_obj, "nome", "<produto>")
                    codigo = getattr(produto_obj, "codigo_barras", None)
                    produto_id = getattr(produto_obj, "id", None)
                    itens_list.append(
                        {
                            "produto": nome,
                            "produto_id": produto_id,
                            "codigo_barras": codigo,
                            "quantidade": it.quantidade,
                            "preco_unitario": it.preco_unitario,
                        }
                    )

                usuario_nome = (
                    self.session.query(User)
                    .filter_by(username=v.usuario_responsavel)
                    .first()
                )
                usuario_str = (
                    usuario_nome.full_name if usuario_nome else v.usuario_responsavel
                )

                relatorio.append(
                    {
                        "id": v.id,
                        "data": v.data_venda.strftime("%d/%m/%Y %H:%M"),
                        "usuario": usuario_str,
                        "total": v.total,
                        "pagamento": v.forma_pagamento,
                        "status": v.status,
                        "descricao_breve": f"Venda {v.id}",
                        "itens": itens_list,
                    }
                )

            print(
                f"[DEBUG] buscar_vendas_por_intervalo retornou {len(relatorio)} vendas para {start_dt} -> {end_dt}"
            )
            return relatorio
        except Exception as ex:
            print(f"Erro em buscar_vendas_por_intervalo: {ex}")
            return []

    def estornar_venda(self, venda_id: int, usuario: str = None):
        """Marca uma venda como ESTORNADA e repõe o estoque dos produtos.

        Retorna (True, mensagem) em sucesso ou (False, mensagem) em erro.
        """
        try:
            venda = self.session.query(Venda).filter_by(id=venda_id).first()
            if not venda:
                return False, "Venda não encontrada."
            if venda.status == "ESTORNADA":
                return False, "Venda já estornada."

            # repor estoque
            for it in venda.itens:
                try:
                    produto = (
                        self.session.query(Produto).filter_by(id=it.produto_id).first()
                    )
                    if produto:
                        produto.estoque_atual = (produto.estoque_atual or 0) + (
                            it.quantidade or 0
                        )
                except Exception:
                    # continua mesmo que um item falhe
                    pass

            venda.status = "ESTORNADA"
            self.session.commit()
            return True, "Venda estornada com sucesso."
        except Exception as ex:
            self.session.rollback()
            print(f"Erro em estornar_venda: {ex}")
            return False, str(ex)

    # ====================================================================
    # MÉTODOS FINANCEIROS/CAIXA (EXISTENTES + CORRIGIDOS)
    # ====================================================================

    def verificar_status_caixa_hoje(self):
        """Retorna True se já existir um fechamento de caixa no dia atual."""
        hoje = date.today()
        fechamento_existente = (
            self.session.query(MovimentoFinanceiro)
            .filter(
                func.date(MovimentoFinanceiro.data) == hoje,
                MovimentoFinanceiro.tipo == "FECHAMENTO_CAIXA",
            )
            .first()
        )
        return fechamento_existente is not None

    def registrar_despesa(self, user, descricao, valor):
        """Registra despesa rápida (uso interno, não é a tela Financeiro)."""
        if valor <= 0:
            return False, "O valor da despesa deve ser positivo."
        try:
            despesa = MovimentoFinanceiro(
                descricao=descricao,
                valor=valor,
                tipo="DESPESA",
                usuario_responsavel=user,
            )
            self.session.add(despesa)
            self.session.commit()
            return True, f"Despesa de R$ {valor:.2f} registrada: {descricao}"
        except Exception as e:
            self.session.rollback()
            return False, f"Erro ao registrar despesa: {e}"

    # ====================================================================
    # MÉTODOS DE CAIXASESSION (EXISTENTES - OK)
    # ====================================================================

    def get_current_open_session(self, user_id: int = None):
        """Obtém a sessão de caixa aberta para o usuário (se houver)."""
        query = self.session.query(CaixaSession).filter(CaixaSession.status == "Open")
        if user_id:
            query = query.filter(CaixaSession.user_id == user_id)
        return query.first()

    def get_all_closed_sessions(self):
        """Retorna todas as sessões de caixa já fechadas."""
        return (
            self.session.query(CaixaSession)
            .filter(CaixaSession.status == "Closed")
            .order_by(CaixaSession.closing_time.desc())
            .all()
        )

    # ====================================================================
    # NOVOS MÉTODOS FINANCEIROS PARA A TELA FINANCEIRO
    # ====================================================================

    def open_new_caixa(self, user_id: int, opening_balance: float):
        """Abre um novo caixa para o usuário informado."""
        try:
            new_session = CaixaSession(
                user_id=user_id,
                opening_balance=opening_balance,
                opening_time=datetime.now(),
                status="Open",
            )
            self.session.add(new_session)
            self.session.commit()
            print(f"✅ CaixaSession criado: ID={new_session.id}, User={user_id}")
            return new_session
        except Exception as e:
            self.session.rollback()
            print(f"❌ ERRO ao abrir caixa: {str(e)}")
            raise e

    def close_caixa_session(
        self,
        session_id: int,
        closing_balance_system: float,
        closing_balance_actual: float,
        notes: str = None,
    ):
        """Fecha e audita uma sessão de caixa existente."""
        try:
            session_to_close = self.session.query(CaixaSession).get(session_id)
            if not session_to_close or session_to_close.status == "Closed":
                return None

            session_to_close.closing_time = datetime.now()
            session_to_close.closing_balance_system = closing_balance_system
            session_to_close.closing_balance_actual = closing_balance_actual
            session_to_close.status = "Closed"
            session_to_close.notes = notes

            self.session.commit()
            print(f"✅ CaixaSession fechado: ID={session_id}")
            return session_to_close
        except Exception as e:
            self.session.rollback()
            print(f"❌ ERRO ao fechar caixa: {str(e)}")
            raise e

    def create_expense(
        self, descricao: str, valor: float, vencimento: str, categoria: str
    ):
        """Cria uma despesa para ser exibida na tela Financeiro."""
        try:
            expense = Expense(
                descricao=descricao,
                valor=valor,
                vencimento=vencimento,
                categoria=categoria,
                status="Pendente",
                data_cadastro=datetime.now(),
            )
            self.session.add(expense)
            self.session.commit()
            print(f"✅ Expense criado: ID={expense.id}")
            return True, "Despesa criada com sucesso!"
        except Exception as e:
            self.session.rollback()
            print(f"❌ ERRO ao criar despesa: {str(e)}")
            return False, f"Erro: {str(e)}"

    def create_receivable(
        self, descricao: str, valor: float, vencimento: str, origem: str
    ):
        """Cria uma receita (recebível) para a tela Financeiro."""
        try:
            receivable = Receivable(
                descricao=descricao,
                valor=valor,
                vencimento=vencimento,
                origem=origem,
                status="Pendente",
                data_cadastro=datetime.now(),
            )
            self.session.add(receivable)
            self.session.commit()
            print(f"✅ Receivable criado: ID={receivable.id}")
            return True, "Receita criada com sucesso!"
        except Exception as e:
            self.session.rollback()
            print(f"❌ ERRO ao criar receita: {str(e)}")
            return False, f"Erro: {str(e)}"

    def mark_expense_as_paid(self, expense_id: int):
        """Marca uma despesa como paga e registra data de pagamento."""
        try:
            expense = self.session.query(Expense).get(expense_id)
            if expense:
                expense.status = "Pago"
                expense.data_pagamento = datetime.now()
                self.session.commit()
                print(f"✅ Expense marcado como pago: ID={expense_id}")
                return True
            return False
        except Exception as e:
            self.session.rollback()
            print(f"❌ ERRO ao marcar despesa: {str(e)}")
            return False

    def mark_receivable_as_paid(self, receivable_id: int):
        """Marca um recebível como recebido e registra data de recebimento."""
        try:
            receivable = self.session.query(Receivable).get(receivable_id)
            if receivable:
                receivable.status = "Recebido"
                receivable.data_recebimento = datetime.now()
                self.session.commit()
                print(f"✅ Receivable marcado como recebido: ID={receivable_id}")
                return True
            return False
        except Exception as e:
            self.session.rollback()
            print(f"❌ ERRO ao marcar recebível: {str(e)}")
            return False

    def get_pending_expenses(self):
        """Busca todas as despesas com status "Pendente"."""
        try:
            return (
                self.session.query(Expense)
                .filter_by(status="Pendente")
                .order_by(Expense.vencimento)
                .all()
            )
        except Exception as e:
            print(f"❌ ERRO ao buscar despesas: {str(e)}")
            return []

    def get_pending_receivables(self):
        """Busca todos os recebíveis com status "Pendente"."""
        try:
            return (
                self.session.query(Receivable)
                .filter_by(status="Pendente")
                .order_by(Receivable.vencimento)
                .all()
            )
        except Exception as e:
            print(f"❌ ERRO ao buscar recebíveis: {str(e)}")
            return []

    # ====================================================================
    # MÉTODO DASHBOARD FINANCEIRO
    # ====================================================================

    def get_dashboard_data(self):
        """Busca dados reais do dashboard do banco de dados"""
        try:
            # Saldo atual: soma de todas as receitas recebidas - todas as despesas pagas
            total_receitas = (
                self.session.query(func.sum(Receivable.valor))
                .filter(Receivable.status == "Recebido")
                .scalar()
                or 0
            )
            total_despesas = (
                self.session.query(func.sum(Expense.valor))
                .filter(Expense.status == "Pago")
                .scalar()
                or 0
            )
            saldo_atual = total_receitas - total_despesas

            # Do mês atual
            mes_atual = datetime.now().month
            ano_atual = datetime.now().year

            receitas_mes = (
                self.session.query(func.sum(Receivable.valor))
                .filter(
                    Receivable.status == "Recebido",
                    func.extract("month", Receivable.data_recebimento) == mes_atual,
                    func.extract("year", Receivable.data_recebimento) == ano_atual,
                )
                .scalar()
                or 0
            )

            despesas_mes = (
                self.session.query(func.sum(Expense.valor))
                .filter(
                    Expense.status == "Pago",
                    func.extract("month", Expense.data_pagamento) == mes_atual,
                    func.extract("year", Expense.data_pagamento) == ano_atual,
                )
                .scalar()
                or 0
            )

            return {
                "saldo_atual": float(saldo_atual),
                "receitas_mes": float(receitas_mes),
                "despesas_mes": float(despesas_mes),
                "lucro_mes": float(receitas_mes - despesas_mes),
            }
        except Exception as ex:
            print(f"❌ Erro em get_dashboard_data: {ex}")
            # Retorna valores padrão se der erro
            return {
                "saldo_atual": 0.0,
                "receitas_mes": 0.0,
                "despesas_mes": 0.0,
                "lucro_mes": 0.0,
            }

    # ====================================================================
    # MÉTODOS DE FORNECEDOR
    # ====================================================================

    def get_all_fornecedores(self):
        self.session.expire_all()
        return (
            self.session.query(Fornecedor).order_by(Fornecedor.nome_razao_social).all()
        )

    def get_fornecedor_by_id(self, fornecedor_id):
        try:
            return self.session.query(Fornecedor).filter_by(id=fornecedor_id).first()
        except Exception:
            return None

    def get_produtos_by_fornecedor(self, fornecedor_id):
        try:
            return (
                self.session.query(Produto)
                .filter_by(fornecedor_id=fornecedor_id)
                .order_by(Produto.nome)
                .all()
            )
        except Exception:
            return []

    def get_all_produtos(self):
        # compatibilidade com código que espera esse método
        return self.get_produtos_list()

    def get_historico_compras_fornecedor(self, fornecedor_id):
        """Retorna lista de objetos com atributos 'data' e 'valor_total' para o histórico."""
        from types import SimpleNamespace

        try:
            # Buscar vendas que possuam itens cujo produto pertence ao fornecedor
            vendas = (
                self.session.query(Venda)
                .join(ItemVenda, ItemVenda.venda_id == Venda.id)
                .join(Produto, Produto.id == ItemVenda.produto_id)
                .filter(Produto.fornecedor_id == fornecedor_id)
                .order_by(Venda.data_venda.desc())
                .all()
            )

            historico = []
            for v in vendas:
                valor_total = 0.0
                for it in v.itens:
                    # somente soma itens do fornecedor
                    if getattr(it.produto, "fornecedor_id", None) == fornecedor_id:
                        valor_total += it.quantidade * it.preco_unitario
                historico.append(
                    SimpleNamespace(data=v.data_venda, valor_total=valor_total)
                )

            return historico
        except Exception:
            return []

    def excluir_fornecedor(self, fornecedor_id):
        try:
            fornecedor = (
                self.session.query(Fornecedor).filter_by(id=fornecedor_id).first()
            )
            if not fornecedor:
                return False, "Fornecedor não encontrado."

            # Verifica produtos vinculados
            if fornecedor.produtos and len(fornecedor.produtos) > 0:
                return False, "FOREIGN KEY: fornecedor tem produtos vinculados"

            self.session.delete(fornecedor)
            self.session.commit()
            return (
                True,
                f"Fornecedor '{getattr(fornecedor, 'nome_razao_social', '')}' excluído com sucesso!",
            )
        except Exception as e:
            self.session.rollback()
            return False, str(e)

    def cadastrar_ou_atualizar_fornecedor(self, dados, fornecedor_id=None):
        try:
            if fornecedor_id:
                fornecedor = (
                    self.session.query(Fornecedor).filter_by(id=fornecedor_id).first()
                )
                if not fornecedor:
                    return False, "Fornecedor não encontrado."
                acao = "atualizado"
            else:
                fornecedor = Fornecedor()
                self.session.add(fornecedor)
                acao = "cadastrado"

            fornecedor.nome_razao_social = dados["nome_razao_social"]
            fornecedor.cnpj_cpf = dados["cnpj_cpf"]
            fornecedor.contato = dados["contato"]
            fornecedor.condicao_pagamento = dados["condicao_pagamento"]
            fornecedor.prazo_entrega_medio = dados["prazo_entrega_medio"]
            fornecedor.status = dados["status"]

            self.session.commit()
            return (
                True,
                f"Fornecedor '{fornecedor.nome_razao_social}' {acao} com sucesso!",
            )
        except Exception as e:
            self.session.rollback()
            if "UNIQUE constraint failed: fornecedores.cnpj_cpf" in str(e):
                return False, "Erro: O CNPJ/CPF informado já está cadastrado."
            return False, f"Erro ao salvar fornecedor: {e}"
