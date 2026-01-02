"""
Scanner de rede para encontrar servidor MySQL na rede local
"""
import socket
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import mysql.connector


def get_local_ip():
    """Retorna o IP local da máquina."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "192.168.0.1"


def get_network_prefix():
    """Retorna o prefixo da rede (ex: 192.168.0)"""
    ip = get_local_ip()
    parts = ip.split('.')
    return '.'.join(parts[:3])


def check_mysql_port(ip: str, port: int = 3306, timeout: float = 0.5) -> bool:
    """Verifica se a porta MySQL está aberta em um IP."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False


def test_mysql_connection(ip: str, user: str = "root", password: str = "color1234", database: str = "sinc_db") -> bool:
    """Testa se a conexão MySQL funciona."""
    try:
        conn = mysql.connector.connect(
            host=ip,
            port=3306,
            user=user,
            password=password,
            database=database,
            connect_timeout=3
        )
        conn.close()
        return True
    except:
        return False


def scan_network_for_mysql(callback=None, max_workers: int = 50) -> list:
    """
    Escaneia a rede local em busca de servidores MySQL.
    
    Args:
        callback: Função chamada com (ip, status) durante o scan
        max_workers: Número de threads paralelas
    
    Returns:
        Lista de IPs com MySQL encontrado
    """
    prefix = get_network_prefix()
    found_servers = []
    total = 254
    checked = [0]
    
    def check_ip(ip):
        checked[0] += 1
        if callback:
            callback(ip, f"Verificando... {checked[0]}/{total}")
        
        if check_mysql_port(ip):
            return ip
        return None
    
    ips = [f"{prefix}.{i}" for i in range(1, 255)]
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(check_ip, ip): ip for ip in ips}
        for future in as_completed(futures):
            result = future.result()
            if result:
                found_servers.append(result)
    
    return found_servers


def scan_network_async(on_found, on_progress, on_complete):
    """
    Executa o scan em uma thread separada.
    
    Args:
        on_found: Callback quando encontra servidor (ip)
        on_progress: Callback de progresso (current, total, ip)
        on_complete: Callback quando termina (list of servers)
    """
    def run_scan():
        prefix = get_network_prefix()
        found = []
        total = 254
        
        for i in range(1, 255):
            ip = f"{prefix}.{i}"
            on_progress(i, total, ip)
            
            if check_mysql_port(ip, timeout=0.3):
                found.append(ip)
                on_found(ip)
        
        on_complete(found)
    
    thread = threading.Thread(target=run_scan, daemon=True)
    thread.start()
    return thread
