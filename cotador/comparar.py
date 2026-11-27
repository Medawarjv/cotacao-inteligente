# -*- coding: utf-8 -*-
"""Escolhe de quem comprar cada item, respeitando pedido mínimo, frete e desconto de cada fornecedor.

Busca exata: testa todas as combinações item × fornecedor e fica com a mais barata que atende todos os pedidos
mínimos. Escolher o mais barato item a item não basta: às vezes compensa pagar um pouco mais num item para
atingir o pedido mínimo de um fornecedor que é o único a ter outro item (ver docs/falhas.md, falha 2)."""
import itertools, math

LIMITE_COMBINACOES = 500_000


def necessidade(catalogo):
    return {c["codigo"]: max(0, c["consumo_semanal"] - c["estoque"]) for c in catalogo}


def linha_compra(oferta, qtd_base):
    """Quantidade e custo para cobrir a necessidade. Embalagem fechada arredonda para cima."""
    if oferta["embalagem_em_base"]:
        n = math.ceil(qtd_base / oferta["embalagem_em_base"] - 1e-9)
        return {"embalagens": n, "qtd_base": round(n * oferta["embalagem_em_base"], 3), "custo": round(n * oferta["preco"], 2)}
    return {"embalagens": None, "qtd_base": qtd_base, "custo": round(qtd_base * oferta["preco_base"], 2)}


def total_fornecedor(subtotal, cond):
    desconto = 0.0
    if cond.get("desconto_percentual") and subtotal >= (cond.get("desconto_acima_de") or 0):
        desconto = round(subtotal * cond["desconto_percentual"] / 100, 2)
    frete = cond.get("frete_valor") or 0
    if cond.get("frete_gratis_acima_de") is not None and subtotal >= cond["frete_gratis_acima_de"]:
        frete = 0
    return {"subtotal": round(subtotal, 2), "desconto": desconto, "frete": frete, "total": round(subtotal - desconto + frete, 2)}


def avaliar(escolha, nec, condicoes):
    por_forn = {}
    for c, o in escolha.items():
        por_forn[o["fornecedor"]] = por_forn.get(o["fornecedor"], 0) + linha_compra(o, nec[c])["custo"]
    if any(sub < (condicoes[f].get("pedido_minimo") or 0) - 1e-9 for f, sub in por_forn.items()):
        return None
    totais = {f: total_fornecedor(sub, condicoes[f]) for f, sub in por_forn.items()}
    return round(sum(t["total"] for t in totais.values()), 2), totais


def otimizar(ofertas, condicoes, nec):
    """ofertas: {codigo: [ofertas válidas, cada uma com 'fornecedor']}; condicoes: {fornecedor: dict}."""
    itens = [c for c, q in nec.items() if q > 0 and ofertas.get(c)]
    sem_oferta = [c for c, q in nec.items() if q > 0 and not ofertas.get(c)]
    opcoes = [ofertas[c] for c in itens]
    n_comb = math.prod(len(o) for o in opcoes)
    if n_comb > LIMITE_COMBINACOES:
        raise RuntimeError(f"{n_comb} combinações: grande demais para busca exata; trocar por programação inteira.")
    melhor = None
    for combo in itertools.product(*opcoes):
        escolha = dict(zip(itens, combo))
        r = avaliar(escolha, nec, condicoes)
        if r and (melhor is None or r[0] < melhor["custo_total"] - 0.005):
            melhor = {"custo_total": r[0], "escolha": escolha, "totais": r[1]}
    if melhor is None:
        return None
    # referências para o resumo
    ingenua = {c: min(ofertas[c], key=lambda o: linha_compra(o, nec[c])["custo"]) for c in itens}
    r_ing = avaliar(ingenua, nec, condicoes)
    melhor.update(combinacoes_testadas=n_comb, sem_oferta=sem_oferta,
                  ingenua_viavel=r_ing is not None, ingenua_custo=r_ing[0] if r_ing else None,
                  ingenua_soma_itens=round(sum(linha_compra(o, nec[c])["custo"] for c, o in ingenua.items()), 2))
    return melhor
