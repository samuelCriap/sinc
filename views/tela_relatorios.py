"""
Tela de Relatórios - Gráficos e Exportação PDF
"""
import flet as ft
import os
import tempfile
from datetime import datetime


def criar_tela_relatorios(page: ft.Page, save_picker: ft.FilePicker, theme):
    """
    Cria a tela de relatórios com abas para Canais e Chamados.
    """
    from services.relatorios import (
        get_estatisticas_canais, get_estatisticas_chamados,
        gerar_grafico_rosca_status, gerar_grafico_barras_canais,
        gerar_grafico_pizza_prioridade,
        gerar_pdf_relatorio_canais, gerar_pdf_relatorio_chamados
    )
    
    # Estado dos gráficos
    graficos_canais = {"rosca": None, "barras": None}
    graficos_chamados = {"prioridade": None}
    stats_canais = {}
    stats_chamados = {}
    
    # Containers para gráficos - inicialmente invisíveis
    img_rosca = ft.Image(width=300, height=300, fit=ft.ImageFit.CONTAIN, visible=False)
    img_barras = ft.Image(width=550, height=350, fit=ft.ImageFit.CONTAIN, visible=False)
    img_prioridade = ft.Image(width=280, height=280, fit=ft.ImageFit.CONTAIN, visible=False)
    
    # Cards de métricas (Canais)
    card_total = ft.Container(
        content=ft.Column([
            ft.Text("0", size=32, weight=ft.FontWeight.BOLD, color="#3B82F6"),
            ft.Text("Total Produtos", size=12, color=theme.get_text_secondary()),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
        padding=20, bgcolor=theme.get_card_bg(), border_radius=12, width=140,
        border=ft.border.all(1, "#3B82F6")
    )
    
    card_ativos = ft.Container(
        content=ft.Column([
            ft.Text("0", size=32, weight=ft.FontWeight.BOLD, color="#22C55E"),
            ft.Text("Ativos", size=12, color=theme.get_text_secondary()),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
        padding=20, bgcolor=theme.get_card_bg(), border_radius=12, width=140,
        border=ft.border.all(1, "#22C55E")
    )
    
    card_erros = ft.Container(
        content=ft.Column([
            ft.Text("0", size=32, weight=ft.FontWeight.BOLD, color="#EF4444"),
            ft.Text("Erros", size=12, color=theme.get_text_secondary()),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
        padding=20, bgcolor=theme.get_card_bg(), border_radius=12, width=140,
        border=ft.border.all(1, "#EF4444")
    )
    
    card_taxa = ft.Container(
        content=ft.Column([
            ft.Text("0%", size=32, weight=ft.FontWeight.BOLD, color="#8B5CF6"),
            ft.Text("Taxa Sucesso", size=12, color=theme.get_text_secondary()),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
        padding=20, bgcolor=theme.get_card_bg(), border_radius=12, width=140,
        border=ft.border.all(1, "#8B5CF6")
    )
    
    # Cards de métricas (Chamados)
    card_ch_total = ft.Container(
        content=ft.Column([
            ft.Text("0", size=32, weight=ft.FontWeight.BOLD, color="#3B82F6"),
            ft.Text("Total Chamados", size=12, color=theme.get_text_secondary()),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
        padding=20, bgcolor=theme.get_card_bg(), border_radius=12, width=150,
        border=ft.border.all(1, "#3B82F6")
    )
    
    card_ch_abertos = ft.Container(
        content=ft.Column([
            ft.Text("0", size=32, weight=ft.FontWeight.BOLD, color="#22C55E"),
            ft.Text("Abertos", size=12, color=theme.get_text_secondary()),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
        padding=20, bgcolor=theme.get_card_bg(), border_radius=12, width=150,
        border=ft.border.all(1, "#22C55E")
    )
    
    card_ch_lixeira = ft.Container(
        content=ft.Column([
            ft.Text("0", size=32, weight=ft.FontWeight.BOLD, color="#EF4444"),
            ft.Text("Na Lixeira", size=12, color=theme.get_text_secondary()),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
        padding=20, bgcolor=theme.get_card_bg(), border_radius=12, width=150,
        border=ft.border.all(1, "#EF4444")
    )
    
    # Tabela de resumo por canal
    tabela_canais = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Canal", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Total", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Ativos", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Catalogando", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Erros", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Taxa %", weight=ft.FontWeight.BOLD)),
        ],
        rows=[],
        heading_row_color=ft.Colors.TRANSPARENT,
        data_row_max_height=40,
    )
    
    def carregar_canais():
        nonlocal stats_canais, graficos_canais
        
        try:
            stats_canais = get_estatisticas_canais()
            totais = stats_canais['totais']
            
            # Atualizar cards
            card_total.content.controls[0].value = str(totais['total'])
            card_ativos.content.controls[0].value = str(totais['ativo'])
            card_erros.content.controls[0].value = str(totais['erro'])
            card_taxa.content.controls[0].value = f"{totais['taxa_sucesso']}%"
            
            # Gerar gráficos
            dark_mode = theme.is_dark[0]
            graficos_canais["rosca"] = gerar_grafico_rosca_status(stats_canais, dark_mode)
            graficos_canais["barras"] = gerar_grafico_barras_canais(stats_canais, dark_mode)
            
            if graficos_canais["rosca"]:
                img_rosca.src = graficos_canais["rosca"]
                img_rosca.visible = True
            if graficos_canais["barras"]:
                img_barras.src = graficos_canais["barras"]
                img_barras.visible = True
            
            # Atualizar tabela
            rows = []
            for canal, dados in stats_canais['por_canal'].items():
                taxa = round((dados['ativo'] / dados['total']) * 100, 1) if dados['total'] > 0 else 0
                rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(canal, weight=ft.FontWeight.W_500)),
                    ft.DataCell(ft.Text(str(dados['total']))),
                    ft.DataCell(ft.Text(str(dados['ativo']), color="#22C55E")),
                    ft.DataCell(ft.Text(str(dados['catalogando']), color="#F59E0B")),
                    ft.DataCell(ft.Text(str(dados['erro']), color="#EF4444")),
                    ft.DataCell(ft.Text(f"{taxa}%", color="#8B5CF6")),
                ]))
            tabela_canais.rows = rows
            
        except Exception as e:
            print(f"Erro ao carregar canais: {e}")
        
        page.update()
    
    def carregar_chamados():
        nonlocal stats_chamados, graficos_chamados
        
        try:
            stats_chamados = get_estatisticas_chamados()
            totais = stats_chamados['totais']
            
            # Atualizar cards
            card_ch_total.content.controls[0].value = str(totais['total'])
            card_ch_abertos.content.controls[0].value = str(totais['abertos'])
            card_ch_lixeira.content.controls[0].value = str(totais['lixeira'])
            
            # Gerar gráfico
            dark_mode = theme.is_dark[0]
            graficos_chamados["prioridade"] = gerar_grafico_pizza_prioridade(stats_chamados, dark_mode)
            
            if graficos_chamados["prioridade"]:
                img_prioridade.src = graficos_chamados["prioridade"]
                img_prioridade.visible = True
            
        except Exception as e:
            print(f"Erro ao carregar chamados: {e}")
        
        page.update()
    
    def exportar_pdf_canais(e):
        if not stats_canais:
            page.snack_bar = ft.SnackBar(ft.Text("Carregue os dados primeiro!"), bgcolor="#EF4444")
            page.snack_bar.open = True
            page.update()
            return
        
        def on_save(result):
            if result.path:
                output = result.path if result.path.endswith('.pdf') else result.path + '.pdf'
                try:
                    gerar_pdf_relatorio_canais(
                        stats_canais, 
                        graficos_canais.get("rosca", ""),
                        graficos_canais.get("barras", ""),
                        output
                    )
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"PDF exportado: {os.path.basename(output)}"), 
                        bgcolor="#22C55E"
                    )
                    page.snack_bar.open = True
                except Exception as ex:
                    page.snack_bar = ft.SnackBar(ft.Text(f"Erro: {str(ex)}"), bgcolor="#EF4444")
                    page.snack_bar.open = True
                page.update()
        
        save_picker.on_result = on_save
        save_picker.save_file(
            file_name=f"relatorio_canais_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            allowed_extensions=["pdf"]
        )
    
    def exportar_pdf_chamados(e):
        if not stats_chamados:
            page.snack_bar = ft.SnackBar(ft.Text("Carregue os dados primeiro!"), bgcolor="#EF4444")
            page.snack_bar.open = True
            page.update()
            return
        
        def on_save(result):
            if result.path:
                output = result.path if result.path.endswith('.pdf') else result.path + '.pdf'
                try:
                    gerar_pdf_relatorio_chamados(
                        stats_chamados,
                        graficos_chamados.get("prioridade", ""),
                        output
                    )
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"PDF exportado: {os.path.basename(output)}"),
                        bgcolor="#22C55E"
                    )
                    page.snack_bar.open = True
                except Exception as ex:
                    page.snack_bar = ft.SnackBar(ft.Text(f"Erro: {str(ex)}"), bgcolor="#EF4444")
                    page.snack_bar.open = True
                page.update()
        
        save_picker.on_result = on_save
        save_picker.save_file(
            file_name=f"relatorio_chamados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            allowed_extensions=["pdf"]
        )
    
    # ══════════════════════════════════════════════════════════════
    # ABA DE CANAIS
    # ══════════════════════════════════════════════════════════════
    aba_canais = ft.Column([
        # Header
        ft.Row([
            ft.Text("📊 Relatório de Canais", size=20, weight=ft.FontWeight.BOLD, color=theme.get_text_color()),
            ft.Container(expand=True),
            ft.ElevatedButton(
                "🔄 Atualizar",
                on_click=lambda e: carregar_canais(),
                bgcolor="#3B82F6",
                color="#FFFFFF"
            ),
            ft.ElevatedButton(
                "📄 Exportar PDF",
                on_click=exportar_pdf_canais,
                bgcolor="#22C55E",
                color="#FFFFFF"
            ),
        ], spacing=15),
        ft.Divider(height=1, color=theme.get_border_color()),
        ft.Container(height=10),
        
        # Cards de métricas
        ft.Row([card_total, card_ativos, card_erros, card_taxa], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
        ft.Container(height=25),
        
        # Gráficos
        ft.Row([
            ft.Container(
                content=ft.Column([
                    ft.Text("Distribuição por Status", size=14, weight=ft.FontWeight.W_600, color=theme.get_text_color()),
                    ft.Container(height=5),
                    img_rosca,
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=theme.get_card_bg(),
                padding=20,
                border_radius=12,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("Produtos por Canal", size=14, weight=ft.FontWeight.W_600, color=theme.get_text_color()),
                    ft.Container(height=5),
                    img_barras,
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=theme.get_card_bg(),
                padding=20,
                border_radius=12,
                expand=True,
            ),
        ], spacing=20),
        ft.Container(height=20),
        
        # Tabela
        ft.Container(
            content=ft.Column([
                ft.Text("Detalhamento por Canal", size=14, weight=ft.FontWeight.W_600, color=theme.get_text_color()),
                ft.Container(height=10),
                tabela_canais,
            ]),
            bgcolor=theme.get_card_bg(),
            padding=20,
            border_radius=12,
        ),
    ], scroll=ft.ScrollMode.AUTO, expand=True)
    
    # ══════════════════════════════════════════════════════════════
    # ABA DE CHAMADOS
    # ══════════════════════════════════════════════════════════════
    aba_chamados = ft.Column([
        # Header
        ft.Row([
            ft.Text("📋 Relatório de Chamados", size=20, weight=ft.FontWeight.BOLD, color=theme.get_text_color()),
            ft.Container(expand=True),
            ft.ElevatedButton(
                "🔄 Atualizar",
                on_click=lambda e: carregar_chamados(),
                bgcolor="#3B82F6",
                color="#FFFFFF"
            ),
            ft.ElevatedButton(
                "📄 Exportar PDF",
                on_click=exportar_pdf_chamados,
                bgcolor="#22C55E",
                color="#FFFFFF"
            ),
        ], spacing=15),
        ft.Divider(height=1, color=theme.get_border_color()),
        ft.Container(height=10),
        
        # Cards de métricas
        ft.Row([card_ch_total, card_ch_abertos, card_ch_lixeira], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
        ft.Container(height=25),
        
        # Gráfico
        ft.Row([
            ft.Container(
                content=ft.Column([
                    ft.Text("Por Prioridade", size=14, weight=ft.FontWeight.W_600, color=theme.get_text_color()),
                    ft.Container(height=5),
                    img_prioridade,
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=theme.get_card_bg(),
                padding=20,
                border_radius=12,
            ),
        ], alignment=ft.MainAxisAlignment.CENTER),
    ], scroll=ft.ScrollMode.AUTO, expand=True)
    
    # Tabs
    tabs = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(text="📊 Canais", content=ft.Container(content=aba_canais, padding=20)),
            ft.Tab(text="📋 Chamados", content=ft.Container(content=aba_chamados, padding=20)),
        ],
        expand=True,
        animation_duration=300,
    )
    
    # Carregar dados iniciais
    carregar_canais()
    carregar_chamados()
    
    return ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Text("Relatórios", size=28, weight=ft.FontWeight.BOLD, color=theme.get_text_color()),
                ft.Text("Análises e estatísticas do sistema", size=12, color=theme.get_text_secondary()),
            ], spacing=2),
            padding=ft.padding.only(left=25, right=25, top=20, bottom=10),
        ),
        ft.Container(
            content=tabs,
            expand=True,
            bgcolor=theme.get_bg(),
        ),
    ], spacing=0, expand=True)
