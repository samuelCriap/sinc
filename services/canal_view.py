"""
Tela de Visualização e Gerenciamento de Produtos por Canal
Status: ATIVO, CATALOGANDO, ERRO
Com edição por duplo-clique e exclusão de produtos
"""
import customtkinter as ctk
from tkinter import ttk, messagebox, simpledialog
from typing import Callable, Optional

# Design System
CORES = {
    "accent": "#3B82F6",
    "accent_hover": "#2563EB",
    "success": "#10B981",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "purple": "#8B5CF6",
    "surface_light": "#FFFFFF",
    "surface_dark": "#1E293B",
    "text_secondary": ("#64748B", "#94A3B8"),
}

# Novos status
STATUS_CORES = {
    "ATIVO": "#10B981",
    "CATALOGANDO": "#F59E0B",
    "ERRO": "#EF4444",
}


def abrir_canal_view(frame, canal: str, usuario: str = None, voltar_callback: Callable = None):
    """Tela de gerenciamento de produtos de um canal específico"""
    
    # Limpa a tela
    for w in frame.winfo_children():
        w.destroy()

    # Container principal
    main_container = ctk.CTkFrame(frame, fg_color="transparent")
    main_container.pack(fill="both", expand=True, padx=20, pady=15)

    # === HEADER ===
    header = ctk.CTkFrame(main_container, fg_color="transparent")
    header.pack(fill="x", pady=(0, 15))
    
    if voltar_callback:
        ctk.CTkButton(
            header,
            text="← Voltar",
            font=("Segoe UI", 12),
            fg_color="transparent",
            text_color=CORES["accent"],
            hover_color=("#E3F2FD", "#1E3A5F"),
            width=80,
            height=35,
            command=voltar_callback
        ).pack(side="left")
    
    ctk.CTkLabel(
        header,
        text=f"📦 {canal}",
        font=("Segoe UI", 24, "bold"),
        anchor="w"
    ).pack(side="left", padx=20)

    # === FILTROS ===
    filtros_frame = ctk.CTkFrame(
        main_container,
        fg_color=(CORES["surface_light"], CORES["surface_dark"]),
        corner_radius=10
    )
    filtros_frame.pack(fill="x", pady=(0, 10))
    
    filtros_inner = ctk.CTkFrame(filtros_frame, fg_color="transparent")
    filtros_inner.pack(fill="x", padx=15, pady=10)
    
    ctk.CTkLabel(filtros_inner, text="Buscar:", font=("Segoe UI", 11)).pack(side="left")
    
    busca_var = ctk.StringVar()
    entry_busca = ctk.CTkEntry(
        filtros_inner,
        textvariable=busca_var,
        width=250,
        height=32,
        placeholder_text="Código, SKU ou descrição..."
    )
    entry_busca.pack(side="left", padx=(5, 20))
    
    ctk.CTkLabel(filtros_inner, text="Status:", font=("Segoe UI", 11)).pack(side="left")
    
    status_var = ctk.StringVar(value="TODOS")
    combo_status = ctk.CTkComboBox(
        filtros_inner,
        values=["TODOS", "SEM STATUS", "ATIVO", "CATALOGANDO", "ERRO"],
        variable=status_var,
        width=140,
        height=32
    )
    combo_status.pack(side="left", padx=5)
    
    dados_produtos = []
    
    def carregar_dados():
        nonlocal dados_produtos
        try:
            from services.database_sinc import listar_produtos_canal
            filtro = status_var.get()
            if filtro == "TODOS":
                status_filtro = None
            elif filtro == "SEM STATUS":
                status_filtro = ""  # Status vazio
            else:
                status_filtro = filtro
            dados_produtos = listar_produtos_canal(canal, status=status_filtro)
        except Exception as e:
            dados_produtos = []
            print(f"Erro ao carregar: {e}")
        
        atualizar_tabela()
    
    def atualizar_tabela():
        for item in tree.get_children():
            tree.delete(item)
        
        busca = busca_var.get().lower()
        
        for prod in dados_produtos:
            if busca:
                texto = f"{prod.get('codigo_produto', '')} {prod.get('sku', '')} {prod.get('descricao', '')}".lower()
                if busca not in texto:
                    continue
            
            status = prod.get('status', '') or ''  # Pode ser vazio
            motivo_erro = prod.get('motivo_bloqueio', '') or ''
            
            # Exibe '-' se não tiver status
            status_display = status if status else '-'
            tag = status if status else "SEM_STATUS"
            
            tree.insert("", "end", values=(
                prod.get('codigo_produto', ''),
                prod.get('sku', ''),
                prod.get('descricao', '')[:60] if prod.get('descricao') else '',
                prod.get('marca', ''),
                status_display,
                motivo_erro[:40] if motivo_erro else '-'
            ), tags=(tag,))
        
        lbl_contador.configure(text=f"{len(tree.get_children())} produtos")
    
    ctk.CTkButton(
        filtros_inner,
        text="🔍 Filtrar",
        font=("Segoe UI", 11, "bold"),
        fg_color=CORES["accent"],
        hover_color=CORES["accent_hover"],
        width=100,
        height=32,
        command=carregar_dados
    ).pack(side="left", padx=10)
    
    entry_busca.bind("<Return>", lambda e: atualizar_tabela())

    # === AÇÕES ===
    acoes_frame = ctk.CTkFrame(main_container, fg_color="transparent")
    acoes_frame.pack(fill="x", pady=(0, 10))
    
    def marcar_como_ativo():
        selecionados = tree.selection()
        if not selecionados:
            messagebox.showwarning("Aviso", "Selecione produtos para marcar como ATIVO")
            return
        
        from services.database_sinc import atualizar_status_produto_canal, buscar_produto_por_codigo
        
        count = 0
        for item in selecionados:
            valores = tree.item(item, "values")
            codigo = valores[0]
            produto = buscar_produto_por_codigo(codigo)
            if produto:
                atualizar_status_produto_canal(produto['id'], canal, "ATIVO", usuario)
                count += 1
        
        messagebox.showinfo("✅ Sucesso", f"{count} produto(s) marcado(s) como ATIVO!")
        carregar_dados()
    
    def marcar_como_catalogando():
        selecionados = tree.selection()
        if not selecionados:
            messagebox.showwarning("Aviso", "Selecione produtos para marcar como CATALOGANDO")
            return
        
        from services.database_sinc import atualizar_status_produto_canal, buscar_produto_por_codigo
        
        count = 0
        for item in selecionados:
            valores = tree.item(item, "values")
            codigo = valores[0]
            produto = buscar_produto_por_codigo(codigo)
            if produto:
                atualizar_status_produto_canal(produto['id'], canal, "CATALOGANDO", usuario)
                count += 1
        
        messagebox.showinfo("✅ Sucesso", f"{count} produto(s) marcado(s) como CATALOGANDO!")
        carregar_dados()
    
    def marcar_como_erro():
        selecionados = tree.selection()
        if not selecionados:
            messagebox.showwarning("Aviso", "Selecione produtos para marcar como ERRO")
            return
        
        # Abre janela para informar o erro
        janela_erro = ctk.CTkToplevel()
        janela_erro.title("❌ Informar Erro")
        janela_erro.geometry("500x300")
        janela_erro.resizable(False, False)
        janela_erro.grab_set()
        
        janela_erro.update_idletasks()
        x = (janela_erro.winfo_screenwidth() // 2) - 250
        y = (janela_erro.winfo_screenheight() // 2) - 150
        janela_erro.geometry(f"500x300+{x}+{y}")
        
        # Força foco
        janela_erro.lift()
        janela_erro.focus_force()
        
        container = ctk.CTkFrame(janela_erro, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=25, pady=20)
        
        ctk.CTkLabel(
            container,
            text="❌ Informar Erro",
            font=("Segoe UI", 20, "bold")
        ).pack(pady=(0, 15))
        
        ctk.CTkLabel(
            container,
            text=f"Produtos selecionados: {len(selecionados)}",
            font=("Segoe UI", 12),
            text_color=CORES["text_secondary"]
        ).pack()
        
        ctk.CTkLabel(
            container,
            text="Descreva o erro:",
            font=("Segoe UI", 13, "bold")
        ).pack(anchor="w", pady=(15, 5))
        
        erro_textbox = ctk.CTkTextbox(container, height=100, font=("Segoe UI", 12))
        erro_textbox.pack(fill="x", pady=(0, 20))
        erro_textbox.focus()
        
        def confirmar_erro():
            descricao_erro = erro_textbox.get("1.0", "end").strip()
            if not descricao_erro:
                messagebox.showwarning("Aviso", "Por favor, descreva o erro")
                return
            
            from services.database_sinc import atualizar_status_produto_canal_com_erro, buscar_produto_por_codigo
            
            count = 0
            for item in selecionados:
                valores = tree.item(item, "values")
                codigo = valores[0]
                produto = buscar_produto_por_codigo(codigo)
                if produto:
                    atualizar_status_produto_canal_com_erro(produto['id'], canal, "ERRO", descricao_erro, usuario)
                    count += 1
            
            janela_erro.destroy()
            messagebox.showinfo("✅ Sucesso", f"{count} produto(s) marcado(s) como ERRO!")
            carregar_dados()
        
        # Frame de botões
        btns_frame = ctk.CTkFrame(container, fg_color="transparent")
        btns_frame.pack(fill="x", pady=(5, 0))
        
        ctk.CTkButton(
            btns_frame,
            text="Cancelar",
            fg_color="gray",
            hover_color="#555555",
            width=120,
            height=40,
            font=("Segoe UI", 12, "bold"),
            command=janela_erro.destroy
        ).pack(side="left")
        
        ctk.CTkButton(
            btns_frame,
            text="✅ Salvar Erro",
            fg_color=CORES["danger"],
            hover_color="#DC2626",
            width=160,
            height=40,
            font=("Segoe UI", 12, "bold"),
            command=confirmar_erro
        ).pack(side="right")
    
    def excluir_produtos():
        """Remove produtos selecionados do canal"""
        selecionados = tree.selection()
        if not selecionados:
            messagebox.showwarning("Aviso", "Selecione produtos para excluir")
            return
        
        if not messagebox.askyesno("Confirmar", f"Deseja excluir {len(selecionados)} produto(s) deste canal?"):
            return
        
        from services.database_sinc import remover_produto_canal, buscar_produto_por_codigo
        
        count = 0
        for item in selecionados:
            valores = tree.item(item, "values")
            codigo = valores[0]
            produto = buscar_produto_por_codigo(codigo)
            if produto:
                remover_produto_canal(produto['id'], canal)
                count += 1
        
        messagebox.showinfo("✅ Sucesso", f"{count} produto(s) removido(s) do canal!")
        carregar_dados()
    
    def editar_celula(event):
        """Permite editar célula com duplo-clique"""
        item = tree.identify_row(event.y)
        coluna = tree.identify_column(event.x)
        
        if not item or not coluna:
            return
        
        col_idx = int(coluna.replace('#', '')) - 1
        colunas_editaveis = {0: 'codigo_produto', 1: 'sku', 2: 'descricao', 3: 'marca'}
        
        if col_idx not in colunas_editaveis:
            return
        
        valores = tree.item(item, "values")
        valor_atual = valores[col_idx]
        
        # Janela de edição
        janela_edicao = ctk.CTkToplevel()
        janela_edicao.title("Editar Campo")
        janela_edicao.geometry("400x150")
        janela_edicao.resizable(False, False)
        janela_edicao.grab_set()
        
        janela_edicao.update_idletasks()
        x = (janela_edicao.winfo_screenwidth() // 2) - 200
        y = (janela_edicao.winfo_screenheight() // 2) - 75
        janela_edicao.geometry(f"400x150+{x}+{y}")
        
        container = ctk.CTkFrame(janela_edicao, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=15)
        
        nomes_colunas = ["Código", "SKU", "Descrição", "Marca"]
        
        ctk.CTkLabel(
            container,
            text=f"Editar {nomes_colunas[col_idx]}:",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w")
        
        entry_edicao = ctk.CTkEntry(container, height=35, font=("Segoe UI", 12))
        entry_edicao.pack(fill="x", pady=10)
        entry_edicao.insert(0, valor_atual)
        entry_edicao.focus()
        entry_edicao.select_range(0, 'end')
        
        def salvar_edicao():
            novo_valor = entry_edicao.get().strip()
            if not novo_valor:
                messagebox.showwarning("Aviso", "O campo não pode estar vazio")
                return
            
            from services.database_sinc import atualizar_produto_campo, buscar_produto_por_codigo
            
            codigo = valores[0]
            campo_db = colunas_editaveis[col_idx]
            produto = buscar_produto_por_codigo(codigo)
            
            if produto:
                atualizar_produto_campo(produto['id'], campo_db, novo_valor)
                janela_edicao.destroy()
                carregar_dados()
        
        entry_edicao.bind("<Return>", lambda e: salvar_edicao())
        
        btns = ctk.CTkFrame(container, fg_color="transparent")
        btns.pack(fill="x", pady=(5, 0))
        
        ctk.CTkButton(btns, text="Cancelar", fg_color="gray", width=80, command=janela_edicao.destroy).pack(side="left")
        ctk.CTkButton(btns, text="Salvar", fg_color=CORES["success"], width=80, command=salvar_edicao).pack(side="right")
    
    # Botões de ação
    ctk.CTkButton(
        acoes_frame,
        text="✅ Ativo",
        font=("Segoe UI", 12, "bold"),
        fg_color=CORES["success"],
        hover_color="#059669",
        height=38,
        width=100,
        command=marcar_como_ativo
    ).pack(side="left", padx=(0, 8))
    
    ctk.CTkButton(
        acoes_frame,
        text="📝 Catalogando",
        font=("Segoe UI", 12, "bold"),
        fg_color=CORES["warning"],
        hover_color="#D97706",
        height=38,
        width=130,
        command=marcar_como_catalogando
    ).pack(side="left", padx=(0, 8))
    
    ctk.CTkButton(
        acoes_frame,
        text="❌ Erro",
        font=("Segoe UI", 12, "bold"),
        fg_color=CORES["danger"],
        hover_color="#DC2626",
        height=38,
        width=80,
        command=marcar_como_erro
    ).pack(side="left", padx=(0, 8))
    
    ctk.CTkButton(
        acoes_frame,
        text="🗑️ Excluir",
        font=("Segoe UI", 12, "bold"),
        fg_color="#6B7280",
        hover_color="#4B5563",
        height=38,
        width=100,
        command=excluir_produtos
    ).pack(side="left", padx=(0, 8))
    
    # Contador
    lbl_contador = ctk.CTkLabel(
        acoes_frame,
        text="0 produtos",
        font=("Segoe UI", 12),
        text_color=CORES["text_secondary"]
    )
    lbl_contador.pack(side="right")

    # === TABELA COM FONTE MAIOR ===
    tabela_frame = ctk.CTkFrame(
        main_container,
        fg_color=(CORES["surface_light"], CORES["surface_dark"]),
        corner_radius=10
    )
    tabela_frame.pack(fill="both", expand=True)
    
    # Estilo com fonte MAIOR
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Canal.Treeview", 
                    background="#FFFFFF",
                    foreground="#1E293B",
                    fieldbackground="#FFFFFF",
                    rowheight=38,
                    font=("Segoe UI", 12))  # Fonte maior
    style.configure("Canal.Treeview.Heading",
                    background="#F1F5F9",
                    foreground="#1E293B",
                    font=("Segoe UI", 13, "bold"))  # Cabeçalho maior
    style.map("Canal.Treeview", background=[("selected", "#3B82F6")])
    
    colunas = ("codigo", "sku", "descricao", "marca", "status", "erro")
    
    tree = ttk.Treeview(
        tabela_frame,
        columns=colunas,
        show="headings",
        selectmode="extended",
        style="Canal.Treeview"
    )
    
    tree.heading("codigo", text="Código")
    tree.heading("sku", text="SKU")
    tree.heading("descricao", text="Descrição")
    tree.heading("marca", text="Marca")
    tree.heading("status", text="Status")
    tree.heading("erro", text="Motivo Erro")
    
    tree.column("codigo", width=130)
    tree.column("sku", width=130)
    tree.column("descricao", width=350)
    tree.column("marca", width=120)
    tree.column("status", width=110)
    tree.column("erro", width=200)
    
    # Tags de cores
    tree.tag_configure("SEM_STATUS", foreground="#1E293B")  # Preto - sem status
    tree.tag_configure("ATIVO", foreground="#10B981")  # Verde
    tree.tag_configure("CATALOGANDO", foreground="#F59E0B")  # Laranja
    tree.tag_configure("ERRO", foreground="#EF4444")  # Vermelho
    
    # Bind duplo-clique para editar
    tree.bind("<Double-1>", editar_celula)
    
    scrollbar = ttk.Scrollbar(tabela_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    
    tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
    scrollbar.pack(side="right", fill="y", pady=5)
    
    carregar_dados()
