# -*- coding: utf-8 -*-
"""Compara a extração com o gabarito: o modelo leu o preço certo? pegou as condições? sinalizou as armadilhas?"""
TOLERANCIA = 0.01  # 1% no preço por unidade-base


def avaliar_fonte(arquivo, normalizados, condicoes, gab):
    validos = {i["codigo_catalogo"]: i for i in normalizados if i.get("preco_base") is not None}
    linhas, acertos = [], 0
    for cod, esperado in gab["itens"].items():
        lido = validos.get(cod, {}).get("preco_base")
        ok = lido is not None and abs(lido / esperado - 1) <= TOLERANCIA
        acertos += ok
        linhas.append({"arquivo": arquivo, "codigo": cod, "esperado": esperado, "lido": lido, "ok": ok})
    extras = [c for c in validos if c not in gab["itens"]]
    fora = [i["texto_original"].lower() for i in normalizados if i["status"] == "fora_catalogo"]
    fora_ok = all(any(f in t for t in fora) for f in gab["fora_catalogo"])
    rev = {i["codigo_catalogo"] for i in normalizados if i["status"] == "revisao"}
    revisao_ok = set(gab["revisao"]) <= rev
    revisao_falso = sorted(rev - set(gab["revisao"]))
    pm_ok = (condicoes.get("pedido_minimo") or 0) == gab["pedido_minimo"]
    frete_ok = (condicoes.get("frete_valor") or 0) == gab["frete"]
    # condições que mudam o total do pedido: frete grátis e desconto condicional
    outras = {k: (condicoes.get(k), gab.get(k)) for k in ("frete_gratis_acima_de", "desconto_percentual", "desconto_acima_de")}
    outras_ok = all((a or None) == (b or None) for a, b in outras.values())
    return {"arquivo": arquivo, "itens": len(gab["itens"]), "acertos": acertos, "extras": extras,
            "fora_catalogo_ok": fora_ok, "revisao_ok": revisao_ok, "revisao_falso_positivo": revisao_falso,
            "pedido_minimo_ok": pm_ok, "frete_ok": frete_ok, "condicoes_extras_ok": outras_ok,
            "condicoes_extras": {k: {"lido": a, "esperado": b} for k, (a, b) in outras.items() if (a or None) != (b or None)},
            "linhas": linhas}


def consolidar(resultados):
    tot = sum(r["itens"] for r in resultados)
    ac = sum(r["acertos"] for r in resultados)
    cond = sum(r["pedido_minimo_ok"] + r["frete_ok"] + r["condicoes_extras_ok"] for r in resultados)
    return {"precos_corretos": f"{ac}/{tot}", "acuracia_preco": round(ac / tot, 4),
            "condicoes_corretas": f"{cond}/{3 * len(resultados)}",
            "armadilhas_sinalizadas": f"{sum(r['revisao_ok'] and r['fora_catalogo_ok'] for r in resultados)}/{len(resultados)}",
            "revisoes_desnecessarias": sum(len(r["revisao_falso_positivo"]) for r in resultados),
            "itens_inventados": sum(len(r["extras"]) for r in resultados)}
