"""
Análise focada na coluna VALOR problemática
"""
import pandas as pd
import openpyxl

# Analisar com openpyxl para ver formatação real
print("=" * 60)
print("ANÁLISE DETALHADA - COLUNA 51 (VALOR[2][51])")
print("=" * 60)

# Arquivo CERTO
wb_certo = openpyxl.load_workbook('certo.xlsx')
ws_certo = wb_certo.active

# Arquivo ERRADO  
wb_errado = openpyxl.load_workbook('errado.xlsx')
ws_errado = wb_errado.active

print(f"\nColunas totais certo: {ws_certo.max_column}")
print(f"Colunas totais errado: {ws_errado.max_column}")

# Coluna 51 = AY (A=1, B=2, ..., Z=26, AA=27, ..., AY=51)
col_51 = 51

print(f"\n--- Coluna 51 (AY) ---")
print(f"\nCABEÇALHO (linha 1):")
print(f"  Certo:  {ws_certo.cell(1, col_51).value}")
print(f"  Errado: {ws_errado.cell(1, col_51).value}")

print(f"\nCÉLULA B2 (linha 2, coluna 51 = VALOR[2][51]):")
cell_certo = ws_certo.cell(2, col_51)
cell_errado = ws_errado.cell(2, col_51)

print(f"  Certo:")
print(f"    Valor: {repr(cell_certo.value)}")
print(f"    Tipo Python: {type(cell_certo.value).__name__}")
print(f"    Número formato: {cell_certo.number_format}")

print(f"\n  Errado:")
print(f"    Valor: {repr(cell_errado.value)}")
print(f"    Tipo Python: {type(cell_errado.value).__name__}")  
print(f"    Número formato: {cell_errado.number_format}")

# Verificar todas as colunas "VALOR" 
print("\n" + "=" * 60)
print("TODAS AS COLUNAS COM 'VALOR' NO NOME")
print("=" * 60)

for col in range(1, min(ws_certo.max_column + 1, 150)):
    header = ws_certo.cell(1, col).value
    if header and 'VALOR' in str(header).upper():
        val_certo = ws_certo.cell(2, col)
        val_errado = ws_errado.cell(2, col)
        print(f"\nCol {col} - {header}:")
        print(f"  Certo:  {repr(val_certo.value)[:40]} | tipo: {type(val_certo.value).__name__} | fmt: {val_certo.number_format}")
        print(f"  Errado: {repr(val_errado.value)[:40]} | tipo: {type(val_errado.value).__name__} | fmt: {val_errado.number_format}")

wb_certo.close()
wb_errado.close()
