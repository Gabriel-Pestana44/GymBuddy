import sqlite3
from werkzeug.security import generate_password_hash

DATABASE = "database/gymbuddy.db"


def popular_banco():
    # 1. Conecta ao banco de dados
    conexao = sqlite3.connect(DATABASE)
    cursor = conexao.cursor()

    print("Gerando hash da senha '123'...")
    senha_comum_hash = generate_password_hash("123")

    # 2. Dados fictícios de usuários (Todos com senha '123')
    usuarios = [
        (
            "Gabriel Pestana",
            "pestana@email.com",
            senha_comum_hash,
            "Rio de Janeiro",
            "RJ",
        ),
        (
            "Lucas Silva",
            "lucas@email.com",
            senha_comum_hash,
            "Rio de Janeiro",
            "RJ",
        ),
        (
            "Ana Costa",
            "ana@email.com",
            senha_comum_hash,
            "São Paulo",
            "SP",
        ),
    ]

    print("Inserindo usuários de teste...")
    cursor.executemany(
        """
        INSERT INTO usuarios (nome, email, senha, cidade, estado)
        VALUES (?, ?, ?, ?, ?)
        """,
        usuarios,
    )

    # 3. Dados fictícios de eventos para testar o sistema
    # Como o feed da Home filtra por 'estado', criamos eventos no RJ e em SP
    eventos = [
        (
            "Treino de Peito Insano",
            "Focar em supino reto, inclinado e crucifixo. Levar garrafa d'água.",
            "Rio de Janeiro",
            "RJ",
            "2026-06-15",
            "19:00",
            "Academia Iron",
            "ABERTO",
            1,  # Criador: Gabriel (id 1)
        ),
        (
            "Corrida na Praia de Copacabana",
            "Cárdio de 5km na orla. Ritmo leve para intermediário.",
            "Rio de Janeiro",
            "RJ",
            "2026-06-20",
            "07:30",
            "Posto 3",
            "FECHADO",
            2,  # Criador: Lucas (id 2)
        ),
        (
            "Treino Funcional no Parque",
            "Circuito de alta intensidade focado em pernas e abdômen.",
            "São Paulo",
            "SP",
            "2026-06-18",
            "18:00",
            "Parque do Ibirapuera",
            "ABERTO",
            3,  # Criador: Ana (id 3)
        ),
    ]

    print("Inserindo eventos de teste...")
    cursor.executemany(
        """
        INSERT INTO eventos (nome, descricao, cidade, estado, data, horario, local, status, criador_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        eventos,
    )

    # 4. Dados fictícios de participação para testar as listas e pendências
    participantes = [
        (2, 1, "ACEITO", "CONFIRMADO"),  # Lucas (id 2) vai no evento do Gabriel (id 1)
        (3, 1, "PENDENTE", "PENDENTE"),  # Ana (id 3) pediu para ir no evento do Gabriel (id 1)
    ]

    print("Inserindo participações de teste...")
    cursor.executemany(
        """
        INSERT INTO participantes (usuario_id, evento_id, status_convite, status_presenca)
        VALUES (?, ?, ?, ?)
        """,
        participantes,
    )

    # Salva as alterações e fecha a conexão
    conexao.commit()
    conexao.close()
    print("\nBanco de dados populado com sucesso para testes!")


if __name__ == "__main__":
    popular_banco()