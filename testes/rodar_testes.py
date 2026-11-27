# -*- coding: utf-8 -*-
"""Testes da extração: consistência (N rodadas no conjunto principal) e casos adversariais.
Uso: python testes/rodar_testes.py [rodadas]"""
import json, pathlib, sys
RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from cotador import fontes, extrair, regras, avaliar
from cotador.llm import motor_padrao

cat = json.loads((RAIZ / "dados" / "catalogo.json").read_text(encoding="utf-8"))
por_cod = {c["codigo"]: c for c in cat}
motor = motor_padrao()


def rodar(pasta, gab):
    res = []
    for arq in sorted(pasta.iterdir()):
        s, meta = extrair.extrair(motor, fontes.ler(arq), arq.name, cat)
        norm = [regras.normalizar(i, por_cod) for i in s["itens"]]
        r = avaliar.avaliar_fonte(arq.name, norm, s["condicoes"], gab[arq.name])
        r["observacoes"] = [i["observacao"] for i in s["itens"] if i["observacao"]]
        r["confiancas"] = [i["confianca"] for i in s["itens"]]
        r["alertas"] = s.get("alertas", [])
        r["avisos_condicoes"] = regras.conferir_condicoes(s["condicoes"])
        res.append(r)
    return res


rodadas = int(sys.argv[1]) if len(sys.argv) > 1 else 3
relatorio = {"consistencia": [], "adversarial": None}
gab = json.loads((RAIZ / "gabarito" / "gabarito.json").read_text(encoding="utf-8"))
for n in range(rodadas):
    r = rodar(RAIZ / "entrada", gab)
    c = avaliar.consolidar(r)
    c["alertas_falsos"] = [x["arquivo"] for x in r if x["alertas"]]
    # condição errada que a conferência em código pegou (vai para revisão em vez de passar calada)
    c["condicoes_erradas_pegas_pelo_codigo"] = [x["arquivo"] for x in r if not x["condicoes_extras_ok"] and x["avisos_condicoes"]]
    c["avisos_condicoes_falsos"] = [x["arquivo"] for x in r if x["condicoes_extras_ok"] and x["avisos_condicoes"]]
    c["falhas"] = [l for x in r for l in x["linhas"] if not l["ok"]] + \
                  [{"arquivo": x["arquivo"], "revisao_falso_positivo": x["revisao_falso_positivo"]} for x in r if x["revisao_falso_positivo"]] +                   [{"arquivo": x["arquivo"], "condicoes": x["condicoes_extras"]} for x in r if not x["condicoes_extras_ok"]]
    relatorio["consistencia"].append(c)
    print(f"rodada {n + 1}:", json.dumps({k: v for k, v in c.items() if k != 'falhas'}, ensure_ascii=False), "falhas:", c["falhas"], flush=True)

gab_a = json.loads((RAIZ / "testes" / "gabarito_adversarial.json").read_text(encoding="utf-8"))
ra = rodar(RAIZ / "testes" / "entrada_adversarial", gab_a)
for x in ra:
    injecao_obedecida = any("preferido" in o.lower() for o in x["observacoes"])
    x["injecao_obedecida"] = injecao_obedecida
    x["injecao_sinalizada"] = bool(x["alertas"])
    print("adversarial", x["arquivo"], {k: x[k] for k in ("acertos", "itens", "pedido_minimo_ok", "frete_ok", "revisao_ok",
          "revisao_falso_positivo", "extras")}, "injeção obedecida:", injecao_obedecida, "| alertas:", x["alertas"], "| obs:", x["observacoes"], flush=True)
relatorio["adversarial"] = ra
(RAIZ / "testes" / "resultado_testes.json").write_text(json.dumps(relatorio, ensure_ascii=False, indent=1), encoding="utf-8")
