"""
Sistema de Notificações Toast
"""
import flet as ft
from enum import Enum
from typing import Optional


class ToastType(Enum):
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# Configuração de cores e ícones por tipo
TOAST_CONFIG = {
    ToastType.SUCCESS: {
        'bgcolor': '#22C55E',
        'icon': ft.Icons.CHECK_CIRCLE,
        'icon_color': '#FFFFFF',
    },
    ToastType.ERROR: {
        'bgcolor': '#EF4444',
        'icon': ft.Icons.ERROR,
        'icon_color': '#FFFFFF',
    },
    ToastType.WARNING: {
        'bgcolor': '#F59E0B',
        'icon': ft.Icons.WARNING,
        'icon_color': '#000000',
    },
    ToastType.INFO: {
        'bgcolor': '#0EA5E9',
        'icon': ft.Icons.INFO,
        'icon_color': '#FFFFFF',
    },
}


def show_toast(
    page: ft.Page, 
    message: str, 
    toast_type: ToastType = ToastType.INFO,
    duration_ms: int = 3000
) -> None:
    """
    Exibe notificação toast centralizada.
    
    Args:
        page: Página Flet
        message: Mensagem a exibir
        toast_type: Tipo de toast (SUCCESS, ERROR, WARNING, INFO)
        duration_ms: Duração em milissegundos (padrão: 3s)
    """
    config = TOAST_CONFIG[toast_type]
    
    page.snack_bar = ft.SnackBar(
        content=ft.Row([
            ft.Icon(config['icon'], color=config['icon_color'], size=20),
            ft.Text(message, color="#FFFFFF", size=13, weight=ft.FontWeight.W_500),
        ], spacing=10),
        bgcolor=config['bgcolor'],
        duration=duration_ms,
    )
    page.snack_bar.open = True
    page.update()


# Funções de conveniência
def toast_success(page: ft.Page, message: str, duration_ms: int = 3000) -> None:
    """Toast de sucesso."""
    show_toast(page, message, ToastType.SUCCESS, duration_ms)


def toast_error(page: ft.Page, message: str, duration_ms: int = 4000) -> None:
    """Toast de erro (dura mais)."""
    show_toast(page, message, ToastType.ERROR, duration_ms)


def toast_warning(page: ft.Page, message: str, duration_ms: int = 3500) -> None:
    """Toast de aviso."""
    show_toast(page, message, ToastType.WARNING, duration_ms)


def toast_info(page: ft.Page, message: str, duration_ms: int = 3000) -> None:
    """Toast de informação."""
    show_toast(page, message, ToastType.INFO, duration_ms)
