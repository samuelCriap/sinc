"""
Tela Configurações - Opções gerais e log de atividades
"""
import flet as ft
import threading
from datetime import datetime
from services.database_sinc import listar_logs, limpar_logs
from services.auto_refresh import is_auto_refresh_enabled, set_auto_refresh_enabled
from services.auto_update import get_local_version
from services.config_rede import get_config, save_config, test_connection
from services.network_scanner import scan_network_async, get_local_ip, test_mysql_connection


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
        
        def abrir_detalhes_log(log_data):
            """Abre modal com detalhes completos do log."""
            def fn(e):
                data_fmt = ""
                if log_data.get('created_at'):
                    try:
                        dt_val = log_data['created_at']
                        if isinstance(dt_val, datetime):
                            data_fmt = dt_val.strftime("%d/%m/%Y às %H:%M:%S")
                        else:
                            data_fmt = datetime.strptime(str(dt_val)[:19], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y às %H:%M:%S")
                    except:
                        data_fmt = str(log_data['created_at'])
                
                def fechar(ev):
                    dlg_detalhes.open = False
                    page.update()
                
                dlg_detalhes = ft.AlertDialog(
                    modal=True,
                    title=ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINE, size=24, color="#1E88E5"),
                        ft.Text("Detalhes do Log", weight=ft.FontWeight.BOLD, size=16),
                    ], spacing=10),
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text("📅 Data/Hora:", weight=ft.FontWeight.BOLD, size=12),
                                ft.Text(data_fmt, size=12),
                            ], spacing=10),
                            ft.Row([
                                ft.Text("👤 Usuário:", weight=ft.FontWeight.BOLD, size=12),
                                ft.Text(log_data.get('usuario', ''), size=12, color="#8B5CF6"),
                            ], spacing=10),
                            ft.Row([
                                ft.Text("🔧 Ação:", weight=ft.FontWeight.BOLD, size=12),
                                ft.Text(log_data.get('acao', ''), size=12),
                            ], spacing=10),
                            ft.Container(height=10),
                            ft.Text("📝 Detalhes:", weight=ft.FontWeight.BOLD, size=12),
                            ft.Container(
                                content=ft.Text(str(log_data.get('detalhes', '') or 'Sem detalhes adicionais'), size=12),
                                bgcolor="#2A2A2A" if theme.is_dark[0] else "#F5F5F5",
                                padding=15,
                                border_radius=8,
                                width=400,
                            ),
                        ], spacing=8),
                        width=450,
                    ),
                    actions=[ft.TextButton("Fechar", on_click=fechar)],
                )
                page.overlay.append(dlg_detalhes)
                dlg_detalhes.open = True
                page.update()
            return fn
        
        for log in logs:
            if filtro_usuario.value and filtro_usuario.value.lower() not in log.get('usuario', '').lower():
                continue
            if filtro_acao.value and filtro_acao.value.lower() not in log.get('acao', '').lower():
                continue
            
            data_fmt = ""
            if log.get('created_at'):
                try:
                    dt_val = log['created_at']
                    if isinstance(dt_val, datetime):
                        data_fmt = dt_val.strftime("%d/%m/%Y %H:%M")
                    else:
                        data_fmt = datetime.strptime(str(dt_val)[:19], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
                except:
                    data_fmt = str(log['created_at'])[:16] if log.get('created_at') else ""
            
            detalhes_preview = str(log.get('detalhes', '') or '')[:50]
            if len(str(log.get('detalhes', '') or '')) > 50:
                detalhes_preview += "..."
            
            rows.append(ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(data_fmt, size=11)),
                    ft.DataCell(ft.Text(log.get('usuario', ''), size=11, weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(log.get('acao', ''), size=11)),
                    ft.DataCell(ft.Text(detalhes_preview, size=11, color="#888888")),
                ],
                on_select_changed=abrir_detalhes_log(log),
            ))
        
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
    
    # ══════════════════════════════════════════════════════════════
    # NETWORK SCANNER
    # ══════════════════════════════════════════════════════════════
    config = get_config()
    servidor_atual = ft.Text(f"Servidor atual: {config.get('mysql_host', 'Não configurado')}", size=12, color="#22C55E")
    scan_progress = ft.ProgressBar(visible=False, width=300)
    scan_status = ft.Text("", size=11, color=theme.get_text_secondary())
    servidores_encontrados = ft.Column([], spacing=5)
    
    def on_server_found(ip):
        """Callback quando encontra um servidor."""
        def selecionar(e):
            # Testa conexão
            if test_mysql_connection(ip):
                # Salva configuração
                new_config = get_config()
                new_config['mysql_host'] = ip
                save_config(new_config)
                servidor_atual.value = f"Servidor atual: {ip}"
                servidor_atual.color = "#22C55E"
                page.snack_bar = ft.SnackBar(ft.Text(f"✅ Conectado a {ip}!"), bgcolor="#22C55E")
            else:
                page.snack_bar = ft.SnackBar(ft.Text(f"❌ Não foi possível conectar a {ip}"), bgcolor="#EF4444")
            page.snack_bar.open = True
            page.update()
        
        servidor_btn = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.STORAGE, color="#22C55E", size=16),
                ft.Text(ip, size=12),
                ft.ElevatedButton("Usar", on_click=selecionar, height=28),
            ], spacing=10),
            padding=8,
            bgcolor=theme.get_card_bg(),
            border_radius=6,
        )
        servidores_encontrados.controls.append(servidor_btn)
        page.update()
    
    def on_progress(current, total, ip):
        """Callback de progresso."""
        scan_progress.value = current / total
        scan_status.value = f"Verificando {ip}... ({current}/{total})"
        if current % 10 == 0:  # Atualiza a cada 10 IPs para não travar UI
            page.update()
    
    def on_complete(servers):
        """Callback quando termina."""
        scan_progress.visible = False
        if servers:
            scan_status.value = f"✅ Encontrado(s) {len(servers)} servidor(es) MySQL"
        else:
            scan_status.value = "❌ Nenhum servidor MySQL encontrado na rede"
        page.update()
    
    def iniciar_scan(e):
        """Inicia o scan da rede."""
        servidores_encontrados.controls.clear()
        scan_progress.visible = True
        scan_progress.value = 0
        scan_status.value = "Iniciando scan..."
        page.update()
        
        scan_network_async(on_server_found, on_progress, on_complete)
    
    btn_scan = ft.ElevatedButton("🔍 Escanear Rede", on_click=iniciar_scan, bgcolor="#1E88E5", color="#FFFFFF")
    
    # Field para IP manual
    ip_manual = ft.TextField(label="IP do Servidor", value=config.get('mysql_host', ''), width=200, height=45)
    
    def testar_conexao_manual(e):
        ip = ip_manual.value.strip()
        if not ip:
            page.snack_bar = ft.SnackBar(ft.Text("Digite um IP"), bgcolor="#EF4444")
            page.snack_bar.open = True
            page.update()
            return
        
        if test_mysql_connection(ip):
            new_config = get_config()
            new_config['mysql_host'] = ip
            save_config(new_config)
            servidor_atual.value = f"Servidor atual: {ip}"
            servidor_atual.color = "#22C55E"
            page.snack_bar = ft.SnackBar(ft.Text(f"✅ Conectado a {ip}!"), bgcolor="#22C55E")
        else:
            page.snack_bar = ft.SnackBar(ft.Text(f"❌ Falha ao conectar em {ip}"), bgcolor="#EF4444")
        page.snack_bar.open = True
        page.update()
    
    btn_testar = ft.ElevatedButton("Testar e Salvar", on_click=testar_conexao_manual, bgcolor="#22C55E", color="#FFFFFF")
    
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
                                        ft.Row([ft.Text("Versão:", weight=ft.FontWeight.BOLD, size=12), ft.Text(f"v{get_local_version()}", size=12)]),
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
                    ft.Tab(
                        text="🌐 Rede",
                        content=ft.Container(
                            content=ft.Column([
                                ft.Text("Conexão MySQL", size=16, weight=ft.FontWeight.BOLD, color=theme.get_text_color()),
                                ft.Container(height=10),
                                servidor_atual,
                                ft.Container(height=15),
                                ft.Text("Conectar Manualmente", size=14, weight=ft.FontWeight.W_600, color=theme.get_text_color()),
                                ft.Row([ip_manual, btn_testar], spacing=10),
                                ft.Container(height=20),
                                ft.Divider(),
                                ft.Container(height=10),
                                ft.Text("Escanear Rede Local", size=14, weight=ft.FontWeight.W_600, color=theme.get_text_color()),
                                ft.Text(f"Seu IP: {get_local_ip()}", size=11, color=theme.get_text_secondary()),
                                ft.Container(height=10),
                                btn_scan,
                                ft.Container(height=10),
                                scan_progress,
                                scan_status,
                                ft.Container(height=10),
                                ft.Text("Servidores encontrados:", size=12, weight=ft.FontWeight.W_500),
                                ft.Container(
                                    content=servidores_encontrados,
                                    height=150,
                                    bgcolor=theme.get_card_bg(),
                                    border_radius=8,
                                    padding=10,
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
