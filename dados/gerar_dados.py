# -*- coding: utf-8 -*-
"""Gera os dados sintéticos do protótipo: catálogo, cotações de entrada (txt, pdf, xlsx) e gabarito.
Uso: python dados/gerar_dados.py   (a partir da raiz do projeto)"""
import json, pathlib, subprocess, shutil
from openpyxl import Workbook
from openpyxl.styles import Font

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ENT, GAB = RAIZ / "entrada", RAIZ / "gabarito"
ENT.mkdir(exist_ok=True); GAB.mkdir(exist_ok=True)

# codigo, nome, unidade-base, consumo semanal, estoque atual, último preço pago (por unidade-base)
CATALOGO = [
    ("P01", "Tomate pelado italiano", "kg", 30, 8, 16.50),
    ("P02", "Muçarela de búfala", "kg", 12, 3, 78.00),
    ("P03", "Parmesão Grana Padano", "kg", 6, 2, 135.00),
    ("P04", "Farinha de trigo tipo 00", "kg", 50, 15, 9.80),
    ("P05", "Azeite extravirgem", "L", 10, 4, 52.00),
    ("P06", "Guanciale", "kg", 4, 1, 145.00),
    ("P07", "Filé mignon limpo", "kg", 15, 4, 89.00),
    ("P08", "Camarão VG limpo", "kg", 8, 2, 115.00),
    ("P09", "Rúcula", "maço", 40, 10, 3.50),
    ("P10", "Manjericão", "maço", 30, 5, 4.00),
    ("P11", "Limão tahiti", "kg", 10, 3, 6.00),
    ("P12", "Cebola", "kg", 20, 6, 5.20),
    ("P13", "Alho descascado", "kg", 4, 1, 32.00),
    ("P14", "Creme de leite fresco", "L", 12, 4, 24.00),
    ("P15", "Ovos", "un", 360, 90, 0.85),
    ("P16", "Manteiga sem sal", "kg", 6, 2, 58.00),
    ("P17", "Batata", "kg", 25, 8, 6.50),
    ("P18", "Água mineral sem gás 500 ml", "un", 240, 60, 1.40),
]
(RAIZ / "dados" / "catalogo.json").write_text(json.dumps(
    [dict(codigo=c, nome=n, unidade=u, consumo_semanal=s, estoque=e, ultimo_preco=p) for c, n, u, s, e, p in CATALOGO],
    ensure_ascii=False, indent=1), encoding="utf-8")

# ---------- F1: WhatsApp, texto curto e abreviado ----------
(ENT / "01_whatsapp_hortifruti_bom_preco.txt").write_text("""[28/10/26 07:12] Hortifruti Bom Preço: Bom dia chef!! segue cotação da semana
[28/10/26 07:12] Hortifruti Bom Preço: rucula maço 3,20
manjericao 3,80 o maço
limao tahiti cx 20kg 98,00
cebola saco 20kg 89
alho descascado pct 1kg 29,90
batata lavada saco 25 kg 135
tomate cereja bandeja 500g 7,50
[28/10/26 07:13] Hortifruti Bom Preço: pedido minimo 300 reais, entrego ter e sex. pix na entrega
[28/10/26 07:13] Hortifruti Bom Preço: preço vale até sexta 👍
""", encoding="utf-8")

# ---------- F2: PDF de orçamento formal ----------
html_f2 = """<!doctype html><html><head><meta charset="utf-8"><style>
body{font-family:Arial;font-size:12px;margin:40px} table{border-collapse:collapse;width:100%} td,th{border:1px solid #999;padding:6px;text-align:left}
h1{font-size:18px} .r{text-align:right}</style></head><body>
<h1>LATICÍNIOS SERRA FINA LTDA</h1><p>CNPJ 00.000.000/0001-00 · Petrópolis, RJ</p>
<p><b>ORÇAMENTO Nº 4471</b> · Data: 28/10/2026 · Validade: 7 dias</p>
<p>Cliente: Restaurante (cozinha central)</p>
<table><tr><th>Cód.</th><th>Descrição</th><th>Embalagem</th><th class="r">Valor unit.</th></tr>
<tr><td>1120</td><td>Mussarela de búfala bolinha</td><td>un 125 g</td><td class="r">R$ 10,40</td></tr>
<tr><td>1301</td><td>Queijo Grana Padano DOP (peça aprox. 4,5 kg)</td><td>kg</td><td class="r">R$ 139,00</td></tr>
<tr><td>2010</td><td>Creme de leite fresco 35% gordura</td><td>garrafa 1 L</td><td class="r">R$ 22,90</td></tr>
<tr><td>2205</td><td>Manteiga sem sal</td><td>tablete 200 g</td><td class="r">R$ 12,50</td></tr>
<tr><td>3001</td><td>Ovos brancos tipo extra</td><td>caixa 30 dúzias</td><td class="r">R$ 279,00</td></tr>
</table>
<p><b>Condições comerciais:</b> pedido mínimo de R$ 500,00. Frete de R$ 40,00 para pedidos abaixo de R$ 1.000,00.
Pagamento: boleto 21 dias. Entrega em até 2 dias úteis.</p></body></html>"""
tmp = RAIZ / "dados" / "_f2.html"; tmp.write_text(html_f2, encoding="utf-8")
edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
subprocess.run([edge, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={ENT / '02_orcamento_laticinios_serra_fina.pdf'}", tmp.as_uri()],
               check=True, capture_output=True)
tmp.unlink()

# ---------- F3: planilha do fornecedor, com um erro de digitação ----------
wb = Workbook(); ws = wb.active; ws.title = "Tabela"
ws.append(["EMPÓRIO ITÁLIA DISTRIBUIDORA", "", "", ""]); ws["A1"].font = Font(bold=True)
ws.append(["Tabela de preços semana 44", "", "", ""]); ws.append([])
ws.append(["PRODUTO", "EMB.", "PREÇO (R$)", "OBS"])
for r in [("Tomate pelado San Marzano lata", "lata 2,5 kg", 39.90, ""),
          ("Farinha 00 Caputo pizzeria", "saco 25 kg", 219.00, ""),
          ("Azeite extra virgem", "lata 5 L", 249.00, ""),
          ("Guanciale", "kg", 152.00, "peça ~1,2 kg"),
          ("Grana Padano", "kg", 128.00, ""),
          ("Mozzarella di bufala", "kg", 7.90, ""),
          ("Água mineral s/ gás 500ml", "fardo 12 un", 15.60, "")]:
    ws.append(list(r))
ws.append([]); ws.append(["Pedido mínimo R$ 1.500,00 · Frete grátis · Pagamento 28 dias"])
wb.save(ENT / "03_tabela_emporio_italia.xlsx")

# ---------- F4: e-mail com desconto condicional ----------
(ENT / "04_email_frigorifico_atlantico.txt").write_text("""De: comercial@frigorificoatlantico.example
Assunto: RE: Cotação semana 44

Prezado,

Segue nossa cotação para esta semana:

- Filé mignon limpo (sem cordão): R$ 92,50/kg
- Camarão VG limpo congelado, caixa 2 kg: R$ 219,00 a caixa

Para pedidos acima de R$ 2.000,00 concedemos 5% de desconto no total.
Preços sujeitos a variação, validade de 48h. Faturamento 14 dias.

Atenciosamente,
Rafael · Frigorífico Atlântico
""", encoding="utf-8")

# ---------- F5: áudio transcrito, números por extenso ----------
(ENT / "05_audio_transcrito_hortifruti_sol.txt").write_text("""[Transcrição de áudio do WhatsApp, Hortifruti Sol, 28/10/26 08:40]
Oi chef, bom dia, tudo bem? Então, essa semana tá assim: limão tá quatro e cinquenta o quilo, cebola cinco reais o quilo,
batata seis e vinte o quilo. Rúcula tô fazendo três e cinquenta o maço. Alho descascado tá trinta e dois o quilo.
Manjericão acabou, só semana que vem. Tomate pelado eu não trabalho. Não tem pedido mínimo não, o frete é vinte e cinco reais.
Pode mandar o pedido até quinta, beleza? Abraço.
""", encoding="utf-8")

# ---------- Gabarito: preço por unidade-base esperado e o que deve ir para revisão ----------
GABARITO = {
 "01_whatsapp_hortifruti_bom_preco.txt": {"fornecedor": "Hortifruti Bom Preço", "pedido_minimo": 300, "frete": 0,
   "frete_gratis_acima_de": None, "desconto_percentual": None, "desconto_acima_de": None,
   "itens": {"P09": 3.20, "P10": 3.80, "P11": 4.90, "P12": 4.45, "P13": 29.90, "P17": 5.40},
   "fora_catalogo": ["tomate cereja"], "revisao": []},
 "02_orcamento_laticinios_serra_fina.pdf": {"fornecedor": "Laticínios Serra Fina", "pedido_minimo": 500, "frete": 40,
   "frete_gratis_acima_de": 1000, "desconto_percentual": None, "desconto_acima_de": None,
   "itens": {"P02": 83.20, "P03": 139.00, "P14": 22.90, "P16": 62.50, "P15": 0.775},
   "fora_catalogo": [], "revisao": []},
 "03_tabela_emporio_italia.xlsx": {"fornecedor": "Empório Itália", "pedido_minimo": 1500, "frete": 0,
   "frete_gratis_acima_de": None, "desconto_percentual": None, "desconto_acima_de": None,
   "itens": {"P01": 15.96, "P04": 8.76, "P05": 49.80, "P06": 152.00, "P03": 128.00, "P02": 7.90, "P18": 1.30},
   "fora_catalogo": [], "revisao": ["P02"]},
 "04_email_frigorifico_atlantico.txt": {"fornecedor": "Frigorífico Atlântico", "pedido_minimo": 0, "frete": 0,
   "frete_gratis_acima_de": None, "desconto_percentual": 5, "desconto_acima_de": 2000,
   "itens": {"P07": 92.50, "P08": 109.50}, "fora_catalogo": [], "revisao": []},
 "05_audio_transcrito_hortifruti_sol.txt": {"fornecedor": "Hortifruti Sol", "pedido_minimo": 0, "frete": 25,
   "frete_gratis_acima_de": None, "desconto_percentual": None, "desconto_acima_de": None,
   "itens": {"P11": 4.50, "P12": 5.00, "P17": 6.20, "P09": 3.50, "P13": 32.00},
   "fora_catalogo": [], "revisao": []},
}
(GAB / "gabarito.json").write_text(json.dumps(GABARITO, ensure_ascii=False, indent=1), encoding="utf-8")
print("ok:", sorted(p.name for p in ENT.iterdir()))
