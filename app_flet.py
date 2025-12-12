"""
SINC - Sistema de Sincronização de SKUs
Design Moderno: Preto & Branco com Menu Expansível

Arquivo principal refatorado - importa telas de views/
"""
import flet as ft
import os
import time
from services.database_sinc import (
    create_tables, criar_usuario_inicial, verificar_usuario, set_db_path,
    cadastrar_usuario, listar_usuarios_pendentes, listar_todos_usuarios,
    aprovar_usuario, rejeitar_usuario, alterar_cargo_usuario, registrar_log
)
from services.config_rede import get_config, save_config, get_db_path, test_connection
from services.backup import executar_backup_automatico
from utils.theme import ThemeManager
from utils.toast import toast_success, toast_error, toast_warning, toast_info
from views.tela_dashboard import criar_tela_dashboard
from views.tela_sinc import criar_tela_sinc
from views.tela_canais import criar_tela_canais
from views.tela_canal import criar_tela_canal
from views.tela_lista_preco import criar_tela_lista_preco
from views.tela_blocklist import criar_tela_blocklist
from views.tela_usuarios import criar_tela_usuarios
from views.tela_automacoes import criar_tela_automacoes
from views.tela_configuracoes import criar_tela_configuracoes
from views.tela_chamados import criar_tela_chamados
from views.tela_relatorios import criar_tela_relatorios


def main(page: ft.Page):
    page.title = "SINC - Sistema de Sincronização"
    page.padding = 0
    page.spacing = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.width = 1200
    page.window.height = 800
    page.window.center()
    
    # Sistema de tema
    theme = ThemeManager()
    
    create_tables()
    criar_usuario_inicial()
    
    # Backup automático diário
    executar_backup_automatico()
    
    usuario_logado = [None]
    pagina_atual = [0]
    menu_expandido = [False]
    atualizar_tela_fn = [None]  # Referência para função de atualizar tela
    
    file_picker = ft.FilePicker()
    save_picker = ft.FilePicker()
    page.overlay.extend([file_picker, save_picker])
    
    # ══════════════════════════════════════════════════════════════
    # ATALHOS DE TECLADO
    # ══════════════════════════════════════════════════════════════
    def on_keyboard(e: ft.KeyboardEvent):
        # F5 - Atualizar tela
        if e.key == "F5":
            if atualizar_tela_fn[0]:
                atualizar_tela_fn[0]()
                toast_info(page, "Tela atualizada!")
        # Escape - Fechar modais
        elif e.key == "Escape":
            for overlay in page.overlay:
                if hasattr(overlay, 'open') and overlay.open:
                    overlay.open = False
            page.update()
    
    page.on_keyboard_event = on_keyboard
    
    # ══════════════════════════════════════════════════════════════
    # TELA DE LOGIN
    # ══════════════════════════════════════════════════════════════
    def criar_login():
        # Carregar configuração salva
        config = get_config()
        
        servidor = ft.TextField(label="Servidor (IP ou localhost)", prefix_icon=ft.Icons.DNS,
                               border_radius=8, bgcolor="#FFFFFF", width=300,
                               value=config.get('server_ip', 'localhost'),
                               hint_text="Ex: 192.168.0.126 ou localhost")
        usuario = ft.TextField(label="Usuário", prefix_icon=ft.Icons.PERSON_OUTLINE, 
                               border_radius=8, bgcolor="#FFFFFF", width=300,
                               on_submit=lambda e: login(e))
        senha = ft.TextField(label="Senha", prefix_icon=ft.Icons.LOCK_OUTLINE, 
                            password=True, can_reveal_password=True, border_radius=8, 
                            bgcolor="#FFFFFF", width=300,
                            on_submit=lambda e: login(e))
        erro = ft.Text("", color=ft.Colors.RED_400, size=12)
        status_conexao = ft.Text("", size=11, color="#22C55E")
        
        def testar_servidor(e):
            ip = servidor.value.strip() or "localhost"
            ok, msg, path = test_connection(ip)
            if ok:
                status_conexao.value = f"✅ {msg}"
                status_conexao.color = "#22C55E"
            else:
                status_conexao.value = f"❌ {msg}"
                status_conexao.color = "#EF4444"
            page.update()
        
        def login(e):
            # Primeiro conecta ao servidor
            ip = servidor.value.strip() or "localhost"
            db_path = get_db_path(ip)
            
            # Salva configuração
            save_config(ip)
            
            # Define o caminho do banco
            set_db_path(db_path)
            
            # Tenta criar tabelas (se for servidor novo)
            try:
                create_tables()
                criar_usuario_inicial()
            except Exception as ex:
                erro.value = f"Erro ao conectar: {str(ex)}"
                page.update()
                return
            
            ok, msg, dados = verificar_usuario(usuario.value, senha.value)
            if ok:
                usuario_logado[0] = dados
                nome = dados.get('nome', dados.get('username', 'Usuário'))
                registrar_log(usuario.value, "Login", f"Usuário logou no sistema")
                mostrar_splash(nome)
            else:
                erro.value = msg
                page.update()
        
        def abrir_cadastro(e):
            nome_cad = ft.TextField(label="Nome completo", prefix_icon=ft.Icons.PERSON, width=280)
            user_cad = ft.TextField(label="Nome de usuário", prefix_icon=ft.Icons.ACCOUNT_CIRCLE, width=280)
            email_cad = ft.TextField(label="Email", prefix_icon=ft.Icons.EMAIL, width=280)
            senha_cad = ft.TextField(label="Senha", prefix_icon=ft.Icons.LOCK, password=True, width=280)
            senha_conf = ft.TextField(label="Confirmar senha", prefix_icon=ft.Icons.LOCK_OUTLINE, password=True, width=280)
            msg_cad = ft.Text("", size=12)
            
            def fazer_cadastro(e):
                if not all([nome_cad.value, user_cad.value, email_cad.value, senha_cad.value]):
                    msg_cad.value = "Preencha todos os campos!"
                    msg_cad.color = "#EF4444"
                    page.update()
                    return
                
                if senha_cad.value != senha_conf.value:
                    msg_cad.value = "Senhas não conferem!"
                    msg_cad.color = "#EF4444"
                    page.update()
                    return
                
                # Primeiro conecta ao servidor
                ip = servidor.value.strip() or "localhost"
                db_path = get_db_path(ip)
                set_db_path(db_path)
                
                try:
                    create_tables()
                except:
                    pass
                
                ok, msg = cadastrar_usuario(user_cad.value, senha_cad.value, nome_cad.value, email_cad.value)
                if ok:
                    msg_cad.value = msg
                    msg_cad.color = "#22C55E"
                    # Limpar campos
                    nome_cad.value = user_cad.value = email_cad.value = senha_cad.value = senha_conf.value = ""
                else:
                    msg_cad.value = msg
                    msg_cad.color = "#EF4444"
                page.update()
            
            def fechar_dlg(e):
                dlg_cadastro.open = False
                page.update()
            
            dlg_cadastro = ft.AlertDialog(
                modal=True,
                title=ft.Text("📝 Criar Conta", weight=ft.FontWeight.BOLD),
                content=ft.Column([
                    nome_cad, user_cad, email_cad, senha_cad, senha_conf,
                    ft.Container(height=5),
                    msg_cad,
                ], tight=True, spacing=10),
                actions=[
                    ft.TextButton("Cancelar", on_click=fechar_dlg),
                    ft.ElevatedButton("Cadastrar", bgcolor="#22C55E", color="#FFFFFF", on_click=fazer_cadastro),
                ],
            )
            page.overlay.append(dlg_cadastro)
            dlg_cadastro.open = True
            page.update()
        
        return ft.Container(
            content=ft.Row([
                # Lado esquerdo - Visual com gradiente
                ft.Container(
                    content=ft.Column([
                        ft.Image(
                            src=os.path.join(os.path.dirname(__file__), "data", "logo2.png"),
                            width=360, height=360, fit=ft.ImageFit.CONTAIN,
                        ),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, 
                       alignment=ft.MainAxisAlignment.CENTER, spacing=15),
                    expand=True,
                    gradient=ft.LinearGradient(
                        begin=ft.alignment.top_left,
                        end=ft.alignment.bottom_right,
                        colors=["#F59E0B", "#F97316", "#14B8A6", "#0D9488", "#1F2937", "#111827"],
                    ),
                ),
                # Lado direito - Form
                ft.Container(
                    content=ft.Column([
                        ft.Text("Entrar", size=32, weight=ft.FontWeight.BOLD, color="#000000"),
                        ft.Container(height=15),
                        servidor,
                        ft.Row([status_conexao, ft.TextButton("Testar", on_click=testar_servidor)], 
                              alignment=ft.MainAxisAlignment.SPACE_BETWEEN, width=300),
                        ft.Container(height=8),
                        usuario,
                        ft.Container(height=8),
                        senha,
                        erro,
                        ft.Container(height=15),
                        ft.ElevatedButton(
                            "Acessar", width=300, height=50,
                            bgcolor="#000000", color="#FFFFFF",
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                            on_click=login,
                        ),
                        ft.Container(height=10),
                        ft.TextButton("Não tem conta? Cadastre-se", on_click=abrir_cadastro),
                        ft.Container(height=10),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, 
                       alignment=ft.MainAxisAlignment.CENTER),
                    expand=True,
                    bgcolor="#FFFFFF",
                    padding=40,
                ),
            ], spacing=0, expand=True),
            expand=True,
        )
    
    # ══════════════════════════════════════════════════════════════
    # SPLASH SCREEN - Animado com "Sinc"
    # ══════════════════════════════════════════════════════════════
    def mostrar_splash(nome_usuario):
        page.window.width = 1000
        page.window.height = 700
        page.window.center()
        page.clean()
        
        # Texto "Sinc" animado (entra da direita) com sombra branca sutil
        texto_sinc = ft.Container(
            content=ft.Stack([
                # Sombra branca sutil (atrás)
                ft.Text(
                    "Sinc", 
                    size=160, 
                    weight=ft.FontWeight.BOLD, 
                    color=ft.Colors.with_opacity(0.3, "#FFFFFF"),
                    font_family="Georgia",
                ),
                # Texto principal (na frente)
                ft.Container(
                    content=ft.Text(
                        "Sinc", 
                        size=160, 
                        weight=ft.FontWeight.BOLD, 
                        color="#000000",
                        font_family="Georgia",
                    ),
                    left=2,  # Desloca levemente para criar efeito de sombra
                    top=2,
                ),
            ]),
            offset=ft.Offset(2, 0),  # Começa fora da tela (direita)
            animate_offset=ft.Animation(1200, ft.AnimationCurve.EASE_OUT_CUBIC),
        )
        
        texto_bemvindo = ft.Container(
            content=ft.Text(
                f"Bem vindo, {nome_usuario}!", 
                size=22, 
                weight=ft.FontWeight.W_400, 
                color="#000000",
                opacity=0.9,
            ),
            opacity=0,
            animate_opacity=ft.Animation(800, ft.AnimationCurve.EASE_OUT),
        )
        
        splash = ft.Container(
            content=ft.Column([
                texto_sinc,
                ft.Container(height=45),
                texto_bemvindo,
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, 
               alignment=ft.MainAxisAlignment.CENTER),
            expand=True,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=["#F59E0B", "#F97316", "#14B8A6", "#0D9488", "#1F2937", "#111827"],
            ),
        )
        
        page.add(splash)
        page.update()
        
        # Animação: texto entra da direita
        time.sleep(0.1)
        texto_sinc.offset = ft.Offset(0, 0)  # Move para o centro
        page.update()
        
        # Animação: bem-vindo aparece
        time.sleep(1.2)
        texto_bemvindo.opacity = 1
        page.update()
        
        time.sleep(2.5)
        abrir_app()
    
    # ══════════════════════════════════════════════════════════════
    # APP PRINCIPAL
    # ══════════════════════════════════════════════════════════════
    def abrir_app():
        page.window.maximized = True
        page.clean()
        
        conteudo = ft.Container(expand=True, padding=0)
        
        def nav(idx):
            pagina_atual[0] = idx
            if idx == 0: 
                conteudo.content = criar_tela_sinc(page, file_picker, usuario_logado, theme)
            elif idx == 1: 
                conteudo.content = criar_tela_canais(page, abrir_canal, theme)
            elif idx == 2: 
                conteudo.content = criar_tela_lista_preco(page, save_picker, theme)
            elif idx == 3: 
                conteudo.content = criar_tela_blocklist(page, theme)
            elif idx == 4:
                conteudo.content = criar_tela_usuarios(page, usuario_logado, theme)
            elif idx == 5:
                conteudo.content = criar_tela_automacoes(page, file_picker, theme)
            elif idx == 6:
                conteudo.content = criar_tela_configuracoes(page, usuario_logado, theme)
            elif idx == 7:
                conteudo.content = criar_tela_chamados(page, usuario_logado, theme)
            elif idx == 8:
                conteudo.content = criar_tela_relatorios(page, save_picker, theme)
            atualizar_menu()
            page.update()
        
        def abrir_canal(canal):
            conteudo.content = criar_tela_canal(page, canal, file_picker, usuario_logado, nav, theme)
            page.update()
        
        def toggle_theme(e):
            theme.toggle()
            if theme.is_dark[0]:
                page.theme_mode = ft.ThemeMode.DARK
            else:
                page.theme_mode = ft.ThemeMode.LIGHT
            
            page.bgcolor = theme.get_bg()
            conteudo.bgcolor = theme.get_bg()
            menu_col.controls[1].content.color = "#FFFFFF"
            atualizar_menu()
            nav(pagina_atual[0])
            page.update()
        
        def criar_menu_item(icone, texto, idx):
            ativo = pagina_atual[0] == idx
            cor_item = "#FFFFFF" if ativo else "#E0E0E0"
            bg_ativo = "#22C55E" if ativo else ft.Colors.TRANSPARENT
            
            return ft.Container(
                content=ft.Row([
                    ft.Icon(icone, size=22, color=cor_item),
                    ft.AnimatedSwitcher(
                        content=ft.Text(texto, size=13, color=cor_item, weight=ft.FontWeight.W_500) if menu_expandido[0] else ft.Container(),
                        duration=200, transition=ft.AnimatedSwitcherTransition.FADE,
                    ),
                ], spacing=15),
                padding=12,
                bgcolor=bg_ativo,
                border_radius=10,
                on_click=lambda e: nav(idx),
                ink=True,
                tooltip=texto if not menu_expandido[0] else None,
            )
        
        menu_items = []
        def atualizar_menu():
            nonlocal menu_items
            menu_items.clear()
            menu_items.extend([
                criar_menu_item(ft.Icons.SYNC, "Sincronização", 0),
                criar_menu_item(ft.Icons.STOREFRONT, "Canais", 1),
                criar_menu_item(ft.Icons.ATTACH_MONEY, "Lista Preço", 2),
                criar_menu_item(ft.Icons.BLOCK, "Blocklist", 3),
                criar_menu_item(ft.Icons.AUTO_MODE, "Automações", 5),
                criar_menu_item(ft.Icons.SUPPORT_AGENT, "Chamados", 7),
                criar_menu_item(ft.Icons.BAR_CHART, "Relatórios", 8),
                criar_menu_item(ft.Icons.SETTINGS, "Configurações", 6),
            ])
            # Menu Usuários só para admins
            cargo = usuario_logado[0].get('cargo', 'usuario') if usuario_logado[0] else 'usuario'
            if cargo == 'admin':
                menu_items.append(criar_menu_item(ft.Icons.PEOPLE, "Usuários", 4))
            
            cor_logo = theme.get_text_color()
            
            menu_col.controls = [
                ft.Container(height=30),
                ft.Container(content=ft.Icon(ft.Icons.SYNC, size=32, color=cor_logo), padding=15),
                ft.Container(height=30),
                *menu_items,
                ft.Container(expand=True),
                ft.Column([
                    ft.IconButton(ft.Icons.BRIGHTNESS_6, icon_color="#E0E0E0", tooltip="Alternar tema", on_click=toggle_theme),
                    ft.IconButton(ft.Icons.LOGOUT, icon_color="#E0E0E0", tooltip="Sair", on_click=lambda e: page.window.close()),
                ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(height=15),
            ]
        
        def on_menu_hover(e):
            menu_expandido[0] = e.data == "true"
            menu_container.width = 200 if menu_expandido[0] else 70
            atualizar_menu()
            page.update()
        
        menu_col = ft.Column([], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        atualizar_menu()
        
        menu_container = ft.Container(
            content=menu_col,
            width=70,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=["#F59E0B", "#F97316", "#14B8A6", "#0D9488", "#1F2937", "#111827"],
            ),
            padding=ft.padding.symmetric(horizontal=10),
            animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
            on_hover=on_menu_hover,
            shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.with_opacity(0.1, "#000000")),
        )
        
        # Tela inicial
        conteudo.content = criar_tela_sinc(page, file_picker, usuario_logado, theme)
        
        page.add(ft.Row([
            menu_container,
            ft.Container(content=conteudo, expand=True, bgcolor=ft.Colors.TRANSPARENT),
        ], expand=True, spacing=0))
    
    page.add(criar_login())


if __name__ == "__main__":
    # App desktop - cada PC conecta ao banco via caminho de rede configurado no login
    ft.app(target=main)
