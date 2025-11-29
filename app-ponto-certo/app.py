# app.py: ponto de entrada principal do sistema Ponto Certo
#
# Este arquivo inicializa o Flet, configura o banco, gerencia rotas e views.
#
# Principais responsabilidades:
# - Inicializar o banco de dados e regras de negócio (PDVCore)
# - Gerenciar autenticação e sessão do usuário
# - Controlar navegação entre telas (views) usando rotas
# - Montar as views conforme o perfil/rota usando funções fábrica
# - Proteger rotas por perfil (gerente, caixa, estoque, etc.)

import flet as ft
from models.db_models import init_db, get_session
from core.sgv import PDVCore
from login.login_view import create_login_view
from gerencial.gerencial_view import create_gerente_view
from configuracoes.configuracoes_view import create_configuracoes_view
from estoque.view import create_estoque_view
from fornecedores.view import create_fornecedores_view
from financeiro.financeiro_view import create_financeiro_view
from vendas.view import create_relatorio_vendas_view
from produtos.relatorio_produtos import create_relatorio_produtos_view
from caixa import create_caixa_view

COLORS = {
    "background": "#FFFFFF",
    "primary": "#007BFF",
    "green": "#28A745",
    "red": "#DC3545",
    "orange": "#FFC107",
    "purple": "#6F42C1",
    "text": "#212121",
    "white": "#FFFFFF",
    "button_dark_hover": "#D32F2F",
    "button_dark_pressed": "#B71C1C",
    "teal": "#008080",
}


def main(page: ft.Page):
    page.title = "Ponto Certo"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = COLORS["background"]

    engine = init_db()
    session = get_session(engine)
    pdv_core = PDVCore(session)

    page.app_data = {"pdv_core": pdv_core}

    username_entry = ft.TextField(
        label="Usuário", value="admin", width=300, prefix_icon=ft.icons.PERSON
    )
    password_entry = ft.TextField(
        label="Senha",
        value="root",
        password=True,
        can_reveal_password=True,
        width=300,
        prefix_icon=ft.icons.LOCK,
    )

    def show_snackbar(message, color=COLORS["green"]):
        page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor=color)
        page.snack_bar.open = True
        page.update()

    def handle_login(e):
        user = username_entry.value
        pwd = password_entry.value
        authenticated_user = pdv_core.authenticate_user(user, pwd)
        if authenticated_user:
            page.session.set("user_id", authenticated_user.id)
            page.session.set("user_username", authenticated_user.username)
            page.session.set("role", authenticated_user.role)
            page.session.set(
                "user_display_name",
                authenticated_user.full_name or authenticated_user.username,
            )
            show_snackbar(
                f"Bem-vindo, {authenticated_user.full_name}!", COLORS["green"]
            )
            page.go(f"/{authenticated_user.role}")
        else:
            show_snackbar("Usuário ou senha inválidos!", COLORS["red"])

    def handle_logout(e=None):
        page.session.clear()
        page.go("/login")

    # ✅ FUNÇÃO SEPARADA para evitar lambda dentro do route_change
    def voltar_para_gerente(e):
        page.go("/gerente")

    def create_appbar(title_text):
        # title_text esperado: "Mercearia Ponto Certo - Nome do Usuário"
        try:
            if "-" in title_text:
                loja, usuario = [p.strip() for p in title_text.split("-", 1)]
            else:
                loja, usuario = title_text, ""

            title_column = ft.Column(
                [
                    ft.Text(
                        loja,
                        size=26,
                        weight="bold",
                        text_align="center",
                    ),
                    ft.Text(
                        usuario,
                        size=14,
                        text_align="center",
                    ),
                ],
                alignment="center",
                horizontal_alignment="center",
            )

            return ft.AppBar(
                title=title_column,
                center_title=True,
                bgcolor=ft.colors.GREY_100,
                actions=[
                    ft.IconButton(
                        icon=ft.icons.LOGOUT,
                        tooltip="Sair [ESC]",
                        on_click=handle_logout,
                    )
                ],
            )
        except Exception as e:
            print(f"❌ ERRO CRÍTICO em create_appbar: {e}")
            return ft.AppBar(title=ft.Text("ERRO"))

    def route_change(route):
        print(f"🔄 Rota alterada para: {page.route}")
        page.views.clear()

        if page.route in ["/", "/login"]:
            page.views.append(
                create_login_view(
                    page, username_entry, password_entry, handle_login, COLORS
                )
            )
        else:
            user = page.session.get("user_username")
            role = page.session.get("role")

            if not user:
                page.go("/login")
                return

            # ✅ PROTEÇÃO DE ROTA
            if page.route.startswith("/gerente") and role != "gerente":
                show_snackbar("Acesso negado! Apenas gerente.", COLORS["red"])
                page.go(f"/{role}")
                return

            # =============================
            # FÁBRICA DE VIEWS (funções fábrica)
            # =============================
            # Cada rota tem uma função que monta a tela correspondente.
            # Isso facilita a organização e evita duplicação de código.
            fabrica_de_views = {
                "/gerente": lambda: create_gerente_view(
                    page.session.get("user_display_name"), page, handle_logout
                ),
                "/estoque": lambda: create_estoque_view(
                    page=page, voltar_callback=voltar_para_gerente
                ),
                "/gerente/relatorio_produtos": lambda: create_relatorio_produtos_view(
                    page=page, pdv_core=pdv_core, handle_back=voltar_para_gerente
                ),
                "/gerente/relatorio_vendas": lambda: create_relatorio_vendas_view(
                    page=page, pdv_core=pdv_core, handle_back=voltar_para_gerente
                ),
                "/gerente/configuracoes": lambda: create_configuracoes_view(
                    page=page,
                    user_id_obj_do_gerente_logado=page.session.get("user_id"),
                    handle_back=voltar_para_gerente,
                ),
                "/gerente/fornecedores": lambda: create_fornecedores_view(
                    page=page, pdv_core=pdv_core, handle_back=voltar_para_gerente
                ),
                "/caixa": lambda: create_caixa_view(
                    page=page,
                    pdv_core=pdv_core,
                    handle_back=voltar_para_gerente,
                    current_user=page.session.get("user_display_name"),
                    appbar=create_appbar(
                        f"Mercearia Ponto Certo - {page.session.get('user_display_name')}"
                    ),
                ),
                "/financeiro": lambda: create_financeiro_view(
                    page=page,
                    pdv_core=pdv_core,
                    handle_back=voltar_para_gerente,
                    create_appbar=create_appbar,
                ),
            }

            # ✅ RESTRIÇÕES EXPLÍCITAS POR ROTA
            if page.route == "/caixa" and role not in ("caixa", "gerente"):
                show_snackbar(
                    "Acesso negado! Apenas caixas podem acessar o Caixa.", COLORS["red"]
                )
                page.go(f"/{role}")
                return

            if page.route == "/estoque" and role not in ("estoque", "gerente"):
                show_snackbar(
                    "Acesso negado! Apenas estoque pode acessar.", COLORS["red"]
                )
                page.go(f"/{role}")
                return

            # ✅ RESTRIÇÃO DE ACESSO PARA FINANCEIRO
            if page.route == "/financeiro" and role not in ["gerente", "estoque"]:
                show_snackbar("Acesso negado a Financeiro.", COLORS["red"])
                page.go(f"/{role}")
                return

            # =============================
            # Fim da fábrica de views
            # =============================

            # Carrega a view da rota usando a função fábrica
            if page.route in fabrica_de_views:
                try:
                    view = fabrica_de_views[page.route]()
                    if view is None:
                        print(f"❌ Função fábrica retornou None para {page.route}")
                        view = ft.View(
                            page.route,
                            [ft.Text(f"Erro: View {page.route} é None")],
                            appbar=create_appbar(
                                f"Mercearia Ponto Certo - {page.session.get('user_display_name')}"
                            ),
                        )
                    page.views.append(view)
                except Exception as ex:
                    import traceback

                    print(f"❌ Exceção ao criar view {page.route}: {ex}")
                    print(traceback.format_exc())
                    page.views.append(
                        ft.View(
                            page.route,
                            [
                                ft.Text(
                                    f"Erro ao carregar view:",
                                    color=ft.Colors.RED,
                                    weight="bold",
                                ),
                                ft.Text(f"{ex}", color=ft.Colors.RED),
                            ],
                            appbar=create_appbar(
                                f"Mercearia Ponto Certo - {page.session.get('user_display_name')}"
                            ),
                        )
                    )

            else:
                # Rota não encontrada
                page.views.append(
                    ft.View(
                        page.route,
                        [
                            ft.Text(
                                f"Rota '{page.route}' não encontrada",
                                color=ft.Colors.RED,
                            )
                        ],
                        appbar=create_appbar(
                            f"Mercearia Ponto Certo - {page.session.get('user_display_name')}"
                        ),
                    )
                )

        # ✅ VERIFICAÇÃO FINAL antes de update
        if not page.views or page.views[-1] is None:
            print("❌ ERRO CRÍTICO: Nenhuma view válida para exibir!")
            page.views.clear()
            page.views.append(
                ft.View(
                    "/",
                    [ft.Text("Erro crítico: Nenhuma view válida", color=ft.Colors.RED)],
                )
            )

        page.update()

    def handle_keyboard(e: ft.KeyboardEvent):
        # Atalhos globais de ESC para navegação/logout
        if e.key == "Escape":
            role = page.session.get("role")
            username = page.session.get("user_username")

            # Gerente: sempre volta para o painel gerencial, nunca para login
            if role == "gerente":
                if page.route != "/gerente":
                    voltar_para_gerente(None)

            # Caixa1 e Auxiliar de Estoque: ESC faz logout e volta para login
            elif username in ("Caixa1", "Auxiliar de Estoque"):
                if page.route not in ["/login", "/"]:
                    handle_logout()

            # Demais perfis: mantém comportamento padrão anterior
            else:
                if (
                    page.route.startswith("/gerente/")
                    or page.route == "/caixa"
                    or page.route == "/estoque"
                ):
                    voltar_para_gerente(None)
                elif page.route not in ["/login", "/"]:
                    handle_logout()

            return

        # Atalhos específicos da tela do caixa (F1–F12, etc.)
        if page.route == "/caixa" and page.views:
            current_view = page.views[-1]
            # A view do caixa expõe um handler interno chamado handle_keyboard_shortcuts
            handler = getattr(current_view, "handle_keyboard_shortcuts", None)
            if callable(handler):
                handler(e)
                return

    page.on_keyboard_event = handle_keyboard
    page.on_route_change = route_change
    page.go(page.route if page.route else "/")


ft.app(
    target=main, assets_dir="assets"
)  # , view=ft.AppView.WEB_BROWSER) ---run in browser
