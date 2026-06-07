DROP TABLE IF EXISTS participantes;
DROP TABLE IF EXISTS eventos;
DROP TABLE IF EXISTS usuarios;

CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha TEXT NOT NULL,

    cidade TEXT NOT NULL,
    estado TEXT NOT NULL
);

CREATE TABLE eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    nome TEXT NOT NULL,
    descricao TEXT,

    cidade TEXT NOT NULL,
    estado TEXT NOT NULL,

    data TEXT NOT NULL,
    horario TEXT NOT NULL,

    local TEXT NOT NULL,

    status TEXT NOT NULL,

    criador_id INTEGER NOT NULL
);

CREATE TABLE participantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    usuario_id INTEGER NOT NULL,

    evento_id INTEGER NOT NULL,

    status_convite TEXT NOT NULL
        DEFAULT 'PENDENTE'
        CHECK(
            status_convite IN (
                'PENDENTE',
                'ACEITO',
                'RECUSADO'
            )
        ),

    status_presenca TEXT NOT NULL
        DEFAULT 'PENDENTE'
        CHECK(
            status_presenca IN (
                'PENDENTE',
                'CONFIRMADO',
                'NEGADO'
            )
        ),

    data_solicitacao DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(usuario_id)
        REFERENCES usuarios(id),

    FOREIGN KEY(evento_id)
        REFERENCES eventos(id),

    UNIQUE(usuario_id, evento_id)
);

CREATE TABLE participantes_banidos (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    usuario_id INTEGER NOT NULL,

    evento_id INTEGER NOT NULL,

    UNIQUE(usuario_id, evento_id)

);