"""
Lógica de Devoluções e Trocas para o Caixa
Funções para processar devoluções direto na tela de vendas
"""

import logging
from models.db_models import Venda, ItemVenda, Produto
from estoque.devolucoes import adicionar_devolucao

logger = logging.getLogger(__name__)


def buscar_vendas_do_caixa(pdv_core, usuario_responsavel: str, limite=10):
    """
    Busca as últimas vendas realizadas pelo caixa

    Args:
        pdv_core: Instância do PDVCore
        usuario_responsavel: Username do caixa
        limite: Número máximo de vendas a retornar

    Returns:
        Lista de vendas formatadas para exibição
    """
    try:
        session = pdv_core.session

        # Debug: Verificar o que está sendo buscado
        logger.info(
            f"[BUSCAR VENDAS] Procurando vendas para: usuario='{usuario_responsavel}', limite={limite}"
        )

        # Primeiro, tenta com o usuário específico
        vendas = (
            session.query(Venda)
            .filter(
                Venda.usuario_responsavel == usuario_responsavel,
                Venda.status == "CONCLUIDA",
            )
            .order_by(Venda.data_venda.desc())
            .limit(limite)
            .all()
        )

        logger.info(
            f"[BUSCAR VENDAS] Encontradas {len(vendas)} vendas para usuário '{usuario_responsavel}'"
        )

        # Se não encontrou, tenta buscar TODAS as vendas CONCLUIDAS (fallback)
        if not vendas:
            logger.warning(
                f"[BUSCAR VENDAS] Nenhuma venda encontrada para '{usuario_responsavel}', buscando todas as vendas CONCLUIDAS..."
            )
            vendas = (
                session.query(Venda)
                .filter(Venda.status == "CONCLUIDA")
                .order_by(Venda.data_venda.desc())
                .limit(limite)
                .all()
            )
            logger.info(
                f"[BUSCAR VENDAS] Encontradas {len(vendas)} vendas CONCLUIDAS no total"
            )

        vendas_formatadas = []
        for venda in vendas:
            produtos = []
            for item in venda.itens:
                produto = session.query(Produto).filter_by(id=item.produto_id).first()
                produto_nome = produto.nome if produto else "Desconhecido"
                produtos.append(
                    {
                        "nome": produto_nome,
                        "quantidade": item.quantidade,
                        "preco": item.preco_unitario,
                    }
                )

            vendas_formatadas.append(
                {
                    "id": venda.id,
                    "data": venda.data_venda.strftime("%d/%m/%Y %H:%M"),
                    "total": venda.total,
                    "pagamento": venda.forma_pagamento,
                    "status": venda.status,
                    "produtos": produtos,
                    "resumo": ", ".join([p["nome"] for p in produtos[:2]]),
                }
            )

        return vendas_formatadas

    except Exception as e:
        logger.error(f"Erro ao buscar vendas do caixa: {e}")
        return []


def processar_devolucao_e_trocar(pdv_core, venda_id: int, usuario_responsavel: str):
    """
    Processa a devolução de uma venda completa e prepara para troca

    Args:
        pdv_core: Instância do PDVCore
        venda_id: ID da venda a devolver
        usuario_responsavel: Username de quem está processando

    Returns:
        Tupla (sucesso, mensagem, carrinho_para_nova_venda)
    """
    try:
        session = pdv_core.session

        # Buscar venda
        venda = session.query(Venda).filter_by(id=venda_id).first()

        if not venda:
            return False, "Venda não encontrada", []

        if venda.status != "CONCLUIDA":
            return False, f"Venda com status {venda.status} não pode ser devolvida", []

        # Processar cada item
        carrinho_para_troca = []

        for item in venda.itens:
            produto = session.query(Produto).filter_by(id=item.produto_id).first()

            if not produto:
                logger.warning(f"Produto {item.produto_id} não encontrado")
                continue

            # Devolver ao estoque
            produto.estoque_atual = (produto.estoque_atual or 0) + item.quantidade

            # Registrar devolução
            try:
                adicionar_devolucao(
                    produto_id=produto.id,
                    produto_nome=produto.nome,
                    quantidade=item.quantidade,
                    preco_unitario=item.preco_unitario,
                    motivo=f"Troca de Venda #{venda_id} (Caixa)",
                    processada_por=usuario_responsavel,
                )
            except Exception as ex_devol:
                logger.warning(f"Falha ao registrar devolução: {ex_devol}")

            # Preparar item para novo carrinho (mesmos produtos)
            carrinho_para_troca.append(
                {
                    "cod": produto.codigo_barras,
                    "nome": produto.nome,
                    "qtd": item.quantidade,
                    "preco": item.preco_unitario,
                    "produto_id": produto.id,
                }
            )

        # Marcar venda como estornada
        venda.status = "ESTORNADA"
        session.commit()

        logger.info(f"Venda #{venda_id} devolvida e marcada para troca")

        return (
            True,
            "Venda devolvida com sucesso. Selecione novos produtos para trocar.",
            carrinho_para_troca,
        )

    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao processar devolução: {e}")
        return False, f"Erro ao processar devolução: {str(e)}", []


def processar_devolucao_parcial(
    pdv_core, venda_id: int, item_ids: list, usuario_responsavel: str
):
    """
    Processa devolução de apenas alguns itens da venda

    Args:
        pdv_core: Instância do PDVCore
        venda_id: ID da venda
        item_ids: Lista de IDs de ItemVenda a devolver
        usuario_responsavel: Username de quem está processando

    Returns:
        Tupla (sucesso, mensagem)
    """
    try:
        session = pdv_core.session

        venda = session.query(Venda).filter_by(id=venda_id).first()

        if not venda:
            return False, "Venda não encontrada"

        total_devolvido = 0.0

        for item_id in item_ids:
            item = (
                session.query(ItemVenda)
                .filter_by(id=item_id, venda_id=venda_id)
                .first()
            )

            if not item:
                continue

            produto = session.query(Produto).filter_by(id=item.produto_id).first()

            if produto:
                # Devolver ao estoque
                produto.estoque_atual = (produto.estoque_atual or 0) + item.quantidade

                # Registrar devolução
                try:
                    adicionar_devolucao(
                        produto_id=produto.id,
                        produto_nome=produto.nome,
                        quantidade=item.quantidade,
                        preco_unitario=item.preco_unitario,
                        motivo=f"Devolução Parcial de Venda #{venda_id} (Caixa)",
                        processada_por=usuario_responsavel,
                    )
                except Exception as ex_devol:
                    logger.warning(f"Falha ao registrar devolução: {ex_devol}")

                total_devolvido += item.quantidade * item.preco_unitario

        # Atualizar total da venda
        venda.total -= total_devolvido
        session.commit()

        logger.info(f"Devolução parcial de {len(item_ids)} itens da venda #{venda_id}")

        return (
            True,
            f"Devolução parcial processada. R$ {total_devolvido:.2f} devolvido.",
        )

    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao processar devolução parcial: {e}")
        return False, f"Erro ao processar devolução: {str(e)}"
