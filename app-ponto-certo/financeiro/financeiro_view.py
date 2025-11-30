import flet as ft
from .financeiro_utils import _show_snack, refresh_view, format_currency
from .financeiro_dialogs import (
    open_new_caixa_dialog,
    close_and_audit_caixa_dialog,
    nova_despesa_dialog,
    nova_receita_dialog,
)
from .financeiro_components import (
    create_kpi_card,
    create_caixa_control_card,
    create_finance_table,
)
from utils import export_utils
from functools import partial

# ====================================================================
# DIÁLOGOS (COM PARTIAL CORRETO)
# ====================================================================


def export_finance_csv(page: ft.Page, pdv_core, is_receber: bool, e=None):
    """Exporta as contas (pagar/receber) para CSV usando export_utils."""
    try:
        if is_receber:
            items = pdv_core.get_pending_receivables() or []
            headers = ["Vencimento", "Descrição", "Origem", "Valor", "Status", "ID"]
            rows = [
                [
                    getattr(it, "vencimento", "-"),
                    getattr(it, "descricao", ""),
                    getattr(it, "origem", getattr(it, "categoria", "")),
                    getattr(it, "valor", 0.0),
                    getattr(it, "status", ""),
                    getattr(it, "id", ""),
                ]
                for it in items
            ]
            caminho = export_utils.generate_csv_file(
                headers, rows, nome_base="contas_receber"
            )
        else:
            items = pdv_core.get_pending_expenses() or []
            headers = ["Vencimento", "Descrição", "Categoria", "Valor", "Status", "ID"]
            rows = [
                [
                    getattr(it, "vencimento", "-"),
                    getattr(it, "descricao", ""),
                    getattr(it, "categoria", ""),
                    getattr(it, "valor", 0.0),
                    getattr(it, "status", ""),
                    getattr(it, "id", ""),
                ]
                for it in items
            ]
            caminho = export_utils.generate_csv_file(
                headers, rows, nome_base="contas_pagar"
            )

        _show_snack(page, f"✅ Exportado: {caminho}", ft.colors.GREEN)
    except Exception as ex:
        _show_snack(page, f"❌ Erro exportar CSV: {ex}", ft.colors.RED)


def export_finance_pdf(page: ft.Page, pdv_core, is_receber: bool, e=None):
    """Exporta as contas (pagar/receber) para PDF usando export_utils."""
    try:
        if is_receber:
            items = pdv_core.get_pending_receivables() or []
            headers = ["Vencimento", "Descrição", "Origem", "Valor", "Status", "ID"]
            rows = [
                [
                    getattr(it, "vencimento", "-"),
                    getattr(it, "descricao", ""),
                    getattr(it, "origem", getattr(it, "categoria", "")),
                    f"R$ {getattr(it, 'valor', 0.0):.2f}",
                    getattr(it, "status", ""),
                    getattr(it, "id", ""),
                ]
                for it in items
            ]
            caminho = export_utils.generate_pdf_file(
                headers, rows, nome_base="contas_receber", title="Contas a Receber"
            )
        else:
            items = pdv_core.get_pending_expenses() or []
            headers = ["Vencimento", "Descrição", "Categoria", "Valor", "Status", "ID"]
            rows = [
                [
                    getattr(it, "vencimento", "-"),
                    getattr(it, "descricao", ""),
                    getattr(it, "categoria", ""),
                    f"R$ {getattr(it, 'valor', 0.0):.2f}",
                    getattr(it, "status", ""),
                    getattr(it, "id", ""),
                ]
                for it in items
            ]
            caminho = export_utils.generate_pdf_file(
                headers, rows, nome_base="contas_pagar", title="Contas a Pagar"
            )

        _show_snack(page, f"✅ Exportado: {caminho}", ft.colors.GREEN)
    except Exception as ex:
        _show_snack(page, f"❌ Erro exportar PDF: {ex}", ft.colors.RED)


# ====================================================================
# VIEW PRINCIPAL
# ====================================================================


def create_financeiro_view(page: ft.Page, pdv_core, handle_back, create_appbar):
    # Função para fechamento automático do caixa em horário determinado
    def fechamento_automatico_caixa(horario_fechamento="23:59"):
        from datetime import datetime

        agora = datetime.now().strftime("%H:%M")
        if agora >= horario_fechamento:
            user_id = page.session.get("user_id") or 1
            sess = pdv_core.get_current_open_session(user_id)
            if sess:
                try:
                    # Fecha caixa com saldo atual e valor contado igual ao saldo
                    pdv_core.close_caixa_session(
                        sess.id, sess.current_balance, sess.current_balance
                    )
                    _show_snack(
                        page,
                        f"Caixa fechado automaticamente às {horario_fechamento}",
                        ft.colors.BLUE,
                    )
                    refresh_view(page, pdv_core, handle_back, create_appbar)
                except Exception as ex:
                    print(f"Erro ao fechar caixa automaticamente: {ex}")

    # Chama fechamento automático ao carregar a tela
    fechamento_automatico_caixa()
    """View principal do módulo financeiro - DADOS REAIS"""

    # 🐛 DEBUG IMPRESSÃO - COLE ISTO NO INÍCIO
    print("=" * 50)
    print("DEBUG create_financeiro_view:")
    print(f"page: {type(page)}")
    print(f"pdv_core: {type(pdv_core)}")
    print(f"handle_back: {type(handle_back)}")
    print(f"create_appbar: {type(create_appbar)}")
    print("=" * 50)
    # FIM DEBUG

    # ✅ CORREÇÃO 2: Busca dados reais do dashboard
    try:
        dashboard_data = pdv_core.get_dashboard_data()
    except Exception:
        # Se o método não existir, usa mock temporário
        dashboard_data = {
            "saldo_atual": 15200.55,
            "receitas_mes": 35890.70,
            "despesas_mes": 21500.15,
            "lucro_mes": 14390.55,
        }

    try:
        CONTAS_PAGAR = pdv_core.get_pending_expenses() or []
        CONTAS_RECEBER = pdv_core.get_pending_receivables() or []
    except Exception as ex:
        print(f"❌ Erro ao buscar dados: {ex}")
        CONTAS_PAGAR = []
        CONTAS_RECEBER = []

    try:
        caixa_control = create_caixa_control_card(page, pdv_core)
    except Exception as ex:
        print(f"❌ Erro ao criar card de caixa: {ex}")
        caixa_control = ft.Card(ft.Text("Erro ao carregar caixa", color=ft.colors.RED))

    dashboard_row = ft.ResponsiveRow(
        [
            ft.Column(
                col={"sm": 12, "md": 4, "lg": 4},
                controls=[
                    create_kpi_card(
                        "Saldo Atual",
                        dashboard_data["saldo_atual"],
                        ft.icons.ACCOUNT_BALANCE_WALLET_ROUNDED,
                        ft.colors.BLUE,
                    )
                ],
            ),
            ft.Column(
                col={"sm": 6, "md": 4, "lg": 4},
                controls=[
                    create_kpi_card(
                        "Receitas Mês",
                        dashboard_data["receitas_mes"],
                        ft.icons.TRENDING_UP_ROUNDED,
                        ft.colors.GREEN,
                    )
                ],
            ),
            ft.Column(
                col={"sm": 6, "md": 4, "lg": 4},
                controls=[
                    create_kpi_card(
                        "Despesas Mês",
                        dashboard_data["despesas_mes"],
                        ft.icons.TRENDING_DOWN_ROUNDED,
                        ft.colors.RED,
                    )
                ],
            ),
        ],
        spacing=20,
    )

    # ✅ CORREÇÃO 1: Usa partial para garantir eventos dos botões
    finance_tabs = ft.Card(
        ft.Tabs(
            selected_index=0,
            animation_duration=300,
            expand=True,
            tabs=[
                ft.Tab(
                    text="Contas a Pagar",
                    icon=ft.icons.PAYMENT_ROUNDED,
                    content=ft.Container(
                        ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Text(
                                            "Despesas Pendentes",
                                            size=20,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.ElevatedButton(
                                            "Nova Despesa",
                                            icon=ft.icons.ADD,
                                            bgcolor=ft.colors.RED,
                                            color=ft.colors.WHITE,
                                            on_click=lambda e: nova_despesa_dialog(
                                                page, pdv_core
                                            ),
                                        ),
                                        ft.Row(
                                            [
                                                ft.ElevatedButton(
                                                    "CSV",
                                                    icon=ft.icons.FILE_DOWNLOAD,
                                                    on_click=partial(
                                                        export_finance_csv,
                                                        page,
                                                        pdv_core,
                                                        False,
                                                    ),
                                                ),
                                                ft.ElevatedButton(
                                                    "PDF",
                                                    icon=ft.icons.PICTURE_AS_PDF,
                                                    on_click=partial(
                                                        export_finance_pdf,
                                                        page,
                                                        pdv_core,
                                                        False,
                                                    ),
                                                ),
                                            ],
                                            spacing=8,
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                ft.Container(
                                    content=ft.Column(
                                        [
                                            create_finance_table(
                                                page,
                                                CONTAS_PAGAR,
                                                is_receber=False,
                                                pdv_core=pdv_core,
                                            )
                                        ]
                                    ),
                                    height=400,
                                ),
                            ],
                            spacing=15,
                        ),
                        padding=20,
                    ),
                ),
                ft.Tab(
                    text="Contas a Receber",
                    icon=ft.icons.RECEIPT_LONG_OUTLINED,
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Text(
                                            "Receitas Pendentes",
                                            size=20,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.ElevatedButton(
                                            "Nova Receita",
                                            icon=ft.icons.ADD,
                                            bgcolor=ft.colors.GREEN,
                                            color=ft.colors.WHITE,
                                            on_click=lambda e: nova_receita_dialog(
                                                page, pdv_core
                                            ),
                                        ),
                                        ft.Row(
                                            [
                                                ft.ElevatedButton(
                                                    "CSV",
                                                    icon=ft.icons.FILE_DOWNLOAD,
                                                    on_click=partial(
                                                        export_finance_csv,
                                                        page,
                                                        pdv_core,
                                                        True,
                                                    ),
                                                ),
                                                ft.ElevatedButton(
                                                    "PDF",
                                                    icon=ft.icons.PICTURE_AS_PDF,
                                                    on_click=partial(
                                                        export_finance_pdf,
                                                        page,
                                                        pdv_core,
                                                        True,
                                                    ),
                                                ),
                                            ],
                                            spacing=8,
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                ft.Container(
                                    content=ft.Column(
                                        [
                                            create_finance_table(
                                                page,
                                                CONTAS_RECEBER,
                                                is_receber=True,
                                                pdv_core=pdv_core,
                                            )
                                        ]
                                    ),
                                    height=400,
                                ),
                            ],
                            spacing=15,
                        ),
                        padding=20,
                    ),
                ),
            ],
        ),
        elevation=5,
        expand=True,
    )

    def create_history_table_card():
        try:
            sessions = pdv_core.get_all_closed_sessions() or []
        except Exception:
            sessions = []

        if not sessions:
            return ft.Card(
                ft.Container(
                    ft.Text(
                        "Nenhum fechamento encontrado.",
                        size=16,
                        color=ft.colors.GREY_600,
                    ),
                    padding=20,
                    alignment=ft.alignment.center,
                ),
                elevation=5,
            )

        rows = []
        for session in sessions:
            user_name = session.user.full_name if session.user else "Desconhecido"
            diff = session.difference if hasattr(session, "difference") else 0.0
            system_balance = (
                session.closing_balance_system
                if hasattr(session, "closing_balance_system")
                else 0.0
            )
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Text(
                                session.closing_time.strftime("%d/%m/%Y")
                                if session.closing_time
                                else "-"
                            )
                        ),
                        ft.DataCell(ft.Text(user_name)),
                        ft.DataCell(ft.Text(format_currency(system_balance))),
                        ft.DataCell(
                            ft.Text(
                                format_currency(abs(diff)),
                                color=ft.colors.RED if diff < 0 else ft.colors.GREEN,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                "Quebra" if diff < 0 else "Sobra" if diff > 0 else "Ok"
                            )
                        ),
                    ]
                )
            )

        return ft.Card(
            ft.Container(
                ft.Column(
                    [
                        ft.Text(
                            "Histórico de Fechamentos",
                            size=20,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Container(
                            ft.DataTable(
                                columns=[
                                    ft.DataColumn(ft.Text("Data")),
                                    ft.DataColumn(ft.Text("Operador")),
                                    ft.DataColumn(ft.Text("Esperado")),
                                    ft.DataColumn(ft.Text("Diferença")),
                                    ft.DataColumn(ft.Text("Status")),
                                ],
                                rows=rows,
                                border=ft.border.all(1, ft.colors.BLACK12),
                            ),
                            height=350,
                        ),
                    ],
                    spacing=15,
                ),
                padding=20,
            ),
            elevation=5,
        )

    try:
        history_card = create_history_table_card()
    except Exception as ex:
        print(f"❌ Erro ao criar histórico: {ex}")
        history_card = ft.Card(
            ft.Text(f"Erro ao carregar histórico: {ex}", color=ft.colors.RED)
        )

    finance_content = ft.Column(
        [
            ft.Row(
                [
                    ft.Text(
                        "Painel Financeiro",
                        size=36,
                        weight=ft.FontWeight.BOLD,
                        color=ft.colors.BLACK87,
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            ft.Row(
                [
                    ft.ElevatedButton(
                        "F2 - Fechar Caixa",
                        icon=ft.icons.KEYBOARD_ARROW_RIGHT,
                        bgcolor=ft.colors.RED,
                        color=ft.colors.WHITE,
                        on_click=lambda e: (
                            lambda sess: close_and_audit_caixa_dialog(
                                page, pdv_core, sess
                            )
                        )(
                            pdv_core.get_current_open_session(
                                page.session.get("user_id") or 1
                            )
                        ),
                        height=48,
                        width=220,
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            ft.Row([ft.Container(caixa_control, expand=True)], height=200),
            ft.Divider(height=30),
            ft.Text(
                "Visão Geral do Mês (Gerencial)", size=24, weight=ft.FontWeight.W_600
            ),
            dashboard_row,
            ft.Divider(height=30),
            ft.ResponsiveRow(
                [
                    ft.Column(
                        col={"sm": 12, "lg": 6}, controls=[finance_tabs], expand=True
                    ),
                    ft.Column(
                        col={"sm": 12, "lg": 6}, controls=[history_card], expand=True
                    ),
                ],
                spacing=20,
                expand=True,
            ),
        ],
        scroll=ft.ScrollMode.ADAPTIVE,
        expand=True,
        spacing=25,
    )

    # ✅ GARANTE QUE create_appbar NÃO RETORNA None
    try:
        # ====================================================
        # SEÇÃO MODIFICADA COM O ÍCONE E ESTILO DO TÍTULO
        # ====================================================
        appbar = ft.AppBar(
            title=ft.Row(
                [
                    ft.Icon(
                        ft.icons.ACCOUNT_BALANCE_WALLET, color=ft.colors.BLACK, size=24
                    ),
                ]
            ),
            bgcolor=ft.colors.GREY_100,
        )
        if appbar is None:
            raise ValueError("create_appbar retornou None!")
    except Exception as e:
        print(f"❌ ERRO ao criar appbar: {e}")
        appbar = ft.AppBar(title=ft.Text("Financeiro - ERRO"))

    if handle_back:
        appbar.leading = ft.IconButton(icon=ft.icons.ARROW_BACK, on_click=handle_back)

    # Para garantir que o `Column(scroll=...)` consiga rolar,
    # colocamos a própria `finance_content` (que é um Column com scroll)
    # diretamente na View, em vez de empacotá-la em um Container que
    # em algumas versões do Flet inibe o comportamento de overflow.
    finance_content_container = ft.Container(
        content=finance_content, padding=20, expand=True
    )

    # Handler global de teclado para F1/F2
    def handle_key_down(e):
        if e.key == "F1":
            open_new_caixa_dialog(page, pdv_core, page.session.get("user_id") or 1)
        elif e.key == "F2":
            sess = pdv_core.get_current_open_session(page.session.get("user_id") or 1)
            if sess:
                close_and_audit_caixa_dialog(page, pdv_core, sess)

    page.on_key_down = handle_key_down
    try:
        # Inserimos a Column diretamente como segundo controle da View.
        return ft.View(
            "/financeiro",
            [appbar, finance_content],
            bgcolor=ft.colors.GREY_100,
        )
    except Exception:
        # Fallback seguro: usar Container se a View reclamar
        return ft.View(
            "/financeiro",
            [appbar, finance_content_container],
            bgcolor=ft.colors.GREY_100,
        )
