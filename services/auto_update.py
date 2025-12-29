"""
Auto-Update Service via GitHub Releases
Verifica atualizações no GitHub e permite download/instalação automática
"""
import os
import sys
import json
import shutil
import tempfile
import threading
from typing import Optional, Tuple, Callable
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

# Versão atual do aplicativo - ATUALIZAR A CADA RELEASE
CURRENT_VERSION = "1.1.2"

# Repositório GitHub
GITHUB_OWNER = "samuelCriap"
GITHUB_REPO = "sinc"

# Token de acesso para repositório privado
GITHUB_TOKEN = "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"

# Nome do arquivo EXE no release
EXE_NAME = "SINC.exe"

# API URL
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"


# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES DE VERSÃO
# ═══════════════════════════════════════════════════════════════════════════════

def get_local_version() -> str:
    """Retorna a versão atual do aplicativo."""
    return CURRENT_VERSION


def parse_version(version_str: str) -> Tuple[int, int, int]:
    """
    Converte string de versão para tupla de inteiros.
    Ex: "1.2.3" -> (1, 2, 3)
        "v1.2.3" -> (1, 2, 3)
    """
    version_str = version_str.strip().lstrip('v')
    parts = version_str.split('.')
    
    try:
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return (major, minor, patch)
    except ValueError:
        return (0, 0, 0)


def is_newer_version(remote_version: str, local_version: str) -> bool:
    """Verifica se a versão remota é mais nova que a local."""
    return parse_version(remote_version) > parse_version(local_version)


# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICAÇÃO DE ATUALIZAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

def check_for_update() -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
    """
    Verifica se há uma nova versão disponível no GitHub.
    
    Returns:
        Tuple contendo:
        - bool: True se há atualização disponível
        - str: Nova versão (ou None)
        - str: URL de download do EXE (ou None)
        - str: Notas do release (ou None)
    """
    try:
        # Preparar request com User-Agent e Token (GitHub requer para repos privados)
        headers = {
            'User-Agent': 'SINC-Auto-Updater',
            'Accept': 'application/vnd.github.v3+json'
        }
        if GITHUB_TOKEN:
            headers['Authorization'] = f'token {GITHUB_TOKEN}'
        
        request = Request(GITHUB_API_URL, headers=headers)
        
        with urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        # Extrair informações do release
        remote_version = data.get('tag_name', '')
        release_notes = data.get('body', '')
        
        # Procurar o asset do EXE
        download_url = None
        for asset in data.get('assets', []):
            if asset.get('name', '').lower() == EXE_NAME.lower():
                download_url = asset.get('browser_download_url')
                break
        
        # Verificar se é uma versão mais nova
        local_version = get_local_version()
        if is_newer_version(remote_version, local_version) and download_url:
            return (True, remote_version, download_url, release_notes)
        
        return (False, None, None, None)
        
    except (URLError, HTTPError, json.JSONDecodeError, KeyError) as e:
        print(f"[AutoUpdate] Erro ao verificar atualização: {e}")
        return (False, None, None, None)
    except Exception as e:
        print(f"[AutoUpdate] Erro inesperado: {e}")
        return (False, None, None, None)


# ═══════════════════════════════════════════════════════════════════════════════
# DOWNLOAD DA ATUALIZAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

def download_update(
    download_url: str,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Baixa a nova versão do EXE.
    
    Args:
        download_url: URL para download do EXE
        progress_callback: Função callback(bytes_baixados, total_bytes) para progresso
        
    Returns:
        Tuple contendo:
        - bool: True se download foi bem sucedido
        - str: Caminho do arquivo baixado (ou None em caso de erro)
    """
    try:
        # Criar arquivo temporário
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"SINC_update_{os.getpid()}.exe")
        
        # Preparar request com token para repos privados
        headers = {'User-Agent': 'SINC-Auto-Updater'}
        if GITHUB_TOKEN:
            headers['Authorization'] = f'token {GITHUB_TOKEN}'
            headers['Accept'] = 'application/octet-stream'
        
        request = Request(download_url, headers=headers)
        
        with urlopen(request, timeout=300) as response:
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            chunk_size = 8192
            
            with open(temp_path, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if progress_callback:
                        progress_callback(downloaded, total_size)
        
        return (True, temp_path)
        
    except Exception as e:
        print(f"[AutoUpdate] Erro ao baixar atualização: {e}")
        return (False, None)


# ═══════════════════════════════════════════════════════════════════════════════
# APLICAR ATUALIZAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

def get_executable_path() -> str:
    """Retorna o caminho do executável atual."""
    if getattr(sys, 'frozen', False):
        # Rodando como EXE compilado
        return sys.executable
    else:
        # Rodando como script Python
        return os.path.abspath(sys.argv[0])


def apply_update(new_exe_path: str) -> bool:
    """
    Aplica a atualização substituindo o EXE atual.
    
    Esta função cria um script batch que:
    1. Aguarda o app fechar
    2. Substitui o EXE antigo pelo novo
    3. (Opcional) Reabre o app
    
    Args:
        new_exe_path: Caminho do novo EXE baixado
        
    Returns:
        bool: True se a substituição foi agendada com sucesso
    """
    try:
        current_exe = get_executable_path()
        
        # Se não está rodando como EXE, simular sucesso para testes
        if not getattr(sys, 'frozen', False):
            print(f"[AutoUpdate] Modo desenvolvimento - simulando atualização")
            print(f"[AutoUpdate] Novo EXE: {new_exe_path}")
            print(f"[AutoUpdate] EXE atual: {current_exe}")
            return True
        
        # Criar script batch para substituição
        batch_path = os.path.join(tempfile.gettempdir(), "sinc_update.bat")
        
        batch_content = f'''@echo off
echo Aguardando aplicativo fechar...
timeout /t 2 /nobreak > nul

:wait_loop
tasklist /FI "PID eq {os.getpid()}" 2>NUL | find /I /N "{os.getpid()}" >NUL
if "%ERRORLEVEL%"=="0" (
    timeout /t 1 /nobreak > nul
    goto wait_loop
)

echo Aplicando atualizacao...
copy /Y "{new_exe_path}" "{current_exe}"

if %ERRORLEVEL% EQU 0 (
    echo Atualizacao concluida com sucesso!
    del "{new_exe_path}"
) else (
    echo Erro ao aplicar atualizacao!
)

del "%~f0"
'''
        
        with open(batch_path, 'w', encoding='utf-8') as f:
            f.write(batch_content)
        
        # Executar script batch em background
        import subprocess
        subprocess.Popen(
            ['cmd', '/c', batch_path],
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            close_fds=True
        )
        
        return True
        
    except Exception as e:
        print(f"[AutoUpdate] Erro ao aplicar atualização: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÃO PRINCIPAL DE ATUALIZAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

def perform_full_update(
    download_url: str,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    status_callback: Optional[Callable[[str], None]] = None
) -> bool:
    """
    Realiza todo o processo de atualização.
    
    Args:
        download_url: URL para download
        progress_callback: Callback de progresso do download
        status_callback: Callback de status textual
        
    Returns:
        bool: True se atualização foi bem sucedida
    """
    try:
        if status_callback:
            status_callback("Baixando atualização...")
        
        success, temp_path = download_update(download_url, progress_callback)
        
        if not success or not temp_path:
            if status_callback:
                status_callback("Erro no download!")
            return False
        
        if status_callback:
            status_callback("Aplicando atualização...")
        
        if apply_update(temp_path):
            if status_callback:
                status_callback("Atualização concluída! Feche o aplicativo.")
            return True
        else:
            if status_callback:
                status_callback("Erro ao aplicar atualização!")
            return False
            
    except Exception as e:
        print(f"[AutoUpdate] Erro na atualização completa: {e}")
        if status_callback:
            status_callback(f"Erro: {e}")
        return False
