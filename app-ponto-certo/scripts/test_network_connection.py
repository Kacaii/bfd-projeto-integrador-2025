#!/usr/bin/env python3
"""
Teste de Conexão de Rede - MariaDB
Verifica se ambos computadores conseguem acessar o servidor
"""

import os
import sys
import socket
import argparse
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class NetworkTest:
    """Testa conectividade entre computadores e servidor MariaDB"""

    def __init__(self):
        self.host = os.getenv("MARIADB_HOST", "localhost")
        self.port = int(os.getenv("MARIADB_PORT", 3306))
        self.user = os.getenv("MARIADB_USER")
        self.password = os.getenv("MARIADB_PASSWORD")
        self.database = os.getenv("MARIADB_DATABASE")

    def run_all_tests(self):
        """Executa todos os testes"""
        logger.info("=" * 60)
        logger.info("TESTE DE CONEXÃO - MARIADB EM REDE")
        logger.info("=" * 60)

        results = {
            "rede": self.test_network(),
            "porta": self.test_port(),
            "banco": self.test_database(),
            "dados": self.test_query(),
        }

        self.print_summary(results)
        return all(results.values())

    def test_network(self):
        """Testa conectividade de rede com ping"""
        logger.info("\n[1/4] Testando conectividade de rede...")

        try:
            socket.gethostbyname(self.host)
            logger.info(f"✓ Host '{self.host}' é acessível")
            return True
        except socket.gaierror:
            logger.error(f"✗ Host '{self.host}' não encontrado")
            return False

    def test_port(self):
        """Testa se porta 3306 está aberta"""
        logger.info("\n[2/4] Testando porta MariaDB (3306)...")

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((self.host, self.port))
            sock.close()

            if result == 0:
                logger.info(f"✓ Porta {self.port} está aberta")
                return True
            else:
                logger.error(f"✗ Porta {self.port} está fechada ou bloqueada")
                logger.error("   Verificar firewall ou MariaDB não está rodando")
                return False

        except Exception as e:
            logger.error(f"✗ Erro ao testar porta: {e}")
            return False

    def test_database(self):
        """Testa conexão com banco de dados"""
        logger.info("\n[3/4] Testando conexão com MariaDB...")

        try:
            connection_string = (
                f"mysql+pymysql://{self.user}:{self.password}@"
                f"{self.host}:{self.port}/{self.database}"
            )
            engine = create_engine(connection_string, echo=False)

            with engine.connect():
                logger.info(f"✓ Conectado ao banco '{self.database}'")
                return True

        except OperationalError as e:
            logger.error(f"✗ Erro de conexão: {e}")
            if "Access denied" in str(e):
                logger.error("   Verificar usuário/senha")
            elif "Unknown database" in str(e):
                logger.error("   Banco não existe. Criar com:")
                logger.error("   CREATE DATABASE ponto_certo CHARACTER SET utf8mb4;")
            return False
        except Exception as e:
            logger.error(f"✗ Erro inesperado: {e}")
            return False

    def test_query(self):
        """Testa execução de query no banco"""
        logger.info("\n[4/4] Testando query no banco...")

        try:
            connection_string = (
                f"mysql+pymysql://{self.user}:{self.password}@"
                f"{self.host}:{self.port}/{self.database}"
            )
            engine = create_engine(connection_string, echo=False)

            with engine.connect() as conn:
                result = conn.execute(text("SELECT NOW() as hora"))
                row = result.fetchone()
                hora = row[0] if row else "N/A"
                logger.info("✓ Query executada com sucesso")
                logger.info(f"  Hora no servidor: {hora}")
                return True

        except Exception as e:
            logger.error(f"✗ Erro ao executar query: {e}")
            return False

    def print_summary(self, results):
        """Imprime resumo dos testes"""
        logger.info("\n" + "=" * 60)
        logger.info("RESUMO DOS TESTES")
        logger.info("=" * 60)

        tests = {
            "Rede": results["rede"],
            "Porta 3306": results["porta"],
            "Banco de Dados": results["banco"],
            "Query": results["dados"],
        }

        for name, passed in tests.items():
            status = "✓ PASSOU" if passed else "✗ FALHOU"
            logger.info(f"{name:20} {status}")

        logger.info("=" * 60)

        if all(results.values()):
            logger.info("✓ TODOS OS TESTES PASSARAM - Sistema pronto!")
            logger.info("\nVocê pode iniciar o app em ambos computadores:")
            logger.info("  python app.py")
        else:
            logger.error("\n✗ Alguns testes falharam - Verificar acima")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Testa conectividade de rede para MariaDB"
    )
    parser.add_argument("--host", help="IP do servidor MariaDB (padrão: do .env)")

    args = parser.parse_args()

    tester = NetworkTest()

    if args.host:
        tester.host = args.host
        logger.info(f"Usando host: {args.host}")

    success = tester.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
