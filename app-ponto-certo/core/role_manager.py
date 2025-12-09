"""
Gerenciador de Funções e Permissões (Gerente vs Caixa)
Controla acesso a módulos baseado na variável MARIADB_ROLE do .env
"""

import os
import logging
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

logger = logging.getLogger(__name__)


class RoleManager:
    """Gerencia permissões de acesso baseado em rol (Gerente ou Caixa)"""

    GERENTE = "gerente"
    CAIXA = "caixa"

    def __init__(self):
        self.role = os.getenv("MARIADB_ROLE", self.GERENTE).lower()
        logger.info(f"Rol carregado: {self.get_role_name()}")

    def is_gerente(self) -> bool:
        """Verifica se é gerente"""
        return self.role == self.GERENTE

    def is_caixa(self) -> bool:
        """Verifica se é caixa"""
        return self.role == self.CAIXA

    def can_access(self, module: str) -> bool:
        """Verifica se o rol pode acessar o módulo"""
        module = module.lower()

        # Módulos que gerente pode acessar
        gerente_modules = {
            "vendas",
            "estoque",
            "financeiro",
            "fornecedores",
            "usuarios",
            "relatorios",
            "home",
            "devolucoes",
            "configuracoes",
        }

        # Módulos que caixa pode acessar
        caixa_modules = {
            "vendas",
            "devolucoes",
            "relatorios_caixa",
            "home_caixa",
        }

        if self.is_gerente():
            return module in gerente_modules
        elif self.is_caixa():
            return module in caixa_modules

        return False

    def get_visible_menu_items(self) -> list:
        """Retorna itens de menu visíveis para o rol"""
        items = []

        if self.is_gerente():
            items = [
                {
                    "nome": "Vendas",
                    "icon": "shopping_cart",
                    "rota": "/vendas",
                    "color": "#007BFF",
                },
                {
                    "nome": "Estoque",
                    "icon": "inventory",
                    "rota": "/estoque",
                    "color": "#B8860B",
                },
                {
                    "nome": "Financeiro",
                    "icon": "attach_money",
                    "rota": "/financeiro",
                    "color": "#28A745",
                },
                {
                    "nome": "Fornecedores",
                    "icon": "local_shipping",
                    "rota": "/fornecedores",
                    "color": "#000000",
                },
                {
                    "nome": "Usuários",
                    "icon": "people",
                    "rota": "/usuarios",
                    "color": "#6C757D",
                },
                {
                    "nome": "Relatórios",
                    "icon": "assessment",
                    "rota": "/relatorios",
                    "color": "#9B59B6",
                },
            ]

        elif self.is_caixa():
            items = [
                {
                    "nome": "Vendas",
                    "icon": "shopping_cart",
                    "rota": "/vendas",
                    "color": "#007BFF",
                },
                {
                    "nome": "Devoluções",
                    "icon": "undo",
                    "rota": "/devolucoes",
                    "color": "#DC3545",
                },
                {
                    "nome": "Meu Desempenho",
                    "icon": "trending_up",
                    "rota": "/relatorios",
                    "color": "#9B59B6",
                },
            ]

        return items

    def get_role_name(self) -> str:
        """Retorna nome legível do rol"""
        if self.is_gerente():
            return "Gerente"
        elif self.is_caixa():
            return "Caixa"
        return "Desconhecido"

    def get_dashboard_title(self) -> str:
        """Retorna título personalizado para cada rol"""
        if self.is_gerente():
            return "Painel de Controle - Gerente"
        elif self.is_caixa():
            return "Ponto de Venda"
        return "Sistema Ponto Certo"

    def can_edit_financeiro(self) -> bool:
        """Apenas gerente pode editar financeiro"""
        return self.is_gerente()

    def can_manage_users(self) -> bool:
        """Apenas gerente pode gerenciar usuários"""
        return self.is_gerente()

    def can_view_relatorios_completos(self) -> bool:
        """Apenas gerente vê relatórios completos"""
        return self.is_gerente()

    def can_access_estoque(self) -> bool:
        """Apenas gerente acessa estoque"""
        return self.is_gerente()

    def can_access_fornecedores(self) -> bool:
        """Apenas gerente acessa fornecedores"""
        return self.is_gerente()

    def can_process_devolucoes(self) -> bool:
        """Caixa pode processar devoluções (trocas) direto na tela de vendas"""
        return True  # Ambos podem

    def can_cancel_devolucao(self) -> bool:
        """Apenas gerente pode cancelar uma devolução já feita"""
        return self.is_gerente()

    def get_relatorio_filters(self) -> dict:
        """Retorna filtros de relatório baseado no rol"""
        if self.is_gerente():
            return {
                "data_inicio": None,  # Sem filtro
                "data_fim": None,
                "todos_usuarios": True,  # Ver todas as vendas
            }
        elif self.is_caixa():
            # Caixa vê apenas suas vendas
            return {
                "data_inicio": None,
                "data_fim": None,
                "apenas_meu_usuario": True,
            }
        return {}

    def log_action(self, action: str, details: str = ""):
        """Registra ação do usuário para auditoria"""
        role_name = self.get_role_name()
        logger.info(f"[{role_name}] {action}: {details}")


# Instância global
_role_manager = None


def get_role_manager() -> RoleManager:
    """Obtém instância global do gerenciador de funções"""
    global _role_manager
    if _role_manager is None:
        _role_manager = RoleManager()
    return _role_manager


def require_gerente(func):
    """Decorator para funções que requerem acesso de gerente"""

    def wrapper(*args, **kwargs):
        role = get_role_manager()
        if not role.is_gerente():
            logger.warning(
                f"Acesso negado: {role.get_role_name()} tentou acessar função de gerente"
            )
            raise PermissionError(
                f"Esta operação é restrita a Gerentes. Você é: {role.get_role_name()}"
            )
        return func(*args, **kwargs)

    return wrapper


def require_caixa_or_gerente(func):
    """Decorator para funções que requerem acesso de caixa ou gerente"""

    def wrapper(*args, **kwargs):
        role = get_role_manager()
        if not (role.is_caixa() or role.is_gerente()):
            logger.warning(f"Acesso negado: rol desconhecido {role.role}")
            raise PermissionError("Acesso não autorizado")
        return func(*args, **kwargs)

    return wrapper
