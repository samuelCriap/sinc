"""
Tela Usuários - Gestão de usuários (apenas para admins)
"""
import flet as ft
from datetime import datetime
from services.database_sinc import (
    listar_usuarios_pendentes, listar_todos_usuarios,
    aprovar_usuario, rejeitar_usuario, alterar_cargo_usuario, bloquear_usuario, remover_usuario
)


def criar_tela_usuarios(page: ft.Page, usuario_logado: list, theme):
    """
    Cria a tela de gestão de usuários.
    
    Args:
        page: Página Flet
        usuario_logado: Lista com dados do usuário logado
        theme: ThemeManager para cores
    
    Returns:
        ft.Column com a tela completa
    """
    # Verificar se é admin
    cargo = usuario_logado[0].get('cargo', 'usuario') if usuario_logado[0] else 'usuario'
    is_admin = cargo == 'admin'
    
    tabela_pendentes = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Nome", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Usuário", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Email", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Data", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Ações", weight=ft.FontWeight.W_600)),
        ],
        rows=[],
        heading_row_color=theme.get_header_bg(),
    )
    
    tabela_todos = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Nome", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Usuário", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Email", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Cargo", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Ações", weight=ft.FontWeight.W_600)),
        ],
        rows=[],
        heading_row_color=theme.get_header_bg(),
    )
    
    def carregar():
        # Pendentes
        pendentes = listar_usuarios_pendentes()
        rows_pend = []
        for u in pendentes:
            data_fmt = ""
            if u.get('created_at'):
                try:
                    data_fmt = datetime.strptime(u['created_at'][:19], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
                except:
                    data_fmt = u['created_at'][:10]
            
            def aprovar_como(uid, cargo):
                def fn(e):
                    aprovar_usuario(uid, cargo)
                    page.snack_bar = ft.SnackBar(ft.Text(f"Usuário aprovado como {cargo}!"), bgcolor="#22C55E")
                    page.snack_bar.open = True
                    carregar()
                    page.update()
                return fn
            
            def rejeitar(uid):
                def fn(e):
                    rejeitar_usuario(uid)
                    page.snack_bar = ft.SnackBar(ft.Text("Usuário rejeitado!"), bgcolor="#EF4444")
                    page.snack_bar.open = True
                    carregar()
                    page.update()
                return fn
            
            rows_pend.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(u.get('nome', ''), size=12)),
                ft.DataCell(ft.Text(u.get('username', ''), size=12)),
                ft.DataCell(ft.Text(u.get('email', ''), size=12)),
                ft.DataCell(ft.Text(data_fmt, size=12)),
                ft.DataCell(ft.Row([
                    ft.ElevatedButton("Admin", bgcolor="#F59E0B", color="#FFFFFF", 
                                     on_click=aprovar_como(u['id'], 'admin'), height=30),
                    ft.ElevatedButton("Usuário", bgcolor="#22C55E", color="#FFFFFF", 
                                     on_click=aprovar_como(u['id'], 'usuario'), height=30),
                    ft.IconButton(ft.Icons.CLOSE, icon_color="#EF4444", 
                                 on_click=rejeitar(u['id']), tooltip="Rejeitar"),
                ], spacing=5)),
            ]))
        tabela_pendentes.rows = rows_pend
        
        # Todos
        todos = listar_todos_usuarios()
        rows_todos = []
        for u in todos:
            cargo_atual = u.get('cargo', 'usuario')
            status = u.get('status', 'ATIVO')
            
            def alterar(uid, novo_cargo):
                def fn(e):
                    alterar_cargo_usuario(uid, novo_cargo)
                    page.snack_bar = ft.SnackBar(ft.Text(f"Cargo alterado para {novo_cargo}!"), bgcolor="#22C55E")
                    page.snack_bar.open = True
                    carregar()
                    page.update()
                return fn
            
            def bloquear(uid, bloquear_flag):
                def fn(e):
                    bloquear_usuario(uid, bloquear_flag)
                    msg = "Usuário bloqueado!" if bloquear_flag else "Usuário desbloqueado!"
                    cor = "#EF4444" if bloquear_flag else "#22C55E"
                    page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=cor)
                    page.snack_bar.open = True
                    carregar()
                    page.update()
                return fn
            
            def remover(uid):
                def fn(e):
                    # Diálogo de confirmação
                    def confirmar(e):
                        remover_usuario(uid)
                        page.snack_bar = ft.SnackBar(ft.Text("Usuário removido!"), bgcolor="#EF4444")
                        page.snack_bar.open = True
                        dlg.open = False
                        carregar()
                        page.update()
                    
                    def cancelar(e):
                        dlg.open = False
                        page.update()
                    
                    dlg = ft.AlertDialog(
                        modal=True,
                        title=ft.Text("Confirmar Remoção"),
                        content=ft.Text("Deseja remover este usuário permanentemente?"),
                        actions=[
                            ft.TextButton("Cancelar", on_click=cancelar),
                            ft.ElevatedButton("Remover", bgcolor="#EF4444", color="#FFFFFF", on_click=confirmar),
                        ],
                    )
                    page.overlay.append(dlg)
                    dlg.open = True
                    page.update()
                return fn
            
            cor_cargo = "#F59E0B" if cargo_atual == 'admin' else "#0EA5E9"
            cor_status = {"ATIVO": "#22C55E", "PENDENTE": "#F59E0B", "INATIVO": "#EF4444"}.get(status, "#888888")
            
            # Menu de ações (não mostrar para admin principal)
            if u.get('username') != 'admin':
                menu_items = [
                    ft.PopupMenuItem(text="Tornar Admin", on_click=alterar(u['id'], 'admin')),
                    ft.PopupMenuItem(text="Tornar Usuário", on_click=alterar(u['id'], 'usuario')),
                    ft.PopupMenuItem(),  # Divider
                ]
                if status == 'ATIVO':
                    menu_items.append(ft.PopupMenuItem(text="🚫 Bloquear", on_click=bloquear(u['id'], True)))
                else:
                    menu_items.append(ft.PopupMenuItem(text="✅ Desbloquear", on_click=bloquear(u['id'], False)))
                menu_items.append(ft.PopupMenuItem())
                menu_items.append(ft.PopupMenuItem(text="🗑️ Remover", on_click=remover(u['id'])))
                
                acoes = ft.PopupMenuButton(items=menu_items)
            else:
                acoes = ft.Text("-", size=12)
            
            rows_todos.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(u.get('nome', ''), size=12)),
                ft.DataCell(ft.Text(u.get('username', ''), size=12)),
                ft.DataCell(ft.Text(u.get('email', ''), size=12)),
                ft.DataCell(ft.Container(
                    content=ft.Text(cargo_atual.upper(), size=10, color="#FFFFFF"),
                    bgcolor=cor_cargo, padding=ft.padding.symmetric(4, 8), border_radius=4,
                )),
                ft.DataCell(ft.Container(
                    content=ft.Text(status, size=10, color="#FFFFFF"),
                    bgcolor=cor_status, padding=ft.padding.symmetric(4, 8), border_radius=4,
                )),
                ft.DataCell(acoes),
            ]))
        tabela_todos.rows = rows_todos
        page.update()
    
    carregar()
    
    if not is_admin:
        return ft.Column([
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.LOCK, size=64, color="#888888"),
                    ft.Text("Acesso Restrito", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text("Apenas administradores podem acessar esta área.", size=14, color="#888888"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                expand=True,
                alignment=ft.alignment.center,
            )
        ], expand=True)
    
    pendentes = listar_usuarios_pendentes()
    badge_pendentes = f" ({len(pendentes)})" if pendentes else ""
    
    return ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Column([
                        ft.Text("Gestão de Usuários", size=28, weight=ft.FontWeight.BOLD, color=theme.get_text_color()),
                        ft.Text("Aprovar cadastros e gerenciar permissões", size=12, color=theme.get_text_secondary()),
                    ], spacing=2),
                ]),
            ]),
            padding=ft.padding.only(left=30, right=30, top=25, bottom=15),
        ),
        ft.Container(
            content=ft.Tabs(
                tabs=[
                    ft.Tab(
                        text=f"⏳ Pendentes{badge_pendentes}",
                        content=ft.Container(
                            content=ft.Column([tabela_pendentes], scroll=ft.ScrollMode.AUTO),
                            padding=20,
                        ),
                    ),
                    ft.Tab(
                        text="👥 Todos os Usuários",
                        content=ft.Container(
                            content=ft.Column([tabela_todos], scroll=ft.ScrollMode.AUTO),
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
