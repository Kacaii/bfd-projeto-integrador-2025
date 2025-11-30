import flet as ft
from datetime import datetime, time
from pathlib import Path
from utils.export_utils import generate_csv_file, generate_pdf_file


def create_relatorio_vendas_view(page, pdv_core, handle_back):
    today_date = datetime.today().date()
    # =========================================================================
    # ESTILOS E VARIÁVEIS
    # =========================================================================
    bg_color = ft.colors.WHITE

    # Define os estados diretamente, compatível com versões mais antigas
    HOVERED = "hovered"

    # =========================================================================
    # FILTROS
    # =========================================================================

    # Labels que exibem a data selecionada
    inicio_label = ft.Text(today_date.strftime("%d/%m/%Y"))
    fim_label = ft.Text(today_date.strftime("%d/%m/%Y"))

    # DatePickers sem recarregar automaticamente a tabela
    def on_start_change(e):
        if start_date_picker.value:
            d = start_date_picker.value
            if isinstance(d, datetime):
                d = d.date()
            inicio_label.value = d.strftime("%d/%m/%Y")
            page.update()

    def on_end_change(e):
        if end_date_picker.value:
            d = end_date_picker.value
            if isinstance(d, datetime):
                d = d.date()
            fim_label.value = d.strftime("%d/%m/%Y")
            page.update()

    start_date_picker = ft.DatePicker(value=today_date, on_change=on_start_change)
    end_date_picker = ft.DatePicker(value=today_date, on_change=on_end_change)
    page.overlay.extend([start_date_picker, end_date_picker])

    metodo_pagamento = ft.Dropdown(
        width=180,
        value="Todos",
        options=[
            ft.dropdown.Option("Todos"),
            ft.dropdown.Option("Débito"),
            ft.dropdown.Option("Crédito"),
            ft.dropdown.Option("Dinheiro"),
            ft.dropdown.Option("PIX"),
        ],
        on_change=lambda e: carregar_vendas(),
        label="Forma de Pagamento",
        border_color=ft.colors.GREY_300,
        content_padding=10,
    )

    def criar_botao_data(texto, picker):
        # Acessando o estado HOVERED através de strings, mais seguro
        return ft.ElevatedButton(
            text=texto,
            icon=ft.icons.CALENDAR_MONTH,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=15,
                bgcolor={HOVERED: ft.colors.GREY_100, "": ft.colors.WHITE},
                color=ft.colors.BLACK,
                elevation=1,
            ),
            on_click=lambda _: picker.pick_date(),
        )

    filtros_content = None  # será definido após carregar_vendas para usar o botão

    # =========================================================================
    # MÉTRICAS (CARDS)
    # =========================================================================
    vendas_hoje_valor = ft.Text(
        "R$ 0.00", size=24, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_700
    )
    lucro_hoje_valor = ft.Text(
        "R$ 0.00", size=24, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_700
    )
    vendas_filtradas = []
    caixa_session = None  # Manter variável para contexto PDV

    def create_metric_card(title, value_ref, icon, icon_bg_color, icon_color):
        return ft.Card(
            elevation=2,
            content=ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(icon, color=icon_color, size=30),
                            bgcolor=icon_bg_color,
                            padding=15,
                            border_radius=12,
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    title,
                                    size=14,
                                    color=ft.colors.GREY_600,
                                    weight=ft.FontWeight.W_500,
                                ),
                                value_ref,
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=2,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    spacing=15,
                ),
                padding=20,
                width=300,
                height=110,
                bgcolor=ft.colors.WHITE,
                border_radius=12,
            ),
        )

    refresh_button = ft.IconButton(
        ft.icons.REFRESH,
        tooltip="Atualizar Dados",
        on_click=lambda e: carregar_vendas(),
        icon_size=24,
        style=ft.ButtonStyle(
            bgcolor=ft.colors.BLUE_50, shape=ft.CircleBorder(), padding=10
        ),
        icon_color=ft.colors.BLUE_700,
    )

    # Cards Centralizados: alignment=ft.MainAxisAlignment.CENTER
    dashboard = ft.Container(
        content=ft.Row(
            [
                create_metric_card(
                    "Total de Vendas",
                    vendas_hoje_valor,
                    ft.icons.ATTACH_MONEY,
                    ft.colors.BLUE_50,
                    ft.colors.BLUE_700,
                ),
                create_metric_card(
                    "Lucro Estimado (30%)",
                    lucro_hoje_valor,
                    ft.icons.TRENDING_UP,
                    ft.colors.GREEN_50,
                    ft.colors.GREEN_700,
                ),
                ft.Container(
                    content=refresh_button,
                    alignment=ft.alignment.center,
                ),
            ],
            wrap=True,
            spacing=20,
            alignment=ft.MainAxisAlignment.CENTER,  # <--- Centraliza os cards
        ),
        padding=ft.padding.only(bottom=10),
    )

    # =========================================================================
    # TABELA DETALHADA E LAYOUT DE VISIBILIDADE
    # =========================================================================
    tabela_vendas = ft.DataTable(
        columns=[
            ft.DataColumn(
                ft.Text("PRODUTO", weight="bold", size=12, color=ft.colors.GREY_700)
            ),
            ft.DataColumn(
                ft.Text(
                    "DATA PAGAMENTO", weight="bold", size=12, color=ft.colors.GREY_700
                )
            ),
            ft.DataColumn(
                ft.Text("PAGAMENTO", weight="bold", size=12, color=ft.colors.GREY_700)
            ),
            ft.DataColumn(
                ft.Text("QTD", weight="bold", size=12, color=ft.colors.GREY_700),
                numeric=True,
            ),
            ft.DataColumn(
                ft.Text(
                    "VALOR TOTAL", weight="bold", size=12, color=ft.colors.GREY_700
                ),
                numeric=True,
            ),
            ft.DataColumn(
                ft.Text("ID VENDA", weight="bold", size=12, color=ft.colors.GREY_700)
            ),
        ],
        rows=[],
        border=ft.border.all(1, ft.colors.GREY_200),
        border_radius=8,
        vertical_lines=ft.border.BorderSide(1, ft.colors.GREY_100),
        horizontal_lines=ft.border.BorderSide(1, ft.colors.GREY_100),
        bgcolor=ft.colors.WHITE,
        heading_row_color=ft.colors.GREY_50,
        heading_row_height=60,
        data_row_min_height=50,
        column_spacing=40,
        divider_thickness=0,
        visible=False,
    )

    no_data_message = ft.Container(
        content=ft.Text(
            "Nenhuma venda encontrada para o período e filtro selecionados.",
            color=ft.colors.GREY_500,
            size=16,
            italic=True,
        ),
        alignment=ft.alignment.center,
        expand=True,
        visible=True,
    )

    tabela_container = ft.Container(
        content=ft.Stack(
            [
                ft.Column(
                    [tabela_vendas],
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
                no_data_message,
            ],
            expand=True,
        ),
        padding=0,
        expand=True,
        border_radius=12,
        bgcolor=ft.colors.WHITE,
        shadow=ft.BoxShadow(
            color=ft.colors.with_opacity(0.05, ft.colors.BLACK),
            blur_radius=15,
            offset=ft.Offset(0, 5),
        ),
    )

    def carregar_vendas(e=None):
        try:
            nonlocal vendas_filtradas, caixa_session

            start_dt = start_date_picker.value
            end_dt = end_date_picker.value

            if not start_dt or not end_dt:
                page.snack_bar = ft.SnackBar(
                    ft.Text("Selecione as datas."), bgcolor=ft.colors.ORANGE
                )
                page.snack_bar.open = True
                page.update()
                return

            start_dt_obj = (
                start_dt.date() if isinstance(start_dt, datetime) else start_dt
            )
            end_dt_obj = end_dt.date() if isinstance(end_dt, datetime) else end_dt

            vendas = []
            if caixa_session:
                start_s = caixa_session.opening_time
                end_s = caixa_session.closing_time or datetime.now()
                vendas = pdv_core.buscar_vendas_por_intervalo(start_s, end_s)
            else:
                dt_ini = datetime.combine(start_dt_obj, time(0, 0))
                dt_fim = datetime.combine(end_dt_obj, time(23, 59, 59))
                vendas = pdv_core.buscar_vendas_por_intervalo(dt_ini, dt_fim)

            filtered = []
            total_periodo = 0.0
            lucro_periodo = 0.0

            for v in vendas:
                if v.get("status") == "ESTORNADA":
                    continue

                pagamento_venda = v.get("pagamento", "Desconhecido")
                filtro_pag = metodo_pagamento.value

                if filtro_pag != "Todos" and pagamento_venda != filtro_pag:
                    continue

                filtered.append(v)
                total_periodo += v.get("total", 0.0)
                lucro_periodo += v.get("total", 0.0) * 0.3

            vendas_filtradas = filtered

            tabela_vendas.rows.clear()

            for v in filtered:
                data_formatada = v["data"]
                pagamento = v["pagamento"]
                venda_id = str(v["id"])

                itens = v.get("itens", [])
                for item in itens:
                    nome_prod = item.get("produto", "?")
                    cod_barras = item.get("codigo_barras", "")
                    qtd = item.get("quantidade", 0)
                    preco_un = item.get("preco_unitario", 0.0)
                    valor_total_item = qtd * preco_un

                    produto_display = (
                        f"{cod_barras} - {nome_prod}" if cod_barras else nome_prod
                    )

                    cor_pag = ft.colors.BLUE_GREY_500
                    if pagamento == "Dinheiro":
                        cor_pag = ft.colors.GREEN_600
                    elif pagamento == "PIX":
                        cor_pag = ft.colors.TEAL_500
                    elif pagamento in ("Débito", "Crédito"):
                        cor_pag = ft.colors.BLUE_600

                    tabela_vendas.rows.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(
                                    ft.Text(
                                        produto_display,
                                        size=13,
                                        weight=ft.FontWeight.W_500,
                                    )
                                ),
                                ft.DataCell(ft.Text(data_formatada, size=13)),
                                ft.DataCell(
                                    ft.Container(
                                        content=ft.Text(
                                            pagamento,
                                            size=11,
                                            color="white",
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        bgcolor=cor_pag,
                                        padding=ft.padding.symmetric(
                                            horizontal=10, vertical=4
                                        ),
                                        border_radius=20,
                                    )
                                ),
                                ft.DataCell(ft.Text(str(qtd), size=13)),
                                ft.DataCell(
                                    ft.Text(
                                        f"R$ {valor_total_item:.2f}",
                                        size=13,
                                        weight=ft.FontWeight.BOLD,
                                    )
                                ),
                                ft.DataCell(
                                    ft.Text(venda_id, size=13, color=ft.colors.GREY_500)
                                ),
                            ]
                        )
                    )

            vendas_hoje_valor.value = f"R$ {total_periodo:.2f}"
            lucro_hoje_valor.value = f"R$ {lucro_periodo:.2f}"

            is_empty = not filtered

            tabela_vendas.visible = not is_empty
            no_data_message.visible = is_empty

            if is_empty:
                page.snack_bar = ft.SnackBar(
                    ft.Text("Nenhuma venda encontrada."), bgcolor=ft.colors.ORANGE
                )
                page.snack_bar.open = True

            page.update()

        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Erro ao carregar vendas: {e}"), bgcolor=ft.colors.RED_400
            )
            page.snack_bar.open = True
            page.update()

    def exportar_vendas(formato: str):
        try:
            if not vendas_filtradas:
                page.snack_bar = ft.SnackBar(
                    ft.Text("Não há vendas para exportar."),
                    bgcolor=ft.colors.ORANGE,
                )
                page.snack_bar.open = True
                page.update()
                return

            base_dir = Path("exports")
            base_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = base_dir / f"relatorio_vendas_{timestamp}.{formato}"

            generate_csv_file(
                filename,
                vendas_filtradas,
                columns=[
                    "id",
                    "data",
                    "pagamento",
                    "total",
                    "status",
                ],
            )

            if formato == "pdf":
                generate_pdf_file(filename, vendas_filtradas)

            page.snack_bar = ft.SnackBar(
                ft.Text(f"Relatório exportado para {filename}"),
                bgcolor=ft.colors.GREEN_400,
            )
            page.snack_bar.open = True
            page.update()

        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Erro ao exportar relatório: {e}"),
                bgcolor=ft.colors.RED_400,
            )
            page.snack_bar.open = True
            page.update()

    # Botão de filtro, posicionado junto ao filtro de data final
    aplicar_filtro_btn = ft.ElevatedButton(
        "Aplicar Filtro",
        icon=ft.icons.SEARCH,
        on_click=carregar_vendas,
    )

    # Agora que carregar_vendas existe, podemos montar o bloco de filtros
    filtros_content = ft.Container(
        content=ft.Row(
            [
                ft.Column(
                    [
                        ft.Text("Início", size=12, color=ft.colors.GREY_700),
                        criar_botao_data("Selecionar Início", start_date_picker),
                        inicio_label,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Column(
                    [
                        ft.Text("Fim", size=12, color=ft.colors.GREY_700),
                        ft.Row(
                            [
                                criar_botao_data("Selecionar Fim", end_date_picker),
                                aplicar_filtro_btn,
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=10,
                        ),
                        fim_label,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Column(
                    [
                        ft.Text("Pagamento", size=12, color=ft.colors.GREY_700),
                        metodo_pagamento,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=40,
            wrap=True,
        ),
        padding=20,
        bgcolor=ft.colors.GREY_50,
        border_radius=12,
    )

    export_buttons = ft.Row(
        [
            ft.ElevatedButton(
                "Exportar CSV",
                icon=ft.icons.TABLE_VIEW,
                on_click=lambda e: exportar_vendas("csv"),
            ),
            ft.ElevatedButton(
                "Exportar PDF",
                icon=ft.icons.PICTURE_AS_PDF,
                on_click=lambda e: exportar_vendas("pdf"),
            ),
        ],
        spacing=10,
    )

    main_content = ft.Column(
        [
            filtros_content,
            ft.Divider(height=20, color=ft.colors.TRANSPARENT),
            dashboard,
            ft.Divider(height=20, color=ft.colors.TRANSPARENT),
            tabela_container,
            ft.Divider(height=10, color=ft.colors.TRANSPARENT),
            export_buttons,
        ],
        spacing=10,
    )

    return ft.View(
        route="/gerente/relatorio_vendas",
        controls=[
            ft.AppBar(
                title=ft.Container(
                    content=ft.Text(
                        "Histórico de Itens Vendidos",
                        text_align=ft.TextAlign.CENTER,
                        size=20,
                        weight=ft.FontWeight.BOLD,
                    ),
                    alignment=ft.alignment.center,
                ),
                center_title=True,
                bgcolor=bg_color,
                leading=ft.IconButton(
                    icon=ft.icons.ARROW_BACK,
                    on_click=handle_back,
                ),
            ),
            ft.Container(
                content=main_content,
                padding=ft.padding.all(20),
                bgcolor=bg_color,
                expand=True,
            ),
        ],
        bgcolor=bg_color,
    )
