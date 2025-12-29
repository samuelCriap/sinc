"""
Changelog - Histórico de Atualizações do SINC
Contém todas as versões e suas novidades
"""
from typing import Dict, List
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════════
# HISTÓRICO DE VERSÕES
# ═══════════════════════════════════════════════════════════════════════════════

CHANGELOG: Dict[str, Dict] = {
    "1.1.2": {
        "data": "2025-12-29",
        "titulo": "🩹 Correção de Bugs (Hotfix)",
        "novidades": [
            "🐛 Correção de erro de compatibilidade com Flet (MaterialState)",
            "⚡ Melhoria na estabilidade da notificação",
        ],
        "cor": "#EF4444"
    },
    "1.1.1": {
        "data": "2025-12-29",
        "titulo": "📢 Notificação de Novidades",
        "novidades": [
            "🎉 Notificação 'What's New' no canto inferior direito após login",
            "⏱️ Auto-close após 5 segundos ou fechamento manual",
            "📖 Botão 'Ver mais' expande histórico completo de versões",
            "✨ Animação suave de slide lateral"
        ],
        "cor": "#8B5CF6"
    },
    "1.1.0": {
        "data": "2025-12-29",
        "titulo": "🚀 Sistema de Auto-Atualização",
        "novidades": [
            "✅ Verificação automática de atualizações via GitHub Releases",
            "📥 Download e instalação de novas versões com barra de progresso",
            "🔐 Suporte a repositório privado com token de acesso",
            "🎯 Diálogo intuitivo para atualizar ao fazer login"
        ],
        "cor": "#22C55E"
    },
    "1.0.0": {
        "data": "2025-12-15",
        "titulo": "🎉 Lançamento Inicial",
        "novidades": [
            "📦 Sistema completo de sincronização de SKUs",
            "👥 Gestão de usuários e permissões",
            "📊 Relatórios e análises",
            "🔄 Integração com canais de venda",
            "📋 Lista de preços e blocklist",
            "🤖 Automações personalizadas"
        ],
        "cor": "#3B82F6"
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════════

def get_latest_version() -> str:
    """Retorna a versão mais recente do changelog."""
    versions = sorted(CHANGELOG.keys(), reverse=True)
    return versions[0] if versions else "1.0.0"


def get_version_info(version: str) -> Dict:
    """
    Retorna informações sobre uma versão específica.
    
    Args:
        version: Versão no formato "X.Y.Z"
        
    Returns:
        Dicionário com informações da versão ou None
    """
    return CHANGELOG.get(version, None)


def get_recent_versions(count: int = 3) -> List[Dict]:
    """
    Retorna as N versões mais recentes com suas informações.
    
    Args:
        count: Quantidade de versões a retornar
        
    Returns:
        Lista de dicionários com versões e informações
    """
    versions = sorted(CHANGELOG.keys(), reverse=True)
    recent = versions[:count]
    
    return [
        {
            "version": v,
            **CHANGELOG[v]
        }
        for v in recent
    ]


def format_changelog_text(versions_count: int = 3) -> str:
    """
    Formata o changelog como texto para exibição.
    
    Args:
        versions_count: Quantas versões incluir
        
    Returns:
        String formatada com o changelog
    """
    versions = get_recent_versions(versions_count)
    
    lines = []
    for v_info in versions:
        lines.append(f"═══ Versão {v_info['version']} ({v_info['data']}) ═══")
        lines.append(v_info['titulo'])
        lines.append("")
        for item in v_info['novidades']:
            lines.append(f"  {item}")
        lines.append("")
    
    return "\n".join(lines)
