"""
Configuração de conexão MySQL para o Sistema de Sincronização
"""
import os
import json

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".sinc_config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# Configuração padrão do MySQL
DEFAULT_CONFIG = {
    "mysql_host": "192.168.0.129",
    "mysql_port": 3306,
    "mysql_user": "root",
    "mysql_password": "color1234",
    "mysql_database": "sinc_db",
}


def get_config():
    """Retorna a configuração salva ou valores padrão."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return {**DEFAULT_CONFIG, **config}
        except:
            pass
    return DEFAULT_CONFIG.copy()


def config_exists():
    """Verifica se já existe uma configuração salva pelo usuário."""
    return os.path.exists(CONFIG_FILE)


def save_config(mysql_host: str = "192.168.0.129", mysql_port: int = 3306, 
                mysql_user: str = "root", mysql_password: str = "color1234",
                mysql_database: str = "sinc_db"):
    """Salva a configuração de conexão MySQL."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    config = {
        "mysql_host": mysql_host,
        "mysql_port": mysql_port,
        "mysql_user": mysql_user,
        "mysql_password": mysql_password,
        "mysql_database": mysql_database,
    }
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    return True


def get_mysql_config():
    """Retorna configuração MySQL como dict para conexão."""
    config = get_config()
    return {
        "host": config.get("mysql_host", "192.168.0.129"),
        "port": config.get("mysql_port", 3306),
        "user": config.get("mysql_user", "root"),
        "password": config.get("mysql_password", "color1234"),
        "database": config.get("mysql_database", "sinc_db"),
    }


def test_connection(server_ip: str = None) -> tuple:
    """
    Testa conexão com MySQL.
    
    Args:
        server_ip: Host do MySQL (opcional, usa config se não informado)
        
    Returns:
        (sucesso, mensagem, host)
    """
    try:
        import mysql.connector
        
        config = get_config()
        host = server_ip.strip() if server_ip else config.get("mysql_host", "192.168.0.129")
        
        conn = mysql.connector.connect(
            host=host,
            port=config.get("mysql_port", 3306),
            user=config.get("mysql_user", "root"),
            password=config.get("mysql_password", "color1234"),
            database=config.get("mysql_database", "sinc_db"),
            connect_timeout=5
        )
        conn.close()
        return True, f"MySQL conectado: {host}", host
        
    except mysql.connector.Error as e:
        if e.errno == 1049:  # Database doesn't exist
            return False, f"Banco 'sinc_db' não existe. Crie-o primeiro.", server_ip
        elif e.errno == 1045:  # Access denied
            return False, f"Acesso negado. Verifique usuário/senha.", server_ip
        elif e.errno == 2003:  # Can't connect
            return False, f"Não foi possível conectar a {server_ip}:3306", server_ip
        else:
            return False, f"Erro MySQL: {e}", server_ip
    except Exception as e:
        return False, f"Erro: {str(e)}", server_ip
