"""
Componente de Tabela Customizada com:
- Cabeçalho fixo (sticky)
- Seleção múltipla (Shift/Ctrl)
- Duplo clique para copiar
- Checkbox "Selecionar todos"
"""
import flet as ft
from typing import List, Dict, Any, Callable, Optional
import pyperclip


class TabelaCustomizada:
    """
    Tabela customizada com cabeçalho fixo e seleção múltipla.
    """
    
    def __init__(
        self, 
        page: ft.Page,
        colunas: List[Dict[str, Any]],
        theme,
        on_selection_change: Optional[Callable] = None,
        altura_linha: int = 40,
    ):
        """
        Args:
            page: Página Flet
            colunas: Lista de dicts com {nome, largura, align}
            theme: ThemeManager
            on_selection_change: Callback quando seleção muda
            altura_linha: Altura de cada linha
        """
        self.page = page
        self.colunas = colunas
        self.theme = theme
        self.on_selection_change = on_selection_change
        self.altura_linha = altura_linha
        
        # Estado
        self.dados: List[Dict[str, Any]] = []
        self.linhas_selecionadas: set = set()
        self.ultima_linha_clicada: int = -1
        self.selecionar_todos_cb: ft.Checkbox = None
        
        # Componentes UI
        self._criar_componentes()
    
    def _criar_componentes(self):
        """Cria os componentes da tabela."""
        # Checkbox selecionar todos
        self.selecionar_todos_cb = ft.Checkbox(
            value=False,
            on_change=self._toggle_selecionar_todos,
            scale=0.8,
        )
        
        # Cabeçalho fixo
        header_cells = [
            ft.Container(
                content=self.selecionar_todos_cb,
                width=35,
                alignment=ft.alignment.center,
            )
        ]
        
        for col in self.colunas:
            header_cells.append(
                ft.Container(
                    content=ft.Text(
                        col.get('nome', ''),
                        size=11,
                        weight=ft.FontWeight.W_600,
                        color=self.theme.get_text_color(),
                    ),
                    width=col.get('largura', 100),
                    alignment=ft.alignment.center_left if col.get('align') != 'center' else ft.alignment.center,
                    padding=ft.padding.symmetric(5, 8),
                )
            )
        
        self.header = ft.Container(
            content=ft.Row(header_cells, spacing=0),
            bgcolor=self.theme.get_header_bg(),
            border_radius=ft.border_radius.only(top_left=8, top_right=8),
            padding=ft.padding.symmetric(8, 10),
        )
        
        # Container para linhas (scrollável)
        self.linhas_container = ft.Column([], spacing=1, scroll=ft.ScrollMode.AUTO)
        
        self.body = ft.Container(
            content=self.linhas_container,
            expand=True,
            bgcolor=self.theme.get_card_bg(),
            padding=5,
        )
        
        # Contador de seleção
        self.contador = ft.Text("0 selecionados", size=11, color=self.theme.get_text_secondary())
    
    def _toggle_selecionar_todos(self, e):
        """Seleciona ou deseleciona todas as linhas."""
        if e.control.value:
            self.linhas_selecionadas = set(range(len(self.dados)))
        else:
            self.linhas_selecionadas.clear()
        self._atualizar_visual()
        self._notificar_selecao()
    
    def _on_linha_click(self, idx: int, e: ft.ControlEvent):
        """Trata clique em uma linha."""
        # Detectar modificadores (Shift/Ctrl) via GestureDetector
        shift = getattr(e, 'shift', False)
        ctrl = getattr(e, 'ctrl', False)
        
        if ctrl:
            # Ctrl+Click: Toggle individual
            if idx in self.linhas_selecionadas:
                self.linhas_selecionadas.discard(idx)
            else:
                self.linhas_selecionadas.add(idx)
        elif shift and self.ultima_linha_clicada >= 0:
            # Shift+Click: Selecionar intervalo
            inicio = min(self.ultima_linha_clicada, idx)
            fim = max(self.ultima_linha_clicada, idx)
            for i in range(inicio, fim + 1):
                self.linhas_selecionadas.add(i)
        else:
            # Clique simples: Seleciona apenas esta
            self.linhas_selecionadas.clear()
            self.linhas_selecionadas.add(idx)
        
        self.ultima_linha_clicada = idx
        self._atualizar_visual()
        self._notificar_selecao()
    
    def _on_linha_double_click(self, idx: int, col_idx: int, valor: str, e):
        """Copia valor ao dar duplo clique."""
        try:
            pyperclip.copy(str(valor))
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"Copiado: {str(valor)[:50]}"),
                bgcolor="#22C55E",
                duration=1500,
            )
            self.page.snack_bar.open = True
            self.page.update()
        except:
            pass
    
    def _on_checkbox_change(self, idx: int, e):
        """Toggle seleção via checkbox."""
        if e.control.value:
            self.linhas_selecionadas.add(idx)
        else:
            self.linhas_selecionadas.discard(idx)
        self._atualizar_visual(atualizar_linhas=False)
        self._notificar_selecao()
    
    def _notificar_selecao(self):
        """Notifica mudança de seleção."""
        self.contador.value = f"{len(self.linhas_selecionadas)} selecionados"
        if self.on_selection_change:
            self.on_selection_change(list(self.linhas_selecionadas))
        self.page.update()
    
    def _atualizar_visual(self, atualizar_linhas=True):
        """Atualiza visual das linhas selecionadas."""
        # Atualizar checkbox "selecionar todos"
        if len(self.dados) > 0:
            self.selecionar_todos_cb.value = len(self.linhas_selecionadas) == len(self.dados)
        
        if atualizar_linhas:
            self._renderizar_linhas()
        
        self.page.update()
    
    def _renderizar_linhas(self):
        """Renderiza todas as linhas."""
        self.linhas_container.controls.clear()
        
        for idx, dado in enumerate(self.dados):
            selecionada = idx in self.linhas_selecionadas
            
            # Checkbox da linha
            cb = ft.Checkbox(
                value=selecionada,
                on_change=lambda e, i=idx: self._on_checkbox_change(i, e),
                scale=0.8,
            )
            
            cells = [
                ft.Container(
                    content=cb,
                    width=35,
                    alignment=ft.alignment.center,
                )
            ]
            
            # Células de dados
            for col_idx, col in enumerate(self.colunas):
                chave = col.get('chave', col.get('nome', ''))
                valor = dado.get(chave, '')
                
                # Widget para a célula
                if col.get('widget'):
                    widget = col['widget'](dado, idx)
                else:
                    widget = ft.Text(str(valor), size=11, color=self.theme.get_text_color())
                
                cell = ft.GestureDetector(
                    content=ft.Container(
                        content=widget,
                        width=col.get('largura', 100),
                        height=self.altura_linha,
                        alignment=ft.alignment.center_left,
                        padding=ft.padding.symmetric(5, 8),
                    ),
                    on_tap=lambda e, i=idx: self._on_linha_click(i, e),
                    on_double_tap=lambda e, i=idx, ci=col_idx, v=valor: self._on_linha_double_click(i, ci, v, e),
                )
                cells.append(cell)
            
            # Linha
            cor_fundo = "#3B82F6" if selecionada else (
                "#2A2A2A" if self.theme.is_dark[0] and idx % 2 == 0 else
                "#333333" if self.theme.is_dark[0] else
                "#F8F9FA" if idx % 2 == 0 else "#FFFFFF"
            )
            cor_texto = "#FFFFFF" if selecionada else self.theme.get_text_color()
            
            linha = ft.Container(
                content=ft.Row(cells, spacing=0),
                bgcolor=cor_fundo,
                border_radius=4,
                on_click=lambda e, i=idx: self._on_linha_click(i, e),
            )
            
            self.linhas_container.controls.append(linha)
    
    def carregar_dados(self, dados: List[Dict[str, Any]]):
        """Carrega dados na tabela."""
        self.dados = dados
        self.linhas_selecionadas.clear()
        self.ultima_linha_clicada = -1
        self._renderizar_linhas()
        self._notificar_selecao()
    
    def get_selecionados(self) -> List[Dict[str, Any]]:
        """Retorna os dados das linhas selecionadas."""
        return [self.dados[i] for i in sorted(self.linhas_selecionadas)]
    
    def build(self) -> ft.Column:
        """Retorna o componente completo."""
        return ft.Column([
            self.header,
            ft.Container(content=self.body, expand=True),
            ft.Container(
                content=self.contador,
                padding=ft.padding.only(left=10, top=5),
            ),
        ], spacing=0, expand=True)
