"""
Tela Chamados - Controle de chamados com lixeira
"""
import flet as ft
from datetime import datetime
import webbrowser
from services.database_sinc import (
    criar_chamado, listar_chamados, atualizar_chamado,
    mover_para_lixeira, restaurar_chamado, excluir_chamado_permanente, registrar_log
)


def criar_tela_chamados(page: ft.Page, usuario_logado: list, theme):
    """Cria a tela de controle de chamados."""
    
    usuario_atual = usuario_logado[0].get('username', 'Usuário') if usuario_logado[0] else 'Usuário'
    
    # Containers das tabelas
    lista_ativos = ft.Column([], scroll=ft.ScrollMode.AUTO, spacing=8)
    lista_lixeira = ft.Column([], scroll=ft.ScrollMode.AUTO, spacing=8)
    
    def calcular_dias_abertos(created_at):
        if not created_at:
            return 0
        try:
            data = datetime.strptime(created_at[:19], "%Y-%m-%d %H:%M:%S")
            return (datetime.now() - data).days
        except:
            return 0
    
    def cor_prioridade(prioridade):
        cores = {"URGENTE": "#EF4444", "ALTA": "#F97316", "MÉDIA": "#F59E0B", "BAIXA": "#22C55E"}
        return cores.get(prioridade, "#888888")
    
    def abrir_link(link):
        if link:
            webbrowser.open(link)
    
    def carregar_chamados():
        # Chamados ativos
        ativos = listar_chamados(na_lixeira=False)
        lista_ativos.controls.clear()
        
        for c in ativos:
            dias = calcular_dias_abertos(c.get('created_at'))
            cor = cor_prioridade(c.get('prioridade', 'MÉDIA'))
            
            lista_ativos.controls.append(
                ft.Container(
                    content=ft.Row([
                        # Indicador de prioridade
                        ft.Container(width=5, height=60, bgcolor=cor, border_radius=3),
                        # Info principal
                        ft.Column([
                            ft.Row([
                                ft.Text(f"#{c.get('numero', '')}", weight=ft.FontWeight.BOLD, size=14, color=theme.get_text_color()),
                                ft.Container(
                                    content=ft.Text(c.get('prioridade', 'MÉDIA'), size=10, color="#FFFFFF"),
                                    bgcolor=cor, padding=ft.padding.symmetric(3, 8), border_radius=4,
                                ),
                                ft.Container(
                                    content=ft.Text(f"{dias} dias", size=10, color="#FFFFFF"),
                                    bgcolor="#6366F1" if dias <= 3 else "#F59E0B" if dias <= 7 else "#EF4444",
                                    padding=ft.padding.symmetric(3, 8), border_radius=4,
                                ),
                                ft.Text(f"| {c.get('canal', '')}", size=11, color=theme.get_text_secondary()),
                                ft.Text(f"| por {c.get('criado_por', 'N/A')}", size=11, color="#8B5CF6", italic=True),
                            ], spacing=8),
                            ft.Text(c.get('observacoes', '')[:80] + ('...' if len(c.get('observacoes', '')) > 80 else ''), 
                                   size=11, color=theme.get_text_secondary()),
                        ], spacing=2, expand=True),
                        # Ações
                        ft.Row([
                            ft.IconButton(ft.Icons.LINK, icon_color="#0EA5E9", tooltip="Abrir link",
                                         on_click=lambda e, l=c.get('link'): abrir_link(l),
                                         visible=bool(c.get('link'))),
                            ft.IconButton(ft.Icons.EDIT, icon_color="#F59E0B", tooltip="Editar",
                                         on_click=lambda e, ch=c: abrir_modal_editar(ch)),
                            ft.IconButton(ft.Icons.DELETE, icon_color="#EF4444", tooltip="Mover para lixeira",
                                         on_click=lambda e, ch=c: mover_lixeira(ch['id'])),
                        ], spacing=0),
                    ], spacing=10),
                    padding=12,
                    bgcolor=theme.get_card_bg(),
                    border_radius=8,
                )
            )
        
        if not ativos:
            lista_ativos.controls.append(
                ft.Text("Nenhum chamado ativo", size=12, color=theme.get_text_secondary(), italic=True)
            )
        
        # Lixeira
        lixeira = listar_chamados(na_lixeira=True)
        lista_lixeira.controls.clear()
        
        for c in lixeira:
            lista_lixeira.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text(f"#{c.get('numero', '')} - {c.get('canal', '')}", size=12, color=theme.get_text_secondary()),
                            ft.Text(c.get('observacoes', '')[:50], size=10, color="#888888"),
                        ], spacing=2, expand=True),
                        ft.IconButton(ft.Icons.RESTORE, icon_color="#22C55E", tooltip="Restaurar",
                                     on_click=lambda e, ch=c: restaurar(ch['id'])),
                        ft.IconButton(ft.Icons.DELETE_FOREVER, icon_color="#EF4444", tooltip="Excluir permanentemente",
                                     on_click=lambda e, ch=c: excluir_permanente(ch['id'])),
                    ], spacing=10),
                    padding=10,
                    bgcolor="#2A2A2A" if theme.is_dark[0] else "#F0F0F0",
                    border_radius=6,
                    opacity=0.7,
                )
            )
        
        if not lixeira:
            lista_lixeira.controls.append(
                ft.Text("Lixeira vazia", size=12, color=theme.get_text_secondary(), italic=True)
            )
        
        page.update()
    
    def mover_lixeira(chamado_id):
        mover_para_lixeira(chamado_id)
        registrar_log(usuario_atual, "Chamado movido para lixeira", f"ID: {chamado_id}")
        carregar_chamados()
    
    def restaurar(chamado_id):
        restaurar_chamado(chamado_id)
        registrar_log(usuario_atual, "Chamado restaurado", f"ID: {chamado_id}")
        carregar_chamados()
    
    def excluir_permanente(chamado_id):
        def confirmar(e):
            excluir_chamado_permanente(chamado_id)
            registrar_log(usuario_atual, "Chamado excluído permanentemente", f"ID: {chamado_id}")
            dlg.open = False
            page.update()
            carregar_chamados()
        
        dlg = ft.AlertDialog(
            title=ft.Text("Excluir Permanentemente?"),
            content=ft.Text("Esta ação não pode ser desfeita."),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(dlg, 'open', False) or page.update()),
                ft.ElevatedButton("Excluir", bgcolor="#EF4444", color="#FFFFFF", on_click=confirmar),
            ],
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()
    
    # Modal de criar/editar
    def abrir_modal_criar(e):
        numero = ft.TextField(label="Número do Chamado", width=200)
        prioridade = ft.Dropdown(label="Prioridade", width=150, value="MÉDIA",
                                  options=[ft.dropdown.Option(p) for p in ["URGENTE", "ALTA", "MÉDIA", "BAIXA"]])
        canal = ft.TextField(label="Canal", width=200)
        observacoes = ft.TextField(label="Observações", multiline=True, min_lines=2, max_lines=4, width=400)
        link = ft.TextField(label="Link (opcional)", width=400)
        
        def salvar(e):
            if not numero.value:
                return
            criar_chamado(numero.value, prioridade.value, canal.value, observacoes.value, link.value, usuario_atual)
            registrar_log(usuario_atual, "Chamado criado", f"#{numero.value}")
            dlg.open = False
            page.update()
            carregar_chamados()
        
        dlg = ft.AlertDialog(
            title=ft.Text("Novo Chamado"),
            content=ft.Column([numero, prioridade, canal, observacoes, link], spacing=10, tight=True),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(dlg, 'open', False) or page.update()),
                ft.ElevatedButton("Criar", bgcolor="#22C55E", color="#FFFFFF", on_click=salvar),
            ],
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()
    
    def abrir_modal_editar(chamado):
        numero = ft.TextField(label="Número", value=chamado.get('numero', ''), width=200)
        prioridade = ft.Dropdown(label="Prioridade", width=150, value=chamado.get('prioridade', 'MÉDIA'),
                                  options=[ft.dropdown.Option(p) for p in ["URGENTE", "ALTA", "MÉDIA", "BAIXA"]])
        canal = ft.TextField(label="Canal", value=chamado.get('canal', ''), width=200)
        observacoes = ft.TextField(label="Observações", value=chamado.get('observacoes', ''), multiline=True, min_lines=2, width=400)
        link = ft.TextField(label="Link", value=chamado.get('link', ''), width=400)
        
        def salvar(e):
            atualizar_chamado(chamado['id'], numero.value, prioridade.value, canal.value, observacoes.value, link.value)
            registrar_log(usuario_atual, "Chamado atualizado", f"#{numero.value}")
            dlg.open = False
            page.update()
            carregar_chamados()
        
        dlg = ft.AlertDialog(
            title=ft.Text("Editar Chamado"),
            content=ft.Column([numero, prioridade, canal, observacoes, link], spacing=10, tight=True),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(dlg, 'open', False) or page.update()),
                ft.ElevatedButton("Salvar", bgcolor="#22C55E", color="#FFFFFF", on_click=salvar),
            ],
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()
    
    carregar_chamados()
    
    return ft.Column([
        ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text("Chamados", size=26, weight=ft.FontWeight.BOLD, color=theme.get_text_color()),
                    ft.Text("Controle de chamados abertos", size=11, color=theme.get_text_secondary()),
                ], spacing=2, expand=True),
                ft.ElevatedButton("+ Novo Chamado", bgcolor="#22C55E", color="#FFFFFF", on_click=abrir_modal_criar),
            ]),
            padding=ft.padding.only(left=25, right=25, top=20, bottom=10),
        ),
        ft.Container(
            content=ft.Tabs(
                tabs=[
                    ft.Tab(
                        text="📋 Ativos",
                        content=ft.Container(content=lista_ativos, padding=15),
                    ),
                    ft.Tab(
                        text="🗑️ Lixeira",
                        content=ft.Container(content=lista_lixeira, padding=15),
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
