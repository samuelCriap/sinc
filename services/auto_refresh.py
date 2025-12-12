"""
Estado Global de Auto-Refresh
Controla o auto-refresh de todas as telas do app
"""

# Estado global
_auto_refresh_enabled = [True]  # Lista para permitir mutação
_refresh_interval = [15]  # Intervalo em segundos


def is_auto_refresh_enabled() -> bool:
    """Retorna se o auto-refresh está habilitado."""
    return _auto_refresh_enabled[0]


def set_auto_refresh_enabled(enabled: bool) -> None:
    """Define se o auto-refresh está habilitado."""
    _auto_refresh_enabled[0] = enabled
    print(f"[AutoRefresh] {'Habilitado' if enabled else 'Desabilitado'}")


def get_refresh_interval() -> int:
    """Retorna o intervalo de refresh em segundos."""
    return _refresh_interval[0]


def set_refresh_interval(seconds: int) -> None:
    """Define o intervalo de refresh em segundos."""
    _refresh_interval[0] = max(5, min(120, seconds))  # Limitar entre 5 e 120 segundos
