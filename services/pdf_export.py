"""
Serviço de Exportação para PDF
"""
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

# Usa fpdf2 (versão mais recente)
try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False
    print("[PDF] fpdf não instalado. Execute: pip install fpdf2")


class RelatorioPDF(FPDF):
    """Classe base para relatórios PDF."""
    
    def __init__(self, titulo: str = "Relatório SINC"):
        super().__init__()
        self.titulo = titulo
        self.set_auto_page_break(auto=True, margin=15)
    
    def header(self):
        """Cabeçalho de cada página."""
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, self.titulo, border=0, ln=True, align='C')
        self.set_font('Arial', '', 9)
        self.cell(0, 5, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
        self.ln(5)
    
    def footer(self):
        """Rodapé de cada página."""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', align='C')
    
    def adicionar_tabela(self, cabecalhos: List[str], dados: List[List[str]], larguras: List[int] = None):
        """
        Adiciona uma tabela ao PDF.
        
        Args:
            cabecalhos: Lista de títulos das colunas
            dados: Lista de listas com os dados
            larguras: Larguras das colunas (opcional)
        """
        if larguras is None:
            largura_total = 190  # Largura útil A4
            larguras = [largura_total // len(cabecalhos)] * len(cabecalhos)
        
        # Cabeçalho da tabela
        self.set_font('Arial', 'B', 9)
        self.set_fill_color(50, 50, 50)
        self.set_text_color(255, 255, 255)
        
        for i, cab in enumerate(cabecalhos):
            self.cell(larguras[i], 8, str(cab)[:20], border=1, fill=True, align='C')
        self.ln()
        
        # Dados da tabela
        self.set_font('Arial', '', 8)
        self.set_text_color(0, 0, 0)
        
        fill = False
        for linha in dados:
            if fill:
                self.set_fill_color(240, 240, 240)
            else:
                self.set_fill_color(255, 255, 255)
            
            for i, valor in enumerate(linha):
                texto = str(valor)[:25] if valor else ""
                self.cell(larguras[i], 6, texto, border=1, fill=True)
            self.ln()
            fill = not fill
    
    def adicionar_secao(self, titulo: str):
        """Adiciona uma seção com título."""
        self.ln(5)
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(100, 100, 100)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, titulo, fill=True, ln=True)
        self.set_text_color(0, 0, 0)
        self.ln(3)


def exportar_relatorio_saldo_pdf(dados: List[Dict], stats: Dict, canal: str, caminho_destino: str) -> bool:
    """
    Exporta relatório de saldo para PDF.
    
    Args:
        dados: Lista de dicionários com SKU, Produto, Estoque_KPL, Estoque_Canal, Diferenca, Status
        stats: Estatísticas (total, ok, divergente, taxa_ok)
        canal: Nome do canal
        caminho_destino: Caminho do arquivo PDF
        
    Returns:
        True se exportou com sucesso
    """
    if not HAS_FPDF:
        print("[PDF] fpdf não instalado")
        return False
    
    try:
        pdf = RelatorioPDF(f"Relatório de Saldo - {canal}")
        pdf.alias_nb_pages()
        pdf.add_page()
        
        # Resumo
        pdf.adicionar_secao("Resumo")
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, f"Canal: {canal}", ln=True)
        pdf.cell(0, 6, f"Total de SKUs: {stats.get('total', 0)}", ln=True)
        pdf.cell(0, 6, f"OK: {stats.get('ok', 0)} | Divergentes: {stats.get('divergente', 0)}", ln=True)
        pdf.cell(0, 6, f"Taxa de Acerto: {stats.get('taxa_ok', 0)}%", ln=True)
        
        # Tabela de divergentes (se houver)
        divergentes = [d for d in dados if d.get('Status', '').startswith('❌')]
        if divergentes:
            pdf.adicionar_secao(f"Produtos Divergentes ({len(divergentes)})")
            
            cabecalhos = ['SKU', 'Produto', 'Est. KPL', 'Est. Canal', 'Diferença']
            larguras = [35, 70, 25, 25, 25]
            
            linhas = []
            for d in divergentes[:100]:  # Limitar a 100
                linhas.append([
                    d.get('SKU', ''),
                    d.get('Produto', ''),
                    str(d.get('Estoque_KPL', 0)),
                    str(d.get('Estoque_Canal', 0)),
                    str(d.get('Diferenca', 0)),
                ])
            
            pdf.adicionar_tabela(cabecalhos, linhas, larguras)
        
        pdf.output(caminho_destino)
        print(f"[PDF] Exportado: {caminho_destino}")
        return True
        
    except Exception as e:
        print(f"[PDF] Erro ao exportar: {e}")
        return False


def exportar_chamados_pdf(chamados: List[Dict], caminho_destino: str) -> bool:
    """
    Exporta lista de chamados para PDF.
    
    Args:
        chamados: Lista de dicionários de chamados
        caminho_destino: Caminho do arquivo PDF
        
    Returns:
        True se exportou com sucesso
    """
    if not HAS_FPDF:
        return False
    
    try:
        pdf = RelatorioPDF("Relatório de Chamados")
        pdf.alias_nb_pages()
        pdf.add_page()
        
        # Resumo por prioridade
        pdf.adicionar_secao("Resumo por Prioridade")
        prioridades = {}
        for c in chamados:
            p = c.get('prioridade', 'N/A')
            prioridades[p] = prioridades.get(p, 0) + 1
        
        pdf.set_font('Arial', '', 10)
        for p, count in sorted(prioridades.items()):
            pdf.cell(0, 6, f"{p}: {count} chamados", ln=True)
        
        # Tabela de chamados
        pdf.adicionar_secao(f"Chamados ({len(chamados)})")
        
        cabecalhos = ['Número', 'Prioridade', 'Canal', 'Criado Por', 'Data']
        larguras = [35, 30, 35, 40, 40]
        
        linhas = []
        for c in chamados[:100]:
            linhas.append([
                c.get('numero', ''),
                c.get('prioridade', ''),
                c.get('canal', ''),
                c.get('criado_por', ''),
                c.get('created_at', '')[:10] if c.get('created_at') else '',
            ])
        
        pdf.adicionar_tabela(cabecalhos, linhas, larguras)
        
        pdf.output(caminho_destino)
        return True
        
    except Exception as e:
        print(f"[PDF] Erro: {e}")
        return False
