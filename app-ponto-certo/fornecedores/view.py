import flet as ft
from models.db_models import Fornecedor
from typing import Optional, Dict, Any, List, TypedDict
from functools import lru_cache
import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


COLORS = {
    "background": "#F5F5F5",
    "primary": "#007BFF",
    "green": "#28A745",
    "red": "#DC3545",
    "orange": "#FFC107",
    "text": "#212121",
    "text_muted": "#757575",
}

MEIOS_PAGAMENTO = ["Débito", "Dinheiro", "Crédito", "Pix"]
STATUS_OPCOES = [("ativo", "Ativo"), ("inativo", "Inativo")]


class FornecedorData(TypedDict, total=False):
    nome_razao_social: str
    cnpj_cpf: Optional[str]
    contato: Optional[str]
    condicao_pagamento: Optional[str]
    prazo_entrega_medio: Optional[str]
    status: str


def show_snackbar(page: ft.Page, message: str, color: str):
    page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor=color)
    page.snack_bar.open = True
    page.update()


def validar_cnpj_cpf(value: str) -> tuple[bool, str]:
    if not value:
        return True, ""

    cleaned = "".join(filter(str.isdigit, value))

    if len(cleaned) == 11:
        return True, cleaned
    elif len(cleaned) == 14:
        return True, cleaned

    return False, value


def formatar_cnpj_cpf(value: str) -> str:
    if not value:
        return ""

    digits = "".join(filter(str.isdigit, value))

    if len(digits) <= 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    else:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


def create_fornecedores_view(
    page: ft.Page, pdv_core: Any, handle_back: callable
) -> ft.View:
    assert isinstance(page, ft.Page), "page deve ser instância de ft.Page"

    loading_ref = ft.Ref[ft.ProgressRing]()
    fornecedores_dt_ref = ft.Ref[ft.DataTable]()
    fornecedores_list_ref = ft.Ref()
    form_title_ref = ft.Ref[ft.Text]()
    selected_id_ref = ft.Ref[ft.TextField]()
    nome_ref = ft.Ref[ft.TextField]()
    cnpj_cpf_ref = ft.Ref[ft.TextField]()
    contato_ref = ft.Ref[ft.TextField]()
    prazo_entrega_ref = ft.Ref[ft.TextField]()
    status_ref = ft.Ref[ft.Dropdown]()
    search_ref = ft.Ref[ft.TextField]()
    detalhes_container_ref = ft.Ref[ft.Container]()
    highlight_id_ref = ft.Ref()

    checkboxes_ref: Dict[str, ft.Ref[ft.Checkbox]] = {
        meio: ft.Ref[ft.Checkbox]() for meio in MEIOS_PAGAMENTO
    }

    @lru_cache(maxsize=128)
    def get_produtos_fornecedor(fornecedor_id: int) -> List[Any]:
        try:
            pdv_core_local = page.app_data.get("pdv_core")
            if not pdv_core_local:
                logger.warning("pdv_core não disponível em page.app_data")
                return []

            if hasattr(pdv_core_local, "get_produtos_by_fornecedor"):
                produtos = pdv_core_local.get_produtos_by_fornecedor(fornecedor_id)
                logger.info(
                    f"get_produtos_by_fornecedor retornou {len(produtos)} produtos"
                )
                return produtos
            else:
                logger.warning(
                    "Método get_produtos_by_fornecedor não disponível, usando fallback"
                )

                if hasattr(pdv_core_local, "get_all_produtos"):
                    todos_produtos = pdv_core_local.get_all_produtos()
                    produtos = [
                        p
                        for p in todos_produtos
                        if getattr(p, "fornecedor_id", None) == fornecedor_id
                    ]
                    logger.info(f"Fallback retornou {len(produtos)} produtos")
                    return produtos

        except Exception as e:
            logger.error(
                f"Erro ao buscar produtos do fornecedor {fornecedor_id}: {e}",
                exc_info=True,
            )

        return []

    def load_fornecedores_table(search_term: str = ""):
        logger.info(f"Carregando lista de fornecedores (busca: '{search_term}')")

        if not fornecedores_list_ref.current:
            logger.warning("Lista ainda não montada, agendando recarregamento...")
            page.run_task(
                lambda: (page.sleep(100), load_fornecedores_table(search_term))
            )
            return

        try:
            loading_ref.current.visible = True
            page.update()

            fornecedores = pdv_core.get_all_fornecedores()
            if search_term:
                fornecedores = [
                    f
                    for f in fornecedores
                    if search_term.lower()
                    in (
                        (getattr(f, "nome_razao_social", "") or "").lower()
                        + (getattr(f, "nome", "") or "").lower()
                    )
                ]

            items: List[ft.Control] = []
            for f in fornecedores:
                produtos_fornecedor = get_produtos_fornecedor(f.id)
                produto_principal = "-"
                if produtos_fornecedor:
                    produto_principal = getattr(produtos_fornecedor[0], "nome", "-")
                    if len(produtos_fornecedor) > 1:
                        produto_principal += f" (+{len(produtos_fornecedor) - 1})"

                nome = getattr(f, "nome_razao_social", getattr(f, "nome", "N/A"))
                contato = getattr(f, "contato", "-")
                status_val = getattr(f, "status", "ativo")
                status_color = (
                    COLORS["green"] if status_val == "ativo" else COLORS["red"]
                )

                actions = ft.Row(
                    [
                        ft.IconButton(
                            icon=ft.icons.EDIT,
                            tooltip="Editar",
                            data=getattr(f, "id", None),
                            on_click=preencher_formulario_edicao,
                            icon_color=COLORS["primary"],
                        ),
                        ft.IconButton(
                            icon=ft.icons.DELETE,
                            tooltip="Excluir",
                            data=getattr(f, "id", None),
                            on_click=excluir_fornecedor,
                            icon_color=COLORS["red"],
                        ),
                    ],
                    spacing=0,
                )

                card = ft.Card(
                    elevation=1,
                    content=ft.Container(
                        content=ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text(
                                            nome,
                                            weight=ft.FontWeight.BOLD,
                                            color=COLORS["text"],
                                        ),
                                        ft.Text(
                                            str(contato),
                                            size=12,
                                            color=COLORS["text_muted"],
                                        ),
                                    ],
                                    expand=True,
                                ),
                                ft.Column(
                                    [
                                        ft.Text(
                                            str(produto_principal),
                                            size=12,
                                            color=COLORS["text_muted"],
                                        ),
                                        ft.Text(
                                            str(status_val).title(),
                                            size=12,
                                            color=status_color,
                                        ),
                                    ],
                                    width=220,
                                    horizontal_alignment=ft.CrossAxisAlignment.END,
                                ),
                                actions,
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=10,
                    ),
                )

                fid = getattr(f, "id", None)
                wrap = ft.GestureDetector(
                    content=card,
                    on_tap=lambda e, _fid=fid: preencher_formulario_edicao(
                        ft.ControlEvent(e.control, data=_fid)
                    ),
                )
                items.append(wrap)

            fornecedores_list_ref.current.controls = items
            fornecedores_list_ref.current.update()

            if not fornecedores:
                show_snackbar(page, "Nenhum fornecedor cadastrado.", COLORS["orange"])

            logger.info(f"{len(fornecedores)} fornecedores carregados")

        except Exception as e:
            logger.exception("Erro ao carregar fornecedores")
            show_snackbar(page, f"Erro ao carregar fornecedores: {e}", COLORS["red"])
        finally:
            loading_ref.current.visible = False
            page.update()

    def clear_highlight():
        try:
            highlight_id_ref.current = None
            load_fornecedores_table()
        except Exception:
            pass

    def excluir_fornecedor(e: ft.ControlEvent):
        fornecedor_id = e.control.data
        logger.info(f"excluir_fornecedor chamado com data: {fornecedor_id}")

        fornecedor = None
        try:
            fornecedor = pdv_core.get_fornecedor_by_id(fornecedor_id)
        except Exception:
            fornecedor = None

        if not fornecedor:
            show_snackbar(page, "Fornecedor não encontrado.", COLORS["red"])
            return

        produtos = get_produtos_fornecedor(fornecedor.id)
        if produtos:
            show_snackbar(page, "Fornecedor tem produtos vinculados!", COLORS["red"])
            return

        def confirmar_exclusao(e: ft.ControlEvent):
            if e.control.text == "Sim":
                try:
                    sucesso, msg = pdv_core.excluir_fornecedor(fornecedor.id)
                    if sucesso:
                        logger.info(f"Fornecedor {fornecedor.id} excluído com sucesso")
                        show_snackbar(
                            page, "Fornecedor excluído com sucesso!", COLORS["green"]
                        )
                        load_fornecedores_table()
                    else:
                        if "FOREIGN KEY" in msg or "foreign key" in msg:
                            show_snackbar(
                                page,
                                "Não é possível excluir: fornecedor tem dados vinculados!",
                                COLORS["red"],
                            )
                        else:
                            show_snackbar(page, f"Erro: {msg}", COLORS["red"])
                except Exception as error:
                    logger.error(
                        f"Erro ao excluir fornecedor {fornecedor.id}: {error}",
                        exc_info=True,
                    )
                    show_snackbar(page, "Erro ao excluir fornecedor", COLORS["red"])
            page.close(dialog)

        dialog = ft.AlertDialog(
            title=ft.Text("Confirmar Exclusão"),
            content=ft.Text(
                f"Excluir '{getattr(fornecedor, 'nome_razao_social', getattr(fornecedor, 'nome', ''))}'?"
            ),
            actions=[
                ft.TextButton("Sim", on_click=confirmar_exclusao),
                ft.TextButton("Não", on_click=lambda e: page.close(dialog)),
            ],
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def preencher_formulario_edicao(e: ft.ControlEvent):
        fornecedor_id = e.control.data
        logger.info(f"preencher_formulario_edicao chamado com data: {fornecedor_id}")
        fornecedor = None
        try:
            fornecedor = pdv_core.get_fornecedor_by_id(fornecedor_id)
        except Exception:
            fornecedor = None

        if not fornecedor:
            show_snackbar(page, "Fornecedor não encontrado para edição.", COLORS["red"])
            return

        logger.info(f"Preenchendo formulário para fornecedor ID: {fornecedor.id}")

        meios_aceitos = getattr(fornecedor, "condicao_pagamento", "") or ""
        meios_aceitos = meios_aceitos.split(", ") if meios_aceitos else []

        nome = getattr(fornecedor, "nome_razao_social", getattr(fornecedor, "nome", ""))

        form_title_ref.current.value = f"Editando: {nome}"
        selected_id_ref.current.value = str(fornecedor.id)
        nome_ref.current.value = nome
        cnpj_cpf_ref.current.value = formatar_cnpj_cpf(
            getattr(fornecedor, "cnpj_cpf", "") or ""
        )
        contato_ref.current.value = getattr(fornecedor, "contato", "") or ""

        for key, ref in checkboxes_ref.items():
            if ref.current:
                ref.current.value = key in meios_aceitos

        prazo_entrega_ref.current.value = (
            getattr(fornecedor, "prazo_entrega_medio", "") or ""
        )
        status_ref.current.value = getattr(fornecedor, "status", "ativo")

        detalhes_container_ref.current.content = create_detalhes_fornecedor(fornecedor)
        page.update()

    def limpar_formulario(e: Optional[ft.ControlEvent] = None):
        form_title_ref.current.value = "Cadastrar Novo Fornecedor"
        selected_id_ref.current.value = ""
        nome_ref.current.value = ""
        cnpj_cpf_ref.current.value = ""
        contato_ref.current.value = ""

        for ref in checkboxes_ref.values():
            if ref.current:
                ref.current.value = False

        prazo_entrega_ref.current.value = ""
        status_ref.current.value = "ativo"
        detalhes_container_ref.current.content = create_detalhes_fornecedor(None)
        page.update()

    def salvar_fornecedor(e: ft.ControlEvent):
        if not nome_ref.current.value.strip():
            show_snackbar(page, "Nome/Razão Social é obrigatório!", COLORS["red"])
            nome_ref.current.focus()
            return

        cnpj_cpf_raw = cnpj_cpf_ref.current.value or ""
        is_valid, cleaned_cnpj_cpf = validar_cnpj_cpf(cnpj_cpf_raw)
        if cnpj_cpf_raw and not is_valid:
            show_snackbar(page, "CNPJ/CPF inválido!", COLORS["red"])
            cnpj_cpf_ref.current.focus()
            return

        meios_selecionados = [
            key
            for key, ref in checkboxes_ref.items()
            if ref.current and ref.current.value
        ]

        dados: FornecedorData = {
            "nome_razao_social": nome_ref.current.value.strip(),
            "cnpj_cpf": cleaned_cnpj_cpf or None,
            "contato": contato_ref.current.value.strip() or None,
            "condicao_pagamento": ", ".join(meios_selecionados) or None,
            "prazo_entrega_medio": prazo_entrega_ref.current.value.strip() or None,
            "status": status_ref.current.value,
        }

        fornecedor_id_str = selected_id_ref.current.value
        fornecedor_id = int(fornecedor_id_str) if fornecedor_id_str else None

        try:
            logger.info(f"Salvando fornecedor: {dados}")
            sucesso, msg = pdv_core.cadastrar_ou_atualizar_fornecedor(
                dados, fornecedor_id
            )

            if sucesso:
                logger.info(
                    f"Fornecedor {'atualizado' if fornecedor_id else 'criado'} com sucesso!"
                )
                show_snackbar(
                    page,
                    f"Fornecedor {'atualizado' if fornecedor_id else 'criado'} com sucesso!",
                    COLORS["green"],
                )
                limpar_formulario()
                try:
                    if search_ref.current:
                        search_ref.current.value = ""
                        search_ref.current.update()
                except Exception:
                    pass

                load_fornecedores_table()
                try:
                    fornecedores_all = pdv_core.get_all_fornecedores()
                    candidato = None
                    for fo in sorted(
                        fornecedores_all,
                        key=lambda x: getattr(x, "id", 0),
                        reverse=True,
                    ):
                        if getattr(
                            fo, "nome_razao_social", getattr(fo, "nome", "")
                        ) == dados.get("nome_razao_social"):
                            candidato = fo
                            break
                    if candidato:
                        highlight_id_ref.current = getattr(candidato, "id", None)
                        load_fornecedores_table()
                        try:
                            page.run_task(lambda: (page.sleep(3000), clear_highlight()))
                        except Exception:
                            pass
                except Exception:
                    pass
            else:
                logger.error(f"Erro ao salvar fornecedor: {msg}")
                show_snackbar(page, f"Erro: {msg}", COLORS["red"])

        except Exception as error:
            logger.error(f"Exceção ao salvar fornecedor: {error}", exc_info=True)
            show_snackbar(page, f"Erro inesperado: {error}", COLORS["red"])
        page.update()

    def create_detalhes_fornecedor(fornecedor: Optional[Fornecedor]) -> ft.Column:
        produto_list_controls = []
        historico_controls = []

        if fornecedor:
            try:
                produtos_fornecedor = get_produtos_fornecedor(fornecedor.id)

                if produtos_fornecedor:
                    for prod in produtos_fornecedor[:5]:
                        nome = getattr(prod, "nome", "Produto sem nome")
                        estoque = getattr(prod, "estoque", 0)
                        produto_list_controls.append(
                            ft.Text(f"• {nome} (Estoque: {estoque})", size=13)
                        )
                else:
                    produto_list_controls.append(
                        ft.Text(
                            "Nenhum produto vinculado.",
                            italic=True,
                            color=COLORS["text_muted"],
                            size=13,
                        )
                    )

                if hasattr(pdv_core, "get_historico_compras_fornecedor"):
                    historico = pdv_core.get_historico_compras_fornecedor(fornecedor.id)
                    if historico:
                        for hist in historico[:3]:
                            data = getattr(hist, "data", "N/A")
                            valor = getattr(hist, "valor_total", 0)
                            historico_controls.extend(
                                [
                                    ft.Text(
                                        f"Data: {data}", size=12, color=COLORS["text"]
                                    ),
                                    ft.Text(
                                        f"Valor: R$ {float(valor):.2f}",
                                        size=12,
                                        weight="bold",
                                    ),
                                    ft.Divider(height=2, color=ft.colors.GREY_300),
                                ]
                            )
                    else:
                        historico_controls.append(
                            ft.Text(
                                "Nenhum histórico de compras disponível.",
                                italic=True,
                                color=COLORS["text_muted"],
                                size=13,
                            )
                        )
                else:
                    historico_controls.append(
                        ft.Text(
                            "Histórico não disponível.",
                            italic=True,
                            color=COLORS["text_muted"],
                            size=13,
                        )
                    )

            except Exception as e:
                logger.error(
                    f"Erro ao buscar detalhes do fornecedor {fornecedor.id}: {e}",
                    exc_info=True,
                )
                produto_list_controls.append(
                    ft.Text(
                        "Erro ao carregar produtos.",
                        italic=True,
                        color=COLORS["red"],
                        size=13,
                    )
                )
        else:
            produto_list_controls.append(
                ft.Text(
                    "Selecione um fornecedor para ver produtos.",
                    italic=True,
                    color=COLORS["text_muted"],
                    size=13,
                )
            )
            historico_controls.append(
                ft.Text(
                    "Selecione um fornecedor para ver histórico.",
                    italic=True,
                    color=COLORS["text_muted"],
                    size=13,
                )
            )

        return ft.Column(
            [
                ft.Card(
                    elevation=2,
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "Produtos Vinculados",
                                    style=ft.TextThemeStyle.TITLE_MEDIUM,
                                    weight=ft.FontWeight.BOLD,
                                    color=COLORS["text"],
                                ),
                                ft.Container(
                                    content=ft.ListView(
                                        controls=produto_list_controls, spacing=5
                                    ),
                                    height=150,
                                    border=ft.border.all(1, ft.colors.GREY_300),
                                    border_radius=5,
                                    padding=10,
                                ),
                            ],
                            spacing=10,
                        ),
                        padding=15,
                    ),
                ),
                ft.Card(
                    elevation=2,
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "Histórico de Compras",
                                    style=ft.TextThemeStyle.TITLE_MEDIUM,
                                    weight=ft.FontWeight.BOLD,
                                    color=COLORS["text"],
                                ),
                                ft.Container(
                                    content=ft.Column(historico_controls, spacing=5),
                                    height=120,
                                    border=ft.border.all(1, ft.colors.GREY_300),
                                    border_radius=5,
                                    padding=10,
                                ),
                            ],
                            spacing=10,
                        ),
                        padding=15,
                    ),
                ),
            ],
            spacing=10,
        )

    def on_cnpj_change(e: ft.ControlEvent):
        value = e.control.value
        e.control.value = formatar_cnpj_cpf(value)
        page.update()

    def filtrar_fornecedores(e: ft.ControlEvent):
        try:
            termo = search_ref.current.value.lower() if search_ref.current else ""
            logger.info(f"filtrar_fornecedores chamado com termo: '{termo}'")
            load_fornecedores_table(termo)
        except Exception as ex:
            logger.error(f"Erro em filtrar_fornecedores: {ex}", exc_info=True)

    def handle_refresh(e: ft.ControlEvent):
        logger.info("Botão de atualização clicado - limpando busca e recarregando")
        if search_ref.current:
            search_ref.current.value = ""
        load_fornecedores_table("")
        show_snackbar(page, "Lista atualizada!", COLORS["green"])

    app_bar = ft.AppBar(
        leading=ft.IconButton(
            icon=ft.icons.ARROW_BACK,
            on_click=handle_back,
            tooltip="Voltar ao Painel Gerencial",
            icon_color=ft.colors.BLACK,
        ),
        title=ft.Container(
            content=ft.Text(
                "Fornecedores",
                size=24,
                weight=ft.FontWeight.BOLD,
                color=ft.colors.BLACK,
                text_align=ft.TextAlign.CENTER,
            ),
            alignment=ft.alignment.center,
        ),
        center_title=True,
    )

    search_field = ft.TextField(
        ref=search_ref,
        label="Buscar fornecedor...",
        prefix_icon=ft.icons.SEARCH,
        on_change=filtrar_fornecedores,
        on_submit=filtrar_fornecedores,
        border_color=COLORS["primary"],
        disabled=False,
        autofocus=False,
    )

    search_row = ft.Row(
        [
            ft.Container(content=search_field, expand=True),
            ft.IconButton(
                icon=ft.icons.SEARCH,
                tooltip="Focar/Buscar",
                on_click=lambda e: (
                    search_ref.current.focus() if search_ref.current else None,
                    filtrar_fornecedores(e),
                ),
                icon_color=COLORS["primary"],
            ),
            ft.IconButton(
                icon=ft.icons.REFRESH,
                tooltip="Atualizar lista",
                on_click=handle_refresh,
                icon_color=COLORS["primary"],
            ),
        ],
        spacing=5,
        alignment=ft.MainAxisAlignment.START,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    lista_fornecedores = ft.Card(
        elevation=4,
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                "Lista de Fornecedores",
                                style=ft.TextThemeStyle.TITLE_LARGE,
                                weight=ft.FontWeight.BOLD,
                                color=COLORS["text"],
                            ),
                            ft.ProgressRing(
                                ref=loading_ref, visible=False, width=20, height=20
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    search_row,
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.DataTable(
                                    ref=fornecedores_dt_ref,
                                    columns=[
                                        ft.DataColumn(
                                            ft.Text(
                                                "Nome/Razão Social",
                                                weight=ft.FontWeight.BOLD,
                                                color=COLORS["text"],
                                            )
                                        ),
                                        ft.DataColumn(
                                            ft.Text(
                                                "Contato",
                                                weight=ft.FontWeight.BOLD,
                                                color=COLORS["text"],
                                            )
                                        ),
                                        ft.DataColumn(
                                            ft.Text(
                                                "Produto Principal",
                                                weight=ft.FontWeight.BOLD,
                                                color=COLORS["text"],
                                            )
                                        ),
                                        ft.DataColumn(
                                            ft.Text(
                                                "Status",
                                                weight=ft.FontWeight.BOLD,
                                                color=COLORS["text"],
                                            )
                                        ),
                                        ft.DataColumn(
                                            ft.Text(
                                                "Ações",
                                                weight=ft.FontWeight.BOLD,
                                                color=COLORS["text"],
                                            )
                                        ),
                                    ],
                                    rows=[],
                                    column_spacing=15,
                                    data_row_min_height=45,
                                    data_text_style=ft.TextStyle(
                                        size=13, color=COLORS["text"]
                                    ),
                                ),
                            ],
                            scroll=ft.ScrollMode.ADAPTIVE,
                        ),
                        expand=True,
                        height=500,
                    ),
                ],
                expand=True,
                spacing=10,
            ),
            padding=15,
            expand=True,
        ),
    )

    checkboxes_group = ft.Row(
        [
            ft.Checkbox(
                label=meio,
                ref=checkboxes_ref[meio],
                fill_color=COLORS["primary"],
                check_color=ft.colors.WHITE,
            )
            for meio in MEIOS_PAGAMENTO
        ],
        wrap=True,
    )

    form_fornecedor = ft.Card(
        elevation=4,
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        ref=form_title_ref,
                        value="Cadastrar Novo Fornecedor",
                        style=ft.TextThemeStyle.TITLE_MEDIUM,
                        weight=ft.FontWeight.BOLD,
                        color=COLORS["text"],
                    ),
                    ft.TextField(ref=selected_id_ref, visible=False),
                    ft.TextField(
                        ref=nome_ref,
                        label="Nome / Razão Social *",
                        hint_text="Obrigatório",
                        border_color=COLORS["primary"],
                    ),
                    ft.Row(
                        [
                            ft.TextField(
                                ref=cnpj_cpf_ref,
                                label="CNPJ / CPF",
                                expand=True,
                                border_color=COLORS["primary"],
                                on_change=on_cnpj_change,
                            ),
                            ft.TextField(
                                ref=contato_ref,
                                label="Contato (Telefone/Email)",
                                expand=True,
                                border_color=COLORS["primary"],
                            ),
                        ]
                    ),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "Condição de Pagamento (Meios Aceitos)",
                                    weight=ft.FontWeight.BOLD,
                                    size=14,
                                    color=COLORS["text"],
                                ),
                                checkboxes_group,
                            ],
                            spacing=5,
                        ),
                        padding=ft.padding.only(top=10, bottom=10),
                    ),
                    ft.TextField(
                        ref=prazo_entrega_ref,
                        label="Prazo Médio Entrega (Ex: 7 dias úteis)",
                        border_color=COLORS["primary"],
                    ),
                    ft.Dropdown(
                        ref=status_ref,
                        label="Status",
                        value="ativo",
                        options=[
                            ft.dropdown.Option(value, label)
                            for value, label in STATUS_OPCOES
                        ],
                        border_color=COLORS["primary"],
                    ),
                    ft.Row(
                        [
                            ft.FilledButton(
                                "Salvar",
                                icon=ft.icons.SAVE,
                                on_click=salvar_fornecedor,
                                style=ft.ButtonStyle(
                                    bgcolor=COLORS["green"], color=ft.colors.WHITE
                                ),
                            ),
                            ft.OutlinedButton(
                                "Novo / Limpar",
                                icon=ft.icons.ADD_CIRCLE_OUTLINE,
                                on_click=limpar_formulario,
                                style=ft.ButtonStyle(color=COLORS["primary"]),
                            ),
                        ]
                    ),
                ],
                spacing=15,
            ),
            padding=15,
        ),
    )

    detalhes_container = ft.Container(
        ref=detalhes_container_ref,
        content=create_detalhes_fornecedor(None),
        padding=ft.padding.only(top=10),
    )

    view = ft.View(
        "/gerente/fornecedores",
        [
            app_bar,
            ft.Container(
                content=ft.ResponsiveRow(
                    [
                        ft.Column(
                            [lista_fornecedores], col={"md": 12, "lg": 5}, expand=True
                        ),
                        ft.Column(
                            [form_fornecedor, detalhes_container],
                            col={"md": 12, "lg": 7},
                            scroll=ft.ScrollMode.ALWAYS,
                        ),
                    ],
                    expand=True,
                    run_spacing=20,
                ),
                padding=ft.padding.all(15),
                expand=True,
            ),
        ],
        padding=0,
    )

    def on_view_did_mount(e):
        logger.info("View de fornecedores montada")
        page.bgcolor = COLORS["background"]
        page.run_task(
            lambda: (page.sleep(200), load_fornecedores_table(), limpar_formulario())
        )

    view.on_view_did_mount = on_view_did_mount
    return view


__all__ = [
    "FornecedorData",
    "COLORS",
    "MEIOS_PAGAMENTO",
    "STATUS_OPCOES",
    "show_snackbar",
    "validar_cnpj_cpf",
    "formatar_cnpj_cpf",
    "create_fornecedores_view",
]
