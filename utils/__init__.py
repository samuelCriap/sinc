# Package utils
import os
import sys


def resource_path(relative_path):
    """
    Retorna o caminho absoluto para um recurso.
    Funciona tanto no modo desenvolvimento quanto empacotado com PyInstaller.
    """
    try:
        # PyInstaller cria uma pasta temporária no _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Em desenvolvimento, usa o diretório do projeto
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    return os.path.join(base_path, relative_path)
