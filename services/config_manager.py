"""
Gerenciador de Configurações do Usuário
Import/Export de preferências
"""
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime


# Arquivo de configurações
CONFIG_FILE = "data/user_config.json"


# Configuração padrão
DEFAULT_CONFIG = {
    'version': '1.0',
    'tema': 'light',
    'filtros_salvos': {},
    'colunas_visiveis': {},
    'ultimo_canal': None,
    'exportar_formato': 'xlsx',
    'created_at': None,
    'updated_at': None,
}


def get_config_path() -> str:
    """Retorna o caminho do arquivo de configuração."""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    return CONFIG_FILE


def carregar_config() -> Dict[str, Any]:
    """
    Carrega configurações do arquivo JSON.
    
    Returns:
        Dicionário de configurações
    """
    path = get_config_path()
    
    if not os.path.exists(path):
        config = DEFAULT_CONFIG.copy()
        config['created_at'] = datetime.now().isoformat()
        salvar_config(config)
        return config
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Mesclar com padrão para garantir todas as chaves
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value
        
        return config
        
    except Exception as e:
        print(f"[Config] Erro ao carregar: {e}")
        return DEFAULT_CONFIG.copy()


def salvar_config(config: Dict[str, Any]) -> bool:
    """
    Salva configurações no arquivo JSON.
    
    Args:
        config: Dicionário de configurações
        
    Returns:
        True se salvou com sucesso
    """
    try:
        config['updated_at'] = datetime.now().isoformat()
        
        path = get_config_path()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return True
        
    except Exception as e:
        print(f"[Config] Erro ao salvar: {e}")
        return False


def get_valor(chave: str, padrao: Any = None) -> Any:
    """
    Obtém um valor específico da configuração.
    
    Args:
        chave: Chave da configuração
        padrao: Valor padrão se não existir
        
    Returns:
        Valor da configuração
    """
    config = carregar_config()
    return config.get(chave, padrao)


def set_valor(chave: str, valor: Any) -> bool:
    """
    Define um valor na configuração.
    
    Args:
        chave: Chave da configuração
        valor: Valor a definir
        
    Returns:
        True se salvou com sucesso
    """
    config = carregar_config()
    config[chave] = valor
    return salvar_config(config)


def exportar_config(caminho_destino: str) -> bool:
    """
    Exporta configurações para um arquivo.
    
    Args:
        caminho_destino: Caminho do arquivo de destino
        
    Returns:
        True se exportou com sucesso
    """
    try:
        config = carregar_config()
        config['exported_at'] = datetime.now().isoformat()
        
        with open(caminho_destino, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"[Config] Exportado para: {caminho_destino}")
        return True
        
    except Exception as e:
        print(f"[Config] Erro ao exportar: {e}")
        return False


def importar_config(caminho_origem: str) -> bool:
    """
    Importa configurações de um arquivo.
    
    Args:
        caminho_origem: Caminho do arquivo fonte
        
    Returns:
        True se importou com sucesso
    """
    try:
        with open(caminho_origem, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Validar versão
        if 'version' not in config:
            print("[Config] Arquivo inválido: sem versão")
            return False
        
        config['imported_at'] = datetime.now().isoformat()
        salvar_config(config)
        
        print(f"[Config] Importado de: {caminho_origem}")
        return True
        
    except Exception as e:
        print(f"[Config] Erro ao importar: {e}")
        return False


# ═══════════════════════════════════════════════════════════════
# FILTROS SALVOS
# ═══════════════════════════════════════════════════════════════

def salvar_filtro(nome: str, canal: str, filtro: Dict) -> bool:
    """Salva um filtro personalizado."""
    config = carregar_config()
    
    if 'filtros_salvos' not in config:
        config['filtros_salvos'] = {}
    
    if canal not in config['filtros_salvos']:
        config['filtros_salvos'][canal] = {}
    
    config['filtros_salvos'][canal][nome] = {
        'filtro': filtro,
        'created_at': datetime.now().isoformat(),
    }
    
    return salvar_config(config)


def listar_filtros(canal: str) -> Dict:
    """Lista filtros salvos para um canal."""
    config = carregar_config()
    return config.get('filtros_salvos', {}).get(canal, {})


def remover_filtro(nome: str, canal: str) -> bool:
    """Remove um filtro salvo."""
    config = carregar_config()
    
    if canal in config.get('filtros_salvos', {}) and nome in config['filtros_salvos'][canal]:
        del config['filtros_salvos'][canal][nome]
        return salvar_config(config)
    
    return False
