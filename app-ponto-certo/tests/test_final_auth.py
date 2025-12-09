from core.sgv import PDVCore
from models.db_models import init_db, get_session

engine = init_db()
session = get_session(engine)
core = PDVCore(session)

# Testando autenticação com admin/2323
user = core.authenticate_user("admin", "2323")
if user:
    print(f"✓ Autenticação bem-sucedida!")
    print(f"  Usuário: {user.username}")
    print(f"  Role: {user.role}")
    print(f"  Full name: {user.full_name}")
else:
    print("✗ Autenticação falhou!")
