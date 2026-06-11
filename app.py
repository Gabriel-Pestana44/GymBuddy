from flask import (
    Flask,
    request,
    render_template,
    session,
    redirect,
    flash,
    url_for
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
    if "usuario_id" in session:
        return redirect(url_for("home"))
    return render_template("index.html")


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        senha = request.form["senha"]
        cidade = request.form["cidade"]
        estado = request.form["estado"].upper().strip()

        senha_hash = generate_password_hash(senha)
        conexao = conectar()

        try:
            conexao.execute(
                """
                INSERT INTO usuarios (nome, email, senha, cidade, estado)
                VALUES (?, ?, ?, ?, ?)
                """,
                (nome, email, senha_hash, cidade, estado)
            )
            conexao.commit()
            flash("Usuário cadastrado com sucesso! Faça seu login.", "sucesso")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Este e-mail já está cadastrado!", "erro")
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
            "SELECT * FROM usuarios WHERE email = ?", (email,)
        ).fetchone()
        conexao.close()

        if usuario is None:
            flash("Usuário não encontrado!", "erro")
            return render_template("login.html")

        if check_password_hash(usuario["senha"], senha):
            session["usuario_id"] = usuario["id"]
            session["usuario_nome"] = usuario["nome"]
            session["usuario_cidade"] = usuario["cidade"]
            session["usuario_estado"] = usuario["estado"]
            return redirect(url_for("home"))

        flash("Senha incorreta!", "erro")

    return render_template("login.html")


@app.route("/home")
def home():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    conexao = conectar()
    termo = request.args.get("busca", "").strip()

    # ==========================================
    # MODO BUSCA
    # ==========================================
    if termo:
        resultados = conexao.execute(
            """
            SELECT * FROM eventos
            WHERE (
                LOWER(nome) LIKE LOWER(?)
                OR LOWER(cidade) LIKE LOWER(?)
                OR LOWER(estado) LIKE LOWER(?)
                OR LOWER(descricao) LIKE LOWER(?)
            )
            AND date(data) BETWEEN date('now', '-3 days') AND date('now', '+30 days')
            ORDER BY data
            """,
            (f"%{termo}%", f"%{termo}%", f"%{termo}%", f"%{termo}%")
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
        SELECT * FROM eventos
        WHERE estado = ?
        AND date(data) BETWEEN date('now', '-3 days') AND date('now', '+30 days')
        ORDER BY data
        """,
        (session["usuario_estado"],)
    ).fetchall()

    meus_eventos = conexao.execute(
        """
        SELECT DISTINCT eventos.* FROM eventos
        JOIN participantes ON participantes.evento_id = eventos.id
        WHERE participantes.usuario_id = ?
        ORDER BY eventos.data
        """,
        (session["usuario_id"],)
    ).fetchall()

    eventos_criados = conexao.execute(
        "SELECT * FROM eventos WHERE criador_id = ? ORDER BY data",
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
        return redirect(url_for("login"))

    if request.method == "POST":
        nome = request.form["nome"]
        descricao = request.form["descricao"]
        cidade = request.form["cidade"]
        estado = request.form["estado"].upper().strip()
        data = request.form["data"]
        horario = request.form["horario"]
        local = request.form["local"]
        status = request.form["status"]

        conexao = conectar()
        cursor = conexao.cursor()

        cursor.execute(
            """
            INSERT INTO eventos (nome, descricao, cidade, estado, data, horario, local, status, criador_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (nome, descricao, cidade, estado, data, horario, local, status, session["usuario_id"])
        )
        evento_id = cursor.lastrowid
        conexao.commit()
        conexao.close()

        flash("Evento criado com sucesso!", "sucesso")
        return redirect(url_for("ver_evento", evento_id=evento_id))

    return render_template("evento.html")


@app.route("/evento/<int:evento_id>")
def ver_evento(evento_id):
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    conexao = conectar()

    evento = conexao.execute(
        """
        SELECT eventos.*, usuarios.nome AS criador_nome
        FROM eventos
        JOIN usuarios ON eventos.criador_id = usuarios.id
        WHERE eventos.id = ?
        """,
        (evento_id,)
    ).fetchone()

    if evento is None:
        conexao.close()
        flash("Evento não encontrado!", "erro")
        return redirect(url_for("home"))

    participantes = conexao.execute(
        """
        SELECT usuarios.id, usuarios.nome, participantes.status_presenca, participantes.status_convite
        FROM participantes
        JOIN usuarios ON participantes.usuario_id = usuarios.id
        WHERE participantes.evento_id = ?
        """,
        (evento_id,)
    ).fetchall()

    total_participantes = len(participantes)
    confirmados = sum(1 for p in participantes if p["status_presenca"] == "CONFIRMADO")
    negados = sum(1 for p in participantes if p["status_presenca"] == "NEGADO")
    pendentes = total_participantes - (confirmados + negados)

    meu_registro = conexao.execute(
        "SELECT * FROM participantes WHERE usuario_id = ? AND evento_id = ?",
        (session["usuario_id"], evento_id)
    ).fetchone()

    eh_admin = (evento["criador_id"] == session["usuario_id"])

    solicitacoes = conexao.execute(
        """
        SELECT participantes.id, usuarios.nome
        FROM participantes
        JOIN usuarios ON usuarios.id = participantes.usuario_id
        WHERE participantes.evento_id = ? AND participantes.status_convite = 'PENDENTE'
        """,
        (evento_id,)
    ).fetchall()

    conexao.close()

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
        return redirect(url_for("login"))

    conexao = conectar()
    evento = conexao.execute("SELECT * FROM eventos WHERE id = ?", (evento_id,)).fetchone()

    if evento is None:
        conexao.close()
        flash("Evento não encontrado!", "erro")
        return redirect(url_for("home"))

    # CORREÇÃO 1: Adicionado o 'return' que faltava para evitar dupla execução
    banido = conexao.execute(
        "SELECT * FROM participantes_banidos WHERE usuario_id = ? AND evento_id = ?",
        (session["usuario_id"], evento_id)
    ).fetchone()

    if banido:
        conexao.close()
        flash("Você foi removido e banido deste evento pelo administrador.", "erro")
        return redirect(url_for("home"))

    if evento["criador_id"] == session["usuario_id"]:
        conexao.close()
        flash("Você é o organizador deste evento!", "info")
        return redirect(url_for("ver_evento", evento_id=evento_id))

    try:
        status_convite = "ACEITO" if evento["status"] == "ABERTO" else "PENDENTE"
        conexao.execute(
            """
            INSERT INTO participantes (usuario_id, evento_id, status_convite, status_presenca)
            VALUES (?, ?, ?, 'PENDENTE')
            """,
            (session["usuario_id"], evento_id, status_convite)
        )
        conexao.commit()
        flash("Inscrição realizada com sucesso!", "sucesso")
    except sqlite3.IntegrityError:
        flash("Você já fez uma solicitação ou participa deste evento!", "info")
    finally:
        conexao.close()

    return redirect(url_for("ver_evento", evento_id=evento_id))


@app.route("/confirmar-presenca/<int:evento_id>")
def confirmar_presenca(evento_id):
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    conexao = conectar()
    registro = conexao.execute(
        "SELECT * FROM participantes WHERE usuario_id = ? AND evento_id = ?",
        (session["usuario_id"], evento_id)
    ).fetchone()

    if registro is None or registro["status_convite"] != "ACEITO":
        conexao.close()
        flash("Você não tem permissão para confirmar presença ainda.", "erro")
        return redirect(url_for("ver_evento", evento_id=evento_id))

    conexao.execute(
        "UPDATE participantes SET status_presenca = 'CONFIRMADO' WHERE usuario_id = ? AND evento_id = ?",
        (session["usuario_id"], evento_id)
    )
    conexao.commit()
    conexao.close()

    flash("Presença confirmada!", "sucesso")
    return redirect(url_for("ver_evento", evento_id=evento_id))


@app.route("/negar-presenca/<int:evento_id>")
def negar_presenca(evento_id):
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    conexao = conectar()
    registro = conexao.execute(
        "SELECT * FROM participantes WHERE usuario_id = ? AND evento_id = ?",
        (session["usuario_id"], evento_id)
    ).fetchone()

    if registro is None or registro["status_convite"] != "ACEITO":
        conexao.close()
        flash("Registro inválido.", "erro")
        return redirect(url_for("ver_evento", evento_id=evento_id))

    conexao.execute(
        "UPDATE participantes SET status_presenca = 'NEGADO' WHERE usuario_id = ? AND evento_id = ?",
        (session["usuario_id"], evento_id)
    )
    conexao.commit()
    conexao.close()

    flash("Você marcou que não vai a este evento.", "info")
    return redirect(url_for("ver_evento", evento_id=evento_id))


@app.route("/aprovar/<int:participante_id>")
def aprovar_solicitacao(participante_id):
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    conexao = conectar()
    participante = conexao.execute(
        "SELECT evento_id FROM participantes WHERE id = ?", (participante_id,)
    ).fetchone()

    if participante is None:
        conexao.close()
        flash("Solicitação não encontrada.", "erro")
        return redirect(url_for("home"))

    conexao.execute(
        "UPDATE participantes SET status_convite = 'ACEITO' WHERE id = ?", (participante_id,)
    )
    conexao.commit()
    conexao.close()

    flash("Participante aprovado!", "sucesso")
    return redirect(url_for("ver_evento", evento_id=participante['evento_id']))


@app.route("/recusar/<int:participante_id>")
def recusar_solicitacao(participante_id):
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    conexao = conectar()
    participante = conexao.execute(
        "SELECT evento_id FROM participantes WHERE id = ?", (participante_id,)
    ).fetchone()

    if participante is None:
        conexao.close()
        flash("Solicitação não encontrada.", "erro")
        return redirect(url_for("home"))

    conexao.execute(
        "UPDATE participantes SET status_convite = 'RECUSADO' WHERE id = ?", (participante_id,)
    )
    conexao.commit()
    conexao.close()

    flash("Solicitação recusada.", "info")
    return redirect(url_for("ver_evento", evento_id=participante['evento_id']))


@app.route("/editar-evento/<int:evento_id>", methods=["GET", "POST"])
def editar_evento(evento_id):
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    conexao = conectar()
    evento = conexao.execute("SELECT * FROM eventos WHERE id = ?", (evento_id,)).fetchone()

    if evento is None:
        conexao.close()
        flash("Evento não encontrado!", "erro")
        return redirect(url_for("home"))

    if evento["criador_id"] != session["usuario_id"]:
        conexao.close()
        flash("Acesso negado!", "erro")
        return redirect(url_for("home"))

    if request.method == "POST":
        nome = request.form["nome"]
        descricao = request.form["descricao"]
        cidade = request.form["cidade"]
        estado = request.form["estado"].upper().strip()
        data = request.form["data"]
        horario = request.form["horario"]
        local = request.form["local"]
        status = request.form["status"]

        conexao.execute(
            """
            UPDATE eventos
            SET nome = ?, descricao = ?, cidade = ?, estado = ?, data = ?, horario = ?, local = ?, status = ?
            WHERE id = ?
            """,
            (nome, descricao, cidade, estado, data, horario, local, status, evento_id)
        )
        conexao.commit()
        conexao.close()

        flash("Evento atualizado com sucesso!", "sucesso")
        return redirect(url_for("ver_evento", evento_id=evento_id))

    conexao.close()
    return render_template("editar_evento.html", evento=evento)
    

@app.route("/editar-perfil", methods=["GET", "POST"])
def editar_perfil():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    conexao = conectar()
    usuario = conexao.execute("SELECT * FROM usuarios WHERE id = ?", (session["usuario_id"],)).fetchone()

    if usuario is None:
        conexao.close()
        session.clear()
        return redirect(url_for("login"))

    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        cidade = request.form["cidade"]
        estado = request.form["estado"].upper().strip()
        senha_atual = request.form["senha_atual"]
        nova_senha = request.form["nova_senha"]

        if not check_password_hash(usuario["senha"], senha_atual):
            conexao.close()
            flash("Senha atual incorreta!", "erro")
            return render_template("editar_perfil.html", usuario=usuario)

        conexao.execute(
            "UPDATE usuarios SET nome = ?, email = ?, cidade = ?, estado = ? WHERE id = ?",
            (nome, email, cidade, estado, session["usuario_id"])
        )

        if nova_senha.strip():
            senha_hash = generate_password_hash(nova_senha)
            conexao.execute("UPDATE usuarios SET senha = ? WHERE id = ?", (senha_hash, session["usuario_id"]))

        conexao.commit()

        session["usuario_nome"] = nome
        session["usuario_cidade"] = cidade
        session["usuario_estado"] = estado
        conexao.close()

        flash("Perfil atualizado com sucesso!", "sucesso")
        return redirect(url_for("home"))

    conexao.close()
    return render_template("editar_perfil.html", usuario=usuario)


@app.route("/deletar-evento/<int:evento_id>")
def deletar_evento(evento_id):
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    conexao = conectar()
    evento = conexao.execute("SELECT * FROM eventos WHERE id = ?", (evento_id,)).fetchone()

    if evento is None or evento["criador_id"] != session["usuario_id"]:
        conexao.close()
        flash("Acesso negado ou evento não encontrado.", "erro")
        return redirect(url_for("home"))

    conexao.execute("DELETE FROM participantes WHERE evento_id = ?", (evento_id,))
    conexao.execute("DELETE FROM eventos WHERE id = ?", (evento_id,))
    conexao.commit()
    conexao.close()

    flash("Evento excluído com sucesso.", "info")
    return redirect(url_for("home"))


@app.route("/expulsar/<int:evento_id>/<int:usuario_id>")
def expulsar_participante(evento_id, usuario_id):
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    conexao = conectar()
    evento = conexao.execute("SELECT * FROM eventos WHERE id = ?", (evento_id,)).fetchone()

    if evento is None or evento["criador_id"] != session["usuario_id"]:
        conexao.close()
        flash("Acesso negado.", "erro")
        return redirect(url_for("home"))

    conexao.execute("DELETE FROM participantes WHERE usuario_id = ? AND evento_id = ?", (usuario_id, evento_id))

    try:
        conexao.execute(
            "INSERT INTO participantes_banidos (usuario_id, evento_id) VALUES (?, ?)",
            (usuario_id, evento_id)
        )
        conexao.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conexao.close()

    flash("Participante removido e banido com sucesso.", "info")
    return redirect(url_for("ver_evento", evento_id=evento_id))


@app.route("/convidar/<int:evento_id>", methods=["GET", "POST"])
def convidar_usuario(evento_id):
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    conexao = conectar()
    evento = conexao.execute("SELECT * FROM eventos WHERE id = ?", (evento_id,)).fetchone()

    if evento is None or evento["criador_id"] != session["usuario_id"]:
        conexao.close()
        flash("Acesso negado.", "erro")
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form["email"]
        usuario = conexao.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()

        if usuario is None:
            conexao.close()
            flash("Usuário não encontrado com esse e-mail!", "erro")
            return render_template("convidar.html", evento_id=evento_id)

        try:
            conexao.execute(
                """
                INSERT INTO participantes (usuario_id, evento_id, status_convite, status_presenca)
                VALUES (?, ?, 'ACEITO', 'PENDENTE')
                """,
                (usuario["id"], evento_id)
            )
            conexao.commit()
            flash("Usuário convidado com sucesso!", "sucesso")
        except sqlite3.IntegrityError:
            flash("Este usuário já faz parte ou tem solicitação ativa neste evento.", "info")
        finally:
            conexao.close()

        return redirect(url_for("ver_evento", evento_id=evento_id))

    conexao.close()
    return render_template("convidar.html", evento_id=evento_id)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)