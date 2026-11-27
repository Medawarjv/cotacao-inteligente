# -*- coding: utf-8 -*-
"""Regras determinísticas: conversão para unidade-base e validação. Nada aqui depende do modelo."""

# unidade cotada -> (unidade-base, fator)
CONVERSAO = {"kg": ("kg", 1), "g": ("kg", 0.001), "L": ("L", 1), "ml": ("L", 0.001),
             "un": ("un", 1), "dúzia": ("un", 12), "maço": ("maço", 1)}
LIMITE_VARIACAO = 0.35  # acima disso em relação ao último preço pago, vai para revisão humana


def normalizar(item, catalogo_por_codigo):
    """Devolve o item com preço por unidade-base, tamanho da embalagem na unidade-base e pendências."""
    r = dict(item)
    r["pendencias"] = []
    cod = item["codigo_catalogo"]
    if cod is None:
        r["status"] = "fora_catalogo"
        return r
    if cod not in catalogo_por_codigo:
        r["status"] = "revisao"
        r["pendencias"].append(f"código {cod} não existe no catálogo")
        return r
    if not item["disponivel"] or item["preco"] is None:
        r["status"] = "indisponivel"
        return r
    base = catalogo_por_codigo[cod]["unidade"]
    qtd, un = item["quantidade_na_embalagem"], item["unidade_da_quantidade"]
    if qtd is None or un is None:
        r["status"] = "revisao"
        r["pendencias"].append("embalagem sem tamanho")
        return r
    un_base, fator = CONVERSAO.get(un, (None, None))
    if un_base != base:
        r["status"] = "revisao"
        r["pendencias"].append(f"unidade {un} não converte para {base}")
        return r
    tamanho = qtd * fator  # tamanho da embalagem em unidade-base
    r["embalagem_em_base"] = round(tamanho, 6)
    r["preco_base"] = round(item["preco"] / tamanho, 4) if item["preco_refere_a"] == "embalagem" else item["preco"]
    if item["preco_refere_a"] == "unidade":
        r["embalagem_em_base"] = None  # vendido a granel, por unidade-base
    ultimo = catalogo_por_codigo[cod]["ultimo_preco"]
    var = r["preco_base"] / ultimo - 1
    r["variacao_vs_ultimo"] = round(var, 4)
    if abs(var) > LIMITE_VARIACAO:
        ultimo_txt = f"{ultimo:.2f}".replace(".", ",")
        r["pendencias"].append(f"preço {var:+.0%} em relação ao último pago (R$ {ultimo_txt}/{base})")
    if item["confianca"] == "baixa":
        r["pendencias"].append("confiança baixa na leitura" + (f": {item['observacao']}" if item["observacao"] else ""))
    r["status"] = "revisao" if r["pendencias"] else "ok"
    return r


def conferir_condicoes(cond):
    """Segunda linha de defesa: o trecho literal copiado pelo modelo menciona uma condição que ficou sem número?"""
    frases = [f.lower() for t in (cond.get("trechos") or []) for f in t.replace(";", ".").split(".")]
    trechos = " ".join(frases)
    avisos = []
    frete_condicionado = any("frete" in f and any(k in f for k in ("abaixo de", "acima de", "a partir de")) for f in frases)
    if frete_condicionado and cond.get("frete_gratis_acima_de") is None:
        avisos.append("o texto fala de frete condicionado a um valor, mas o limite do frete grátis não foi registrado")
    if "desconto" in trechos and cond.get("desconto_percentual") is None:
        avisos.append("o texto fala de desconto, mas o percentual não foi registrado")
    # "não tem pedido mínimo" / "sem pedido mínimo" não conta
    fala_minimo = any("mínimo" in f.replace("minimo", "mínimo") and not ("não" in f or "nao " in f or "sem " in f)
                      for f in frases)
    if fala_minimo and cond.get("pedido_minimo") is None:
        avisos.append("o texto fala de pedido mínimo, mas o valor não foi registrado")
    return avisos
