import flet as ft
from functools import partial
from .financeiro_utils import format_currency, view_transaction, mark_as_paid
from .financeiro_dialogs import (
    close_and_audit_caixa_dialog,
    open_new_caixa_dialog,
    nova_despesa_dialog,
    nova_receita_dialog,
)


def create_kpi_card(title, value, icon, color):
    return ft.Card(
        ft.Container(
            padding=20,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(title, size=16, weight=ft.FontWeight.W_500),
                            ft.Icon(icon, color=color, size=30),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Text(
                        format_currency(value),
                        size=32,
                        weight=ft.FontWeight.BOLD,
                        color=color,
                    ),
                ],
                spacing=10,
            ),
        ),
        elevation=5,
    )


def create_caixa_control_card(page: ft.Page, pdv_core):
    user_id = page.session.get("user_id")
    if user_id is None:
        user_id = 1
    current_open_session = pdv_core.get_current_open_session(user_id)

    def handle_caixa_action(e):
        if current_open_session:
            close_and_audit_caixa_dialog(page, pdv_core, current_open_session)
        else:
            open_new_caixa_dialog(page, pdv_core, user_id)

    status_text = ft.Text(
        "CAIXA ABERTO" if current_open_session else "CAIXA FECHADO",
        color=ft.colors.GREEN if current_open_session else ft.colors.RED,
        weight=ft.FontWeight.BOLD,
        size=18,
    )
    action_button = ft.ElevatedButton(
        "FECHAR CAIXA E AUDITAR" if current_open_session else "ABRIR NOVO CAIXA",
        icon=ft.icons.LOCK_OUTLINED if current_open_session else ft.icons.KEY_ROUNDED,
        bgcolor=ft.colors.RED if current_open_session else ft.colors.GREEN,
        color=ft.colors.WHITE,
        on_click=handle_caixa_action,
    )
    saldo_valor = current_open_session.opening_balance if current_open_session else 0.0
    return ft.Card(
        ft.Container(
            padding=20,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(
                                ft.icons.LOCK_OPEN_ROUNDED
                                if current_open_session
                                else ft.icons.LOCK_OUTLINED,
                                size=28,
                            ),
                            ft.Text(
                                "Controle Operacional de Caixa",
                                size=20,
                                weight=ft.FontWeight.W_600,
                            ),
                        ]
                    ),
                    ft.Divider(height=10),
                    status_text,
                    ft.Text(
                        f"Saldo Inicial: {format_currency(saldo_valor)}",
                        size=22,
                        weight=ft.FontWeight.BOLD,
                        color=ft.colors.BLUE,
                    ),
                    ft.Container(action_button, padding=ft.padding.only(top=10)),
                ],
                spacing=10,
            ),
        ),
        elevation=5,
    )


def create_finance_table(page: ft.Page, data, is_receber=False, pdv_core=None):
    if data is None:
        data = []
    rows = []
    for item in data:
        item_id = getattr(item, "id", 0)
        descricao = getattr(item, "descricao", "N/A")
        valor = getattr(item, "valor", 0.0)
        status = getattr(item, "status", "Pendente")
        categoria = getattr(item, "categoria", getattr(item, "origem", "N/A"))
        vencimento = getattr(item, "vencimento", "-")
        action_button = ft.IconButton(
            icon=ft.icons.VISIBILITY
            if status in ["Pago", "Recebido"]
            else ft.icons.CHECK_CIRCLE,
            tooltip="Visualizar"
            if status in ["Pago", "Recebido"]
            else ("Marcar como Recebido" if is_receber else "Marcar como Pago"),
            on_click=partial(view_transaction, page, item_id, is_receber)
            if status in ["Pago", "Recebido"]
            else partial(mark_as_paid, page, pdv_core, item_id, is_receber),
        )
        rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(vencimento)),
                    ft.DataCell(ft.Text(descricao)),
                    ft.DataCell(ft.Text(categoria)),
                    ft.DataCell(ft.Text(format_currency(valor))),
                    ft.DataCell(
                        ft.Container(
                            ft.Text(status, size=12, color=ft.colors.WHITE),
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                            bgcolor=ft.colors.GREEN
                            if status in ["Pago", "Recebido"]
                            else ft.colors.ORANGE,
                            border_radius=5,
                        )
                    ),
                    ft.DataCell(action_button),
                ]
            )
        )
    return ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Vencimento")),
            ft.DataColumn(ft.Text("Descrição")),
            ft.DataColumn(ft.Text("Categoria" if not is_receber else "Origem")),
            ft.DataColumn(ft.Text("Valor"), numeric=True),
            ft.DataColumn(ft.Text("Status")),
            ft.DataColumn(ft.Text("Ações")),
        ],
        rows=rows,
        border=ft.border.all(1, ft.colors.BLACK12),
    )
