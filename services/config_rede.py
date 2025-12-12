"""
Configuração de conexão de rede para o Sistema de Sincronização
"""
import os
import json

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".sinc_config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


def get_config():
    """Retorna a configuração salva ou valores padrão."""
    default = {
        "server_ip": "localhost",  # localhost = banco local, IP = banco na rede
        "server_port": 8080,
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return {**default, **config}
        except:
            pass
    return default


def save_config(server_ip: str, server_port: int = 8080):
    """Salva a configuração de conexão."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    config = {
        "server_ip": server_ip,
        "server_port": server_port,
    }
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    return True


def get_db_path(server_ip: str = None):
    """
    Retorna o caminho do banco de dados.
    - localhost: usa banco local
    - IP: usa caminho de rede compartilhado
    """
    if server_ip is None:
        server_ip = get_config().get("server_ip", "localhost")
    
    if server_ip in ["localhost", "127.0.0.1", ""]:
        # Banco local
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, "data", "sincronizacao.db")
    else:
        # Banco na rede - caminho UNC
        return f"\\\\{server_ip}\\Sincronizacao\\sincronizacao.db"


def test_connection(server_ip: str) -> tuple:
    """Testa conexão com o servidor."""
    import sqlite3
    
    db_path = get_db_path(server_ip)
    
    try:
        if server_ip in ["localhost", "127.0.0.1", ""]:
            # Local - sempre funciona se existe a pasta
            return True, "Conexão local OK", db_path
        else:
            # Rede - testa se consegue acessar
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path, timeout=5)
                conn.close()
                return True, "Conexão com rede OK", db_path
            else:
                # Tenta criar conexão mesmo assim (pasta pode existir sem o arquivo)
                pasta_rede = os.path.dirname(db_path)
                if os.path.exists(pasta_rede):
                    return True, "Pasta de rede acessível", db_path
                else:
                    return False, f"Pasta não encontrada: {pasta_rede}", db_path
    except Exception as e:
        return False, f"Erro: {str(e)}", db_path
