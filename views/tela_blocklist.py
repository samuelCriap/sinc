"""
Tela Blocklist - Gerenciamento de termos bloqueados
"""
import flet as ft
from services.database_sinc import listar_blocklist, adicionar_blocklist, remover_blocklist, CANAIS


def criar_tela_blocklist(page: ft.Page, theme):
    """
    Cria a tela de gerenciamento de blocklist.
    
    Args:
        page: Página Flet
        theme: ThemeManager para cores
    
    Returns:
        ft.Column com a tela completa
    """
    # Inputs
    canal_dd = ft.Dropdown(
        label="Canal", 
        options=[ft.dropdown.Option(c) for c in CANAIS], 
        value=CANAIS[0], 
        width=150
    )
    tipo_dd = ft.Dropdown(
        label="Tipo", 
        options=[ft.dropdown.Option("MARCA"), ft.dropdown.Option("MODELO")], 
        value="MODELO", 
        width=130
    )
    termo_tf = ft.TextField(label="Termo", width=250)
    
    tabela = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Canal", weight=ft.FontWeight.W_600, color=theme.get_text_color())),
            ft.DataColumn(ft.Text("Termo", weight=ft.FontWeight.W_600, color=theme.get_text_color())),
            ft.DataColumn(ft.Text("Tipo", weight=ft.FontWeight.W_600, color=theme.get_text_color())),
            ft.DataColumn(ft.Text("", weight=ft.FontWeight.W_600)),
        ],
        rows=[], 
        heading_row_color=theme.get_header_bg(),
    )
    
    def adicionar(e):
        if not termo_tf.value: 
            return
        adicionar_blocklist(canal_dd.value, termo_tf.value, tipo_dd.value)
        termo_tf.value = ""
        carregar()
    
    def carregar():
        items = listar_blocklist()
        rows = []
        for bl in items:
            def rm(e, bid=bl['id']):
                remover_blocklist(bid)
                carregar()
            rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(bl['canal'], size=12)),
                ft.DataCell(ft.Text(bl['termo_bloqueio'][:40], size=12)),
                ft.DataCell(ft.Text(bl.get('tipo', 'MODELO'), size=12)),
                ft.DataCell(ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED, on_click=rm)),
            ]))
        tabela.rows = rows
        page.update()
    
    carregar()
    
    return ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Text("Blocklist", size=28, weight=ft.FontWeight.BOLD, color=theme.get_text_color()),
                ft.Text("Gerencie termos bloqueados", size=12, color=theme.get_text_secondary()),
            ], spacing=2),
            padding=ft.padding.only(left=30, right=30, top=25, bottom=20),
            bgcolor=ft.Colors.TRANSPARENT,
        ),
        ft.Container(
            content=ft.Row([
                canal_dd, tipo_dd, termo_tf, 
                ft.ElevatedButton(
                    "Adicionar", 
                    bgcolor="#333333" if theme.is_dark[0] else "#000000", 
                    color="#FFFFFF", 
                    on_click=adicionar
                )
            ], spacing=15),
            bgcolor=theme.get_card_bg(),
            border_radius=12,
            margin=ft.margin.only(left=20, right=20),
            padding=20,
        ),
        ft.Container(height=15),
        ft.Container(
            content=ft.Column([tabela], scroll=ft.ScrollMode.AUTO),
            bgcolor=theme.get_card_bg(),
            border_radius=12,
            margin=ft.margin.only(left=20, right=20, bottom=20),
            padding=20,
            expand=True,
        ),
    ], spacing=0, expand=True)
