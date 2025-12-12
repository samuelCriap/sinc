"""
Módulo de acesso ao banco de dados SQLite para o Sistema de Sincronização de SKUs
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

# Caminho do banco de dados (padrão local, pode ser alterado via set_db_path)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "sincronizacao.db")

# Lista de canais suportados
CANAIS = [
    "NETSHOES", "CENTAURO", "TIKTOK", "SHEIN", 
    "RENNER", "SHOPEE", "MELI", "DAFITI", "AMAZON"
]

# Status possíveis de um produto em um canal (vazio = sem status definido)
STATUS_PRODUTO = ["", "ATIVO", "CATALOGANDO", "ERRO"]


def set_db_path(new_path: str):
    """Define um novo caminho para o banco de dados (usado para conexão de rede)."""
    global DB_PATH
    DB_PATH = new_path


def get_db_path() -> str:
    """Retorna o caminho atual do banco de dados."""
    return DB_PATH


def get_connection() -> sqlite3.Connection:
    """Retorna uma conexão com o banco de dados."""
    # Cria pasta apenas se for caminho local
    if not DB_PATH.startswith("\\\\"):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)  # Espera até 10s se banco travado
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")  # Timeout adicional de 5s
    return conn


def create_tables():
    """Cria as tabelas do banco de dados se não existirem."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabela principal de produtos sincronizados
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos_sinc (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_produto TEXT NOT NULL,
            sku TEXT,
            descricao TEXT,
            marca TEXT,
            gtin TEXT,
            categoria TEXT,
            preco REAL,
            importado_por TEXT,
            col_b TEXT,
            col_c TEXT,
            col_i TEXT,
            col_k TEXT,
            col_l TEXT,
            col_m TEXT,
            col_n TEXT,
            col_o TEXT,
            col_p TEXT,
            col_q TEXT,
            col_r TEXT,
            col_ab TEXT,
            col_ac TEXT,
            col_ae TEXT,
            col_af TEXT,
            col_ag TEXT,
            col_ao TEXT,
            col_ap TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(codigo_produto)
        )
    """)
    
    # Status por canal (1 linha por produto/canal)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produto_canal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            canal TEXT NOT NULL,
            status TEXT DEFAULT '',
            bloqueado INTEGER DEFAULT 0,
            motivo_bloqueio TEXT,
            importado_omnie INTEGER DEFAULT 0,
            importado_anymarket INTEGER DEFAULT 0,
            usuario_alteracao TEXT,
            data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (produto_id) REFERENCES produtos_sinc(id),
            UNIQUE(produto_id, canal)
        )
    """)
    # Blocklist por canal - tipos: MARCA (bloqueia toda a marca) ou MODELO (bloqueia modelo específico)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blocklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            canal TEXT NOT NULL,
            termo_bloqueio TEXT NOT NULL,
            tipo TEXT DEFAULT 'MODELO',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(canal, termo_bloqueio)
        )
    """)
    
    # Log de importações
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS importacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            arquivo TEXT,
            tipo_modelo TEXT,
            qtd_produtos INTEGER,
            usuario TEXT,
            data_importacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabela de usuários com cargo e status de aprovação
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL,
            nome TEXT,
            email TEXT,
            cargo TEXT DEFAULT 'usuario',
            status TEXT DEFAULT 'PENDENTE',
            ativo INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabela de listas de preço (vinculada às importações)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lista_precos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            importacao_id INTEGER,
            caminho_planilha TEXT NOT NULL,
            nome_planilha TEXT,
            qtd_produtos INTEGER,
            data_inicio_vigencia TEXT,
            data_fim_vigencia TEXT,
            caminho_csv TEXT,
            baixado INTEGER DEFAULT 0,
            usuario TEXT,
            data_geracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabela de produtos bloqueados por canal (não aparecem em produto_canal, só aqui)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produto_blocklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            canal TEXT NOT NULL,
            termo_bloqueado TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (produto_id) REFERENCES produtos_sinc(id),
            UNIQUE(produto_id, canal)
        )
    """)
    
    # Tabela de log de atividades
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS log_atividades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            acao TEXT NOT NULL,
            detalhes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabela de controle de chamados
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chamados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT NOT NULL,
            prioridade TEXT DEFAULT 'MÉDIA',
            canal TEXT,
            observacoes TEXT,
            link TEXT,
            criado_por TEXT NOT NULL,
            na_lixeira INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabela de histórico de alterações por produto
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_produto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL,
            campo TEXT NOT NULL,
            valor_antigo TEXT,
            valor_novo TEXT,
            usuario TEXT NOT NULL,
            canal TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Índices para histórico
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_historico_sku ON historico_produto(sku)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_historico_created ON historico_produto(created_at)")
    
    # ══════════════════════════════════════════════════════════════
    # MIGRAÇÕES - Adiciona colunas novas se não existirem
    # ══════════════════════════════════════════════════════════════
    try:
        cursor.execute("ALTER TABLE produto_canal ADD COLUMN cod_marketplace TEXT")
    except sqlite3.OperationalError:
        pass  # Coluna já existe
    
    conn.commit()
    conn.close()


def criar_usuario_inicial():
    """Cria um usuário admin inicial se não existir."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    count = cursor.fetchone()[0]
    
    if count == 0:
        cursor.execute(
            "INSERT INTO usuarios (username, senha, nome, email, cargo, status) VALUES (?, ?, ?, ?, ?, ?)",
            ("admin", "admin123", "Administrador", "admin@sistema.com", "admin", "ATIVO")
        )
        conn.commit()
    
    conn.close()


def cadastrar_usuario(username: str, senha: str, nome: str, email: str) -> tuple:
    """Cadastra um novo usuário com status PENDENTE."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO usuarios (username, senha, nome, email, cargo, status)
            VALUES (?, ?, ?, ?, 'usuario', 'PENDENTE')
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
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, nome, email, created_at FROM usuarios WHERE status = 'PENDENTE'")
    result = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return result


def listar_todos_usuarios() -> list:
    """Lista todos os usuários."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, nome, email, cargo, status, created_at FROM usuarios")
    result = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return result


def aprovar_usuario(user_id: int, cargo: str = "usuario") -> bool:
    """Aprova um usuário pendente."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET status = 'ATIVO', cargo = ? WHERE id = ?", (cargo, user_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def rejeitar_usuario(user_id: int) -> bool:
    """Rejeita um usuário pendente (deleta)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def alterar_cargo_usuario(user_id: int, novo_cargo: str) -> bool:
    """Altera o cargo de um usuário."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET cargo = ? WHERE id = ?", (novo_cargo, user_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def bloquear_usuario(user_id: int, bloquear: bool = True) -> bool:
    """Bloqueia (status=INATIVO) ou desbloqueia (status=ATIVO) um usuário."""
    status = "INATIVO" if bloquear else "ATIVO"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET status = ? WHERE id = ?", (status, user_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def remover_usuario(user_id: int) -> bool:
    """Remove um usuário permanentemente do banco de dados."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
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
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO log_atividades (usuario, acao, detalhes)
            VALUES (?, ?, ?)
        """, (usuario, acao, detalhes))
        conn.commit()
        conn.close()
    except Exception:
        pass  # Não falhar se log não funcionar


def listar_logs(limite: int = 100) -> list:
    """Lista os últimos registros de log."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT usuario, acao, detalhes, created_at 
        FROM log_atividades 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (limite,))
    result = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return result


def limpar_logs(dias: int = 30):
    """Remove logs mais antigos que X dias."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM log_atividades 
        WHERE created_at < datetime('now', '-' || ? || ' days')
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
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO historico_produto (sku, campo, valor_antigo, valor_novo, usuario, canal)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (sku, campo, str(valor_antigo) if valor_antigo else None, 
              str(valor_novo) if valor_novo else None, usuario, canal))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Histórico] Erro ao registrar: {e}")


def listar_historico_produto(sku: str, limite: int = 50) -> list:
    """Lista histórico de alterações de um produto."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, sku, campo, valor_antigo, valor_novo, usuario, canal, created_at
        FROM historico_produto WHERE sku = ? ORDER BY created_at DESC LIMIT ?
    """, (sku, limite))
    result = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return result


def listar_historico_geral(limite: int = 100) -> list:
    """Lista histórico geral de alterações."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, sku, campo, valor_antigo, valor_novo, usuario, canal, created_at
        FROM historico_produto ORDER BY created_at DESC LIMIT ?
    """, (limite,))
    result = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return result


# ============================================================
# FUNÇÕES DE CHAMADOS
# ============================================================

def criar_chamado(numero: str, prioridade: str, canal: str, observacoes: str, link: str, criado_por: str) -> int:
    """Cria um novo chamado."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chamados (numero, prioridade, canal, observacoes, link, criado_por)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (numero, prioridade, canal, observacoes, link, criado_por))
    conn.commit()
    chamado_id = cursor.lastrowid
    conn.close()
    return chamado_id


def listar_chamados(na_lixeira: bool = False) -> list:
    """Lista chamados ativos ou na lixeira."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, numero, prioridade, canal, observacoes, link, criado_por, na_lixeira, created_at
        FROM chamados
        WHERE na_lixeira = ?
        ORDER BY 
            CASE prioridade 
                WHEN 'URGENTE' THEN 1 
                WHEN 'ALTA' THEN 2 
                WHEN 'MÉDIA' THEN 3 
                WHEN 'BAIXA' THEN 4 
            END,
            created_at DESC
    """, (1 if na_lixeira else 0,))
    result = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return result


def atualizar_chamado(chamado_id: int, numero: str, prioridade: str, canal: str, observacoes: str, link: str) -> bool:
    """Atualiza um chamado existente."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE chamados 
        SET numero = ?, prioridade = ?, canal = ?, observacoes = ?, link = ?
        WHERE id = ?
    """, (numero, prioridade, canal, observacoes, link, chamado_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def mover_para_lixeira(chamado_id: int) -> bool:
    """Move um chamado para a lixeira."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE chamados SET na_lixeira = 1 WHERE id = ?", (chamado_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def restaurar_chamado(chamado_id: int) -> bool:
    """Restaura um chamado da lixeira."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE chamados SET na_lixeira = 0 WHERE id = ?", (chamado_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def excluir_chamado_permanente(chamado_id: int) -> bool:
    """Exclui permanentemente um chamado."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chamados WHERE id = ?", (chamado_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


# ============================================================
# FUNÇÕES DE PRODUTOS
# ============================================================

def inserir_produto(codigo_produto: str, sku: str = None, descricao: str = None,
                    marca: str = None, gtin: str = None, categoria: str = None,
                    preco: float = None, importado_por: str = None,
                    **kwargs) -> int:
    """Insere um produto na tabela produtos_sinc. Retorna o ID do produto."""
    conn = get_connection()
    cursor = conn.cursor()
    
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            codigo_produto, sku, descricao, marca, gtin, categoria, preco, importado_por,
            col_b, col_c, col_i, col_k, col_l, col_m, col_n, col_o, col_p, col_q, col_r,
            col_ab, col_ac, col_ae, col_af, col_ag, col_ao, col_ap
        ))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        # Produto já existe, retorna ID existente
        cursor.execute("SELECT id FROM produtos_sinc WHERE codigo_produto = ?", (codigo_produto,))
        row = cursor.fetchone()
        return row['id'] if row else None
    finally:
        conn.close()


def buscar_produto_por_codigo(codigo_produto: str) -> Optional[Dict[str, Any]]:
    """Busca um produto pelo código."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM produtos_sinc WHERE codigo_produto = ?", (codigo_produto,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def listar_produtos(limite: int = 1000) -> List[Dict[str, Any]]:
    """Lista todos os produtos."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM produtos_sinc ORDER BY id DESC LIMIT ?", (limite,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# Função duplicada removida
def listar_produtos_canal_old(canal: str) -> List[Dict[str, Any]]:
    return []


def atualizar_produto_campo(produto_id: int, campo: str, valor: str):
    """Atualiza um campo específico de um produto."""
    campos_permitidos = ['codigo_produto', 'sku', 'descricao', 'marca', 'gtin', 'categoria']
    if campo not in campos_permitidos:
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        UPDATE produtos_sinc 
        SET {campo} = ?, updated_at = ?
        WHERE id = ?
    """, (valor, datetime.now(), produto_id))
    conn.commit()
    conn.close()
    return True


def remover_produto_canal(produto_id: int, canal: str) -> bool:
    """Remove um produto de um canal específico."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM produto_canal 
        WHERE produto_id = ? AND canal = ?
    """, (produto_id, canal.upper()))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


# ============================================================
# FUNÇÕES DE PRODUTO_BLOCKLIST
# ============================================================

def registrar_produto_blocklist(produto_id: int, canal: str, termo_bloqueado: str = None) -> bool:
    """Registra um produto como bloqueado para um canal específico (não insere em produto_canal)."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO produto_blocklist (produto_id, canal, termo_bloqueado)
            VALUES (?, ?, ?)
        """, (produto_id, canal.upper(), termo_bloqueado))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def listar_produtos_bloqueados(produto_id: int) -> Dict[str, str]:
    """Retorna um dicionário {canal: termo_bloqueado} dos canais bloqueados para um produto."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT canal, termo_bloqueado FROM produto_blocklist WHERE produto_id = ?
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
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO produto_canal (produto_id, canal, status, bloqueado, motivo_bloqueio, usuario_alteracao)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (produto_id, canal.upper(), status, 1 if bloqueado else 0, motivo_bloqueio, usuario))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Já existe
        return False
    finally:
        conn.close()


def atualizar_importacao_externa(produto_id: int, canal: str, omnie: bool = None, anymarket: bool = None):
    """Atualiza checkboxes de importação externa (Omnie One / AnyMarket)."""
    conn = get_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if omnie is not None:
        updates.append("importado_omnie = ?")
        params.append(1 if omnie else 0)
    
    if anymarket is not None:
        updates.append("importado_anymarket = ?")
        params.append(1 if anymarket else 0)
    
    if updates:
        params.extend([produto_id, canal.upper()])
        cursor.execute(f"""
            UPDATE produto_canal 
            SET {', '.join(updates)}, data_alteracao = CURRENT_TIMESTAMP
            WHERE produto_id = ? AND canal = ?
        """, params)
        conn.commit()
    
    conn.close()


def marcar_importacao_externa_em_massa(produto_ids: List[int], campo: str, valor: bool) -> int:
    """
    Atualiza em massa flags de importação externa.
    campo: 'omnie' ou 'anymarket'
    """
    conn = get_connection()
    cursor = conn.cursor()
    
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
            placeholders = ','.join(['?'] * len(batch))
            
            cursor.execute(f"""
                UPDATE produto_canal 
                SET {coluna} = ?, data_alteracao = CURRENT_TIMESTAMP
                WHERE produto_id IN ({placeholders})
            """, [val_int] + batch)
            
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
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE produto_canal 
        SET status = ?, usuario_alteracao = ?, data_alteracao = ?
    WHERE produto_id = ? AND canal = ?
    """, (novo_status, usuario, datetime.now(), produto_id, canal.upper()))
    
    # Se o novo status não é blocklist, remove da tabela produto_blocklist
    if novo_status and novo_status.upper() != 'BLOCKLIST':
        cursor.execute("""
            DELETE FROM produto_blocklist 
            WHERE produto_id = ? AND canal = ?
        """, (produto_id, canal.upper()))
    
    conn.commit()
    conn.close()


def atualizar_status_em_massa(canal: str, atualizacoes: Dict[str, str], usuario: str = None) -> int:
    """
    Atualiza status de múltiplos produtos em um canal usando SKU ou codigo_produto.
    atualizacoes: dict {sku: novo_status}
    """
    conn = get_connection()
    cursor = conn.cursor()
    
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
            placeholders = ','.join(['?'] * len(batch))
            
            # Buscar por SKU ou codigo_produto
            cursor.execute(f"""
                SELECT id, sku, codigo_produto FROM produtos_sinc 
                WHERE sku IN ({placeholders}) OR codigo_produto IN ({placeholders})
            """, batch + batch)
            
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
                SET status = ?, usuario_alteracao = ?, data_alteracao = CURRENT_TIMESTAMP
                WHERE produto_id = ? AND canal = ?
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
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE produto_canal 
        SET status = ?, motivo_bloqueio = ?, usuario_alteracao = ?, data_alteracao = ?
        WHERE produto_id = ? AND canal = ?
    """, (novo_status, motivo_erro, usuario, datetime.now(), produto_id, canal.upper()))
    
    # Se o novo status não é blocklist, remove da tabela produto_blocklist
    if novo_status and novo_status.upper() != 'BLOCKLIST':
        cursor.execute("""
            DELETE FROM produto_blocklist 
            WHERE produto_id = ? AND canal = ?
        """, (produto_id, canal.upper()))
    
    conn.commit()
    conn.close()


def atualizar_status_em_massa_com_erro(canal: str, atualizacoes: Dict[str, Tuple[str, str]], usuario: str = None) -> int:
    """
    Atualiza status de múltiplos produtos em um canal usando SKU ou codigo_produto.
    atualizacoes: dict {sku: (novo_status, motivo_erro)}
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    count = 0
    
    try:
        # Busca IDs dos SKUs para update direto (busca em sku E codigo_produto)
        skus = list(atualizacoes.keys())
        
        # Dividir em lotes de 400 para evitar limite de variáveis SQL
        BATCH_SIZE = 400
        mapa_sku_id = {}
        
        for i in range(0, len(skus), BATCH_SIZE):
            batch = skus[i:i + BATCH_SIZE]
            placeholders = ','.join(['?'] * len(batch))
            
            # Buscar por SKU ou codigo_produto
            cursor.execute(f"""
                SELECT id, sku, codigo_produto FROM produtos_sinc 
                WHERE sku IN ({placeholders}) OR codigo_produto IN ({placeholders})
            """, batch + batch)
            
            for row in cursor.fetchall():
                if row['sku']: mapa_sku_id[row['sku']] = row['id']
                if row['codigo_produto']: mapa_sku_id[row['codigo_produto']] = row['id']
        
        print(f"[Netshoes] SKUs encontrados no banco: {len(mapa_sku_id)} de {len(skus)}")
        
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
                campos = ["status = ?", "usuario_alteracao = ?", "data_alteracao = CURRENT_TIMESTAMP"]
                params = [status, usuario]
                
                if motivo:
                    campos.append("motivo_bloqueio = ?")
                    params.append(motivo)
                
                if cod_mp:
                    campos.append("cod_marketplace = ?")
                    params.append(cod_mp)
                
                params.append(pid)
                params.append(canal.upper())
                
                cursor.execute(f"""
                    UPDATE produto_canal 
                    SET {', '.join(campos)}
                    WHERE produto_id = ? AND canal = ?
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
    cursor = conn.cursor()
    
    query = """
        SELECT p.*, pc.canal, pc.status, pc.bloqueado, pc.motivo_bloqueio, pc.data_alteracao, pc.cod_marketplace,
               p.col_b, p.col_c, p.col_i, p.col_k, p.col_l, p.col_m, p.col_n, p.col_o, p.col_p, p.col_q, p.col_r,
               p.col_ab, p.col_ac, p.col_ae, p.col_af, p.col_ag, p.col_ao, p.col_ap
        FROM produtos_sinc p
        JOIN produto_canal pc ON p.id = pc.produto_id
        WHERE pc.canal = ?
    """
    params = [canal.upper()]
    
    if status:
        query += " AND pc.status = ?"
        params.append(status)
    
    query += " ORDER BY p.id DESC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def contar_produtos_por_status_canal(canal: str) -> Dict[str, int]:
    """Conta produtos por status em um canal."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT status, COUNT(*) as qtd
        FROM produto_canal
        WHERE canal = ?
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
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO blocklist (canal, termo_bloqueio, tipo)
            VALUES (?, ?, ?)
        """, (canal.upper(), termo, tipo))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def listar_blocklist(canal: str = None) -> List[Dict[str, Any]]:
    """Lista itens da blocklist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    if canal:
        cursor.execute("SELECT * FROM blocklist WHERE canal = ? ORDER BY termo_bloqueio", (canal.upper(),))
    else:
        cursor.execute("SELECT * FROM blocklist ORDER BY canal, termo_bloqueio")
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


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
    cursor = conn.cursor()
    cursor.execute("DELETE FROM blocklist WHERE id = ?", (id,))
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
    cursor = conn.cursor()
    
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
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(ids_para_remover))
        cursor.execute(f"DELETE FROM produto_blocklist WHERE id IN ({placeholders})", ids_para_remover)
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
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO importacoes (arquivo, tipo_modelo, qtd_produtos, usuario)
        VALUES (?, ?, ?, ?)
    """, (arquivo, tipo_modelo, qtd_produtos, usuario))
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id


def listar_importacoes(limite: int = 50) -> List[Dict[str, Any]]:
    """Lista as últimas importações."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM importacoes ORDER BY data_importacao DESC LIMIT ?
    """, (limite,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ============================================================
# FUNÇÕES DE LISTA DE PREÇO
# ============================================================

def salvar_lista_preco(caminho_planilha: str, nome_planilha: str, qtd_produtos: int,
                       importacao_id: int = None, usuario: str = None) -> int:
    """Registra uma lista de preço disponível para download (sem gerar CSV ainda)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO lista_precos (importacao_id, caminho_planilha, nome_planilha, qtd_produtos, usuario)
        VALUES (?, ?, ?, ?, ?)
    """, (importacao_id, caminho_planilha, nome_planilha, qtd_produtos, usuario))
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id


def atualizar_lista_preco_baixada(id: int, data_inicio: str, data_fim: str, caminho_csv: str):
    """Marca uma lista de preço como baixada e salva o caminho do CSV."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE lista_precos 
        SET data_inicio_vigencia = ?, data_fim_vigencia = ?, caminho_csv = ?, baixado = 1
        WHERE id = ?
    """, (data_inicio, data_fim, caminho_csv, id))
    conn.commit()
    conn.close()


def listar_listas_preco(limite: int = 50) -> List[Dict[str, Any]]:
    """Lista as listas de preço disponíveis."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM lista_precos ORDER BY data_geracao DESC LIMIT ?
    """, (limite,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def buscar_lista_preco(id: int) -> Optional[Dict[str, Any]]:
    """Busca uma lista de preço pelo ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lista_precos WHERE id = ?", (id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def remover_lista_preco(id: int) -> bool:
    """Remove uma lista de preço."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM lista_precos WHERE id = ?", (id,))
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
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE username = ? AND ativo = 1", (username,))
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
