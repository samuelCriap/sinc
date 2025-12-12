"""
Tela Início do Sistema de Sincronização - Tabela SINC
"""
import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
from typing import Callable

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

# Abreviações para colunas
ABREV_CANAIS = {
    "NETSHOES": "NT", "CENTAURO": "CT", "TIKTOK": "TK", "SHEIN": "SN",
    "RENNER": "RN", "SHOPEE": "SP", "MELI": "ML", "DAFITI": "DF", "AMAZON": "AZ",
}


def abrir_tela_inicio(frame, usuario: str = None, abrir_canal_callback: Callable = None):
    """Tela inicial com tabela SINC"""
    from services.database_sinc import CANAIS, listar_produtos, get_connection
    
    for w in frame.winfo_children():
        w.destroy()

    main_container = ctk.CTkFrame(frame, fg_color="transparent")
    main_container.pack(fill="both", expand=True, padx=20, pady=15)

    # === HEADER ===
    header = ctk.CTkFrame(main_container, fg_color="transparent")
    header.pack(fill="x", pady=(0, 15))
    
    ctk.CTkLabel(header, text="🔄 Sincronização de SKUs", font=("Segoe UI", 24, "bold"), anchor="w").pack(side="left")
    
    def importar_planilha():
        from services.importador import importar_planilha_produtos
        
        arquivo = filedialog.askopenfilename(
            title="Selecionar Planilha",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        
        if arquivo:
            loading = ctk.CTkToplevel()
            loading.title("Importando...")
            loading.geometry("300x100")
            loading.resizable(False, False)
            loading.grab_set()
            ctk.CTkLabel(loading, text="⏳ Importando...", font=("Segoe UI", 12)).pack(expand=True)
            loading.update()
            
            try:
                sucesso, msg, stats = importar_planilha_produtos(arquivo, CANAIS, usuario)
                loading.destroy()
                if sucesso:
                    messagebox.showinfo("✅ Sucesso", msg)
                    carregar_sinc()
                else:
                    messagebox.showerror("❌ Erro", msg)
            except Exception as e:
                loading.destroy()
                messagebox.showerror("Erro", str(e))
    
    ctk.CTkButton(header, text="📥 Importar Planilha", font=("Segoe UI", 12, "bold"),
                  fg_color=CORES["accent"], height=40, command=importar_planilha).pack(side="right")

    # === TABELA SINC ===
    ctk.CTkLabel(main_container, text="📊 Tabela SINC - Status por Canal", font=("Segoe UI", 16, "bold"), anchor="w").pack(fill="x", pady=(10, 8))
    
    tabela_frame = ctk.CTkFrame(main_container, fg_color=(CORES["surface_light"], CORES["surface_dark"]), corner_radius=10)
    tabela_frame.pack(fill="both", expand=True)
    
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Sinc.Treeview", background="#FFFFFF", foreground="#1E293B",
                    fieldbackground="#FFFFFF", rowheight=28, font=("Segoe UI", 10))
    style.configure("Sinc.Treeview.Heading", background="#F1F5F9", foreground="#1E293B", font=("Segoe UI", 9, "bold"))
    style.map("Sinc.Treeview", background=[("selected", "#3B82F6")])
    
    # Colunas: SKU, Nome, Marca, Omnie, AnyM, + cada canal
    colunas = ["sku", "nome", "marca", "omnie", "anym"] + [ABREV_CANAIS[c] for c in CANAIS]
    
    tree = ttk.Treeview(tabela_frame, columns=colunas, show="headings", selectmode="extended", style="Sinc.Treeview")
    
    tree.heading("sku", text="SKU")
    tree.heading("nome", text="Nome")
    tree.heading("marca", text="Marca")
    tree.heading("omnie", text="📦 One")
    tree.heading("anym", text="🛒 Any")
    
    tree.column("sku", width=110)
    tree.column("nome", width=220)
    tree.column("marca", width=80)
    tree.column("omnie", width=50, anchor="center")
    tree.column("anym", width=50, anchor="center")
    
    for canal in CANAIS:
        abrev = ABREV_CANAIS[canal]
        tree.heading(abrev, text=abrev)
        tree.column(abrev, width=42, anchor="center")
    
    scrollbar_tree = ttk.Scrollbar(tabela_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar_tree.set)
    
    tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
    scrollbar_tree.pack(side="right", fill="y", pady=5)
    
    def carregar_sinc():
        for item in tree.get_children():
            tree.delete(item)
        
        produtos = listar_produtos(limite=500)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        for prod in produtos:
            cursor.execute("""
                SELECT canal, status, importado_omnie, importado_anymarket 
                FROM produto_canal WHERE produto_id = ?
            """, (prod['id'],))
            canais_data = {row['canal']: row for row in cursor.fetchall()}
            
            omnie = "✅" if any(c.get('importado_omnie') for c in canais_data.values()) else "⬜"
            anym = "✅" if any(c.get('importado_anymarket') for c in canais_data.values()) else "⬜"
            
            valores = [
                prod.get('codigo_produto', ''),
                (prod.get('descricao', '') or '')[:35],
                prod.get('marca', '') or '',
                omnie,
                anym
            ]
            
            for canal in CANAIS:
                if canal in canais_data:
                    status = canais_data[canal].get('status', '') or ''
                    if status == 'ATIVO':
                        valores.append("✅")
                    elif status == 'ERRO':
                        valores.append("❌")
                    elif status == 'CATALOGANDO':
                        valores.append("📝")
                    else:
                        valores.append("-")
                else:
                    valores.append("")
            
            tree.insert("", "end", values=valores, iid=str(prod['id']))
        
        conn.close()
    
    def toggle_checkbox(event):
        item = tree.identify_row(event.y)
        coluna = tree.identify_column(event.x)
        if not item or not coluna:
            return
        col_idx = int(coluna.replace('#', '')) - 1
        
        if col_idx == 3:  # Omnie
            from services.database_sinc import atualizar_importacao_externa
            produto_id = int(item)
            valores = tree.item(item, "values")
            atual = valores[3] == "✅"
            for canal in CANAIS:
                atualizar_importacao_externa(produto_id, canal, omnie=not atual)
            carregar_sinc()
        elif col_idx == 4:  # AnyMarket
            from services.database_sinc import atualizar_importacao_externa
            produto_id = int(item)
            valores = tree.item(item, "values")
            atual = valores[4] == "✅"
            for canal in CANAIS:
                atualizar_importacao_externa(produto_id, canal, anymarket=not atual)
            carregar_sinc()
    
    tree.bind("<Button-1>", toggle_checkbox)
    
    carregar_sinc()
