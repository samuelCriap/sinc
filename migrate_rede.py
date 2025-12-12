"""
Script para verificar e corrigir tabela usuarios no banco de REDE
"""
import sqlite3

# Banco na rede
db_path = r"\\192.168.0.126\Sincronizacao\sincronizacao.db"

print(f"Conectando a: {db_path}")
conn = sqlite3.connect(db_path, timeout=10)
cursor = conn.cursor()

# Ver estrutura atual
cursor.execute("PRAGMA table_info(usuarios)")
cols = cursor.fetchall()
print("\nColunas atuais:")
col_names = []
for c in cols:
    print(f"  - {c[1]} ({c[2]})")
    col_names.append(c[1])

# Ver dados atuais
cursor.execute("SELECT * FROM usuarios")
rows = cursor.fetchall()
print(f"\nUsuários existentes: {len(rows)}")
for r in rows:
    print(f"  {r}")

# Adicionar colunas que faltam
if 'nome' not in col_names:
    try:
        cursor.execute('ALTER TABLE usuarios ADD COLUMN nome TEXT')
        print("\nColuna 'nome' adicionada!")
    except Exception as e:
        print(f"Erro ao adicionar nome: {e}")

if 'cargo' not in col_names:
    try:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN cargo TEXT DEFAULT 'usuario'")
        print("Coluna 'cargo' adicionada!")
    except Exception as e:
        print(f"Erro ao adicionar cargo: {e}")

if 'status' not in col_names:
    try:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN status TEXT DEFAULT 'ATIVO'")
        print("Coluna 'status' adicionada!")
    except Exception as e:
        print(f"Erro ao adicionar status: {e}")

conn.commit()

# Atualizar usuarios existentes com valores padrão
cursor.execute("UPDATE usuarios SET cargo = 'admin', status = 'ATIVO' WHERE cargo IS NULL OR status IS NULL")
conn.commit()

conn.close()
print("\nConcluído!")
