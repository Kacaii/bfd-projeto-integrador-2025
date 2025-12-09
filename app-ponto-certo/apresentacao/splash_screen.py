import flet as ft
from datetime import datetime
import asyncio


def create_splash_screen(page: ft.Page) -> ft.View:
    """Cria uma tela de apresentação elegante ao iniciar a aplicação"""
    
    # Cores da marca
    PRIMARY_COLOR = "#007BFF"
    BACKGROUND = "#F5F5F5"
    TEXT_COLOR = "#2D3748"
    
    # Criar componentes com referências para animação
    title_ref = ft.Ref[ft.Text]()
    subtitle_ref = ft.Ref[ft.Text]()
    logo_ref = ft.Ref[ft.Container]()
    progress_ref = ft.Ref[ft.ProgressRing]()
    status_ref = ft.Ref[ft.Text]()
    
    def create_animated_circle():
        """Cria o logo com imagem da marca"""
        return ft.Container(
            ref=logo_ref,
            width=140,
            height=140,
            border_radius=70,
            shadow=ft.BoxShadow(
                spread_radius=5,
                blur_radius=15,
                color=ft.Colors.with_opacity(0.3, PRIMARY_COLOR),
                offset=ft.Offset(0, 5),
            ),
            content=ft.Image(
                src="Mercadinho_Ponto_Certo.png",
                width=140,
                height=140,
                fit=ft.ImageFit.CONTAIN,
            ),
            animate_scale=ft.Animation(1000, ft.AnimationCurve.EASE_IN_OUT),
            animate_opacity=ft.Animation(1000, ft.AnimationCurve.EASE_IN_OUT),
        )
    
    splash_view = ft.View(
        "/splash",
        bgcolor=BACKGROUND,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(
                expand=True,
                content=ft.Column(
                    [
                        ft.Container(height=20),
                        # Logo animado
                        create_animated_circle(),
                        ft.Container(height=30),
                        # Título principal
                        ft.Text(
                            ref=title_ref,
                            value="Mercearia Ponto Certo",
                            size=42,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_COLOR,
                            text_align=ft.TextAlign.CENTER,
                            opacity=0,
                        ),
                        ft.Container(height=10),
                        # Subtítulo
                        ft.Text(
                            ref=subtitle_ref,
                            value="Sistema de Gestão Integrado",
                            size=16,
                            color="#718096",
                            text_align=ft.TextAlign.CENTER,
                            opacity=0,
                        ),
                        ft.Container(height=40),
                        # Indicador de progresso
                        ft.Container(
                            content=ft.ProgressRing(
                                ref=progress_ref,
                                color=PRIMARY_COLOR,
                                stroke_width=4,
                                width=50,
                                height=50,
                            ),
                            alignment=ft.alignment.center,
                        ),
                        ft.Container(height=20),
                        # Status text
                        ft.Text(
                            ref=status_ref,
                            value="Carregando...",
                            size=12,
                            color=ft.Colors.with_opacity(0.6, TEXT_COLOR),
                            text_align=ft.TextAlign.CENTER,
                            opacity=0.5,
                        ),
                        ft.Container(height=20),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=0,
                ),
                alignment=ft.alignment.center,
                padding=40,
            ),
            # Rodapé com versão
            ft.Container(
                content=ft.Text(
                    f"v1.0.0 • {datetime.now().year}",
                    size=10,
                    color=ft.Colors.with_opacity(0.4, TEXT_COLOR),
                    text_align=ft.TextAlign.CENTER,
                ),
                alignment=ft.alignment.bottom_center,
                padding=20,
            ),
        ],
    )
    
    async def animate_splash():
        """Anima os elementos da tela de apresentação e navega para login"""
        messages = [
            "Inicializando...",
            "Carregando banco de dados...",
            "Verificando permissões...",
            "Preparando interface...",
            "Quase pronto...",
        ]
        
        # Aguardar um pouco para os controles serem renderizados
        await asyncio.sleep(0.5)
        
        # Animar título
        if title_ref.current:
            title_ref.current.opacity = 1
            page.update()
        
        # Animar subtítulo
        await asyncio.sleep(0.3)
        if subtitle_ref.current:
            subtitle_ref.current.opacity = 1
            page.update()
        
        # Animar logo
        if logo_ref.current:
            logo_ref.current.scale = 1.1
            page.update()
            await asyncio.sleep(0.5)
            logo_ref.current.scale = 1.0
            page.update()
        
        # Atualizar mensagens de status
        for i, msg in enumerate(messages):
            if status_ref.current:
                status_ref.current.value = msg
                page.update()
            await asyncio.sleep(0.6)
        
        # Navegar para login após animação completar
        page.go("/login")
    
    # Executar animação em background
    page.run_task(animate_splash)
    
    return splash_view
