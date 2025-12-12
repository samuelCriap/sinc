"""
Tela Canal - Gerenciamento de produtos por canal
"""
import flet as ft
import csv
import tempfile
import os
import threading
from datetime import datetime
from services.database_sinc import (
    listar_produtos_canal, 
    atualizar_status_produto_canal, 
    atualizar_status_produto_canal_com_erro,
    atualizar_status_em_massa,
    STATUS_PRODUTO
)
from services.auto_refresh import is_auto_refresh_enabled, get_refresh_interval
from utils.theme import COR_CANAL, ABREV

# Controle de auto-refresh
_canal_refresh_timer = [None]


def criar_tela_canal(page: ft.Page, canal_nome: str, file_picker: ft.FilePicker, usuario_logado: list, nav_callback, theme):
    """
    Cria a tela de gerenciamento de produtos de um canal.
    
    Args:
        page: Página Flet
        canal_nome: Nome do canal
        file_picker: FilePicker para seleção de arquivos
        usuario_logado: Lista com dados do usuário logado
        nav_callback: Função para navegação
        theme: ThemeManager para cores
    
    Returns:
        ft.Column com a tela completa
    """
    selecionados = {}
    produtos_data = []
    dados_filtrados = []  # Para exportação
    
    select_all_cb = ft.Checkbox(label="Selecionar Todos", value=False)
    
    tabela = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Container(content=ft.Text(""), width=15)),
            ft.DataColumn(ft.Container(content=ft.Text("SKU", weight=ft.FontWeight.W_600), width=80)),
            ft.DataColumn(ft.Text("Produto", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Marca", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Container(content=ft.Text("Data", weight=ft.FontWeight.W_600), width=80)),
            ft.DataColumn(ft.Container(content=ft.Text("Id Mkp", weight=ft.FontWeight.W_600), width=80)),
            ft.DataColumn(ft.Container(content=ft.Text("Status", weight=ft.FontWeight.W_600), width=80)),
            ft.DataColumn(ft.Container(content=ft.Text("Descrição Erro", weight=ft.FontWeight.W_600), width=400)),
            ft.DataColumn(ft.Text("GTIN", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Categoria", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Container(content=ft.Text("Preço", weight=ft.FontWeight.W_600), width=80)),
            ft.DataColumn(ft.Text("Importado Por", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("CodProdPai", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("CodBarras", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Classe", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Familia", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Grupo", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("SubGrupo", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Peso", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Comprim", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Largura", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Espessura", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("QtdEmb", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("DescPre1", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("DescPre2", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("DescComp1", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("DescComp2", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("DescComp3", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("PrecoTab", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("PrecoPromo", weight=ft.FontWeight.W_600)),
        ],
        rows=[],
        heading_row_color=ft.Colors.TRANSPARENT,
        horizontal_margin=15,
        column_spacing=80,
        data_row_max_height=45,
    )
    
    msg_vazio = ft.Text("Nenhum produto neste canal. Importe uma planilha primeiro.", 
                       size=14, color="#888888", italic=True)
    msg_vazio.visible = False
    
    def on_select_all(e):
        val = select_all_cb.value
        for pid in selecionados:
            selecionados[pid] = val
        carregar_tabela()
    
    select_all_cb.on_change = on_select_all
    
    # Filtros
    filtro_sku = ft.TextField(label="SKU", width=150, on_change=lambda e: carregar_tabela())
    filtro_status = ft.Dropdown(
        label="Status",
        width=130,
        options=[
            ft.dropdown.Option("", "Todos"),
            ft.dropdown.Option("ATIVO", "Ativo"),
            ft.dropdown.Option("CATALOGANDO", "Catalogando"),
            ft.dropdown.Option("ERRO", "Erro"),
            ft.dropdown.Option("SEM_STATUS", "Sem Status"),
        ],
        on_change=lambda e: carregar_tabela(),
    )
    data_inicio = ft.TextField(label="Data Início", hint_text="DD/MM/AAAA", width=120, on_change=lambda e: carregar_tabela())
    data_fim = ft.TextField(label="Data Fim", hint_text="DD/MM/AAAA", width=120, on_change=lambda e: carregar_tabela())
    
    def carregar_tabela(termo=""):
        nonlocal produtos_data, dados_filtrados
        dados_filtrados = []  # Limpar antes
        if not produtos_data:
            produtos = listar_produtos_canal(canal_nome)
            produtos_data = produtos
        else:
            produtos = produtos_data
        
        # Filtragem
        itens_filtrados = []
        f_status = filtro_status.value
        f_sku = (filtro_sku.value or "").strip().lower()
        d_ini = datetime.strptime(data_inicio.value, "%d/%m/%Y") if data_inicio.value and len(data_inicio.value)==10 else None
        d_fim = datetime.strptime(data_fim.value, "%d/%m/%Y") if data_fim.value and len(data_fim.value)==10 else None
        
        for p in produtos:
            # Filtro SKU
            if f_sku:
                sku_prod = (p.get('sku', '') or p.get('codigo_produto', '') or '').lower()
                if f_sku not in sku_prod:
                    continue
            
            # Filtro Status
            if f_status and p.get('status') != f_status:
                continue
            
            # Filtro Data
            data_obj = None
            created_at = p.get('created_at')
            if created_at:
                try:
                    data_str = created_at.split('.')[0]
                    data_obj = datetime.strptime(data_str, "%Y-%m-%d %H:%M:%S")
                except:
                    pass
            
            if d_ini and data_obj and data_obj < d_ini: continue
            if d_fim and data_obj and data_obj > d_fim.replace(hour=23, minute=59, second=59): continue
            
            itens_filtrados.append(p)
        
        produtos = itens_filtrados

        if not produtos:
            msg_vazio.visible = True
            tabela.visible = False
        else:
            msg_vazio.visible = False
            tabela.visible = True
            rows = []
            for p in produtos:
                pid = p.get('produto_id') or p.get('id')
                status_atual = p.get('status', '') or ''
                
                created_at = p.get('created_at')
                data_fmt = ""
                if created_at:
                    try:
                        data_fmt = datetime.strptime(created_at.split('.')[0], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
                    except:
                        data_fmt = created_at or ""
                
                if pid not in selecionados:
                    selecionados[pid] = False
                
                def on_check(e, pid=pid):
                    selecionados[pid] = e.control.value
                    page.update()
                
                cb = ft.Checkbox(value=selecionados.get(pid, False), on_change=on_check)
                
                cor_status = {"ATIVO": "#22C55E", "CATALOGANDO": "#F59E0B", "ERRO": "#EF4444"}.get(status_atual, "#888888")
                status_badge = ft.Container(
                    content=ft.Text(status_atual or "—", size=10, color="#FFFFFF" if status_atual else "#666666"),
                    bgcolor=cor_status if status_atual else "#E0E0E0",
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=4,
                )
                
                desc_erro = p.get('motivo_bloqueio', '') or '—'
                id_mkp = p.get('cod_marketplace', '') or '—'
                
                rows.append(ft.DataRow(cells=[
                    ft.DataCell(cb),
                    ft.DataCell(ft.Text(p.get('codigo_produto', ''), size=12, weight=ft.FontWeight.W_500)),
                    ft.DataCell(ft.Text((p.get('descricao', '') or '')[:50], size=11)),
                    ft.DataCell(ft.Text(p.get('marca', '') or '', size=11)),
                    ft.DataCell(ft.Text(data_fmt, size=11)),
                    ft.DataCell(ft.Text(id_mkp, size=11)),
                    ft.DataCell(status_badge),
                    ft.DataCell(ft.Container(
                        content=ft.Text(desc_erro[:150], size=10, color="#EF4444" if desc_erro != '—' else theme.get_text_secondary(), overflow=ft.TextOverflow.ELLIPSIS),
                        width=400
                    )),
                    ft.DataCell(ft.Text(p.get('gtin', '') or '', size=11)),
                    ft.DataCell(ft.Text((p.get('categoria', '') or '')[:30], size=11)),
                    ft.DataCell(ft.Text(f"R$ {p.get('preco', 0) or 0:.2f}".replace('.', ','), size=11)),
                    ft.DataCell(ft.Text(p.get('importado_por', '') or '', size=11)),
                    ft.DataCell(ft.Text(p.get('col_b', '') or '', size=11)),
                    ft.DataCell(ft.Text(p.get('col_c', '') or '', size=11)),
                    ft.DataCell(ft.Text(p.get('col_i', '') or '', size=11)),
                    ft.DataCell(ft.Text(p.get('col_k', '') or '', size=11)),
                    ft.DataCell(ft.Text(p.get('col_l', '') or '', size=11)),
                    ft.DataCell(ft.Text(p.get('col_m', '') or '', size=11)),
                    ft.DataCell(ft.Text(p.get('col_n', '') or '', size=11)),
                    ft.DataCell(ft.Text(p.get('col_o', '') or '', size=11)),
                    ft.DataCell(ft.Text(p.get('col_p', '') or '', size=11)),
                    ft.DataCell(ft.Text(p.get('col_q', '') or '', size=11)),
                    ft.DataCell(ft.Text(p.get('col_r', '') or '', size=11)),
                    ft.DataCell(ft.Text(p.get('col_ab', '') or '', size=11)),
                    ft.DataCell(ft.Text(p.get('col_ac', '') or '', size=11)),
                    ft.DataCell(ft.Text(p.get('col_ae', '') or '', size=11)),
                    ft.DataCell(ft.Text(p.get('col_af', '') or '', size=11)),
                    ft.DataCell(ft.Text(p.get('col_ag', '') or '', size=11)),
                    ft.DataCell(ft.Text(p.get('col_ao', '') or '', size=11)),
                    ft.DataCell(ft.Text(p.get('col_ap', '') or '', size=11)),
                ]))
                
                # Guardar para exportação
                dados_filtrados.append({
                    'SKU': p.get('codigo_produto', ''),
                    'Produto': (p.get('descricao', '') or '')[:50],
                    'Marca': p.get('marca', '') or '',
                    'Data': data_fmt,
                    'Status': status_atual,
                    'Erro': desc_erro if desc_erro != '—' else '',
                })
            tabela.rows = rows
        page.update()
    
    def aplicar_status(status):
        nonlocal produtos_data
        ids = [pid for pid, sel in selecionados.items() if sel]
        if not ids:
            page.snack_bar = ft.SnackBar(ft.Text("Selecione pelo menos um produto!"), bgcolor="#EF4444")
            page.snack_bar.open = True
            page.update()
            return
        
        if status == "ERRO":
            erro_tf = ft.TextField(label="Descrição do erro", multiline=True, min_lines=2)
            
            def confirmar_erro(e):
                nonlocal produtos_data
                motivo = erro_tf.value or ""
                for pid in ids:
                    atualizar_status_produto_canal_com_erro(pid, canal_nome, "ERRO", motivo)
                dlg.open = False
                produtos_data = []
                carregar_tabela()
                page.snack_bar = ft.SnackBar(ft.Text(f"{len(ids)} produtos marcados como ERRO"), bgcolor="#000000")
                page.snack_bar.open = True
                page.update()
            
            dlg = ft.AlertDialog(
                title=ft.Text("Marcar como Erro"),
                content=ft.Column([ft.Text(f"Você selecionou {len(ids)} produto(s)."), erro_tf], tight=True),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: setattr(dlg, 'open', False) or page.update()),
                    ft.ElevatedButton("Confirmar", bgcolor="#EF4444", color="#FFFFFF", on_click=confirmar_erro),
                ],
            )
            page.overlay.append(dlg)
            dlg.open = True
            page.update()
        else:
            for pid in ids:
                atualizar_status_produto_canal_com_erro(pid, canal_nome, status, "")
            produtos_data = []
            carregar_tabela()
            page.snack_bar = ft.SnackBar(ft.Text(f"{len(ids)} produtos atualizados para {status or 'SEM STATUS'}"), bgcolor="#000000")
            page.snack_bar.open = True
            page.update()
    
    def importar_status(e):
        def on_pick_status(r):
            nonlocal produtos_data
            if r.files and len(r.files) > 0:
                import pandas as pd
                from services.database_sinc import atualizar_status_em_massa_com_erro
                
                arquivo = r.files[0].path
                try:
                    prog_txt = ft.Text("Lendo arquivo...", size=14)
                    prog_bar = ft.ProgressBar(width=300, value=None)
                    dlg_prog = ft.AlertDialog(
                        title=ft.Text("Importando Status"),
                        content=ft.Column([prog_txt, prog_bar], tight=True, width=350),
                        modal=True
                    )
                    page.overlay.append(dlg_prog)
                    dlg_prog.open = True
                    page.update()
                    
                    # ══════════════════════════════════════════════════════════════
                    # NETSHOES - Parsing específico (CSV com status JSON na coluna I)
                    # ══════════════════════════════════════════════════════════════
                    if canal_nome == "NETSHOES":
                        prog_txt.value = "Processando CSV Netshoes..."
                        page.update()
                        
                        # Ler como CSV (ou converter se for Excel)
                        if arquivo.lower().endswith('.csv'):
                            # Tentar diferentes encodings + detecção automática de separador
                            try:
                                df = pd.read_csv(arquivo, header=None, encoding='utf-8', sep=None, engine='python', on_bad_lines='skip')
                            except UnicodeDecodeError:
                                try:
                                    df = pd.read_csv(arquivo, header=None, encoding='latin-1', sep=None, engine='python', on_bad_lines='skip')
                                except:
                                    df = pd.read_csv(arquivo, header=None, encoding='cp1252', sep=None, engine='python', on_bad_lines='skip')
                        else:
                            # Converter Excel para DataFrame
                            df = pd.read_excel(arquivo, header=None)
                        
                        total_linhas = len(df)
                        print(f"[Netshoes] Arquivo lido: {total_linhas} linhas. Colunas: {len(df.columns)}")
                        
                        # DEBUG: Imprimir primeiras linhas para conferência
                        print(f"--- AMOSTRA DAS PRIMEIRAS 3 LINHAS ---")
                        print(df.head(3).to_string())
                        print(f"--------------------------------------")
                        
                        if total_linhas < 2:
                            dlg_prog.open = False
                            page.update()
                            page.snack_bar = ft.SnackBar(ft.Text("Arquivo vazio ou sem dados!"), bgcolor="#EF4444")
                            page.snack_bar.open = True
                            return
                        
                        atualizacoes = {}  # {sku: (status, motivo)}
                        count_ativo = 0
                        count_cat = 0
                        count_erro = 0
                        
                        prog_txt.value = f"Processando {total_linhas:,} linhas..."
                        prog_bar.value = 0
                        page.update()
                        
                        for idx, row in df.iterrows():
                            if idx % 5000 == 0:
                                prog_bar.value = (idx + 1) / total_linhas
                                prog_txt.value = f"Processando... {idx+1:,} de {total_linhas:,}"
                                page.update()
                            
                            # Coluna B (índice 1) = SKU
                            # Coluna I (índice 8) = Status
                            if len(row) < 9:
                                continue
                            
                            sku = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
                            status_raw = str(row.iloc[8]).strip() if pd.notna(row.iloc[8]) else ""
                            
                            if not sku or sku.lower() in ['none', 'nan', '', 'sku']:
                                continue
                            
                            # Parsing do status (busca no texto JSON)
                            status_upper = status_raw.upper()
                            
                            if '"APPROVED"' in status_upper or "'APPROVED'" in status_upper or 'APPROVED' in status_upper:
                                atualizacoes[sku] = ("ATIVO", None)
                                count_ativo += 1
                            elif '"CATALOGING"' in status_upper or "'CATALOGING'" in status_upper or 'CATALOGING' in status_upper:
                                atualizacoes[sku] = ("CATALOGANDO", None)
                                count_cat += 1
                            elif '"CRITICIZED"' in status_upper or "'CRITICIZED'" in status_upper or 'CRITICIZED' in status_upper:
                                # Erro - salva a célula inteira como motivo
                                atualizacoes[sku] = ("ERRO", status_raw[:500])  # Limita a 500 chars
                                count_erro += 1
                        
                        print(f"[Netshoes] SKUs processados: {len(atualizacoes)} (Ativos: {count_ativo}, Cat: {count_cat}, Erro: {count_erro})")
                    # ══════════════════════════════════════════════════════════════
                    # CENTAURO - Lógica Específica (CSV: Col F=SKU, Col G=ID/Status)
                    # ══════════════════════════════════════════════════════════════
                    elif canal_nome == "CENTAURO":
                        prog_txt.value = "Processando CSV Centauro..."
                        page.update()
                        
                        # Ler como CSV (com fallbacks)
                        df = None
                        try:
                             df = pd.read_csv(arquivo, header=None, encoding='utf-8', sep=None, engine='python', on_bad_lines='skip')
                        except:
                            try:
                                df = pd.read_csv(arquivo, header=None, encoding='latin-1', sep=None, engine='python', on_bad_lines='skip')
                            except:
                                df = pd.read_csv(arquivo, header=None, encoding='cp1252', sep=None, engine='python', on_bad_lines='skip')
                        
                        total_linhas = len(df)
                        print(f"[Centauro] Arquivo lido: {total_linhas} linhas. Colunas: {len(df.columns)}")
                        
                        if total_linhas < 2:
                            dlg_prog.open = False
                            page.update()
                            page.snack_bar = ft.SnackBar(ft.Text("Arquivo vazio!"), bgcolor="#EF4444")
                            page.snack_bar.open = True
                            return

                        atualizacoes = {}
                        count_ativo = 0
                        count_cat = 0
                        count_erro = 0
                        
                        prog_txt.value = f"Processando {total_linhas:,} linhas..."
                        prog_bar.value = 0
                        page.update()
                        
                        for idx, row in df.iterrows():
                             if idx % 5000 == 0:
                                prog_bar.value = (idx + 1) / total_linhas
                                prog_txt.value = f"Processando... {idx+1:,} de {total_linhas:,}"
                                page.update()
                             
                             # F=5, G=6 (0-indexed)
                             if len(row) < 7: continue
                             
                             sku = str(row.iloc[5]).strip() if pd.notna(row.iloc[5]) else ""
                             col_g = str(row.iloc[6]).strip() if pd.notna(row.iloc[6]) else ""
                             
                             if not sku or sku.lower() in ['sku', 'codigo', 'nan', 'none']: continue
                             
                             # Lógica
                             if not col_g or col_g.lower() in ['nan', 'none', '']:
                                 # Ausente -> Catalogando
                                 atualizacoes[sku] = ("CATALOGANDO", None)
                                 count_cat += 1
                             elif "ERRO" in col_g.upper():
                                 # Erro
                                 atualizacoes[sku] = ("ERRO", col_g[:500])
                                 count_erro += 1
                             else:
                                 # Tem valor -> Ativo + Salvar ID
                                 atualizacoes[sku] = ("ATIVO", None, col_g)
                                 count_ativo += 1
                                 
                        print(f"[Centauro] SKUs: {len(atualizacoes)} (Ativos: {count_ativo}, Cat: {count_cat}, Erro: {count_erro})")

                    # ══════════════════════════════════════════════════════════════
                    # MELI - Lógica Específica (Col S=SKU, Col I=Status, Col A=ID)
                    # ══════════════════════════════════════════════════════════════
                    elif canal_nome == "MELI":
                        prog_txt.value = "Processando planilha MELI..."
                        page.update()
                        
                        # Ler Excel ou CSV
                        if arquivo.lower().endswith('.csv'):
                            try:
                                df = pd.read_csv(arquivo, header=None, encoding='utf-8', sep=None, engine='python', on_bad_lines='skip')
                            except:
                                try:
                                    df = pd.read_csv(arquivo, header=None, encoding='latin-1', sep=None, engine='python', on_bad_lines='skip')
                                except:
                                    df = pd.read_csv(arquivo, header=None, encoding='cp1252', sep=None, engine='python', on_bad_lines='skip')
                        else:
                            df = pd.read_excel(arquivo, header=None)
                        
                        total_linhas = len(df)
                        print(f"[MELI] Arquivo lido: {total_linhas} linhas. Colunas: {len(df.columns)}")
                        
                        if total_linhas < 2:
                            dlg_prog.open = False
                            page.update()
                            page.snack_bar = ft.SnackBar(ft.Text("Arquivo vazio!"), bgcolor="#EF4444")
                            page.snack_bar.open = True
                            return
                        
                        atualizacoes = {}
                        count_ativo = 0
                        count_cat = 0
                        count_erro = 0
                        count_paused = 0
                        
                        prog_txt.value = f"Processando {total_linhas:,} linhas..."
                        prog_bar.value = 0
                        page.update()
                        
                        for idx, row in df.iterrows():
                            if idx % 5000 == 0:
                                prog_bar.value = (idx + 1) / total_linhas
                                prog_txt.value = f"Processando... {idx+1:,} de {total_linhas:,}"
                                page.update()
                            
                            # Coluna S (índice 18) = SKU
                            # Coluna I (índice 8) = Status
                            # Coluna A (índice 0) = ID Marketplace
                            if len(row) < 19:
                                continue
                            
                            sku = str(row.iloc[18]).strip() if pd.notna(row.iloc[18]) else ""
                            status_raw = str(row.iloc[8]).strip().lower() if pd.notna(row.iloc[8]) else ""
                            id_meli = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
                            
                            if not sku or sku.lower() in ['none', 'nan', '', 'sku', 'seller_custom_field']:
                                continue
                            
                            # Mapear status
                            if status_raw == 'active':
                                atualizacoes[sku] = ("ATIVO", None, id_meli)
                                count_ativo += 1
                            elif status_raw == 'paused':
                                atualizacoes[sku] = ("ATIVO", "Possivelmente está sem estoque (paused)", id_meli)
                                count_paused += 1
                            elif status_raw == 'under_review':
                                atualizacoes[sku] = ("CATALOGANDO", None, id_meli)
                                count_cat += 1
                            elif status_raw == 'inactive':
                                atualizacoes[sku] = ("ERRO", "Status: inactive", id_meli)
                                count_erro += 1
                        
                        print(f"[MELI] SKUs: {len(atualizacoes)} (Ativos: {count_ativo}, Paused: {count_paused}, Cat: {count_cat}, Erro: {count_erro})")

                    # ══════════════════════════════════════════════════════════════
                    # OUTROS CANAIS - Lógica padrão (Excel com Col B=SKU, Col G=Status, Col D=ID)
                    # Shopee, Renner, Shein, Amazon, Dafiti, TikTok
                    # ══════════════════════════════════════════════════════════════
                    else:
                        prog_txt.value = "Processando planilha..."
                        page.update()
                        
                        # Ler Excel ou CSV com colunas B(1), D(3), G(6)
                        if arquivo.lower().endswith('.csv'):
                            try:
                                df = pd.read_csv(arquivo, header=None, encoding='utf-8', sep=None, engine='python', on_bad_lines='skip')
                            except:
                                try:
                                    df = pd.read_csv(arquivo, header=None, encoding='latin-1', sep=None, engine='python', on_bad_lines='skip')
                                except:
                                    df = pd.read_csv(arquivo, header=None, encoding='cp1252', sep=None, engine='python', on_bad_lines='skip')
                        else:
                            df = pd.read_excel(arquivo, header=None)
                        
                        total_linhas = len(df)
                        print(f"[{canal_nome}] Planilha: {total_linhas} linhas. Colunas: {len(df.columns)}")
                        
                        if total_linhas < 2:
                            dlg_prog.open = False
                            page.update()
                            page.snack_bar = ft.SnackBar(ft.Text("Planilha vazia!"), bgcolor="#EF4444")
                            page.snack_bar.open = True
                            page.update()
                            return
                        
                        prog_txt.value = f"Processando {total_linhas:,} linhas..."
                        prog_bar.value = 0
                        page.update()
                        
                        atualizacoes = {}  # {sku: (status, motivo, id_marketplace)}
                        count_erro = 0
                        count_ativo = 0
                        count_cat = 0
                        
                        for idx, row in df.iterrows():
                            if idx % 5000 == 0:
                                prog_bar.value = (idx + 1) / total_linhas
                                prog_txt.value = f"Processando... {idx+1:,} de {total_linhas:,}"
                                page.update()
                            
                            # Coluna B (índice 1) = SKU
                            # Coluna D (índice 3) = ID Marketplace
                            # Coluna G (índice 6) = Status
                            if len(row) < 7:
                                continue
                            
                            sku = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
                            id_marketplace = str(row.iloc[3]).strip() if len(row) > 3 and pd.notna(row.iloc[3]) else ""
                            st_raw = str(row.iloc[6]).strip().upper() if pd.notna(row.iloc[6]) else ""
                            
                            if not sku or sku.lower() in ['none', 'nan', '', 'sku']:
                                continue
                            
                            novo_status = "CATALOGANDO"
                            if st_raw in ['ATIVO', 'OK', 'SUCESSO', 'PROCESSADO', 'ACTIVE', 'APPROVED']:
                                novo_status = "ATIVO"
                                count_ativo += 1
                            elif 'ERRO' in st_raw or 'FALHA' in st_raw or 'ERROR' in st_raw or 'REJECTED' in st_raw:
                                novo_status = "ERRO"
                                count_erro += 1
                            else:
                                count_cat += 1
                            
                            atualizacoes[sku] = (novo_status, None, id_marketplace)
                    
                    # ══════════════════════════════════════════════════════════════
                    # SALVAR NO BANCO DE DADOS
                    # ══════════════════════════════════════════════════════════════
                    primeiros_skus = list(atualizacoes.keys())[:10]
                    print(f"Total SKUs lidos: {len(atualizacoes)}")
                    print(f"Primeiros SKUs: {primeiros_skus}")
                    
                    if atualizacoes:
                        prog_txt.value = "Salvando no banco de dados..."
                        prog_bar.value = None
                        page.update()
                        
                        skus_exemplo = list(atualizacoes.keys())[:5]
                        qtd = atualizar_status_em_massa_com_erro(canal_nome, atualizacoes, usuario=usuario_logado[0].get('username', 'admin'))
                        
                        dlg_prog.open = False
                        page.update()
                        
                        if qtd > 0:
                            page.snack_bar = ft.SnackBar(ft.Text(f"✅ {qtd} produtos atualizados!\nAtivos: {count_ativo}, Erros: {count_erro}, Catalogando: {count_cat}"), bgcolor="#22C55E")
                        else:
                            page.snack_bar = ft.SnackBar(ft.Text(f"⚠️ Nenhum produto atualizado! {len(atualizacoes)} SKUs não encontrados.\nExemplo: {skus_exemplo[0] if skus_exemplo else 'N/A'}"), bgcolor="#F59E0B")
                        page.snack_bar.open = True
                        produtos_data = []
                        carregar_tabela()
                    else:
                        dlg_prog.open = False
                        page.update()
                        page.snack_bar = ft.SnackBar(ft.Text("Nenhum produto válido encontrado no arquivo."), bgcolor="#EF4444")
                        page.snack_bar.open = True
                        
                except Exception as ex:
                    import traceback
                    traceback.print_exc()
                    if 'dlg_prog' in locals():
                        dlg_prog.open = False
                    page.update()
                    page.snack_bar = ft.SnackBar(ft.Text(f"Erro na importação: {str(ex)}"), bgcolor="#EF4444")
                    page.snack_bar.open = True
                page.update()

        file_picker.on_result = on_pick_status
        # Netshoes e Centauro aceitam CSV, outros canais aceitam Excel
        if canal_nome in ["NETSHOES", "CENTAURO"]:
            file_picker.pick_files(allowed_extensions=["csv", "xlsx", "xls"], allow_multiple=False)
        else:
            file_picker.pick_files(allowed_extensions=["xlsx", "xls"], allow_multiple=False)
    
    def exportar(e):
        if not dados_filtrados:
            page.snack_bar = ft.SnackBar(ft.Text("Nenhum dado para exportar!"), bgcolor="#EF4444")
            page.snack_bar.open = True
            page.update()
            return
        
        def on_save(result):
            if result.path:
                try:
                    import pandas as pd
                    df = pd.DataFrame(dados_filtrados)
                    caminho = result.path if result.path.endswith('.xlsx') else result.path + '.xlsx'
                    df.to_excel(caminho, index=False)
                    page.snack_bar = ft.SnackBar(ft.Text(f"Exportado: {os.path.basename(caminho)}"), bgcolor="#22C55E")
                    page.snack_bar.open = True
                except Exception as ex:
                    page.snack_bar = ft.SnackBar(ft.Text(f"Erro: {str(ex)}"), bgcolor="#EF4444")
                    page.snack_bar.open = True
                page.update()
        
        file_picker.on_result = on_save
        file_picker.save_file(file_name=f"{canal_nome}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", allowed_extensions=["xlsx"])

    # Auto-refresh controlado globalmente
    def auto_refresh():
        nonlocal produtos_data
        if is_auto_refresh_enabled():
            try:
                produtos_data = []  # Força recarregar do banco
                carregar_tabela()
            except:
                pass
        interval = get_refresh_interval()
        _canal_refresh_timer[0] = threading.Timer(float(interval), auto_refresh)
        _canal_refresh_timer[0].daemon = True
        _canal_refresh_timer[0].start()
    
    carregar_tabela()
    cor = COR_CANAL.get(canal_nome, "#888888")
    
    # Inicia auto-refresh
    interval = get_refresh_interval()
    _canal_refresh_timer[0] = threading.Timer(float(interval), auto_refresh)
    _canal_refresh_timer[0].daemon = True
    _canal_refresh_timer[0].start()
    
    # Botão de Importar Status
    btn_importar_status = ft.Container()
    if canal_nome in ['NETSHOES', 'CENTAURO', 'MELI', 'SHOPEE', 'RENNER', 'SHEIN', 'DAFITI', 'AMAZON', 'TIKTOK']:
        tooltip_txt = "Importar CSV/XLSX de status (NETSHOES: col B=SKU, col I=Status)" if canal_nome == "NETSHOES" else "Importar planilha de status (SKU na col B, Status na col G)"
        btn_importar_status = ft.ElevatedButton(
            "Importar Status", icon=ft.Icons.UPLOAD_FILE,
            bgcolor="#333333" if theme.is_dark[0] else "#000000", color="#FFFFFF",
            on_click=importar_status,
            tooltip=tooltip_txt
        )
    
    return ft.Column([
        ft.Container(
            content=ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, icon_color=theme.get_text_color(), on_click=lambda e: nav_callback(1)),
                ft.Container(
                    content=ft.Text(ABREV[canal_nome], size=14, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                    bgcolor=cor, width=40, height=40, border_radius=20, alignment=ft.alignment.center,
                ),
                ft.Column([
                    ft.Text(canal_nome, size=24, weight=ft.FontWeight.BOLD, color=theme.get_text_color()),
                    ft.Text("Gerencie produtos deste canal", size=12, color=theme.get_text_secondary()),
                ], spacing=2, expand=True),
                btn_importar_status,
            ]),
            padding=ft.padding.only(left=20, right=30, top=20, bottom=10),
            bgcolor=ft.Colors.TRANSPARENT,
        ),
        ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Filtros:", weight=ft.FontWeight.BOLD, color=theme.get_text_secondary()),
                    filtro_sku, filtro_status, data_inicio, data_fim,
                ], spacing=10, scroll=ft.ScrollMode.HIDDEN),
                ft.Divider(color=theme.get_border_color()),
                ft.Row([
                    select_all_cb,
                    ft.Container(width=20),
                    ft.Text("Ações em massa:", size=12, color=theme.get_text_secondary()),
                    ft.ElevatedButton("ATIVO", bgcolor="#22C55E", color="#FFFFFF", on_click=lambda e: aplicar_status("ATIVO")),
                    ft.ElevatedButton("CAT", bgcolor="#F59E0B", color="#FFFFFF", on_click=lambda e: aplicar_status("CATALOGANDO")),
                    ft.ElevatedButton("ERRO", bgcolor="#EF4444", color="#FFFFFF", on_click=lambda e: aplicar_status("ERRO")),
                    ft.OutlinedButton("Sem Status", on_click=lambda e: aplicar_status("")),
                    ft.Container(expand=True),
                    ft.ElevatedButton("Exportar", icon=ft.Icons.DOWNLOAD, bgcolor="#0EA5E9", color="#FFFFFF", on_click=exportar),
                ], spacing=10, scroll=ft.ScrollMode.HIDDEN),
            ], spacing=15),
            padding=ft.padding.symmetric(horizontal=20, vertical=15),
            bgcolor=theme.get_card_bg(),
        ),
        ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            msg_vazio,
                            tabela,
                        ],
                        scroll=ft.ScrollMode.AUTO,  # Scroll vertical dentro
                        expand=True,
                        spacing=0,
                    )
                ],
                scroll=ft.ScrollMode.ALWAYS,  # Scroll horizontal sempre visível (por fora)
            ),
            expand=True,
            bgcolor=theme.get_card_bg(),
            margin=0,
            border_radius=0,
            padding=ft.padding.only(left=10, right=10, top=5, bottom=0),
        ),
    ], spacing=0, expand=True)
