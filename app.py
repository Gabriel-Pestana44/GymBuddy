from flask import (
    Flask,
    request,
    render_template,
    session,
    redirect
)
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
import sqlite3

app = Flask(__name__)
app.secret_key = "gymbuddy123"

DATABASE = "database/gymbuddy.db"


def conectar():
    conexao = sqlite3.connect(DATABASE)
    conexao.row_factory = sqlite3.Row
    return conexao


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():

    if request.method == "POST":

        nome = request.form["nome"]
        email = request.form["email"]
        senha = request.form["senha"]
        cidade = request.form["cidade"]
        estado = request.form["estado"]

        senha_hash = generate_password_hash(senha)

        conexao = conectar()

        try:

            conexao.execute(
            """
            INSERT INTO usuarios
            (
                nome,
                email,
                senha,
                cidade,
                estado
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                nome,
                email,
                senha_hash,
                cidade,
                estado
            )
        )

            conexao.commit()

            return "Usuário cadastrado com sucesso!"

        except sqlite3.IntegrityError:

            return "Email já cadastrado!"

        finally:

            conexao.close()

    return render_template("cadastro.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        senha = request.form["senha"]
        

        conexao = conectar()

        usuario = conexao.execute(
            """
            SELECT *
            FROM usuarios
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        conexao.close()

        if usuario is None:
            return "Usuário não encontrado!"

        if check_password_hash(
            usuario["senha"],
            senha
        ):

            session["usuario_id"] = usuario["id"]
            session["usuario_nome"] = usuario["nome"]
            session["usuario_cidade"] = usuario["cidade"]
            session["usuario_estado"] = usuario["estado"]

            return redirect("/home")

        return "Senha incorreta!"

    return render_template("login.html")

@app.route("/home")
def home():

    if "usuario_id" not in session:
        return redirect("/login")

    conexao = conectar()

    termo = request.args.get(
        "busca",
        ""
    ).strip()

    # ==========================================
    # MODO BUSCA
    # ==========================================

    if termo:

        resultados = conexao.execute(
            """
            SELECT *
            FROM eventos
            WHERE
            (
                LOWER(nome) LIKE LOWER(?)
                OR LOWER(cidade) LIKE LOWER(?)
                OR LOWER(estado) LIKE LOWER(?)
                OR LOWER(descricao) LIKE LOWER(?)
            )

            AND date(data)
                BETWEEN
                    date('now', '-3 days')
                AND
                    date('now', '+30 days')

            ORDER BY data
            """,
            (
                f"%{termo}%",
                f"%{termo}%",
                f"%{termo}%",
                f"%{termo}%"
            )
        ).fetchall()

        conexao.close()

        return render_template(
            "home.html",
            nome=session["usuario_nome"],
            busca=termo,
            resultados=resultados
        )

    # ==========================================
    # HOME NORMAL
    # ==========================================

    eventos_proximos = conexao.execute(
        """
        SELECT *
        FROM eventos
        WHERE estado = ?
        AND date(data)
            BETWEEN
                date('now', '-3 days')
            AND
                date('now', '+30 days')
        ORDER BY data
        """,
        (session["usuario_estado"],)
    ).fetchall()

    meus_eventos = conexao.execute(
        """
        SELECT DISTINCT eventos.*
        FROM eventos

        JOIN participantes
            ON participantes.evento_id = eventos.id

        WHERE participantes.usuario_id = ?

        ORDER BY eventos.data
        """,
        (session["usuario_id"],)
    ).fetchall()

    eventos_criados = conexao.execute(
        """
        SELECT *
        FROM eventos
        WHERE criador_id = ?
        ORDER BY data
        """,
        (session["usuario_id"],)
    ).fetchall()

    conexao.close()

    return render_template(
        "home.html",
        nome=session["usuario_nome"],
        busca="",
        resultados=[],
        eventos_proximos=eventos_proximos,
        meus_eventos=meus_eventos,
        eventos_criados=eventos_criados
    )

@app.route("/criar-evento", methods=["GET", "POST"])
def criar_evento():

    if "usuario_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        nome = request.form["nome"]
        descricao = request.form["descricao"]

        cidade = request.form["cidade"]
        estado = request.form["estado"]

        data = request.form["data"]
        horario = request.form["horario"]
        local = request.form["local"]
        status = request.form["status"]

        conexao = conectar()

        cursor = conexao.cursor()

        cursor.execute(
            """
            INSERT INTO eventos
            (
                nome,
                descricao,
                cidade,
                estado,
                data,
                horario,
                local,
                status,
                criador_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nome,
                descricao,
                cidade,
                estado,
                data,
                horario,
                local,
                status,
                session["usuario_id"]
            )
        )

        evento_id = cursor.lastrowid

        conexao.commit()

        conexao.close()

        return f"Evento criado com ID {evento_id}"

    return render_template("evento.html")

@app.route("/evento/<int:evento_id>")
def ver_evento(evento_id):

    if "usuario_id" not in session:
        return redirect("/login")

    conexao = conectar()

    # 1. Busca os dados do evento e do criador
    evento = conexao.execute(
        """
        SELECT
            eventos.*,
            usuarios.nome AS criador_nome
        FROM eventos
        JOIN usuarios
            ON eventos.criador_id = usuarios.id
        WHERE eventos.id = ?
        """,
        (evento_id,)
    ).fetchone()

    if evento is None:
        conexao.close()
        return "Evento não encontrado!"

    # 2. Busca os participantes do evento (Trazendo do lugar antigo para cá)
    participantes = conexao.execute(
    """
    SELECT
        usuarios.id,
        usuarios.nome,
        participantes.status_presenca,
        participantes.status_convite
    FROM participantes
    JOIN usuarios
        ON participantes.usuario_id = usuarios.id
    WHERE participantes.evento_id = ?
    """,
    (evento_id,)
).fetchall()

    total_participantes = len(participantes)

    confirmados = 0
    pendentes = 0
    negados = 0

    for participante in participantes:

        if participante["status_presenca"] == "CONFIRMADO":
            confirmados += 1

        elif participante["status_presenca"] == "NEGADO":
            negados += 1

        else:
            pendentes += 1

    meu_registro = conexao.execute(
        """
        SELECT *
        FROM participantes
        WHERE usuario_id = ?
        AND evento_id = ?
        """,
        (
            session["usuario_id"],
            evento_id
        )
    ).fetchone()

    eh_admin = (
    evento["criador_id"]
    == session["usuario_id"]
)

    solicitacoes = conexao.execute(
        """
        SELECT
            participantes.id,
            usuarios.nome
        FROM participantes
        JOIN usuarios
            ON usuarios.id = participantes.usuario_id
        WHERE participantes.evento_id = ?
        AND participantes.status_convite = 'PENDENTE'
        """,
        (evento_id,)
    ).fetchall()

    # 3. Fecha a conexão após realizar todas as queries
    conexao.close()

    # 4. Agora sim, ambas as variáveis existem no escopo desta função!
    return render_template(
    "evento_detalhes.html",
    evento=evento,
    participantes=participantes,
    meu_registro=meu_registro,
    total_participantes=total_participantes,
    confirmados=confirmados,
    pendentes=pendentes,
    negados=negados,
    eh_admin=eh_admin,
    solicitacoes=solicitacoes
    )

@app.route("/participar/<int:evento_id>")
def participar_evento(evento_id):

    if "usuario_id" not in session:
        return redirect("/login")

    conexao = conectar()

    evento = conexao.execute(
        """
        SELECT *
        FROM eventos
        WHERE id = ?
        """,
        (evento_id,)
    ).fetchone()

    if evento is None:
        conexao.close()
        return "Evento não encontrado!"

    banido = conexao.execute(
    """
    SELECT *
    FROM participantes_banidos
    WHERE usuario_id = ?
    AND evento_id = ?
    """,
    (
        session["usuario_id"],
        evento_id
    )
).fetchone()

    if banido:

        conexao.close()

    return "Você foi removido deste evento pelo administrador."

    # Correção aqui: Se for o criador, barra e retorna. 
    # Se não for, o Python ignora o IF e continua executando o código abaixo!
    if evento["criador_id"] == session["usuario_id"]:
        conexao.close()
        return "Você é o criador deste evento!"

    try:
        if evento["status"] == "ABERTO":
            conexao.execute(
                """
                INSERT INTO participantes
                (
                    usuario_id,
                    evento_id,
                    status_convite,
                    status_presenca
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    session["usuario_id"],
                    evento_id,
                    "ACEITO",
                    "PENDENTE"
                )
            )
        else:
            conexao.execute(
                """
                INSERT INTO participantes
                (
                    usuario_id,
                    evento_id,
                    status_convite,
                    status_presenca
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    session["usuario_id"],
                    evento_id,
                    "PENDENTE",
                    "PENDENTE"
                )
            )

        conexao.commit()

    except sqlite3.IntegrityError:
        conexao.close()
        return "Você já participa deste evento!"

    conexao.close()
    return redirect(f"/evento/{evento_id}")

@app.route("/confirmar-presenca/<int:evento_id>")
def confirmar_presenca(evento_id):

    if "usuario_id" not in session:
        return redirect("/login")

    conexao = conectar()

    registro = conexao.execute(
        """
        SELECT *
        FROM participantes
        WHERE usuario_id = ?
        AND evento_id = ?
        """,
        (
            session["usuario_id"],
            evento_id
        )
    ).fetchone()

    if registro is None:

        conexao.close()

        return "Você não participa deste evento!"

    if registro["status_convite"] != "ACEITO":

        conexao.close()

        return "Seu convite ainda não foi aprovado!"

    conexao.execute(
        """
        UPDATE participantes
        SET status_presenca = 'CONFIRMADO'
        WHERE usuario_id = ?
        AND evento_id = ?
        """,
        (
            session["usuario_id"],
            evento_id
        )
    )

    conexao.commit()
    conexao.close()

    return redirect(f"/evento/{evento_id}")

@app.route("/negar-presenca/<int:evento_id>")
def negar_presenca(evento_id):

    if "usuario_id" not in session:
        return redirect("/login")

    conexao = conectar()

    registro = conexao.execute(
        """
        SELECT *
        FROM participantes
        WHERE usuario_id = ?
        AND evento_id = ?
        """,
        (
            session["usuario_id"],
            evento_id
        )
    ).fetchone()

    if registro is None:

        conexao.close()

        return "Você não participa deste evento!"

    if registro["status_convite"] != "ACEITO":

        conexao.close()

        return "Seu convite ainda não foi aprovado!"

    conexao.execute(
        """
        UPDATE participantes
        SET status_presenca = 'NEGADO'
        WHERE usuario_id = ?
        AND evento_id = ?
        """,
        (
            session["usuario_id"],
            evento_id
        )
    )

    conexao.commit()
    conexao.close()

    return redirect(f"/evento/{evento_id}")

@app.route("/aprovar/<int:participante_id>")
def aprovar_solicitacao(participante_id):

    if "usuario_id" not in session:
        return redirect("/login")

    conexao = conectar()

    participante = conexao.execute(
        """
        SELECT evento_id
        FROM participantes
        WHERE id = ?
        """,
        (participante_id,)
    ).fetchone()

    if participante is None:
        conexao.close()
        return "Participante não encontrado!"

    conexao.execute(
        """
        UPDATE participantes
        SET status_convite = 'ACEITO'
        WHERE id = ?
        """,
        (participante_id,)
    )

    conexao.commit()
    conexao.close()

    return redirect(
        f"/evento/{participante['evento_id']}"
    )

@app.route("/recusar/<int:participante_id>")
def recusar_solicitacao(participante_id):

    if "usuario_id" not in session:
        return redirect("/login")

    conexao = conectar()

    participante = conexao.execute(
        """
        SELECT evento_id
        FROM participantes
        WHERE id = ?
        """,
        (participante_id,)
    ).fetchone()

    if participante is None:
        conexao.close()
        return "Participante não encontrado!"

    conexao.execute(
        """
        UPDATE participantes
        SET status_convite = 'RECUSADO'
        WHERE id = ?
        """,
        (participante_id,)
    )

    conexao.commit()
    conexao.close()

    return redirect(
        f"/evento/{participante['evento_id']}"
    )

@app.route("/editar-evento/<int:evento_id>",methods=["GET", "POST"])
def editar_evento(evento_id):

    if "usuario_id" not in session:
        return redirect("/login")

    conexao = conectar()

    evento = conexao.execute(
        """
        SELECT *
        FROM eventos
        WHERE id = ?
        """,
        (evento_id,)
    ).fetchone()

    if evento is None:

        conexao.close()

        return "Evento não encontrado!"

    if evento["criador_id"] != session["usuario_id"]:

        conexao.close()

        return "Acesso negado!"

    if request.method == "POST":

        nome = request.form["nome"]
        descricao = request.form["descricao"]
        cidade = request.form["cidade"]
        estado = request.form["estado"]
        data = request.form["data"]
        horario = request.form["horario"]
        local = request.form["local"]
        status = request.form["status"]

        conexao.execute(
            """
            UPDATE eventos
            SET
                nome = ?,
                descricao = ?,
                cidade = ?,
                estado = ?,
                data = ?,
                horario = ?,
                local = ?,
                status = ?
            WHERE id = ?
            """,
            (
                nome,
                descricao,
                cidade,
                estado,
                data,
                horario,
                local,
                status,
                evento_id
            )
        )

        conexao.commit()
        conexao.close()

        return redirect(f"/evento/{evento_id}")

    conexao.close()

    return render_template(
        "editar_evento.html",
        evento=evento
    )
    
@app.route("/editar-perfil", methods=["GET", "POST"])
def editar_perfil():

    if "usuario_id" not in session:
        return redirect("/login")

    conexao = conectar()

    usuario = conexao.execute(
        """
        SELECT *
        FROM usuarios
        WHERE id = ?
        """,
        (session["usuario_id"],)
    ).fetchone()

    if usuario is None:

        conexao.close()

        session.clear()

        return redirect("/login")

    if request.method == "POST":

        nome = request.form["nome"]
        email = request.form["email"]
        cidade = request.form["cidade"]
        estado = request.form["estado"]

        senha_atual = request.form["senha_atual"]
        nova_senha = request.form["nova_senha"]

        # Verifica a senha atual
        if not check_password_hash(
            usuario["senha"],
            senha_atual
        ):

            conexao.close()

            return "Senha atual incorreta!"

        # Atualiza os dados básicos
        conexao.execute(
            """
            UPDATE usuarios
            SET
                nome = ?,
                email = ?,
                cidade = ?,
                estado = ?
            WHERE id = ?
            """,
            (
                nome,
                email,
                cidade,
                estado,
                session["usuario_id"]
            )
        )

        # Atualiza senha somente se o campo foi preenchido
        if nova_senha.strip():

            senha_hash = generate_password_hash(
                nova_senha
            )

            conexao.execute(
                """
                UPDATE usuarios
                SET senha = ?
                WHERE id = ?
                """,
                (
                    senha_hash,
                    session["usuario_id"]
                )
            )

        conexao.commit()

        session["usuario_nome"] = nome
        session["usuario_cidade"] = cidade
        session["usuario_estado"] = estado

        conexao.close()

        return redirect("/home")

    conexao.close()

    return render_template(
        "editar_perfil.html",
        usuario=usuario
    )

@app.route("/deletar-evento/<int:evento_id>")
def deletar_evento(evento_id):

    if "usuario_id" not in session:
        return redirect("/login")

    conexao = conectar()

    evento = conexao.execute(
        """
        SELECT *
        FROM eventos
        WHERE id = ?
        """,
        (evento_id,)
    ).fetchone()

    if evento is None:

        conexao.close()

        return "Evento não encontrado!"

    if evento["criador_id"] != session["usuario_id"]:

        conexao.close()

        return "Acesso negado!"

    conexao.execute(
        """
        DELETE FROM participantes
        WHERE evento_id = ?
        """,
        (evento_id,)
    )

    conexao.execute(
        """
        DELETE FROM eventos
        WHERE id = ?
        """,
        (evento_id,)
    )

    conexao.commit()
    conexao.close()

    return redirect("/home")

@app.route("/expulsar/<int:evento_id>/<int:usuario_id>")
def expulsar_participante(evento_id, usuario_id):

    if "usuario_id" not in session:
        return redirect("/login")

    conexao = conectar()

    evento = conexao.execute(
        """
        SELECT *
        FROM eventos
        WHERE id = ?
        """,
        (evento_id,)
    ).fetchone()

    if evento is None:

        conexao.close()

        return "Evento não encontrado!"

    if evento["criador_id"] != session["usuario_id"]:

        conexao.close()

        return "Acesso negado!"

    conexao.execute(
        """
        DELETE FROM participantes
        WHERE usuario_id = ?
        AND evento_id = ?
        """,
        (
            usuario_id,
            evento_id
        )
    )

    try:

        conexao.execute(
            """
            INSERT INTO participantes_banidos
            (
                usuario_id,
                evento_id
            )
            VALUES (?, ?)
            """,
            (
                usuario_id,
                evento_id
            )
        )

    except sqlite3.IntegrityError:
        pass

    conexao.commit()
    conexao.close()

    return redirect(f"/evento/{evento_id}")

@app.route("/convidar/<int:evento_id>",methods=["GET", "POST"])
def convidar_usuario(evento_id):

    if "usuario_id" not in session:
        return redirect("/login")

    conexao = conectar()

    evento = conexao.execute(
        """
        SELECT *
        FROM eventos
        WHERE id = ?
        """,
        (evento_id,)
    ).fetchone()

    if evento["criador_id"] != session["usuario_id"]:

        conexao.close()

        return "Acesso negado!"

    if request.method == "POST":

        email = request.form["email"]

        usuario = conexao.execute(
            """
            SELECT *
            FROM usuarios
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        if usuario is None:

            conexao.close()

            return "Usuário não encontrado!"

        try:

            conexao.execute(
                """
                INSERT INTO participantes
                (
                    usuario_id,
                    evento_id,
                    status_convite,
                    status_presenca
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    usuario["id"],
                    evento_id,
                    "ACEITO",
                    "PENDENTE"
                )
            )

            conexao.commit()

        except sqlite3.IntegrityError:

            conexao.close()

            return "Usuário já está no evento!"

        conexao.close()

        return redirect(f"/evento/{evento_id}")

    conexao.close()

    return render_template(
        "convidar.html",
        evento_id=evento_id
    )



    if "usuario_id" not in session:
        return redirect("/login")

    resultados = []

    termo = ""

    if request.method == "POST":

        termo = request.form["termo"].strip()

        conexao = conectar()

        resultados = conexao.execute(
            """
            SELECT *
            FROM eventos
            WHERE
                (
                    LOWER(nome) LIKE LOWER(?)
                    OR LOWER(cidade) LIKE LOWER(?)
                    OR LOWER(estado) LIKE LOWER(?)
                    OR LOWER(descricao) LIKE LOWER(?)
                )
            AND date(data)
                BETWEEN
                    date('now', '-3 days')
                AND
                    date('now', '+30 days')
            ORDER BY data
            """,
            (
                f"%{termo}%",
                f"%{termo}%",
                f"%{termo}%",
                f"%{termo}%"
            )
        ).fetchall()

        conexao.close()

    return render_template(
        "buscar.html",
        resultados=resultados,
        termo=termo
    )


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)