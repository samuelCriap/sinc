"""
Relatório de Saldo Geral - Comparação de estoque KPL vs Canais
"""
import os
import zipfile
import tempfile
import pandas as pd
from datetime import datetime
from typing import Dict, Tuple, Optional


# Configuração de colunas por canal
CONFIG_CANAIS = {
    'SHOPEE': {
        'sku_col': 5,      # Coluna F (índice 5)
        'estoque_col': 8,  # Coluna I (índice 8)
        'nome': 'Shopee',
        'requer_zip': True,
        'remove_dashes': False,
    },
    'SHEIN': {
        'sku_col': 17,     # Coluna R (índice 17)
        'estoque_col': 36, # Coluna AK (índice 36)
        'nome': 'Shein',
        'requer_zip': False,
        'remove_dashes': False,
    },
    'RENNER': {
        'sku_col': 5,      # Coluna F (índice 5)
        'estoque_col': 6,  # Coluna G (índice 6)
        'nome': 'Renner',
        'requer_zip': False,
        'remove_dashes': True,  # SKU no canal não tem traços (3128-01-G → 312801G)
    },
    'DAFITI': {
        'sku_col': 19,     # Coluna T (índice 19)
        'estoque_col': 22, # Coluna W (índice 22)
        'nome': 'Dafiti',
        'requer_zip': False,
        'remove_dashes': False,
    },
    'NETSHOES': {
        'sku_col': 0,      # Coluna A (índice 0)
        'estoque_col': 1,  # Coluna B (índice 1)
        'nome': 'Netshoes',
        'requer_zip': False,
        'remove_dashes': False,
    },
    # Outros canais podem ser adicionados aqui futuramente
}

# Configuração KPL
CONFIG_KPL = {
    'sku_col': 1,       # Coluna B (índice 1)
    'nome_col': 2,      # Coluna C (índice 2)
    'estoque_col': 7,   # Coluna H (índice 7)
}


def consolidar_shopee_zip(zip_path: str) -> pd.DataFrame:
    """
    Consolida as 8 planilhas do ZIP Shopee em um único DataFrame.
    - Usa planilha 1 como base
    - Copia dados das planilhas 2-8 (a partir da linha 7) para a planilha 1
    
    Args:
        zip_path: Caminho do arquivo ZIP
        
    Returns:
        DataFrame consolidado com todos os dados
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Extrair ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        def ler_excel_robusto(caminho):
            """Tenta ler Excel com múltiplos engines."""
            for engine in ['calamine', 'openpyxl', 'xlrd']:
                try:
                    return pd.read_excel(caminho, header=None, engine=engine)
                except:
                    continue
            raise ValueError(f"Não foi possível ler {os.path.basename(caminho)}")
        
        # Carregar planilha base (1.xlsx)
        base_path = os.path.join(temp_dir, '1.xlsx')
        if not os.path.exists(base_path):
            raise FileNotFoundError("Arquivo 1.xlsx não encontrado no ZIP")
        
        df_base = ler_excel_robusto(base_path)
        
        # Consolidar planilhas 2-8
        for i in range(2, 9):
            file_path = os.path.join(temp_dir, f'{i}.xlsx')
            if os.path.exists(file_path):
                try:
                    df_extra = ler_excel_robusto(file_path)
                    # Pegar dados a partir da linha 7 (índice 6)
                    if len(df_extra) > 6:
                        dados_extra = df_extra.iloc[6:]
                        df_base = pd.concat([df_base, dados_extra], ignore_index=True)
                except Exception as e:
                    print(f"Erro ao processar {i}.xlsx: {e}")
        
        return df_base
        
    finally:
        # Limpar pasta temporária
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def ler_planilha_kpl(arquivo: str) -> pd.DataFrame:
    """
    Lê a planilha KPL e retorna DataFrame com SKU, Nome e Estoque.
    """
    # Detectar tipo de arquivo e ler
    if arquivo.lower().endswith('.csv'):
        try:
            df = pd.read_csv(arquivo, header=None, encoding='utf-8', sep=None, engine='python', on_bad_lines='skip')
        except:
            try:
                df = pd.read_csv(arquivo, header=None, encoding='latin-1', sep=None, engine='python', on_bad_lines='skip')
            except:
                df = pd.read_csv(arquivo, header=None, encoding='cp1252', sep=None, engine='python', on_bad_lines='skip')
    else:
        # Tentar múltiplos engines para Excel
        df = None
        errors = []
        
        # Engine 1: calamine (mais rápido e robusto)
        try:
            df = pd.read_excel(arquivo, header=None, engine='calamine')
        except Exception as e1:
            errors.append(f"calamine: {e1}")
        
        # Engine 2: openpyxl (padrão)
        if df is None:
            try:
                df = pd.read_excel(arquivo, header=None, engine='openpyxl')
            except Exception as e2:
                errors.append(f"openpyxl: {e2}")
        
        # Engine 3: xlrd (arquivos antigos)
        if df is None:
            try:
                df = pd.read_excel(arquivo, header=None, engine='xlrd')
            except Exception as e3:
                errors.append(f"xlrd: {e3}")
        
        if df is None:
            raise ValueError(f"Não foi possível ler o arquivo KPL. Erros: {'; '.join(errors)}")
    
    # Validar colunas
    min_col = max(CONFIG_KPL['sku_col'], CONFIG_KPL['nome_col'], CONFIG_KPL['estoque_col'])
    if df.shape[1] <= min_col:
        raise ValueError(f"Planilha KPL tem apenas {df.shape[1]} colunas. Esperado pelo menos {min_col + 1} colunas.\n"
                        f"Verifique: SKU na col B, Nome na col C, Estoque na col H")
    
    # Extrair colunas relevantes
    resultado = pd.DataFrame({
        'SKU': df.iloc[:, CONFIG_KPL['sku_col']].astype(str).str.strip(),
        'Produto': df.iloc[:, CONFIG_KPL['nome_col']].astype(str).str.strip(),
        'Estoque_KPL': pd.to_numeric(df.iloc[:, CONFIG_KPL['estoque_col']], errors='coerce').fillna(0).astype(int)
    })
    
    # Remover linhas com SKU vazio ou inválido
    resultado = resultado[resultado['SKU'].notna() & (resultado['SKU'] != '') & (resultado['SKU'] != 'nan')]
    
    # Remover possível cabeçalho
    resultado = resultado[~resultado['SKU'].str.lower().isin(['sku', 'codigo', 'código'])]
    
    print(f"[KPL] Linhas lidas: {len(resultado)}, Colunas no arquivo: {df.shape[1]}")
    
    return resultado


def ler_planilha_canal(df_canal: pd.DataFrame, canal: str) -> pd.DataFrame:
    """
    Lê DataFrame do canal e retorna DataFrame com SKU e Estoque.
    """
    config = CONFIG_CANAIS.get(canal)
    if not config:
        raise ValueError(f"Canal '{canal}' não configurado")
    
    # Validar colunas
    min_col = max(config['sku_col'], config['estoque_col'])
    if df_canal.shape[1] <= min_col:
        raise ValueError(f"Planilha {canal} tem apenas {df_canal.shape[1]} colunas. Esperado pelo menos {min_col + 1} colunas.\n"
                        f"Verifique: SKU na col F (idx 5), Estoque na col I (idx 8)")
    
    # Extrair colunas relevantes
    resultado = pd.DataFrame({
        'SKU': df_canal.iloc[:, config['sku_col']].astype(str).str.strip(),
        'Estoque_Canal': pd.to_numeric(df_canal.iloc[:, config['estoque_col']], errors='coerce').fillna(0).astype(int)
    })
    
    # Remover linhas com SKU vazio ou inválido
    resultado = resultado[resultado['SKU'].notna() & (resultado['SKU'] != '') & (resultado['SKU'] != 'nan')]
    
    # Remover possíveis cabeçalhos
    resultado = resultado[~resultado['SKU'].str.lower().isin(['sku', 'codigo', 'código', 'seller_custom_field'])]
    
    print(f"[{canal}] Linhas lidas: {len(resultado)}, Colunas no arquivo: {df_canal.shape[1]}")
    
    return resultado


def comparar_estoque(df_kpl: pd.DataFrame, df_canal: pd.DataFrame) -> pd.DataFrame:
    """
    Compara estoque entre KPL e Canal.
    
    Args:
        df_kpl: DataFrame com SKU, Produto, Estoque_KPL
        df_canal: DataFrame com SKU, Estoque_Canal
        
    Returns:
        DataFrame com comparação e status
    """
    # Merge: apenas SKUs que existem em AMBOS (inner join)
    df_merged = df_kpl.merge(df_canal, on='SKU', how='inner')
    
    # Calcular diferença e status
    df_merged['Diferenca'] = df_merged['Estoque_KPL'] - df_merged['Estoque_Canal']
    df_merged['Status'] = df_merged.apply(
        lambda row: '✅ OK' if row['Estoque_KPL'] == row['Estoque_Canal'] else '❌ DIVERGENTE', 
        axis=1
    )
    
    # Ordenar por status (divergentes primeiro)
    df_merged = df_merged.sort_values(by='Status', ascending=False)
    
    return df_merged[['SKU', 'Produto', 'Estoque_KPL', 'Estoque_Canal', 'Diferenca', 'Status']]


def gerar_relatorio_saldo(arquivo_kpl: str, arquivo_canal: str, canal: str) -> Tuple[str, Dict]:
    """
    Gera relatório completo de saldo.
    
    Args:
        arquivo_kpl: Caminho da planilha KPL
        arquivo_canal: Caminho do arquivo do canal (planilha ou ZIP para Shopee)
        canal: Nome do canal (ex: 'SHOPEE')
        
    Returns:
        Tuple com (caminho_arquivo_gerado, estatisticas)
    """
    config = CONFIG_CANAIS.get(canal)
    if not config:
        raise ValueError(f"Canal '{canal}' não configurado")
    
    # Ler KPL
    df_kpl = ler_planilha_kpl(arquivo_kpl)
    
    # Ler Canal (com tratamento especial para Shopee)
    if canal == 'SHOPEE' and arquivo_canal.lower().endswith('.zip'):
        df_canal_raw = consolidar_shopee_zip(arquivo_canal)
    else:
        # Tentar ler como Excel ou CSV
        if arquivo_canal.lower().endswith('.csv'):
            try:
                df_canal_raw = pd.read_csv(arquivo_canal, header=None, encoding='utf-8', sep=None, engine='python', on_bad_lines='skip')
            except:
                try:
                    df_canal_raw = pd.read_csv(arquivo_canal, header=None, encoding='latin-1', sep=None, engine='python', on_bad_lines='skip')
                except:
                    df_canal_raw = pd.read_csv(arquivo_canal, header=None, encoding='cp1252', sep=None, engine='python', on_bad_lines='skip')
        else:
            # Usar leitura robusta com múltiplos engines
            df_canal_raw = None
            for engine in ['calamine', 'openpyxl', 'xlrd']:
                try:
                    df_canal_raw = pd.read_excel(arquivo_canal, header=None, engine=engine)
                    break
                except:
                    continue
            if df_canal_raw is None:
                raise ValueError(f"Não foi possível ler a planilha do canal {canal}")
    
    df_canal = ler_planilha_canal(df_canal_raw, canal)
    
    # Tratamento especial para canais com remove_dashes (ex: Renner)
    if config.get('remove_dashes', False):
        # Guardar SKU original do KPL
        df_kpl['SKU_Original'] = df_kpl['SKU']
        # Criar SKU normalizado (sem traços) para comparação
        df_kpl['SKU'] = df_kpl['SKU'].str.replace('-', '', regex=False)
        
        # Fazer comparação com SKU normalizado
        df_resultado = comparar_estoque(df_kpl, df_canal)
        
        # Restaurar SKU original no resultado final
        sku_map = df_kpl.set_index('SKU')['SKU_Original'].to_dict()
        df_resultado['SKU'] = df_resultado['SKU'].map(sku_map).fillna(df_resultado['SKU'])
    else:
        # Comparação normal
        df_resultado = comparar_estoque(df_kpl, df_canal)
    
    # Estatísticas
    total = len(df_resultado)
    ok = (df_resultado['Status'] == '✅ OK').sum()
    divergente = (df_resultado['Status'] == '❌ DIVERGENTE').sum()
    
    stats = {
        'total': total,
        'ok': ok,
        'divergente': divergente,
        'taxa_ok': round((ok / total * 100) if total > 0 else 0, 1),
        'skus_kpl': len(df_kpl),
        'skus_canal': len(df_canal),
    }
    
    # Salvar em arquivo temporário
    temp_dir = tempfile.gettempdir()
    output_file = os.path.join(temp_dir, f"relatorio_saldo_{canal}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    
    # Criar Excel com formatação
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df_resultado.to_excel(writer, sheet_name='Comparação', index=False)
        
        # Adicionar aba de resumo
        resumo = pd.DataFrame([
            ['Data do Relatório', datetime.now().strftime('%d/%m/%Y %H:%M')],
            ['Canal', config['nome']],
            ['Total SKUs Comparados', total],
            ['Estoques OK', ok],
            ['Estoques Divergentes', divergente],
            ['Taxa de Acerto', f"{stats['taxa_ok']}%"],
            ['SKUs na base KPL', stats['skus_kpl']],
            ['SKUs na base Canal', stats['skus_canal']],
        ], columns=['Métrica', 'Valor'])
        resumo.to_excel(writer, sheet_name='Resumo', index=False)
    
    return output_file, stats
