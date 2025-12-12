"""
Tela Configurações - Opções gerais e log de atividades
"""
import flet as ft
from datetime import datetime
from services.database_sinc import listar_logs, limpar_logs
from services.auto_refresh import is_auto_refresh_enabled, set_auto_refresh_enabled


def criar_tela_configuracoes(page: ft.Page, usuario_logado: list, theme):
    """
    Cria a tela de configurações.
    """
    # Verificar se é admin
    cargo = usuario_logado[0].get('cargo', 'usuario') if usuario_logado[0] else 'usuario'
    is_admin = cargo == 'admin'
    
    # Tabela de logs
    tabela_logs = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Data/Hora", weight=ft.FontWeight.W_600, size=12)),
            ft.DataColumn(ft.Text("Usuário", weight=ft.FontWeight.W_600, size=12)),
            ft.DataColumn(ft.Text("Ação", weight=ft.FontWeight.W_600, size=12)),
            ft.DataColumn(ft.Text("Detalhes", weight=ft.FontWeight.W_600, size=12)),
        ],
        rows=[],
        heading_row_color=theme.get_header_bg(),
        column_spacing=20,
    )
    
    filtro_usuario = ft.TextField(label="Filtrar usuário", width=150, height=45, text_size=12)
    filtro_acao = ft.TextField(label="Filtrar ação", width=150, height=45, text_size=12)
    
    def carregar_logs():
        logs = listar_logs(500)
        rows = []
        
        for log in logs:
            if filtro_usuario.value and filtro_usuario.value.lower() not in log.get('usuario', '').lower():
                continue
            if filtro_acao.value and filtro_acao.value.lower() not in log.get('acao', '').lower():
                continue
            
            data_fmt = ""
            if log.get('created_at'):
                try:
                    data_fmt = datetime.strptime(log['created_at'][:19], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
                except:
                    data_fmt = log['created_at'][:16]
            
            rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(data_fmt, size=11)),
                ft.DataCell(ft.Text(log.get('usuario', ''), size=11, weight=ft.FontWeight.BOLD)),
                ft.DataCell(ft.Text(log.get('acao', ''), size=11)),
                ft.DataCell(ft.Text(str(log.get('detalhes', '') or '')[:50], size=11)),
            ]))
        
        tabela_logs.rows = rows
        page.update()
    
    def on_filtro_change(e):
        carregar_logs()
    
    filtro_usuario.on_change = on_filtro_change
    filtro_acao.on_change = on_filtro_change
    
    def limpar_logs_antigos(e):
        removidos = limpar_logs(30)
        page.snack_bar = ft.SnackBar(ft.Text(f"Removidos {removidos} logs com mais de 30 dias"), bgcolor="#22C55E")
        page.snack_bar.open = True
        carregar_logs()
    
    carregar_logs()
    
    # Configurações gerais - conectado ao estado global
    def on_auto_refresh_change(e):
        set_auto_refresh_enabled(config_auto_refresh.value)
        status = "ativado" if config_auto_refresh.value else "desativado"
        page.snack_bar = ft.SnackBar(ft.Text(f"Auto-refresh {status} para todas as telas"), bgcolor="#22C55E")
        page.snack_bar.open = True
        page.update()
    
    config_auto_refresh = ft.Switch(label="Auto-refresh (15s)", value=is_auto_refresh_enabled())
    config_auto_refresh.on_change = on_auto_refresh_change
    
    return ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Column([
                        ft.Text("Configurações", size=28, weight=ft.FontWeight.BOLD, color=theme.get_text_color()),
                        ft.Text("Opções gerais e registro de atividades", size=12, color=theme.get_text_secondary()),
                    ], spacing=2),
                ]),
            ]),
            padding=ft.padding.only(left=30, right=30, top=25, bottom=15),
        ),
        ft.Container(
            content=ft.Tabs(
                tabs=[
                    ft.Tab(
                        text="⚙️ Geral",
                        content=ft.Container(
                            content=ft.Column([
                                ft.Text("Preferências", size=16, weight=ft.FontWeight.BOLD, color=theme.get_text_color()),
                                ft.Container(height=10),
                                ft.Container(
                                    content=ft.Column([
                                        config_auto_refresh,
                                    ], spacing=10),
                                    padding=20,
                                    bgcolor=theme.get_card_bg(),
                                    border_radius=8,
                                ),
                                ft.Container(height=20),
                                ft.Text("Informações do Sistema", size=16, weight=ft.FontWeight.BOLD, color=theme.get_text_color()),
                                ft.Container(height=10),
                                ft.Container(
                                    content=ft.Column([
                                        ft.Row([ft.Text("Versão:", weight=ft.FontWeight.BOLD, size=12), ft.Text("1.0.0", size=12)]),
                                        ft.Row([ft.Text("Usuário logado:", weight=ft.FontWeight.BOLD, size=12), 
                                                ft.Text(usuario_logado[0].get('nome', usuario_logado[0].get('username', '')) if usuario_logado[0] else '', size=12)]),
                                        ft.Row([ft.Text("Cargo:", weight=ft.FontWeight.BOLD, size=12), ft.Text(cargo.upper(), size=12)]),
                                    ], spacing=8),
                                    padding=20,
                                    bgcolor=theme.get_card_bg(),
                                    border_radius=8,
                                ),
                            ]),
                            padding=20,
                        ),
                    ),
                    ft.Tab(
                        text="📋 Log de Atividades",
                        content=ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    filtro_usuario,
                                    filtro_acao,
                                    ft.Container(expand=True),
                                    ft.ElevatedButton("Atualizar", icon=ft.Icons.REFRESH, on_click=lambda e: carregar_logs()),
                                    ft.ElevatedButton("Limpar antigos (30d)", icon=ft.Icons.DELETE_SWEEP, bgcolor="#EF4444", color="#FFFFFF",
                                                     on_click=limpar_logs_antigos) if is_admin else ft.Container(),
                                ], spacing=10),
                                ft.Container(height=10),
                                ft.Container(
                                    content=ft.Column([tabela_logs], scroll=ft.ScrollMode.AUTO),
                                    height=400, bgcolor=theme.get_card_bg(), border_radius=8, padding=10,
                                ),
                            ]),
                            padding=20,
                        ),
                    ),
                ],
                expand=True,
            ),
            expand=True,
            bgcolor=theme.get_card_bg(),
            margin=ft.margin.only(left=20, right=20, bottom=20),
            border_radius=12,
        ),
    ], spacing=0, expand=True)
