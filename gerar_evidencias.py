"""Gera as evidências do trabalho: prints de todas as telas e imagens das tabelas do banco já preenchido.
Uso: python3 scripts/gerar_evidencias.py   (precisa de: pip install playwright matplotlib && playwright install chromium)
Cria um banco temporário, executa os fluxos reais pela interface e salva tudo em docs/evidencias/."""
import json, os, sqlite3, subprocess, sys, time, urllib.request
from datetime import date, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "docs" / "evidencias"; OUT.mkdir(parents=True, exist_ok=True)
DBP = "/tmp/bp_evidencias.db"; PORT = 8765; URL = f"http://localhost:{PORT}"
for f in OUT.glob("*.png"): f.unlink()
if os.path.exists(DBP): os.remove(DBP)
srv = subprocess.Popen([sys.executable, str(RAIZ / "server.py")], env={**os.environ, "DB_PATH": DBP, "PORT": str(PORT)})
time.sleep(1.5)

dias = []; d = date.today()
while len(dias) < 7:
    if d.weekday() != 6: dias.append(d.isoformat())
    d += timedelta(days=1)
D = dias[1]

def api(m, p, body=None, ck=None):
    r = urllib.request.Request(f"{URL}/api/{p}", method=m, data=json.dumps(body).encode() if body is not None else None,
                               headers={"Content-Type": "application/json", **({"Cookie": ck} if ck else {})})
    return json.load(urllib.request.urlopen(r))
def reserva(nome, tel, barb, hora, sv, forma, troco=None):
    return api("POST", "agendamentos", {"nome": nome, "telefone": tel, "barbeiro_id": barb, "data": D, "hora": hora, "servicos": sv, "forma": forma, "troco_para": troco})["codigo"]

n = [0]
def shot(page, nome):
    n[0] += 1; page.wait_for_timeout(350)
    page.screenshot(path=str(OUT / f"{n[0]:02d}_{nome}.png"), full_page=True)

try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        novo = lambda: b.new_context(viewport={"width": 520, "height": 800}).new_page()
        # --- Visitante A agenda (com troco) ---
        A = novo(); A.goto(URL); A.wait_for_selector("text=1. Serviços")
        shot(A, "agendar_inicio")
        A.evaluate(f"A.tg('s',1);A.tg('s',2);A.tg('b',1);A.tg('d','{D}');A.tg('t','10:30');A.tg('m','Dinheiro')")
        A.wait_for_selector("text=Precisa de troco"); A.fill("input[type=number]", "100")
        A.fill("input[placeholder=Nome]", "Marcos Lima"); A.fill("input[placeholder^=Telefone]", "31988881111")
        shot(A, "agendar_horario_pagamento_troco_dados")
        A.click("text=Confirmar agendamento"); A.wait_for_selector("text=Agendamento enviado")
        shot(A, "confirmacao_codigo")
        A.click("text=Ver meus agendamentos"); A.wait_for_selector("text=Corte de cabelo + Barba")
        shot(A, "meus_agendamentos")
        # --- Outros agendamentos (via API) para preencher a agenda ---
        c_pix = reserva("João Pereira", "31999990000", 1, "09:00", [1], "Pix")
        c_car = reserva("Pedro Alves", "31977772222", 1, "11:00", [2], "Cartão")
        reserva("Bruno Costa", "31955554444", 1, "14:00", [4], "Pix")
        c_x = reserva("Ana Ribeiro", "31944443333", 1, "15:00", [1, 3], "Pix")
        c_falta = reserva("Tiago Nunes", "31933332222", 1, "16:00", [1], "Dinheiro", 50)
        reserva("Léo Martins", "31922221111", 2, "10:00", [1, 2], "Pix"); reserva("Caio Dias", "31911110000", 3, "13:00", [3], "Cartão")
        # --- Visitante B: horário ocupado -> lista de espera ---
        B = novo(); B.goto(URL); B.wait_for_selector("text=1. Serviços")
        B.evaluate(f"A.tg('s',1);A.tg('b',1);A.tg('d','{D}')"); B.wait_for_selector("text=4. Horário"); B.wait_for_timeout(600)
        B.evaluate("A.tg('t','15:00')"); B.fill("input[placeholder=Nome]", "Rafaela Torres"); B.fill("input[placeholder^=Telefone]", "31966665555")
        B.wait_for_selector("button:has-text('Entrar na lista de espera')"); shot(B, "horario_ocupado_lista_de_espera")
        B.click("button:has-text('Entrar na lista de espera')"); B.wait_for_selector("h2:has-text('Lista de espera')"); shot(B, "lista_de_espera_visitante")
        B.evaluate("A.set('tab','me')"); B.fill("#cd", c_pix); B.click("text=Consultar");
        B.wait_for_timeout(600); shot(B, "consulta_por_codigo")
        # --- Barbeiro ---
        M = novo(); M.goto(URL); M.wait_for_selector("text=Sou barbeiro"); M.click("text=Sou barbeiro"); shot(M, "login_barbeiro")
        M.click("text=Criar conta"); shot(M, "cadastro_barbeiro")
        M.click("text=Já tenho conta"); M.fill("#e", "carlos@bp.com"); M.fill("#w", "123456"); M.click("button.p")
        M.wait_for_selector("text=atendimentos"); M.evaluate(f"A.set('bd','{D}')"); M.wait_for_selector("text=Marcos Lima")
        shot(M, "agenda_barbeiro_pendentes")
        ck = [c for c in M.context.cookies() if c["name"] == "bp_sess"][0]; cookie = f"bp_sess={ck['value']}"
        act = lambda cod, a: api("POST", f"agendamentos/{cod}/acao", {"acao": a}, cookie)
        for cod in (c_pix, c_car): [act(cod, a) for a in ("confirmar", "concluir", "pagar")]
        act(c_falta, "confirmar"); act(c_falta, "faltou")
        M.wait_for_timeout(5500)
        M.click("text=Confirmar >> nth=0"); M.wait_for_timeout(500)
        shot(M, "agenda_barbeiro_confirmado_pagamentos_taxa")
        M.click("text=Concluir e liberar pagamento >> nth=0"); M.wait_for_timeout(600); shot(M, "agenda_barbeiro_pagamento_liberado")
        M.click("text=Registrar pagamento >> nth=0"); M.wait_for_timeout(600); shot(M, "agenda_barbeiro_resumo_taxa_20")
        # --- Cancelamento libera a vaga para a lista de espera ---
        act(c_x, "confirmar"); act(c_x, "cancelar")
        M.wait_for_timeout(5500); shot(M, "agenda_barbeiro_vaga_livre_lista_espera")
        B.wait_for_timeout(5500); B.evaluate("A.set('tab','me')"); shot(B, "visitante_vaga_liberada")
        B.click("text=Reservar agora"); B.wait_for_selector("text=Agendamento enviado"); shot(B, "reserva_pela_lista_de_espera")
        # cliente cancela com o código
        A.evaluate("A.set('tab','me')"); A.wait_for_timeout(300)
        b.close()
    # --- Imagens do banco ---
    con = sqlite3.connect(DBP); con.row_factory = sqlite3.Row
    for t in ["barbeiro", "cliente", "servico", "forma_pagamento", "agendamento", "agendamento_servico", "pagamento", "lista_espera", "lista_espera_servico", "sessao"]:
        cols = [r[1] for r in con.execute(f"PRAGMA table_info({t})")]
        rows = [[(str(v)[:22] + "…" if len(str(v)) > 24 else str(v)) if v is not None else "NULL" for v in r] for r in con.execute(f"SELECT * FROM {t}")]
        if t == "barbeiro": rows = [[r[0], r[1], r[2], r[3][:12] + "…", r[4][:8] + "…", r[5]] for r in rows]
        fig, ax = plt.subplots(figsize=(max(7, 1.6 * len(cols)), 0.45 * (len(rows) + 2) + 0.6)); ax.axis("off")
        ax.set_title(f"Tabela: {t}  ({len(rows)} registros)", loc="left", fontsize=11, fontweight="bold")
        tb = ax.table(cellText=rows or [[""] * len(cols)], colLabels=cols, loc="upper center", cellLoc="left"); tb.auto_set_font_size(False); tb.set_fontsize(8); tb.auto_set_column_width(range(len(cols)))
        for (r, c), cell in tb.get_celld().items():
            if r == 0: cell.set_facecolor("#b8791f"); cell.set_text_props(color="white", fontweight="bold")
        fig.savefig(OUT / f"db_{t}.png", dpi=130, bbox_inches="tight"); plt.close(fig)
    (RAIZ / "db" / "dados_exemplo.sql").write_text("\n".join(con.iterdump()), encoding="utf-8")
    print("Evidências geradas em", OUT)
finally:
    srv.terminate()
