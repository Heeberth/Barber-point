BEGIN TRANSACTION;
CREATE TABLE agendamento (
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
INSERT INTO "agendamento" VALUES('Q39QDHEF',1,1,'2026-11-03','10:30','concluído',3,100.0,'pago','2026-11-01 20:47:12');
INSERT INTO "agendamento" VALUES('F7PTQEVV',2,1,'2026-11-03','09:00','concluído',1,NULL,'pago','2026-11-01 20:47:13');
INSERT INTO "agendamento" VALUES('2W6VX4K8',3,1,'2026-11-03','11:00','concluído',2,NULL,'pago','2026-11-01 20:47:13');
INSERT INTO "agendamento" VALUES('CKFV9UGB',4,1,'2026-11-03','14:00','pendente',1,NULL,'aguardando','2026-11-01 20:47:13');
INSERT INTO "agendamento" VALUES('CH8TR52Z',5,1,'2026-11-03','15:00','cancelado',1,NULL,'aguardando','2026-11-01 20:47:13');
INSERT INTO "agendamento" VALUES('HPTAKKZF',6,1,'2026-11-03','16:00','faltou',3,50.0,'aguardando','2026-11-01 20:47:13');
INSERT INTO "agendamento" VALUES('EZHMTAJS',7,2,'2026-11-03','10:00','pendente',1,NULL,'aguardando','2026-11-01 20:47:13');
INSERT INTO "agendamento" VALUES('GP8XZ6YB',8,3,'2026-11-03','13:00','pendente',2,NULL,'aguardando','2026-11-01 20:47:13');
INSERT INTO "agendamento" VALUES('FWWAB9NZ',9,1,'2026-11-03','15:00','pendente',1,NULL,'aguardando','2026-11-01 20:47:38');
CREATE TABLE agendamento_servico (
  agendamento_codigo TEXT NOT NULL REFERENCES agendamento(codigo) ON DELETE CASCADE,
  servico_id INTEGER NOT NULL REFERENCES servico(id),
  preco_cobrado REAL NOT NULL,
  PRIMARY KEY (agendamento_codigo, servico_id)
);
INSERT INTO "agendamento_servico" VALUES('Q39QDHEF',1,40.0);
INSERT INTO "agendamento_servico" VALUES('Q39QDHEF',2,30.0);
INSERT INTO "agendamento_servico" VALUES('F7PTQEVV',1,40.0);
INSERT INTO "agendamento_servico" VALUES('2W6VX4K8',2,30.0);
INSERT INTO "agendamento_servico" VALUES('CKFV9UGB',4,80.0);
INSERT INTO "agendamento_servico" VALUES('CH8TR52Z',1,40.0);
INSERT INTO "agendamento_servico" VALUES('CH8TR52Z',3,20.0);
INSERT INTO "agendamento_servico" VALUES('HPTAKKZF',1,40.0);
INSERT INTO "agendamento_servico" VALUES('EZHMTAJS',1,40.0);
INSERT INTO "agendamento_servico" VALUES('EZHMTAJS',2,30.0);
INSERT INTO "agendamento_servico" VALUES('GP8XZ6YB',3,20.0);
INSERT INTO "agendamento_servico" VALUES('FWWAB9NZ',1,40.0);
CREATE TABLE barbeiro (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  senha_hash TEXT NOT NULL,
  salt TEXT NOT NULL,
  criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO "barbeiro" VALUES(1,'Carlos','carlos@bp.com','8abfa397eed7b2131736af763979efaaa967785d25112c382877efbec86eaef4','79dbc71393a68f64f8db0ebbd192d847','2026-11-01 20:47:08');
INSERT INTO "barbeiro" VALUES(2,'Rafael','rafael@bp.com','1d02c8b84ced46db226459b14300095910e314410c63cd56d2b2b2c4e5ca2d82','ae9fbe93c8d79b2724030265543a1531','2026-11-01 20:47:08');
INSERT INTO "barbeiro" VALUES(3,'Diego','diego@bp.com','57bf7de65611dbb5eb6214bba7490a7a005b14937b8631e2ddec1dbcdb54ab32','1fd2d14747d067ec1eb76326704081b5','2026-11-01 20:47:08');
CREATE TABLE cliente (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL,
  telefone TEXT NOT NULL UNIQUE,
  criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO "cliente" VALUES(1,'Marcos Lima','31988881111','2026-11-01 20:47:12');
INSERT INTO "cliente" VALUES(2,'João Pereira','31999990000','2026-11-01 20:47:13');
INSERT INTO "cliente" VALUES(3,'Pedro Alves','31977772222','2026-11-01 20:47:13');
INSERT INTO "cliente" VALUES(4,'Bruno Costa','31955554444','2026-11-01 20:47:13');
INSERT INTO "cliente" VALUES(5,'Ana Ribeiro','31944443333','2026-11-01 20:47:13');
INSERT INTO "cliente" VALUES(6,'Tiago Nunes','31933332222','2026-11-01 20:47:13');
INSERT INTO "cliente" VALUES(7,'Léo Martins','31922221111','2026-11-01 20:47:13');
INSERT INTO "cliente" VALUES(8,'Caio Dias','31911110000','2026-11-01 20:47:13');
INSERT INTO "cliente" VALUES(9,'Rafaela Torres','31966665555','2026-11-01 20:47:14');
CREATE TABLE forma_pagamento (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL UNIQUE
);
INSERT INTO "forma_pagamento" VALUES(1,'Pix');
INSERT INTO "forma_pagamento" VALUES(2,'Cartão');
INSERT INTO "forma_pagamento" VALUES(3,'Dinheiro');
CREATE TABLE lista_espera (
  id TEXT PRIMARY KEY,
  cliente_id INTEGER NOT NULL REFERENCES cliente(id),
  barbeiro_id INTEGER NOT NULL REFERENCES barbeiro(id),
  data TEXT NOT NULL,
  hora TEXT NOT NULL,
  forma_pagamento_id INTEGER NOT NULL REFERENCES forma_pagamento(id),
  troco_para REAL,
  criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE lista_espera_servico (
  espera_id TEXT NOT NULL REFERENCES lista_espera(id) ON DELETE CASCADE,
  servico_id INTEGER NOT NULL REFERENCES servico(id),
  PRIMARY KEY (espera_id, servico_id)
);
CREATE TABLE pagamento (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  agendamento_codigo TEXT NOT NULL UNIQUE REFERENCES agendamento(codigo),
  valor_bruto REAL NOT NULL,
  taxa_percentual REAL NOT NULL,
  valor_taxa REAL NOT NULL,
  valor_liquido REAL NOT NULL,
  pago_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO "pagamento" VALUES(1,'F7PTQEVV',40.0,0.2,8.0,32.0,'2026-11-01 20:47:18');
INSERT INTO "pagamento" VALUES(2,'2W6VX4K8',30.0,0.2,6.0,24.0,'2026-11-01 20:47:18');
INSERT INTO "pagamento" VALUES(3,'Q39QDHEF',70.0,0.2,14.0,56.0,'2026-11-01 20:47:25');
CREATE TABLE servico (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL UNIQUE,
  preco REAL NOT NULL CHECK (preco >= 0),
  duracao_min INTEGER NOT NULL DEFAULT 30
);
INSERT INTO "servico" VALUES(1,'Corte de cabelo',40.0,30);
INSERT INTO "servico" VALUES(2,'Barba',30.0,30);
INSERT INTO "servico" VALUES(3,'Lavagem',20.0,30);
INSERT INTO "servico" VALUES(4,'Tintura',80.0,30);
CREATE TABLE sessao (
  token TEXT PRIMARY KEY,
  barbeiro_id INTEGER NOT NULL REFERENCES barbeiro(id) ON DELETE CASCADE,
  criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO "sessao" VALUES('4d1mOOWclQbfPmNhVRjBRmL2GVX0T3i5EbZnBXeWHm0',1,'2026-11-01 20:47:17');
CREATE UNIQUE INDEX ux_horario_ativo
  ON agendamento (barbeiro_id, data, hora)
  WHERE status IN ('pendente','confirmado','concluído');
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('servico',4);
INSERT INTO "sqlite_sequence" VALUES('forma_pagamento',3);
INSERT INTO "sqlite_sequence" VALUES('barbeiro',3);
INSERT INTO "sqlite_sequence" VALUES('cliente',9);
INSERT INTO "sqlite_sequence" VALUES('pagamento',3);
COMMIT;