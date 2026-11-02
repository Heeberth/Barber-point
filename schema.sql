-- Barber Point: modelo relacional (SQLite). Normalizado até a 3FN.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS barbeiro (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  senha_hash TEXT NOT NULL,
  salt TEXT NOT NULL,
  criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sessao (
  token TEXT PRIMARY KEY,
  barbeiro_id INTEGER NOT NULL REFERENCES barbeiro(id) ON DELETE CASCADE,
  criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS cliente (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL,
  telefone TEXT NOT NULL UNIQUE,
  criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS servico (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL UNIQUE,
  preco REAL NOT NULL CHECK (preco >= 0),
  duracao_min INTEGER NOT NULL DEFAULT 30
);
CREATE TABLE IF NOT EXISTS forma_pagamento (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS agendamento (
  codigo TEXT PRIMARY KEY,
  cliente_id INTEGER NOT NULL REFERENCES cliente(id),
  barbeiro_id INTEGER NOT NULL REFERENCES barbeiro(id),
  data TEXT NOT NULL,
  hora TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pendente'
    CHECK (status IN ('pendente','confirmado','concluído','cancelado','faltou')),
  forma_pagamento_id INTEGER NOT NULL REFERENCES forma_pagamento(id),
  troco_para REAL,
  pagamento_status TEXT NOT NULL DEFAULT 'aguardando'
    CHECK (pagamento_status IN ('aguardando','liberado','pago')),
  criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- Impede dois agendamentos ativos no mesmo horário do mesmo barbeiro (resolve o conflito de agenda).
CREATE UNIQUE INDEX IF NOT EXISTS ux_horario_ativo
  ON agendamento (barbeiro_id, data, hora)
  WHERE status IN ('pendente','confirmado','concluído');
CREATE TABLE IF NOT EXISTS agendamento_servico (
  agendamento_codigo TEXT NOT NULL REFERENCES agendamento(codigo) ON DELETE CASCADE,
  servico_id INTEGER NOT NULL REFERENCES servico(id),
  preco_cobrado REAL NOT NULL,
  PRIMARY KEY (agendamento_codigo, servico_id)
);
CREATE TABLE IF NOT EXISTS pagamento (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  agendamento_codigo TEXT NOT NULL UNIQUE REFERENCES agendamento(codigo),
  valor_bruto REAL NOT NULL,
  taxa_percentual REAL NOT NULL,
  valor_taxa REAL NOT NULL,
  valor_liquido REAL NOT NULL,
  pago_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS lista_espera (
  id TEXT PRIMARY KEY,
  cliente_id INTEGER NOT NULL REFERENCES cliente(id),
  barbeiro_id INTEGER NOT NULL REFERENCES barbeiro(id),
  data TEXT NOT NULL,
  hora TEXT NOT NULL,
  forma_pagamento_id INTEGER NOT NULL REFERENCES forma_pagamento(id),
  troco_para REAL,
  criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS lista_espera_servico (
  espera_id TEXT NOT NULL REFERENCES lista_espera(id) ON DELETE CASCADE,
  servico_id INTEGER NOT NULL REFERENCES servico(id),
  PRIMARY KEY (espera_id, servico_id)
);
