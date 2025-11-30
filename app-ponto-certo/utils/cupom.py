import flet as ft
from datetime import datetime
import os
from pathlib import Path
from utils.export_utils import generate_pdf_file

# tentativa de usar win32print para enviar dados RAW ao driver do Windows
try:
    import win32print

    HAS_WIN32 = True
except Exception:
    HAS_WIN32 = False


def show_cupom_dialog(
    page: ft.Page,
    itens_cupom,
    titulo_cupom,
    current_total,
    p_type,
    received=None,
    change=None,
    auto_print: bool = False,
):
    """Monta e exibe o diálogo do cupom fiscal e possibilita salvar como PDF.

    - `itens_cupom`: lista de linhas [nome, qtd, preco_u, total_str]
    - `titulo_cupom`: título do diálogo
    - `current_total`: valor numérico do total
    - `p_type`: método de pagamento (string)
    - `received`, `change`: valores numéricos opcionalmente exibidos
    """

    # Cabeçalho
    merchant_name = titulo_cupom.replace("Cupom Fiscal - ", "")
    header_items = [
        ft.Text(
            merchant_name,
            size=18,
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER,
        ),
        ft.Text(
            f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            size=12,
            text_align=ft.TextAlign.CENTER,
        ),
        ft.Text(f"Pagamento: {p_type}", size=12, text_align=ft.TextAlign.CENTER),
    ]
    if received is not None:
        header_items.append(
            ft.Text(
                f"Recebido: R$ {received:.2f}".replace(".", ","),
                size=12,
                text_align=ft.TextAlign.CENTER,
            )
        )
        header_items.append(
            ft.Text(
                f"Troco: R$ {change:.2f}".replace(".", ","),
                size=12,
                text_align=ft.TextAlign.CENTER,
            )
        )

    # Cabeçalho da tabela de itens
    itens_rows = []
    itens_rows.append(
        ft.Row(
            [
                ft.Text("Produto", size=13, weight=ft.FontWeight.BOLD, expand=True),
                ft.Text(
                    "Qtd",
                    size=13,
                    weight=ft.FontWeight.BOLD,
                    width=50,
                    text_align=ft.TextAlign.RIGHT,
                ),
                ft.Text(
                    "Preço",
                    size=13,
                    weight=ft.FontWeight.BOLD,
                    width=90,
                    text_align=ft.TextAlign.RIGHT,
                ),
                ft.Text(
                    "Total",
                    size=13,
                    weight=ft.FontWeight.BOLD,
                    width=90,
                    text_align=ft.TextAlign.RIGHT,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
    )

    for nome, qtd, preco_u, tot in itens_cupom:
        itens_rows.append(
            ft.Row(
                [
                    ft.Text(nome, size=13, expand=True),
                    ft.Text(qtd, size=13, width=50, text_align=ft.TextAlign.RIGHT),
                    ft.Text(preco_u, size=13, width=90, text_align=ft.TextAlign.RIGHT),
                    ft.Text(tot, size=13, width=90, text_align=ft.TextAlign.RIGHT),
                ],
                spacing=6,
            )
        )

    total_text = ft.Text(
        f"TOTAL: R$ {current_total:.2f}".replace(".", ","),
        size=18,
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.RIGHT,
    )
    footer_text = ft.Text(
        "Muito obrigado, volte sempre!",
        size=14,
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.CENTER,
    )

    receipt_column = ft.Column(
        header_items
        + [ft.Divider()]
        + itens_rows
        + [ft.Divider(), total_text, ft.Divider(), footer_text],
        spacing=6,
    )

    def _send_raw_to_printer(printer_name: str, data: bytes) -> None:
        """Envia bytes RAW para impressora via win32print."""
        hPrinter = None
        try:
            hPrinter = win32print.OpenPrinter(printer_name)
            win32print.StartDocPrinter(hPrinter, 1, ("Cupom", None, "RAW"))
            win32print.StartPagePrinter(hPrinter)
            win32print.WritePrinter(hPrinter, data)
            win32print.EndPagePrinter(hPrinter)
            win32print.EndDocPrinter(hPrinter)
        finally:
            if hPrinter:
                win32print.ClosePrinter(hPrinter)

    def _build_receipt_text(
        merchant_name, itens_cupom, current_total, p_type, received=None, change=None
    ):
        lines = []
        lines.append(merchant_name)
        lines.append(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lines.append(f"Pagamento: {p_type}")
        if received is not None:
            lines.append(f"Recebido: R$ {received:.2f}".replace(".", ","))
            lines.append(f"Troco: R$ {change:.2f}".replace(".", ","))
        lines.append("--------------------------------")
        for nome, qtd, preco_u, tot in itens_cupom:
            # formato simples: Produto (qtd x unit)  total
            lines.append(f"{nome} {qtd} x {preco_u}  {tot}")
        lines.append("--------------------------------")
        lines.append(f"TOTAL: R$ {current_total:.2f}".replace(".", ","))
        lines.append("")
        lines.append("Muito obrigado, volte sempre!")
        # juntar e retornar bytes (usar encoding compatível com impressora)
        text = "\n".join(lines) + "\n\n"
        return text.encode("utf-8")

    def salvar_pdf_cupom(_e):
        try:
            headers = ["Produto", "Qtd", "Preço Unit.", "Total"]
            pdf_rows = list(itens_cupom) + [
                ["", "", "", "Muito obrigado, volte sempre!"]
            ]
            caminho = generate_pdf_file(
                headers, pdf_rows, nome_base="cupom_fiscal", title=titulo_cupom
            )
            # abrir arquivo no sistema (Windows: os.startfile)
            try:
                os.startfile(caminho)
            except Exception:
                pass
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✅ Cupom salvo: {Path(caminho).name}"),
                bgcolor=ft.colors.GREEN_600,
            )
            page.snack_bar.open = True
            page.update()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ Erro ao salvar cupom: {ex}"), bgcolor=ft.colors.RED_600
            )
            page.snack_bar.open = True
            page.update()

    # Mostrar título genérico para evitar duplicação do nome do estabelecimento
    cupom_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Cupom Fiscal"),
        content=receipt_column,
        actions_alignment=ft.MainAxisAlignment.END,
    )

    original_keyboard_handler = page.on_keyboard_event

    def fechar_cupom(_e=None):
        # Restaura handler global antes de fechar
        page.on_keyboard_event = original_keyboard_handler
        cupom_dialog.open = False
        page.update()

    cupom_dialog.actions = [
        ft.TextButton(
            "Fechar",
            on_click=fechar_cupom,
        ),
        ft.ElevatedButton("Salvar PDF", on_click=salvar_pdf_cupom),
    ]

    page.dialog = cupom_dialog
    cupom_dialog.open = True

    # Enquanto o cupom estiver aberto, Enter fecha o diálogo
    def cupom_keyboard_handler(e: ft.KeyboardEvent):
        if e.key == "Enter":
            fechar_cupom()

    page.on_keyboard_event = cupom_keyboard_handler
    page.update()

    # Impressão automática opcional
    if auto_print:
        try:
            data = _build_receipt_text(
                merchant_name, itens_cupom, current_total, p_type, received, change
            )
            if HAS_WIN32:
                printer_name = win32print.GetDefaultPrinter()
                _send_raw_to_printer(printer_name, data)
            else:
                # Fallback: gerar PDF e enviar para impressão pelo app associado
                headers = ["Produto", "Qtd", "Preço Unit.", "Total"]
                pdf_rows = list(itens_cupom) + [
                    ["", "", "", "Muito obrigado, volte sempre!"]
                ]
                caminho = generate_pdf_file(
                    headers,
                    pdf_rows,
                    nome_base="cupom_fiscal",
                    title=f"Cupom Fiscal - {merchant_name}",
                )
                try:
                    os.startfile(caminho, "print")
                except Exception:
                    # platform fallback: abrir sem imprimir
                    try:
                        os.startfile(caminho)
                    except Exception:
                        raise

            page.snack_bar = ft.SnackBar(
                ft.Text("✅ Cupom enviado para impressora"), bgcolor=ft.colors.GREEN_600
            )
            page.snack_bar.open = True
            page.update()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ Erro ao imprimir cupom: {ex}"), bgcolor=ft.colors.RED_600
            )
            page.snack_bar.open = True
            page.update()
