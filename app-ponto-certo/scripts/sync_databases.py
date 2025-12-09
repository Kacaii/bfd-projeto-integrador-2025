#!/usr/bin/env python3
"""
Script de Sincronização entre SQLite e MariaDB
Copia dados de um banco para outro
"""

import os
import sys
import argparse
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, select
from sqlalchemy.orm import sessionmaker

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseSync:
    """Sincroniza dados entre SQLite e MariaDB"""

    def __init__(self, source_type: str, dest_type: str):
        self.source_type = source_type.lower()
        self.dest_type = dest_type.lower()

        self.source_engine = self._get_engine(self.source_type)
        self.dest_engine = self._get_engine(self.dest_type)

        logger.info(f"Origem: {self.source_type.upper()}")
        logger.info(f"Destino: {self.dest_type.upper()}")

    def _get_engine(self, db_type: str):
        """Cria engine para o tipo de banco especificado"""
        if db_type == "sqlite":
            db_path = os.getenv("SQLITE_DATABASE", "./mercadinho.db")
            connection_string = f"sqlite:///{db_path}"
            logger.info(f"SQLite: {db_path}")
            return create_engine(connection_string)

        elif db_type == "mariadb":
            host = os.getenv("MARIADB_HOST", "localhost")
            port = os.getenv("MARIADB_PORT", "3306")
            user = os.getenv("MARIADB_USER")
            password = os.getenv("MARIADB_PASSWORD")
            database = os.getenv("MARIADB_DATABASE")

            if not all([user, password, database]):
                raise ValueError("Variáveis MariaDB não configuradas no .env")

            connection_string = (
                f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
            )
            logger.info(f"MariaDB: {host}:{port}/{database}")
            return create_engine(connection_string)

        else:
            raise ValueError(f"Tipo de banco desconhecido: {db_type}")

    def sync(self):
        """Executa a sincronização completa"""
        try:
            logger.info("Iniciando sincronização...")

            # Obter metadados da origem
            source_metadata = MetaData()
            source_metadata.reflect(bind=self.source_engine)

            # Copiar dados para cada tabela
            source_session = sessionmaker(bind=self.source_engine)()
            dest_session = sessionmaker(bind=self.dest_engine)()

            for table_name in source_metadata.tables:
                self._sync_table(
                    table_name, source_metadata, source_session, dest_session
                )

            source_session.close()
            dest_session.close()

            logger.info("✓ Sincronização concluída com sucesso!")

        except Exception as e:
            logger.error(f"✗ Erro durante sincronização: {e}")
            sys.exit(1)

    def _sync_table(self, table_name: str, metadata, source_session, dest_session):
        """Sincroniza uma tabela específica"""
        try:
            table = metadata.tables[table_name]

            # Limpar tabela de destino
            dest_session.execute(table.delete())

            # Copiar dados
            rows = source_session.execute(select(table))

            for row in rows:
                dest_session.execute(table.insert().values(**row._mapping))

            dest_session.commit()

            logger.info(f"✓ Tabela '{table_name}' sincronizada")

        except Exception as e:
            logger.warning(f"⚠ Erro ao sincronizar '{table_name}': {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Sincroniza dados entre SQLite e MariaDB"
    )
    parser.add_argument(
        "--from",
        dest="source",
        required=True,
        choices=["sqlite", "mariadb"],
        help="Banco de origem",
    )
    parser.add_argument(
        "--to",
        dest="destination",
        required=True,
        choices=["sqlite", "mariadb"],
        help="Banco de destino",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Apenas simula, não executa"
    )

    args = parser.parse_args()

    if args.source == args.destination:
        logger.error("Origem e destino não podem ser iguais!")
        sys.exit(1)

    if args.dry_run:
        logger.warning("MODO DRY-RUN: Nenhum dado será copiado")

    sync = DatabaseSync(args.source, args.destination)
    sync.sync()


if __name__ == "__main__":
    main()
