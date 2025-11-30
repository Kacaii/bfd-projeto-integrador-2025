import flet as ft
from datetime import datetime
from pathlib import Path
from utils.export_utils import generate_csv_file, generate_pdf_file

# Modern Color Palette - Dark Mode Friendly
COLORS = {
    "primary": ft.LinearGradient(
        begin=ft.alignment.top_left,
        end=ft.alignment.bottom_right,
        colors=["#6C5CE7", "#4A90E2"],
    ),
    "primary_solid": "#6C5CE7",
    "background": "#F8F9FA",
    "surface": "#FFFFFF",
    "text_primary": "#2D3436",
    "text_secondary": "#636E72",
    "success": "#00B894",
    "warning": "#FDCB6E",
    "danger": "#FF7675",
    "info": "#74B9FF",
    "border": "#DFE6E9",
    "hover": "#F1F2F6",
}

# Modern Typography
TYPOGRAPHY = {
    "h1": {"size": 28, "weight": ft.FontWeight.BOLD},
    "h2": {"size": 20, "weight": ft.FontWeight.BOLD},
    "h3": {"size": 16, "weight": ft.FontWeight.W_600},
    "body": {"size": 14, "weight": ft.FontWeight.NORMAL},
    "caption": {"size": 12, "weight": ft.FontWeight.W_500},
}


def show_snackbar(page: ft.Page, message: str, color=COLORS["success"]):
    """Modern snackbar with icon and better styling"""
    page.snack_bar = ft.SnackBar(
        content=ft.Row(
            [
                ft.Icon(ft.icons.CHECK_CIRCLE, color=ft.colors.WHITE, size=20),
                ft.Text(message, color=ft.colors.WHITE, weight=ft.FontWeight.W_500),
            ]
        ),
        bgcolor=color,
        behavior=ft.SnackBarBehavior.FLOATING,
        margin=10,
        duration=3000,
    )
    page.snack_bar.open = True
    page.update()


def format_brl(val: float) -> str:
    """Format currency with Brazilian Real"""
    return f"R$ {val:,.2f}".replace(".", "#").replace(",", ".").replace("#", ",")


def create_status_chip(value: float, is_percentage: bool = False) -> ft.Container:
    """Create colored status chip for values"""
    color = COLORS["success"] if value > 0 else COLORS["danger"]
    if is_percentage and value > 30:
        color = COLORS["success"]
    elif is_percentage and value < 10:
        color = COLORS["warning"]

    return ft.Container(
        content=ft.Text(
            f"{value:.2f}%" if is_percentage else format_brl(value),
            size=12,
            weight=ft.FontWeight.W_600,
            color=color,
        ),
        bgcolor=ft.colors.with_opacity(0.2, color),
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        border_radius=20,
    )


def create_modern_button(
    text: str,
    icon: str,
    on_click,
    style: str = "primary",
    expand: bool = False,
) -> ft.Container:
    """Create modern styled button"""
    color_map = {
        "primary": COLORS["primary_solid"],
        "secondary": COLORS["text_secondary"],
        "success": COLORS["success"],
    }

    return ft.Container(
        content=ft.ElevatedButton(
            content=ft.Row(
                [ft.Icon(icon, size=18), ft.Text(text, size=14)],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            ),
            on_click=on_click,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=color_map[style],
                elevation=2,
                overlay_color=ft.colors.with_opacity(0.1, ft.colors.WHITE),
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.padding.symmetric(horizontal=16, vertical=12),
            ),
            expand=expand,
        ),
        animate=ft.animation.Animation(200, ft.AnimationCurve.EASE_OUT),
    )


def create_relatorio_produtos_view(page: ft.Page, pdv_core, handle_back):
    # Modern refs with better naming
    chart_ref = ft.Ref[ft.BarChart]()
    loading_ring = ft.Ref[ft.ProgressRing]()
    data_table = ft.Ref[ft.DataTable]()

    def create_summary_card(label: str, icon: str, color: str) -> ft.Container:
        """Create modern summary card"""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(icon, size=24, color=color),
                            ft.Text(
                                label,
                                **TYPOGRAPHY["caption"],
                                color=COLORS["text_secondary"],
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Text(
                        "R$ 0,00", **TYPOGRAPHY["h2"], color=COLORS["text_primary"]
                    ),
                ]
            ),
            padding=16,
            border_radius=16,
            bgcolor=COLORS["surface"],
            border=ft.border.all(1, COLORS["border"]),
            shadow=ft.BoxShadow(
                color=ft.colors.with_opacity(0.1, ft.colors.BLACK),
                blur_radius=8,
                offset=ft.Offset(0, 2),
            ),
            animate_scale=ft.animation.Animation(200, ft.AnimationCurve.EASE_OUT),
        )

    summary_cards = {
        "custo": create_summary_card("Total Custo", "attach_money", COLORS["warning"]),
        "venda": create_summary_card("Total Venda", "trending_up", COLORS["info"]),
        "lucro": create_summary_card(
            "Total Lucro", "account_balance", COLORS["success"]
        ),
    }

    def get_bar_color(prod, total_lucro):
        """Determine bar color based on profit margin"""
        if total_lucro < 0:
            return COLORS["danger"]
        if prod["venda"] > 0:
            margin = (prod["margem"] / prod["venda"]) * 100
            if margin > 30:
                return COLORS["success"]
            elif margin > 15:
                return COLORS["warning"]
        return COLORS["primary_solid"]

    def create_bar_chart_group(x, value, name, color):
        """Create animated bar chart group"""
        return ft.BarChartGroup(
            x=x,
            bar_rods=[
                ft.BarChartRod(
                    from_y=0,
                    to_y=value,
                    width=20,
                    color=color,
                    gradient=ft.LinearGradient(
                        begin=ft.alignment.bottom_center,
                        end=ft.alignment.top_center,
                        colors=[ft.colors.with_opacity(0.5, color), color],
                    ),
                    tooltip=f"{name}\nLucro: {format_brl(value)}",
                    border_radius=8,
                )
            ],
        )

    def create_chart_label(value, label):
        """Create rotated chart label"""
        return ft.ChartAxisLabel(
            value=value,
            label=ft.Container(
                content=ft.Text(label[:12], size=11, color=COLORS["text_secondary"]),
                padding=5,
                rotate=ft.Rotate(angle=-0.5),
            ),
        )

    def update_summary_cards(totals):
        """Update summary cards with animation"""
        for key, card in summary_cards.items():
            value_label = card.content.controls[1]
            value_label.value = format_brl(totals[key])
            value_label.update()

    def show_empty_state(message: str):
        """Show empty state illustration"""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Icon(
                        ft.icons.INVENTORY_2_OUTLINED,
                        size=64,
                        color=COLORS["text_secondary"],
                    ),
                    ft.Text(
                        message, **TYPOGRAPHY["h3"], color=COLORS["text_secondary"]
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            alignment=ft.alignment.center,
            expand=True,
        )

    def load_relatorio_produtos():
        """Load products report with modern loading state"""
        if not loading_ring.current:
            page.run_task(lambda: (page.sleep(100), load_relatorio_produtos()))
            return

        try:
            loading_ring.current.visible = True
            loading_ring.current.update()

            pdv_core = page.app_data.get("pdv_core")
            if not pdv_core:
                raise RuntimeError("Sistema não iniciado")

            todos_produtos = pdv_core.gerar_relatorio_produtos()
            produtos = [p for p in todos_produtos if p["estoque"] > 0]

            if not produtos:
                show_snackbar(
                    page, "Nenhum produto em estoque encontrado.", ft.colors.ORANGE_700
                )
                return

            if data_table.current:
                data_table.current.rows.clear()

            chart_bars = []
            chart_labels = []
            totals = {"custo": 0.0, "venda": 0.0, "lucro": 0.0}

            produtos_ordenados = sorted(
                produtos, key=lambda p: p["margem"] * p["estoque"], reverse=True
            )

            for idx, prod in enumerate(produtos_ordenados):
                total_custo = prod["custo"] * prod["estoque"]
                total_venda = prod["venda"] * prod["estoque"]
                total_lucro = prod["margem"] * prod["estoque"]

                totals["custo"] += total_custo
                totals["venda"] += total_venda
                totals["lucro"] += total_lucro

                row = ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(prod["id"]), **TYPOGRAPHY["body"])),
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.icons.INVENTORY_2_OUTLINED,
                                        size=16,
                                        color=COLORS["primary_solid"],
                                    ),
                                    ft.Text(
                                        prod["nome"],
                                        **TYPOGRAPHY["body"],
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                ],
                                spacing=8,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(str(prod["estoque"]), **TYPOGRAPHY["body"])
                        ),
                        ft.DataCell(create_status_chip(total_custo, False)),
                        ft.DataCell(create_status_chip(total_venda, False)),
                        ft.DataCell(
                            create_status_chip(
                                (prod["margem"] / prod["venda"] * 100)
                                if prod["venda"]
                                else 0,
                                True,
                            )
                        ),
                        ft.DataCell(create_status_chip(total_lucro, False)),
                    ],
                    color=ft.colors.with_opacity(0.05, COLORS["primary_solid"])
                    if idx % 2 == 0
                    else None,
                )

                if data_table.current:
                    data_table.current.rows.append(row)

                bar_color = get_bar_color(prod, total_lucro)
                chart_bars.append(
                    create_bar_chart_group(idx, total_lucro, prod["nome"], bar_color)
                )
                chart_labels.append(create_chart_label(idx, prod["nome"]))

            update_summary_cards(totals)

            if chart_ref.current:
                chart_ref.current.bar_groups = chart_bars
                chart_ref.current.bottom_axis.labels = chart_labels
                chart_ref.current.update()

            if data_table.current:
                data_table.current.update()

            show_snackbar(page, f"✅ {len(produtos)} produtos em estoque carregados")

        except Exception as ex:
            show_snackbar(page, f"Erro: {str(ex)}", COLORS["danger"])
        finally:
            loading_ring.current.visible = False
            loading_ring.current.update()

    def export_relatorio(export_type: str):
        """Export report with modern feedback"""
        try:
            pdv_core = page.app_data.get("pdv_core")
            if not pdv_core:
                raise RuntimeError("Sistema não iniciado")

            todos_produtos = pdv_core.gerar_relatorio_produtos()
            produtos = [p for p in todos_produtos if p["estoque"] > 0]

            if not produtos:
                show_snackbar(
                    page, "Nenhum dado em estoque para exportar", COLORS["warning"]
                )
                return

            headers = [
                "ID",
                "Produto",
                "Estoque",
                "Custo Unit.",
                "Venda Unit.",
                "Margem Lucro",
                "Total Custo",
                "Total Venda",
                "Total Lucro",
            ]
            data = []

            for prod in produtos:
                data.append(
                    [
                        prod["id"],
                        prod["nome"],
                        prod["estoque"],
                        prod["custo"],
                        prod["venda"],
                        prod["margem"],
                        prod["custo"] * prod["estoque"],
                        prod["venda"] * prod["estoque"],
                        prod["margem"] * prod["estoque"],
                    ]
                )

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            caminho = (
                generate_csv_file(headers, data, f"relatorio_produtos_{timestamp}")
                if export_type == "csv"
                else generate_pdf_file(
                    headers,
                    data,
                    f"relatorio_produtos_{timestamp}",
                    "Relatório de Rentabilidade",
                )
            )

            show_snackbar(page, f"✅ Exportado: {Path(caminho).name}")

        except Exception as ex:
            show_snackbar(page, f"Erro ao exportar: {str(ex)}", COLORS["danger"])

    def create_sortable_header(text: str, sort_key: str) -> ft.Container:
        """Create clickable sortable header"""
        return ft.Container(
            content=ft.Row(
                [
                    ft.Text(
                        text, **TYPOGRAPHY["caption"], color=COLORS["text_primary"]
                    ),
                    ft.Icon(
                        ft.icons.UNFOLD_MORE,
                        size=16,
                        color=COLORS["text_secondary"],
                    ),
                ],
                spacing=4,
            ),
            padding=ft.padding.only(right=12),
            on_click=lambda e: handle_sort(sort_key),
        )

    def handle_sort(key: str):
        """Handle column sorting"""
        pass

    app_bar = ft.AppBar(
        leading=ft.IconButton(
            icon=ft.icons.ARROW_BACK,
            tooltip="Voltar",
            on_click=lambda _: page.go("/gerente"),
            icon_color=ft.colors.BLACK,
        ),
        title=ft.Container(
            content=ft.Text(
                "Relatórios de Produtos",
                **TYPOGRAPHY["h2"],
                text_align=ft.TextAlign.CENTER,
            ),
            alignment=ft.alignment.center,
        ),
        center_title=True,
        bgcolor=COLORS["surface"],
        elevation=2,
    )

    relatorio_dt = ft.DataTable(
        ref=data_table,
        columns=[
            ft.DataColumn(create_sortable_header("ID", "id")),
            ft.DataColumn(create_sortable_header("Produto", "nome")),
            ft.DataColumn(create_sortable_header("Estoque", "estoque")),
            ft.DataColumn(create_sortable_header("Custo Unit.", "custo")),
            ft.DataColumn(create_sortable_header("Venda Unit.", "venda")),
            ft.DataColumn(create_sortable_header("Margem %", "margem")),
            ft.DataColumn(create_sortable_header("Total Lucro", "total_lucro")),
        ],
        rows=[],
        expand=True,
        heading_row_color=ft.colors.with_opacity(0.05, COLORS["primary_solid"]),
        data_row_color={"hovered": COLORS["hover"]},
        column_spacing=20,
    )

    view = ft.View(
        "/gerente/relatorio_produtos",
        [
            app_bar,
            ft.Container(
                content=ft.ProgressRing(
                    ref=loading_ring,
                    width=40,
                    height=40,
                    color=COLORS["primary_solid"],
                ),
                alignment=ft.alignment.center,
                visible=False,
            ),
            ft.Container(
                content=ft.ResponsiveRow(
                    [
                        ft.Column(col=4, controls=[card])
                        for card in summary_cards.values()
                    ],
                    spacing=16,
                ),
                padding=ft.padding.only(bottom=24),
            ),
            ft.Container(
                content=ft.ResponsiveRow(
                    [
                        ft.Column(
                            col={"md": 12, "lg": 8},
                            controls=[
                                ft.Container(
                                    content=ft.Column(
                                        [
                                            ft.Row(
                                                [
                                                    ft.Text(
                                                        "Produtos em Estoque",
                                                        **TYPOGRAPHY["h2"],
                                                    ),
                                                    ft.Container(
                                                        content=ft.Text(
                                                            "Live",
                                                            size=12,
                                                            weight=ft.FontWeight.W_600,
                                                            color=ft.colors.WHITE,
                                                        ),
                                                        bgcolor=COLORS["success"],
                                                        padding=ft.padding.symmetric(
                                                            horizontal=8,
                                                            vertical=4,
                                                        ),
                                                        border_radius=12,
                                                    ),
                                                ],
                                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                            ),
                                            ft.Container(
                                                content=ft.Column(
                                                    [relatorio_dt],
                                                    scroll=ft.ScrollMode.AUTO,
                                                ),
                                                border=ft.border.all(
                                                    1, COLORS["border"]
                                                ),
                                                border_radius=16,
                                                bgcolor=COLORS["surface"],
                                                padding=0,
                                                expand=True,
                                                shadow=ft.BoxShadow(
                                                    color=ft.colors.with_opacity(
                                                        0.05, ft.colors.BLACK
                                                    ),
                                                    blur_radius=10,
                                                    offset=ft.Offset(0, 4),
                                                ),
                                            ),
                                        ]
                                    ),
                                    expand=True,
                                )
                            ],
                        ),
                        ft.Column(
                            col={"md": 12, "lg": 4},
                            controls=[
                                ft.Card(
                                    elevation=0,
                                    content=ft.Container(
                                        content=ft.Column(
                                            [
                                                ft.Text(
                                                    "Lucro por Produto",
                                                    **TYPOGRAPHY["h2"],
                                                ),
                                                ft.Container(
                                                    content=ft.BarChart(
                                                        ref=chart_ref,
                                                        bar_groups=[],
                                                        bottom_axis=ft.ChartAxis(
                                                            labels=[],
                                                            labels_size=40,
                                                        ),
                                                        left_axis=ft.ChartAxis(
                                                            title=ft.Text(
                                                                "Valor (R$)",
                                                                **TYPOGRAPHY["caption"],
                                                            ),
                                                            labels_size=60,
                                                        ),
                                                        tooltip_bgcolor=ft.colors.with_opacity(
                                                            0.9,
                                                            COLORS["text_primary"],
                                                        ),
                                                        border=ft.border.all(
                                                            0, ft.colors.TRANSPARENT
                                                        ),
                                                        expand=True,
                                                    ),
                                                    height=400,
                                                    border_radius=16,
                                                    border=ft.border.all(
                                                        1, COLORS["border"]
                                                    ),
                                                    bgcolor=COLORS["surface"],
                                                    padding=10,
                                                ),
                                            ],
                                            spacing=16,
                                        ),
                                        padding=16,
                                    ),
                                    surface_tint_color=COLORS["surface"],
                                )
                            ],
                        ),
                    ],
                    spacing=24,
                ),
                expand=True,
            ),
            ft.Container(
                content=ft.Row(
                    [
                        create_modern_button(
                            "Atualizar",
                            ft.icons.REFRESH,
                            lambda _: load_relatorio_produtos(),
                            "primary",
                        ),
                        ft.VerticalDivider(),
                        create_modern_button(
                            "CSV",
                            ft.icons.DOWNLOAD,
                            lambda _: export_relatorio("csv"),
                            "secondary",
                        ),
                        create_modern_button(
                            "PDF",
                            ft.icons.PICTURE_AS_PDF,
                            lambda _: export_relatorio("pdf"),
                            "secondary",
                        ),
                    ],
                    spacing=12,
                ),
                padding=ft.padding.only(top=24),
            ),
        ],
        padding=ft.padding.all(24),
        bgcolor=COLORS["background"],
        scroll=ft.ScrollMode.AUTO,
    )

    def on_view_did_mount(e):
        print("📊 View montada - Iniciando carga")
        load_relatorio_produtos()

    view.on_view_did_mount = on_view_did_mount
    return view
