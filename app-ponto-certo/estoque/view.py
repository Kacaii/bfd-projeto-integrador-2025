# View de Estoque: tela responsável por cadastro, edição,
# importação e visualização de produtos de estoque.

import flet as ft
from datetime import datetime
from pathlib import Path
from utils.export_utils import generate_csv_file, generate_pdf_file
from utils.barcode_reader import BarcodeReader
import os
import json
import csv

# Paleta de cores usada na tela de estoque
COLORS = {
    "primary": "#2C7A7B",
    "accent": "#38B2AC",
    "background": "#F7FAFC",
    "text": "#2D3748",
}
CATEGORIAS = [
    "Hortifrúti",
    "Carnes (açougue)",
    "Frios e laticínios",
    "Mercearia",
    "Padaria",
    "Bebidas",
    "Higiene e Limpeza",
    "Utensílios Domésticos",
    "Pet Shop",
]

# Caminho base do projeto (um nível acima da pasta "estoque")
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
# Arquivo JSON onde os produtos de estoque são salvos/carregados
ARQUIVO_DADOS = os.path.join(BASE_DIR, "data", "produtos.json")


def carregar_produtos():
    """Carrega produtos do arquivo JSON e converte campos.

    - Converte a string de validade para datetime.
    - Garante que preco_venda seja float.
    """
    if os.path.exists(ARQUIVO_DADOS):
        with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
            dados = json.load(f)
            for p in dados:
                p["validade"] = datetime.strptime(p["validade"], "%d/%m/%Y")
                p["preco_venda"] = float(p.get("preco_venda", p.get("preco", 0.0)))
            return dados
    return []


def salvar_produtos(produtos):
    """Persiste a lista de produtos no arquivo JSON padronizando campos."""
    dados = []
    for p in produtos:
        dados.append(
            {
                "id": p["id"],
                "nome": p["nome"],
                "categoria": p["categoria"],
                "validade": p["validade"].strftime("%d/%m/%Y"),
                "quantidade": p["quantidade"],
                "preco_venda": float(p.get("preco_venda", p.get("preco", 0.0))),
                "codigo_barras": p.get("codigo_barras", ""),
            }
        )
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def create_estoque_view(page: ft.Page, voltar_callback):
    """Monta e retorna a View do módulo de Estoque.

    - `page`: instância principal do Flet.
    - `voltar_callback`: função chamada ao clicar no botão de voltar.
    """
    page.locale = "pt-BR"

    # Leitor de código de barras via câmera (utils/barcode_reader)
    barcode_reader = BarcodeReader()

    # DatePicker "global" da página para reaproveitar em vários lugares
    page.overlay.append(
        ft.DatePicker(
            first_date=datetime(2020, 1, 1),
            last_date=datetime(2050, 12, 31),
            confirm_text="Confirmar",
            cancel_text="Cancelar",
            help_text="Selecione a data",
            error_format_text="Formato inválido",
            error_invalid_text="Data fora do limite",
            field_label_text="Digite a data",
            field_hint_text="DD/MM/AAAA",
        )
    )

    # Lista em memória com todos os produtos exibidos/editados na tela
    produtos = carregar_produtos()

    # Calcula contadores dos cards (baixo estoque, total e vencidos)
    def atualizar_estatisticas():
        baixo = sum(1 for p in produtos if p["quantidade"] < 10)
        venc = sum(1 for p in produtos if p["validade"] < datetime.now())
        return baixo, len(produtos), venc

    # Converte texto dd/mm/aaaa em datetime ou None
    def converter_texto_para_data(texto):
        try:
            return datetime.strptime(texto, "%d/%m/%Y")
        except ValueError:
            return None

    # Converte texto de preço (com R$, vírgula/ponto) em float
    def converter_texto_para_preco(texto):
        if texto is None:
            return 0.0
        try:
            s = str(texto).strip()
            s = s.replace("R$", "").replace("r$", "").strip()
            s = s.replace(".", "").replace(",", ".")
            if s == "":
                return 0.0
            return float(s)
        except Exception:
            return 0.0

    # Valida campos básicos do produto e retorna quantidade como int
    def validar_produto(nome, categoria, quantidade, validade_obj):
        if not (nome and categoria and quantidade):
            raise ValueError("⚠️ Todos os campos são obrigatórios!")
        if validade_obj is None:
            raise ValueError("⚠️ Data inválida! Use o formato DD/MM/AAAA.")
        try:
            qtd = int(quantidade)
            if qtd < 0:
                raise ValueError()
            return qtd
        except Exception:
            raise ValueError("Quantidade deve ser um número inteiro positivo")

    # Atualiza os cards de resumo e recarrega as linhas da tabela
    def atualizar_tabela():
        baixo, total, venc = atualizar_estatisticas()
        texto_baixo_estoque.value = str(baixo)
        texto_total_produtos.value = str(total)
        texto_vencidos.value = str(venc)
        data_table.rows.clear()
        for p in produtos:
            data_table.rows.append(criar_linha_tabela(p))
        page.update()

    # Fecha o diálogo de cadastro/edição de produto
    def fechar_dialog():
        dialog.open = False
        page.update()

    # Limpa todos os campos do formulário de produto
    def limpar_campos():
        nome_field.value = ""
        categoria_field.value = None
        quantidade_field.value = ""
        preco_field.value = ""
        codigo_barras_field.value = ""
        codigo_barras_leitor_field.value = ""
        data_atual = datetime.now()
        validade_picker.value = data_atual
        data_validade_field.value = data_atual.strftime("%d/%m/%Y")

    # Abre o diálogo no modo "Adicionar Produto"
    def abrir_dialog(e):
        dialog.title = ft.Text("Adicionar Produto")
        dialog.actions[1] = ft.ElevatedButton(
            "Salvar",
            bgcolor=COLORS["accent"],
            color="white",
            on_click=lambda _: adicionar_produto(None),
        )
        limpar_campos()
        page.dialog = dialog
        dialog.open = True
        page.update()

    # Entra no modo edição preenchendo o diálogo com dados do produto
    def editar_produto(e, produto_id):
        produto = next((p for p in produtos if p["id"] == produto_id), None)
        if not produto:
            return
        nome_field.value = produto["nome"]
        categoria_field.value = produto["categoria"]
        quantidade_field.value = str(produto["quantidade"])
        codigo_barras_field.value = produto.get("codigo_barras", "")
        codigo_barras_leitor_field.value = produto.get("codigo_barras", "")
        validade_picker.value = produto["validade"]
        data_validade_field.value = produto["validade"].strftime("%d/%m/%Y")
        preco_field.value = f"{produto.get('preco_venda', 0.0):.2f}".replace(".", ",")
        dialog.title = ft.Text("Editar Produto")

        def salvar_edicao(_):
            try:
                nova_validade = converter_texto_para_data(data_validade_field.value)
                qtd = validar_produto(
                    nome_field.value,
                    categoria_field.value,
                    quantidade_field.value,
                    nova_validade,
                )
                produto["nome"] = nome_field.value
                produto["categoria"] = categoria_field.value
                produto["validade"] = nova_validade
                produto["quantidade"] = qtd
                produto["codigo_barras"] = codigo_barras_field.value
                produto["preco_venda"] = converter_texto_para_preco(preco_field.value)
                salvar_produtos(produtos)
                atualizar_tabela()
                fechar_dialog()
                limpar_campos()
                page.snack_bar = ft.SnackBar(
                    ft.Text("✅ Produto editado com sucesso!", color="white"),
                    bgcolor=ft.colors.GREEN_600,
                )
                page.snack_bar.open = True
                page.update()
            except ValueError as err:
                page.snack_bar = ft.SnackBar(
                    ft.Text(str(err), color="white"), bgcolor=ft.colors.RED_600
                )
                page.snack_bar.open = True
                page.update()

        dialog.actions[1] = ft.ElevatedButton(
            "Salvar Alterações",
            bgcolor=ft.colors.ORANGE_600,
            color="white",
            on_click=salvar_edicao,
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    produto_id_para_excluir = None

    # Abre o diálogo de confirmação de exclusão
    def excluir_produto(e, produto_id):
        nonlocal produto_id_para_excluir
        produto_id_para_excluir = produto_id
        confirmar_exclusao_dialog.content.value = (
            f"Tem certeza que deseja excluir o produto #{produto_id}?"
        )
        page.dialog = confirmar_exclusao_dialog
        confirmar_exclusao_dialog.open = True
        page.update()

    # Confirma a exclusão e remove o produto da lista/arquivo
    def confirmar_exclusao(e):
        nonlocal produto_id_para_excluir
        if produto_id_para_excluir is not None:
            produtos[:] = [p for p in produtos if p["id"] != produto_id_para_excluir]
            salvar_produtos(produtos)
            atualizar_tabela()
            page.snack_bar = ft.SnackBar(
                ft.Text("✅ Produto excluído!", color="white"),
                bgcolor=ft.colors.GREEN_600,
            )
            page.snack_bar.open = True
        produto_id_para_excluir = None
        confirmar_exclusao_dialog.open = False
        page.update()

    # Cancela a exclusão em andamento
    def cancelar_exclusao(e):
        nonlocal produto_id_para_excluir
        produto_id_para_excluir = None
        confirmar_exclusao_dialog.open = False
        page.update()

    # Diálogo de confirmação de exclusão de produto
    confirmar_exclusao_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("⚠️ Confirmar Exclusão"),
        content=ft.Text("Tem certeza que deseja excluir este produto?"),
        actions=[
            ft.TextButton("Cancelar", on_click=cancelar_exclusao),
            ft.ElevatedButton(
                "Sim, Excluir",
                bgcolor=ft.colors.RED_600,
                color="white",
                on_click=confirmar_exclusao,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    # Cria um novo produto a partir do formulário e salva
    def adicionar_produto(e):
        try:
            data_val = converter_texto_para_data(data_validade_field.value)
            qtd = validar_produto(
                nome_field.value,
                categoria_field.value,
                quantidade_field.value,
                data_val,
            )
            preco_val = converter_texto_para_preco(preco_field.value)
            novo = {
                "id": max([p["id"] for p in produtos], default=0) + 1,
                "nome": nome_field.value,
                "categoria": categoria_field.value,
                "validade": data_val,
                "quantidade": qtd,
                "preco_venda": preco_val,
                "codigo_barras": codigo_barras_field.value,
            }
            produtos.append(novo)
            salvar_produtos(produtos)
            atualizar_tabela()
            fechar_dialog()
            limpar_campos()
            page.snack_bar = ft.SnackBar(
                ft.Text("✅ Produto adicionado!", color="white"),
                bgcolor=ft.colors.GREEN_600,
            )
            page.snack_bar.open = True
            page.update()
        except Exception as err:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"{err}", color="white"), bgcolor=ft.colors.RED_600
            )
            page.snack_bar.open = True
            page.update()

    # Gera um CSV do estoque atual usando utilitário de exportação
    def exportar_csv(e):
        try:
            headers = ["ID", "Nome", "Categoria", "Validade", "Quantidade", "Preço"]
            data = [
                [
                    p["id"],
                    p["nome"],
                    p["categoria"],
                    p["validade"].strftime("%d/%m/%Y"),
                    p["quantidade"],
                    f"{float(p.get('preco_venda', p.get('preco', 0.0))):.2f}".replace(
                        ".",
                        ",",
                    ),
                ]
                for p in produtos
            ]
            caminho = generate_csv_file(headers, data, nome_base="estoque")
            os.startfile(caminho)
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✅ CSV exportado: {Path(caminho).name}"),
                bgcolor=ft.colors.GREEN_600,
            )
            page.snack_bar.open = True
            page.update()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ Erro ao exportar: {str(ex)}"), bgcolor=ft.colors.RED_600
            )
            page.snack_bar.open = True
            page.update()

    # Gera um PDF do estoque atual usando utilitário de exportação
    def exportar_pdf(e):
        try:
            headers = ["ID", "Nome", "Categoria", "Validade", "Quantidade", "Preço"]
            data = [
                [
                    p["id"],
                    p["nome"],
                    p["categoria"],
                    p["validade"].strftime("%d/%m/%Y"),
                    p["quantidade"],
                    f"{float(p.get('preco_venda', p.get('preco', 0.0))):.2f}".replace(
                        ".",
                        ",",
                    ),
                ]
                for p in produtos
            ]
            caminho = generate_pdf_file(
                headers, data, nome_base="estoque", title="Relatório de Estoque"
            )
            os.startfile(caminho)
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✅ PDF exportado: {Path(caminho).name}"),
                bgcolor=ft.colors.GREEN_600,
            )
            page.snack_bar.open = True
            page.update()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ Erro ao gerar PDF: {str(ex)}"), bgcolor=ft.colors.RED_600
            )
            page.snack_bar.open = True
            page.update()

    # Handler chamado após o usuário escolher um arquivo CSV
    def on_file_selected(ev):
        file_path = (
            file_picker.result.files[0].path if file_picker.result.files else None
        )
        if not file_path:
            return
        novos = []
        try:
            with open(file_path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        nome = row.get("Nome") or row.get("nome")
                        categoria = row.get("Categoria") or row.get("categoria")
                        validade = row.get("Validade") or row.get("validade")
                        quantidade = row.get("Quantidade") or row.get("quantidade")
                        codigo_barras = (
                            row.get("Código de Barras")
                            or row.get("codigo_barras")
                            or row.get("Codigo de Barras")
                        )
                        validade_obj = converter_texto_para_data(validade)
                        qtd = validar_produto(nome, categoria, quantidade, validade_obj)
                        preco_venda = converter_texto_para_preco(
                            row.get("Preço")
                            or row.get("Preco")
                            or row.get("preco_venda")
                            or row.get("preco")
                            or row.get("Preço de Venda")
                        )
                        novo = {
                            "id": max([p["id"] for p in produtos], default=0)
                            + 1
                            + len(novos),
                            "nome": nome,
                            "categoria": categoria,
                            "validade": validade_obj,
                            "quantidade": qtd,
                            "preco_venda": preco_venda,
                            "codigo_barras": codigo_barras or "",
                        }
                        novos.append(novo)
                    except Exception:
                        continue
            if novos:
                produtos.extend(novos)
                salvar_produtos(produtos)
                atualizar_tabela()
                page.snack_bar = ft.SnackBar(
                    ft.Text(
                        f"✅ {len(novos)} produto(s) importado(s) do CSV!",
                        color="white",
                    ),
                    bgcolor=ft.colors.GREEN_600,
                )
            else:
                page.snack_bar = ft.SnackBar(
                    ft.Text("Nenhum produto válido encontrado no CSV.", color="white"),
                    bgcolor=ft.colors.RED_600,
                )
            page.snack_bar.open = True
            page.update()
        except Exception as err:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Erro ao importar CSV: {err}", color="white"),
                bgcolor=ft.colors.RED_600,
            )
            page.snack_bar.open = True
            page.update()

    # FilePicker para importar produtos de um arquivo CSV
    file_picker = ft.FilePicker(on_result=on_file_selected)
    page.overlay.append(file_picker)

    # Abre o seletor de arquivo CSV de produtos
    def importar_csv(e):
        file_picker.pick_files(allow_multiple=False, allowed_extensions=["csv"])

    # DatePicker usado especificamente para o campo de validade do produto
    validade_picker = ft.DatePicker(
        first_date=datetime(2020, 1, 1),
        last_date=datetime(2050, 12, 31),
        on_change=lambda e: setattr(
            data_validade_field, "value", e.control.value.strftime("%d/%m/%Y")
        ),
    )
    page.overlay.append(validade_picker)

    # Abre o calendário já posicionado na data atual do campo
    def abrir_calendario(e):
        try:
            dia, mes, ano = map(int, data_validade_field.value.split("/"))
            validade_picker.value = datetime(ano, mes, dia)
        except Exception:
            validade_picker.value = datetime.now()
        validade_picker.pick_date()

    texto_baixo_estoque = ft.Text(
        "0", size=24, weight=ft.FontWeight.BOLD, color=ft.colors.RED_600
    )
    texto_total_produtos = ft.Text(
        "0", size=24, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_600
    )
    texto_vencidos = ft.Text(
        "0", size=24, weight=ft.FontWeight.BOLD, color=ft.colors.ORANGE_600
    )

    # Cria um card de métrica (baixo estoque, total, vencidos)
    def criar_card_layout(titulo, texto_valor, icone, cor_icone, cor_fundo):
        return ft.Card(
            content=ft.Container(
                ft.ListTile(
                    leading=ft.Icon(icone, color=cor_icone, size=30),
                    title=ft.Text(titulo, size=16, color=ft.colors.GREY_700),
                    subtitle=texto_valor,
                ),
                bgcolor=cor_fundo,
                padding=10,
                border_radius=8,
            )
        )

    card_baixo_estoque = criar_card_layout(
        "Baixo Estoque",
        texto_baixo_estoque,
        ft.icons.WARNING,
        ft.colors.RED_600,
        ft.colors.RED_50,
    )
    card_total_produtos = criar_card_layout(
        "Total de Produtos",
        texto_total_produtos,
        ft.icons.INVENTORY,
        ft.colors.BLUE_600,
        ft.colors.BLUE_50,
    )
    card_vencidos = criar_card_layout(
        "Produtos Próximos do Vencimento",
        texto_vencidos,
        ft.icons.EVENT_BUSY,
        ft.colors.ORANGE_600,
        ft.colors.ORANGE_50,
    )

    nome_field = ft.TextField(label="Nome do Produto", dense=True, expand=True)
    categoria_field = ft.Dropdown(
        label="Categoria",
        options=[ft.dropdown.Option(c) for c in CATEGORIAS],
        dense=True,
        expand=True,
    )
    quantidade_field = ft.TextField(
        label="Quantidade",
        dense=True,
        expand=True,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    codigo_barras_field = ft.TextField(
        label="Código de Barras", dense=True, expand=True
    )
    preco_field = ft.TextField(
        label="Preço de Venda",
        dense=True,
        expand=True,
        prefix_text="R$",
        keyboard_type=ft.KeyboardType.NUMBER,
        hint_text="Ex: 4,99",
    )

    # Inicia leitura de código de barras via câmera
    def iniciar_leitura_camera(e):
        def on_barcode_detected(barcode_data):
            codigo_barras_field.value = barcode_data
            codigo_barras_leitor_field.value = barcode_data
            page.update()
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✅ Código lido: {barcode_data}", color="white"),
                bgcolor=ft.colors.GREEN_600,
            )
            page.snack_bar.open = True
            page.update()

        if not barcode_reader.is_camera_available():
            page.snack_bar = ft.SnackBar(
                ft.Text("❌ Câmera não disponível!", color="white"),
                bgcolor=ft.colors.RED_600,
            )
            page.snack_bar.open = True
            page.update()
            return

        barcode_reader.start_camera(on_barcode_detected)
        page.snack_bar = ft.SnackBar(
            ft.Text(
                "📷 Câmera iniciada. Aponte para o código de barras...",
                color="white",
            ),
            bgcolor=ft.colors.BLUE_600,
        )
        page.snack_bar.open = True
        page.update()

    codigo_barras_leitor_field = ft.TextField(
        label="Scanner de Código de Barras",
        dense=True,
        expand=True,
        keyboard_type=ft.KeyboardType.TEXT,
        hint_text="Escaneie o código aqui ou digite manualmente",
        on_change=lambda e: setattr(codigo_barras_field, "value", e.control.value),
        suffix=ft.IconButton(
            icon=ft.icons.CAMERA_ALT,
            on_click=iniciar_leitura_camera,
            tooltip="Ler código via câmera",
        ),
    )

    data_validade_field = ft.TextField(
        label="Data de Validade",
        value=datetime.now().strftime("%d/%m/%Y"),
        read_only=False,
        dense=True,
        expand=True,
        suffix=ft.IconButton(
            icon=ft.icons.CALENDAR_MONTH,
            on_click=abrir_calendario,
            tooltip="Selecionar Data",
        ),
        keyboard_type=ft.KeyboardType.DATETIME,
    )

    # Tabela principal que lista os produtos de estoque
    data_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID", size=14, weight=ft.FontWeight.BOLD, width=60)),
            ft.DataColumn(
                ft.Text(
                    "Nome do Produto", size=14, weight=ft.FontWeight.BOLD, expand=True
                )
            ),
            ft.DataColumn(
                ft.Text("Categoria", size=14, weight=ft.FontWeight.BOLD, expand=True)
            ),
            ft.DataColumn(
                ft.Text("Validade", size=14, weight=ft.FontWeight.BOLD, width=100)
            ),
            ft.DataColumn(
                ft.Text("Quantidade", size=14, weight=ft.FontWeight.BOLD, width=100)
            ),
            ft.DataColumn(
                ft.Text("Preço", size=14, weight=ft.FontWeight.BOLD, width=100)
            ),
            ft.DataColumn(
                ft.Text(
                    "Código de Barras", size=14, weight=ft.FontWeight.BOLD, width=120
                )
            ),
            ft.DataColumn(
                ft.Text("Ações", size=14, weight=ft.FontWeight.BOLD, width=120)
            ),
        ],
        rows=[],
        column_spacing=30,
        bgcolor="white",
        border=ft.border.all(1, ft.colors.GREY_300),
        border_radius=5,
    )

    tabela_container = ft.Container(
        content=ft.ListView(
            controls=[data_table],
            expand=True,
            auto_scroll=False,
        ),
        expand=True,
        width=float("inf"),
        border=ft.border.all(1, ft.colors.GREY_300),
        border_radius=8,
        bgcolor="white",
        padding=0,
        margin=ft.margin.only(top=15),
    )

    # Diálogo de cadastro/edição de produto
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Adicionar Produto"),
        content=ft.Column(
            [
                ft.Row([nome_field, categoria_field], spacing=12),
                ft.Row(
                    [data_validade_field, quantidade_field, preco_field], spacing=12
                ),
                ft.Row([codigo_barras_field, codigo_barras_leitor_field], spacing=12),
            ],
            tight=True,
            spacing=12,
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: fechar_dialog()),
            ft.ElevatedButton(
                "Salvar",
                bgcolor=COLORS["accent"],
                color="white",
                on_click=lambda e: adicionar_produto(e),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        inset_padding=ft.padding.all(20),
    )

    cards_row = ft.Row(
        [card_baixo_estoque, card_total_produtos, card_vencidos], spacing=20, wrap=True
    )
    botoes_acao = ft.Row(
        [
            ft.ElevatedButton(
                "Adicionar Produto",
                icon=ft.icons.ADD,
                bgcolor=COLORS["accent"],
                color="white",
                on_click=abrir_dialog,
            ),
            ft.ElevatedButton(
                "Importar CSV",
                icon=ft.icons.UPLOAD_FILE,
                on_click=importar_csv,
                bgcolor=ft.colors.GREEN_600,
                color="white",
            ),
            ft.ElevatedButton(
                "Exportar CSV",
                icon=ft.icons.FILE_PRESENT,
                on_click=exportar_csv,
                bgcolor=ft.colors.BLUE_600,
                color="white",
            ),
            ft.ElevatedButton(
                "Exportar PDF",
                icon=ft.icons.PICTURE_AS_PDF,
                on_click=exportar_pdf,
                bgcolor=ft.colors.RED_600,
                color="white",
            ),
        ],
        spacing=12,
    )

    # View principal da rota "/estoque"
    view = ft.View(
        "/estoque",
        bgcolor=COLORS["background"],
        padding=ft.padding.all(20),
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.IconButton(
                                    icon=ft.icons.ARROW_BACK,
                                    on_click=voltar_callback,
                                    icon_color=ft.colors.BLACK,
                                    icon_size=28,
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        "Controle de Estoque",
                                        size=24,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.colors.BLACK,
                                        text_align=ft.TextAlign.CENTER,
                                    ),
                                    expand=True,
                                    alignment=ft.alignment.center,
                                ),
                            ],
                            spacing=15,
                        ),
                        ft.Divider(height=2, thickness=2, color=ft.colors.GREY_300),
                        cards_row,
                        ft.Divider(height=1, thickness=1, color=ft.colors.GREY_300),
                        botoes_acao,
                        tabela_container,
                    ],
                    expand=True,
                    spacing=20,
                ),
                expand=True,
            )
        ],
    )

    # Monta uma linha da tabela de produtos a partir de um dict `p`
    def criar_linha_tabela(p):
        cor_qtd = ft.colors.RED_600 if p["quantidade"] < 10 else ft.colors.GREEN_600
        btn_editar = ft.IconButton(
            icon=ft.icons.EDIT_OUTLINED,
            tooltip="Editar",
            icon_color=ft.colors.BLUE_600,
            on_click=lambda e: editar_produto(e, p["id"]),
        )
        btn_excluir = ft.IconButton(
            icon=ft.icons.DELETE_OUTLINE,
            tooltip="Excluir",
            icon_color=ft.colors.RED_600,
            on_click=lambda e: excluir_produto(e, p["id"]),
        )

        return ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(str(p["id"]), size=14)),
                ft.DataCell(
                    ft.Container(
                        content=ft.Text(
                            p["nome"], size=14, max_lines=2, overflow="visible"
                        ),
                        width=180,
                        padding=ft.padding.only(right=4),
                    )
                ),
                ft.DataCell(ft.Text(p["categoria"], size=14)),
                ft.DataCell(ft.Text(p["validade"].strftime("%d/%m/%Y"), size=14)),
                ft.DataCell(
                    ft.Text(
                        str(p["quantidade"]),
                        size=14,
                        color=cor_qtd,
                        weight=ft.FontWeight.BOLD,
                    )
                ),
                ft.DataCell(
                    ft.Text(
                        f"R$ {float(p.get('preco_venda', p.get('preco', 0.0))):.2f}".replace(
                            ".",
                            ",",
                        ),
                        size=14,
                        color=ft.colors.GREY_800,
                    )
                ),
                ft.DataCell(
                    ft.Text(
                        p.get("codigo_barras", "-"),
                        size=12,
                        color=ft.colors.GREY_700,
                    )
                ),
                ft.DataCell(ft.Row([btn_editar, btn_excluir], spacing=5)),
            ]
        )

    atualizar_tabela()
    return view


__all__ = [
    "COLORS",
    "CATEGORIAS",
    "ARQUIVO_DADOS",
    "carregar_produtos",
    "salvar_produtos",
    "create_estoque_view",
]
