import flet as ft


def create_gerente_view(user_display_name, page, handle_logout):
    COLORS = {
        "text": "#131111",  # Cor preta (texto padrão)
        "white": "#FFFFFF",
        "primary": "#007BFF",
        "green": "#28A745",
        "red": "#DC3545",
        "orange": "#FFC107",
        "teal": "#66119E",
        "background": ft.colors.GREY_50,
    }

    # --- Helper: Função para criar os botões da barra de ferramentas ---
    def create_toolbar_button(icon_name, text, on_click_handler, color=COLORS["text"]):
        """Cria um botão padronizado para a toolbar, com ícone e texto."""
        return ft.TextButton(
            content=ft.Column(
                [
                    ft.Icon(icon_name, size=50, color=color),
                    ft.Text(text, size=15, color=color, weight=ft.FontWeight.W_500),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            ),
            on_click=on_click_handler,
            height=100,
            width=130,
            style=ft.ButtonStyle(
                bgcolor=ft.colors.TRANSPARENT,
                overlay_color=ft.colors.GREY_300,
                shape=ft.RoundedRectangleBorder(radius=6),
            ),
        )

    # --- Cria a Barra de Ferramentas (Toolbar) ---
    toolbar = ft.Container(
        content=ft.Row(
            [
                ft.Row(
                    [
                        create_toolbar_button(
                            ft.icons.INVENTORY,
                            "Estoque",
                            lambda _: page.go("/estoque"),
                            color=COLORS["orange"],
                        ),
                        create_toolbar_button(
                            ft.icons.RECEIPT,
                            "Vendas",
                            lambda _: page.go("/gerente/relatorio_vendas"),
                            color=COLORS["primary"],
                        ),
                        create_toolbar_button(
                            ft.icons.ACCOUNT_BALANCE_WALLET,
                            "Financeiro",
                            lambda _: page.go("/financeiro"),
                            color=COLORS["green"],
                        ),
                        create_toolbar_button(
                            ft.icons.POINT_OF_SALE,
                            "Caixa",
                            lambda _: page.go("/caixa"),
                            color=COLORS["red"],
                        ),
                        create_toolbar_button(
                            ft.icons.ASSIGNMENT,
                            "Rel. Produtos",
                            lambda _: page.go("/gerente/relatorio_produtos"),
                            color=COLORS["teal"],
                        ),
                        create_toolbar_button(
                            ft.icons.LOCAL_SHIPPING,
                            "Fornecedores",
                            lambda _: page.go("/gerente/fornecedores"),
                            color=COLORS["text"],
                        ),
                    ],
                    wrap=True,
                    spacing=10,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=ft.colors.GREY_200,
        padding=ft.padding.symmetric(horizontal=15, vertical=10),
        border=ft.border.only(bottom=ft.BorderSide(1, ft.colors.GREY_300)),
    )

    # --- Cria o Conteúdo Principal (Logo) ---
    main_content = ft.Container(
        content=ft.Column(
            [
                ft.Image(
                    src="assets/Mercadinho_Ponto_Certo.png",
                    width=400,
                    height=400,
                    fit=ft.ImageFit.CONTAIN,
                ),
                ft.Text(
                    "Qualidade e confiança em cada compra.",
                    size=20,
                    color=COLORS["text"],
                    weight=ft.FontWeight.W_500,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10,
        ),
        expand=True,
        alignment=ft.alignment.center,
        padding=20,
    )

    # --- Cria a AppBar específica para o Gerente ---
    app_bar_gerente = ft.AppBar(
        title=ft.Text("PAINEL GERENCIAL", weight=ft.FontWeight.BOLD),
        bgcolor=ft.colors.GREY_100,
        actions=[
            ft.Row(
                [
                    ft.Icon(ft.icons.PERSON, color=COLORS["text"]),
                    ft.Text(
                        user_display_name,
                        style=ft.TextThemeStyle.TITLE_MEDIUM,
                        color=COLORS["text"],
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=5,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.IconButton(
                icon=ft.icons.SETTINGS,
                tooltip="Configurações",
                on_click=lambda _: page.go("/gerente/configuracoes"),
                icon_color=COLORS["text"],
            ),
            ft.FilledButton(
                "Sair", on_click=lambda e: handle_logout(e), icon=ft.icons.LOGOUT
            ),
        ],
    )

    view = ft.View(
        "/gerente",
        [
            app_bar_gerente,
            toolbar,
            main_content,
        ],
        padding=0,
        bgcolor=COLORS["background"],
    )

    def on_view_did_mount():
        page.bgcolor = COLORS["background"]

    view.on_view_did_mount = on_view_did_mount
    return view
