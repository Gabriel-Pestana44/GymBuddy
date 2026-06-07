import sqlite3

with open("schema.sql", "r", encoding="utf-8") as arquivo:
    sql = arquivo.read()

conexao = sqlite3.connect("database/gymbuddy.db")

conexao.executescript(sql)

conexao.commit()
conexao.close()

print("Banco criado com sucesso!")