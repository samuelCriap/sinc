"""
Tela Sincronização - Visualização e importação de produtos
"""
import flet as ft
import os
import shutil
import threading
from datetime import datetime
from services.database_sinc import (
    listar_produtos, get_connection, atualizar_importacao_externa, 
    salvar_lista_preco, listar_produtos_bloqueados, CANAIS, registrar_log
)
from services.auto_refresh import is_auto_refresh_enabled, get_refresh_interval
from utils.theme import COR_CANAL, ABREV

# Controle de auto-refresh global
_refresh_timer = [None]


def criar_tela_sinc(page: ft.Page, file_picker: ft.FilePicker, usuario_logado: list, theme):
    """
    Cria a tela de sincronização de produtos.
    
    Args:
        page: Página Flet
        file_picker: FilePicker para seleção de arquivos
        usuario_logado: Lista com dados do usuário logado
        theme: ThemeManager para cores
    
    Returns:
        ft.Column com a tela completa
    """
    # Usuário atual para logs
    usuario_atual = usuario_logado[0].get('username', 'Usuário') if usuario_logado[0] else 'Usuário'
    
    # ══════════════════════════════════════════════════════════════
    # ESTADO GLOBAL PARA TECLAS MODIFICADORAS (Shift/Ctrl)
    # ══════════════════════════════════════════════════════════════
    teclas_modificadoras = {'shift': False, 'ctrl': False}
    
    def on_keyboard_event(e: ft.KeyboardEvent):
        """Rastreia o estado das teclas Shift e Ctrl."""
        teclas_modificadoras['shift'] = e.shift
        teclas_modificadoras['ctrl'] = e.ctrl
    
    # Registrar handler de teclado na página
    page.on_keyboard_event = on_keyboard_event
    
    # Filtros
    filtro_sku = ft.TextField(label="SKU", width=150, height=45, text_size=12)
    filtro_data = ft.TextField(label="Data", hint_text="DD/MM/AAAA", width=130, height=45, text_size=12)
    filtro_status = ft.Dropdown(
        label="Status", width=130, text_size=12,
        options=[
            ft.dropdown.Option("", "Todos"),
            ft.dropdown.Option("ATIVO", "Ativo"),
            ft.dropdown.Option("CATALOGANDO", "Catalogando"),
            ft.dropdown.Option("ERRO", "Erro"),
            ft.dropdown.Option("BLOCKLIST", "Blocklist"),
        ],
    )
    
    # Larguras fixas para sincronizar cabeçalho e corpo
    COL_WIDTHS = {
        'cb': 30, '#': 35, 'SKU': 100, 'Produto': 180, 'Marca': 100, 
        'Data': 85, 'Usuario': 80, 'P.Omnie': 60, 'P.Any': 60, 'canal': 38
    }
    
    # Função para criar célula de cabeçalho com largura fixa
    def header_cell(texto, largura, cor_fundo=None):
        content = ft.Text(texto, size=10, weight=ft.FontWeight.W_600, color="#FFFFFF" if cor_fundo else theme.get_text_color())
        container = ft.Container(
            content=content, 
            width=largura, 
            bgcolor=cor_fundo,
            border_radius=4 if cor_fundo else 0,
            padding=ft.padding.symmetric(2, 5),
            alignment=ft.alignment.center,
        )
        return container
    
    # Estado de seleção múltipla
    linhas_selecionadas = set()
    ultima_linha_clicada = [-1]  # Mutável para usar em closures
    todos_dados_linhas = []  # Lista de dicts com dados de cada linha
    
    # Contador de seleção
    contador_selecao = ft.Text("0 selecionados", size=11, color=theme.get_text_secondary())
    
    # Checkbox selecionar todos
    def toggle_selecionar_todos(e):
        if e.control.value:
            for i in range(len(todos_dados_linhas)):
                linhas_selecionadas.add(i)
        else:
            linhas_selecionadas.clear()
        
        # Atualiza visual apenas dos checkboxes (sem mudar cor de fundo)
        for i, linha in enumerate(linhas_container.controls):
            try:
                cb_container = linha.content.controls[0]
                if cb_container and cb_container.content:
                    cb_container.content.value = e.control.value
            except:
                pass
        
        contador_selecao.value = f"{len(linhas_selecionadas)} selecionados"
        page.update()
    
    cb_selecionar_todos = ft.Checkbox(value=False, on_change=toggle_selecionar_todos, scale=0.8)
    
    # Cabeçalho fixo com checkbox
    header_controls = [
        ft.Container(content=cb_selecionar_todos, width=COL_WIDTHS['cb'], alignment=ft.alignment.center),
        header_cell("#", COL_WIDTHS['#']),
        header_cell("SKU", COL_WIDTHS['SKU']),
        header_cell("Produto", COL_WIDTHS['Produto']),
        header_cell("Marca", COL_WIDTHS['Marca']),
        header_cell("Data", COL_WIDTHS['Data']),
        header_cell("Usuário", COL_WIDTHS['Usuario']),
        header_cell("P.Omnie", COL_WIDTHS['P.Omnie']),
        header_cell("P.Any", COL_WIDTHS['P.Any']),
    ] + [header_cell(ABREV[c], COL_WIDTHS['canal'], COR_CANAL.get(c, "#888")) for c in CANAIS]
    
    tabela_header = ft.Container(
        content=ft.Row(header_controls, spacing=5),
        bgcolor=theme.get_header_bg(),
        padding=ft.padding.symmetric(10, 15),
        border_radius=ft.border_radius.only(top_left=8, top_right=8),
    )
    
    # Container para as linhas (será populado pelo carregar)
    linhas_container = ft.Column([], spacing=2, scroll=ft.ScrollMode.AUTO)
    
    def atualizar_visual_selecao():
        """Atualiza apenas o contador de selecionados."""
        contador_selecao.value = f"{len(linhas_selecionadas)} selecionados"
        cb_selecionar_todos.value = len(linhas_selecionadas) == len(todos_dados_linhas) if todos_dados_linhas else False
        page.update()
    
    def on_checkbox_linha_change(idx: int, e):
        """Toggle seleção via checkbox da linha."""
        if e.control.value:
            linhas_selecionadas.add(idx)
        else:
            linhas_selecionadas.discard(idx)
        ultima_linha_clicada[0] = idx
        atualizar_visual_selecao()
    
    # Dados filtrados para exportação
    dados_filtrados = []
    
    def carregar():
        nonlocal dados_filtrados
        dados_filtrados = []  # Limpar antes de carregar
        todos_dados_linhas.clear()
        linhas_selecionadas.clear()
        ultima_linha_clicada[0] = -1
        
        produtos = listar_produtos(limite=500)
        if not produtos:
            linhas_container.controls.clear()
            page.update()
            return
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # ══════════════════════════════════════════════════════════════
        # OTIMIZAÇÃO: Carregar todos os dados de canais em batch
        # ══════════════════════════════════════════════════════════════
        produto_ids = [p['id'] for p in produtos]
        placeholders = ','.join('?' * len(produto_ids))
        
        # Carregar todos os canais de uma vez
        cursor.execute(f"""
            SELECT produto_id, canal, status, importado_omnie, importado_anymarket 
            FROM produto_canal 
            WHERE produto_id IN ({placeholders})
        """, produto_ids)
        
        canais_por_produto = {}
        for row in cursor.fetchall():
            r = dict(row)
            pid = r['produto_id']
            if pid not in canais_por_produto:
                canais_por_produto[pid] = {}
            canais_por_produto[pid][r['canal']] = r
        
        # Carregar todos os bloqueios de uma vez
        cursor.execute(f"""
            SELECT produto_id, canal 
            FROM produto_blocklist 
            WHERE produto_id IN ({placeholders})
        """, produto_ids)
        
        bloqueados_por_produto = {}
        for row in cursor.fetchall():
            r = dict(row)
            pid = r['produto_id']
            if pid not in bloqueados_por_produto:
                bloqueados_por_produto[pid] = set()
            bloqueados_por_produto[pid].add(r['canal'])
        
        conn.close()
        
        linhas_container.controls.clear()
        
        f_sku = (filtro_sku.value or "").strip().lower()
        f_data = (filtro_data.value or "").strip()
        f_status = filtro_status.value or ""
        
        # Pré-calcular cores alternadas
        cor_par_dark = "#2A2A2A"
        cor_impar_dark = "#333333"
        cor_par_light = "#F8F9FA"
        cor_impar_light = "#FFFFFF"
        is_dark = theme.is_dark[0]
        
        linhas_batch = []
        row_num = 0
        
        for prod in produtos:
            pid = prod['id']
            canais = canais_por_produto.get(pid, {})
            bloqueados = bloqueados_por_produto.get(pid, set())
            
            if f_sku and f_sku not in (prod.get('codigo_produto', '') or '').lower():
                continue
            
            data_import = prod.get('created_at', '') or ''
            data_import_fmt = ""
            if data_import:
                try:
                    dt = datetime.strptime(data_import[:19], "%Y-%m-%d %H:%M:%S")
                    data_import_fmt = dt.strftime("%d/%m/%Y")
                except:
                    data_import_fmt = data_import[:10]
            
            if f_data and f_data != data_import_fmt:
                continue
            
            if f_status:
                status_list = [c.get('status', '') for c in canais.values()]
                if f_status not in status_list:
                    continue
            
            omnie = any(c.get('importado_omnie') for c in canais.values())
            anym = any(c.get('importado_anymarket') for c in canais.values())
            
            def mk_toggle(pid, tipo):
                def fn(e):
                    for c in CANAIS:
                        if tipo == 'o': atualizar_importacao_externa(pid, c, omnie=e.control.value)
                        else: atualizar_importacao_externa(pid, c, anymarket=e.control.value)
                return fn
            
            usuario_import = prod.get('importado_por', '') or ''
            current_idx = row_num
            
            # Criar células da linha de forma otimizada
            cells = [
                ft.Container(
                    content=ft.Checkbox(value=False, on_change=lambda e, idx=current_idx: on_checkbox_linha_change(idx, e), scale=0.7),
                    width=COL_WIDTHS['cb'], alignment=ft.alignment.center
                ),
                ft.Container(content=ft.Text(str(row_num + 1), size=10, color="#888888"), width=COL_WIDTHS['#'], padding=2),
                ft.Container(content=ft.Text(prod.get('codigo_produto', ''), size=10, weight=ft.FontWeight.W_500), width=COL_WIDTHS['SKU'], padding=2),
                ft.Container(content=ft.Text((prod.get('descricao', '') or '')[:25], size=10), width=COL_WIDTHS['Produto'], padding=2),
                ft.Container(content=ft.Text((prod.get('marca', '') or '')[:12], size=10), width=COL_WIDTHS['Marca'], padding=2),
                ft.Container(content=ft.Text(data_import_fmt, size=10), width=COL_WIDTHS['Data'], padding=2),
                ft.Container(content=ft.Text(usuario_import[:8], size=10), width=COL_WIDTHS['Usuario'], padding=2),
                ft.Container(content=ft.Checkbox(value=omnie, on_change=mk_toggle(pid, 'o'), scale=0.7), width=COL_WIDTHS['P.Omnie'], padding=2),
                ft.Container(content=ft.Checkbox(value=anym, on_change=mk_toggle(pid, 'a'), scale=0.7), width=COL_WIDTHS['P.Any'], padding=2),
            ]
            
            # Células dos canais (otimizado)
            for canal in CANAIS:
                st = canais.get(canal, {}).get('status', '') or ''
                is_blocklist = canal in bloqueados
                
                # Widget simples baseado no status
                if is_blocklist or st == 'BLOCKLIST':
                    w = ft.Container(width=10, height=10, bgcolor="#000000", border_radius=5)
                elif st == 'ATIVO':
                    w = ft.Container(width=10, height=10, bgcolor="#22C55E", border_radius=5)
                elif st == 'ERRO':
                    w = ft.Container(width=10, height=10, bgcolor="#EF4444", border_radius=5)
                elif st == 'CATALOGANDO':
                    w = ft.Container(width=10, height=10, bgcolor="#F59E0B", border_radius=5)
                else:
                    w = ft.Container(width=10, height=10, bgcolor="#E0E0E0", border_radius=5)
                cells.append(ft.Container(content=w, width=COL_WIDTHS['canal'], alignment=ft.alignment.center))
            
            # Cor de fundo alternada
            if is_dark:
                bg_cor = cor_par_dark if row_num % 2 == 0 else cor_impar_dark
            else:
                bg_cor = cor_par_light if row_num % 2 == 0 else cor_impar_light
            
            # Container da linha
            linha = ft.Container(
                content=ft.Row(cells, spacing=5),
                bgcolor=bg_cor,
                padding=ft.padding.symmetric(5, 10),
                border_radius=4,
                # on_click removido para melhor performance e UX
            )
            linhas_batch.append(linha)
            
            # Guardar dados para exportação com status por canal
            export_row = {
                'SKU': prod.get('codigo_produto', ''),
                'Produto': prod.get('descricao', '') or '',
                'Marca': prod.get('marca', '') or '',
                'Data': data_import_fmt,
                'Usuario': usuario_import,
            }
            
            # Adicionar status de cada canal (convertendo ícones para texto)
            for canal in CANAIS:
                if canal in bloqueados:
                    status_texto = 'BLOCKLIST'
                elif canal in canais:
                    st = canais[canal].get('status', '') or ''
                    if st == 'ATIVO':
                        status_texto = 'ATIVO'
                    elif st == 'ERRO':
                        status_texto = 'ERRO'
                    elif st == 'CATALOGANDO':
                        status_texto = 'CAT'
                    else:
                        status_texto = ''
                else:
                    status_texto = ''
                export_row[f'St_{canal}'] = status_texto
            
            dados_filtrados.append(export_row)
            
            # Guardar referência para seleção
            todos_dados_linhas.append(prod)
            row_num += 1
        
        # Adicionar todas as linhas de uma vez
        linhas_container.controls = linhas_batch
        atualizar_visual_selecao()
    
    filtro_sku.on_change = lambda e: carregar()
    filtro_data.on_change = lambda e: carregar()
    filtro_status.on_change = lambda e: carregar()
    
    def exportar(e):
        if not dados_filtrados:
            page.snack_bar = ft.SnackBar(ft.Text("Nenhum dado para exportar!"), bgcolor="#EF4444")
            page.snack_bar.open = True
            page.update()
            return
        
        def on_save(result):
            if result.path:
                try:
                    import pandas as pd
                    df = pd.DataFrame(dados_filtrados)
                    caminho = result.path if result.path.endswith('.xlsx') else result.path + '.xlsx'
                    df.to_excel(caminho, index=False)
                    registrar_log(usuario_atual, "Planilha exportada", f"{len(dados_filtrados)} registros - {os.path.basename(caminho)}")
                    page.snack_bar = ft.SnackBar(ft.Text(f"Exportado: {os.path.basename(caminho)}"), bgcolor="#22C55E")
                    page.snack_bar.open = True
                except Exception as ex:
                    page.snack_bar = ft.SnackBar(ft.Text(f"Erro: {str(ex)}"), bgcolor="#EF4444")
                    page.snack_bar.open = True
                page.update()
        
        file_picker.on_result = on_save
        file_picker.save_file(file_name=f"Sincronizacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", allowed_extensions=["xlsx"])
    
    def importar(e):
        def on_pick(r):
            if r.files and len(r.files) > 0:
                from services.importador import importar_planilha_produtos
                
                total_arquivos = len(r.files)
                
                progress_text = ft.Text(f"Preparando importação de {total_arquivos} arquivo(s)...", size=14)
                progress_bar = ft.ProgressBar(width=300, value=0)
                progress_file = ft.Text("", size=12, color=theme.get_text_secondary())
                
                dlg_progress = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("📥 Importando...", weight=ft.FontWeight.BOLD),
                    content=ft.Column([
                        progress_text,
                        ft.Container(height=10),
                        progress_bar,
                        progress_file,
                    ], tight=True, width=350),
                )
                page.overlay.append(dlg_progress)
                dlg_progress.open = True
                page.update()
                
                total_produtos = 0
                arquivos_importados = []
                erros = []
                pasta_planilhas = os.path.join(os.path.dirname(__file__), "..", "data", "planilhas")
                os.makedirs(pasta_planilhas, exist_ok=True)
                
                for i, arquivo in enumerate(r.files):
                    try:
                        arquivo_original = arquivo.path
                        nome_arquivo = os.path.basename(arquivo_original)
                        
                        progress_text.value = f"Importando {i+1} de {total_arquivos}..."
                        progress_bar.value = (i + 1) / total_arquivos
                        progress_file.value = nome_arquivo
                        page.update()
                        
                        arquivo_destino = os.path.join(pasta_planilhas, nome_arquivo)
                        shutil.copy2(arquivo_original, arquivo_destino)
                        arquivos_importados.append(arquivo_destino)
                        
                        ok, msg, qtd = importar_planilha_produtos(arquivo_destino, CANAIS, usuario_logado[0].get('username', 'admin'))
                        if ok:
                            total_produtos += (qtd.get('produtos_importados', 0) if isinstance(qtd, dict) else qtd) or 0
                        else:
                            erros.append(f"{nome_arquivo}: {msg}")
                    except Exception as ex:
                        erros.append(f"{arquivo.name}: {str(ex)}")
                
                dlg_progress.open = False
                page.update()
                
                if arquivos_importados:
                    nomes = " + ".join([os.path.basename(a) for a in arquivos_importados])
                    salvar_lista_preco("|".join(arquivos_importados), nomes, total_produtos, usuario=usuario_logado[0].get('username', 'admin'))
                
                def fechar_dlg(e):
                    dlg_conclusao.open = False
                    page.update()
                
                msg_erros = "\n".join(erros) if erros else ""
                dlg_conclusao = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("✅ Importação Concluída!", weight=ft.FontWeight.BOLD),
                    content=ft.Column([
                        ft.Text(f"Arquivos processados: {total_arquivos}", size=14),
                        ft.Text(f"Arquivos importados: {len(arquivos_importados)}", size=14),
                        ft.Text(f"Total de produtos: {total_produtos}", size=14, weight=ft.FontWeight.BOLD),
                        ft.Text("Lista de preço criada!", size=12, color="#22C55E") if arquivos_importados else ft.Container(),
                        ft.Container(height=10) if erros else ft.Container(),
                        ft.Text(f"Erros:\n{msg_erros}", size=12, color=ft.Colors.RED) if erros else ft.Container(),
                    ], tight=True),
                    actions=[ft.TextButton("OK", on_click=fechar_dlg)],
                )
                page.overlay.append(dlg_conclusao)
                dlg_conclusao.open = True
                carregar()
                page.update()
                
        file_picker.on_result = on_pick
        file_picker.pick_files(allowed_extensions=["xlsx", "xls"], allow_multiple=True)
    
    # ══════════════════════════════════════════════════════════════
    # FUNÇÕES PARA MARCAR P.OMNIE E P.ANY EM MASSA
    # ══════════════════════════════════════════════════════════════
    # ══════════════════════════════════════════════════════════════
    # FUNÇÕES PARA MARCAR P.OMNIE E P.ANY EM MASSA (OTIMIZADO)
    # ══════════════════════════════════════════════════════════════
    def marcar_omnie_selecionados(e):
        """Marca P.Omnie para todos os produtos selecionados."""
        if not linhas_selecionadas:
            page.snack_bar = ft.SnackBar(ft.Text("Selecione pelo menos um produto!"), bgcolor="#EF4444")
            page.snack_bar.open = True
            page.update()
            return
        
        # Coletar IDs
        ids_para_atualizar = []
        for idx in linhas_selecionadas:
            if idx < len(todos_dados_linhas):
                # O ID pode estar como 'produto_id' ou 'id' dependendo da query original
                prod = todos_dados_linhas[idx]
                pid = prod.get('id') or prod.get('produto_id')
                if pid:
                    ids_para_atualizar.append(pid)
        
        if not ids_para_atualizar:
            return

        # Update no banco em batch
        from services.database_sinc import marcar_importacao_externa_em_massa
        total = marcar_importacao_externa_em_massa(ids_para_atualizar, 'omnie', True)
        
        # Update Visual instantâneo (sem recarregar)
        for i, linha in enumerate(linhas_container.controls):
            if i in linhas_selecionadas:
                try:
                    # Índice 7 = Coluna P.Omnie
                    linha.content.controls[7].content.value = True
                except: pass
        
        page.snack_bar = ft.SnackBar(ft.Text(f"✅ P.Omnie marcado para {len(ids_para_atualizar)} produtos! (Afetou {total} registros)"), bgcolor="#22C55E")
        page.snack_bar.open = True
        page.update()
    
    def marcar_any_selecionados(e):
        """Marca P.Any para todos os produtos selecionados."""
        if not linhas_selecionadas:
            page.snack_bar = ft.SnackBar(ft.Text("Selecione pelo menos um produto!"), bgcolor="#EF4444")
            page.snack_bar.open = True
            page.update()
            return
        
        # Coletar IDs
        ids_para_atualizar = []
        for idx in linhas_selecionadas:
            if idx < len(todos_dados_linhas):
                prod = todos_dados_linhas[idx]
                pid = prod.get('id') or prod.get('produto_id')
                if pid:
                    ids_para_atualizar.append(pid)
        
        if not ids_para_atualizar:
            return

        # Update no banco em batch
        from services.database_sinc import marcar_importacao_externa_em_massa
        total = marcar_importacao_externa_em_massa(ids_para_atualizar, 'anymarket', True)
        
        # Update Visual instantâneo (sem recarregar)
        for i, linha in enumerate(linhas_container.controls):
            if i in linhas_selecionadas:
                try:
                    # Índice 8 = Coluna P.Any
                    linha.content.controls[8].content.value = True
                except: pass
        
        page.snack_bar = ft.SnackBar(ft.Text(f"✅ P.Any marcado para {len(ids_para_atualizar)} produtos! (Afetou {total} registros)"), bgcolor="#22C55E")
        page.snack_bar.open = True
        page.update()
    
    # Auto-refresh controlado globalmente
    def auto_refresh():
        if is_auto_refresh_enabled():
            try:
                carregar()
            except:
                pass
        # Reagendar (sempre reagenda para verificar estado global)
        interval = get_refresh_interval()
        _refresh_timer[0] = threading.Timer(float(interval), auto_refresh)
        _refresh_timer[0].daemon = True
        _refresh_timer[0].start()
    
    carregar()
    
    # Inicia auto-refresh
    interval = get_refresh_interval()
    _refresh_timer[0] = threading.Timer(float(interval), auto_refresh)
    _refresh_timer[0].daemon = True
    _refresh_timer[0].start()
    
    legenda = ft.Row([
        ft.Container(width=10, height=10, bgcolor="#22C55E", border_radius=5),
        ft.Text("Ativo", size=10),
        ft.Container(width=10, height=10, bgcolor="#000000", border_radius=5),
        ft.Text("Blocklist", size=10),
        ft.Icon(ft.Icons.EDIT, size=12, color=ft.Colors.ORANGE),
        ft.Text("Catalogando", size=10),
        ft.Icon(ft.Icons.CLOSE, size=12, color=ft.Colors.RED),
        ft.Text("Erro", size=10),
        ft.Container(width=10, height=10, bgcolor="#E0E0E0", border_radius=5),
        ft.Text("Pendente", size=10),
    ], spacing=5)
    
    return ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Column([
                        ft.Text("Sincronização", size=28, weight=ft.FontWeight.BOLD, color=theme.get_text_color()),
                        ft.Text("Gerencie SKUs em todos os canais", size=12, color=theme.get_text_secondary()),
                    ], spacing=2),
                    ft.Container(expand=True),
                    contador_selecao,
                    legenda,
                ], spacing=20),
                ft.Container(height=15),
                ft.Row([
                    filtro_sku, filtro_data, filtro_status,
                    ft.Container(expand=True),
                    # Botões para marcar P.Omnie e P.Any em massa
                    ft.ElevatedButton("P.Omnie", icon=ft.Icons.CHECK_CIRCLE, 
                                     bgcolor="#6366F1", color="#FFFFFF", on_click=marcar_omnie_selecionados,
                                     tooltip="Marcar P.Omnie para selecionados"),
                    ft.ElevatedButton("P.Any", icon=ft.Icons.CHECK_CIRCLE, 
                                     bgcolor="#8B5CF6", color="#FFFFFF", on_click=marcar_any_selecionados,
                                     tooltip="Marcar P.Any para selecionados"),
                    ft.ElevatedButton("Exportar", icon=ft.Icons.DOWNLOAD, 
                                     bgcolor="#22C55E", color="#FFFFFF", on_click=exportar),
                    ft.ElevatedButton("Importar", icon=ft.Icons.UPLOAD_FILE, 
                                     bgcolor="#333333" if theme.is_dark[0] else "#000000", color="#FFFFFF", on_click=importar),
                ], spacing=10),
            ]),
            padding=ft.padding.only(left=30, right=30, top=25, bottom=15),
            bgcolor=ft.Colors.TRANSPARENT,
        ),
        ft.Container(
            content=ft.Column([
                # Cabeçalho fixo
                tabela_header,
                # Corpo com scroll
                ft.Container(
                    content=linhas_container,
                    expand=True,
                ),
            ], spacing=0),
            expand=True,
            bgcolor=theme.get_card_bg(),
            margin=ft.margin.only(left=20, right=20, bottom=20),
            border_radius=12,
            padding=10,
        ),
    ], spacing=0, expand=True)
