"""
Tela Lista de Preço - Geração de CSVs com datas de vigência
"""
import flet as ft
import os
from datetime import datetime
from services.database_sinc import listar_listas_preco, buscar_lista_preco, atualizar_lista_preco_baixada


def criar_tela_lista_preco(page: ft.Page, save_picker: ft.FilePicker, theme):
    """
    Cria a tela de lista de preço.
    
    Args:
        page: Página Flet
        save_picker: FilePicker para salvar arquivos
        theme: ThemeManager para cores
    
    Returns:
        ft.Column com a tela completa
    """
    
    tabela = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Planilha", weight=ft.FontWeight.W_600, color=theme.get_text_color())),
            ft.DataColumn(ft.Text("Qtd", weight=ft.FontWeight.W_600, color=theme.get_text_color())),
            ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.W_600, color=theme.get_text_color())),
            ft.DataColumn(ft.Text("Ação", weight=ft.FontWeight.W_600, color=theme.get_text_color())),
        ],
        rows=[], 
        heading_row_color=theme.get_header_bg(),
    )
    
    def carregar():
        listas = listar_listas_preco()
        rows = []
        for lp in listas:
            st = "✓" if lp.get('baixado') else "○"
            cor = "#00AA00" if lp.get('baixado') else "#888888"
            
            def baixar(e, lid=lp['id']):
                lista = buscar_lista_preco(lid)
                if not lista: 
                    return
                
                inicio = ft.TextField(label="Início Vigência", hint_text="DD/MM/AAAA", width=200)
                fim = ft.TextField(label="Fim Vigência", hint_text="DD/MM/AAAA", width=200)
                
                def gerar(e):
                    if not inicio.value or not fim.value: 
                        page.snack_bar = ft.SnackBar(ft.Text("Preencha as datas de vigência!"), bgcolor=ft.Colors.RED)
                        page.snack_bar.open = True
                        page.update()
                        return
                    dlg.open = False
                    page.update()
                    
                    # Gerar dados do CSV - consolidar múltiplos arquivos
                    try:
                        import pandas as pd
                        dados = []
                        
                        # Suporte a múltiplos arquivos (separados por |)
                        caminhos = lista['caminho_planilha'].split("|")
                        
                        for caminho in caminhos:
                            caminho = caminho.strip()
                            if not os.path.exists(caminho):
                                continue
                            
                            xl = pd.ExcelFile(caminho)
                            aba = "PRODUTOS" if "PRODUTOS" in xl.sheet_names else xl.sheet_names[0]
                            df = xl.parse(aba)
                            
                            for _, row in df.iterrows():
                                cod = row[df.columns[0]]
                                if pd.isna(cod): 
                                    continue
                                
                                def formatar_preco(valor):
                                    if pd.isna(valor) or valor == "":
                                        return ""
                                    try:
                                        return f"{float(valor):.2f}"
                                    except:
                                        return str(valor)
                                
                                preco_tabela = row[df.columns[40]] if len(df.columns) > 40 else ""
                                preco_promo = row[df.columns[41]] if len(df.columns) > 41 else ""
                                
                                dados.append({
                                    "CodigoProduto": str(cod).strip(),
                                    "PrecoTabela": formatar_preco(preco_tabela),
                                    "PrecoPromocao": formatar_preco(preco_promo),
                                    "InicioVigenciaPromocao": inicio.value,
                                    "TerminoVigenciaPromocao": fim.value
                                })
                        
                        # Adicionar linha final com 'a' minúsculo
                        dados.append({
                            "CodigoProduto": "a",
                            "PrecoTabela": "",
                            "PrecoPromocao": "",
                            "InicioVigenciaPromocao": "",
                            "TerminoVigenciaPromocao": ""
                        })
                        
                        def on_save_result(result):
                            if result.path:
                                try:
                                    caminho_csv = result.path if result.path.endswith('.csv') else result.path + '.csv'
                                    pd.DataFrame(dados).to_csv(caminho_csv, index=False, sep=";", encoding="utf-8-sig")
                                    atualizar_lista_preco_baixada(lid, inicio.value, fim.value, caminho_csv)
                                    page.snack_bar = ft.SnackBar(ft.Text(f"CSV salvo: {os.path.basename(caminho_csv)}"), bgcolor="#000000")
                                    page.snack_bar.open = True
                                    carregar()
                                except Exception as ex:
                                    page.snack_bar = ft.SnackBar(ft.Text(f"Erro ao salvar: {str(ex)}"), bgcolor=ft.Colors.RED)
                                    page.snack_bar.open = True
                                page.update()
                        
                        save_picker.on_result = on_save_result
                        nome_sugerido = f"ListaPreco_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                        save_picker.save_file(file_name=nome_sugerido, allowed_extensions=["csv"])
                        
                    except Exception as ex:
                        import traceback
                        traceback.print_exc()
                        page.snack_bar = ft.SnackBar(ft.Text(f"Erro: {str(ex)}"), bgcolor=ft.Colors.RED)
                        page.snack_bar.open = True
                    page.update()
                
                dlg = ft.AlertDialog(
                    title=ft.Text("Definir Vigência"),
                    content=ft.Column([inicio, fim], tight=True, spacing=15),
                    actions=[
                        ft.TextButton("Cancelar", on_click=lambda e: setattr(dlg, 'open', False) or page.update()),
                        ft.ElevatedButton("Gerar CSV", bgcolor="#000000", color="#FFFFFF", on_click=gerar)
                    ],
                )
                page.overlay.append(dlg)
                dlg.open = True
                page.update()
            
            rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(lp.get('nome_planilha', '-')[:35], size=12)),
                ft.DataCell(ft.Text(str(lp.get('qtd_produtos', 0)), size=12)),
                ft.DataCell(ft.Text(st, size=16, color=cor, weight=ft.FontWeight.BOLD)),
                ft.DataCell(ft.IconButton(ft.Icons.DOWNLOAD, icon_color="#000000", on_click=baixar)),
            ]))
        tabela.rows = rows
        page.update()
    
    carregar()
    
    return ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Text("Lista de Preço", size=28, weight=ft.FontWeight.BOLD, color=theme.get_text_color()),
                ft.Text("Gere CSVs com datas de vigência", size=12, color=theme.get_text_secondary()),
            ], spacing=2),
            padding=ft.padding.only(left=30, right=30, top=25, bottom=20),
            bgcolor=ft.Colors.TRANSPARENT,
        ),
        ft.Container(
            content=tabela,
            bgcolor=theme.get_card_bg(),
            border_radius=12,
            margin=ft.margin.only(left=20, right=20, bottom=20),
            padding=20,
            expand=True,
        ),
    ], spacing=0, expand=True)
