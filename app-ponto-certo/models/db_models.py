# db_models.py

import flet as ft
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
)
from sqlalchemy.orm import sessionmaker, relationship, declarative_base, Session
from datetime import datetime, date
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente (se existirem) ou usa SQLite local
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///mercadinho.db")

Base = declarative_base()


class User(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # gerente, caixa, iro
    full_name = Column(String(100), nullable=True)

    # Relação bidirecional com CaixaSession
    caixa_sessions = relationship(
        "CaixaSession", back_populates="user", cascade="all, delete-orphan"
    )


class Fornecedor(Base):
    __tablename__ = "fornecedores"
    id = Column(Integer, primary_key=True)
    nome_razao_social = Column(String(200), nullable=False, index=True)
    cnpj_cpf = Column(String(20), unique=True, nullable=True, index=True)
    contato = Column(String(100), nullable=True)
    condicao_pagamento = Column(
        String(100), nullable=True
    )  # "Débito, Dinheiro, Crédito, Pix"
    prazo_entrega_medio = Column(String(50), nullable=True)  # ex: "7 dias úteis"
    status = Column(
        String(20), nullable=False, default="ativo", index=True
    )  # ativo, inativo

    # Relação bidirecional com Produto
    produtos = relationship(
        "Produto", back_populates="fornecedor", cascade="all, delete-orphan"
    )


class Produto(Base):
    __tablename__ = "produtos"
    id = Column(Integer, primary_key=True)
    codigo_barras = Column(String(50), unique=True, nullable=False, index=True)
    nome = Column(String(200), nullable=False, index=True)
    preco_custo = Column(Float, nullable=False)
    preco_venda = Column(Float, nullable=False)
    estoque_atual = Column(Integer, default=0, nullable=False)
    estoque_minimo = Column(
        Integer, default=10, nullable=True
    )  # Para controle de estoque mínimo
    validade = Column(String(20), nullable=True)

    # Chave estrangeira e relação bidirecional
    fornecedor_id = Column(
        Integer, ForeignKey("fornecedores.id"), nullable=True, index=True
    )
    fornecedor = relationship("Fornecedor", back_populates="produtos")

    # Propriedade para compatibilidade com código legado que usa 'estoque'
    @property
    def estoque(self):
        """Alias para compatibilidade com código legado"""
        return self.estoque_atual

    @estoque.setter
    def estoque(self, value):
        """Alias para compatibilidade com código legado"""
        self.estoque_atual = value


class Venda(Base):
    __tablename__ = "vendas"
    id = Column(Integer, primary_key=True)
    data_venda = Column(DateTime, default=datetime.now, nullable=False, index=True)
    total = Column(Float, nullable=False)
    usuario_responsavel = Column(String(100), nullable=False, index=True)
    forma_pagamento = Column(String(50), nullable=False, default="Dinheiro")
    valor_pago = Column(Float, nullable=False, default=0.0)
    status = Column(
        String(20), nullable=False, default="CONCLUIDA", index=True
    )  # CONCLUIDA, ESTORNADA, PENDENTE

    # Relação bidirecional
    itens = relationship(
        "ItemVenda", back_populates="venda", cascade="all, delete-orphan"
    )


class ItemVenda(Base):
    __tablename__ = "itens_venda"
    id = Column(Integer, primary_key=True)
    venda_id = Column(Integer, ForeignKey("vendas.id"), nullable=False, index=True)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False, index=True)
    quantidade = Column(Integer, nullable=False)
    preco_unitario = Column(Float, nullable=False)

    # Relações bidirecionais
    venda = relationship("Venda", back_populates="itens")
    produto = relationship("Produto")


class MovimentoFinanceiro(Base):
    __tablename__ = "movimentos_financeiros"
    id = Column(Integer, primary_key=True)
    data = Column(DateTime, default=datetime.now, nullable=False, index=True)
    descricao = Column(String(200), nullable=False)
    tipo = Column(
        String(50), nullable=False, index=True
    )  # RECEITA, DESPESA, FECHAMENTO_CAIXA
    valor = Column(Float, nullable=False)
    usuario_responsavel = Column(String(100), nullable=False, index=True)


class CaixaSession(Base):
    __tablename__ = "caixa_sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)

    opening_time = Column(DateTime, default=datetime.now, nullable=False)
    opening_balance = Column(Float, nullable=False)

    closing_time = Column(DateTime)
    closing_balance_system = Column(Float)
    closing_balance_actual = Column(Float)

    status = Column(
        String(20), default="Open", nullable=False, index=True
    )  # Open, Closed
    notes = Column(Text, nullable=True)

    # Relação bidirecional
    user = relationship("User", back_populates="caixa_sessions")

    @property
    def difference(self):
        """Calcula a quebra/sobra de caixa."""
        if (
            self.closing_balance_system is not None
            and self.closing_balance_actual is not None
        ):
            return round(self.closing_balance_actual - self.closing_balance_system, 2)
        return 0.0

    @property
    def current_balance(self):
        """Calcula saldo atual (aberto + vendas do dia)"""
        # TODO: Implementar cálculo real incluindo vendas do dia
        return self.opening_balance if hasattr(self, "opening_balance") else 0.0


class Expense(Base):
    """Tabela de Contas a Pagar / Despesas"""

    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True)
    descricao = Column(String(200), nullable=False)
    valor = Column(Float, nullable=False)
    vencimento = Column(String(10), nullable=False)  # formato dd/mm/aaaa
    categoria = Column(String(50), nullable=True)
    status = Column(
        String(20), default="Pendente", nullable=False, index=True
    )  # Pendente, Pago
    data_cadastro = Column(DateTime, default=datetime.now, nullable=False)
    data_pagamento = Column(DateTime, nullable=True)


class Receivable(Base):
    """Tabela de Contas a Receber / Receitas"""

    __tablename__ = "receivables"
    id = Column(Integer, primary_key=True)
    descricao = Column(String(200), nullable=False)
    valor = Column(Float, nullable=False)
    vencimento = Column(String(10), nullable=False)  # formato dd/mm/aaaa
    origem = Column(String(50), nullable=True)
    status = Column(
        String(20), default="Pendente", nullable=False, index=True
    )  # Pendente, Recebido
    data_cadastro = Column(DateTime, default=datetime.now, nullable=False)
    data_recebimento = Column(DateTime, nullable=True)


# ====================================================================
# Funções de inicialização
# ====================================================================
def init_db():
    """Cria o engine e as tabelas se não existirem"""
    engine = create_engine(DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """Retorna uma nova sessão do banco de dados"""
    Session = sessionmaker(bind=engine)
    return Session()


# ====================================================================
# Funções utilitárias (BÔNUS - úteis para desenvolvimento)
# ====================================================================
def reset_database():
    """
    ⚠️ APAGA E RECRIA TODAS AS TABELAS (USE COM EXTREMO CUIDADO!)
    Útil apenas em desenvolvimento.
    """
    engine = create_engine(DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("🔄 Banco de dados resetado com sucesso!")


def seed_sample_data(session):
    """
    Popula o banco com dados de exemplo para desenvolvimento
    """
    # TODO: Implementar conforme necessário
    pass
