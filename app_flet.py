"""
SINC - Sistema de Sincronização de SKUs
Design Moderno: Preto & Branco com Menu Expansível

Arquivo principal refatorado - importa telas de views/
"""
import flet as ft
import os
import sys
import threading
from utils import resource_path
from services.database_sinc import (
    create_tables, criar_usuario_inicial, verificar_usuario, set_db_path,
    cadastrar_usuario, listar_usuarios_pendentes, listar_todos_usuarios,
    aprovar_usuario, rejeitar_usuario, alterar_cargo_usuario, registrar_log
)
from services.config_rede import get_config, save_config, get_db_path, test_connection, config_exists
from services.backup import executar_backup_automatico
from services.usuarios_online import (
    registrar_usuario_online, listar_usuarios_online, 
    criar_tabela_usuarios_online, remover_usuario_online
)
from services.auto_update import (
    check_for_update, perform_full_update, get_local_version
)
from services.changelog import get_recent_versions, get_latest_version
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
    
    # Só inicializa DB se já existe configuração salva
    # Novos usuários vão configurar o IP primeiro na tela de login
    if config_exists():
        try:
            create_tables()
            criar_usuario_inicial()
            # Backup automático diário
            executar_backup_automatico()
        except Exception as e:
            print(f"[Aviso] Erro ao conectar ao banco: {e}")
    
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
    # VERIFICAÇÃO DE ATUALIZAÇÃO
    # ══════════════════════════════════════════════════════════════
    def verificar_atualizacao_e_continuar(nome_usuario):
        """Verifica se há atualização disponível e mostra diálogo se houver."""
        
        def checar_em_thread():
            try:
                has_update, new_version, download_url, release_notes = check_for_update()
                
                if has_update and download_url:
                    # Mostrar diálogo de atualização
                    mostrar_dialogo_atualizacao(nome_usuario, new_version, download_url, release_notes)
                else:
                    # Sem atualização, continuar para splash
                    mostrar_splash(nome_usuario)
                    
            except Exception as ex:
                print(f"[AutoUpdate] Erro na verificação: {ex}")
                # Em caso de erro, continuar normalmente
                mostrar_splash(nome_usuario)
        
        # Executar verificação em thread separada para não bloquear UI
        threading.Thread(target=checar_em_thread, daemon=True).start()
    
    def mostrar_dialogo_atualizacao(nome_usuario, new_version, download_url, release_notes):
        """Mostra diálogo para o usuário decidir se quer atualizar."""
        
        local_version = get_local_version()
        
        # Componentes do diálogo
        progress_bar = ft.ProgressBar(width=350, visible=False, color="#22C55E")
        progress_text = ft.Text("", size=12, color="#666666")
        status_text = ft.Text("", size=12, color="#666666")
        btn_atualizar = ft.ElevatedButton(
            "🚀 Atualizar Agora",
            bgcolor="#22C55E",
            color="#FFFFFF",
            width=150,
        )
        btn_depois = ft.TextButton("Depois", width=100)
        
        def fechar_dialogo(e=None):
            dlg_update.open = False
            page.update()
            mostrar_splash(nome_usuario)
        
        def iniciar_atualizacao(e):
            btn_atualizar.disabled = True
            btn_depois.disabled = True
            progress_bar.visible = True
            status_text.value = "Baixando atualização..."
            page.update()
            
            def fazer_download():
                def on_progress(baixado, total):
                    if total > 0:
                        pct = baixado / total
                        progress_bar.value = pct
                        mb_baixado = baixado / (1024 * 1024)
                        mb_total = total / (1024 * 1024)
                        progress_text.value = f"{mb_baixado:.1f} MB / {mb_total:.1f} MB"
                        page.update()
                
                def on_status(msg):
                    status_text.value = msg
                    page.update()
                
                success = perform_full_update(
                    download_url,
                    progress_callback=on_progress,
                    status_callback=on_status
                )
                
                if success:
                    # Atualização aplicada com sucesso
                    status_text.value = "✅ Atualização concluída!"
                    status_text.color = "#22C55E"
                    progress_text.value = "Feche o aplicativo e abra novamente."
                    progress_bar.visible = False
                    
                    # Mudar botões
                    btn_atualizar.text = "Fechar Aplicativo"
                    btn_atualizar.disabled = False
                    btn_atualizar.on_click = lambda e: fechar_app()
                    btn_depois.visible = False
                    page.update()
                else:
                    status_text.value = "❌ Erro na atualização. Tente novamente mais tarde."
                    status_text.color = "#EF4444"
                    btn_atualizar.disabled = False
                    btn_depois.disabled = False
                    btn_atualizar.text = "Tentar Novamente"
                    page.update()
            
            threading.Thread(target=fazer_download, daemon=True).start()
        
        def fechar_app():
            """Fecha o aplicativo após atualização."""
            import os
            page.window.close()
            threading.Timer(0.5, lambda: os._exit(0)).start()
        
        btn_atualizar.on_click = iniciar_atualizacao
        btn_depois.on_click = fechar_dialogo
        
        # Formatar notas do release (limitar tamanho)
        notas_resumidas = ""
        if release_notes:
            notas_resumidas = release_notes[:300] + "..." if len(release_notes) > 300 else release_notes
        
        dlg_update = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.SYSTEM_UPDATE, color="#22C55E", size=28),
                ft.Text("Nova Versão Disponível!", weight=ft.FontWeight.BOLD, size=18),
            ], spacing=10),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(
                        f"Uma nova versão do SINC está disponível.",
                        size=14,
                    ),
                    ft.Container(height=10),
                    ft.Row([
                        ft.Container(
                            content=ft.Column([
                                ft.Text("Versão Atual", size=11, color="#888888"),
                                ft.Text(f"v{local_version}", size=16, weight=ft.FontWeight.BOLD),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                            bgcolor="#F3F4F6",
                            padding=15,
                            border_radius=8,
                            expand=True,
                        ),
                        ft.Icon(ft.Icons.ARROW_FORWARD, color="#22C55E"),
                        ft.Container(
                            content=ft.Column([
                                ft.Text("Nova Versão", size=11, color="#888888"),
                                ft.Text(f"{new_version}", size=16, weight=ft.FontWeight.BOLD, color="#22C55E"),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                            bgcolor="#ECFDF5",
                            padding=15,
                            border_radius=8,
                            expand=True,
                        ),
                    ], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
                    ft.Container(height=10),
                    ft.Text(notas_resumidas, size=12, color="#666666") if notas_resumidas else ft.Container(),
                    ft.Container(height=15),
                    progress_bar,
                    progress_text,
                    status_text,
                ], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                width=380,
                padding=10,
            ),
            actions=[
                btn_depois,
                btn_atualizar,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        page.overlay.append(dlg_update)
        dlg_update.open = True
        page.update()
    
    # ══════════════════════════════════════════════════════════════
    # TELA DE LOGIN
    # ══════════════════════════════════════════════════════════════
    def criar_login():
        # Carregar configuração salva
        config = get_config()
        
        servidor = ft.TextField(label="Servidor MySQL (IP)", prefix_icon=ft.Icons.DNS,
                               border_radius=8, bgcolor="#FFFFFF", width=300,
                               value=config.get('mysql_host', 'localhost'),
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
            # Configurar conexão MySQL
            ip = servidor.value.strip() or "localhost"
            
            # Salva configuração MySQL
            save_config(mysql_host=ip)
            
            # Tenta criar tabelas no MySQL
            try:
                create_tables()
                criar_usuario_inicial()
            except Exception as ex:
                erro.value = f"Erro ao conectar MySQL: {str(ex)}"
                page.update()
                return
            
            ok, msg, dados = verificar_usuario(usuario.value, senha.value)
            if ok:
                usuario_logado[0] = dados
                nome = dados.get('nome', dados.get('username', 'Usuário'))
                registrar_log(usuario.value, "Login", f"Usuário logou no sistema")
                
                # Verificar atualização disponível
                verificar_atualizacao_e_continuar(nome)
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
                            src=resource_path(os.path.join("data", "logo2.png")),
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
            animate_offset=ft.Animation(800, ft.AnimationCurve.EASE_OUT_CUBIC),
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
            animate_opacity=ft.Animation(600, ft.AnimationCurve.EASE_OUT),
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
        
        # ══════════════════════════════════════════════════════════════
        # ANIMAÇÃO NÃO-BLOQUEANTE usando threading
        # ══════════════════════════════════════════════════════════════
        def animar_texto():
            texto_sinc.offset = ft.Offset(0, 0)  # Move para o centro
            page.update()
        
        def animar_bemvindo():
            texto_bemvindo.opacity = 1
            page.update()
        
        def finalizar_splash():
            abrir_app()
        
        # Agendar animações com timers (não-bloqueante)
        threading.Timer(0.05, animar_texto).start()
        threading.Timer(0.9, animar_bemvindo).start()
        threading.Timer(1.8, finalizar_splash).start()
    
    # ══════════════════════════════════════════════════════════════
    # APP PRINCIPAL
    # ══════════════════════════════════════════════════════════════
    def abrir_app():
        page.window.maximized = True
        page.clean()
        
        conteudo = ft.Container(expand=True, padding=0)
        
        # ══════════════════════════════════════════════════════════════
        # NOTIFICAÇÃO DE CHANGELOG (What's New)
        # ══════════════════════════════════════════════════════════════
        notificacao_ref = [None]  # Referência para a notificação
        
        def mostrar_notificacao_changelog():
            """Mostra notificação de changelog no canto inferior direito."""
            latest_version_info = get_recent_versions(1)[0]
            
            # Container da notificação (pequeno)
            notif_container = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.CELEBRATION, color="#FFFFFF", size=20),
                        ft.Text(
                            f"Novidades v{latest_version_info['version']}",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color="#FFFFFF"
                        ),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            icon_size=16,
                            icon_color="#FFFFFF",
                            on_click=lambda e: fechar_notificacao(),
                        ),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=5),
                    ft.Container(height=5),
                    ft.Column([
                        ft.Text(
                            item[:50] + "..." if len(item) > 50 else item,
                            size=11,
                            color="#FFFFFF",
                            opacity=0.9
                        )
                        for item in latest_version_info['novidades'][:2]
                    ], spacing=3),
                    ft.Container(height=5),
                    ft.TextButton(
                        "Ver mais",
                        on_click=lambda e: expandir_changelog(),
                        style=ft.ButtonStyle(
                            color="#FFFFFF",
                            bgcolor={ft.MaterialState.DEFAULT: ft.Colors.with_opacity(0.2, "#FFFFFF")}
                        ),
                    ),
                ], spacing=5, tight=True),
                bgcolor=latest_version_info.get('cor', '#22C55E'),
                padding=15,
                border_radius=10,
                width=300,
                shadow=ft.BoxShadow(
                    blur_radius=15,
                    color=ft.Colors.with_opacity(0.3, "#000000"),
                    offset=ft.Offset(-2, 2)
                ),
                right=20,
                bottom=20,
                animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
                offset=ft.Offset(2, 0),  # Começa fora da tela (direita)
            )
            
            notificacao_ref[0] = notif_container
            page.overlay.append(notif_container)
            page.update()
            
            # Animar entrada
            def animar_entrada():
                notif_container.offset = ft.Offset(0, 0)
                page.update()
            
            threading.Timer(0.1, animar_entrada).start()
            
            # Auto-close após 5 segundos
            def auto_close():
                if notificacao_ref[0] and notificacao_ref[0] in page.overlay:
                    fechar_notificacao()
            
            threading.Timer(5, auto_close).start()
        
        def fechar_notificacao():
            """Fecha a notificação com animação."""
            if notificacao_ref[0] and notificacao_ref[0] in page.overlay:
                notificacao_ref[0].offset = ft.Offset(2, 0)
                page.update()
                
                def remover():
                    if notificacao_ref[0] in page.overlay:
                        page.overlay.remove(notificacao_ref[0])
                        page.update()
                
                threading.Timer(0.3, remover).start()
        
        def expandir_changelog():
            """Expande para modal completo com todas as versões."""
            fechar_notificacao()
            
            versions = get_recent_versions(5)
            
            # Criar colunas de versões
            version_cards = []
            for v_info in versions:
                version_cards.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Container(
                                    content=ft.Text(
                                        f"v{v_info['version']}",
                                        size=18,
                                        weight=ft.FontWeight.BOLD,
                                        color="#FFFFFF"
                                    ),
                                    bgcolor=v_info.get('cor', '#22C55E'),
                                    padding=ft.padding.symmetric(horizontal=15, vertical=5),
                                    border_radius=20,
                                ),
                                ft.Text(
                                    v_info['data'],
                                    size=12,
                                    color="#888888"
                                ),
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Container(height=5),
                            ft.Text(
                                v_info['titulo'],
                                size=16,
                                weight=ft.FontWeight.W_500,
                            ),
                            ft.Container(height=8),
                            ft.Column([
                                ft.Text(
                                    item,
                                    size=13,
                                )
                                for item in v_info['novidades']
                            ], spacing=5),
                        ], spacing=8),
                        padding=20,
                        border=ft.border.all(1, "#E5E7EB"),
                        border_radius=10,
                        bgcolor="#FAFAFA",
                    )
                )
            
            dlg_changelog = ft.AlertDialog(
                modal=True,
                title=ft.Row([
                    ft.Icon(ft.Icons.HISTORY, color="#22C55E", size=28),
                    ft.Text("O que há de novo?", weight=ft.FontWeight.BOLD, size=20),
                ], spacing=10),
                content=ft.Container(
                    content=ft.Column(
                        version_cards,
                        spacing=15,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    width=600,
                    height=500,
                ),
                actions=[
                    ft.TextButton("Fechar", on_click=lambda e: fechar_dlg()),
                ],
            )
            
            def fechar_dlg():
                dlg_changelog.open = False
                page.update()
            
            page.overlay.append(dlg_changelog)
            dlg_changelog.open = True
            page.update()
        
        def nav(idx):
            pagina_atual[0] = idx
            if idx == 0: 
                conteudo.content = criar_tela_sinc(page, file_picker, usuario_logado, theme)
            elif idx == 1: 
                conteudo.content = criar_tela_canais(page, abrir_canal, theme)
            elif idx == 2: 
                conteudo.content = criar_tela_lista_preco(page, save_picker, usuario_logado, theme)
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
        
        # ══════════════════════════════════════════════════════════════
        # SISTEMA DE USUÁRIOS ONLINE
        # ══════════════════════════════════════════════════════════════
        ping_ativo = [True]
        
        def fazer_ping():
            """Envia ping para manter status online"""
            if ping_ativo[0] and usuario_logado[0]:
                username = usuario_logado[0].get('username', '')
                if username:
                    registrar_usuario_online(username)
                
                # Timer deve ser Daemon para não impedir o fechamento do app
                t = threading.Timer(30, fazer_ping)
                t.daemon = True
                t.start()
        
        def fazer_logout(e=None):
            """Remove usuário da lista online e fecha definitivamente"""
            ping_ativo[0] = False
            if usuario_logado[0]:
                username = usuario_logado[0].get('username', '')
                if username:
                    try:
                        remover_usuario_online(username)
                    except:
                        pass
            
            # Fecha a janela e agenda o encerramento do processo
            def encerrar():
                import os
                os._exit(0)
            
            page.window.close()
            # Aguarda 0.5 segundo antes de forçar encerramento
            t_exit = threading.Timer(0.5, encerrar)
            t_exit.daemon = True
            t_exit.start()
        
        def criar_indicador_online():
            """Cria indicador de usuários online no menu"""
            try:
                online = listar_usuarios_online(timeout_minutos=2)
                
                # Lista de bolinhas com nomes
                items = []
                for u in online[:5]:  # Max 5 usuários
                    username = u.get('username', '')
                    items.append(
                        ft.Row([
                            ft.Container(
                                width=8, height=8, 
                                bgcolor="#22C55E",  # Verde
                                border_radius=4,
                            ),
                            ft.Text(username[:15], size=10, color="#E0E0E0") if menu_expandido[0] else ft.Container(),
                        ], spacing=5)
                    )
                
                if not items:
                    items.append(ft.Text("Nenhum online", size=9, color="#888888", italic=True) if menu_expandido[0] else ft.Container())
                
                return ft.Container(
                    content=ft.Column(items, spacing=3),
                    padding=ft.padding.symmetric(horizontal=10, vertical=8),
                    visible=menu_expandido[0],
                )
            except:
                return ft.Container()
        
        # Iniciar ping e criar tabela
        try:
            criar_tabela_usuarios_online()
            fazer_ping()
        except Exception as ex:
            print(f"Erro ao iniciar sistema de usuários online: {ex}")
        
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
                # Indicador de usuários online
                criar_indicador_online(),
                ft.Column([
                    ft.IconButton(ft.Icons.BRIGHTNESS_6, icon_color="#E0E0E0", tooltip="Alternar tema", on_click=toggle_theme),
                    ft.IconButton(ft.Icons.LOGOUT, icon_color="#E0E0E0", tooltip="Sair", on_click=fazer_logout),
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
        
        # Mostrar notificação de changelog após 1 segundo
        threading.Timer(1, mostrar_notificacao_changelog).start()
    
    page.add(criar_login())


if __name__ == "__main__":
    # App desktop - cada PC conecta ao banco via caminho de rede configurado no login
    ft.app(target=main)
