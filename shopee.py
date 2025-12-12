import zipfile
import os
import pandas as pd
from openpyxl import load_workbook
import shutil
import tempfile
from utils import resource_path  # garante caminho correto no .exe

# Base do projeto no disco (para escrita persistente)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def executar_fluxo_shopee():
    """
    Executa o fluxo de processamento Shopee.
    Retorna o caminho do arquivo gerado (em pasta temporária).
    """
    # === LOCALIZA O ZIP NA PASTA DOWNLOADS ===
    downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")

    # lista todos os arquivos que começam com mass_update_sales_info e terminam com .zip
    arquivos = [
        os.path.join(downloads_path, f)
        for f in os.listdir(downloads_path)
        if f.startswith("mass_update_sales_info") and f.endswith(".zip")
    ]

    if not arquivos:
        raise FileNotFoundError("Nenhum arquivo mass_update_sales_info*.zip encontrado na pasta Downloads.")

    # pega o mais recente pela data de modificação
    zip_file = max(arquivos, key=os.path.getmtime)

    if not zip_file:
        raise FileNotFoundError("Nenhum arquivo mass_update_sales_info*.zip encontrado na pasta Downloads.")

    # === CONFIGURAÇÕES DE PASTAS ===
    extract_path = os.path.join(BASE_DIR, "data", "temp", "shopee")   # escrita no disco
    base_path = resource_path("data/base/shopee")                     # leitura do bundle
    temp_output = tempfile.gettempdir()  # Salva em pasta temporária
    os.makedirs(extract_path, exist_ok=True)

    # === ETAPA 1: Extrair apenas os arquivos .xlsx ===
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        for member in zip_ref.namelist():
            if member.endswith(".xlsx"):
                zip_ref.extract(member, extract_path)

    # === ETAPA 2: Copiar dados para as planilhas base ===
    for i in range(1, 9):
        file_path = os.path.join(extract_path, f"{i}.xlsx")
        base_file = os.path.join(base_path, f"{i}.xlsx")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo {i}.xlsx não encontrado no ZIP.")
        if not os.path.exists(base_file):
            raise FileNotFoundError(f"Arquivo base {i}.xlsx não encontrado em {base_path}.")

        # tenta ler com vários métodos
        df = None
        errors = []
        
        # Método 1: openpyxl (Excel padrão)
        try:
            df = pd.read_excel(file_path, engine="openpyxl")
        except Exception as e1:
            errors.append(f"openpyxl: {e1}")
        
        # Método 2: xlrd (Excel antigo .xls)
        if df is None:
            try:
                df = pd.read_excel(file_path, engine="xlrd")
            except Exception as e2:
                errors.append(f"xlrd: {e2}")
        
        # Método 3: calamine (Excel rápido)
        if df is None:
            try:
                df = pd.read_excel(file_path, engine="calamine")
            except Exception as e3:
                errors.append(f"calamine: {e3}")
        
        # Método 3: CSV com encoding UTF-8
        if df is None:
            try:
                df = pd.read_csv(file_path, sep=";", encoding="utf-8")
            except Exception as e3:
                errors.append(f"csv utf-8: {e3}")
        
        # Método 4: CSV com encoding Latin-1
        if df is None:
            try:
                df = pd.read_csv(file_path, sep=";", encoding="latin-1")
            except Exception as e4:
                errors.append(f"csv latin-1: {e4}")
        
        # Método 5: CSV com tab como separador
        if df is None:
            try:
                df = pd.read_csv(file_path, sep="\t", encoding="utf-8")
            except Exception as e5:
                errors.append(f"csv tab: {e5}")
        
        if df is None:
            raise ValueError(f"Não foi possível ler {file_path}. Erros: {'; '.join(errors)}")

        # pega colunas E e F (índices 4 e 5)
        col_e = df.iloc[:, 4].dropna().tolist() if df.shape[1] > 4 else []
        col_f = df.iloc[:, 5].dropna().tolist() if df.shape[1] > 5 else []

        # abre a planilha base e substitui os valores
        wb = load_workbook(base_file)
        ws = wb.active

        # limpa conteúdo antigo
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=2):
            for cell in row:
                cell.value = None

        # escreve novos valores
        for idx, val in enumerate(col_e, start=2):
            ws[f"A{idx}"] = val
        for idx, val in enumerate(col_f, start=2):
            ws[f"B{idx}"] = val

        wb.save(base_file)

    # === ETAPA 3: Consolidar tudo na planilha 1 ===
    todos_valores = []
    for i in range(1, 9):
        df = pd.read_excel(os.path.join(base_path, f"{i}.xlsx"), engine="openpyxl")
        col_a = df.iloc[:, 0].dropna().tolist()
        col_b = df.iloc[:, 1].dropna().tolist()
        todos_valores.extend(col_a)
        todos_valores.extend(col_b)

    # remove duplicatas mantendo ordem
    valores_unicos = list(dict.fromkeys(todos_valores))

    # salva consolidado em pasta temporária
    from datetime import datetime
    output_file = os.path.join(temp_output, f"shopee_consolidado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    df_final = pd.DataFrame(valores_unicos, columns=["SKU"])
    df_final.to_excel(output_file, index=False)

    # limpa pasta temporária de extração
    shutil.rmtree(extract_path, ignore_errors=True)
    
    return output_file