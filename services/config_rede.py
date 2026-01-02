"""
Configuração de conexão para o Sistema de Sincronização
Suporta MySQL Community para múltiplos usuários
"""
import os
import json

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".sinc_config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


def get_config():
    """Retorna a configuração salva ou valores padrão."""
    default = {
        "db_type": "mysql",  # 'mysql' ou 'sqlite'
        "mysql_host": "192.168.0.129",
        "mysql_port": 3306,
        "mysql_user": "root",
        "mysql_password": "color1234",
        "mysql_database": "sinc_db",
        # Fallback SQLite (para desenvolvimento local)
        "sqlite_path": None,  # None = usar padrão local
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return {**default, **config}
        except:
            pass
    return default


def config_exists():
    """Verifica se já existe uma configuração salva pelo usuário."""
    return os.path.exists(CONFIG_FILE)


def save_config(mysql_host: str = "192.168.0.129", mysql_port: int = 3306, 
                mysql_user: str = "root", mysql_password: str = "color1234",
                mysql_database: str = "sinc_db", db_type: str = "mysql"):
    """Salva a configuração de conexão MySQL."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    config = {
        "db_type": db_type,
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


def get_db_path(server_ip: str = None):
    """
    Retorna o caminho do banco SQLite (apenas para fallback/desenvolvimento).
    Em produção, usar MySQL via get_mysql_config().
    """
    if server_ip is None:
        config = get_config()
        sqlite_path = config.get("sqlite_path")
        if sqlite_path:
            return sqlite_path
    
    if server_ip and server_ip.strip().lower() not in ["localhost", "127.0.0.1", ""]:
        # Caminho de rede
        if len(server_ip) >= 1 and server_ip[0].isalpha() and (len(server_ip) == 1 or server_ip[1] == ':'):
            # Letra de unidade
            drive_path = server_ip if server_ip.endswith("\\") else server_ip + "\\"
            return os.path.join(drive_path, "sincronizacao.db")
        return f"\\\\{server_ip}\\Sincronizacao\\sincronizacao.db"
    
    # Local
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "data", "sincronizacao.db")


def test_connection(server_ip: str = None) -> tuple:
    """
    Testa conexão com MySQL.
    
    Args:
        server_ip: Host do MySQL
        
    Returns:
        (sucesso, mensagem, info)
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
