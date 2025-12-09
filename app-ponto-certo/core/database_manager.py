"""
Gerenciador de Banco de Dados - Suporta SQLite e MariaDB
Seleciona automaticamente baseado na variável MODE do .env
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Gerencia conexões com SQLite (dev) ou MariaDB (produção)"""

    def __init__(self):
        self.mode = os.getenv("MODE", "development").lower()
        self.engine = self._get_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._log_info()

    def _get_engine(self):
        """Retorna engine do banco configurado"""
        if self.mode == "production":
            return self._get_mariadb_engine()
        else:
            return self._get_sqlite_engine()

    def _get_sqlite_engine(self):
        """Cria engine para SQLite (desenvolvimento)"""
        db_path = os.getenv("SQLITE_DATABASE", "./mercadinho.db")
        connection_string = f"sqlite:///{db_path}"

        logger.info(f"SQLite DB: {db_path}")

        return create_engine(
            connection_string,
            connect_args={"check_same_thread": False},
            echo=os.getenv("DEBUG", "False").lower() == "true",
        )

    def _get_mariadb_engine(self):
        """Cria engine para MariaDB (produção)"""
        host = os.getenv("MARIADB_HOST", "localhost")
        port = os.getenv("MARIADB_PORT", "3306")
        user = os.getenv("MARIADB_USER")
        password = os.getenv("MARIADB_PASSWORD")
        database = os.getenv("MARIADB_DATABASE")

        if not all([user, password, database]):
            raise ValueError(
                "Variáveis MARIADB_USER, MARIADB_PASSWORD e MARIADB_DATABASE "
                "devem ser definidas para modo production"
            )

        connection_string = (
            f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        )

        logger.info(f"MariaDB: {host}:{port}/{database}")

        return create_engine(
            connection_string,
            echo=os.getenv("DEBUG", "False").lower() == "true",
            pool_size=10,
            max_overflow=20,
        )

    def get_connection(self):
        """Retorna uma conexão com o banco"""
        return self.engine.connect()

    def get_session(self) -> Session:
        """Retorna uma nova sessão SQLAlchemy"""
        return self.SessionLocal()

    def _log_info(self):
        """Log informações de conexão"""
        logger.info(f"Modo: {self.mode.upper()}")
        logger.info(f"Engine URL: {self.engine.url}")


# Instância global
_db_manager = None


def get_db_manager() -> DatabaseManager:
    """Obtém instância global do gerenciador de banco"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def get_session() -> Session:
    """Atalho para obter uma nova sessão"""
    return get_db_manager().get_session()
