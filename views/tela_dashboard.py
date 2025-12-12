"""
Tela Dashboard - Painel inicial com métricas e gráficos
"""
import flet as ft
from datetime import datetime, timedelta
from services.database_sinc import get_connection, CANAIS


def criar_tela_dashboard(page: ft.Page, usuario_logado: list, theme):
    """Cria a tela de dashboard com métricas e gráficos."""
    
    usuario_atual = usuario_logado[0].get('username', 'Usuário') if usuario_logado[0] else 'Usuário'
    
    # ══════════════════════════════════════════════════════════════
    # FUNÇÕES DE DADOS
    # ══════════════════════════════════════════════════════════════
    
    def obter_metricas():
        """Obtém métricas gerais do sistema."""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Total de produtos (tabela correta: produtos_sinc)
            try:
                cursor.execute("SELECT COUNT(*) FROM produtos_sinc")
                total_produtos = cursor.fetchone()[0]
            except:
                total_produtos = 0
            
            # Produtos sincronizados (com pelo menos 1 canal)
            try:
                cursor.execute("SELECT COUNT(DISTINCT sku) FROM produto_canal WHERE status = 'ATIVO'")
                produtos_ativos = cursor.fetchone()[0]
            except:
                produtos_ativos = 0
            
            # Chamados abertos
            try:
                cursor.execute("SELECT COUNT(*) FROM chamados WHERE na_lixeira = 0")
                chamados_abertos = cursor.fetchone()[0]
            except:
                chamados_abertos = 0
            
            # Chamados urgentes
            try:
                cursor.execute("SELECT COUNT(*) FROM chamados WHERE na_lixeira = 0 AND prioridade = 'URGENTE'")
                chamados_urgentes = cursor.fetchone()[0]
            except:
                chamados_urgentes = 0
            
            # Usuários ativos
            try:
                cursor.execute("SELECT COUNT(*) FROM usuarios WHERE status = 'ATIVO'")
                usuarios_ativos = cursor.fetchone()[0]
            except:
                usuarios_ativos = 0
            
            # Produtos na blocklist
            try:
                cursor.execute("SELECT COUNT(*) FROM produtos_bloqueados")
                blocklist = cursor.fetchone()[0]
            except:
                blocklist = 0
            
            conn.close()
            
            return {
                'total_produtos': total_produtos,
                'produtos_ativos': produtos_ativos,
                'chamados_abertos': chamados_abertos,
                'chamados_urgentes': chamados_urgentes,
                'usuarios_ativos': usuarios_ativos,
                'blocklist': blocklist,
            }
        except Exception as e:
            print(f"[Dashboard] Erro ao obter métricas: {e}")
            return {
                'total_produtos': 0, 'produtos_ativos': 0, 'chamados_abertos': 0,
                'chamados_urgentes': 0, 'usuarios_ativos': 0, 'blocklist': 0,
            }
    
    def obter_produtos_por_canal():
        """Obtém contagem de produtos por canal."""
        conn = get_connection()
        cursor = conn.cursor()
        
        dados = {}
        for canal in CANAIS:
            cursor.execute("SELECT COUNT(*) FROM produto_canal WHERE canal = ? AND status = 'ATIVO'", (canal,))
            dados[canal] = cursor.fetchone()[0]
        
        conn.close()
        return dados
    
    def obter_chamados_por_prioridade():
        """Obtém contagem de chamados por prioridade."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT prioridade, COUNT(*) 
            FROM chamados 
            WHERE na_lixeira = 0 
            GROUP BY prioridade
        """)
        
        dados = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return dados
    
    # ══════════════════════════════════════════════════════════════
    # COMPONENTES VISUAIS
    # ══════════════════════════════════════════════════════════════
    
    def criar_card_metrica(titulo: str, valor: str, icone, cor: str, subtitulo: str = ""):
        """Cria um card de métrica."""
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(icone, size=28, color=cor),
                    ft.Column([
                        ft.Text(titulo, size=11, color=theme.get_text_secondary()),
                        ft.Text(str(valor), size=26, weight=ft.FontWeight.BOLD, color=theme.get_text_color()),
                    ], spacing=0, expand=True),
                ], spacing=10),
                ft.Text(subtitulo, size=10, color=theme.get_text_secondary()) if subtitulo else ft.Container(),
            ], spacing=5),
            padding=20,
            bgcolor=theme.get_card_bg(),
            border_radius=12,
            expand=True,
        )
    
    def criar_grafico_barras(dados: dict, titulo: str, cores: dict = None):
        """Cria um gráfico de barras simples."""
        if not dados or all(v == 0 for v in dados.values()):
            return ft.Container(
                content=ft.Text("Sem dados", size=12, color=theme.get_text_secondary()),
                padding=20,
            )
        
        max_valor = max(dados.values()) if dados.values() else 1
        
        barras = []
        for label, valor in sorted(dados.items(), key=lambda x: x[1], reverse=True)[:8]:
            cor = cores.get(label, "#6366F1") if cores else "#6366F1"
            porcentagem = (valor / max_valor) * 100 if max_valor > 0 else 0
            
            barras.append(
                ft.Row([
                    ft.Text(label[:12], size=10, width=80, color=theme.get_text_color()),
                    ft.Container(
                        content=ft.Container(
                            bgcolor=cor,
                            border_radius=3,
                            width=porcentagem * 1.2,
                            height=16,
                        ),
                        width=150,
                        height=16,
                        bgcolor="#333333" if theme.is_dark[0] else "#E0E0E0",
                        border_radius=3,
                    ),
                    ft.Text(str(valor), size=10, width=40, color=theme.get_text_secondary()),
                ], spacing=8)
            )
        
        return ft.Container(
            content=ft.Column([
                ft.Text(titulo, size=13, weight=ft.FontWeight.W_600, color=theme.get_text_color()),
                ft.Column(barras, spacing=6),
            ], spacing=10),
            padding=15,
            bgcolor=theme.get_card_bg(),
            border_radius=12,
            expand=True,
        )
    
    # ══════════════════════════════════════════════════════════════
    # CARREGAR DADOS
    # ══════════════════════════════════════════════════════════════
    
    metricas = obter_metricas()
    produtos_canal = obter_produtos_por_canal()
    chamados_prio = obter_chamados_por_prioridade()
    
    # Cores por canal
    cores_canais = {
        'NETSHOES': '#1E88E5', 'CENTAURO': '#43A047', 'MELI': '#FFD600',
        'SHOPEE': '#FF5722', 'RENNER': '#E53935', 'SHEIN': '#EC407A',
        'DAFITI': '#7E57C2', 'AMAZON': '#FF9800', 'TIKTOK': '#000000',
    }
    
    # Cores por prioridade
    cores_prio = {
        'URGENTE': '#EF4444', 'ALTA': '#F97316', 
        'MÉDIA': '#F59E0B', 'BAIXA': '#22C55E',
    }
    
    # ══════════════════════════════════════════════════════════════
    # LAYOUT
    # ══════════════════════════════════════════════════════════════
    
    return ft.Column([
        # Header
        ft.Container(
            content=ft.Column([
                ft.Text(f"Olá, {usuario_atual}! 👋", size=24, weight=ft.FontWeight.BOLD, color=theme.get_text_color()),
                ft.Text(f"Bem-vindo ao SINC • {datetime.now().strftime('%d/%m/%Y')}", size=12, color=theme.get_text_secondary()),
            ], spacing=2),
            padding=ft.padding.only(left=25, right=25, top=20, bottom=10),
        ),
        
        # Cards de métricas
        ft.Container(
            content=ft.Row([
                criar_card_metrica("Produtos", f"{metricas['total_produtos']:,}", ft.Icons.INVENTORY_2, "#6366F1"),
                criar_card_metrica("Ativos em Canais", f"{metricas['produtos_ativos']:,}", ft.Icons.CHECK_CIRCLE, "#22C55E"),
                criar_card_metrica("Chamados", str(metricas['chamados_abertos']), ft.Icons.SUPPORT_AGENT, "#F59E0B", 
                                  f"{metricas['chamados_urgentes']} urgentes" if metricas['chamados_urgentes'] else ""),
                criar_card_metrica("Blocklist", str(metricas['blocklist']), ft.Icons.BLOCK, "#EF4444"),
            ], spacing=15),
            padding=ft.padding.only(left=20, right=20, bottom=15),
        ),
        
        # Gráficos
        ft.Container(
            content=ft.Row([
                criar_grafico_barras(produtos_canal, "📊 Produtos por Canal", cores_canais),
                criar_grafico_barras(chamados_prio, "🎫 Chamados por Prioridade", cores_prio),
            ], spacing=15),
            padding=ft.padding.only(left=20, right=20, bottom=20),
            expand=True,
        ),
    ], spacing=0, expand=True)
