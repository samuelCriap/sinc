import os
import glob
import zipfile
import shutil
import xlwings as xw
import datetime
import csv
from utils import resource_path  # garante caminhos corretos no .exe

# Base do projeto no disco (usado para gravação persistente)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Pastas internas / caminhos
downloads = os.path.join(os.path.expanduser("~"), "Downloads")  # continua pegando do PC
planilha1 = resource_path("data/base/1.xlsm")
planilha2 = resource_path("data/base/2.xlsm")
saida_path = os.path.join(BASE_DIR, "data", "output")   # gravação persistente em disco
historico_dir_disk = os.path.join(BASE_DIR, "data", "historico")

# Variáveis globais
app_global: xw.App | None = None
wb2_global: xw.Book | None = None

# -------------------------------
# Função auxiliar - Forçar VALOR como TEXTO (OTIMIZADA)
# -------------------------------
def forcar_texto_colunas_valor(ws):
    """
    Converte valores numéricos e booleanos para texto nas colunas que contêm 'VALOR' no nome.
    VERSÃO OTIMIZADA: Usa operações em batch ao invés de célula por célula.
    """
    try:
        # Obter cabeçalhos (linha 1) - leitura única
        headers = ws.range("1:1").value
        if not headers:
            return
        
        # Encontrar colunas que contêm "VALOR" no nome
        colunas_valor = []
        for i, header in enumerate(headers):
            if header and 'VALOR' in str(header).upper():
                colunas_valor.append(i)  # índice 0-based para lista Python
        
        if not colunas_valor:
            return
            
        # Obter última linha com dados
        ultima_linha = ws.range("A1").expand().rows.count
        if ultima_linha < 2:
            return
        
        # Ler TODOS os dados de uma vez (muito mais rápido)
        dados = ws.range("A1").expand().value
        
        # Converter valores nas colunas VALOR
        modificado = False
        for row_idx in range(1, len(dados)):  # Pula cabeçalho (índice 0)
            row = dados[row_idx]
            if not row:
                continue
            for col_idx in colunas_valor:
                if col_idx < len(row):
                    valor = row[col_idx]
                    if valor is not None:
                        # Converter para string
                        if isinstance(valor, bool):
                            dados[row_idx][col_idx] = 'true' if valor else 'false'
                            modificado = True
                        elif isinstance(valor, (int, float)):
                            if isinstance(valor, float) and valor.is_integer():
                                dados[row_idx][col_idx] = str(int(valor))
                            else:
                                dados[row_idx][col_idx] = str(valor)
                            modificado = True
        
        # Escrever TODOS os dados de volta de uma vez (muito mais rápido)
        if modificado:
            ws.range("A1").value = dados
            
            # Aplicar formato texto nas colunas VALOR
            for col_idx in colunas_valor:
                col_letter = chr(65 + col_idx) if col_idx < 26 else chr(64 + col_idx // 26) + chr(65 + col_idx % 26)
                try:
                    ws.range(f"{col_letter}2:{col_letter}{ultima_linha}").number_format = "@"
                except:
                    pass
                    
    except Exception as e:
        print(f"Erro ao forçar texto: {e}")

# -------------------------------
# Script 1 - CSV -> Planilha2 (aba URL)
# -------------------------------
def processar_csv():
    global app_global, wb2_global
    arquivos = glob.glob(os.path.join(downloads, "url*.csv"))
    if not arquivos:
        print("Nenhum CSV encontrado.")
        return
    csv_file = max(arquivos, key=os.path.getmtime)
    print(f"Processando CSV: {csv_file}")

    if app_global is None:
        app_global = xw.App(visible=False)
    wb_source = app_global.books.open(csv_file)
    ws_source = wb_source.sheets[0]

    wb2_global = app_global.books.open(planilha2)
    ws_destino = wb2_global.sheets["URL"]

    ws_destino.clear()
    dados = ws_source.range("A1").expand().value
    ws_destino.range("A1").value = dados

    wb_source.close()
    wb2_global.save()

# -------------------------------
# Script 2 - ZIP -> Planilha1 (aba Colunas)
# -------------------------------
def processar_zip():
    global app_global
    arquivos = glob.glob(os.path.join(downloads, "2025*.zip"))
    if not arquivos:
        print("Nenhum ZIP encontrado.")
        return
    zip_file = max(arquivos, key=os.path.getmtime)
    print(f"Processando ZIP: {zip_file}")

    temp_disk = os.path.join(BASE_DIR, "data", "temp")
    if os.path.exists(temp_disk):
        shutil.rmtree(temp_disk)
    os.makedirs(temp_disk, exist_ok=True)

    with zipfile.ZipFile(zip_file, "r") as z:
        z.extractall(temp_disk)

    excel_files = glob.glob(os.path.join(temp_disk, "**", "*.xls*"), recursive=True)
    if not excel_files:
        print("Nenhum Excel encontrado dentro do ZIP.")
        shutil.rmtree(temp_disk, ignore_errors=True)
        return
    xls_file = excel_files[0]

    if app_global is None:
        app_global = xw.App(visible=False)

    wb_source = app_global.books.open(xls_file)
    ws_source = wb_source.sheets[0]

    dados = ws_source.range("A1").expand().value
    dados_para_escrever = dados[1:] if isinstance(dados, list) and len(dados) > 1 else []

    wb_destino = app_global.books.open(planilha1)
    ws_destino = wb_destino.sheets["Colunas"]

    try:
        ws_destino.range("A2").expand().clear()
    except (AttributeError, ValueError):
        pass
    ws_destino.range("A2").value = dados_para_escrever

    wb_source.close()
    wb_destino.save()
    wb_destino.close()

    shutil.rmtree(temp_disk, ignore_errors=True)

# -------------------------------
# Script 3 - Manipulação de Excel
# -------------------------------
def manipular_planilhas():
    global app_global
    if app_global is None:
        app_global = xw.App(visible=False)

    wb1 = app_global.books.open(planilha1)
    ws1 = wb1.sheets[0]

    try:
        used_rng = ws1.range("A1").expand()
        used_rng.api.AutoFilter(Field=28, Criteria1="<>")
        ws1.range("A2:IL100000").api.Delete(Shift=-4162)
    except Exception:
        pass

    for action in ("ShowAllData",):
        try:
            getattr(ws1.api, action)()
        except Exception:
            pass
    try:
        ws1.api.AutoFilterMode = False
    except Exception:
        pass

    try:
        ws1.api.Sort.SortFields.Clear()
        ws1.api.Sort.SortFields.Add(
            Key=ws1.range("D1").api,
            SortOn=0, Order=1, DataOption=0
        )
        rng_sort = ws1.range("A1").expand().api
        ws1.api.Sort.SetRange(rng_sort)
        ws1.api.Sort.Header = 1
        ws1.api.Sort.Apply()
    except Exception:
        pass

    try:
        ws1.range("A1:CU600").color = (255, 255, 255)
    except Exception:
        pass

    try:
        col_agrupador = ws1.range("A2:A1000").value or []
        for i, valor in enumerate(col_agrupador, start=2):
            if valor:
                ws1.range(f"M{i}").value = "NOVO"
            else:
                break
    except Exception:
        pass

    try:
        col_titulos = ws1.range("C2:C1000").value or []
        for i, titulo in enumerate(col_titulos, start=2):
            if not titulo:
                break
            t = str(titulo).lower()
            if "masculino" in t:
                ws1.range(f"AR{i}").value = "masculino"
            elif "feminino" in t:
                ws1.range(f"AR{i}").value = "feminino"
            elif "unissex" in t:
                ws1.range(f"AR{i}").value = "unissex"
    except Exception:
        pass

    try:
        wb1.macro("AplicarProcxECopiar")()
    except Exception:
        pass

    # ===== CORREÇÃO: Forçar colunas VALOR como TEXTO =====
    # Isso evita que o AnyMarket interprete números/booleanos incorretamente
    try:
        forcar_texto_colunas_valor(ws1)
    except Exception as e:
        print(f"Aviso ao converter VALOR para texto: {e}")

    # Salva em arquivo temporário primeiro (será movido depois) - formato XLSX (sem macros)
    temp_output = os.path.join(BASE_DIR, "data", "temp_output")
    os.makedirs(temp_output, exist_ok=True)
    destino = os.path.join(temp_output, f"resultado_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    wb1.save(destino)
    wb1.close()
    
    return destino  # Retorna o caminho do arquivo gerado

# -------------------------------
# Script 4 - Limpeza final
# -------------------------------
def limpeza_final():
    global wb2_global, app_global
    if wb2_global is not None:
        try:
            wb2_global.close()
        except Exception:
            pass
    if app_global is not None:
        try:
            app_global.quit()
        except Exception:
            pass
        app_global = None

    temp_disk = os.path.join(BASE_DIR, "data", "temp")
    shutil.rmtree(temp_disk, ignore_errors=True)

# -------------------------------
# Fluxo principal
# -------------------------------
def executar_fluxo():
    """Executa o fluxo completo e retorna o caminho do arquivo gerado."""
    global app_global
    arquivo_gerado = None
    try:
        app_global = xw.App(visible=False)
        processar_csv()
        processar_zip()
        arquivo_gerado = manipular_planilhas()
        registrar_historico("✅ Fluxo executado com sucesso")
        print(f"Fluxo concluído. Arquivo: {arquivo_gerado}")
        return arquivo_gerado
    except Exception as e:
        registrar_historico(f"❌ Erro na execução: {str(e)}")
        print(f"Erro no fluxo: {e}")
        raise e
    finally:
        limpeza_final()

# -------------------------------
# Registro de histórico
# -------------------------------
def registrar_historico(status: str):
    os.makedirs(historico_dir_disk, exist_ok=True)
    historico_csv = os.path.join(historico_dir_disk, "log_execucoes.csv")

    agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linha = [agora, status]

    escrever_cabecalho = not os.path.exists(historico_csv)

    with open(historico_csv, mode="a", newline="", encoding="utf-8") as arquivo:
        writer = csv.writer(arquivo)
        if escrever_cabecalho:
            writer.writerow(["Data/Hora", "Status"])
        writer.writerow(linha)