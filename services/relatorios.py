"""
Módulo de Relatórios - Geração de gráficos e PDFs
"""
import os
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import matplotlib
matplotlib.use('Agg')  # Backend não-interativo
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from io import BytesIO

# Cores do tema
CORES_STATUS = {
    'ATIVO': '#22C55E',
    'CATALOGANDO': '#F59E0B', 
    'ERRO': '#EF4444',
    'BLOCKLIST': '#000000',
    'SEM STATUS': '#E0E0E0'
}

CORES_CANAIS = {
    'NETSHOES': '#E53935', 'CENTAURO': '#1E88E5', 'TIKTOK': '#000000',
    'SHEIN': '#FF6B6B', 'RENNER': '#8B5CF6', 'SHOPEE': '#FF5722',
    'MELI': '#FFE500', 'DAFITI': '#00BCD4', 'AMAZON': '#FF9800'
}

CORES_PRIORIDADE = {
    'ALTA': '#EF4444',
    'MÉDIA': '#F59E0B',
    'BAIXA': '#22C55E'
}


def get_estatisticas_canais() -> Dict[str, Any]:
    """Retorna estatísticas agregadas de todos os canais."""
    from services.database_sinc import get_connection, CANAIS
    
    conn = get_connection()
    cursor = conn.cursor()
    
    stats = {
        'por_canal': {},
        'totais': {'total': 0, 'ativo': 0, 'catalogando': 0, 'erro': 0, 'blocklist': 0, 'sem_status': 0}
    }
    
    for canal in CANAIS:
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'ATIVO' THEN 1 ELSE 0 END) as ativo,
                SUM(CASE WHEN status = 'CATALOGANDO' THEN 1 ELSE 0 END) as catalogando,
                SUM(CASE WHEN status = 'ERRO' THEN 1 ELSE 0 END) as erro,
                SUM(CASE WHEN status = 'BLOCKLIST' THEN 1 ELSE 0 END) as blocklist,
                SUM(CASE WHEN status IS NULL OR status = '' THEN 1 ELSE 0 END) as sem_status
            FROM produto_canal
            WHERE canal = ?
        """, (canal,))
        
        row = cursor.fetchone()
        if row:
            r = dict(row)
            stats['por_canal'][canal] = {
                'total': r['total'] or 0,
                'ativo': r['ativo'] or 0,
                'catalogando': r['catalogando'] or 0,
                'erro': r['erro'] or 0,
                'blocklist': r['blocklist'] or 0,
                'sem_status': r['sem_status'] or 0
            }
            
            for k, v in stats['por_canal'][canal].items():
                stats['totais'][k] += v
    
    # Calcular taxa de sucesso
    if stats['totais']['total'] > 0:
        stats['totais']['taxa_sucesso'] = round(
            (stats['totais']['ativo'] / stats['totais']['total']) * 100, 1
        )
    else:
        stats['totais']['taxa_sucesso'] = 0
    
    conn.close()
    return stats


def get_estatisticas_chamados() -> Dict[str, Any]:
    """Retorna estatísticas dos chamados."""
    from services.database_sinc import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    stats = {
        'por_prioridade': {'ALTA': 0, 'MÉDIA': 0, 'BAIXA': 0},
        'por_status': {'abertos': 0, 'lixeira': 0},
        'totais': {'total': 0, 'abertos': 0, 'lixeira': 0},
        'recentes': []
    }
    
    try:
        # Por prioridade
        cursor.execute("""
            SELECT prioridade, COUNT(*) as qtd
            FROM chamados
            WHERE na_lixeira = 0
            GROUP BY prioridade
        """)
        for row in cursor.fetchall():
            r = dict(row)
            pri = r['prioridade'] or 'MÉDIA'
            if pri in stats['por_prioridade']:
                stats['por_prioridade'][pri] = r['qtd']
        
        # Por status (abertos vs lixeira)
        cursor.execute("SELECT COUNT(*) FROM chamados WHERE na_lixeira = 0")
        stats['totais']['abertos'] = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM chamados WHERE na_lixeira = 1")
        stats['totais']['lixeira'] = cursor.fetchone()[0] or 0
        
        stats['totais']['total'] = stats['totais']['abertos'] + stats['totais']['lixeira']
        
        # Chamados recentes (usando colunas que existem)
        cursor.execute("""
            SELECT id, numero, prioridade, observacoes, created_at
            FROM chamados
            WHERE na_lixeira = 0
            ORDER BY created_at DESC
            LIMIT 10
        """)
        stats['recentes'] = [dict(r) for r in cursor.fetchall()]
    except Exception as e:
        print(f"Erro ao buscar estatísticas de chamados: {e}")
    
    conn.close()
    return stats


def gerar_grafico_rosca_status(stats: Dict[str, Any], dark_mode: bool = False) -> str:
    """Gera gráfico de rosca com distribuição de status. Retorna caminho da imagem."""
    totais = stats['totais']
    
    # Dados para o gráfico
    labels = []
    sizes = []
    colors = []
    
    for status, cor in [('ativo', CORES_STATUS['ATIVO']), 
                        ('catalogando', CORES_STATUS['CATALOGANDO']),
                        ('erro', CORES_STATUS['ERRO']),
                        ('blocklist', CORES_STATUS['BLOCKLIST']),
                        ('sem_status', CORES_STATUS['SEM STATUS'])]:
        if totais.get(status, 0) > 0:
            labels.append(status.replace('_', ' ').title())
            sizes.append(totais[status])
            colors.append(cor)
    
    if not sizes:
        sizes = [1]
        labels = ['Sem dados']
        colors = ['#CCCCCC']
    
    # Configurar estilo
    bg_color = '#1E1E1E' if dark_mode else '#FFFFFF'
    text_color = '#FFFFFF' if dark_mode else '#000000'
    
    fig, ax = plt.subplots(figsize=(6, 6), facecolor=bg_color)
    ax.set_facecolor(bg_color)
    
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors, autopct='%1.1f%%',
        pctdistance=0.75, startangle=90,
        wedgeprops=dict(width=0.5, edgecolor=bg_color)
    )
    
    for text in texts + autotexts:
        text.set_color(text_color)
        text.set_fontsize(10)
    
    ax.set_title('Distribuição por Status', fontsize=14, fontweight='bold', color=text_color, pad=20)
    
    # Salvar em arquivo temporário
    temp_dir = tempfile.gettempdir()
    filepath = os.path.join(temp_dir, f'grafico_rosca_{datetime.now().strftime("%H%M%S")}.png')
    plt.savefig(filepath, dpi=120, bbox_inches='tight', facecolor=bg_color)
    plt.close()
    
    return filepath


def gerar_grafico_barras_canais(stats: Dict[str, Any], dark_mode: bool = False) -> str:
    """Gera gráfico de barras horizontais com produtos por canal - Visual Premium."""
    por_canal = stats['por_canal']
    
    # Ordenar por total (maior para menor)
    canais_ordenados = sorted(por_canal.keys(), key=lambda c: por_canal[c]['total'], reverse=True)
    totais = [por_canal[c]['total'] for c in canais_ordenados]
    cores = [CORES_CANAIS.get(c, '#888888') for c in canais_ordenados]
    
    # Configurar estilo
    bg_color = '#1E1E1E' if dark_mode else '#FFFFFF'
    text_color = '#FFFFFF' if dark_mode else '#333333'
    grid_color = '#444444' if dark_mode else '#E0E0E0'
    
    fig, ax = plt.subplots(figsize=(10, 6), facecolor=bg_color)
    ax.set_facecolor(bg_color)
    
    # Gráfico de barras verticais (mais bonito)
    x = range(len(canais_ordenados))
    bars = ax.bar(x, totais, color=cores, edgecolor='none', width=0.7, 
                  alpha=0.9, zorder=3)
    
    # Adicionar valores em cima das barras
    for bar, total in zip(bars, totais):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, height + max(totais)*0.02, 
                str(total), ha='center', va='bottom', color=text_color, 
                fontsize=11, fontweight='bold')
    
    # Estilização
    ax.set_xticks(x)
    ax.set_xticklabels(canais_ordenados, rotation=45, ha='right', fontsize=10)
    ax.set_ylabel('Quantidade de Produtos', color=text_color, fontsize=11)
    ax.set_title('Produtos por Canal', fontsize=16, fontweight='bold', 
                 color=text_color, pad=20)
    
    # Grid sutil
    ax.yaxis.grid(True, linestyle='--', alpha=0.3, color=grid_color, zorder=0)
    ax.set_axisbelow(True)
    
    # Remover bordas
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color(grid_color)
    ax.spines['left'].set_color(grid_color)
    ax.tick_params(colors=text_color, labelsize=10)
    
    # Ajustar margem do Y para dar espaço aos valores
    ax.set_ylim(0, max(totais) * 1.15 if totais else 10)
    
    plt.tight_layout()
    
    # Salvar
    temp_dir = tempfile.gettempdir()
    filepath = os.path.join(temp_dir, f'grafico_barras_{datetime.now().strftime("%H%M%S")}.png')
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor=bg_color)
    plt.close()
    
    return filepath


def gerar_grafico_pizza_prioridade(stats: Dict[str, Any], dark_mode: bool = False) -> str:
    """Gera gráfico de pizza para prioridade de chamados."""
    por_prioridade = stats['por_prioridade']
    
    labels = []
    sizes = []
    colors = []
    
    for pri in ['ALTA', 'MÉDIA', 'BAIXA']:
        if por_prioridade.get(pri, 0) > 0:
            labels.append(pri)
            sizes.append(por_prioridade[pri])
            colors.append(CORES_PRIORIDADE[pri])
    
    if not sizes:
        sizes = [1]
        labels = ['Sem dados']
        colors = ['#CCCCCC']
    
    bg_color = '#1E1E1E' if dark_mode else '#FFFFFF'
    text_color = '#FFFFFF' if dark_mode else '#000000'
    
    fig, ax = plt.subplots(figsize=(5, 5), facecolor=bg_color)
    ax.set_facecolor(bg_color)
    
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors, autopct='%1.0f%%',
        startangle=90, explode=[0.02] * len(sizes)
    )
    
    for text in texts + autotexts:
        text.set_color(text_color)
        text.set_fontsize(11)
    
    ax.set_title('Chamados por Prioridade', fontsize=14, fontweight='bold', color=text_color, pad=15)
    
    temp_dir = tempfile.gettempdir()
    filepath = os.path.join(temp_dir, f'grafico_prioridade_{datetime.now().strftime("%H%M%S")}.png')
    plt.savefig(filepath, dpi=120, bbox_inches='tight', facecolor=bg_color)
    plt.close()
    
    return filepath


def gerar_pdf_relatorio_canais(stats: Dict[str, Any], grafico_rosca: str, grafico_barras: str, output_path: str):
    """Gera PDF do relatório de canais."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
    
    doc = SimpleDocTemplate(output_path, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    
    # Estilos customizados
    titulo_style = ParagraphStyle('Titulo', parent=styles['Heading1'], fontSize=18, spaceAfter=20)
    subtitulo_style = ParagraphStyle('Subtitulo', parent=styles['Heading2'], fontSize=14, spaceAfter=10)
    
    elements = []
    
    # Título
    elements.append(Paragraph("📊 Relatório de Canais", titulo_style))
    elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Métricas principais
    totais = stats['totais']
    elements.append(Paragraph("Métricas Gerais", subtitulo_style))
    
    data = [
        ['Total Produtos', 'Ativos', 'Catalogando', 'Erros', 'Taxa Sucesso'],
        [str(totais['total']), str(totais['ativo']), str(totais['catalogando']), 
         str(totais['erro']), f"{totais['taxa_sucesso']}%"]
    ]
    
    t = Table(data, colWidths=[1.4*inch]*5)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.18, 0.18, 0.18)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.Color(0.95, 0.95, 0.95)),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    elements.append(t)
    elements.append(Spacer(1, 30))
    
    # Gráficos
    if os.path.exists(grafico_rosca):
        elements.append(Paragraph("Distribuição por Status", subtitulo_style))
        elements.append(Image(grafico_rosca, width=4*inch, height=4*inch))
        elements.append(Spacer(1, 20))
    
    if os.path.exists(grafico_barras):
        elements.append(Paragraph("Produtos por Canal", subtitulo_style))
        elements.append(Image(grafico_barras, width=5.5*inch, height=3.5*inch))
        elements.append(Spacer(1, 20))
    
    # Tabela detalhada por canal
    elements.append(Paragraph("Detalhamento por Canal", subtitulo_style))
    
    data_canais = [['Canal', 'Total', 'Ativos', 'Catalogando', 'Erros', 'Blocklist']]
    for canal, dados in stats['por_canal'].items():
        data_canais.append([
            canal, str(dados['total']), str(dados['ativo']), 
            str(dados['catalogando']), str(dados['erro']), str(dados['blocklist'])
        ])
    
    t2 = Table(data_canais, colWidths=[1.2*inch, 0.8*inch, 0.8*inch, 1*inch, 0.8*inch, 0.9*inch])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.18, 0.18, 0.18)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.Color(0.95, 0.95, 0.95)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.Color(0.98, 0.98, 0.98), colors.whitesmoke])
    ]))
    elements.append(t2)
    
    doc.build(elements)


def gerar_pdf_relatorio_chamados(stats: Dict[str, Any], grafico_prioridade: str, output_path: str):
    """Gera PDF do relatório de chamados."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
    
    doc = SimpleDocTemplate(output_path, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    
    titulo_style = ParagraphStyle('Titulo', parent=styles['Heading1'], fontSize=18, spaceAfter=20)
    subtitulo_style = ParagraphStyle('Subtitulo', parent=styles['Heading2'], fontSize=14, spaceAfter=10)
    
    elements = []
    
    # Título
    elements.append(Paragraph("📋 Relatório de Chamados", titulo_style))
    elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Métricas
    totais = stats['totais']
    elements.append(Paragraph("Resumo", subtitulo_style))
    
    data = [
        ['Total', 'Abertos', 'Na Lixeira'],
        [str(totais['total']), str(totais['abertos']), str(totais['lixeira'])]
    ]
    
    t = Table(data, colWidths=[1.5*inch]*3)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.18, 0.18, 0.18)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.Color(0.95, 0.95, 0.95)),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    elements.append(t)
    elements.append(Spacer(1, 30))
    
    # Gráfico
    if os.path.exists(grafico_prioridade):
        elements.append(Paragraph("Distribuição por Prioridade", subtitulo_style))
        elements.append(Image(grafico_prioridade, width=3.5*inch, height=3.5*inch))
        elements.append(Spacer(1, 20))
    
    # Últimos chamados
    if stats.get('recentes'):
        elements.append(Paragraph("Últimos Chamados", subtitulo_style))
        data_chamados = [['#', 'Título', 'Prioridade', 'Data']]
        for ch in stats['recentes'][:8]:
            data_fmt = ''
            if ch.get('created_at'):
                try:
                    data_fmt = datetime.strptime(ch['created_at'][:19], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
                except:
                    data_fmt = ch['created_at'][:10]
            data_chamados.append([
                str(ch.get('id', '')), 
                (ch.get('numero', '') or ch.get('observacoes', '') or '')[:40], 
                ch.get('prioridade', '') or 'MÉDIA',
                data_fmt
            ])
        
        t2 = Table(data_chamados, colWidths=[0.5*inch, 3.5*inch, 1*inch, 1*inch])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.18, 0.18, 0.18)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.Color(0.98, 0.98, 0.98), colors.whitesmoke])
        ]))
        elements.append(t2)
    
    doc.build(elements)
