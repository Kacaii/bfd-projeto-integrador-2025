"""
Componentes de UI para Devolver & Trocar no Caixa
Modal e botões para gerenciar devoluções e trocas direto da tela de vendas
"""

import flet as ft
from vendas.vendas_devolucoes_logic import (
    buscar_vendas_do_caixa,
    processar_devolucao_e_trocar,
)
from models.db_models import Produto

# Cores padrão
PRIMARY_COLOR = "#007BFF"
DANGER_COLOR = "#FF7675"
SUCCESS_COLOR = "#00B894"
TEXT_COLOR = "#2D3748"
CARD_BG = "#F8F9FA"

# Armazenar referências de modais (evita recriação)
_modais_cache = {}


def buscar_produto_por_barras(pdv_core, codigo_barras: str):
    """Busca produto pelo código de barras"""
    try:
        session = pdv_core.session
        produto = session.query(Produto).filter_by(codigo_barras=codigo_barras).first()
        if produto:
            return {
                "id": produto.id,
                "nome": produto.nome,
                "preco": produto.preco_venda,
                "estoque": produto.estoque_atual,
            }
        return None
    except Exception as e:
        print(f"[DEVOLVER TROCAR] Erro ao buscar produto: {e}")
        return None


def criar_modal_confirmacao_troca(
    page, carrinho_original, trocas_selecionadas, callback_confirmar
):
    """
    Cria modal de confirmação para a troca

    Args:
        page: Página Flet
        carrinho_original: Lista de produtos originais devolvidos
        trocas_selecionadas: Dict com produtos selecionados para trocar
        callback_confirmar: Callback quando confirmar a troca
    """

    # Criar coluna com comparação de produtos
    comparacao_column = ft.Column(spacing=12)

    for produto_original in carrinho_original:
        produto_id = produto_original["id"]
        produto_troca = trocas_selecionadas.get(produto_id)

        if produto_troca:
            # Linha com original -> novo
            linha = ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "Devolução → Troca",
                            size=11,
                            weight=ft.FontWeight.BOLD,
                            color="#636E72",
                        ),
                        ft.Row(
                            [
                                # Original (esquerda)
                                ft.Container(
                                    content=ft.Column(
                                        [
                                            ft.Icon(
                                                ft.Icons.ARROW_BACK,
                                                color=DANGER_COLOR,
                                                size=16,
                                            ),
                                            ft.Text(
                                                produto_original["nome"],
                                                size=11,
                                                weight=ft.FontWeight.BOLD,
                                                color=TEXT_COLOR,
                                            ),
                                            ft.Text(
                                                f"Qtd: {produto_original['quantidade']}",
                                                size=10,
                                                color="#636E72",
                                            ),
                                        ],
                                        spacing=4,
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                    padding=ft.padding.all(10),
                                    bgcolor=f"{DANGER_COLOR}20",
                                    border_radius=6,
                                    expand=True,
                                ),
                                # Seta
                                ft.Icon(
                                    ft.Icons.ARROW_FORWARD, color=PRIMARY_COLOR, size=20
                                ),
                                # Novo (direita)
                                ft.Container(
                                    content=ft.Column(
                                        [
                                            ft.Icon(
                                                ft.Icons.ARROW_FORWARD,
                                                color=SUCCESS_COLOR,
                                                size=16,
                                            ),
                                            ft.Text(
                                                produto_troca["nome"],
                                                size=11,
                                                weight=ft.FontWeight.BOLD,
                                                color=TEXT_COLOR,
                                            ),
                                            ft.Text(
                                                f"R$ {produto_troca['preco']:.2f}",
                                                size=10,
                                                color=SUCCESS_COLOR,
                                            ),
                                        ],
                                        spacing=4,
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                    padding=ft.padding.all(10),
                                    bgcolor=f"{SUCCESS_COLOR}20",
                                    border_radius=6,
                                    expand=True,
                                ),
                            ],
                            spacing=10,
                            expand=True,
                        ),
                    ],
                    spacing=8,
                ),
                padding=ft.padding.all(12),
                border=ft.border.all(1, "#DFE6E9"),
                border_radius=8,
            )
            comparacao_column.controls.append(linha)

    # Modal de confirmação
    def on_confirmar_click(e):
        """Confirma a troca e fecha o modal"""
        print("[DEVOLVER TROCAR] Confirmando troca...")
        callback_confirmar(trocas_selecionadas)

        # Fechar modal
        if hasattr(page, "_troca_modal_ref") and page._troca_modal_ref:
            page._troca_modal_ref.open = False
            page.update()

    def on_cancelar_click(e):
        """Cancela a troca"""
        print("[DEVOLVER TROCAR] Cancelando troca...")
        if hasattr(page, "_troca_modal_ref") and page._troca_modal_ref:
            page._troca_modal_ref.open = False
            page.update()

    modal_content = ft.Column(
        [
            ft.Row(
                [
                    ft.Text(
                        "Confirmar Troca",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_COLOR,
                    ),
                    ft.Container(expand=True),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Divider(height=10, color="#DFE6E9"),
            ft.Text(
                "Revise os produtos devolvidos e os novos produtos selecionados:",
                size=12,
                color="#636E72",
            ),
            ft.Container(
                content=comparacao_column,
                height=300,
                border_radius=8,
                border=ft.border.all(1, "#DFE6E9"),
                padding=ft.padding.all(8),
            ),
            ft.Divider(height=10, color="#DFE6E9"),
            ft.Row(
                [
                    ft.ElevatedButton(
                        text="❌ Cancelar",
                        width=150,
                        height=45,
                        on_click=on_cancelar_click,
                        style=ft.ButtonStyle(
                            bgcolor=DANGER_COLOR,
                            color=ft.Colors.WHITE,
                        ),
                    ),
                    ft.Container(expand=True),
                    ft.ElevatedButton(
                        text="✅ Confirmar Troca",
                        width=200,
                        height=45,
                        on_click=on_confirmar_click,
                        style=ft.ButtonStyle(
                            bgcolor=SUCCESS_COLOR,
                            color=ft.Colors.WHITE,
                        ),
                    ),
                ],
                spacing=10,
            ),
        ],
        spacing=12,
    )

    # Criar diálogo
    dialog = ft.AlertDialog(
        modal=True,
        title_padding=20,
        content_padding=20,
        inset_padding=20,
        content=ft.Container(
            content=modal_content,
            width=700,
            height=600,
        ),
    )

    # Armazenar referência na página
    page._troca_modal_ref = dialog

    # Adicionar ao overlay
    if dialog not in page.overlay:
        page.overlay.append(dialog)

    # Abrir
    dialog.open = True
    page.update()
    print("[DEVOLVER TROCAR] Modal de confirmação aberto")


def criar_modal_devolver_trocar(
    page: ft.Page, pdv_core, usuario_responsavel: str, callback_nova_venda
):
    """
    Cria modal para devolver e trocar produtos

    Args:
        page: Página Flet
        pdv_core: Core da aplicação
        usuario_responsavel: Username do caixa
        callback_nova_venda: Callback para iniciar nova venda

    Returns:
        Função que abre o modal existente
    """

    # Usar chave única para cada página/usuário
    cache_key = f"{id(page)}_{usuario_responsavel}"

    # Se modal já existe no cache, retornar função que abre ele
    if cache_key in _modais_cache:
        return _modais_cache[cache_key]["show_modal"]

    # Referências reutilizáveis
    dialog_ref = ft.Ref[ft.AlertDialog]()
    vendas_column = ft.Column(spacing=12, scroll="auto")
    produtos_troca_column = ft.Column(spacing=12, scroll="auto")

    # Estado para rastrear a venda selecionada
    estado = {"venda_selecionada": None, "produtos_trocados": {}}

    def criar_campo_troca(produto_original):
        """Cria um campo de troca para um produto devolvido"""
        campo_barras = ft.TextField(
            label=f"Código de barras para trocar por: {produto_original['nome']}",
            hint_text="Digite o código de barras",
            width=400,
            height=50,
            border_radius=8,
        )

        resultado = ft.Container(height=0)  # Inicialmente vazio

        def on_barras_submit(e):
            """Busca o produto quando Enter é pressionado"""
            print(
                f"[DEVOLVER TROCAR] Enter pressionado com valor: '{campo_barras.value}'"
            )

            if len(campo_barras.value) >= 1:
                produto = buscar_produto_por_barras(
                    pdv_core, campo_barras.value.strip()
                )

                if produto:
                    print(f"[DEVOLVER TROCAR] Produto encontrado: {produto['nome']}")
                    estado["produtos_trocados"][produto_original["id"]] = produto

                    # Mostrar resultado
                    resultado.content = ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.CHECK_CIRCLE, color=SUCCESS_COLOR, size=20
                                ),
                                ft.Column(
                                    [
                                        ft.Text(
                                            produto["nome"],
                                            size=12,
                                            weight=ft.FontWeight.BOLD,
                                            color=TEXT_COLOR,
                                        ),
                                        ft.Text(
                                            f"R$ {produto['preco']:.2f} | Estoque: {produto['estoque']}",
                                            size=11,
                                            color="#636E72",
                                        ),
                                    ],
                                    spacing=2,
                                ),
                            ],
                            spacing=10,
                        ),
                        padding=ft.padding.all(10),
                        bgcolor=f"{SUCCESS_COLOR}20",
                        border_radius=8,
                    )
                    resultado.height = 60
                    print("[DEVOLVER TROCAR] Resultado do produto exibido, altura: 60")
                else:
                    print(
                        f"[DEVOLVER TROCAR] Produto NÃO encontrado para barras: {campo_barras.value}"
                    )
                    resultado.content = ft.Text(
                        "❌ Produto não encontrado",
                        color=DANGER_COLOR,
                        size=11,
                    )
                    resultado.height = 25
                    estado["produtos_trocados"].pop(produto_original["id"], None)

                page.update()
            else:
                print("[DEVOLVER TROCAR] Campo vazio, ignorando")

        campo_barras.on_submit = on_barras_submit

        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Text(
                            f"🔄 {produto_original['nome']} (Qtd: {produto_original['quantidade']})",
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_COLOR,
                        ),
                        padding=ft.padding.all(10),
                        bgcolor=CARD_BG,
                        border_radius=8,
                    ),
                    campo_barras,
                    resultado,
                ],
                spacing=8,
            ),
            padding=ft.padding.all(10),
            border=ft.border.all(1, "#DFE6E9"),
            border_radius=8,
        )

    def atualizar_lista_vendas():
        """Atualiza a lista de vendas exibidas no modal"""
        vendas_column.controls.clear()
        estado["venda_selecionada"] = None

        # Buscar vendas do caixa
        vendas = buscar_vendas_do_caixa(pdv_core, usuario_responsavel, limite=20)

        if not vendas:
            vendas_column.controls.append(
                ft.Text(
                    "Nenhuma venda encontrada para devolver.",
                    color=DANGER_COLOR,
                    size=14,
                )
            )
            return

        for venda in vendas:

            def on_select_venda(venda_data):
                def handler(e):
                    print(f"[DEVOLVER TROCAR] Selecionada venda #{venda_data['id']}")

                    # Processar devolução
                    sucesso, mensagem, carrinho = processar_devolucao_e_trocar(
                        pdv_core, venda_data["id"], usuario_responsavel
                    )

                    if sucesso:
                        estado["venda_selecionada"] = venda_data["id"]
                        estado["produtos_trocados"] = {}

                        # Limpar e popular com produtos para trocar
                        produtos_troca_column.controls.clear()

                        for item in carrinho:
                            campo_troca = criar_campo_troca(
                                {
                                    "id": item["produto_id"],
                                    "nome": item["nome"],
                                    "quantidade": item["qtd"],
                                    "preco": item["preco"],
                                }
                            )
                            produtos_troca_column.controls.append(campo_troca)

                        # Mostrar painel de trocas
                        page.update()
                        print(
                            f"[DEVOLVER TROCAR] {len(carrinho)} produtos prontos para trocar"
                        )
                    else:
                        snackbar = ft.SnackBar(
                            content=ft.Text(mensagem, color="white"),
                            bgcolor=DANGER_COLOR,
                        )
                        page.overlay.append(snackbar)
                        snackbar.open = True
                        page.update()

                return handler

            venda_card = ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text(
                                            f"Venda #{venda['id']}",
                                            size=14,
                                            weight=ft.FontWeight.BOLD,
                                            color=TEXT_COLOR,
                                        ),
                                        ft.Text(
                                            venda["data"],
                                            size=12,
                                            color="#636E72",
                                        ),
                                    ],
                                    spacing=2,
                                ),
                                ft.Container(expand=True),
                                ft.Column(
                                    [
                                        ft.Text(
                                            f"R$ {venda['total']:.2f}",
                                            size=14,
                                            weight=ft.FontWeight.BOLD,
                                            color=PRIMARY_COLOR,
                                        ),
                                        ft.Text(
                                            venda["pagamento"],
                                            size=11,
                                            color="#636E72",
                                        ),
                                    ],
                                    spacing=2,
                                    horizontal_alignment=ft.CrossAxisAlignment.END,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Text(
                            f"Produtos: {venda['resumo']}",
                            size=11,
                            color="#636E72",
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    spacing=4,
                ),
                padding=ft.padding.all(12),
                bgcolor=CARD_BG,
                border_radius=8,
                border=ft.border.all(1, "#DFE6E9"),
                data=venda,
            )

            # Envolver em GestureDetector para capturar cliques
            venda_row = ft.GestureDetector(
                content=venda_card,
                on_tap=on_select_venda(venda),
            )
            vendas_column.controls.append(venda_row)

    # Criar conteúdo do modal (UMA ÚNICA VEZ)
    # Painel esquerdo: Lista de vendas
    painel_vendas = ft.Column(
        [
            ft.Text(
                "Selecionar Venda",
                size=14,
                weight=ft.FontWeight.BOLD,
                color=TEXT_COLOR,
            ),
            ft.Container(
                content=vendas_column,
                height=300,
                border_radius=8,
                border=ft.border.all(1, "#DFE6E9"),
                padding=ft.padding.all(8),
                expand=True,
            ),
        ],
        spacing=8,
        expand=False,
        width=350,
    )

    # Painel direito: Produtos para trocar
    def on_confirmar_trocas_click(e):
        """Abre o modal de confirmação"""
        if estado["venda_selecionada"] and len(estado["produtos_trocados"]) > 0:
            print(
                f"[DEVOLVER TROCAR] Abrindo confirmação com {len(estado['produtos_trocados'])} trocas"
            )

            # Buscar carrinho original
            carrinho_original = []
            for item in produtos_troca_column.controls:
                # Extrair dados do item (container com info do produto)
                if hasattr(item, "content") and hasattr(item.content, "controls"):
                    # O primeiro control é o Container com nome e quantidade
                    primeira_linha = item.content.controls[0]
                    if hasattr(primeira_linha, "content"):
                        texto = primeira_linha.content.value
                        # Parse "🔄 Nome (Qtd: X)"
                        if "Qtd:" in texto:
                            nome = texto.split("(Qtd:")[0].replace("🔄 ", "").strip()
                            qtd_str = texto.split("Qtd:")[1].replace(")", "").strip()
                            # Encontrar o produto_id correspondente nas trocas selecionadas
                            for prod_id in estado["produtos_trocados"]:
                                carrinho_original.append(
                                    {
                                        "id": prod_id,
                                        "nome": nome,
                                        "quantidade": int(qtd_str),
                                    }
                                )
                                break

            # Callback para confirmar
            def callback_confirmar(trocas):
                print("[DEVOLVER TROCAR] Troca confirmada!")
                # Fechar primeiro modal
                if dialog_ref.current:
                    dialog_ref.current.open = False
                page.update()

                # Mostrar sucesso
                snackbar = ft.SnackBar(
                    content=ft.Text("✅ Troca realizada com sucesso!", color="white"),
                    bgcolor=SUCCESS_COLOR,
                    duration=3000,
                )
                page.overlay.append(snackbar)
                snackbar.open = True
                page.update()

            # Abrir modal de confirmação
            criar_modal_confirmacao_troca(
                page, carrinho_original, estado["produtos_trocados"], callback_confirmar
            )
        else:
            # Mostrar erro
            snackbar = ft.SnackBar(
                content=ft.Text(
                    "❌ Selecione todos os produtos para trocar!", color="white"
                ),
                bgcolor=DANGER_COLOR,
                duration=3000,
            )
            page.overlay.append(snackbar)
            snackbar.open = True
            page.update()

    painel_trocas = ft.Column(
        [
            ft.Text(
                "Produtos para Trocar",
                size=14,
                weight=ft.FontWeight.BOLD,
                color=TEXT_COLOR,
            ),
            ft.Container(
                content=produtos_troca_column,
                height=300,
                border_radius=8,
                border=ft.border.all(1, "#DFE6E9"),
                padding=ft.padding.all(8),
                expand=True,
            ),
            ft.ElevatedButton(
                text="✅ Confirmar Trocas",
                width=250,
                height=45,
                on_click=on_confirmar_trocas_click,
                style=ft.ButtonStyle(
                    bgcolor=SUCCESS_COLOR,
                    color=ft.Colors.WHITE,
                ),
            ),
        ],
        spacing=8,
        expand=True,
    )

    # Layout em duas colunas
    modal_content = ft.Column(
        [
            ft.Row(
                [
                    ft.Text(
                        "Devolver & Trocar Produtos",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_COLOR,
                    ),
                    ft.Container(expand=True),
                    ft.IconButton(
                        ft.Icons.CLOSE,
                        icon_color=TEXT_COLOR,
                        on_click=lambda e: _close_modal(dialog_ref, page),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Divider(height=10, color="#DFE6E9"),
            ft.Row(
                [
                    painel_vendas,
                    ft.VerticalDivider(width=1, color="#DFE6E9"),
                    painel_trocas,
                ],
                spacing=10,
                expand=True,
            ),
        ],
        spacing=12,
    )

    # Criar dialog (UMA ÚNICA VEZ)
    dialog_ref.current = ft.AlertDialog(
        modal=True,
        title_padding=20,
        content_padding=20,
        inset_padding=20,
        content=ft.Container(
            content=modal_content,
            width=900,
            height=500,
        ),
    )

    def show_modal():
        """Abre o modal (reutilizável)"""
        print("[DEVOLVER TROCAR] Abrindo modal de devoluções...")

        # Atualizar lista de vendas
        atualizar_lista_vendas()

        # Limpar trocas anteriores
        produtos_troca_column.controls.clear()
        estado["venda_selecionada"] = None

        # Usar page.overlay para o AlertDialog
        # Se o dialog já está no overlay, apenas abrir
        if dialog_ref.current not in page.overlay:
            page.overlay.append(dialog_ref.current)
            print("[DEVOLVER TROCAR] Dialog adicionado ao overlay")

        # Abrir dialog
        if dialog_ref.current:
            dialog_ref.current.open = True
            page.update()
            print("[DEVOLVER TROCAR] Modal aberto com sucesso")
        else:
            print("[DEVOLVER TROCAR] ❌ Dialog não foi criado corretamente")

    # Armazenar no cache
    _modais_cache[cache_key] = {"show_modal": show_modal, "dialog_ref": dialog_ref}

    return show_modal


def _close_modal(dialog_ref, page):
    """Fecha o modal"""
    if dialog_ref.current:
        dialog_ref.current.open = False
        page.update()
        print("[DEVOLVER TROCAR] Modal fechado")


def criar_botao_devolver_trocar(
    page: ft.Page,
    pdv_core,
    usuario_responsavel: str,
    callback_nova_venda,
    colors: dict = None,
):
    """
    Cria botão "Devolver & Trocar" para a tela do Caixa

    Args:
        page: Página Flet
        pdv_core: Core da aplicação
        usuario_responsavel: Username do caixa
        callback_nova_venda: Callback para iniciar nova venda
        colors: Dicionário customizado de cores

    Returns:
        Botão ft.ElevatedButton
    """
    if colors is None:
        colors = {
            "warning": "#FDCB6E",
            "text": "#2D3748",
            "text_light": "#FFF",
        }

    modal_function = criar_modal_devolver_trocar(
        page, pdv_core, usuario_responsavel, callback_nova_venda
    )

    def on_button_click(e):
        """Handler para clique no botão Devolver & Trocar"""
        try:
            print("[DEVOLVER TROCAR] Botão clicado")
            modal_function()
            print("[DEVOLVER TROCAR] Modal chamado com sucesso")
        except Exception as ex:
            print(f"[DEVOLVER TROCAR] ❌ Erro ao abrir modal: {ex}")
            import traceback

            traceback.print_exc()

    botao = ft.ElevatedButton(
        text="↩️  Devolver & Trocar",
        icon=ft.Icons.UNDO,
        width=200,
        height=50,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.WHITE,
            color=colors["text_dark"],
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=15,
        ),
        on_click=on_button_click,
    )

    return botao
