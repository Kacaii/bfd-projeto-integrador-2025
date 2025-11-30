import flet as ft


COLORS = {
    "primary": ft.colors.BLUE_600,
    "white": ft.colors.WHITE,
    "background": ft.colors.GREY_100,
}


def show_snackbar(page: ft.Page, message: str, color: str):
    page.snack_bar = ft.SnackBar(
        ft.Text(message, color=ft.colors.BLACK), bgcolor=color, duration=3000
    )
    page.snack_bar.open = True
    page.update()


def create_configuracoes_view(
    page: ft.Page, user_id_obj_do_gerente_logado, handle_back
):
    print("🔧 Iniciando view de configurações...")

    # CRIAR REFERÊNCIAS
    user_dropdown_ref = ft.Ref[ft.Dropdown]()
    full_name_ref = ft.Ref[ft.TextField]()
    password_ref = ft.Ref[ft.TextField]()
    save_button_ref = ft.Ref[ft.FilledButton]()
    delete_button_ref = ft.Ref[ft.ElevatedButton]()
    printer_name_ref = ft.Ref[ft.TextField]()
    paper_size_ref = ft.Ref[ft.Dropdown]()

    # FUNÇÃO PARA CARREGAR USUÁRIOS
    def load_users():
        try:
            pdv_core = page.app_data.get("pdv_core")
            if not pdv_core:
                print("❌ pdv_core não encontrado")
                return []

            users = pdv_core.get_all_users()
            editable = [
                u
                for u in users
                if (u.get("role") if isinstance(u, dict) else getattr(u, "role", None))
                in ("gerente", "caixa", "estoque")
            ]
            print(f"✅ {len(editable)} usuários carregados")
            return editable
        except Exception as e:
            print(f"❌ Erro ao carregar usuários: {e}")
            return []

    # FUNÇÃO PARA POPULAR DROPDOWN (COM RETRY)
    def populate_dropdown(users, selected_id=None, attempt=0):
        max_attempts = 5

        if not user_dropdown_ref.current:
            if attempt < max_attempts:
                print(f"⏳ Dropdown não pronto, tentativa {attempt + 1}/{max_attempts}")
                page.run_task(
                    lambda: (
                        page.sleep(200),
                        populate_dropdown(users, selected_id, attempt + 1),
                    )
                )
            else:
                print("❌ Falhou após muitas tentativas")
            return

        try:
            # Limpar opções existentes
            user_dropdown_ref.current.options.clear()

            # Adicionar opções
            for u in users:
                user_id = str(u.get("id") if isinstance(u, dict) else u.id)
                user_name = (
                    u.get("full_name") or u.get("username")
                    if isinstance(u, dict)
                    else (u.full_name or u.username)
                )
                user_role = (u.get("role") if isinstance(u, dict) else u.role).title()

                # ft.dropdown.Option(key, text) -> primeiro argumento é a chave/valor,
                # segundo é o texto visível.
                user_dropdown_ref.current.options.append(
                    ft.dropdown.Option(user_id, f"{user_name} ({user_role})")
                )

            # Set valor selecionado
            user_dropdown_ref.current.value = str(selected_id) if selected_id else None

            # FORÇAR ATUALIZAÇÃO
            user_dropdown_ref.current.update()
            print(f"✅ Dropdown populado com {len(users)} usuários")
        except Exception as e:
            print(f"❌ Erro ao popular: {e}")

    # --- Construir opções iniciais imediatamente para evitar dropdown vazio/inacessível ---
    try:
        _initial_users = load_users()
        initial_options = []
        for u in _initial_users:
            uid = str(u.get("id") if isinstance(u, dict) else u.id)
            uname = (
                u.get("full_name") or u.get("username")
                if isinstance(u, dict)
                else (u.full_name or u.username)
            )
            urole = (u.get("role") if isinstance(u, dict) else u.role).title()
            initial_options.append(ft.dropdown.Option(uid, f"{uname} ({urole})"))
    except Exception:
        initial_options = []

    # FUNÇÃO PARA RESETAR CAMPOS
    def reset_user_fields():
        try:
            if not all(
                [full_name_ref.current, password_ref.current, save_button_ref.current]
            ):
                return

            full_name_ref.current.value = ""
            password_ref.current.value = ""
            full_name_ref.current.disabled = True
            password_ref.current.disabled = True
            save_button_ref.current.disabled = True
            if delete_button_ref.current:
                delete_button_ref.current.disabled = True

            full_name_ref.current.update()
            password_ref.current.update()
            save_button_ref.current.update()
            print("🔄 Campos resetados")
        except Exception as e:
            print(f"❌ Erro ao resetar: {e}")

    # FUNÇÃO PARA HABILITAR CAMPOS
    def enable_user_fields(user_data):
        try:
            if not all(
                [full_name_ref.current, password_ref.current, save_button_ref.current]
            ):
                print("⏳ Campos não prontos")
                return

            name = (
                user_data.get("full_name", "")
                if isinstance(user_data, dict)
                else (user_data.full_name or "")
            )

            full_name_ref.current.value = name
            full_name_ref.current.disabled = False
            password_ref.current.disabled = False
            save_button_ref.current.disabled = False
            # Habilitar botão deletar (mas proteger último gerente no core)
            if delete_button_ref.current:
                delete_button_ref.current.disabled = False

            full_name_ref.current.update()
            password_ref.current.update()
            save_button_ref.current.update()
            print(f"✅ Campos habilitados para: {name}")
        except Exception as e:
            print(f"❌ Erro ao habilitar: {e}")

    # HANDLER DE SELEÇÃO (COM DEBUG)
    def on_user_select(e):
        print(f"🎯 EVENTO on_change ACIONADO! Valor: {e.control.value}")
        selected_id = e.control.value

        if not selected_id:
            reset_user_fields()
            return

        pdv_core = page.app_data.get("pdv_core")
        if not pdv_core:
            print("❌ pdv_core não encontrado")
            return

        try:
            user = pdv_core.get_user_by_id(int(selected_id))
            if user:
                enable_user_fields(user)
            else:
                print("❌ Usuário não encontrado")
                reset_user_fields()
        except Exception as e:
            print(f"❌ Erro ao buscar usuário: {e}")

    # SALVAR USUÁRIO
    def save_user(e):
        print("💾 Tentando salvar usuário...")
        if not user_dropdown_ref.current or not user_dropdown_ref.current.value:
            show_snackbar(page, "Selecione um usuário primeiro", ft.colors.RED)
            return

        pdv_core = page.app_data.get("pdv_core")
        if not pdv_core:
            return

        user_id = int(user_dropdown_ref.current.value)
        full_name = full_name_ref.current.value.strip()
        password = password_ref.current.value.strip()

        if not full_name:
            show_snackbar(page, "Nome não pode estar vazio", ft.colors.RED)
            return

        sucesso, msg = pdv_core.update_user_settings(
            user_id, full_name, password or None
        )

        if sucesso:
            show_snackbar(page, "Usuário atualizado!", ft.colors.GREEN)
            password_ref.current.value = ""
            password_ref.current.update()

            # Recarregar dropdown
            users = load_users()
            populate_dropdown(users, selected_id=user_id)
        else:
            show_snackbar(page, f"Erro: {msg}", ft.colors.RED)

    # REMOVER USUÁRIO SELECIONADO
    def delete_user_handler(e):
        try:
            if not user_dropdown_ref.current or not user_dropdown_ref.current.value:
                show_snackbar(page, "Selecione um usuário primeiro", ft.colors.RED)
                return

            user_id = int(user_dropdown_ref.current.value)
            pdv_core = page.app_data.get("pdv_core")
            if not pdv_core:
                show_snackbar(page, "Core não iniciado", ft.colors.RED)
                return

            # Confirmação via diálogo
            def confirm_delete(_e):
                ok, msg = pdv_core.delete_user(user_id)
                if ok:
                    show_snackbar(page, msg, ft.colors.GREEN)
                    users = load_users()
                    populate_dropdown(users)
                else:
                    show_snackbar(page, msg, ft.colors.RED)
                page.dialog.open = False
                page.update()

            def cancel(_e):
                page.dialog.open = False
                page.update()

            dlg = ft.AlertDialog(
                title=ft.Text("Confirmar Remoção"),
                content=ft.Text("Deseja realmente remover o usuário selecionado?"),
                actions=[
                    ft.TextButton("Cancelar", on_click=cancel),
                    ft.ElevatedButton(
                        "Remover",
                        bgcolor=ft.colors.RED_600,
                        on_click=confirm_delete,
                    ),
                ],
            )

            page.dialog = dlg
            page.dialog.open = True
            page.update()

        except Exception as ex:
            print(f"❌ Erro em delete_user_handler: {ex}")
            show_snackbar(page, f"Erro: {ex}", ft.colors.RED)

    # UI SIMPLIFICADA
    user_card = ft.Card(
        content=ft.Container(
            padding=20,
            content=ft.Column(
                [
                    ft.Text(
                        "Gerenciamento de Usuários 👥",
                        style=ft.TextThemeStyle.TITLE_LARGE,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Text("Selecione um usuário para editar"),
                    ft.Dropdown(
                        ref=user_dropdown_ref,
                        label="Selecionar Usuário",
                        options=initial_options,
                        on_change=on_user_select,
                        width=400,
                    ),
                    ft.TextField(
                        ref=full_name_ref,
                        label="Nome Completo",
                        disabled=True,
                        prefix_icon=ft.icons.PERSON,
                    ),
                    ft.TextField(
                        ref=password_ref,
                        label="Nova Senha",
                        disabled=True,
                        password=True,
                        can_reveal_password=True,
                        prefix_icon=ft.icons.LOCK,
                    ),
                    ft.Row(
                        [
                            ft.FilledButton(
                                "Salvar Alterações",
                                ref=save_button_ref,
                                icon=ft.icons.SAVE,
                                on_click=save_user,
                                disabled=True,
                            ),
                            ft.ElevatedButton(
                                "Novo Usuário",
                                icon=ft.icons.PERSON_ADD,
                                on_click=lambda e: nova_usuario_dialog(page),
                            ),
                            ft.ElevatedButton(
                                "Deletar Usuário",
                                ref=delete_button_ref,
                                icon=ft.icons.DELETE,
                                bgcolor=ft.colors.RED_600,
                                on_click=delete_user_handler,
                                disabled=True,
                            ),
                        ],
                        spacing=12,
                    ),
                ],
                spacing=15,
            ),
        )
    )

    # SALVAR IMPRESSORA
    def save_printer(e):
        printer_name = printer_name_ref.current.value.strip()
        paper_size = paper_size_ref.current.value

        if not printer_name:
            show_snackbar(page, "Informe o nome da impressora", ft.colors.ORANGE)
            return

        pdv_core = page.app_data.get("pdv_core")
        if pdv_core and hasattr(pdv_core, "save_printer_config"):
            sucesso, msg = pdv_core.save_printer_config(printer_name, paper_size)
            show_snackbar(page, msg, ft.colors.GREEN if sucesso else ft.colors.RED)
        else:
            page.session.set("printer_name", printer_name)
            page.session.set("paper_size", paper_size)
            show_snackbar(page, "Configurações salvas na sessão!", ft.colors.GREEN)

    printer_card = ft.Card(
        content=ft.Container(
            padding=20,
            content=ft.Column(
                [
                    ft.Text(
                        "Configurações da Impressora 🖨️",
                        style=ft.TextThemeStyle.TITLE_LARGE,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.TextField(
                        ref=printer_name_ref,
                        label="Nome da Impressora",
                        prefix_icon=ft.icons.PRINT,
                    ),
                    ft.Dropdown(
                        ref=paper_size_ref,
                        label="Tamanho do Papel",
                        options=[
                            ft.dropdown.Option("80mm"),
                            ft.dropdown.Option("58mm"),
                        ],
                        value="80mm",
                    ),
                    ft.FilledButton(
                        "Salvar Config. Impressora",
                        icon=ft.icons.SAVE,
                        on_click=save_printer,
                    ),
                ],
                spacing=15,
            ),
        )
    )

    view = ft.View(
        "/gerente/configuracoes",
        [
            ft.AppBar(
                title=ft.Text(
                    "Configurações Gerais",
                    style=ft.TextThemeStyle.TITLE_LARGE,
                    weight=ft.FontWeight.BOLD,
                ),
                center_title=True,
                bgcolor=ft.colors.GREY_100,
                leading=ft.IconButton(ft.icons.ARROW_BACK, on_click=handle_back),
            ),
            ft.Container(
                content=ft.Column(
                    [user_card, printer_card],
                    spacing=20,
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=20,
                expand=True,
            ),
        ],
        padding=0,
    )

    # LIFECYCLE - GARANTIR TUDO ESTEJA PRONTO
    def on_view_did_mount(e):
        page.bgcolor = COLORS["background"]
        print("🎨 View montada, iniciando carregamento...")

        # Usar run_task para garantir que a view está completamente montada
        def delayed_setup():
            page.sleep(300)  # Aguardar 300ms
            users = load_users()
            populate_dropdown(users)
            reset_user_fields()
            print("✅ Setup completo!")

        page.run_task(delayed_setup)

    view.on_view_did_mount = on_view_did_mount

    # DIALOG PARA CRIAR NOVO USUÁRIO
    def nova_usuario_dialog(page: ft.Page):
        pdv_core = page.app_data.get("pdv_core")
        if not pdv_core:
            show_snackbar(page, "Core não iniciado", ft.colors.RED)
            return

        username_field = ft.TextField(label="Username")
        fullname_field = ft.TextField(label="Nome Completo")
        password_field = ft.TextField(
            label="Senha", password=True, can_reveal_password=True
        )
        role_dropdown = ft.Dropdown(
            label="Funções",
            value="caixa",
            options=[
                ft.dropdown.Option("gerente", "Gerente"),
                ft.dropdown.Option("caixa", "Caixa"),
                ft.dropdown.Option("estoque", "Estoque"),
            ],
        )

        def submit(e):
            uname = username_field.value.strip()
            fname = fullname_field.value.strip()
            pwd = password_field.value.strip()
            role = role_dropdown.value
            if not uname or not pwd or not role:
                show_snackbar(
                    page, "Informe username, senha e função", ft.colors.ORANGE
                )
                return

            ok, result = pdv_core.create_user(uname, pwd, role, fname or None)
            if ok:
                new_user = result
                show_snackbar(page, "Usuário criado com sucesso", ft.colors.GREEN)
                # Recarregar dropdown e selecionar o novo usuário
                users = load_users()
                populate_dropdown(users, selected_id=getattr(new_user, "id", None))
                page.dialog.open = False
                page.update()
            else:
                show_snackbar(page, f"Erro: {result}", ft.colors.RED)

        dialog = ft.AlertDialog(
            title=ft.Text("Novo Usuário"),
            content=ft.Column(
                [username_field, fullname_field, password_field, role_dropdown]
            ),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    on_click=lambda e: (
                        setattr(page, "dialog", page.dialog)
                        or (page.dialog.__setattr__("open", False), page.update())
                    )[0],
                ),
                ft.ElevatedButton("Criar", on_click=submit),
            ],
        )

        page.dialog = dialog
        page.dialog.open = True
        page.update()

    return view
