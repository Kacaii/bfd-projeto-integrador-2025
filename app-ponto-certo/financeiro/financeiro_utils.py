import flet as ft
from utils import export_utils
from datetime import datetime
from functools import partial


def format_currency(value):
    """Formata valor para moeda brasileira."""
    try:
        return (
            f"R$ {float(value):,.2f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
    except Exception:
        return str(value)


def _close_dialog(page: ft.Page):
    try:
        if hasattr(page, "close_dialog"):
            page.close_dialog()
        else:
            if getattr(page, "dialog", None):
                page.dialog.open = False
                page.update()
    except Exception:
        try:
            if getattr(page, "dialog", None):
                page.dialog.open = False
                page.update()
        except Exception:
            pass


def _show_snack(page: ft.Page, message: str, color=ft.colors.BLUE):
    """Mostra um snack bar na tela."""
    page.snack_bar = ft.SnackBar(
        ft.Text(message, color=color), bgcolor=ft.colors.WHITE, open=True
    )
    page.update()


def parse_currency(value_str):
    if not value_str or value_str.strip() == "":
        return 0.0
    try:
        cleaned = (
            value_str.replace("R$", "")
            .replace(" ", "")
            .replace(".", "")
            .replace(",", ".")
        )
        return float(cleaned) if cleaned else 0.0
    except Exception:
        return 0.0


def view_transaction(page: ft.Page, item_id: int, is_receber: bool, e=None):
    print(f"👁️ Visualizando ID: {item_id}")
    _show_snack(page, f"📋 Detalhes ID: {item_id}", ft.colors.BLUE)


def mark_as_paid(page: ft.Page, pdv_core, item_id: int, is_receber: bool, e=None):
    try:
        print(f"mark_as_paid called: item_id={item_id}, is_receber={is_receber}")
        if is_receber:
            pdv_core.mark_receivable_as_paid(item_id)
        else:
            pdv_core.mark_expense_as_paid(item_id)
        _close_dialog(page)
        _show_snack(page, "✅ Status atualizado!", ft.colors.GREEN)
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


def refresh_view(page: ft.Page, pdv_core, handle_back, create_appbar, view_func=None):
    try:
        if len(page.views) > 0:
            page.views.pop()
        if view_func:
            page.views.append(view_func(page, pdv_core, handle_back, create_appbar))
        page.update()
    except Exception as ex:
        print(f"❌ Erro ao atualizar view: {ex}")
