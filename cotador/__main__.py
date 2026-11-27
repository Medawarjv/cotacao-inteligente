# -*- coding: utf-8 -*-
"""Roda a cotação de ponta a ponta.
Uso (na raiz do projeto):  python -m cotador [--reextrair] [--entrada PASTA] [--saida PASTA]"""
import argparse, hashlib, json, pathlib, subprocess, time
from . import fontes, extrair, regras, comparar, avaliar, saidas
from .llm import motor_padrao
from .saidas import brl

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", default=str(RAIZ / "entrada"))
    ap.add_argument("--saida", default=str(RAIZ / "saida"))
    ap.add_argument("--reextrair", action="store_true", help="ignora o cache e chama o Claude de novo")
    a = ap.parse_args()
    ent, sai = pathlib.Path(a.entrada), pathlib.Path(a.saida)
    cache_dir = sai / "extracoes"; cache_dir.mkdir(parents=True, exist_ok=True)
    catalogo = json.loads((RAIZ / "dados" / "catalogo.json").read_text(encoding="utf-8"))
    por_cod = {c["codigo"]: c for c in catalogo}
    gab_path = RAIZ / "gabarito" / "gabarito.json"
    gabarito = json.loads(gab_path.read_text(encoding="utf-8")) if gab_path.exists() else {}
    motor, t0 = None, time.time()

    # 1) ler e extrair cada cotação (com cache por conteúdo + prompt)
    normalizados, condicoes, log, fonte_de, alertas = {}, {}, [], {}, {}
    for arq in sorted(p for p in ent.iterdir() if p.is_file()):
        texto = fontes.ler(arq)
        chave = hashlib.sha256((texto + extrair.montar_sistema(catalogo) + json.dumps(extrair.SCHEMA)).encode()).hexdigest()[:16]
        cache = cache_dir / f"{arq.stem}.json"
        dados = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else None
        do_cache = bool(dados and dados.get("chave") == chave and not a.reextrair)
        if not do_cache:
            motor = motor or motor_padrao()
            print(f"Extraindo {arq.name} ...", flush=True)
            saida, meta = extrair.extrair(motor, texto, arq.name, catalogo)
            dados = {"chave": chave, "arquivo": arq.name, "saida": saida, "meta": meta}
            cache.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
        s = dados["saida"]
        f = s["fornecedor"].strip()
        if f.isupper():  # "LATICÍNIOS SERRA FINA LTDA" -> "Laticínios Serra Fina Ltda"
            f = f.title()
        fonte_de[f] = arq.name
        condicoes[f] = s["condicoes"]
        normalizados[f] = [dict(regras.normalizar(i, por_cod), fornecedor=f) for i in s["itens"]]
        alertas[f] = s.get("alertas", []) + regras.conferir_condicoes(s["condicoes"])
        m = dados["meta"]
        log.append({"arquivo": arq.name, "fornecedor": f, "motor": m.get("motor"), "segundos": m.get("segundos"),
                    "tokens_entrada": m.get("tokens_entrada"), "tokens_saida": m.get("tokens_saida"),
                    "itens": len(s["itens"]), "cache": do_cache})

    # 2) ofertas válidas e otimização
    ofertas = {}
    for f, itens in normalizados.items():
        for i in itens:
            if i["status"] == "ok":
                ofertas.setdefault(i["codigo_catalogo"], []).append(i)
    nec = comparar.necessidade(catalogo)
    res = comparar.otimizar(ofertas, condicoes, nec)
    if res is None:
        raise SystemExit("Nenhuma combinação atende os pedidos mínimos. Revise as cotações.")

    # 3) números para o gestor
    comprado = {cod: comparar.linha_compra(o, nec[cod]) for cod, o in res["escolha"].items()}
    custo_ultimo = round(sum(comprado[c]["qtd_base"] * por_cod[c]["ultimo_preco"] for c in comprado), 2)
    economia = round(custo_ultimo - res["custo_total"], 2)
    revisao_linhas = [(f, i["texto_original"], "; ".join(i["pendencias"]) or "fora do catálogo")
                      for f, itens in normalizados.items() for i in itens if i["status"] in ("revisao", "fora_catalogo")]
    revisao_linhas += [(f, "(cotação inteira)", "ALERTA: " + a) for f, lista in alertas.items() for a in lista]
    aval = None
    if gabarito:
        fontes_av = [avaliar.avaliar_fonte(fonte_de[f], normalizados[f], condicoes[f], gabarito[fonte_de[f]])
                     for f in normalizados if fonte_de[f] in gabarito]
        aval = {"consolidado": avaliar.consolidar(fontes_av), "fontes": fontes_av}
    kpis = {"Total do pedido": brl(res["custo_total"]),
            "Economia vs último preço pago": f"{brl(economia)} ({economia / custo_ultimo:.0%})",
            "Itens para revisão humana": str(len(revisao_linhas)),
            "Preços lidos corretamente": aval["consolidado"]["precos_corretos"] if aval else "sem gabarito"}
    resumo = [
        f"Cotação da semana: {len(normalizados)} fornecedores, {sum(len(v) for v in normalizados.values())} itens lidos.",
        f"Pedido otimizado: {brl(res['custo_total'])} em {len(res['totais'])} fornecedores "
        f"({res['combinacoes_testadas']} combinações testadas).",
        f"Pelos últimos preços pagos, a mesma compra sairia {brl(custo_ultimo)}. Economia de {brl(economia)} ({economia / custo_ultimo:.0%}).",
        ("Escolher o mais barato item a item não atenderia todos os pedidos mínimos." if not res["ingenua_viavel"]
         else f"O mais barato item a item custaria {brl(res['ingenua_custo'])}."),
        f"{len(revisao_linhas)} itens precisam de revisão humana antes da compra (aba Revisão).",
    ] + ([f"Sem oferta válida nesta semana: {', '.join(por_cod[c]['nome'] for c in res['sem_oferta'])}."] if res["sem_oferta"] else [])

    ctx = {"catalogo": catalogo, "resultado": res, "normalizados": normalizados, "necessidade": nec,
           "condicoes": condicoes, "log": log, "resumo_linhas": resumo, "avaliacao": aval, "kpis": kpis,
           "revisao_linhas": revisao_linhas, "alertas": alertas, "titulo": "restaurante italiano, Rio de Janeiro",
           "subtitulo": f"{len(normalizados)} cotações, cada uma num formato: WhatsApp, áudio transcrito, PDF, planilha e e-mail"}

    # 4) saídas
    saidas.planilha(sai / "mapa_de_cotacao.xlsx", ctx)
    arquivos = saidas.mensagens(sai / "pedidos", ctx)
    saidas.relatorio_html(sai / "relatorio.html", ctx)
    (sai / "resumo.md").write_text("# Resumo da cotação\n\n" + "\n".join(f"- {l}" for l in resumo) + "\n", encoding="utf-8")
    execucao = {"segundos_total": round(time.time() - t0, 1), "log": log, "resumo": resumo,
                "avaliacao": aval["consolidado"] if aval else None,
                "totais": res["totais"], "custo_total": res["custo_total"], "custo_ultimo": custo_ultimo}
    (sai / "execucao.json").write_text(json.dumps(execucao, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n".join(resumo))
    if aval:
        print("Avaliação:", json.dumps(aval["consolidado"], ensure_ascii=False))
    print(f"Saídas em {sai.relative_to(RAIZ) if sai.is_relative_to(RAIZ) else sai}: mapa_de_cotacao.xlsx, relatorio.html, resumo.md, {len(arquivos)} mensagens em pedidos/")


if __name__ == "__main__":
    main()
