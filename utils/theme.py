"""
Utilitários de Tema - Funções compartilhadas para cores e estilos
"""
import flet as ft

# Constantes de cores por canal
COR_CANAL = {
    "NETSHOES": "#FF6600", "CENTAURO": "#E31937", "TIKTOK": "#000000", "SHEIN": "#000000",
    "RENNER": "#C8102E", "SHOPEE": "#EE4D2D",
    "MELI": "#FFE600", "DAFITI": "#1A1A1A", "AMAZON": "#FF9900",
}

# Abreviações dos canais
ABREV = {
    "NETSHOES": "NT", "CENTAURO": "CT", "TIKTOK": "TK", "SHEIN": "SN",
    "RENNER": "RN", "SHOPEE": "SP", "MELI": "ML", "DAFITI": "DF", "AMAZON": "AZ"
}


class ThemeManager:
    """Gerenciador de tema (claro/escuro)"""
    
    def __init__(self):
        self.is_dark = [False]  # Lista para permitir modificação em closures
    
    def toggle(self):
        """Alterna entre tema claro e escuro"""
        self.is_dark[0] = not self.is_dark[0]
    
    def get_bg(self):
        return "#1A1A1A" if self.is_dark[0] else "#F5F5F5"
    
    def get_card_bg(self):
        return "#2D2D2D" if self.is_dark[0] else "#FFFFFF"
    
    def get_text_color(self):
        return "#FFFFFF" if self.is_dark[0] else "#000000"
    
    def get_text_secondary(self):
        return "#888888" if self.is_dark[0] else "#666666"
    
    def get_border_color(self):
        return "#3D3D3D" if self.is_dark[0] else "#E5E5E5"
    
    def get_header_bg(self):
        return ft.Colors.with_opacity(0.03, "#FFFFFF") if self.is_dark[0] else ft.Colors.with_opacity(0.03, "#000000")
