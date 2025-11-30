import flet as ft
from datetime import datetime
from .financeiro_utils import (
    parse_currency,
    _close_dialog,
    _show_snack,
    refresh_view,
    format_currency,
)


def open_new_caixa_dialog(page: ft.Page, pdv_core, user_id: int):
    balance_field = ft.TextField(
        label="Saldo Inicial (R$)", value="0,00", prefix_text="R$ ", autofocus=True
    )

    def confirm(e):
        try:
            balance = parse_currency(balance_field.value)
            pdv_core.open_new_caixa(user_id, balance)
            _close_dialog(page)
            _show_snack(page, "✅ Caixa aberto!", ft.colors.GREEN)
            try:
                refresh_view(page, pdv_core, None, None)
            except Exception:
                pass
        except Exception as ex:
            _show_snack(page, f"❌ Erro: {str(ex)[:50]}", ft.colors.RED)

    page.dialog = ft.AlertDialog(
        title=ft.Text("Abrir Novo Caixa"),
        content=balance_field,
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: _close_dialog(page)),
            ft.ElevatedButton(
                "Confirmar",
                bgcolor=ft.colors.GREEN,
                color=ft.colors.WHITE,
                on_click=confirm,
            ),
        ],
    )
    page.dialog.open = True
    page.update()


def close_and_audit_caixa_dialog(page: ft.Page, pdv_core, session):
    counted_field = ft.TextField(
        label="Valor Contado (R$)", value="0,00", prefix_text="R$ "
    )

    def confirm(e):
        try:
            counted = parse_currency(counted_field.value)
            try:
                current_bal = session.current_balance
            except Exception:
                current_bal = session.opening_balance
            pdv_core.close_caixa_session(session.id, current_bal, counted)
            _close_dialog(page)
            _show_snack(page, "✅ Caixa fechado!", ft.colors.BLUE)
            try:
                refresh_view(page, pdv_core, None, None)
            except Exception:
                pass
            try:
                page.update()
            except Exception:
                pass
        except Exception as ex:
            _show_snack(page, f"❌ Erro: {str(ex)[:50]}", ft.colors.RED)

    page.dialog = ft.AlertDialog(
        title=ft.Text("Fechar Caixa e Auditar"),
        content=ft.Column(
            [
                ft.Text(
                    f"Esperado: {format_currency(getattr(session, 'current_balance', session.opening_balance))}"
                ),
                counted_field,
            ],
            tight=True,
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: _close_dialog(page)),
            ft.ElevatedButton(
                "Confirmar",
                bgcolor=ft.colors.RED,
                color=ft.colors.WHITE,
                on_click=confirm,
            ),
        ],
    )
    page.dialog.open = True
    page.update()


def nova_despesa_dialog(page: ft.Page, pdv_core, e=None):
    descricao_field = ft.TextField(label="Descrição", autofocus=True)
    valor_field = ft.TextField(
        label="Valor (R$)", prefix_text="R$ ", keyboard_type=ft.KeyboardType.NUMBER
    )
    vencimento_field = ft.TextField(
        label="Vencimento", value=datetime.now().strftime("%d/%m/%Y")
    )
    categoria_field = ft.Dropdown(
        label="Categoria",
        options=[
            ft.dropdown.Option("Operacional"),
            ft.dropdown.Option("Mercadorias"),
            ft.dropdown.Option("Funcionários"),
            ft.dropdown.Option("Outros"),
        ],
    )

    def confirm(e):
        if not descricao_field.value or not valor_field.value:
            _show_snack(page, "❌ Preencha todos os campos!", ft.colors.RED)
            return
        try:
            valor = parse_currency(valor_field.value)
            pdv_core.create_expense(
                descricao_field.value,
                valor,
                vencimento_field.value,
                categoria_field.value,
            )
            _close_dialog(page)
            _show_snack(page, "✅ Despesa criada!", ft.colors.GREEN)
            try:
                refresh_view(page, pdv_core, None, None)
            except Exception:
                pass
            try:
                page.update()
            except Exception:
                pass
        except Exception as ex:
            _show_snack(page, f"❌ Erro: {str(ex)[:50]}", ft.colors.RED)

    page.dialog = ft.AlertDialog(
        title=ft.Text("Nova Despesa"),
        content=ft.Column(
            [descricao_field, valor_field, vencimento_field, categoria_field],
            tight=True,
            spacing=10,
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: _close_dialog(page)),
            ft.ElevatedButton(
                "Salvar", bgcolor=ft.colors.RED, color=ft.colors.WHITE, on_click=confirm
            ),
        ],
    )
    page.dialog.open = True
    page.update()


def nova_receita_dialog(page: ft.Page, pdv_core, e=None):
    descricao_field = ft.TextField(label="Descrição", autofocus=True)
    valor_field = ft.TextField(
        label="Valor (R$)", prefix_text="R$ ", keyboard_type=ft.KeyboardType.NUMBER
    )
    vencimento_field = ft.TextField(
        label="Vencimento", value=datetime.now().strftime("%d/%m/%Y")
    )
    origem_field = ft.Dropdown(
        label="Origem",
        options=[
            ft.dropdown.Option("Vendas"),
            ft.dropdown.Option("Serviços"),
            ft.dropdown.Option("Outros"),
        ],
    )

    def confirm(e):
        if not descricao_field.value or not valor_field.value:
            _show_snack(page, "❌ Preencha todos os campos!", ft.colors.RED)
            return
        try:
            valor = parse_currency(valor_field.value)
            pdv_core.create_receivable(
                descricao_field.value, valor, vencimento_field.value, origem_field.value
            )
            _close_dialog(page)
            _show_snack(page, "✅ Receita criada!", ft.colors.GREEN)
            try:
                refresh_view(page, pdv_core, None, None)
            except Exception:
                pass
            try:
                page.update()
            except Exception:
                pass
        except Exception as ex:
            _show_snack(page, f"❌ Erro: {str(ex)[:50]}", ft.colors.RED)

    page.dialog = ft.AlertDialog(
        title=ft.Text("Nova Receita"),
        content=ft.Column(
            [descricao_field, valor_field, vencimento_field, origem_field],
            tight=True,
            spacing=10,
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: _close_dialog(page)),
            ft.ElevatedButton(
                "Salvar",
                bgcolor=ft.colors.GREEN,
                color=ft.colors.WHITE,
                on_click=confirm,
            ),
        ],
    )
    page.dialog.open = True
    page.update()
