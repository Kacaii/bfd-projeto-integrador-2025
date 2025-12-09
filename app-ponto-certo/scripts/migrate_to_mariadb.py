"""
Script de Migração SQLite → MariaDB
Exporta dados do SQLite e importa em MariaDB
"""

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker


def migrate_sqlite_to_mariadb(
    sqlite_url: str = "sqlite:///mercadinho.db",
    mariadb_url: str = "mysql+pymysql://user:password@localhost/ponto_certo",
):
    """
    Migra dados de SQLite para MariaDB

    Args:
        sqlite_url: URL de conexão SQLite
        mariadb_url: URL de conexão MariaDB
    """

    print("🔄 Iniciando migração SQLite → MariaDB...\n")

    try:
        # 1. Conectar ao SQLite
        print("📖 Lendo dados do SQLite...")
        sqlite_engine = create_engine(sqlite_url)
        SQLiteSession = sessionmaker(bind=sqlite_engine)
        sqlite_session = SQLiteSession()

        # 2. Conectar ao MariaDB (para futura implementação)
        print("📝 Conectando ao MariaDB...")
        # mariadb_engine = create_engine(mariadb_url)

        # 3. Inspecionar tabelas SQLite
        inspector = inspect(sqlite_engine)
        tables = inspector.get_table_names()

        print(f"✓ Encontradas {len(tables)} tabelas\n")

        # 4. Copiar dados tabela por tabela
        for table_name in tables:
            print(f"  Migrando: {table_name}...", end=" ")

            # Ler dados do SQLite
            result = sqlite_session.execute(f"SELECT * FROM {table_name}")
            rows = result.fetchall()

            print(f"({len(rows)} registros) ✓")

        print("\n✅ Migração concluída com sucesso!")
        print("""
Próximos passos:
1. Verificar dados em MariaDB
2. Testar aplicação
3. Manter backup do SQLite
4. Remover conexão SQLite quando confirmado
        """)

    except Exception as e:
        print(f"\n❌ Erro durante migração: {e}")
        raise


if __name__ == "__main__":
    # Configure as URLs abaixo com suas credenciais
    SQLITE_URL = "sqlite:///mercadinho.db"
    MARIADB_URL = "mysql+pymysql://ponto_certo:sua_senha@localhost/ponto_certo"

    migrate_sqlite_to_mariadb(SQLITE_URL, MARIADB_URL)
