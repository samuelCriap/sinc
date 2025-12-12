"""
Script para migrar tabela usuarios com novos campos
"""
from services.database_sinc import get_connection

conn = get_connection()
cursor = conn.cursor()

# Adicionar colunas que faltam
try:
    cursor.execute('ALTER TABLE usuarios ADD COLUMN nome TEXT')
    print("Coluna 'nome' adicionada!")
except Exception as e:
    print(f"Coluna nome: {e}")

try:
    cursor.execute("ALTER TABLE usuarios ADD COLUMN cargo TEXT DEFAULT 'usuario'")
    print("Coluna 'cargo' adicionada!")
except Exception as e:
    print(f"Coluna cargo: {e}")

try:
    cursor.execute("ALTER TABLE usuarios ADD COLUMN status TEXT DEFAULT 'ATIVO'")
    print("Coluna 'status' adicionada!")
except Exception as e:
    print(f"Coluna status: {e}")

conn.commit()

# Atualizar admin existente
cursor.execute("UPDATE usuarios SET status = 'ATIVO', cargo = 'admin' WHERE username = 'admin'")
conn.commit()
print("Admin atualizado com cargo='admin' e status='ATIVO'!")

conn.close()
print("\nMigração concluída!")
