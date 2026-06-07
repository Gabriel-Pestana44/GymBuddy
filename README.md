# 🏋️‍♂️ GymBuddy

O **GymBuddy** é uma aplicação web focada na organização e agendamento de atividades físicas e treinos entre amigos. O objetivo principal é permitir que usuários criem eventos esportivos ou de musculação, gerenciem a participação de amigos e controlem a lista de presença de forma dinâmica e segura.

> 🚀 **Status do Projeto:** O Core do Back-end está 100% funcional e blindado com todas as regras de negócio aplicadas. A interface gráfica (Front-end) está em estágio inicial de desenvolvimento (protótipo estrutural).

---

## 🛠️ Tecnologias Utilizadas

O projeto foi construído utilizando as seguintes tecnologias no ecossistema Python e Linux:

* **Linguagem:** Python 3.12
* **Framework Web:** Flask (Modo de Desenvolvimento)
* **Banco de Dados:** SQLite3 (Persistência local leve e rápida)
* **Segurança:** Werkzeug (Criptografia de senhas com hashing seguro)
* **Template Engine:** Jinja2 (Renderização de dados no HTML)

---

## ⚙️ Funcionalidades Implementadas (Back-end)

### 🔐 Autenticação & Segurança
* **Cadastro de Usuários:** Coleta de dados geográficos (Cidade/Estado) para futuras filtragens de eventos regionais.
* **Criptografia de Senhas:** Uso de hashes seguros para garantir que senhas não sejam expostas em texto puro no banco.
* **Gerenciamento de Sessão:** Controle de rotas protegidas usando `flask.session` (apenas usuários logados acessam o painel principal).

### 📅 Gestão de Eventos
* **Criação de Eventos:** Definição de nome, descrição, data, horário, local específico e status de privacidade (`ABERTO` ou `FECHADO`).
* **Filtro Regional Automático:** A timeline principal (`/home`) exibe de forma inteligente apenas os eventos criados no mesmo estado do usuário logado.
* **Edição e Exclusão:** O criador do evento possui controle total para alterar dados ou deletar o evento (o que limpa em cascata os participantes vinculados).

### 👥 Sistema de Participação & Moderamento
* **Entrada em Eventos:** Fluxo automatizado onde eventos `ABERTO` aceitam a entrada direta e eventos `FECHADO` jogam a solicitação para um estado de aprovação pendente.
* **Painel do Administrador (Criador):** Visualização exclusiva de requisições pendentes com rotas dedicadas para `Aceitar` ou `Recusar` novos membros.
* **Controle de Presença:** Interface para os participantes confirmados alterarem seu status para "Confirmado" ou "Não Vou".
* **Sistema de Banimento:** O administrador pode expulsar participantes e inseri-los em uma lista de restrição (`participantes_banidos`), impedindo novas solicitações de entrada no mesmo evento.

---

## 📂 Estrutura de Arquivos Principal

```text
├── app.py                  # Arquivo principal com as rotas e lógica do Flask
├── init_db.py              # Script de inicialização e criação das tabelas SQL
├── population_db.py        # Script para semear dados de teste controlados
├── schema.sql              # Estrutura física do Banco de Dados SQLite
├── requirements.txt        # Dependências e bibliotecas do projeto
├── .gitignore              # Filtros de arquivos para o Git ignorar (.venv, caches)
└── templates/              # Páginas HTML estruturais (Protótipo do Front)
    ├── index.html
    ├── login.html
    ├── cadastro.html
    ├── home.html
    ├── evento.html
    ├── evento_detalhes.html
    └── editar_eventos.html
