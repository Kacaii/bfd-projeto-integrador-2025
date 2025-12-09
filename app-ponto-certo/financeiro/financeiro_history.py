"""Componentes para histórico de fechamentos de caixa com auditoria - Versão com atualização instantânea."""

import flet as ft
from models.db_models import CaixaSession, Venda, Expense, Receivable
from datetime import datetime, timedelta


def create_caixa_history_table(page: ft.Page, pdv_core):
    """Cria tabela de histórico de fechamentos de caixa com atualização instantânea após deletar.

    Args:
        page: página Flet
        pdv_core: objeto do núcleo de negócio

    Returns:
        ft.Column com a tabela (que pode ser atualizada instantaneamente)
    """
    from .financeiro_utils import _show_snack

    # Container que será retornado - permite atualizar o conteúdo
    table_container = ft.Column(expand=True)

    def atualizar_tabela():
        """Função para atualizar a tabela após mudanças"""
        try:
            # Limpar e recrear o conteúdo
            table_container.controls.clear()
            novo_conteudo = _criar_conteudo_tabela()
            if novo_conteudo:
                table_container.controls.append(novo_conteudo)
            page.update()
        except Exception as ex:
            print(f"[ERRO] atualizar_tabela: {ex}")

    def _criar_conteudo_tabela():
        """Cria o conteúdo da tabela (separado para permitir atualização)"""
        from .financeiro_utils import _show_snack as show_snack_inner

        try:

            def deletar_sessao_direto(session_id: int):
                """Deleta uma sessão de caixa com confirmação"""
                try:

                    def confirmar_delete(e):
                        overlay_confirm.visible = False
                        try:
                            session_to_delete = pdv_core.session.query(
                                CaixaSession
                            ).get(session_id)
                            if session_to_delete:
                                pdv_core.session.delete(session_to_delete)
                                pdv_core.session.commit()
                                show_snack_inner(
                                    page,
                                    "✅ Sessão deletada com sucesso!",
                                    color=ft.Colors.GREEN,
                                )
                                # Atualizar a tabela instantaneamente
                                atualizar_tabela()
                            else:
                                show_snack_inner(
                                    page,
                                    "❌ Sessão não encontrada!",
                                    color=ft.Colors.RED,
                                )
                        except Exception as ex:
                            show_snack_inner(
                                page,
                                f"❌ Erro ao deletar: {str(ex)}",
                                color=ft.Colors.RED,
                            )
                            print(f"[ERRO] deletar_sessao_direto: {ex}")
                        finally:
                            page.update()

                    def cancelar_delete(e):
                        overlay_confirm.visible = False
                        page.update()

                    # Criar overlay de confirmação
                    content_confirm = ft.Column(
                        [
                            ft.Text(
                                "Deseja deletar esta sessão?", size=16, weight="bold"
                            ),
                            ft.Text(
                                "Esta ação não pode ser desfeita.",
                                size=12,
                                color=ft.Colors.RED,
                            ),
                            ft.Row(
                                [
                                    ft.TextButton("Cancelar", on_click=cancelar_delete),
                                    ft.ElevatedButton(
                                        "Deletar",
                                        on_click=confirmar_delete,
                                        bgcolor=ft.Colors.RED,
                                        color=ft.Colors.WHITE,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.END,
                            ),
                        ],
                        spacing=12,
                    )

                    overlay_confirm = ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Container(expand=True),
                                        ft.Container(
                                            content=content_confirm,
                                            width=350,
                                            bgcolor="white",
                                            border_radius=8,
                                            padding=20,
                                        ),
                                        ft.Container(expand=True),
                                    ],
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                            ],
                            expand=True,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        visible=True,
                        bgcolor="rgba(0, 0, 0, 0.5)",
                        expand=True,
                    )

                    if overlay_confirm not in page.overlay:
                        page.overlay.append(overlay_confirm)
                    page.update()

                except Exception as ex:
                    show_snack_inner(
                        page, f"Erro ao deletar: {str(ex)}", color=ft.Colors.RED
                    )
                    print(f"[ERRO] deletar_sessao_direto: {ex}")

            def abrir_detalhes_sessao(session_id: int):
                """Abre modal com detalhes da sessão (todas as transações)"""
                try:
                    # Buscar sessão pelo ID
                    session = pdv_core.session.query(CaixaSession).get(session_id)

                    if not session:
                        show_snack_inner(
                            page, "Sessão não encontrada", color=ft.Colors.RED
                        )
                        return

                    # Buscar todas as transações dessa sessão pelo período
                    data_inicio = session.opening_time
                    data_fim = (
                        session.closing_time
                        if session.closing_time
                        else datetime.now() + timedelta(days=1)
                    )

                    # Buscar vendas no período
                    vendas = (
                        pdv_core.session.query(Venda)
                        .filter(
                            Venda.data_venda >= data_inicio,
                            Venda.data_venda <= data_fim,
                        )
                        .all()
                        or []
                    )

                    # Buscar despesas no período
                    despesas = (
                        pdv_core.session.query(Expense)
                        .filter(
                            Expense.data_cadastro >= data_inicio,
                            Expense.data_cadastro <= data_fim,
                        )
                        .all()
                        or []
                    )

                    # Buscar receitas no período
                    receitas = (
                        pdv_core.session.query(Receivable)
                        .filter(
                            Receivable.data_cadastro >= data_inicio,
                            Receivable.data_cadastro <= data_fim,
                        )
                        .all()
                        or []
                    )

                    # Montar conteúdo do modal
                    content_rows = []

                    # Título e informações gerais
                    content_rows.append(
                        ft.Text(
                            f"Detalhes da Sessão #{session_id}",
                            size=18,
                            weight="bold",
                        )
                    )
                    content_rows.append(
                        ft.Text(f"Abertura: {session.opening_time}", size=12)
                    )
                    if session.closing_time:
                        content_rows.append(
                            ft.Text(f"Fechamento: {session.closing_time}", size=12)
                        )
                    content_rows.append(
                        ft.Text(
                            f"Saldo Inicial: R$ {session.opening_balance:,.2f}",
                            size=12,
                        )
                    )
                    content_rows.append(
                        ft.Text(
                            f"Saldo Final: R$ {session.closing_balance_actual or 0:,.2f}",
                            size=12,
                        )
                    )
                    content_rows.append(ft.Divider())

                    # Vendas
                    if vendas:
                        content_rows.append(
                            ft.Text(
                                f"📊 Vendas ({len(vendas)})", size=14, weight="bold"
                            )
                        )
                        for venda in vendas:
                            content_rows.append(
                                ft.Row(
                                    [
                                        ft.Text(
                                            f"{venda.created_at}", size=11, width=150
                                        ),
                                        ft.Text(
                                            f"Total: R$ {venda.total:,.2f}", size=11
                                        ),
                                        ft.Text(f"Status: {venda.status}", size=11),
                                    ]
                                )
                            )
                        content_rows.append(ft.Divider())

                    # Despesas
                    if despesas:
                        content_rows.append(
                            ft.Text(
                                f"💸 Despesas ({len(despesas)})",
                                size=14,
                                weight="bold",
                            )
                        )
                        for despesa in despesas:
                            content_rows.append(
                                ft.Row(
                                    [
                                        ft.Text(f"{despesa.data}", size=11, width=150),
                                        ft.Text(f"{despesa.descricao}", size=11),
                                        ft.Text(f"R$ {despesa.valor:,.2f}", size=11),
                                    ]
                                )
                            )
                        content_rows.append(ft.Divider())

                    # Receitas
                    if receitas:
                        content_rows.append(
                            ft.Text(
                                f"💰 Receitas ({len(receitas)})",
                                size=14,
                                weight="bold",
                            )
                        )
                        for receita in receitas:
                            content_rows.append(
                                ft.Row(
                                    [
                                        ft.Text(
                                            f"{receita.data_vencimento}",
                                            size=11,
                                            width=150,
                                        ),
                                        ft.Text(f"{receita.descricao}", size=11),
                                        ft.Text(f"R$ {receita.valor:,.2f}", size=11),
                                    ]
                                )
                            )

                    # Criar overlay customizado para detalhes
                    overlay = ft.Container(expand=True)  # placeholder

                    def fechar_modal():
                        overlay.visible = False
                        page.update()

                    def deletar_sessao():
                        """Deleta a sessão de caixa"""
                        try:
                            session_to_delete = pdv_core.session.query(
                                CaixaSession
                            ).get(session_id)
                            if session_to_delete:
                                pdv_core.session.delete(session_to_delete)
                                pdv_core.session.commit()
                                fechar_modal()
                                show_snack_inner(
                                    page,
                                    "✅ Sessão deletada com sucesso!",
                                    color=ft.Colors.GREEN,
                                )
                                # Atualizar a tabela
                                atualizar_tabela()
                            else:
                                show_snack_inner(
                                    page,
                                    "❌ Sessão não encontrada!",
                                    color=ft.Colors.RED,
                                )
                        except Exception as ex:
                            show_snack_inner(
                                page,
                                f"❌ Erro ao deletar: {str(ex)}",
                                color=ft.Colors.RED,
                            )
                            print(f"[ERRO] deletar_sessao: {ex}")

                    # Conteúdo do overlay
                    content = ft.Column(
                        spacing=12,
                        controls=[
                            ft.Text(
                                f"Auditoria - Sessão #{session_id}",
                                size=18,
                                weight="bold",
                            ),
                            ft.Divider(),
                            ft.Column(
                                content_rows,
                                scroll=ft.ScrollMode.AUTO,
                            ),
                            ft.Row(
                                [
                                    ft.TextButton(
                                        "Fechar", on_click=lambda e: fechar_modal()
                                    ),
                                    ft.ElevatedButton(
                                        "Deletar",
                                        icon=ft.Icons.DELETE,
                                        on_click=lambda e: deletar_sessao(),
                                        bgcolor=ft.Colors.RED,
                                        color=ft.Colors.WHITE,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.END,
                            ),
                        ],
                    )

                    overlay = ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Container(expand=True),
                                        ft.Container(
                                            content=content,
                                            width=600,
                                            bgcolor="white",
                                            border_radius=8,
                                            padding=20,
                                        ),
                                        ft.Container(expand=True),
                                    ],
                                    vertical_alignment=ft.CrossAxisAlignment.START,
                                ),
                            ],
                            expand=True,
                            alignment=ft.MainAxisAlignment.START,
                        ),
                        visible=True,
                        bgcolor="rgba(0, 0, 0, 0.5)",
                        expand=True,
                    )

                    if overlay not in page.overlay:
                        page.overlay.append(overlay)
                    page.update()

                except Exception as ex:
                    show_snack_inner(
                        page,
                        f"Erro ao abrir detalhes: {str(ex)}",
                        color=ft.Colors.RED,
                    )
                    print(f"[ERRO] abrir_detalhes_sessao: {ex}")

            # Buscar histórico de sessões de caixa
            sessions = (
                pdv_core.session.query(CaixaSession)
                .order_by(CaixaSession.opening_time.desc())
                .limit(20)
                .all()
                or []
            )

            # Criar colunas da tabela
            columns = [
                ft.DataColumn(ft.Text("ID", weight="bold", size=14), numeric=False),
                ft.DataColumn(
                    ft.Text("Abertura", weight="bold", size=14), numeric=False
                ),
                ft.DataColumn(
                    ft.Text("Fechamento", weight="bold", size=14), numeric=False
                ),
                ft.DataColumn(
                    ft.Text("Saldo Inicial", weight="bold", size=14), numeric=True
                ),
                ft.DataColumn(
                    ft.Text("Saldo Final", weight="bold", size=14), numeric=True
                ),
                ft.DataColumn(ft.Text("Ações", weight="bold", size=14), numeric=False),
            ]

            # Criar linhas
            rows = []
            for session in sessions:
                abertura = (
                    session.opening_time.strftime("%d/%m %H:%M")
                    if session.opening_time
                    else "-"
                )
                fechamento = (
                    session.closing_time.strftime("%d/%m %H:%M")
                    if session.closing_time
                    else "-"
                )

                rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(session.id), size=13)),
                            ft.DataCell(ft.Text(abertura, size=13)),
                            ft.DataCell(ft.Text(fechamento, size=13)),
                            ft.DataCell(
                                ft.Text(f"R$ {session.opening_balance:,.2f}", size=13)
                            ),
                            ft.DataCell(
                                ft.Text(
                                    f"R$ {session.closing_balance_actual or 0:,.2f}",
                                    size=13,
                                )
                            ),
                            ft.DataCell(
                                ft.Container(
                                    ft.Row(
                                        [
                                            ft.IconButton(
                                                icon=ft.Icons.DETAILS,
                                                icon_size=22,
                                                tooltip="Ver detalhes",
                                                on_click=lambda e,
                                                sid=session.id: abrir_detalhes_sessao(
                                                    sid
                                                ),
                                            ),
                                            ft.IconButton(
                                                icon=ft.Icons.DELETE,
                                                icon_size=22,
                                                tooltip="Deletar sessão",
                                                on_click=lambda e,
                                                sid=session.id: deletar_sessao_direto(
                                                    sid
                                                ),
                                            ),
                                        ],
                                        spacing=0,
                                    ),
                                    padding=0,
                                )
                            ),
                        ]
                    )
                )

            # Criar DataTable
            data_table = ft.DataTable(
                columns=columns,
                rows=rows,
                border=ft.border.all(1, ft.Colors.BLACK12),
                border_radius=8,
                heading_row_color=ft.Colors.BLUE_100,
                data_row_color=ft.Colors.GREY_50,
                bgcolor=ft.Colors.WHITE,
                column_spacing=10,
                divider_thickness=1,
                expand=True,
                show_checkbox_column=False,
                horizontal_lines=ft.border.BorderSide(1, ft.Colors.BLACK12),
                vertical_lines=ft.border.BorderSide(1, ft.Colors.BLACK12),
                heading_row_height=45,
                data_row_max_height=45,
            )

            # Wrapper para a tabela com Container preenchendo espaço
            table_wrapper = ft.Container(
                content=data_table,
                expand=True,
                bgcolor=ft.Colors.WHITE,
            )

            # Retornar Column com scroll
            return ft.Column(
                [table_wrapper],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
                spacing=0,
            )

        except Exception as ex:
            print(f"[ERRO] _criar_conteudo_tabela: {ex}")
            import traceback

            traceback.print_exc()

            return ft.Column(
                [
                    ft.Text(
                        "Erro ao carregar histórico de fechamentos",
                        color=ft.Colors.RED,
                    ),
                    ft.Text(str(ex), size=10, color=ft.Colors.RED),
                ]
            )

    # Criação inicial da tabela
    try:
        conteudo_inicial = _criar_conteudo_tabela()
        if conteudo_inicial:
            table_container.controls.append(conteudo_inicial)
    except Exception as ex:
        print(f"[ERRO] create_caixa_history_table inicial: {ex}")
        table_container.controls.append(
            ft.Text(f"Erro ao carregar histórico: {str(ex)}", color=ft.Colors.RED)
        )

    return table_container
