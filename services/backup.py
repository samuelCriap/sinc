"""
Sistema de Backup Automático do Banco de Dados
"""
import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Tuple


# Configuração
BACKUP_FOLDER = "data/backups"
MAX_BACKUPS = 7  # Manter últimos 7 backups
DB_PATH = "data/sinc.db"


def get_backup_folder() -> str:
    """Retorna caminho da pasta de backups, criando se necessário."""
    if not os.path.exists(BACKUP_FOLDER):
        os.makedirs(BACKUP_FOLDER)
    return BACKUP_FOLDER


def listar_backups() -> List[Tuple[str, datetime, int]]:
    """
    Lista todos os backups disponíveis.
    
    Returns:
        Lista de tuplas (caminho, data, tamanho_bytes)
    """
    folder = get_backup_folder()
    backups = []
    
    for filename in os.listdir(folder):
        if filename.startswith('sinc_backup_') and filename.endswith('.db'):
            filepath = os.path.join(folder, filename)
            stat = os.stat(filepath)
            
            # Extrair data do nome
            try:
                date_str = filename.replace('sinc_backup_', '').replace('.db', '')
                date = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
            except:
                date = datetime.fromtimestamp(stat.st_mtime)
            
            backups.append((filepath, date, stat.st_size))
    
    # Ordenar por data (mais recente primeiro)
    backups.sort(key=lambda x: x[1], reverse=True)
    return backups


def criar_backup() -> Optional[str]:
    """
    Cria um backup do banco de dados.
    
    Returns:
        Caminho do backup criado ou None se falhou
    """
    if not os.path.exists(DB_PATH):
        print("[Backup] Banco de dados não encontrado")
        return None
    
    try:
        folder = get_backup_folder()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(folder, f'sinc_backup_{timestamp}.db')
        
        # Usar SQLite backup API para segurança
        source = sqlite3.connect(DB_PATH)
        dest = sqlite3.connect(backup_path)
        
        source.backup(dest)
        
        source.close()
        dest.close()
        
        print(f"[Backup] Criado: {backup_path}")
        
        # Limpar backups antigos
        limpar_backups_antigos()
        
        return backup_path
        
    except Exception as e:
        print(f"[Backup] Erro ao criar: {e}")
        return None


def limpar_backups_antigos() -> int:
    """
    Remove backups além do limite MAX_BACKUPS.
    
    Returns:
        Número de backups removidos
    """
    backups = listar_backups()
    removidos = 0
    
    if len(backups) > MAX_BACKUPS:
        for backup_path, _, _ in backups[MAX_BACKUPS:]:
            try:
                os.remove(backup_path)
                removidos += 1
                print(f"[Backup] Removido antigo: {backup_path}")
            except:
                pass
    
    return removidos


def restaurar_backup(backup_path: str) -> bool:
    """
    Restaura um backup para o banco de dados principal.
    
    Args:
        backup_path: Caminho do backup a restaurar
        
    Returns:
        True se sucesso, False se falhou
    """
    if not os.path.exists(backup_path):
        print(f"[Backup] Arquivo não encontrado: {backup_path}")
        return False
    
    try:
        # Criar backup do estado atual antes de restaurar
        current_backup = criar_backup()
        
        # Restaurar
        shutil.copy2(backup_path, DB_PATH)
        print(f"[Backup] Restaurado: {backup_path}")
        return True
        
    except Exception as e:
        print(f"[Backup] Erro ao restaurar: {e}")
        return False


def backup_necessario() -> bool:
    """
    Verifica se é necessário criar backup (não há backup hoje).
    
    Returns:
        True se precisa fazer backup
    """
    backups = listar_backups()
    
    if not backups:
        return True
    
    ultimo_backup_date = backups[0][1].date()
    hoje = datetime.now().date()
    
    return ultimo_backup_date < hoje


def executar_backup_automatico() -> Optional[str]:
    """
    Executa backup automático se necessário.
    
    Returns:
        Caminho do backup ou None se não foi necessário
    """
    if backup_necessario():
        print("[Backup] Executando backup automático...")
        return criar_backup()
    else:
        print("[Backup] Backup de hoje já existe")
        return None
