"""
Módulo de acesso ao banco de dados MySQL para o Sistema de Sincronização de SKUs
"""
import mysql.connector
from mysql.connector import Error as MySQLError
import os
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

from services.config_rede import get_mysql_config

# Lista de canais suportados
CANAIS = [
    "NETSHOES", "CENTAURO", "TIKTOK", "SHEIN", 
    "RENNER", "SHOPEE", "MELI", "DAFITI", "AMAZON"
]

# Status possíveis de um produto em um canal (vazio = sem status definido)
STATUS_PRODUTO = ["", "ATIVO", "CATALOGANDO", "ERRO"]


def get_connection():
    """
    Retorna uma conexão MySQL otimizada para performance.
    Usa cursor do tipo dictionary para retornar rows como dicts.
    """
    config = get_mysql_config()
    
    conn = mysql.connector.connect(
        host=config['host'],
        port=config['port'],
        user=config['user'],
        password=config['password'],
        database=config['database'],
        autocommit=False,
        connection_timeout=10,
        # Pool de conexões para melhor performance
        pool_name="sinc_pool",
        pool_size=5,
        pool_reset_session=True
    )
    
    return conn


def create_tables():
    """Cria as tabelas do banco de dados MySQL se não existirem."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Tabela principal de produtos sincronizados
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos_sinc (
            id INT PRIMARY KEY AUTO_INCREMENT,
            codigo_produto VARCHAR(100) NOT NULL,
            sku VARCHAR(100),
            descricao TEXT,
            marca VARCHAR(200),
            gtin VARCHAR(50),
            categoria VARCHAR(200),
            preco DECIMAL(10,2),
            importado_por VARCHAR(100),
            col_b VARCHAR(255),
            col_c VARCHAR(255),
            col_i VARCHAR(255),
            col_k VARCHAR(255),
            col_l VARCHAR(255),
            col_m VARCHAR(255),
            col_n VARCHAR(255),
            col_o VARCHAR(255),
            col_p VARCHAR(255),
            col_q VARCHAR(255),
            col_r VARCHAR(255),
            col_ab VARCHAR(255),
            col_ac VARCHAR(255),
            col_ae VARCHAR(255),
            col_af VARCHAR(255),
            col_ag VARCHAR(255),
            col_ao VARCHAR(255),
            col_ap VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_codigo_produto (codigo_produto)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # Status por canal (1 linha por produto/canal)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produto_canal (
            id INT PRIMARY KEY AUTO_INCREMENT,
            produto_id INT NOT NULL,
            canal VARCHAR(50) NOT NULL,
            status VARCHAR(50) DEFAULT '',
            bloqueado TINYINT(1) DEFAULT 0,
            motivo_bloqueio TEXT,
            importado_omnie TINYINT(1) DEFAULT 0,
            importado_anymarket TINYINT(1) DEFAULT 0,
            usuario_alteracao VARCHAR(100),
            cod_marketplace VARCHAR(100),
            data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_produto_canal (produto_id, canal),
            INDEX idx_produto_id (produto_id),
            INDEX idx_canal (canal)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # Blocklist por canal
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blocklist (
            id INT PRIMARY KEY AUTO_INCREMENT,
            canal VARCHAR(50) NOT NULL,
            termo_bloqueio VARCHAR(255) NOT NULL,
            tipo VARCHAR(50) DEFAULT 'MODELO',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_canal_termo (canal, termo_bloqueio)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # Log de importações
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS importacoes (
            id INT PRIMARY KEY AUTO_INCREMENT,
            arquivo TEXT,
            tipo_modelo VARCHAR(100),
            qtd_produtos INT,
            usuario VARCHAR(100),
            data_importacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # Tabela de usuários
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INT PRIMARY KEY AUTO_INCREMENT,
            username VARCHAR(100) NOT NULL UNIQUE,
            senha VARCHAR(255) NOT NULL,
            nome VARCHAR(200),
            email VARCHAR(200),
            cargo VARCHAR(50) DEFAULT 'usuario',
            status VARCHAR(50) DEFAULT 'PENDENTE',
            ativo TINYINT(1) DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # Tabela de listas de preço
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lista_precos (
            id INT PRIMARY KEY AUTO_INCREMENT,
            importacao_id INT,
            caminho_planilha TEXT NOT NULL,
            nome_planilha VARCHAR(255),
            qtd_produtos INT,
            data_inicio_vigencia VARCHAR(20),
            data_fim_vigencia VARCHAR(20),
            caminho_csv TEXT,
            baixado TINYINT(1) DEFAULT 0,
            usuario VARCHAR(100),
            baixado_por VARCHAR(100),
            data_geracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # Tabela de produtos bloqueados por canal
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produto_blocklist (
            id INT PRIMARY KEY AUTO_INCREMENT,
            produto_id INT NOT NULL,
            canal VARCHAR(50) NOT NULL,
            termo_bloqueado VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_produto_canal (produto_id, canal),
            INDEX idx_produto_id (produto_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # Tabela de log de atividades
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS log_atividades (
            id INT PRIMARY KEY AUTO_INCREMENT,
            usuario VARCHAR(100) NOT NULL,
            acao VARCHAR(200) NOT NULL,
            detalhes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_usuario (usuario),
            INDEX idx_created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # Tabela de controle de chamados
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chamados (
            id INT PRIMARY KEY AUTO_INCREMENT,
            numero VARCHAR(100) NOT NULL,
            prioridade VARCHAR(50) DEFAULT 'MÉDIA',
            canal VARCHAR(50),
            observacoes TEXT,
            link TEXT,
            criado_por VARCHAR(100) NOT NULL,
            na_lixeira TINYINT(1) DEFAULT 0,
            concluido TINYINT(1) DEFAULT 0,
            data_conclusao TIMESTAMP NULL,
            concluido_por VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_prioridade (prioridade),
            INDEX idx_criado_por (criado_por)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # Tabela de histórico de alterações por produto
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_produto (
            id INT PRIMARY KEY AUTO_INCREMENT,
            sku VARCHAR(100) NOT NULL,
            campo VARCHAR(100) NOT NULL,
            valor_antigo TEXT,
            valor_novo TEXT,
            usuario VARCHAR(100) NOT NULL,
            canal VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_sku (sku),
            INDEX idx_created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    conn.commit()
    cursor.close()
    conn.close()


def criar_usuario_inicial():
    """Cria um usuário admin inicial se não existir."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT COUNT(*) AS cnt FROM usuarios")
    result = cursor.fetchone()
    count = result['cnt'] if result else 0
    
    if count == 0:
        cursor.execute(
            "INSERT INTO usuarios (username, senha, nome, email, cargo, status) VALUES (%s, %s, %s, %s, %s, %s)",
            ("admin", "admin123", "Administrador", "admin@sistema.com", "admin", "ATIVO")
        )
        conn.commit()
    
    cursor.close()
    conn.close()


def cadastrar_usuario(username: str, senha: str, nome: str, email: str) -> tuple:
    """Cadastra um novo usuário com status PENDENTE."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            INSERT INTO usuarios (username, senha, nome, email, cargo, status)
            VALUES (%s, %s, %s, %s, 'usuario', 'PENDENTE')
        """, (username, senha, nome, email))
        conn.commit()
        return True, "Cadastro realizado! Aguarde aprovação do administrador."
    except Exception as e:
        if "UNIQUE" in str(e):
            return False, "Usuário já existe!"
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()


def listar_usuarios_pendentes() -> list:
    """Lista usuários com status PENDENTE."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, nome, email, created_at FROM usuarios WHERE status = 'PENDENTE'")
    result = cursor.fetchall()
    conn.close()
    return result


def listar_todos_usuarios() -> list:
    """Lista todos os usuários."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, nome, email, cargo, status, created_at FROM usuarios")
    result = cursor.fetchall()
    conn.close()
    return result


def aprovar_usuario(user_id: int, cargo: str = "usuario") -> bool:
    """Aprova um usuário pendente."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("UPDATE usuarios SET status = 'ATIVO', cargo = %s WHERE id = %s", (cargo, user_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def rejeitar_usuario(user_id: int) -> bool:
    """Rejeita um usuário pendente (deleta)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("DELETE FROM usuarios WHERE id = %s", (user_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def alterar_cargo_usuario(user_id: int, novo_cargo: str) -> bool:
    """Altera o cargo de um usuário."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("UPDATE usuarios SET cargo = %s WHERE id = %s", (novo_cargo, user_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def bloquear_usuario(user_id: int, bloquear: bool = True) -> bool:
    """Bloqueia (status=INATIVO) ou desbloqueia (status=ATIVO) um usuário."""
    status = "INATIVO" if bloquear else "ATIVO"
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("UPDATE usuarios SET status = %s WHERE id = %s", (status, user_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def remover_usuario(user_id: int) -> bool:
    """Remove um usuário permanentemente do banco de dados."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("DELETE FROM usuarios WHERE id = %s", (user_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


# ============================================================
# FUNÇÕES DE LOG DE ATIVIDADES
# ============================================================

def registrar_log(usuario: str, acao: str, detalhes: str = None):
    """Registra uma ação no log de atividades."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            INSERT INTO log_atividades (usuario, acao, detalhes)
            VALUES (%s, %s, %s)
        """, (usuario, acao, detalhes))
        conn.commit()
        conn.close()
    except Exception:
        pass  # Não falhar se log não funcionar


def listar_logs(limite: int = 100) -> list:
    """Lista os últimos registros de log."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT usuario, acao, detalhes, created_at 
        FROM log_atividades 
        ORDER BY created_at DESC 
        LIMIT %s
    """, (limite,))
    result = cursor.fetchall()
    conn.close()
    return result


def limpar_logs(dias: int = 30):
    """Remove logs mais antigos que X dias."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        DELETE FROM log_atividades 
        WHERE created_at < datetime('now', '-' || %s || ' days')
    """, (dias,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected


# ============================================================
# FUNÇÕES DE HISTÓRICO DE PRODUTO
# ============================================================

def registrar_historico(sku: str, campo: str, valor_antigo: str, valor_novo: str, usuario: str, canal: str = None):
    """Registra uma alteração no histórico do produto."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            INSERT INTO historico_produto (sku, campo, valor_antigo, valor_novo, usuario, canal)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (sku, campo, str(valor_antigo) if valor_antigo else None, 
              str(valor_novo) if valor_novo else None, usuario, canal))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Histórico] Erro ao registrar: {e}")


def listar_historico_produto(sku: str, limite: int = 50) -> list:
    """Lista histórico de alterações de um produto."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, sku, campo, valor_antigo, valor_novo, usuario, canal, created_at
        FROM historico_produto WHERE sku = %s ORDER BY created_at DESC LIMIT %s
    """, (sku, limite))
    result = cursor.fetchall()
    conn.close()
    return result


def listar_historico_geral(limite: int = 100) -> list:
    """Lista histórico geral de alterações."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, sku, campo, valor_antigo, valor_novo, usuario, canal, created_at
        FROM historico_produto ORDER BY created_at DESC LIMIT %s
    """, (limite,))
    result = cursor.fetchall()
    conn.close()
    return result


# ============================================================
# FUNÇÕES DE CHAMADOS
# ============================================================

def criar_chamado(numero: str, prioridade: str, canal: str, observacoes: str, link: str, criado_por: str) -> int:
    """Cria um novo chamado."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        INSERT INTO chamados (numero, prioridade, canal, observacoes, link, criado_por)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (numero, prioridade, canal, observacoes, link, criado_por))
    conn.commit()
    chamado_id = cursor.lastrowid
    conn.close()
    return chamado_id


def listar_chamados(na_lixeira: bool = False) -> list:
    """Lista chamados ativos ou na lixeira (exclui concluídos)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, numero, prioridade, canal, observacoes, link, criado_por, na_lixeira, created_at
        FROM chamados
        WHERE na_lixeira = %s AND (concluido = 0 OR concluido IS NULL)
        ORDER BY 
            CASE prioridade 
                WHEN 'URGENTE' THEN 1 
                WHEN 'ALTA' THEN 2 
                WHEN 'MÉDIA' THEN 3 
                WHEN 'BAIXA' THEN 4 
            END,
            created_at DESC
    """, (1 if na_lixeira else 0,))
    result = cursor.fetchall()
    conn.close()
    return result


def atualizar_chamado(chamado_id: int, numero: str, prioridade: str, canal: str, observacoes: str, link: str) -> bool:
    """Atualiza um chamado existente."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        UPDATE chamados 
        SET numero = %s, prioridade = %s, canal = %s, observacoes = %s, link = %s
        WHERE id = %s
    """, (numero, prioridade, canal, observacoes, link, chamado_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def mover_para_lixeira(chamado_id: int) -> bool:
    """Move um chamado para a lixeira."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("UPDATE chamados SET na_lixeira = 1 WHERE id = %s", (chamado_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def restaurar_chamado(chamado_id: int) -> bool:
    """Restaura um chamado da lixeira."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("UPDATE chamados SET na_lixeira = 0 WHERE id = %s", (chamado_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def excluir_chamado_permanente(chamado_id: int) -> bool:
    """Exclui permanentemente um chamado."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("DELETE FROM chamados WHERE id = %s", (chamado_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def concluir_chamado(chamado_id: int, usuario: str) -> bool:
    """Marca um chamado como concluído."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        UPDATE chamados 
        SET concluido = 1, data_conclusao = %s, concluido_por = %s
        WHERE id = %s
    """, (datetime.now(), usuario, chamado_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def listar_chamados_concluidos() -> list:
    """Lista chamados concluídos."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, numero, prioridade, canal, observacoes, link, criado_por, 
               concluido, data_conclusao, concluido_por, created_at
        FROM chamados
        WHERE concluido = 1 AND na_lixeira = 0
        ORDER BY data_conclusao DESC
    """)
    result = cursor.fetchall()
    conn.close()
    return result


# ============================================================
# FUNÇÕES DE PRODUTOS
# ============================================================

def inserir_produto(codigo_produto: str, sku: str = None, descricao: str = None,
                    marca: str = None, gtin: str = None, categoria: str = None,
                    preco: float = None, importado_por: str = None,
                    **kwargs) -> int:
    """Insere um produto na tabela produtos_sinc. Retorna o ID do produto."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Extrair campos extras
    col_b = kwargs.get('col_b')
    col_c = kwargs.get('col_c')
    col_i = kwargs.get('col_i')
    col_k = kwargs.get('col_k')
    col_l = kwargs.get('col_l')
    col_m = kwargs.get('col_m')
    col_n = kwargs.get('col_n')
    col_o = kwargs.get('col_o')
    col_p = kwargs.get('col_p')
    col_q = kwargs.get('col_q')
    col_r = kwargs.get('col_r')
    col_ab = kwargs.get('col_ab')
    col_ac = kwargs.get('col_ac')
    col_ae = kwargs.get('col_ae')
    col_af = kwargs.get('col_af')
    col_ag = kwargs.get('col_ag')
    col_ao = kwargs.get('col_ao')
    col_ap = kwargs.get('col_ap')
    
    try:
        cursor.execute("""
            INSERT INTO produtos_sinc (
                codigo_produto, sku, descricao, marca, gtin, categoria, preco, importado_por,
                col_b, col_c, col_i, col_k, col_l, col_m, col_n, col_o, col_p, col_q, col_r,
                col_ab, col_ac, col_ae, col_af, col_ag, col_ao, col_ap
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            codigo_produto, sku, descricao, marca, gtin, categoria, preco, importado_por,
            col_b, col_c, col_i, col_k, col_l, col_m, col_n, col_o, col_p, col_q, col_r,
            col_ab, col_ac, col_ae, col_af, col_ag, col_ao, col_ap
        ))
        conn.commit()
        return cursor.lastrowid
    except mysql.connector.IntegrityError:
        # Produto já existe, retorna ID existente
        cursor.execute("SELECT id FROM produtos_sinc WHERE codigo_produto = %s", (codigo_produto,))
        row = cursor.fetchone()
        return row['id'] if row else None
    finally:
        conn.close()


def buscar_produto_por_codigo(codigo_produto: str) -> Optional[Dict[str, Any]]:
    """Busca um produto pelo código."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM produtos_sinc WHERE codigo_produto = %s", (codigo_produto,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def listar_produtos(limite: int = 1000) -> List[Dict[str, Any]]:
    """Lista todos os produtos."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM produtos_sinc ORDER BY id DESC LIMIT %s", (limite,))
    rows = cursor.fetchall()
    conn.close()
    return list(rows)


# Função duplicada removida
def listar_produtos_canal_old(canal: str) -> List[Dict[str, Any]]:
    return []


def atualizar_produto_campo(produto_id: int, campo: str, valor: str):
    """Atualiza um campo específico de um produto."""
    campos_permitidos = ['codigo_produto', 'sku', 'descricao', 'marca', 'gtin', 'categoria']
    if campo not in campos_permitidos:
        return False
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"""
        UPDATE produtos_sinc 
        SET {campo} = %s, updated_at = %s
        WHERE id = %s
    """, (valor, datetime.now(), produto_id))
    conn.commit()
    conn.close()
    return True


def remover_produto_canal(produto_id: int, canal: str) -> bool:
    """Remove um produto de um canal específico."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        DELETE FROM produto_canal 
        WHERE produto_id = %s AND canal = %s
    """, (produto_id, canal.upper()))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def excluir_produto_canal(produto_id: int, canal: str, usuario: str = None) -> bool:
    """
    Exclui um produto de um canal marcando status como '-'.
    Não remove a entrada, apenas marca como excluído do canal.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        UPDATE produto_canal 
        SET status = '-', motivo_bloqueio = 'Removido manualmente', usuario_alteracao = %s, data_alteracao = NOW()
        WHERE produto_id = %s AND canal = %s
    """, (usuario, produto_id, canal.upper()))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def adicionar_sku_canal(sku: str, canal: str, status: str = "", usuario: str = None,
                         descricao: str = None, marca: str = None, gtin: str = None,
                         categoria: str = None, preco: float = None) -> dict:
    """
    Adiciona um SKU a um canal. Se o produto não existir no banco, cria.
    
    Args:
        sku: Código SKU do produto
        canal: Nome do canal
        status: Status inicial no canal
        usuario: Usuário que está adicionando
        descricao: Descrição do produto (opcional)
        marca: Marca do produto (opcional)
        gtin: GTIN/EAN do produto (opcional)
        categoria: Categoria do produto (opcional)
        preco: Preço do produto (opcional)
    
    Returns:
        dict com 'produto_id', 'criado' (bool se foi criado novo), 'adicionado' (bool se foi adicionado ao canal)
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Verificar se produto existe
    cursor.execute("SELECT id FROM produtos_sinc WHERE sku = %s OR codigo_produto = %s", (sku, sku))
    row = cursor.fetchone()
    
    criado = False
    if row:
        produto_id = row['id']
    else:
        # Criar produto (sem data_criacao que não existe na tabela)
        cursor.execute("""
            INSERT INTO produtos_sinc (codigo_produto, sku, descricao, marca, gtin, categoria, preco, importado_por)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (sku, sku, descricao, marca, gtin, categoria, preco, usuario))
        produto_id = cursor.lastrowid
        criado = True
    
    # Verificar se já existe no canal
    cursor.execute("""
        SELECT id, status FROM produto_canal 
        WHERE produto_id = %s AND canal = %s
    """, (produto_id, canal.upper()))
    canal_row = cursor.fetchone()
    
    adicionado = False
    if canal_row:
        # Já existe - atualizar status se diferente de '-'
        if canal_row['status'] == '-':
            cursor.execute("""
                UPDATE produto_canal SET status = %s, motivo_bloqueio = NULL, usuario_alteracao = %s, data_alteracao = NOW()
                WHERE id = %s
            """, (status, usuario, canal_row['id']))
            adicionado = True
    else:
        # Adicionar ao canal
        cursor.execute("""
            INSERT INTO produto_canal (produto_id, canal, status, bloqueado, usuario_alteracao)
            VALUES (%s, %s, %s, 0, %s)
        """, (produto_id, canal.upper(), status, usuario))
        adicionado = True
    
    conn.commit()
    conn.close()
    
    return {
        'produto_id': produto_id,
        'criado': criado,
        'adicionado': adicionado
    }


# ============================================================
# FUNÇÕES DE PRODUTO_BLOCKLIST
# ============================================================

def registrar_produto_blocklist(produto_id: int, canal: str, termo_bloqueado: str = None) -> bool:
    """Registra um produto como bloqueado para um canal específico (não insere em produto_canal)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            INSERT INTO produto_blocklist (produto_id, canal, termo_bloqueado)
            VALUES (%s, %s, %s)
        """, (produto_id, canal.upper(), termo_bloqueado))
        conn.commit()
        return True
    except mysql.connector.IntegrityError:
        return False
    finally:
        conn.close()


def listar_produtos_bloqueados(produto_id: int) -> Dict[str, str]:
    """Retorna um dicionário {canal: termo_bloqueado} dos canais bloqueados para um produto."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT canal, termo_bloqueado FROM produto_blocklist WHERE produto_id = %s
    """, (produto_id,))
    results = {row['canal']: row['termo_bloqueado'] for row in cursor.fetchall()}
    conn.close()
    return results


# ============================================================
# FUNÇÕES DE PRODUTO/CANAL
# ============================================================


def adicionar_produto_canal(produto_id: int, canal: str, status: str = "",
                            bloqueado: bool = False, motivo_bloqueio: str = None,
                            usuario: str = None) -> bool:
    """Adiciona um produto a um canal."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            INSERT INTO produto_canal (produto_id, canal, status, bloqueado, motivo_bloqueio, usuario_alteracao)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (produto_id, canal.upper(), status, 1 if bloqueado else 0, motivo_bloqueio, usuario))
        conn.commit()
        return True
    except mysql.connector.IntegrityError:
        # Já existe
        return False
    finally:
        conn.close()


def atualizar_importacao_externa(produto_id: int, canal: str, omnie: bool = None, anymarket: bool = None):
    """Atualiza checkboxes de importação externa (Omnie One / AnyMarket)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    updates = []
    params = []
    
    if omnie is not None:
        updates.append("importado_omnie = %s")
        params.append(1 if omnie else 0)
    
    if anymarket is not None:
        updates.append("importado_anymarket = %s")
        params.append(1 if anymarket else 0)
    
    if updates:
        params.extend([produto_id, canal.upper()])
        cursor.execute(f"""
            UPDATE produto_canal 
            SET {', '.join(updates)}, data_alteracao = CURRENT_TIMESTAMP
            WHERE produto_id = %s AND canal = %s
        """, params)
        conn.commit()
    
    conn.close()


def marcar_importacao_externa_em_massa(produto_ids: List[int], campo: str, valor: bool) -> int:
    """
    Atualiza em massa flags de importação externa.
    campo: 'omnie' ou 'anymarket'
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    coluna = 'importado_omnie' if campo == 'omnie' else 'importado_anymarket'
    val_int = 1 if valor else 0
    
    if not produto_ids:
        conn.close()
        return 0
        
    # Dividir em lotes de 900 para evitar limite do SQLite
    BATCH_SIZE = 900
    total_afetados = 0
    
    try:
        for i in range(0, len(produto_ids), BATCH_SIZE):
            batch = produto_ids[i:i+BATCH_SIZE]
            placeholders = ','.join(['%s'] * len(batch))
            
            cursor.execute(f"""
                UPDATE produto_canal 
                SET {coluna} = %s, data_alteracao = CURRENT_TIMESTAMP
                WHERE produto_id IN ({placeholders})
            """, tuple([val_int] + list(batch)))
            
            total_afetados += cursor.rowcount
            
        conn.commit()
    except Exception as e:
        print(f"Erro no update em massa {campo}: {e}")
        conn.rollback()
    finally:
        conn.close()
        
    return total_afetados


def atualizar_status_produto_canal(produto_id: int, canal: str, novo_status: str, usuario: str = None):
    """Atualiza o status de um produto em um canal."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        UPDATE produto_canal 
        SET status = %s, usuario_alteracao = %s, data_alteracao = %s
    WHERE produto_id = %s AND canal = %s
    """, (novo_status, usuario, datetime.now(), produto_id, canal.upper()))
    
    # Se o novo status não é blocklist, remove da tabela produto_blocklist
    if novo_status and novo_status.upper() != 'BLOCKLIST':
        cursor.execute("""
            DELETE FROM produto_blocklist 
            WHERE produto_id = %s AND canal = %s
        """, (produto_id, canal.upper()))
    
    conn.commit()
    conn.close()


def atualizar_status_em_massa(canal: str, atualizacoes: Dict[str, str], usuario: str = None) -> int:
    """
    Atualiza status de múltiplos produtos em um canal usando SKU ou codigo_produto.
    atualizacoes: dict {sku: novo_status}
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    count = 0
    now = datetime.now()
    
    try:
        # Busca IDs dos SKUs para update direto (busca em sku E codigo_produto)
        skus = list(atualizacoes.keys())
        
        # Dividir em lotes de 400 para evitar limite de variáveis SQL
        BATCH_SIZE = 400
        mapa_sku_id = {}
        
        for i in range(0, len(skus), BATCH_SIZE):
            batch = skus[i:i + BATCH_SIZE]
            placeholders = ','.join(['%s'] * len(batch))
            
            # Buscar por SKU ou codigo_produto
            cursor.execute(f"""
                SELECT id, sku, codigo_produto FROM produtos_sinc 
                WHERE sku IN ({placeholders}) OR codigo_produto IN ({placeholders})
            """, tuple(batch + batch))
            
            for row in cursor.fetchall():
                if row['sku']: mapa_sku_id[row['sku']] = row['id']
                if row['codigo_produto']: mapa_sku_id[row['codigo_produto']] = row['id']
        
        print(f"SKUs encontrados no banco: {len(mapa_sku_id)} de {len(skus)}")
        
        updates_data = []
        for sku, status in atualizacoes.items():
            if sku in mapa_sku_id:
                pid = mapa_sku_id[sku]
                updates_data.append((status, usuario, pid, canal.upper()))
        
        print(f"Updates a realizar: {len(updates_data)}")
        
        if updates_data:
            cursor.executemany("""
                UPDATE produto_canal 
                SET status = %s, usuario_alteracao = %s, data_alteracao = CURRENT_TIMESTAMP
                WHERE produto_id = %s AND canal = %s
            """, updates_data)
            count = cursor.rowcount
            conn.commit()
            print(f"Rows afetadas: {count}")
            
    except Exception as e:
        print(f"Erro ao atualizar em massa: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()
        
    return count


def atualizar_status_produto_canal_com_erro(produto_id: int, canal: str, novo_status: str, motivo_erro: str, usuario: str = None):
    """Atualiza o status de um produto em um canal com motivo de erro."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        UPDATE produto_canal 
        SET status = %s, motivo_bloqueio = %s, usuario_alteracao = %s, data_alteracao = %s
        WHERE produto_id = %s AND canal = %s
    """, (novo_status, motivo_erro, usuario, datetime.now(), produto_id, canal.upper()))
    
    # Se o novo status não é blocklist, remove da tabela produto_blocklist
    if novo_status and novo_status.upper() != 'BLOCKLIST':
        cursor.execute("""
            DELETE FROM produto_blocklist 
            WHERE produto_id = %s AND canal = %s
        """, (produto_id, canal.upper()))
    
    conn.commit()
    conn.close()


def atualizar_status_em_massa_com_erro(canal: str, atualizacoes: Dict[str, Tuple[str, str]], usuario: str = None) -> int:
    """
    Atualiza status de múltiplos produtos em um canal usando SKU ou codigo_produto.
    atualizacoes: dict {sku: (novo_status, motivo_erro)}
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    count = 0
    
    try:
        # Busca IDs dos SKUs para update direto (busca em sku E codigo_produto)
        skus = list(atualizacoes.keys())
        
        # Dividir em lotes de 400 para evitar limite de variáveis SQL
        BATCH_SIZE = 400
        mapa_sku_id = {}
        
        for i in range(0, len(skus), BATCH_SIZE):
            batch = skus[i:i + BATCH_SIZE]
            placeholders = ','.join(['%s'] * len(batch))
            
            # Buscar por SKU ou codigo_produto
            cursor.execute(f"""
                SELECT id, sku, codigo_produto FROM produtos_sinc 
                WHERE sku IN ({placeholders}) OR codigo_produto IN ({placeholders})
            """, tuple(batch + batch))
            
            for row in cursor.fetchall():
                if row['sku']: mapa_sku_id[row['sku']] = row['id']
                if row['codigo_produto']: mapa_sku_id[row['codigo_produto']] = row['id']
        
        print(f"[{canal}] SKUs encontrados no banco: {len(mapa_sku_id)} de {len(skus)}")
        
        # Atualizar cada produto (suporta tupla de 2 ou 3 elementos)
        for sku, dados in atualizacoes.items():
            if len(dados) == 3:
                status, motivo, cod_mp = dados
            else:
                status, motivo = dados
                cod_mp = None
            
            if sku in mapa_sku_id:
                pid = mapa_sku_id[sku]
                
                # Montar query dinâmica
                campos = ["status = %s", "usuario_alteracao = %s", "data_alteracao = CURRENT_TIMESTAMP"]
                params = [status, usuario]
                
                if motivo:
                    campos.append("motivo_bloqueio = %s")
                    params.append(motivo)
                
                if cod_mp:
                    campos.append("cod_marketplace = %s")
                    params.append(cod_mp)
                
                params.append(pid)
                params.append(canal.upper())
                
                cursor.execute(f"""
                    UPDATE produto_canal 
                    SET {', '.join(campos)}
                    WHERE produto_id = %s AND canal = %s
                """, params)
                
                count += cursor.rowcount
        
        conn.commit()
        print(f"[Netshoes] Produtos atualizados: {count}")
            
    except Exception as e:
        print(f"Erro ao atualizar em massa com erro: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()
        
    return count


def listar_produtos_canal(canal: str, status: str = None) -> List[Dict[str, Any]]:
    """Lista produtos de um canal específico."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT p.*, pc.canal, pc.status, pc.bloqueado, pc.motivo_bloqueio, pc.data_alteracao, pc.cod_marketplace,
               p.col_b, p.col_c, p.col_i, p.col_k, p.col_l, p.col_m, p.col_n, p.col_o, p.col_p, p.col_q, p.col_r,
               p.col_ab, p.col_ac, p.col_ae, p.col_af, p.col_ag, p.col_ao, p.col_ap
        FROM produtos_sinc p
        JOIN produto_canal pc ON p.id = pc.produto_id
        WHERE pc.canal = %s
    """
    params = [canal.upper()]
    
    if status:
        query += " AND pc.status = %s"
        params.append(status)
    
    query += " ORDER BY p.id DESC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return list(rows)


def contar_produtos_por_status_canal(canal: str) -> Dict[str, int]:
    """Conta produtos por status em um canal."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT status, COUNT(*) as qtd
        FROM produto_canal
        WHERE canal = %s
        GROUP BY status
    """, (canal.upper(),))
    rows = cursor.fetchall()
    conn.close()
    return {row['status']: row['qtd'] for row in rows}


def contar_total_por_canal() -> Dict[str, Dict[str, int]]:
    """Retorna contagem de produtos por canal e status."""
    resultado = {}
    for canal in CANAIS:
        resultado[canal] = contar_produtos_por_status_canal(canal)
    return resultado


# ============================================================
# FUNÇÕES DE BLOCKLIST
# ============================================================

def adicionar_blocklist(canal: str, termo: str, tipo: str = "PALAVRA") -> bool:
    """Adiciona um termo à blocklist de um canal."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            INSERT INTO blocklist (canal, termo_bloqueio, tipo)
            VALUES (%s, %s, %s)
        """, (canal.upper(), termo, tipo))
        conn.commit()
        return True
    except mysql.connector.IntegrityError:
        return False
    finally:
        conn.close()


def listar_blocklist(canal: str = None) -> List[Dict[str, Any]]:
    """Lista itens da blocklist."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    if canal:
        cursor.execute("SELECT * FROM blocklist WHERE canal = %s ORDER BY termo_bloqueio", (canal.upper(),))
    else:
        cursor.execute("SELECT * FROM blocklist ORDER BY canal, termo_bloqueio")
    
    rows = cursor.fetchall()
    conn.close()
    return list(rows)


def verificar_blocklist(canal: str, nome_produto: str, marca: str = None) -> Tuple[bool, Optional[str]]:
    """Verifica se um produto está bloqueado para um canal.
    
    Tipos de bloqueio:
    - MARCA: Bloqueia TODOS os produtos da marca (ex: NIKE bloqueada = nenhum Nike entra)
    - MODELO: Bloqueia modelo específico por palavras-chave (ex: ASICS - Netburner bloqueia só esse modelo)
    
    Retorna (bloqueado, termo_encontrado).
    """
    import re
    
    blocklist = listar_blocklist(canal)
    nome_lower = nome_produto.lower() if nome_produto else ""
    marca_lower = marca.lower() if marca else ""
    
    for item in blocklist:
        termo = item['termo_bloqueio']
        tipo = item.get('tipo', 'MODELO').upper()
        
        if tipo == 'MARCA':
            # Bloqueia toda a marca - verifica se o termo está na marca do produto
            termo_lower = termo.lower()
            if termo_lower in marca_lower or termo_lower in nome_lower:
                return True, f"[MARCA] {termo}"
        else:
            # MODELO - Bloqueia por palavras-chave no nome do produto
            palavras_termo = re.findall(r'\w+', termo.lower())
            
            if not palavras_termo:
                continue
            
            # Verifica se TODAS as palavras do termo estão no nome
            todas_presentes = all(palavra in nome_lower for palavra in palavras_termo)
            
            if todas_presentes:
                return True, f"[MODELO] {termo}"
    
    return False, None


def remover_blocklist(id: int) -> bool:
    """Remove um item da blocklist."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("DELETE FROM blocklist WHERE id = %s", (id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def limpar_blocklist_falsos_positivos() -> Dict[str, int]:
    """
    Limpa produtos da tabela produto_blocklist que não casam mais com os 
    termos atuais da blocklist. Retorna estatísticas da limpeza.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Buscar todos os produtos bloqueados com seus dados
    cursor.execute("""
        SELECT pb.id, pb.produto_id, pb.canal, p.descricao, p.marca
        FROM produto_blocklist pb
        JOIN produtos_sinc p ON pb.produto_id = p.id
    """)
    
    produtos_bloqueados = cursor.fetchall()
    conn.close()
    
    removidos = 0
    mantidos = 0
    ids_para_remover = []
    
    for row in produtos_bloqueados:
        r = dict(row)
        pb_id = r['id']
        canal = r['canal']
        descricao = r['descricao'] or ''
        marca = r['marca'] or ''
        
        # Re-verificar contra a blocklist atual
        bloqueado, _ = verificar_blocklist(canal, descricao, marca)
        
        if not bloqueado:
            # Produto não casa mais com blocklist - marcar para remoção
            ids_para_remover.append(pb_id)
            removidos += 1
        else:
            mantidos += 1
    
    # Remover em lote
    if ids_para_remover:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        placeholders = ','.join(['%s'] * len(ids_para_remover))
        cursor.execute(f"DELETE FROM produto_blocklist WHERE id IN ({placeholders})", tuple(ids_para_remover))
        conn.commit()
        conn.close()
    
    return {
        "removidos": removidos,
        "mantidos": mantidos,
        "total_verificados": removidos + mantidos
    }


# ============================================================
# FUNÇÕES DE IMPORTAÇÃO
# ============================================================

def registrar_importacao(arquivo: str, tipo_modelo: str, qtd_produtos: int, usuario: str = None) -> int:
    """Registra uma importação de planilha."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        INSERT INTO importacoes (arquivo, tipo_modelo, qtd_produtos, usuario)
        VALUES (%s, %s, %s, %s)
    """, (arquivo, tipo_modelo, qtd_produtos, usuario))
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id


def listar_importacoes(limite: int = 50) -> List[Dict[str, Any]]:
    """Lista as últimas importações."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM importacoes ORDER BY data_importacao DESC LIMIT %s
    """, (limite,))
    rows = cursor.fetchall()
    conn.close()
    return list(rows)


# ============================================================
# FUNÇÕES DE LISTA DE PREÇO
# ============================================================

def salvar_lista_preco(caminho_planilha: str, nome_planilha: str, qtd_produtos: int,
                       importacao_id: int = None, usuario: str = None) -> int:
    """Registra uma lista de preço disponível para download (sem gerar CSV ainda)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        INSERT INTO lista_precos (importacao_id, caminho_planilha, nome_planilha, qtd_produtos, usuario)
        VALUES (%s, %s, %s, %s, %s)
    """, (importacao_id, caminho_planilha, nome_planilha, qtd_produtos, usuario))
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id


def atualizar_lista_preco_baixada(id: int, data_inicio: str, data_fim: str, caminho_csv: str, baixado_por: str = None):
    """Marca uma lista de preço como baixada e salva o caminho do CSV."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        UPDATE lista_precos 
        SET data_inicio_vigencia = %s, data_fim_vigencia = %s, caminho_csv = %s, baixado = 1, baixado_por = %s
        WHERE id = %s
    """, (data_inicio, data_fim, caminho_csv, baixado_por, id))
    conn.commit()
    conn.close()


def listar_listas_preco(limite: int = 50) -> List[Dict[str, Any]]:
    """Lista as listas de preço disponíveis."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM lista_precos ORDER BY data_geracao DESC LIMIT %s
    """, (limite,))
    rows = cursor.fetchall()
    conn.close()
    return list(rows)


def buscar_lista_preco(id: int) -> Optional[Dict[str, Any]]:
    """Busca uma lista de preço pelo ID."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM lista_precos WHERE id = %s", (id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def remover_lista_preco(id: int) -> bool:
    """Remove uma lista de preço."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("DELETE FROM lista_precos WHERE id = %s", (id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


# ============================================================
# FUNÇÕES DE USUÁRIOS
# ============================================================

def verificar_usuario(username: str, senha: str) -> Tuple[bool, str, Optional[Dict]]:
    """Verifica credenciais do usuário."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios WHERE username = %s AND ativo = 1", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return False, "Usuário não encontrado", None
    
    if row['senha'] != senha:
        return False, "Senha incorreta", None
    
    # Converter para dict para usar .get()
    user_data = dict(row)
    
    # Verificar status de aprovação
    status = user_data.get('status', 'ATIVO')  # Compatibilidade com dados antigos
    if status == 'PENDENTE':
        return False, "Aguardando aprovação do administrador", None
    elif status == 'INATIVO':
        return False, "Usuário desativado", None
    
    return True, "Login realizado com sucesso!", user_data


# Inicializa o banco ao importar o módulo
if __name__ == "__main__":
    create_tables()
    criar_usuario_inicial()
    print(f"Banco de dados criado em: {DB_PATH}")
