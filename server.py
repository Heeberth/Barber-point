"""Barber Point - back-end (Python 3, sem dependências externas).
Serve o front-end estático e uma API JSON sobre um banco relacional SQLite.
Uso: python3 server.py   ->  http://localhost:8000
"""
import hashlib, json, os, re, secrets, sqlite3
from datetime import datetime
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE = Path(__file__).parent
DB_PATH = os.environ.get("DB_PATH", str(BASE / "db" / "barberpoint.db"))
SHOP_ID = os.environ.get("SHOP_ID", "BP2026")        # código para cadastrar barbeiros
TAXA = float(os.environ.get("TAXA", "0.20"))          # taxa da barbearia (20%)
PORT = int(os.environ.get("PORT", "8000"))
HORAS = [f"{h:02d}:{m}" for h in range(9, 18) for m in ("00", "30")]
ATIVOS = ("pendente", "confirmado", "concluído")
ALFA = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def conectar():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def hash_senha(senha, salt):
    return hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(salt), 120_000).hex()


def iniciar_banco():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with conectar() as c:
        c.executescript((BASE / "db" / "schema.sql").read_text(encoding="utf-8"))
        if not c.execute("SELECT 1 FROM servico").fetchone():
            c.executemany("INSERT INTO servico(nome, preco) VALUES (?,?)",
                          [("Corte de cabelo", 40), ("Barba", 30), ("Lavagem", 20), ("Tintura", 80)])
            c.executemany("INSERT INTO forma_pagamento(nome) VALUES (?)", [("Pix",), ("Cartão",), ("Dinheiro",)])
            for nome, email in [("Carlos", "carlos@bp.com"), ("Rafael", "rafael@bp.com"), ("Diego", "diego@bp.com")]:
                salt = secrets.token_hex(16)
                c.execute("INSERT INTO barbeiro(nome,email,senha_hash,salt) VALUES (?,?,?,?)",
                          (nome, email, hash_senha("123456", salt), salt))


class Erro(Exception):
    def __init__(self, status, msg):
        self.status, self.msg = status, msg


def agendamento_dict(c, codigo):
    r = c.execute("""SELECT a.*, cl.nome AS cliente, cl.telefone, b.nome AS barbeiro, f.nome AS forma
        FROM agendamento a JOIN cliente cl ON cl.id=a.cliente_id JOIN barbeiro b ON b.id=a.barbeiro_id
        JOIN forma_pagamento f ON f.id=a.forma_pagamento_id WHERE a.codigo=?""", (codigo,)).fetchone()
    if not r:
        return None
    sv = [dict(s) for s in c.execute("""SELECT s.id, s.nome, x.preco_cobrado AS preco FROM agendamento_servico x
        JOIN servico s ON s.id=x.servico_id WHERE x.agendamento_codigo=?""", (codigo,))]
    return {"codigo": codigo, "cliente": r["cliente"], "telefone": r["telefone"], "barbeiro_id": r["barbeiro_id"],
            "barbeiro": r["barbeiro"], "data": r["data"], "hora": r["hora"], "status": r["status"], "forma": r["forma"],
            "troco_para": r["troco_para"], "pagamento": r["pagamento_status"], "servicos": sv,
            "total": sum(s["preco"] for s in sv)}


def validar_reserva(c, d):
    nome = str(d.get("nome", "")).strip()
    tel = re.sub(r"\D", "", str(d.get("telefone", "")))
    if len(nome) < 2 or len(nome) > 60: raise Erro(400, "Informe seu nome.")
    if len(tel) not in (10, 11): raise Erro(400, "Informe um telefone com DDD.")
    ids = sorted({int(i) for i in d.get("servicos", [])})
    precos = {r["id"]: r["preco"] for r in c.execute("SELECT id, preco FROM servico")}
    if not ids or any(i not in precos for i in ids): raise Erro(400, "Escolha ao menos um serviço válido.")
    f = c.execute("SELECT id FROM forma_pagamento WHERE nome=?", (d.get("forma"),)).fetchone()
    if not f: raise Erro(400, "Forma de pagamento inválida.")
    if not c.execute("SELECT 1 FROM barbeiro WHERE id=?", (d.get("barbeiro_id"),)).fetchone(): raise Erro(400, "Barbeiro inválido.")
    data, hora = str(d.get("data", "")), str(d.get("hora", ""))
    try: dt = datetime.strptime(data + " " + hora, "%Y-%m-%d %H:%M")
    except ValueError: raise Erro(400, "Data ou horário inválido.")
    if hora not in HORAS or dt.weekday() == 6: raise Erro(400, "Horário fora do expediente.")
    troco = d.get("troco_para")
    troco = float(troco) if troco not in (None, "") else None
    total = sum(precos[i] for i in ids)
    if d.get("forma") != "Dinheiro": troco = None
    if troco is not None and troco < total: raise Erro(400, "O valor para o troco precisa ser maior ou igual ao total.")
    return nome, tel, ids, precos, f["id"], int(d["barbeiro_id"]), data, hora, troco, dt


def upsert_cliente(c, nome, tel):
    r = c.execute("SELECT id FROM cliente WHERE telefone=?", (tel,)).fetchone()
    if r:
        c.execute("UPDATE cliente SET nome=? WHERE id=?", (nome, r["id"]))
        return r["id"]
    return c.execute("INSERT INTO cliente(nome, telefone) VALUES (?,?)", (nome, tel)).lastrowid


def criar_agendamento(c, d, checar_passado=True):
    nome, tel, ids, precos, forma_id, barb, data, hora, troco, dt = validar_reserva(c, d)
    if checar_passado and dt <= datetime.now(): raise Erro(400, "Esse horário já passou.")
    cid = upsert_cliente(c, nome, tel)
    codigo = "".join(secrets.choice(ALFA) for _ in range(8))
    try:
        c.execute("""INSERT INTO agendamento(codigo,cliente_id,barbeiro_id,data,hora,forma_pagamento_id,troco_para)
                     VALUES (?,?,?,?,?,?,?)""", (codigo, cid, barb, data, hora, forma_id, troco))
    except sqlite3.IntegrityError:
        raise Erro(409, "Esse horário acabou de ser ocupado. Escolha outro ou entre na lista de espera.")
    c.executemany("INSERT INTO agendamento_servico VALUES (?,?,?)", [(codigo, i, precos[i]) for i in ids])
    return codigo


def espera_dict(c, eid):
    r = c.execute("""SELECT e.*, cl.nome AS cliente, cl.telefone, f.nome AS forma FROM lista_espera e
        JOIN cliente cl ON cl.id=e.cliente_id JOIN forma_pagamento f ON f.id=e.forma_pagamento_id WHERE e.id=?""", (eid,)).fetchone()
    if not r: return None
    sv = [dict(s) for s in c.execute("""SELECT s.id, s.nome, s.preco FROM lista_espera_servico x JOIN servico s ON s.id=x.servico_id
        WHERE x.espera_id=?""", (eid,))]
    ocupado = c.execute(f"SELECT 1 FROM agendamento WHERE barbeiro_id=? AND data=? AND hora=? AND status IN {ATIVOS}",
                        (r["barbeiro_id"], r["data"], r["hora"])).fetchone()
    return {"id": eid, "cliente": r["cliente"], "telefone": r["telefone"], "barbeiro_id": r["barbeiro_id"], "data": r["data"],
            "hora": r["hora"], "forma": r["forma"], "troco_para": r["troco_para"], "servicos": sv, "livre": not ocupado}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def enviar(self, status, obj, extra=None):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items(): self.send_header(k, v)
        self.end_headers(); self.wfile.write(body)

    def barbeiro_logado(self, c):
        ck = cookies.SimpleCookie(self.headers.get("Cookie", ""))
        t = ck["bp_sess"].value if "bp_sess" in ck else ""
        return c.execute("""SELECT b.id, b.nome FROM sessao s JOIN barbeiro b ON b.id=s.barbeiro_id WHERE s.token=?""", (t,)).fetchone()

    def exigir_barbeiro(self, c):
        b = self.barbeiro_logado(c)
        if not b: raise Erro(401, "Faça login como barbeiro.")
        return b

    def tratar(self, metodo):
        u = urlparse(self.path); p = u.path; qs = {k: v[0] for k, v in parse_qs(u.query).items()}
        if not p.startswith("/api/"):
            if metodo != "GET": raise Erro(405, "Método não permitido.")
            return self.estatico(p)
        corpo = {}
        if metodo in ("POST", "DELETE"):
            n = int(self.headers.get("Content-Length") or 0)
            if n: corpo = json.loads(self.rfile.read(n) or b"{}")
        seg = p[5:].strip("/").split("/")
        with conectar() as c:
            r = self.rota(c, metodo, seg, qs, corpo)
        if r is not None: self.enviar(*r)

    def rota(self, c, m, s, qs, d):
        if m == "GET" and s == ["servicos"]: return 200, [dict(r) for r in c.execute("SELECT id,nome,preco FROM servico")]
        if m == "GET" and s == ["barbeiros"]: return 200, [dict(r) for r in c.execute("SELECT id,nome FROM barbeiro ORDER BY nome")]
        if m == "GET" and s == ["horarios"]:
            r = c.execute(f"SELECT hora FROM agendamento WHERE barbeiro_id=? AND data=? AND status IN {ATIVOS}", (qs.get("barbeiro"), qs.get("data")))
            return 200, [x["hora"] for x in r]
        if m == "POST" and s == ["agendamentos"]:
            return 201, {"codigo": criar_agendamento(c, d)}
        if s[0] == "agendamentos" and len(s) >= 2:
            cod = s[1].upper()
            a = agendamento_dict(c, cod)
            if m == "GET" and len(s) == 2:
                if not a: raise Erro(404, "Código não encontrado.")
                return 200, a
            if not a: raise Erro(404, "Código não encontrado.")
            if m == "POST" and s[2:] == ["cancelar"]:   # cliente cancela com o código
                if a["status"] not in ("pendente", "confirmado"): raise Erro(400, "Este agendamento não pode ser cancelado.")
                c.execute("UPDATE agendamento SET status='cancelado' WHERE codigo=?", (cod,)); return 200, {"ok": True}
            if m == "POST" and s[2:] == ["acao"]:       # ações do barbeiro
                b = self.exigir_barbeiro(c)
                if a["barbeiro_id"] != b["id"]: raise Erro(403, "Este agendamento é de outro barbeiro.")
                self.acao(c, a, d.get("acao")); return 200, {"ok": True}
        if m == "POST" and s == ["espera"]:
            nome, tel, ids, _, forma_id, barb, data, hora, troco, _dt = validar_reserva(c, d)
            eid = "".join(secrets.choice(ALFA) for _ in range(10))
            c.execute("INSERT INTO lista_espera VALUES (?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", (eid, upsert_cliente(c, nome, tel), barb, data, hora, forma_id, troco))
            c.executemany("INSERT INTO lista_espera_servico VALUES (?,?)", [(eid, i) for i in ids]); return 201, {"id": eid}
        if s[0] == "espera" and len(s) >= 2:
            e = espera_dict(c, s[1])
            if not e: raise Erro(404, "Item não encontrado.")
            if m == "GET": return 200, e
            if m == "DELETE": c.execute("DELETE FROM lista_espera WHERE id=?", (s[1],)); return 200, {"ok": True}
            if m == "POST" and s[2:] == ["reservar"]:
                cod = criar_agendamento(c, {"nome": e["cliente"], "telefone": e["telefone"], "barbeiro_id": e["barbeiro_id"], "data": e["data"],
                                            "hora": e["hora"], "servicos": [x["id"] for x in e["servicos"]], "forma": e["forma"], "troco_para": e["troco_para"]})
                c.execute("DELETE FROM lista_espera WHERE id=?", (s[1],)); return 201, {"codigo": cod}
        if m == "POST" and s == ["cadastro"]:
            if d.get("shop") != SHOP_ID: raise Erro(403, "ID da barbearia inválido.")
            nome, email, senha = str(d.get("nome", "")).strip(), str(d.get("email", "")).strip().lower(), str(d.get("senha", ""))
            if not nome or not re.match(r"^\S+@\S+\.\S+$", email): raise Erro(400, "Informe nome e e-mail válidos.")
            if len(senha) < 6: raise Erro(400, "A senha precisa de 6+ caracteres.")
            salt = secrets.token_hex(16)
            try: bid = c.execute("INSERT INTO barbeiro(nome,email,senha_hash,salt) VALUES (?,?,?,?)", (nome, email, hash_senha(senha, salt), salt)).lastrowid
            except sqlite3.IntegrityError: raise Erro(409, "E-mail já cadastrado.")
            return self.abrir_sessao(c, bid, nome)
        if m == "POST" and s == ["login"]:
            r = c.execute("SELECT * FROM barbeiro WHERE email=?", (str(d.get("email", "")).strip().lower(),)).fetchone()
            if not r or not secrets.compare_digest(r["senha_hash"], hash_senha(str(d.get("senha", "")), r["salt"])): raise Erro(401, "E-mail ou senha incorretos.")
            return self.abrir_sessao(c, r["id"], r["nome"])
        if m == "POST" and s == ["logout"]:
            ck = cookies.SimpleCookie(self.headers.get("Cookie", ""))
            if "bp_sess" in ck: c.execute("DELETE FROM sessao WHERE token=?", (ck["bp_sess"].value,))
            return 200, {"ok": True}
        if m == "GET" and s == ["me"]:
            b = self.barbeiro_logado(c); return 200, ({"id": b["id"], "nome": b["nome"]} if b else None)
        if m == "GET" and s == ["agenda"]:
            b = self.exigir_barbeiro(c); data = qs.get("data", "")
            cods = [r["codigo"] for r in c.execute("SELECT codigo FROM agendamento WHERE barbeiro_id=? AND data=? ORDER BY hora", (b["id"], data))]
            ags = [agendamento_dict(c, x) for x in cods]
            esp = [espera_dict(c, r["id"]) for r in c.execute("SELECT id FROM lista_espera WHERE barbeiro_id=? AND data=? ORDER BY hora", (b["id"], data))]
            rs = c.execute("""SELECT COALESCE(SUM(p.valor_bruto),0) bruto, COALESCE(SUM(p.valor_taxa),0) taxa, COALESCE(SUM(p.valor_liquido),0) liq
                FROM pagamento p JOIN agendamento a ON a.codigo=p.agendamento_codigo WHERE a.barbeiro_id=? AND a.data=?""", (b["id"], data)).fetchone()
            return 200, {"agendamentos": ags, "espera": esp, "ocupados": sum(1 for a in ags if a["status"] in ATIVOS),
                         "resumo": {"bruto": rs["bruto"], "taxa": rs["taxa"], "liquido": rs["liq"], "taxa_percentual": TAXA}}
        raise Erro(404, "Rota não encontrada.")

    def abrir_sessao(self, c, bid, nome):
        t = secrets.token_urlsafe(32)
        c.execute("INSERT INTO sessao(token, barbeiro_id) VALUES (?,?)", (t, bid))
        return 200, {"id": bid, "nome": nome}, {"Set-Cookie": f"bp_sess={t}; Path=/; HttpOnly; SameSite=Lax"}

    def acao(self, c, a, acao):
        cod, st, pg = a["codigo"], a["status"], a["pagamento"]
        regras = {"confirmar": ("pendente",), "recusar": ("pendente",), "cancelar": ("confirmado",), "faltou": ("confirmado",), "concluir": ("confirmado",)}
        if acao in regras and st not in regras[acao]: raise Erro(400, "Ação indisponível para este status.")
        if acao == "confirmar": c.execute("UPDATE agendamento SET status='confirmado' WHERE codigo=?", (cod,))
        elif acao in ("recusar", "cancelar"): c.execute("UPDATE agendamento SET status='cancelado' WHERE codigo=?", (cod,))
        elif acao == "faltou": c.execute("UPDATE agendamento SET status='faltou' WHERE codigo=?", (cod,))
        elif acao == "concluir": c.execute("UPDATE agendamento SET status='concluído', pagamento_status='liberado' WHERE codigo=?", (cod,))
        elif acao == "pagar":
            if pg != "liberado": raise Erro(400, "Pagamento ainda não liberado.")
            bruto = a["total"]; taxa = round(bruto * TAXA, 2)
            c.execute("UPDATE agendamento SET pagamento_status='pago' WHERE codigo=?", (cod,))
            c.execute("INSERT INTO pagamento(agendamento_codigo,valor_bruto,taxa_percentual,valor_taxa,valor_liquido) VALUES (?,?,?,?,?)",
                      (cod, bruto, TAXA, taxa, round(bruto - taxa, 2)))
        else: raise Erro(400, "Ação inválida.")

    def estatico(self, p):
        f = (BASE / "public" / (p.lstrip("/") or "index.html")).resolve()
        if not str(f).startswith(str(BASE / "public")) or not f.is_file(): raise Erro(404, "Arquivo não encontrado.")
        tipos = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8"}
        b = f.read_bytes()
        self.send_response(200); self.send_header("Content-Type", tipos.get(f.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def despachar(self, m):
        try: self.tratar(m)
        except Erro as e: self.enviar(e.status, {"erro": e.msg})
        except (ValueError, KeyError, TypeError, json.JSONDecodeError): self.enviar(400, {"erro": "Requisição inválida."})

    def do_GET(self): self.despachar("GET")
    def do_POST(self): self.despachar("POST")
    def do_DELETE(self): self.despachar("DELETE")


if __name__ == "__main__":
    iniciar_banco()
    print(f"Barber Point em http://localhost:{PORT}  (banco: {DB_PATH})")
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
