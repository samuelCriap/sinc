"""
Módulo para importação de planilhas de produtos (modelo Columbia e outros)
"""
import os
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from services.database_sinc import (
    inserir_produto, adicionar_produto_canal, registrar_importacao,
    verificar_blocklist, buscar_produto_por_codigo, registrar_produto_blocklist, CANAIS
)


# Mapeamentos conhecidos de modelos de planilha
MODELOS_CONHECIDOS = {
    "COLUMBIA": {
        "identificador_coluna": "CodigoProduto",
        "colunas": {
            "codigo_produto": "CodigoProduto",
            "sku": "SKU",
            "nome_produto": "NomeProduto",  # Campo com o nome do produto!
            "descricao": "Descrição",
            "marca": "Marca",
            "gtin": "GTIN",
            "categoria": "Categoria",
            "preco": "Preço"
        }
    },
    "GENERICO": {
        "identificador_coluna": None,
        "colunas": {
            "codigo_produto": ["CodigoProduto", "Codigo", "SKU", "Código", "codigo"],
            "sku": ["SKU", "Sku", "sku"],
            "nome_produto": ["NomeProduto", "Nome", "Produto", "NomeProduto", "nome_produto"],
            "descricao": ["Descrição", "Descricao", "descricao"],
            "marca": ["Marca", "Brand", "marca"],
            "gtin": ["GTIN", "EAN", "gtin", "ean"],
            "categoria": ["Categoria", "Category", "categoria"],
            "preco": ["Preço", "Preco", "Price", "preco"]
        }
    }
}


def detectar_modelo_planilha(df: pd.DataFrame) -> str:
    """Detecta qual modelo de planilha está sendo importado."""
    colunas = [str(col).strip() for col in df.columns]
    
    # Verifica modelo Columbia
    if "CodigoProduto" in colunas:
        return "COLUMBIA"
    
    return "GENERICO"


def mapear_colunas(df: pd.DataFrame, modelo: str) -> Dict[str, str]:
    """Mapeia as colunas da planilha para os campos do banco."""
    colunas_df = [str(col).strip() for col in df.columns]
    mapeamento = {}
    
    if modelo == "COLUMBIA":
        config = MODELOS_CONHECIDOS["COLUMBIA"]["colunas"]
        for campo, coluna in config.items():
            if coluna in colunas_df:
                mapeamento[campo] = coluna
    else:
        # Modelo genérico - busca por várias possibilidades
        config = MODELOS_CONHECIDOS["GENERICO"]["colunas"]
        for campo, possiveis in config.items():
            for possivel in possiveis:
                if possivel in colunas_df:
                    mapeamento[campo] = possivel
                    break
    
    return mapeamento


def excel_col_to_index(col_str: str) -> int:
    """Converte letra de coluna Excel (ex: 'BC') para índice 0-based."""
    col_str = col_str.upper().strip()
    idx = 0
    for char in col_str:
        if 'A' <= char <= 'Z':
            idx = idx * 26 + (ord(char) - ord('A') + 1)
    return idx - 1

def importar_planilha_produtos(
    caminho_arquivo: str,
    canais_destino: List[str] = None,
    usuario: str = None,
    aba: str = None
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Importa uma planilha de produtos.
    """
    if not os.path.exists(caminho_arquivo):
        return False, f"Arquivo não encontrado: {caminho_arquivo}", {}
    
    try:
        # Carrega o arquivo Excel
        # Lê cabeçalho na linha 0 (padrão) para ter acesso por iloc e nomes
        xl = pd.ExcelFile(caminho_arquivo)
        
        # Determina qual aba usar
        if aba and aba in xl.sheet_names:
            nome_aba = aba
        elif "PRODUTOS" in xl.sheet_names:
            nome_aba = "PRODUTOS"
        else:
            nome_aba = xl.sheet_names[0]
        
        df = xl.parse(nome_aba)
        
        # Detecta o modelo
        modelo = detectar_modelo_planilha(df)
        
        # Mapeia as colunas (A, F, J são mapeadas por nome se possível, se não, fallback)
        mapeamento = mapear_colunas(df, modelo)
        
        if "codigo_produto" not in mapeamento:
            # Tentar fallback para Coluna A (0) se não achar header
            if len(df.columns) > 0:
                print("Aviso: Header não encontrado, tentando coluna A como SKU")
                # Não temos como saber se A é SKU sem header, mas vamos seguir a lógica atual
                map_manual = True
            else:
                return False, "Não foi possível identificar a coluna de código do produto", {}
        
        # Define canais destino
        if canais_destino is None:
            canais_destino = CANAIS
        
        # Estatísticas
        stats = {
            "total_linhas": len(df),
            "produtos_importados": 0,
            "produtos_existentes": 0,
            "produtos_bloqueados": {},
            "erros": 0
        }
        
        for canal in canais_destino:
            stats["produtos_bloqueados"][canal] = 0
        
        # Configurar índices das colunas extras
        # Lista: B, C, I, K, L, M, N, O, P, Q, E, AB, AC, AE, AF, AG, AO, AP
        COLUNAS_EXTRAS = {
            "col_b": "B", "col_c": "C", "col_i": "I", "col_k": "K", "col_l": "L", 
            "col_m": "M", "col_n": "N", "col_o": "O", "col_p": "P", "col_q": "Q", 
            "col_r": "R", "col_ab": "AB", "col_ac": "AC", "col_ae": "AE", 
            "col_af": "AF", "col_ag": "AG", "col_ao": "AO", "col_ap": "AP"
        }
        idx_extras = {k: excel_col_to_index(v) for k, v in COLUNAS_EXTRAS.items()}
        
        # Processa cada linha
        for idx, row in df.iterrows():
            try:
                # Extrai dados mapeados
                codigo = str(row[mapeamento["codigo_produto"]]).strip() if "codigo_produto" in mapeamento and pd.notna(row[mapeamento["codigo_produto"]]) else None
                
                # Fallback: Se não mapeou por nome, tenta coluna A (0)
                if not codigo and len(df.columns) > 0:
                     codigo = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else None

                if not codigo or codigo.lower() == "nan":
                    continue
                
                # SKU
                sku = codigo
                if "sku" in mapeamento and pd.notna(row.get(mapeamento["sku"])):
                    sku_val = str(row[mapeamento["sku"]]).strip()
                    if sku_val: sku = sku_val
                
                # Nome / Descrição
                nome_produto = None
                if "nome_produto" in mapeamento:
                    col_nome = mapeamento["nome_produto"]
                    if col_nome in df.columns and pd.notna(row[col_nome]):
                        nome_produto = str(row[col_nome]).strip()
                elif len(df.columns) > 5: # Fallback Coluna F (5)
                     val = row.iloc[5]
                     if pd.notna(val): nome_produto = str(val).strip()

                descricao = nome_produto
                if "descricao" in mapeamento:
                    col_desc = mapeamento["descricao"]
                    if col_desc in df.columns and pd.notna(row[col_desc]):
                        descricao = str(row[col_desc]).strip()
                
                # Marca
                marca = None
                if "marca" in mapeamento:
                     if pd.notna(row.get(mapeamento["marca"])):
                         marca = str(row[mapeamento["marca"]]).strip()
                elif len(df.columns) > 9: # Fallback Coluna J (9)
                     val = row.iloc[9]
                     if pd.notna(val): marca = str(val).strip()

                gtin = str(row[mapeamento["gtin"]]).strip() if "gtin" in mapeamento and pd.notna(row.get(mapeamento.get("gtin"))) else None
                categoria = str(row[mapeamento["categoria"]]).strip() if "categoria" in mapeamento and pd.notna(row.get(mapeamento.get("categoria"))) else None
                preco = float(row[mapeamento["preco"]]) if "preco" in mapeamento and pd.notna(row.get(mapeamento.get("preco"))) else None
                
                # Extrair colunas extras por índice
                dados_extras = {}
                for campo, col_idx_val in idx_extras.items():
                    if col_idx_val < len(df.columns):
                        val = row.iloc[col_idx_val]
                        dados_extras[campo] = str(val).strip() if pd.notna(val) else ""
                    else:
                        dados_extras[campo] = ""

                # Verifica se produto já existe
                produto_existente = buscar_produto_por_codigo(codigo)
                
                if produto_existente:
                    produto_id = produto_existente["id"]
                    stats["produtos_existentes"] += 1
                else:
                    # Insere o produto com extras
                    produto_id = inserir_produto(
                        codigo_produto=codigo,
                        sku=sku,
                        descricao=descricao,
                        marca=marca,
                        gtin=gtin,
                        categoria=categoria,
                        preco=preco,
                        importado_por=usuario,
                        **dados_extras  # Passa colunas extras
                    )
                    stats["produtos_importados"] += 1
                
                # Adiciona aos canais (verificando blocklist)
                for canal in canais_destino:
                    bloqueado, termo = verificar_blocklist(canal, nome_produto or '', marca)
                    
                    if bloqueado:
                        stats["produtos_bloqueados"][canal] += 1
                        registrar_produto_blocklist(produto_id, canal, termo)
                    else:
                        adicionar_produto_canal(
                            produto_id=produto_id,
                            canal=canal,
                            status="",
                            bloqueado=False,
                            usuario=usuario
                        )
                
            except Exception as e:
                stats["erros"] += 1
                continue
        
        # Registra a importação
        importacao_id = registrar_importacao(
            arquivo=os.path.basename(caminho_arquivo),
            tipo_modelo=modelo,
            qtd_produtos=stats["produtos_importados"],
            usuario=usuario
        )
        
        # Lista de preço será registrada pelo chamador (app_flet) para consolidar múltiplos arquivos
        
        mensagem = f"Importação concluída! {stats['produtos_importados']} novos produtos, {stats['produtos_existentes']} já existentes."
        return True, mensagem, stats
        
    except Exception as e:
        return False, f"Erro ao importar: {str(e)}", {}


def importar_blocklist_planilha(
    caminho_arquivo: str,
    aba: str = "BLOCK"
) -> Tuple[bool, str, int]:
    """
    Importa a blocklist de uma planilha de sincronização.
    
    Args:
        caminho_arquivo: Caminho para o arquivo Excel
        aba: Nome da aba com a blocklist
    
    Returns:
        Tuple (sucesso, mensagem, qtd_importados)
    """
    from services.database_sinc import adicionar_blocklist
    
    if not os.path.exists(caminho_arquivo):
        return False, f"Arquivo não encontrado: {caminho_arquivo}", 0
    
    try:
        xl = pd.ExcelFile(caminho_arquivo)
        
        if aba not in xl.sheet_names:
            return False, f"Aba '{aba}' não encontrada", 0
        
        df = xl.parse(aba)
        
        # A estrutura da BLOCK tem colunas por canal
        qtd_importados = 0
        
        for col in df.columns:
            canal = str(col).upper().strip()
            if canal in CANAIS:
                for idx, row in df.iterrows():
                    valor = row[col]
                    if pd.notna(valor) and str(valor).strip():
                        termo = str(valor).strip()
                        if adicionar_blocklist(canal, termo, "PALAVRA"):
                            qtd_importados += 1
        
        return True, f"Blocklist importada! {qtd_importados} termos adicionados.", qtd_importados
        
    except Exception as e:
        return False, f"Erro ao importar blocklist: {str(e)}", 0


if __name__ == "__main__":
    # Teste de importação
    print("Testando importação de ColumbiaModelo.xls...")
    
    sucesso, msg, stats = importar_planilha_produtos(
        caminho_arquivo=r"c:\Users\marco\PycharmProjects\Sincronização\ColumbiaModelo.xls",
        canais_destino=["NETSHOES", "CENTAURO"],
        usuario="teste"
    )
    
    print(f"Sucesso: {sucesso}")
    print(f"Mensagem: {msg}")
    print(f"Estatísticas: {stats}")
