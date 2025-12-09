"""
Módulo de gerenciamento de usuários
Responsável pela visualização e manipulação de usuários do sistema
"""

import flet as ft


def create_usuarios_view(page, pdv_core):
    """Cria a view de gerenciamento de usuários"""

    usuarios_list = []

    def carregar_usuarios():
        """Carrega todos os usuários do banco de dados"""
        nonlocal usuarios_list
        try:
            usuarios_list = pdv_core.get_all_users()
            atualizar_lista()
        except Exception as e:
            print(f"Erro ao carregar usuários: {e}")

    def atualizar_lista():
        """Atualiza a lista de usuários na tela"""
        usuarios_container.controls.clear()

        for usuario in usuarios_list:
            username = getattr(usuario, "username", "N/A")
            full_name = getattr(usuario, "full_name", "N/A")
            role = getattr(usuario, "role", "N/A")

            # Criar card para cada usuário
            usuario_card = ft.Container(
                content=ft.Column(
                    [
                        ft.Text(f"Usuário: {username}", weight=ft.FontWeight.BOLD),
                        ft.Text(f"Nome: {full_name}"),
                        ft.Text(f"Função: {role}"),
                    ]
                ),
                padding=10,
                border=ft.border.all(1, "#CCCCCC"),
                border_radius=5,
                margin=5,
            )
            usuarios_container.controls.append(usuario_card)

        page.update()

    # Container para listar usuários
    usuarios_container = ft.Column(
        scroll=ft.ScrollMode.AUTO,
    )

    # Botão para recarregar
    btn_recarregar = ft.IconButton(
        ft.Icons.REFRESH,
        on_click=lambda e: carregar_usuarios(),
        tooltip="Recarregar usuários",
    )

    # Cabeçalho
    header = ft.Row(
        [
            ft.Text("Gerenciamento de Usuários", size=20, weight=ft.FontWeight.BOLD),
            btn_recarregar,
        ]
    )

    # View principal
    view = ft.View(
        "/usuarios",
        [
            ft.Container(
                content=ft.Column(
                    [
                        header,
                        ft.Divider(),
                        usuarios_container,
                    ]
                ),
                padding=20,
                expand=True,
            )
        ],
        padding=0,
    )

    # Carregar usuários ao iniciar
    carregar_usuarios()

    return view
