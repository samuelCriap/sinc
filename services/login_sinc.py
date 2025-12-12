"""
Tela de Login do Sistema de Sincronização de SKUs
Baseado no login.py de referência
"""
import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, Optional


class LoginSincApp(ctk.CTk):
    def __init__(self, on_success_callback: Optional[Callable[[str], None]] = None):
        super().__init__()
        self.on_success_callback = on_success_callback

        # Login sempre claro
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title("Login - Sistema de Sincronização de SKUs")
        self.geometry("400x500")
        self.resizable(False, False)
        
        # Centraliza a janela
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - 200
        y = (self.winfo_screenheight() // 2) - 250
        self.geometry(f"400x500+{x}+{y}")
        
        self.mostrar_tela_login()

    def mostrar_tela_login(self):
        """Exibe a tela de login"""
        for w in self.winfo_children():
            w.destroy()

        # Fundo principal claro
        frame = ctk.CTkFrame(self, fg_color="#f7f7f7")
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Header com ícone
        ctk.CTkLabel(
            frame,
            text="🔄",
            font=("Segoe UI", 60)
        ).pack(pady=(30, 10))

        # Título
        ctk.CTkLabel(
            frame,
            text="Sincronização de SKUs",
            font=("Segoe UI", 24, "bold"),
            text_color="black"
        ).pack(pady=(0, 5))
        
        ctk.CTkLabel(
            frame,
            text="Multi-Canal",
            font=("Segoe UI", 14),
            text_color="#666666"
        ).pack(pady=(0, 30))

        # Campo usuário
        ctk.CTkLabel(frame, text="Usuário", text_color="black", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=30)
        self.usuario = ctk.CTkEntry(frame, height=40, font=("Segoe UI", 13), corner_radius=10)
        self.usuario.pack(pady=(5, 15), padx=30, fill="x")

        # Campo senha
        ctk.CTkLabel(frame, text="Senha", text_color="black", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=30)
        self.senha = ctk.CTkEntry(frame, show="●", height=40, font=("Segoe UI", 13), corner_radius=10)
        self.senha.pack(pady=(5, 10), padx=30, fill="x")

        # Bind Enter para login
        self.usuario.bind("<Return>", lambda e: self.senha.focus())
        self.senha.bind("<Return>", lambda e: self.validar())

        # Mensagem retorno
        self.msg = ctk.CTkLabel(frame, text="", text_color="black", font=("Segoe UI", 11))
        self.msg.pack(pady=15)

        # Botão entrar
        ctk.CTkButton(
            frame, 
            text="Entrar", 
            command=self.validar,
            height=45,
            font=("Segoe UI", 14, "bold"),
            fg_color="#3B82F6",
            hover_color="#2563EB",
            corner_radius=10
        ).pack(pady=(5, 15), padx=30, fill="x")
        
        # Rodapé
        ctk.CTkLabel(
            frame,
            text="Sistema de Sincronização v1.0",
            font=("Segoe UI", 10),
            text_color="#999999"
        ).pack(side="bottom", pady=10)

        self.usuario.focus()

    def validar(self):
        """Valida credenciais do usuário"""
        user = self.usuario.get().strip()
        pwd = self.senha.get()

        if not user or not pwd:
            self.msg.configure(text="❌ Preencha todos os campos!", text_color="red")
            return

        self.msg.configure(text="Verificando...", text_color="#3B82F6")
        self.update()

        try:
            from services.database_sinc import verificar_usuario
            sucesso, mensagem, dados = verificar_usuario(user, pwd)
            
            if sucesso:
                self.msg.configure(text="✅ " + mensagem, text_color="green")
                self.after(800, lambda: self._entrar(user))
            else:
                self.msg.configure(text="❌ " + mensagem, text_color="red")
                
        except Exception as e:
            self.msg.configure(text=f"❌ Erro: {str(e)}", text_color="red")

    def _entrar(self, username):
        """Fecha login e abre sistema"""
        self.destroy()
        if self.on_success_callback:
            self.on_success_callback(username)


if __name__ == "__main__":
    app = LoginSincApp(on_success_callback=lambda u: print(f"Login: {u}"))
    app.mainloop()
