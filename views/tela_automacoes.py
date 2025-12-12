"""
Tela Automações - Execução de fluxos automatizados (Excel, CSV, etc)
Usa janela modal para exibir log de execução
"""
import flet as ft
import threading
import shutil
import os
from datetime import datetime


def criar_tela_automacoes(page: ft.Page, file_picker: ft.FilePicker, theme):
    """
    Cria a tela de automações com layout compacto.
    """
    # Armazena o arquivo gerado temporariamente
    arquivo_temp = [None]
    
    def executar_fluxo_excel(e):
        """Executa o fluxo e mostra progresso em janela modal."""
        try:
            from excel import executar_fluxo
        except ImportError as ie:
            page.snack_bar = ft.SnackBar(ft.Text(f"Erro: {ie}"), bgcolor="#EF4444")
            page.snack_bar.open = True
            page.update()
            return
        
        # Log para a janela modal
        log_items = []
        log_column = ft.Column([], scroll=ft.ScrollMode.AUTO, spacing=4)
        
        def adicionar_log_modal(mensagem, tipo="info"):
            cores = {"info": "#888888", "sucesso": "#22C55E", "erro": "#EF4444", "aviso": "#F59E0B"}
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_column.controls.append(
                ft.Text(f"[{timestamp}] {mensagem}", size=11, color=cores.get(tipo, "#888888"))
            )
            page.update()
        
        # Criar janela modal
        btn_fechar = ft.ElevatedButton("Fechar", disabled=True, on_click=lambda e: fechar_modal())
        btn_salvar = ft.ElevatedButton("Salvar Como...", icon=ft.Icons.SAVE_AS, 
                                       bgcolor="#0EA5E9", color="#FFFFFF", 
                                       disabled=True, on_click=lambda e: salvar_resultado())
        
        status_icon = ft.ProgressRing(width=20, height=20, stroke_width=3)
        status_text = ft.Text("Executando...", size=12, color="#F59E0B", weight=ft.FontWeight.W_500)
        
        dlg_modal = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.IMAGE, size=24, color="#22C55E"),
                ft.Text("Planilha de Imagens", weight=ft.FontWeight.BOLD, size=16),
            ], spacing=10),
            content=ft.Container(
                content=ft.Column([
                    # Status
                    ft.Row([status_icon, status_text], spacing=10),
                    ft.Divider(height=10),
                    # Log
                    ft.Container(
                        content=log_column,
                        bgcolor="#1A1A1A" if theme.is_dark[0] else "#F5F5F5",
                        padding=10,
                        border_radius=8,
                        height=200,
                        width=400,
                    ),
                ], spacing=10),
                width=420,
            ),
            actions=[btn_salvar, btn_fechar],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        def fechar_modal():
            dlg_modal.open = False
            page.update()
        
        def salvar_resultado():
            if not arquivo_temp[0] or not os.path.exists(arquivo_temp[0]):
                return
            
            def on_save(ev):
                if ev.path:
                    try:
                        destino = ev.path if ev.path.endswith('.xlsx') else ev.path + '.xlsx'
                        shutil.copy2(arquivo_temp[0], destino)
                        adicionar_log_modal(f"✅ Salvo: {os.path.basename(destino)}", "sucesso")
                        try: os.remove(arquivo_temp[0])
                        except: pass
                        arquivo_temp[0] = None
                        btn_salvar.disabled = True
                        page.update()
                    except Exception as ex:
                        adicionar_log_modal(f"❌ Erro ao salvar: {ex}", "erro")
            
            file_picker.on_result = on_save
            file_picker.save_file(
                file_name=f"planilha_imagens_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                allowed_extensions=["xlsx"]
            )
        
        # Abrir modal
        page.overlay.append(dlg_modal)
        dlg_modal.open = True
        page.update()
        
        # Executar em thread separada
        def run():
            try:
                adicionar_log_modal("Iniciando processamento...", "info")
                adicionar_log_modal("Buscando arquivos na pasta Downloads...", "info")
                adicionar_log_modal("Processando CSV...", "info")
                adicionar_log_modal("Processando ZIP...", "info")
                adicionar_log_modal("Manipulando planilhas...", "info")
                
                arquivo = executar_fluxo()
                arquivo_temp[0] = arquivo
                
                adicionar_log_modal("✅ Processamento concluído com sucesso!", "sucesso")
                adicionar_log_modal(f"Arquivo gerado: {os.path.basename(arquivo)}", "sucesso")
                
                # Atualizar UI
                status_icon.visible = False
                status_text.value = "✅ Concluído!"
                status_text.color = "#22C55E"
                btn_fechar.disabled = False
                btn_salvar.disabled = False
                page.update()
                
            except Exception as ex:
                adicionar_log_modal(f"❌ Erro: {str(ex)}", "erro")
                status_icon.visible = False
                status_text.value = "❌ Erro na execução"
                status_text.color = "#EF4444"
                btn_fechar.disabled = False
                page.update()
        
        threading.Thread(target=run, daemon=True).start()
    
    # Card de automação (sem log embaixo)
    card_planilha_imagens = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.IMAGE, size=32, color="#22C55E"),
            ft.Column([
                ft.Text("Planilha de Imagens", size=16, weight=ft.FontWeight.BOLD, color=theme.get_text_color()),
                ft.Text("Faça o Donwload do arquivo URL OmnieOne e o Arquivo SKU Anymarket e executa", size=11, color=theme.get_text_secondary()),
            ], spacing=2, expand=True),
            ft.ElevatedButton(
                "Executar", 
                icon=ft.Icons.PLAY_ARROW, 
                bgcolor="#22C55E", 
                color="#FFFFFF", 
                height=40,
                on_click=executar_fluxo_excel
            ),
        ], spacing=15, alignment=ft.MainAxisAlignment.START),
        padding=20,
        bgcolor=theme.get_card_bg(),
        border_radius=12,
    )
    
    # ══════════════════════════════════════════════════════════════
    # AUTOMAÇÃO SHOPEE
    # ══════════════════════════════════════════════════════════════
    arquivo_temp_shopee = [None]
    
    def executar_fluxo_shopee(e):
        """Executa o fluxo Shopee e mostra progresso em janela modal."""
        try:
            from shopee import executar_fluxo_shopee as shopee_run
        except ImportError as ie:
            page.snack_bar = ft.SnackBar(ft.Text(f"Erro: {ie}"), bgcolor="#EF4444")
            page.snack_bar.open = True
            page.update()
            return
        
        log_column_shopee = ft.Column([], scroll=ft.ScrollMode.AUTO, spacing=4)
        
        def adicionar_log(mensagem, tipo="info"):
            cores = {"info": "#888888", "sucesso": "#22C55E", "erro": "#EF4444", "aviso": "#F59E0B"}
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_column_shopee.controls.append(
                ft.Text(f"[{timestamp}] {mensagem}", size=11, color=cores.get(tipo, "#888888"))
            )
            page.update()
        
        btn_fechar_sp = ft.ElevatedButton("Fechar", disabled=True, on_click=lambda e: fechar_modal_sp())
        btn_salvar_sp = ft.ElevatedButton("Salvar Como...", icon=ft.Icons.SAVE_AS, 
                                       bgcolor="#FF5722", color="#FFFFFF", 
                                       disabled=True, on_click=lambda e: salvar_resultado_sp())
        
        status_icon_sp = ft.ProgressRing(width=20, height=20, stroke_width=3)
        status_text_sp = ft.Text("Executando...", size=12, color="#F59E0B", weight=ft.FontWeight.W_500)
        
        dlg_modal_sp = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.STOREFRONT, size=24, color="#FF5722"),
                ft.Text("Automação Shopee", weight=ft.FontWeight.BOLD, size=16),
            ], spacing=10),
            content=ft.Container(
                content=ft.Column([
                    ft.Row([status_icon_sp, status_text_sp], spacing=10),
                    ft.Divider(height=10),
                    ft.Container(
                        content=log_column_shopee,
                        bgcolor="#1A1A1A" if theme.is_dark[0] else "#F5F5F5",
                        padding=10,
                        border_radius=8,
                        height=200,
                        width=400,
                    ),
                ], spacing=10),
                width=420,
            ),
            actions=[btn_salvar_sp, btn_fechar_sp],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        def fechar_modal_sp():
            dlg_modal_sp.open = False
            page.update()
        
        def salvar_resultado_sp():
            if not arquivo_temp_shopee[0] or not os.path.exists(arquivo_temp_shopee[0]):
                return
            
            def on_save_sp(ev):
                if ev.path:
                    try:
                        destino = ev.path if ev.path.endswith('.xlsx') else ev.path + '.xlsx'
                        shutil.copy2(arquivo_temp_shopee[0], destino)
                        adicionar_log(f"✅ Salvo: {os.path.basename(destino)}", "sucesso")
                        try: os.remove(arquivo_temp_shopee[0])
                        except: pass
                        arquivo_temp_shopee[0] = None
                        btn_salvar_sp.disabled = True
                        page.update()
                    except Exception as ex:
                        adicionar_log(f"❌ Erro ao salvar: {ex}", "erro")
            
            file_picker.on_result = on_save_sp
            file_picker.save_file(
                file_name=f"shopee_consolidado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                allowed_extensions=["xlsx"]
            )
        
        page.overlay.append(dlg_modal_sp)
        dlg_modal_sp.open = True
        page.update()
        
        def run_shopee():
            try:
                adicionar_log("Iniciando processamento Shopee...", "info")
                adicionar_log("Buscando arquivos mass_update_sales_info*.zip...", "info")
                adicionar_log("Extraindo planilhas do ZIP...", "info")
                adicionar_log("Processando dados...", "info")
                adicionar_log("Consolidando resultados...", "info")
                
                arquivo = shopee_run()
                arquivo_temp_shopee[0] = arquivo
                
                adicionar_log("✅ Processamento concluído com sucesso!", "sucesso")
                adicionar_log(f"Arquivo gerado: {os.path.basename(arquivo)}", "sucesso")
                
                status_icon_sp.visible = False
                status_text_sp.value = "✅ Concluído!"
                status_text_sp.color = "#22C55E"
                btn_fechar_sp.disabled = False
                btn_salvar_sp.disabled = False
                page.update()
                
            except Exception as ex:
                adicionar_log(f"❌ Erro: {str(ex)}", "erro")
                status_icon_sp.visible = False
                status_text_sp.value = "❌ Erro na execução"
                status_text_sp.color = "#EF4444"
                btn_fechar_sp.disabled = False
                page.update()
        
        threading.Thread(target=run_shopee, daemon=True).start()
    
    card_shopee = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.STOREFRONT, size=32, color="#FF5722"),
            ft.Column([
                ft.Text("Automação Shopee", size=16, weight=ft.FontWeight.BOLD, color=theme.get_text_color()),
                ft.Text("Faça donwload do arquivo na Shopee e executa", size=11, color=theme.get_text_secondary()),
            ], spacing=2, expand=True),
            ft.ElevatedButton(
                "Executar", 
                icon=ft.Icons.PLAY_ARROW, 
                bgcolor="#FF5722", 
                color="#FFFFFF", 
                height=40,
                on_click=executar_fluxo_shopee
            ),
        ], spacing=15, alignment=ft.MainAxisAlignment.START),
        padding=20,
        bgcolor=theme.get_card_bg(),
        border_radius=12,
    )
    
    # ══════════════════════════════════════════════════════════════
    # RELATÓRIO DE SALDO GERAL
    # ══════════════════════════════════════════════════════════════
    arquivo_kpl_saldo = [None]
    arquivo_canal_saldo = [None]
    arquivo_resultado_saldo = [None]
    canal_selecionado_saldo = [None]
    
    # Canais disponíveis para Relatório de Saldo
    CANAIS_SALDO = {
        'SHOPEE': {'nome': 'Shopee', 'cor': '#FF5722', 'icone': ft.Icons.STOREFRONT, 'extensoes': ['zip'], 'label_arquivo': '📦 ZIP Shopee (8 planilhas)'},
        'NETSHOES': {'nome': 'Netshoes', 'cor': '#1E88E5', 'icone': ft.Icons.SPORTS_TENNIS, 'extensoes': ['xlsx', 'xls', 'csv'], 'label_arquivo': '📊 Planilha Netshoes'},
        'CENTAURO': {'nome': 'Centauro', 'cor': '#43A047', 'icone': ft.Icons.SPORTS_SOCCER, 'extensoes': ['xlsx', 'xls', 'csv'], 'label_arquivo': '📊 Planilha Centauro'},
        'MELI': {'nome': 'Mercado Livre', 'cor': '#FFD600', 'icone': ft.Icons.SHOPPING_BAG, 'extensoes': ['xlsx', 'xls', 'csv'], 'label_arquivo': '📊 Planilha Meli'},
        'AMAZON': {'nome': 'Amazon', 'cor': '#FF9800', 'icone': ft.Icons.LOCAL_SHIPPING, 'extensoes': ['xlsx', 'xls', 'csv'], 'label_arquivo': '📊 Planilha Amazon'},
        'TIKTOK': {'nome': 'TikTok', 'cor': '#000000', 'icone': ft.Icons.MUSIC_NOTE, 'extensoes': ['xlsx', 'xls', 'csv'], 'label_arquivo': '📊 Planilha TikTok'},
        'RENNER': {'nome': 'Renner', 'cor': '#E53935', 'icone': ft.Icons.STORE, 'extensoes': ['xlsx', 'xls', 'csv'], 'label_arquivo': '📊 Planilha Renner'},
        'SHEIN': {'nome': 'Shein', 'cor': '#EC407A', 'icone': ft.Icons.CHECKROOM, 'extensoes': ['xlsx', 'xls', 'csv'], 'label_arquivo': '📊 Planilha Shein'},
        'DAFITI': {'nome': 'Dafiti', 'cor': '#7E57C2', 'icone': ft.Icons.SHOPPING_CART, 'extensoes': ['xlsx', 'xls', 'csv'], 'label_arquivo': '📊 Planilha Dafiti'},
    }
    
    def executar_relatorio_saldo(e):
        """Abre seleção de canal para Relatório de Saldo."""
        
        def selecionar_canal_saldo(canal_key):
            def fn(e):
                dlg_canais.open = False
                page.update()
                abrir_dialogo_arquivos(canal_key)
            return fn
        
        # Criar cards de canais
        cards_canais = []
        for key, info in CANAIS_SALDO.items():
            card = ft.Container(
                content=ft.Row([
                    ft.Icon(info['icone'], size=24, color=info['cor']),
                    ft.Text(info['nome'], size=14, weight=ft.FontWeight.W_500, color=theme.get_text_color()),
                ], spacing=10),
                padding=ft.padding.symmetric(12, 15),
                bgcolor=theme.get_card_bg(),
                border_radius=8,
                border=ft.border.all(1, info['cor']),
                on_click=selecionar_canal_saldo(key),
                ink=True,
            )
            cards_canais.append(card)
        
        dlg_canais = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.COMPARE_ARROWS, size=24, color="#8B5CF6"),
                ft.Text("Selecione o Canal", weight=ft.FontWeight.BOLD, size=16),
            ], spacing=10),
            content=ft.Container(
                content=ft.Column(cards_canais, spacing=8, scroll=ft.ScrollMode.AUTO),
                width=350,
                height=400,
            ),
            actions=[ft.TextButton("Cancelar", on_click=lambda e: setattr(dlg_canais, 'open', False) or page.update())],
        )
        
        page.overlay.append(dlg_canais)
        dlg_canais.open = True
        page.update()
    
    def abrir_dialogo_arquivos(canal_key):
        """Abre diálogo para upload de arquivos do canal selecionado."""
        canal_selecionado_saldo[0] = canal_key
        arquivo_kpl_saldo[0] = None
        arquivo_canal_saldo[0] = None
        arquivo_resultado_saldo[0] = None
        
        info_canal = CANAIS_SALDO[canal_key]
        
        txt_kpl = ft.Text("Nenhum arquivo selecionado", size=11, color="#888888")
        txt_canal = ft.Text("Nenhum arquivo selecionado", size=11, color="#888888")
        txt_resultado = ft.Text("", size=12)
        
        btn_processar = ft.ElevatedButton("Processar", icon=ft.Icons.PLAY_ARROW, bgcolor="#22C55E", color="#FFFFFF", disabled=True)
        btn_salvar = ft.ElevatedButton("Salvar Como...", icon=ft.Icons.SAVE_AS, bgcolor="#0EA5E9", color="#FFFFFF", disabled=True)
        
        def verificar_pronto():
            btn_processar.disabled = not (arquivo_kpl_saldo[0] and arquivo_canal_saldo[0])
            page.update()
        
        def selecionar_kpl(e):
            def on_pick(r):
                if r.files and len(r.files) > 0:
                    arquivo_kpl_saldo[0] = r.files[0].path
                    txt_kpl.value = os.path.basename(r.files[0].path)
                    txt_kpl.color = "#22C55E"
                    verificar_pronto()
            file_picker.on_result = on_pick
            file_picker.pick_files(allowed_extensions=["xlsx", "xls", "csv"])
        
        def selecionar_canal_arquivo(e):
            def on_pick(r):
                if r.files and len(r.files) > 0:
                    arquivo_canal_saldo[0] = r.files[0].path
                    txt_canal.value = os.path.basename(r.files[0].path)
                    txt_canal.color = "#22C55E"
                    verificar_pronto()
            file_picker.on_result = on_pick
            file_picker.pick_files(allowed_extensions=info_canal['extensoes'])
        
        def processar(e):
            from services.relatorio_saldo import gerar_relatorio_saldo
            try:
                btn_processar.disabled = True
                btn_processar.text = "Processando..."
                page.update()
                
                arquivo, stats = gerar_relatorio_saldo(arquivo_kpl_saldo[0], arquivo_canal_saldo[0], canal_key)
                arquivo_resultado_saldo[0] = arquivo
                
                txt_resultado.value = f"✅ {stats['total']} SKUs | OK: {stats['ok']} | Divergentes: {stats['divergente']} | {stats['taxa_ok']}%"
                txt_resultado.color = "#22C55E"
                btn_salvar.disabled = False
                page.update()
            except Exception as ex:
                txt_resultado.value = f"❌ Erro: {str(ex)}"
                txt_resultado.color = "#EF4444"
                btn_processar.disabled = False
                btn_processar.text = "Processar"
                page.update()
        
        def salvar(e):
            if not arquivo_resultado_saldo[0]: return
            def on_save(ev):
                if ev.path:
                    try:
                        destino = ev.path if ev.path.endswith('.xlsx') else ev.path + '.xlsx'
                        shutil.copy2(arquivo_resultado_saldo[0], destino)
                        page.snack_bar = ft.SnackBar(ft.Text(f"Salvo: {os.path.basename(destino)}"), bgcolor="#22C55E")
                        page.snack_bar.open = True
                        dlg_arquivos.open = False
                        page.update()
                    except Exception as ex:
                        page.snack_bar = ft.SnackBar(ft.Text(f"Erro: {ex}"), bgcolor="#EF4444")
                        page.snack_bar.open = True
                        page.update()
            file_picker.on_result = on_save
            file_picker.save_file(file_name=f"saldo_{canal_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", allowed_extensions=["xlsx"])
        
        btn_processar.on_click = processar
        btn_salvar.on_click = salvar
        
        dlg_arquivos = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(info_canal['icone'], size=24, color=info_canal['cor']),
                ft.Text(f"Saldo - {info_canal['nome']}", weight=ft.FontWeight.BOLD, size=16),
            ], spacing=10),
            content=ft.Container(
                content=ft.Column([
                    ft.Row([ft.Text("📊 Planilha KPL:", size=12, weight=ft.FontWeight.W_500), 
                            ft.ElevatedButton("Selecionar", icon=ft.Icons.UPLOAD_FILE, on_click=selecionar_kpl)], spacing=10),
                    txt_kpl,
                    ft.Container(height=10),
                    ft.Row([ft.Text(info_canal['label_arquivo'] + ":", size=12, weight=ft.FontWeight.W_500), 
                            ft.ElevatedButton("Selecionar", icon=ft.Icons.UPLOAD_FILE, on_click=selecionar_canal_arquivo)], spacing=10),
                    txt_canal,
                    ft.Container(height=10),
                    ft.Divider(),
                    txt_resultado,
                ], spacing=5, tight=True),
                width=420,
            ),
            actions=[btn_salvar, btn_processar, ft.TextButton("Fechar", on_click=lambda e: setattr(dlg_arquivos, 'open', False) or page.update())],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        page.overlay.append(dlg_arquivos)
        dlg_arquivos.open = True
        page.update()
    
    card_saldo = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.COMPARE_ARROWS, size=32, color="#8B5CF6"),
            ft.Column([
                ft.Text("Relatório de Saldo Geral", size=16, weight=ft.FontWeight.BOLD, color=theme.get_text_color()),
                ft.Text("Compara estoque KPL vs Canal Marketplace", size=11, color=theme.get_text_secondary()),
            ], spacing=2, expand=True),
            ft.ElevatedButton(
                "Executar", 
                icon=ft.Icons.PLAY_ARROW, 
                bgcolor="#8B5CF6", 
                color="#FFFFFF", 
                height=40,
                on_click=executar_relatorio_saldo
            ),
        ], spacing=15, alignment=ft.MainAxisAlignment.START),
        padding=20,
        bgcolor=theme.get_card_bg(),
        border_radius=12,
    )
    
    return ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Text("Automações", size=26, weight=ft.FontWeight.BOLD, color=theme.get_text_color()),
                ft.Text("Fluxos automatizados de processamento", size=11, color=theme.get_text_secondary()),
            ], spacing=2),
            padding=ft.padding.only(left=25, right=25, top=20, bottom=15),
        ),
        ft.Container(
            content=ft.Column([
                card_planilha_imagens,
                card_shopee,
                card_saldo,
            ], spacing=15),
            expand=True,
            padding=ft.padding.only(left=20, right=20, bottom=20),
        ),
    ], spacing=0, expand=True)
