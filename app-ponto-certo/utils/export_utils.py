# export_utils.py
from pathlib import Path
from datetime import datetime
import csv
from fpdf import FPDF

EXPORTS_DIR = Path("exports")
EXPORTS_DIR.mkdir(exist_ok=True)


def generate_csv_file(headers, data, nome_base="relatorio"):
    """Gera CSV na pasta exports/ com nome base + timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = EXPORTS_DIR / f"{nome_base}_{timestamp}.csv"
    try:
        with open(file_path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(data)
        return str(file_path)
    except Exception as e:
        raise Exception(f"Erro ao gerar CSV: {e}")


def generate_pdf_file(headers, data, nome_base="relatorio", title="Relatório"):
    """Gera PDF com tabela alinhada e quebra automática interna."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = EXPORTS_DIR / f"{nome_base}_{timestamp}.pdf"

    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, title, ln=True, align="C")
        pdf.ln(10)

        # Ajustar larguras dinamicamente conforme quantidade de colunas
        ncols = max(1, len(headers))
        page_width = pdf.w - 2 * pdf.l_margin
        col_width = page_width / ncols
        col_widths = [col_width] * ncols
        line_height = 6
        font_size = 10

        # Cabeçalho
        pdf.set_font("Arial", "B", font_size)
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], line_height, str(header), border=1, align="C")
        pdf.ln()

        # Dados com quebra DENTRO da célula
        pdf.set_font("Arial", "", font_size)
        for row in data:
            # Garantir que row tenha o mesmo número de colunas
            row_cells = [str(x) for x in row]
            if len(row_cells) < ncols:
                row_cells += [""] * (ncols - len(row_cells))

            # Calcular altura necessária (estimativa) e imprimir
            max_lines = 1
            for i, item in enumerate(row_cells):
                # estimativa simples: largura do texto / largura da coluna
                text_width = pdf.get_string_width(item)
                # transformar largura da coluna (mm) para unidade de string width aproximada
                est_lines = max(1, int(text_width / (col_widths[i] * 0.35)) + 1)
                max_lines = max(max_lines, est_lines)

            for i, item in enumerate(row_cells):
                x = pdf.get_x()
                y = pdf.get_y()
                pdf.multi_cell(col_widths[i], line_height, item, border=1)
                pdf.set_xy(x + col_widths[i], y)

            pdf.ln(line_height * max_lines)

        pdf.output(str(file_path))
        return str(file_path)
    except Exception as e:
        raise Exception(f"Erro ao gerar PDF: {e}")
