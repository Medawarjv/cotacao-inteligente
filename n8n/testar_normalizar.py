# -*- coding: utf-8 -*-
"""Confere que a regra em JavaScript (nó do n8n) dá o mesmo resultado que a versão Python, item a item,
usando as extrações reais em saida/extracoes e os casos de teste adversariais."""
import json, pathlib, subprocess, sys
RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from cotador import regras

cat = {c["codigo"]: c for c in json.loads((RAIZ / "dados" / "catalogo.json").read_text(encoding="utf-8"))}
itens = [i for f in sorted((RAIZ / "saida" / "extracoes").glob("*.json"))
         for i in json.loads(f.read_text(encoding="utf-8"))["saida"]["itens"]]
# casos de borda feitos à mão
itens += [
    {"texto_original": "tomate cx", "codigo_catalogo": "P01", "disponivel": True, "preco": 42, "preco_refere_a": "embalagem",
     "embalagem": "caixa", "quantidade_na_embalagem": None, "unidade_da_quantidade": None, "confianca": "baixa", "observacao": "sem tamanho"},
    {"texto_original": "limão dúzia", "codigo_catalogo": "P11", "disponivel": True, "preco": 5, "preco_refere_a": "embalagem",
     "embalagem": "dúzia", "quantidade_na_embalagem": 1, "unidade_da_quantidade": "dúzia", "confianca": "media", "observacao": ""},
    {"texto_original": "x", "codigo_catalogo": "P99", "disponivel": True, "preco": 1, "preco_refere_a": "unidade",
     "embalagem": "kg", "quantidade_na_embalagem": 1, "unidade_da_quantidade": "kg", "confianca": "alta", "observacao": ""},
]
py = [regras.normalizar(i, cat) for i in itens]
js_src = (RAIZ / "n8n" / "normalizar.js").as_posix()
script = f"const {{normalizar}} = require('{js_src}'); const d = JSON.parse(require('fs').readFileSync(0, 'utf8'));" \
         "process.stdout.write(JSON.stringify(d.itens.map(i => normalizar(i, d.cat))));"
js = json.loads(subprocess.run(["node", "-e", script], input=json.dumps({"itens": itens, "cat": cat}),
                               capture_output=True, text=True, encoding="utf-8", check=True).stdout)
campos = ["status", "preco_base", "embalagem_em_base", "variacao_vs_ultimo", "pendencias"]
dif = [(i, c, p.get(c), j.get(c)) for i, (p, j) in enumerate(zip(py, js)) for c in campos if p.get(c) != j.get(c)]
print(f"{len(itens)} itens comparados, {len(dif)} diferenças")
for d in dif:
    print("  DIF", d)
# conferência de condições: mesmas frases, mesmo resultado
conds = [json.loads(f.read_text(encoding="utf-8"))["saida"]["condicoes"] for f in sorted((RAIZ / "saida" / "extracoes").glob("*.json"))]
conds += [{"trechos": ["Frete de R$ 40,00 para pedidos abaixo de R$ 1.000,00."], "frete_gratis_acima_de": None, "pedido_minimo": None,
           "desconto_percentual": None},
          {"trechos": ["Para pedidos acima de R$ 2.000,00 concedemos 5% de desconto.", "Frete grátis."], "desconto_percentual": 5},
          {"trechos": ["Não tem pedido mínimo não, o frete é vinte e cinco reais."], "pedido_minimo": None, "frete_valor": 25},
          {"trechos": ["pedido minimo 300 reais"], "pedido_minimo": None}]
script2 = f"const {{conferirCondicoes}} = require('{js_src}'); const d = JSON.parse(require('fs').readFileSync(0, 'utf8'));"           "process.stdout.write(JSON.stringify(d.map(conferirCondicoes)));"
js2 = json.loads(subprocess.run(["node", "-e", script2], input=json.dumps(conds), capture_output=True, text=True,
                                encoding="utf-8", check=True).stdout)
dif2 = [(i, a, b) for i, (a, b) in enumerate(zip([regras.conferir_condicoes(c) for c in conds], js2)) if a != b]
print(f"{len(conds)} condições comparadas, {len(dif2)} diferenças")
for d in dif2:
    print("  DIF", d)
sys.exit(1 if dif or dif2 else 0)
