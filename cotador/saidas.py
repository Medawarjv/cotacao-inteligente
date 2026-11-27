# -*- coding: utf-8 -*-
"""Gera o mapa de cotação (Excel), as mensagens de pedido, o resumo para o gestor e o relatório visual."""
import html, re, unicodedata
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from .comparar import linha_compra

VERDE, AMARELO, CINZA = PatternFill("solid", fgColor="C6EFCE"), PatternFill("solid", fgColor="FFEB9C"), PatternFill("solid", fgColor="EDEDED")
NEGRITO = Font(bold=True)


def brl(v):
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


PLURAL = {"maço": "maços", "un": "unidades", "kg": "kg", "L": "L"}


def _cabecalho(ws, cols):
    ws.append(cols)
    for c in ws[1]:
        c.font = NEGRITO; c.fill = CINZA
    ws.freeze_panes = "A2"


def _larguras(ws, larguras):
    for i, w in enumerate(larguras, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def planilha(caminho, ctx):
    cat, res, normal, nec = ctx["catalogo"], ctx["resultado"], ctx["normalizados"], ctx["necessidade"]
    forn = sorted(ctx["condicoes"])
    wb = Workbook()

    ws = wb.active; ws.title = "Resumo"
    for linha in ctx["resumo_linhas"]:
        ws.append([linha])
    ws["A1"].font = Font(bold=True, size=13); _larguras(ws, [110])

    ws = wb.create_sheet("Mapa")
    _cabecalho(ws, ["Código", "Item", "Unid.", "Necessidade", "Último pago"] + forn + ["Escolhido"])
    for c in cat:
        linha = [c["codigo"], c["nome"], c["unidade"], nec[c["codigo"]], c["ultimo_preco"]]
        celulas = {}
        for f in forn:
            o = next((i for i in normal[f] if i["codigo_catalogo"] == c["codigo"]), None)
            if o is None:
                linha.append(None)
            elif o["status"] == "indisponivel":
                linha.append("em falta")
            else:
                linha.append(o.get("preco_base")); celulas[f] = o["status"]
        esc = res["escolha"].get(c["codigo"]) if res else None
        linha.append(esc["fornecedor"] if esc else ("sem oferta" if nec[c["codigo"]] else "estoque ok"))
        ws.append(linha)
        r = ws.max_row
        for j, f in enumerate(forn):
            cel = ws.cell(r, 6 + j)
            if celulas.get(f) == "revisao":
                cel.fill = AMARELO
            if esc and esc["fornecedor"] == f:
                cel.fill = VERDE; cel.font = NEGRITO
            if isinstance(cel.value, float):
                cel.number_format = '"R$" #,##0.00'
        ws.cell(r, 5).number_format = '"R$" #,##0.00'
    _larguras(ws, [8, 30, 7, 12, 12] + [20] * len(forn) + [22])

    ws = wb.create_sheet("Pedido")
    _cabecalho(ws, ["Fornecedor", "Código", "Item", "Embalagens", "Qtd (unid.-base)", "Preço cotado", "Custo"])
    if res:
        for f in sorted(res["totais"]):
            for cod, o in res["escolha"].items():
                if o["fornecedor"] != f:
                    continue
                lc = linha_compra(o, nec[cod])
                ws.append([f, cod, next(c["nome"] for c in cat if c["codigo"] == cod),
                           f"{lc['embalagens']} × {o['embalagem']}" if lc["embalagens"] else "a granel",
                           lc["qtd_base"], o["preco"], lc["custo"]])
            t = res["totais"][f]
            ws.append([f, "", "Subtotal / desconto / frete / total", "", "", "", None])
            ws.append(["", "", f"{brl(t['subtotal'])}  −{brl(t['desconto'])}  +{brl(t['frete'])}", "", "", "", t["total"]])
            ws.cell(ws.max_row, 7).font = NEGRITO
        for row in ws.iter_rows(min_row=2):
            for idx in (5, 6):
                if isinstance(row[idx].value, (int, float)):
                    row[idx].number_format = '"R$" #,##0.00'
    _larguras(ws, [24, 8, 34, 28, 16, 14, 14])

    ws = wb.create_sheet("Revisão")
    _cabecalho(ws, ["Fornecedor", "Texto original", "Status", "Motivo", "O que fazer"])
    for f in forn:
        for i in normal[f]:
            if i["status"] in ("revisao", "fora_catalogo"):
                motivo = "; ".join(i["pendencias"]) if i["pendencias"] else "item fora do catálogo"
                acao = ("Confirmar o preço com o fornecedor antes de usar" if i["status"] == "revisao"
                        else "Decidir se entra no catálogo")
                ws.append([f, i["texto_original"], i["status"], motivo, acao])
                for c in ws[ws.max_row]:
                    c.alignment = Alignment(wrap_text=True, vertical="top")
    for f, lista in ctx.get("alertas", {}).items():
        for a in lista:
            ws.append([f, "(cotação inteira)", "alerta", a, "Ler a mensagem original e falar com o fornecedor"])
            for c in ws[ws.max_row]:
                c.alignment = Alignment(wrap_text=True, vertical="top"); c.fill = AMARELO
    _larguras(ws, [24, 40, 14, 60, 36])

    ws = wb.create_sheet("Log")
    _cabecalho(ws, ["Arquivo", "Fornecedor", "Motor", "Segundos", "Tokens entrada", "Tokens saída", "Itens lidos", "Do cache"])
    for l in ctx["log"]:
        ws.append([l["arquivo"], l["fornecedor"], l["motor"], l["segundos"], l["tokens_entrada"], l["tokens_saida"], l["itens"], l["cache"]])
    _larguras(ws, [42, 24, 20, 10, 14, 12, 10, 10])
    wb.save(caminho)


def mensagens(pasta, ctx):
    res, nec, cat = ctx["resultado"], ctx["necessidade"], {c["codigo"]: c for c in ctx["catalogo"]}
    pasta.mkdir(parents=True, exist_ok=True)
    arquivos = []
    for f, t in sorted(res["totais"].items()):
        linhas = []
        for cod, o in res["escolha"].items():
            if o["fornecedor"] == f:
                lc = linha_compra(o, nec[cod])
                q = (f"{lc['embalagens']} × {o['embalagem']}" if lc["embalagens"]
                     else f"{lc['qtd_base']:g} {PLURAL.get(cat[cod]['unidade'], cat[cod]['unidade']) if lc['qtd_base'] != 1 else cat[cod]['unidade']}")
                linhas.append(f"• {q} de {cat[cod]['nome'].lower()}")
        extra = []
        if t["desconto"]:
            extra.append(f"com o desconto de {brl(t['desconto'])}")
        if t["frete"]:
            extra.append(f"mais {brl(t['frete'])} de frete")
        txt = (f"Bom dia! Segue o pedido da semana:\n" + "\n".join(linhas) +
               f"\n\nTotal pela sua cotação: {brl(t['total'])}" + (f" ({', '.join(extra)})" if extra else "") +
               ".\nPode confirmar o pedido e a data de entrega? Obrigado!")
        p = pasta / f"pedido_{slug(f)}.txt"
        p.write_text(txt, encoding="utf-8"); arquivos.append(p)
    return arquivos


def relatorio_html(caminho, ctx):
    res, aval = ctx["resultado"], ctx["avaliacao"]
    e = html.escape
    cards = "".join(f"<div class=k><b>{e(v)}</b><span>{e(k)}</span></div>" for k, v in ctx["kpis"].items())
    ped = "".join(f"<tr><td>{e(f)}</td><td class=r>{brl(t['subtotal'])}</td><td class=r>{brl(t['desconto'])}</td>"
                  f"<td class=r>{brl(t['frete'])}</td><td class=r><b>{brl(t['total'])}</b></td></tr>"
                  for f, t in sorted(res["totais"].items()))
    rev = "".join(f"<tr><td>{e(r[0])}</td><td>{e(r[1])}</td><td>{e(r[2])}</td></tr>" for r in ctx["revisao_linhas"])
    av = "".join(f"<tr><td>{e(r['arquivo'])}</td><td class=r>{r['acertos']}/{r['itens']}</td>"
                 f"<td>{'ok' if r['pedido_minimo_ok'] and r['frete_ok'] else 'erro'}</td>"
                 f"<td>{'ok' if r['revisao_ok'] and r['fora_catalogo_ok'] else 'falhou'}</td></tr>" for r in aval["fontes"])
    caminho.write_text(f"""<!doctype html><html lang=pt-BR><head><meta charset=utf-8><title>Cotação da semana</title><style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:32px;color:#1d2b27;background:#fff;max-width:1100px}}
h1{{margin:0 0 4px;font-size:24px}} .sub{{color:#5b6b66;margin-bottom:20px}} h2{{font-size:16px;margin:26px 0 8px}}
.ks{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}} .k{{border:1px solid #d9e2df;border-radius:10px;padding:14px}}
.k b{{display:block;font-size:22px;color:#1f6f5c}} .k span{{color:#5b6b66;font-size:13px}}
table{{border-collapse:collapse;width:100%;font-size:13px}} td,th{{border-bottom:1px solid #e5ebe9;padding:7px 8px;text-align:left}}
th{{background:#f3f6f5}} .r{{text-align:right}} .note{{font-size:12px;color:#5b6b66;margin-top:18px}}</style></head><body>
<h1>Cotação da semana · {e(ctx['titulo'])}</h1><div class=sub>{e(ctx['subtitulo'])}</div>
<div class=ks>{cards}</div>
<h2>Pedido otimizado por fornecedor</h2><table><tr><th>Fornecedor</th><th class=r>Subtotal</th><th class=r>Desconto</th><th class=r>Frete</th><th class=r>Total</th></tr>{ped}</table>
<h2>Para revisão humana antes de comprar</h2><table><tr><th>Fornecedor</th><th>Texto original</th><th>Motivo</th></tr>{rev}</table>
<h2>Avaliação da extração contra o gabarito</h2><table><tr><th>Cotação</th><th class=r>Preços corretos</th><th>Condições</th><th>Armadilhas</th></tr>{av}</table>
<div class=note>Dados sintéticos. Extração pelo Claude com saída estruturada; contas, validação e otimização em Python. Nenhuma mensagem é enviada sem aprovação.</div>
</body></html>""", encoding="utf-8")
