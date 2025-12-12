"""
Tela Canais - Cards de visualização de status por canal
"""
import flet as ft
from services.database_sinc import contar_total_por_canal
from utils.theme import COR_CANAL, ABREV


def criar_tela_canais(page: ft.Page, abrir_canal_callback, theme):
    """
    Cria a tela de canais com cards de status.
    
    Args:
        page: Página Flet
        abrir_canal_callback: Função callback para abrir detalhes do canal
        theme: ThemeManager para cores
    
    Returns:
        ft.Column com a tela completa
    """
    stats = contar_total_por_canal()
    
    def criar_card(canal):
        dados = stats.get(canal, {})
        total = sum(dados.values())
        ativos = dados.get('ATIVO', 0)
        catalogando = dados.get('CATALOGANDO', 0)
        erros = dados.get('ERRO', 0)
        outros = total - ativos - catalogando - erros
        cor = COR_CANAL.get(canal, "#888888")
        
        return ft.Container(
            content=ft.Column([
                # Header do card
                ft.Row([
                    ft.Container(
                        content=ft.Text(ABREV[canal], size=16, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                        bgcolor=cor, width=50, height=50, border_radius=25,
                        alignment=ft.alignment.center,
                    ),
                    ft.Column([
                        ft.Text(canal, size=16, weight=ft.FontWeight.BOLD, color=theme.get_text_color()),
                        ft.Text(f"{total} produtos", size=11, color=theme.get_text_secondary()),
                    ], spacing=2, expand=True),
                ], spacing=15),
                ft.Container(height=15),
                # Grid de estatísticas 1x4 (horizontal)
                ft.Row([
                    ft.Column([
                        ft.Text(str(ativos), size=22, weight=ft.FontWeight.BOLD, color="#22C55E"),
                        ft.Text("Ativos", size=9, color=theme.get_text_secondary()),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True),
                    ft.Container(width=1, height=35, bgcolor=theme.get_border_color()),
                    ft.Column([
                        ft.Text(str(catalogando), size=22, weight=ft.FontWeight.BOLD, color="#F59E0B"),
                        ft.Text("Cat.", size=9, color=theme.get_text_secondary()),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True),
                    ft.Container(width=1, height=35, bgcolor=theme.get_border_color()),
                    ft.Column([
                        ft.Text(str(erros), size=22, weight=ft.FontWeight.BOLD, color="#EF4444"),
                        ft.Text("Erros", size=9, color=theme.get_text_secondary()),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True),
                    ft.Container(width=1, height=35, bgcolor=theme.get_border_color()),
                    ft.Column([
                        ft.Text(str(outros), size=22, weight=ft.FontWeight.BOLD, color=theme.get_text_color()),
                        ft.Text("Outros", size=9, color=theme.get_text_secondary()),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True),
                ]),
                ft.Container(height=15),
                ft.Container(
                    content=ft.Text("Ver Produtos", size=14, weight=ft.FontWeight.W_500, color="#FFFFFF", text_align=ft.TextAlign.CENTER),
                    bgcolor=cor,
                    width=280,
                    height=40,
                    border_radius=20,
                    alignment=ft.alignment.center,
                    on_click=lambda e, c=canal: abrir_canal_callback(c),
                    ink=True,
                ),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=theme.get_card_bg(),
            border_radius=16,
            padding=20,
            width=340,
            height=250,
            shadow=ft.BoxShadow(
                blur_radius=15, spread_radius=0, 
                color=ft.Colors.with_opacity(0.15 if theme.is_dark[0] else 0.08, "#000000")
            ),
        )
    
    # Ordem específica: 3 fileiras x 3 colunas
    ordem_canais = [
        "NETSHOES", "CENTAURO", "TIKTOK",
        "SHEIN", "RENNER", "SHOPEE", 
        "MELI", "DAFITI", "AMAZON"
    ]
    cards = [criar_card(c) for c in ordem_canais]
    
    # Criar 3 fileiras com 3 cards cada
    fileira1 = ft.Row(cards[0:3], spacing=25, alignment=ft.MainAxisAlignment.CENTER)
    fileira2 = ft.Row(cards[3:6], spacing=25, alignment=ft.MainAxisAlignment.CENTER)
    fileira3 = ft.Row(cards[6:9], spacing=25, alignment=ft.MainAxisAlignment.CENTER)
    
    return ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Text("Canais de Venda", size=28, weight=ft.FontWeight.BOLD, color=theme.get_text_color()),
                ft.Text("Status de cada marketplace", size=12, color=theme.get_text_secondary()),
            ], spacing=2),
            padding=ft.padding.only(left=30, right=30, top=25, bottom=20),
            bgcolor=ft.Colors.TRANSPARENT,
        ),
        ft.Container(
            content=ft.Column([
                fileira1,
                fileira2,
                fileira3,
            ], spacing=25, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            expand=True,
            padding=20,
        ),
    ], spacing=0, expand=True)
