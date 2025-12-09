#!/usr/bin/env python3
import sqlite3
from passlib.hash import pbkdf2_sha256

# Conectar ao banco
conn = sqlite3.connect("mercadinho.db")
c = conn.cursor()

# Verificar usuários existentes
c.execute("SELECT username, role FROM usuarios")
usuarios_atuais = c.fetchall()

print("Usuários atuais no banco:")
for u in usuarios_atuais:
    print(f"  - {u[0]} ({u[1]})")

# Definir usuários desejados
usuarios_desejados = [
    ("admin", pbkdf2_sha256.hash("2323"), "gerente", "admin"),
    ("user_caixa", pbkdf2_sha256.hash("123"), "caixa", "Caixa 1"),
    ("user_estoque", pbkdf2_sha256.hash("456"), "estoque", "Auxiliar de Estoque"),
]

print("\nRestaurando usuários...")

# Limpar usuários antigos
c.execute("DELETE FROM usuarios")

# Inserir usuários novos
for username, pwd_hash, role, full_name in usuarios_desejados:
    c.execute(
        "INSERT INTO usuarios (username, password, role, full_name) VALUES (?, ?, ?, ?)",
        (username, pwd_hash, role, full_name),
    )
    print(f"✓ {username} ({role}) inserido")

conn.commit()

# Verificar inserção
c.execute("SELECT username, role FROM usuarios")
usuarios_finais = c.fetchall()

print(f"\nTotal de usuários: {len(usuarios_finais)}")
for u in usuarios_finais:
    print(f"  - {u[0]} ({u[1]})")

conn.close()
print("\n✓ Usuários restaurados com sucesso!")
