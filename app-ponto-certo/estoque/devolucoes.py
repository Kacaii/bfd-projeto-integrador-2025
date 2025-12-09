import json
import os
from datetime import datetime
import uuid


DEVOLUCOES_FILE = "data/devolucoes.json"


def garantir_arquivo_devolucoes():
    """Garante que o arquivo de devoluções existe"""
    if not os.path.exists(DEVOLUCOES_FILE):
        os.makedirs(os.path.dirname(DEVOLUCOES_FILE), exist_ok=True)
        with open(DEVOLUCOES_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def carregar_devol():
    """Carrega todas as devoluções do arquivo JSON"""
    garantir_arquivo_devolucoes()
    try:
        with open(DEVOLUCOES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def salvar_devol(devolucoes):
    """Salva devoluções no arquivo JSON"""
    garantir_arquivo_devolucoes()
    with open(DEVOLUCOES_FILE, "w", encoding="utf-8") as f:
        json.dump(devolucoes, f, ensure_ascii=False, indent=2)


def adicionar_devolucao(
    produto_id, produto_nome, quantidade, preco_unitario, motivo=""
):
    """Adiciona uma nova devolução ao arquivo"""
    devolucoes = carregar_devol()

    nova_devolucao = {
        "id": str(uuid.uuid4()),
        "produto_id": produto_id,
        "produto_nome": produto_nome,
        "quantidade": quantidade,
        "preco_unitario": preco_unitario,
        "valor_total": quantidade * preco_unitario,
        "motivo": motivo,
        "data": datetime.now().isoformat(),
    }

    devolucoes.append(nova_devolucao)
    salvar_devol(devolucoes)

    return nova_devolucao


def remover_devolucao(devolucao_id):
    """Remove uma devolução pelo ID"""
    devolucoes = carregar_devol()
    devolucoes = [d for d in devolucoes if d.get("id") != devolucao_id]
    salvar_devol(devolucoes)


def obter_devolucoes_produto(produto_id):
    """Obtém todas as devoluções de um produto específico"""
    devolucoes = carregar_devol()
    return [d for d in devolucoes if d.get("produto_id") == produto_id]


def obter_devolucoes_data(data_inicio, data_fim):
    """Obtém devoluções em um intervalo de data"""
    devolucoes = carregar_devol()
    resultado = []

    for d in devolucoes:
        data_devol = datetime.fromisoformat(d.get("data", ""))
        data_inicio_dt = datetime.fromisoformat(data_inicio)
        data_fim_dt = datetime.fromisoformat(data_fim)

        if data_inicio_dt <= data_devol <= data_fim_dt:
            resultado.append(d)

    return resultado


def estatisticas_devolucoes():
    """Retorna estatísticas gerais das devoluções"""
    devolucoes = carregar_devol()

    if not devolucoes:
        return {
            "total_devolucoes": 0,
            "valor_total": 0,
            "quantidade_total": 0,
            "produtos_devolvidos": 0,
        }

    produtos_unicos = set(d.get("produto_id") for d in devolucoes)

    return {
        "total_devolucoes": len(devolucoes),
        "valor_total": sum(d.get("valor_total", 0) for d in devolucoes),
        "quantidade_total": sum(d.get("quantidade", 0) for d in devolucoes),
        "produtos_devolvidos": len(produtos_unicos),
    }


def adicionar_troca(devolucao_id, novo_produto_id, novo_produto_nome):
    """Registra uma troca de produto com o mesmo valor"""
    devolucoes = carregar_devol()

    # Encontrar a devolução original
    devolucao = None
    for d in devolucoes:
        if d.get("id") == devolucao_id:
            devolucao = d
            break

    if not devolucao:
        raise ValueError(f"Devolução {devolucao_id} não encontrada")

    # Registrar a troca
    troca = {
        "id": str(uuid.uuid4()),
        "devolucao_id": devolucao_id,
        "produto_id_original": devolucao.get("produto_id"),
        "produto_nome_original": devolucao.get("produto_nome"),
        "novo_produto_id": novo_produto_id,
        "novo_produto_nome": novo_produto_nome,
        "valor_original": devolucao.get("valor_total"),
        "quantidade": devolucao.get("quantidade"),
        "data_troca": datetime.now().isoformat(),
    }

    # Atualizar a devolução com informação de troca
    for d in devolucoes:
        if d.get("id") == devolucao_id:
            d["foi_trocado"] = True
            d["troca_info"] = troca
            break

    salvar_devol(devolucoes)
    return troca


def obter_trocas():
    """Retorna todas as trocas registradas"""
    devolucoes = carregar_devol()
    trocas = []

    for d in devolucoes:
        if d.get("foi_trocado"):
            trocas.append(d.get("troca_info"))

    return trocas


def obter_trocas_pendentes():
    """Retorna devoluções que podem ser trocadas (não foram trocadas ainda)"""
    devolucoes = carregar_devol()
    return [d for d in devolucoes if not d.get("foi_trocado", False)]


def validar_produto_existe(pdv_core, produto_id_ou_barras):
    """Valida se produto existe por ID ou código de barras"""
    try:
        from models.db_models import Produto

        # Tenta buscar por ID primeiro
        try:
            produto_id = int(produto_id_ou_barras)
            produto = pdv_core.session.query(Produto).filter_by(id=produto_id).first()
            if produto:
                return True, produto
        except (ValueError, TypeError):
            pass

        # Se não encontrar por ID, tenta por código de barras
        produto = (
            pdv_core.session.query(Produto)
            .filter_by(codigo_barras=str(produto_id_ou_barras))
            .first()
        )
        return produto is not None, produto
    except Exception as e:
        print(f"[TROCA] Erro ao validar produto: {e}")
        return False, None


def atualizar_estoque_troca(pdv_core, produto_original_id, novo_produto_id, quantidade):
    """Atualiza estoque: diminui produto original, aumenta novo produto"""
    try:
        from models.db_models import Produto

        # Buscar produtos
        prod_original = (
            pdv_core.session.query(Produto).filter_by(id=produto_original_id).first()
        )
        prod_novo = (
            pdv_core.session.query(Produto).filter_by(id=novo_produto_id).first()
        )

        if not prod_original or not prod_novo:
            return False, "Produto não encontrado"

        # Verificar estoque do novo produto
        estoque_novo = prod_novo.estoque_atual or 0
        if estoque_novo < quantidade:
            return (
                False,
                f"Estoque insuficiente de {prod_novo.nome} (disponível: {estoque_novo})",
            )

        # Atualizar estoque
        prod_original.estoque_atual = (prod_original.estoque_atual or 0) + quantidade
        prod_novo.estoque_atual = estoque_novo - quantidade

        pdv_core.session.commit()
        return True, "Estoque atualizado com sucesso"
    except Exception as e:
        pdv_core.session.rollback()
        print(f"[TROCA] Erro ao atualizar estoque: {e}")
        return False, f"Erro ao atualizar estoque: {str(e)}"
