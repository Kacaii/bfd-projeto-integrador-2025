"""View do Caixa: registra vendas, controla carrinho e pagamentos.

- Faz leitura de produtos via código de barras (cache em memória).
- Integra com o núcleo de negócio (`pdv_core`) para gravar vendas.
- Atualiza estoque no JSON após venda (mantém compatibilidade com fluxo antigo).
"""

import flet as ft
import os
import json
import io
import base64
from types import SimpleNamespace

from utils.cupom import show_cupom_dialog
from .state import COLORS, PAYMENT_METHODS, FKEY_MAP
from .logic import (
    carregar_produtos_de_json,
    montar_cache_produtos,
    calcular_troco,
    montar_itens_cupom,
    validar_estoque_disponivel,
    persistir_estoque_json,
    montar_payload_pix,
)


def create_caixa_view(
    page: ft.Page, pdv_core, handle_back, current_user, appbar: ft.AppBar
):
    """Monta e retorna a View do Caixa.

    - `page`: instância principal do Flet.
    - `pdv_core`: objeto de regra de negócio (vendas, estoque em banco).
    - `handle_back`: callback para voltar à tela anterior.
    - `current_user`: usuário logado (pode ser usado para permissões).
    - `appbar`: barra de topo compartilhada entre views.
    """
    # Cache em memória de produtos; índice por id e código de barras
    produtos_cache = {}
    cache_loaded = ft.Ref[bool]()
    cache_loaded.current = False
    # Coluna que renderiza visualmente os itens do carrinho
    cart_items_column = ft.Column(spacing=1, expand=True, scroll="auto")
    # Total acumulado da venda atual
    total_value = ft.Ref[float]()
    total_value.current = 0.0

    # Textos exibidos na barra inferior (subtotal e total)
    subtotal_text = ft.Text(
        "R$ 0,00", size=20, weight="bold", color=COLORS["text_dark"]
    )
    total_final_text = ft.Text(
        "R$ 0,00", size=36, weight="bold", color=COLORS["secondary"]
    )
    # Campo de busca por código de barras e texto com nome/estoque do último produto
    search_field_ref = ft.Ref[ft.TextField]()
    product_name_text = ft.Text("", size=16, color=COLORS["primary"])

    # Carrega produtos para o cache a partir do JSON e/ou banco (pdv_core)
    def carregar_produtos_cache(force_reload: bool = False) -> bool:
        if cache_loaded.current and not force_reload:
            print(f"✅ Cache já carregado com {len(produtos_cache)} produtos")
            return True

        print("📦 Carregando cache de produtos...")

        try:
            produtos = []
            base_dir = os.path.dirname(os.path.dirname(__file__))
            arquivo = os.path.join(base_dir, "data", "produtos.json")
            if os.path.exists(arquivo):
                try:
                    with open(arquivo, "r", encoding="utf-8") as f:
                        dados = json.load(f)
                    produtos = carregar_produtos_de_json(dados)
                    print(
                        f"✅ Carregou {len(produtos)} produtos de {arquivo} (priorizado)"
                    )
                except Exception as e:
                    print(f"❌ Falha ao ler {arquivo}: {e}")

            # Se JSON falhar ou estiver vazio, busca direto no banco via pdv_core
            if not produtos:
                pdv_core_local = page.app_data.get("pdv_core")
                if not pdv_core_local:
                    print(
                        "❌ pdv_core não encontrado em page.app_data e produtos.json vazio!"
                    )
                    return False

                if hasattr(pdv_core_local, "get_produtos_list"):
                    produtos = pdv_core_local.get_produtos_list()
                    print(
                        f"✅ Método get_produtos_list() retornou {len(produtos)} produtos (pdv_core)"
                    )
                elif hasattr(pdv_core_local, "get_all_produtos"):
                    produtos = pdv_core_local.get_all_produtos()
                    print(
                        f"✅ Método get_all_produtos() retornou {len(produtos)} produtos (pdv_core)"
                    )
                else:
                    print(
                        "❌ Nenhum método de busca de produtos encontrado no pdv_core!"
                    )
                    return False

            if not produtos:
                print(
                    "❌ Nenhum produto disponível após tentativas de fallback (json e pdv_core)"
                )
                return False

            # Mapa auxiliar de produtos por ID (para ligar com dados do JSON)
            id_map = {}
            for p in produtos:
                if isinstance(p, dict):
                    id_map[str(p.get("id", "")).strip()] = p
                else:
                    id_map[str(getattr(p, "id", "")).strip()] = p

            # Mapeamentos extras: códigos de barras que só existem no JSON
            extra_mappings = {}
            if os.path.exists(arquivo):
                try:
                    with open(arquivo, "r", encoding="utf-8") as f:
                        dados_json = json.load(f)
                    for pj in dados_json:
                        cod = str(
                            pj.get("codigo_barras") or pj.get("codigo", "")
                        ).strip()
                        idv = str(pj.get("id", "")).strip()
                        if not cod:
                            continue
                        if idv and idv in id_map:
                            extra_mappings[cod] = id_map[idv]
                        else:
                            pj.setdefault(
                                "preco_venda",
                                float(pj.get("preco_venda", pj.get("preco", 0.0))),
                            )
                            pj.setdefault(
                                "nome",
                                pj.get("nome", pj.get("descricao", "Produto")),
                            )
                            pj.setdefault("quantidade", int(pj.get("quantidade", 0)))
                            extra_mappings[cod] = SimpleNamespace(**pj)
                except Exception as e:
                    print(f"⚠️ Falha ao ler {arquivo} para overlay de códigos: {e}")

            # Monta o cache final combinando produtos de banco + overlay do JSON
            produtos_cache.clear()
            produtos_cache.update(montar_cache_produtos(produtos, extra_mappings))

            cache_loaded.current = True
            sample_keys = list(produtos_cache.keys())[:10]
            print(f"✅ Cache criado com {len(produtos_cache)} produtos")
            print(f"🔎 Sample keys: {sample_keys}")
            try:
                present_1000 = "1000" in produtos_cache
            except Exception:
                present_1000 = False
            print(f"🔔 Código '1000' presente no cache? {present_1000}")
            return True
        except Exception as e:
            print(f"❌ ERRO CRÍTICO ao carregar produtos: {e}")
            import traceback

            traceback.print_exc()
            return False

    # Estado de pagamento e referências a campos de valor recebido/troco
    selected_payment_type = ft.Ref[str]()
    money_received_field = ft.Ref[ft.TextField]()
    change_text = ft.Ref[ft.Text]()

    # Estrutura em memória do carrinho (key = código do produto)
    cart_data = {}
    last_added_product_id = ft.Ref[str]()
    last_added_product_id.current = None
    payment_buttons_refs: list[ft.Ref] = []

    # Diálogos auxiliares para F6 (consulta) e F7 (cancelamento)
    price_check_dialog_ref = ft.Ref[ft.AlertDialog]()
    cancel_sale_dialog_ref = ft.Ref[ft.AlertDialog]()

    # Helper para exibir mensagens rápidas na parte inferior da tela
    def show_snackbar(message, color):
        page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor=color, duration=2000)
        page.snack_bar.open = True
        page.update()

    # ==========================
    # F6 - CONSULTA DE PREÇO
    # ==========================

    # Abre diálogo de "Consulta de Preço" (atalho F6)
    def open_price_check_dialog(e=None):
        if not cache_loaded.current:
            if not carregar_produtos_cache(force_reload=True):
                show_snackbar(
                    "Nenhum produto cadastrado para consulta.", COLORS["danger"]
                )
                return

            result_text = ft.Text("", size=16)

        # Faz a busca de preço/estoque a partir de um código de barras
        def do_price_lookup(code: str):
            codigo = (code or "").strip()
            if not codigo:
                show_snackbar("Informe um código.", COLORS["warning"])
                return

            produto = produtos_cache.get(codigo)
            if not produto:
                result_text.value = "Produto não encontrado."
                result_text.color = COLORS["danger"]
                page.update()
                return

            if isinstance(produto, dict):
                nome = produto.get("nome", "")
                preco = float(produto.get("preco_venda", 0.0))
                estoque = int(produto.get("quantidade", 0))
            else:
                nome = getattr(produto, "nome", "")
                preco = float(getattr(produto, "preco_venda", 0.0))
                estoque = int(getattr(produto, "estoque_atual", 0))

            result_text.value = f"{nome} — R$ {preco:.2f} — Estoque: {estoque}"
            result_text.color = COLORS["primary"] if estoque > 0 else COLORS["danger"]
            page.update()

        code_field = ft.TextField(
            label="Código de barras",
            prefix_icon=ft.Icons.QR_CODE_SCANNER,
            autofocus=True,
            border_radius=8,
            filled=True,
            bgcolor=ft.colors.WHITE,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_submit=lambda ev: do_price_lookup(ev.control.value),
        )

        def close_price_check_dialog(e=None):
            if price_check_dialog_ref.current:
                price_check_dialog_ref.current.open = False
                page.update()

        price_check_dialog_ref.current = ft.AlertDialog(
            modal=True,
            title=ft.Text("Consulta de Preço (F6)"),
            content=ft.Column(
                [code_field, ft.Divider(), result_text],
                tight=True,
                spacing=10,
                width=400,
            ),
            actions=[
                ft.TextButton("Fechar", on_click=close_price_check_dialog),
            ],
        )

        page.dialog = price_check_dialog_ref.current
        price_check_dialog_ref.current.open = True
        page.update()

    # =====================================
    # F7 - CANCELAR VENDA FINALIZADA (GERENTE)
    # =====================================

    # Abre diálogo de "Cancelar venda finalizada" (atalho F7, só gerente)
    def open_cancel_sale_dialog(e=None):
        """Abre o diálogo de cancelamento (F7) com lista de vendas do dia.

        O gerente apenas informa a senha; o usuário logado já vem preenchido
        e desabilitado, e a venda é escolhida em uma lista em vez de digitar ID.
        """

        from datetime import datetime, time

        hoje = datetime.now().date()
        inicio = datetime.combine(hoje, time.min)
        fim = datetime.combine(hoje, time.max)

        # Busca vendas do dia pelo core; se não houver método, cai para lista vazia
        vendas_dia = []
        if hasattr(pdv_core, "buscar_vendas_por_intervalo"):
            try:
                vendas_dia = pdv_core.buscar_vendas_por_intervalo(inicio, fim)
            except Exception as ex:
                print(f"Erro ao buscar vendas do dia para F7: {ex}")

        if not vendas_dia:
            show_snackbar("Nenhuma venda encontrada para hoje.", COLORS["warning"])
            return

        # Carrega produtos do JSON para detalhar itens (nome, preço, id)
        produtos_por_codigo = {}
        try:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            arquivo = os.path.join(base_dir, "data", "produtos.json")
            if os.path.exists(arquivo):
                with open(arquivo, "r", encoding="utf-8") as f:
                    dados_json = json.load(f)
                for pj in dados_json:
                    cod = str(pj.get("codigo_barras") or pj.get("codigo") or "").strip()
                    if not cod:
                        continue
                    produtos_por_codigo[cod] = pj
        except Exception as ex:
            print(f"[F7] Erro ao carregar produtos.json para detalhes da venda: {ex}")

        def make_option(v):
            # Cada entrada de v vem de buscar_vendas_por_intervalo
            vid = v.get("id")
            total = float(v.get("total", 0.0))
            data_str = v.get("data", "")

            # Monta uma linha de cabeçalho da venda
            header = f"#{vid} • {data_str} • Total: R$ {total:.2f}"

            # Monta um resumo dos itens (até alguns itens)
            itens = v.get("itens", []) or []
            itens_parts = []
            for idx, it in enumerate(itens[:3], start=1):
                cod = (
                    str(it.get("codigo_barras") or "").strip()
                    or str(it.get("produto_id") or "").strip()
                )
                qtd = it.get("quantidade", 0)

                # Tenta pegar nome/preço do JSON de produtos
                pj = produtos_por_codigo.get(cod)
                if pj:
                    nome = pj.get("nome") or pj.get("descricao") or "Produto"
                    pu = float(
                        pj.get(
                            "preco_venda",
                            pj.get("preco", it.get("preco_unitario", 0.0)),
                        )
                        or 0.0
                    )
                    pid = pj.get("id", "?")
                    itens_parts.append(
                        f"{idx}) ID {pid} • {cod} - {nome} x{qtd} R$ {pu:.2f}"
                    )
                else:
                    # Fallback: usa dados que vieram do banco
                    nome = it.get("produto", "Produto")
                    pu = float(it.get("preco_unitario", 0.0))
                    itens_parts.append(
                        f"{idx}) {cod or '?'} - {nome} x{qtd} R$ {pu:.2f}"
                    )

            if len(itens) > 3:
                itens_parts.append(f"... (+{len(itens) - 3} itens)")

            itens_str = (
                "\n".join(itens_parts) if itens_parts else "(Sem itens registrados)"
            )

            # Usa label multilinha para mostrar cabeçalho + itens
            label = f"{header}\n{itens_str}"
            return ft.Radio(value=str(vid), label=label)

        radios = [make_option(v) for v in vendas_dia]

        # Seleciona por padrão a venda mais recente (primeiro item)
        default_value = str(vendas_dia[0].get("id")) if vendas_dia else None

        vendas_group = ft.RadioGroup(
            value=default_value,
            content=ft.Column(radios, scroll="auto", height=200),
        )

        gerente_user_field = ft.TextField(
            label="Usuário do gerente",
            autofocus=True,
        )

        password_field = ft.TextField(
            label="Senha do gerente",
            password=True,
            can_reveal_password=True,
            on_submit=lambda e: do_cancel(),
        )

        status_text = ft.Text("", size=14)

        def do_cancel(e=None):
            selected_value = vendas_group.value
            username = (gerente_user_field.value or "").strip()
            password = (password_field.value or "").strip()

            print("[F7] do_cancel chamado - selected_value=", selected_value)
            print("[F7] username=", username)
            print("[F7] password_bruto=", repr(password))

            if not selected_value:
                show_snackbar("Selecione uma venda para cancelar.", COLORS["warning"])
                return

            if not username or not password:
                show_snackbar("Informe usuário e senha do gerente.", COLORS["warning"])
                return

            gerente = pdv_core.authenticate_user(username, password)
            if not gerente or getattr(gerente, "role", "") != "gerente":
                show_snackbar("Apenas GERENTE pode cancelar venda.", COLORS["danger"])
                return

            venda_id = int(selected_value)
            ok, msg = pdv_core.estornar_venda(venda_id, usuario=gerente.username)
            status_text.value = msg
            status_text.color = COLORS["primary"] if ok else COLORS["danger"]
            page.update()

            if ok:
                show_snackbar(
                    f"Venda #{venda_id} estornada com sucesso.",
                    COLORS["secondary"],
                )
                close_cancel_sale_dialog()

        def close_cancel_sale_dialog(e=None):
            if cancel_sale_dialog_ref.current:
                cancel_sale_dialog_ref.current.open = False
                page.update()

        cancel_sale_dialog_ref.current = ft.AlertDialog(
            modal=True,
            title=ft.Text("Cancelar Venda Finalizada (F7)"),
            content=ft.Column(
                [
                    ft.Text(
                        "Selecione a venda do dia que deseja cancelar:",
                        size=14,
                        weight="bold",
                    ),
                    vendas_group,
                    gerente_user_field,
                    password_field,
                    ft.Divider(),
                    status_text,
                ],
                tight=True,
                spacing=10,
                width=500,
            ),
            actions=[
                ft.TextButton("Cancelar venda", on_click=do_cancel),
                ft.TextButton("Fechar", on_click=close_cancel_sale_dialog),
            ],
        )

        page.dialog = cancel_sale_dialog_ref.current
        cancel_sale_dialog_ref.current.open = True
        page.update()

    # Limpa o carrinho e reseta estado de pagamento/troco
    def reset_cart(e=None):
        cart_items_column.controls.clear()
        cart_data.clear()
        calculate_total()
        selected_payment_type.current = None

        if money_received_field.current:
            money_received_field.current.value = ""
            money_received_field.current.visible = False
        if change_text.current:
            change_text.current.value = "Troco: R$ 0,00"
            change_text.current.visible = False

        for btn in payment_buttons_refs:
            btn.current.style.bgcolor = COLORS["card_bg"]
            btn.current.style.color = COLORS["text_dark"]

        # Só foca se o campo ainda estiver montado na página
        if search_field_ref.current and search_field_ref.current.page:
            search_field_ref.current.value = ""
            search_field_ref.current.focus()

        page.update()

    # Recalcula o total do carrinho e atualiza textos de subtotal/total
    def calculate_total():
        current_total = sum(item["preco"] * item["qtd"] for item in cart_data.values())
        total_value.current = current_total

        subtotal_text.value = f"R$ {current_total:.2f}".replace(".", ",")
        total_final_text.value = f"R$ {current_total:.2f}".replace(".", ",")

        if (
            selected_payment_type.current == "Dinheiro"
            and money_received_field.current
            and money_received_field.current.visible
        ):
            calculate_change(None)

        page.update()

    # Atualiza apenas a parte visual (UI) de um item do carrinho
    def update_cart_item_ui(product_id, new_quantity):
        if product_id in cart_data:
            item = cart_data[product_id]
            item["qtd_ref"].current.value = f"x{new_quantity}"
            new_line_total = item["preco"] * new_quantity
            item["total_row_ref"].current.value = f"R$ {new_line_total:.2f}".replace(
                ".", ","
            )
        page.update()

    # Atualiza a quantidade de um item no carrinho, respeitando estoque
    def update_cart_item(product_id, quantity_change):
        if product_id not in cart_data:
            return

        item = cart_data[product_id]
        new_quantity = item["qtd"] + quantity_change

        if quantity_change > 0:
            prod_obj = get_product_from_cache(product_id)
            available = get_stock_for_product_obj(prod_obj)
            qtd_atual = int(item.get("qtd", 0))
            ok, msg = validar_estoque_disponivel(available, qtd_atual, quantity_change)
            if not ok:
                show_snackbar(msg, COLORS["danger"])
                return

        if new_quantity <= 0:
            cart_items_column.controls.remove(item["card_ref"].current)
            del cart_data[product_id]
        else:
            item["qtd"] = new_quantity
            update_cart_item_ui(product_id, new_quantity)

        calculate_total()
        page.update()

    # Cria a linha visual de um item do carrinho (nome, qtd, preço)
    def create_cart_item_row(item_data, product_id):
        qtd_ref = ft.Ref[ft.Text]()
        total_row_ref = ft.Ref[ft.Text]()

        row = ft.Row(
            [
                ft.Text(
                    item_data["nome"],
                    expand=True,
                    size=14,
                    weight="bold",
                    color=COLORS["text_dark"],
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Container(
                    ft.Row(
                        [
                            ft.IconButton(
                                ft.icons.REMOVE,
                                icon_color=COLORS["danger"],
                                tooltip="Remover item",
                                icon_size=18,
                                on_click=lambda e: update_cart_item(product_id, -1),
                                style=ft.ButtonStyle(
                                    padding=5,
                                    shape=ft.RoundedRectangleBorder(radius=4),
                                ),
                            ),
                            ft.Text(
                                f"x{item_data['qtd']}",
                                ref=qtd_ref,
                                size=16,
                                weight="bold",
                                width=30,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.IconButton(
                                ft.icons.ADD,
                                icon_color=COLORS["secondary"],
                                tooltip="Adicionar item",
                                icon_size=18,
                                on_click=lambda e: update_cart_item(product_id, 1),
                                style=ft.ButtonStyle(
                                    padding=5,
                                    shape=ft.RoundedRectangleBorder(radius=4),
                                ),
                            ),
                        ],
                        spacing=0,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    width=150,
                    alignment=ft.alignment.center_right,
                ),
                ft.Text(
                    f"R$ {item_data['preco']:.2f}".replace(".", ","),
                    size=14,
                    color=COLORS["text_muted"],
                    width=100,
                    text_align=ft.TextAlign.RIGHT,
                ),
                ft.Text(
                    f"R$ {item_data['preco'] * item_data['qtd']:.2f}".replace(".", ","),
                    ref=total_row_ref,
                    size=16,
                    weight="bold",
                    color=COLORS["primary"],
                    width=120,
                    text_align=ft.TextAlign.RIGHT,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        )

        item_data["qtd_ref"] = qtd_ref
        item_data["total_row_ref"] = total_row_ref

        return ft.Container(
            row,
            border=ft.border.only(bottom=ft.border.BorderSide(1, ft.colors.BLACK12)),
            padding=ft.padding.symmetric(vertical=8, horizontal=10),
            bgcolor=COLORS["card_bg"],
        )

    # Adiciona um produto ao carrinho (ou incrementa se já existir)
    def add_to_cart(product, quantity: int = 1):
        product_id = str(product.codigo_barras).strip()

        if product_id in cart_data:
            update_cart_item(product_id, quantity)
        else:
            item_data = {
                "nome": product.nome,
                "preco": product.preco_venda,
                "qtd": quantity,
                "card_ref": ft.Ref[ft.Container](),
            }

            item_container = create_cart_item_row(item_data, product_id)
            item_data["card_ref"].current = item_container

            cart_data[product_id] = item_data
            last_added_product_id.current = product_id
            cart_items_column.controls.append(item_container)

            calculate_total()
            cart_items_column.scroll_to(offset=-1, duration=300)

    # Entrada principal de venda: adiciona produto usando código de barras
    def add_by_code(code):
        if not code:
            print("⚠️ Código vazio, ignorando...")
            return

        print(f"🔍 Buscando código: '{code}' (tipo: {type(code)})")

        if not cache_loaded.current:
            print("⚠️ Cache não carregado! Tentando recarregar...")
            if not carregar_produtos_cache(force_reload=True):
                show_snackbar(
                    "ERRO: Nenhum produto cadastrado no sistema!", COLORS["danger"]
                )
                search_field_ref.current.value = ""
                search_field_ref.current.focus()
                return

        codigo_busca = str(code).strip()
        print(f"🔍 Buscando código normalizado: '{codigo_busca}'")
        print(f"📦 Cache tem {len(produtos_cache)} produtos")
        try:
            keys_preview = list(produtos_cache.keys())[:12]
        except Exception:
            keys_preview = []
        print(f"🔎 Preview das chaves do cache: {keys_preview}")
        print(f"🔔 Chave exata presente? {codigo_busca in produtos_cache}")

        produto = produtos_cache.get(codigo_busca)

        if produto:
            nome_prod = (
                produto.nome
                if not isinstance(produto, dict)
                else produto.get("nome", "")
            )

            if isinstance(produto, dict):
                prod_key = str(
                    produto.get("codigo_barras")
                    or produto.get("codigo")
                    or produto.get("id", "")
                ).strip()
            else:
                prod_key = str(
                    getattr(produto, "codigo_barras", "")
                    or getattr(produto, "codigo", "")
                    or getattr(produto, "id", "")
                ).strip()

            available = get_stock_for_product_obj(produto)
            print(f"✅ Produto encontrado: {nome_prod} (estoque: {available})")

            try:
                product_name_text.value = f"{nome_prod} — Estoque: {available}"
                product_name_text.color = (
                    COLORS["primary"] if available > 0 else COLORS["danger"]
                )
            except Exception:
                pass

            current_in_cart = 0
            if prod_key in cart_data:
                current_in_cart = int(cart_data[prod_key].get("qtd", 0))

            if available <= 0:
                show_snackbar(
                    "Estoque insuficiente: produto sem unidades disponíveis.",
                    COLORS["danger"],
                )
                if search_field_ref.current:
                    search_field_ref.current.focus()
                return

            if available < (current_in_cart + 1):
                show_snackbar(
                    "Estoque insuficiente para adicionar outra unidade.",
                    COLORS["danger"],
                )
                if search_field_ref.current:
                    search_field_ref.current.focus()
                return

            add_to_cart(produto)
            search_field_ref.current.value = ""
            search_field_ref.current.focus()
            page.update()
        else:
            print(f"❌ Produto com código '{codigo_busca}' não encontrado")
            try:
                preview = list(produtos_cache.items())[:10]
                pretty = [(k, type(v).__name__) for k, v in preview]
                print(f"🔍 Preview cache items (key, type): {pretty}")
            except Exception as e:
                print(f"⚠️ Falha ao gerar preview do cache: {e}")
            try:
                product_name_text.value = ""
            except Exception:
                pass
            if produtos_cache:
                exemplos = list(produtos_cache.keys())[:3]
                show_snackbar(
                    f"Código inválido! Tente: {', '.join(exemplos)}", COLORS["danger"]
                )
            else:
                show_snackbar("NENHUM PRODUTO CADASTRADO NO SISTEMA!", COLORS["danger"])
            search_field_ref.current.focus()
            if search_field_ref.current:
                search_field_ref.current.focus()

    # Calcula o troco com base no valor recebido digitado
    def calculate_change(e):
        try:
            recebido, change = calcular_troco(
                total_value.current, money_received_field.current.value
            )
            change_text.current.value = f"Troco: R$ {change:.2f}".replace(".", ",")
            change_text.current.color = (
                COLORS["secondary"] if change >= 0 else COLORS["danger"]
            )
            page.update()
        except ValueError:
            change_text.current.value = "Valor inválido."
            change_text.current.color = COLORS["danger"]
            page.update()

    # Atualiza o JSON de estoque com base no carrinho (pós-venda)
    def persistir_estoque_apos_venda():
        base_dir = os.path.dirname(os.path.dirname(__file__))
        caminho = os.path.join(base_dir, "data", "produtos.json")
        persistir_estoque_json(caminho, cart_data)

    # Busca um produto no cache pelo identificador
    def get_product_from_cache(product_id):
        return produtos_cache.get(str(product_id).strip())

    # Extrai o estoque disponível de um objeto/dict de produto
    def get_stock_for_product_obj(p):
        try:
            if p is None:
                return 0
            if isinstance(p, dict):
                return int(p.get("quantidade", 0) or 0)
            return int(getattr(p, "quantidade", 0) or 0)
        except Exception:
            return 0

    # Seleciona o método de pagamento (dinheiro, cartão, Pix, etc.)
    def select_payment(type_name, btn_ref):
        selected_payment_type.current = type_name
        is_money = type_name == "Dinheiro"

        money_received_field.current.visible = is_money
        change_text.current.visible = is_money

        if is_money:
            calculate_change(None)

        for ref in payment_buttons_refs:
            if ref.current == btn_ref.current:
                ref.current.style.bgcolor = COLORS["primary"]
                ref.current.style.color = ft.colors.WHITE
            else:
                ref.current.style.bgcolor = COLORS["card_bg"]
                ref.current.style.color = COLORS["text_dark"]

        page.update()

    # Finaliza a venda: valida carrinho, grava no banco e emite cupom
    def finalize_transaction(e=None):
        p_type = selected_payment_type.current
        current_total = total_value.current

        if current_total <= 0:
            show_snackbar("O carrinho está vazio.", COLORS["danger"])
            return

        if not p_type:
            show_snackbar("Selecione um método de pagamento.", COLORS["danger"])
            return

        # Montar lista de itens para o PDVCore
        carrinho_itens = []
        for codigo, item in cart_data.items():
            carrinho_itens.append(
                {
                    "cod": codigo,
                    "qtd": int(item.get("qtd", 0) or 0),
                }
            )

        if not carrinho_itens:
            show_snackbar("O carrinho está vazio.", COLORS["danger"])
            return

        valor_pago = 0.0
        if p_type == "Dinheiro":
            try:
                received_str = (
                    money_received_field.current.value.replace("R$", "")
                    .replace(",", ".")
                    .strip()
                )
                if not received_str:
                    received_str = "0"
                valor_pago = float(received_str)
                if valor_pago < current_total:
                    show_snackbar("Valor recebido insuficiente.", COLORS["danger"])
                    return
            except ValueError:
                show_snackbar("Valor recebido inválido.", COLORS["danger"])
                return
        else:
            valor_pago = float(current_total)

        # Registrar venda no banco via PDVCore
        usuario_id = page.session.get("user_id")
        sucesso, resultado, troco_core = pdv_core.finalizar_venda(
            carrinho_itens, p_type, valor_pago, usuario_id
        )

        if not sucesso:
            show_snackbar(f"Erro ao finalizar venda: {resultado}", COLORS["danger"])
            return

        # Sincronizar estoque do JSON apenas após gravar no banco
        persistir_estoque_apos_venda()

        merchant_name = "Mercearia Ponto Certo"
        titulo_cupom = f"Cupom Fiscal - {merchant_name}"
        itens_cupom = montar_itens_cupom(cart_data)

        current_total = total_value.current
        received = None
        change = None
        if p_type == "Dinheiro" and money_received_field.current:
            received, change = calcular_troco(
                current_total, money_received_field.current.value
            )

        if p_type == "Pix":
            payload_text = montar_payload_pix("Mercearia Ponto Certo", current_total)
            qr_base64 = None
            try:
                import qrcode

                qr = qrcode.QRCode(box_size=6, border=2)
                qr.add_data(payload_text)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                qr_base64 = b64
            except Exception:
                qr_base64 = None

            original_keyboard_handler = page.on_keyboard_event

            def finalizar_e_mostrar_cupom():
                # Restaura handler global antes de qualquer coisa
                page.on_keyboard_event = original_keyboard_handler
                show_cupom_dialog(
                    page,
                    itens_cupom,
                    titulo_cupom,
                    current_total,
                    p_type,
                    received,
                    change,
                    auto_print=True,
                )
                pix_dialog.open = False
                page.update()
                reset_cart()
                show_snackbar(
                    f"Venda de R$ {current_total:.2f} finalizada em {p_type}.",
                    COLORS["secondary"],
                )

            def confirmar_pix(e):
                finalizar_e_mostrar_cupom()

            def cancelar_pix(e):
                page.on_keyboard_event = original_keyboard_handler
                pix_dialog.open = False
                page.update()

            qr_control = ft.Image(src_base64=qr_base64) if qr_base64 else ft.Container()
            pix_column = ft.Column(
                [
                    ft.Text(
                        "Aproxime o leitor para pagar via Pix",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Row([qr_control], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Text(payload_text, size=12),
                ],
                spacing=8,
            )

            pix_dialog = ft.AlertDialog(
                title=ft.Text("Pagamento via Pix"),
                content=pix_column,
                actions=[
                    ft.TextButton("Cancelar", on_click=cancelar_pix),
                    ft.ElevatedButton("Pagamento recebido", on_click=confirmar_pix),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )

            page.dialog = pix_dialog
            pix_dialog.open = True

            # Enquanto o diálogo Pix estiver aberto, enter confirma o pagamento
            def pix_keyboard_handler(e: ft.KeyboardEvent):
                if e.key == "Enter":
                    finalizar_e_mostrar_cupom()

            page.on_keyboard_event = pix_keyboard_handler
            page.update()
        else:
            show_cupom_dialog(
                page,
                itens_cupom,
                titulo_cupom,
                current_total,
                p_type,
                received,
                change,
                auto_print=True,
            )
            reset_cart()
            show_snackbar(
                f"Venda de R$ {current_total:.2f} finalizada em {p_type}.",
                COLORS["secondary"],
            )

    # Cria um botão de método de pagamento a partir de um item de configuração
    def create_payment_button(item):
        btn_ref = ft.Ref[ft.ElevatedButton]()
        payment_buttons_refs.append(btn_ref)

        return ft.Container(
            ft.ElevatedButton(
                ref=btn_ref,
                content=ft.Row(
                    [
                        ft.Icon(item["icon"], size=20),
                        ft.Text(
                            f"({item['key']}) {item['name']}",
                            size=14,
                            weight="bold",
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),
                data=item["name"],
                style=ft.ButtonStyle(
                    bgcolor=COLORS["card_bg"],
                    color=COLORS["text_dark"],
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.padding.symmetric(horizontal=15, vertical=10),
                    side=ft.border.BorderSide(1, ft.colors.BLACK12),
                    elevation=1,
                    overlay_color=ft.colors.BLACK12,
                ),
                on_click=lambda e, name=item["name"], ref=btn_ref: select_payment(
                    name, ref
                ),
                height=50,
                expand=True,
            ),
            padding=ft.padding.only(bottom=5),
        )

    payment_buttons = [create_payment_button(item) for item in PAYMENT_METHODS]

    # Campo de valor recebido (aparece apenas quando o pagamento é em dinheiro)
    money_received_input = ft.TextField(
        ref=money_received_field,
        label="Valor Recebido (R$)",
        prefix_text="R$",
        keyboard_type=ft.KeyboardType.NUMBER,
        on_change=calculate_change,
        visible=False,
        border_radius=8,
        filled=True,
        bgcolor=COLORS["background"],
        height=50,
        text_size=16,
    )

    # Texto grande exibindo o troco calculado
    change_display = ft.Text(
        ref=change_text,
        value="Troco: R$ 0,00",
        size=24,
        weight="bold",
        color=COLORS["secondary"],
        visible=False,
        text_align=ft.TextAlign.RIGHT,
    )

    # Painel da direita com métodos de pagamento, campo de valor recebido e troco
    payment_options_panel = ft.Container(
        ft.Column(
            [
                ft.Text(
                    "OPÇÕES DE PAGAMENTO",
                    size=18,
                    weight="bold",
                    color=COLORS["text_dark"],
                ),
                ft.Divider(height=10, color=ft.colors.BLACK12),
                ft.Column(payment_buttons, spacing=5),
                ft.Divider(height=10, color=ft.colors.BLACK12),
                # Campo de valor recebido (só aparece se pagamento for em dinheiro)
                money_received_input,
                ft.Divider(height=10, color=ft.colors.BLACK12),
                ft.Row(
                    [
                        ft.Text(
                            "Troco:",
                            size=24,
                            weight="bold",
                            color=COLORS["text_dark"],
                        ),
                        change_display,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(expand=True),
            ],
            spacing=10,
            expand=True,
        ),
        padding=ft.padding.all(20),
        bgcolor=COLORS["card_bg"],
        border_radius=ft.border_radius.all(12),
        width=350,
        border=ft.border.all(1, ft.colors.BLACK12),
    )

    # Cabeçalho da lista de itens do carrinho
    cart_header = ft.Container(
        content=ft.Row(
            [
                ft.Text(
                    "Produto",
                    expand=True,
                    size=14,
                    color=COLORS["text_dark"],
                    weight="w600",
                ),
                ft.Container(
                    ft.Text("Qtd", size=14, color=COLORS["text_dark"], weight="w600"),
                    width=150,
                    alignment=ft.alignment.center_right,
                ),
                ft.Text(
                    "Preço Unit.",
                    size=14,
                    color=COLORS["text_dark"],
                    weight="w600",
                    width=100,
                    text_align=ft.TextAlign.RIGHT,
                ),
                ft.Text(
                    "Total",
                    size=14,
                    color=COLORS["text_dark"],
                    weight="w600",
                    width=120,
                    text_align=ft.TextAlign.RIGHT,
                ),
            ],
            spacing=10,
        ),
        padding=ft.padding.only(left=10, right=10, top=10, bottom=10),
        border=ft.border.only(bottom=ft.border.BorderSide(2, ft.colors.BLACK12)),
        bgcolor=ft.colors.BLACK12,
    )

    # Campo principal onde o operador digita / bipa o código de barras
    search_field = ft.TextField(
        ref=search_field_ref,
        label="Código de Barras",
        autofocus=True,
        prefix_icon=ft.icons.QR_CODE_SCANNER,
        border_radius=8,
        filled=True,
        bgcolor=ft.colors.WHITE,
        height=50,
        content_padding=15,
        text_size=16,
        on_submit=lambda e: add_by_code(e.control.value),
    )

    # Painel principal do lado esquerdo (carrinho)
    cart_main_panel = ft.Container(
        ft.Column(
            [
                ft.Text(
                    "CAIXA LIVRE",
                    size=32,
                    weight="bold",
                    color=COLORS["primary"],
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(
                    ft.Column(
                        [
                            search_field,
                            product_name_text,
                            ft.Text(
                                "Status: ABERTO",
                                size=14,
                                color=COLORS["text_muted"],
                            ),
                        ],
                        spacing=5,
                    ),
                    padding=ft.padding.only(bottom=20),
                ),
                cart_header,
                ft.Container(cart_items_column, expand=True, bgcolor=COLORS["card_bg"]),
            ],
            spacing=15,
            expand=True,
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.all(20),
        bgcolor=COLORS["card_bg"],
        expand=True,
        border_radius=12,
    )

    # Barra inferior com ações rápidas (cancelar venda, F6, F7, total, F12)
    bottom_bar = ft.Container(
        ft.Row(
            [
                ft.FilledButton(
                    "CANCELAR VENDA (F11)",
                    on_click=lambda e: (
                        reset_cart(),
                        show_snackbar("Venda Cancelada.", COLORS["danger"]),
                    ),
                    style=ft.ButtonStyle(
                        bgcolor=COLORS["primary"],
                        color=ft.colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    height=45,
                    width=220,
                ),
                # NOVOS BOTÕES F6 / F7
                ft.ElevatedButton(
                    "F6 - Consultar preço",
                    icon=ft.icons.SEARCH,
                    bgcolor=COLORS["card_bg"],
                    on_click=open_price_check_dialog,
                ),
                ft.ElevatedButton(
                    "F7 - Estornar venda",
                    icon=ft.icons.CANCEL,
                    bgcolor=COLORS["danger"],
                    color=ft.colors.WHITE,
                    on_click=open_cancel_sale_dialog,
                ),
                ft.Container(expand=True),
                ft.Row(
                    [
                        ft.Text("Subtotal:", size=20, color=COLORS["text_dark"]),
                        subtotal_text,
                    ],
                    spacing=10,
                    alignment=ft.MainAxisAlignment.END,
                ),
                ft.VerticalDivider(width=30, thickness=2, color=ft.colors.BLACK12),
                ft.Container(
                    ft.Row(
                        [
                            ft.Text(
                                "TOTAL:",
                                size=30,
                                weight="bold",
                                color=COLORS["text_dark"],
                            ),
                            total_final_text,
                        ],
                        alignment=ft.MainAxisAlignment.END,
                        spacing=15,
                    ),
                    width=300,
                ),
                ft.FilledButton(
                    "FINALIZAR VENDA (F12)",
                    icon=ft.icons.PAYMENT,
                    on_click=finalize_transaction,
                    style=ft.ButtonStyle(
                        bgcolor=COLORS["primary"],
                        color=ft.colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    height=45,
                    width=240,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=20, vertical=10),
        bgcolor=COLORS["card_bg"],
        border=ft.border.only(top=ft.border.BorderSide(1, ft.colors.BLACK12)),
    )

    # Atalhos de teclado do caixa (F-keys, Escape, etc.)
    def handle_keyboard_shortcuts(e: ft.KeyboardEvent):
        if e.key in FKEY_MAP:
            idx = FKEY_MAP[e.key]
            if idx < len(PAYMENT_METHODS):
                method = PAYMENT_METHODS[idx]
                btn_ref = payment_buttons_refs[idx]
                select_payment(method["name"], btn_ref)
                search_field_ref.current.focus()
                page.update()

        if e.key == "F6":
            open_price_check_dialog()
            return

        if e.key == "F7":
            open_cancel_sale_dialog()
            return
        if e.key == "F8":
            # Diminuir quantidade do último item adicionado
            if (
                last_added_product_id.current
                and last_added_product_id.current in cart_data
            ):
                update_cart_item(last_added_product_id.current, -1)
            return
        if e.key == "F9":
            # Aumentar quantidade do último item adicionado
            if (
                last_added_product_id.current
                and last_added_product_id.current in cart_data
            ):
                update_cart_item(last_added_product_id.current, 1)
            return
        elif e.key == "F11":
            reset_cart()
            show_snackbar("Venda Cancelada.", COLORS["danger"])
        elif e.key == "F12":
            finalize_transaction()
        elif e.key == "Escape":
            if cart_data:
                show_snackbar(
                    "Saindo do caixa. Venda não finalizada.", COLORS["danger"]
                )
            reset_cart()
            handle_back()

    # Layout principal em duas colunas: carrinho (esq) e pagamentos (dir)
    caixa_layout = ft.Row(
        [cart_main_panel, payment_options_panel],
        expand=True,
        spacing=15,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    # View associada à rota "/caixa"
    view = ft.View(
        "/caixa",
        [
            appbar,
            ft.Container(
                content=caixa_layout,
                padding=ft.padding.only(left=15, right=15, top=15, bottom=0),
                expand=True,
            ),
            bottom_bar,
        ],
        bgcolor=COLORS["background"],
    )

    # expor o handler de atalhos via atributo da view
    view.handle_keyboard_shortcuts = handle_keyboard_shortcuts

    # Handler chamado quando a view é montada (equivalente a on_load)
    def on_view_did_mount(e):
        print("🎰 View do Caixa montada")
        page.bgcolor = COLORS["background"]

        if carregar_produtos_cache():
            print("✅ Cache carregado na inicialização")
        else:
            print("⚠️ Cache vazio na inicialização, tentando novamente...")
            page.run_task(
                lambda: (page.sleep(300), carregar_produtos_cache(force_reload=True))
            )

        if search_field_ref.current:
            search_field_ref.current.focus()

    view.on_view_did_mount = on_view_did_mount

    return view
