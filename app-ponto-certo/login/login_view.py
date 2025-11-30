import flet as ft


def create_login_view(page, username_entry, password_entry, handle_login, COLORS):
    # Imagem animada (GIF) sempre visível
    animation = ft.Image(
        src="assets/animacao.gif", width=80, height=80, fit=ft.ImageFit.CONTAIN
    )

    # Logo
    logo = ft.Image(
        src="Mercadinho_Ponto_Certo.png", width=250, height=250, fit=ft.ImageFit.CONTAIN
    )

    # Slogan
    slogan = ft.Text(
        "Qualidade e confiança em cada compra.",
        size=16,
        weight=ft.FontWeight.BOLD,
        color=COLORS["text"],
    )

    # Botão Entrar
    btn_entrar = ft.Container(
        content=ft.TextButton(
            "ENTRAR",
            width=200,
            height=40,
            on_click=handle_login,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=COLORS["red"],
                shape=ft.RoundedRectangleBorder(radius=6),
                overlay_color="#B71C1C",
            ),
        ),
        alignment=ft.alignment.center,
    )

    # Lista de usuários (caixa / estoque)
    user_dropdown = None

    try:
        pdv_core = page.app_data.get("pdv_core")
        if pdv_core:
            # Filtra apenas Gerente, Caixa 1 e Auxiliar de Estoque
            users = []
            for u in pdv_core.get_all_users():
                if getattr(u, "username", "") == "admin":
                    users.append((u, "Gerente"))
                elif getattr(u, "username", "") == "user_caixa":
                    users.append((u, "Caixa 1"))
                elif getattr(u, "role", "") == "estoque":
                    users.append((u, "Auxiliar de Estoque"))

            options = [ft.dropdown.Option(str(u.id), label) for u, label in users]

            def on_user_select(e):
                try:
                    uid = e.control.value
                    if not uid:
                        return
                    user = pdv_core.get_user_by_id(int(uid))
                    if not user:
                        return

                    # Preencher username sempre
                    username_entry.value = user.username

                    # Gerente e Auxiliar de Estoque: campo usuário desabilitado, só digita senha
                    if (
                        getattr(user, "username", "") == "admin"
                        or getattr(user, "role", "") == "estoque"
                    ):
                        username_entry.disabled = True
                        password_entry.disabled = False
                        try:
                            password_entry.can_reveal_password = True
                        except Exception:
                            pass
                        password_entry.value = ""
                    # Caixa 1: login automático, ambos desabilitados
                    elif getattr(user, "username", "") == "user_caixa":
                        username_entry.disabled = True
                        password_entry.disabled = True
                        try:
                            password_entry.can_reveal_password = False
                        except Exception:
                            pass
                        stored = getattr(user, "password", "") or ""
                        if not (
                            stored.startswith("$2")
                            or stored.startswith("$pbkdf2-sha256$")
                        ):
                            password_entry.value = stored
                        else:
                            password_entry.value = ""
                        if password_entry.value:
                            try:
                                page.run_task(
                                    lambda: (page.sleep(100), handle_login(None))
                                )
                            except Exception:
                                pass
                    else:
                        username_entry.disabled = False
                        password_entry.disabled = False
                        try:
                            password_entry.can_reveal_password = True
                        except Exception:
                            pass
                        password_entry.value = ""

                    username_entry.update()
                    password_entry.update()
                except Exception:
                    pass

            user_dropdown = ft.Dropdown(
                label="Entrar como",
                options=options,
                width=350,
                on_change=on_user_select,
            )

            # Seleciona automaticamente Caixa 1 se existir
            first_caixa = next((u for u, label in users if label == "Caixa 1"), None)
            if first_caixa:
                user_dropdown.value = str(first_caixa.id)
                try:
                    user = first_caixa
                    username_entry.value = user.username
                    username_entry.disabled = True
                    password_entry.disabled = True
                    try:
                        password_entry.can_reveal_password = False
                    except Exception:
                        pass
                    stored = getattr(user, "password", "") or ""
                    if not (
                        stored.startswith("$2") or stored.startswith("$pbkdf2-sha256$")
                    ):
                        password_entry.value = stored
                    else:
                        password_entry.value = ""
                    if password_entry.value:
                        try:
                            page.run_task(lambda: (page.sleep(100), handle_login(None)))
                        except Exception:
                            pass
                except Exception:
                    pass
    except Exception:
        user_dropdown = None

    # Submeter ao pressionar Enter (on_submit) nos campos
    try:
        username_entry.on_submit = handle_login
        password_entry.on_submit = handle_login
    except Exception:
        pass

    # Coluna central
    login_column = ft.Column(
        [
            animation,
            ft.Container(height=10),
            logo,
            ft.Container(height=20),
            slogan,
            ft.Container(height=30),
            user_dropdown if user_dropdown is not None else ft.Container(),
            username_entry,
            password_entry,
            ft.Container(height=20),
            btn_entrar,
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Fundo com rolagem apenas na coluna central
    login_container = ft.Container(
        content=ft.Column(
            [
                ft.Container(height=40),  # margem superior
                login_column,
                ft.Container(height=40),  # margem inferior
            ],
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.START,
        ),
        expand=True,
        bgcolor=COLORS["background"],
        padding=ft.padding.all(16),
    )

    return ft.View(
        "/login",
        [login_container],
        padding=0,
        bgcolor=COLORS["background"],
    )
