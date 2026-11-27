# -*- coding: utf-8 -*-
"""Gera o workflow do n8n (versão para produção leve) a partir do mesmo prompt, esquema e catálogo do Python.
Uso: python n8n/gerar_workflow.py  ->  n8n/cotacao_inteligente.json (importar no n8n: Workflows > Import from file)"""
import json, pathlib, sys
RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from cotador import extrair

catalogo = json.loads((RAIZ / "dados" / "catalogo.json").read_text(encoding="utf-8"))
SISTEMA = extrair.montar_sistema(catalogo)
NORMALIZAR_JS = (RAIZ / "n8n" / "normalizar.js").read_text(encoding="utf-8")

montar_req = f"""// Junta o corpo do e-mail e o texto do PDF anexo e monta a chamada à API da Anthropic.
const email = $('Gmail: cotação recebida').first().json;
const pdf = $input.first().json.text || '';
const texto = `De: ${{email.from?.text || ''}}\\nAssunto: ${{email.subject || ''}}\\n\\n${{email.text || ''}}\\n\\n${{pdf}}`;
const body = {{
  model: 'claude-sonnet-5-5',
  max_tokens: 4096,
  system: {json.dumps(SISTEMA, ensure_ascii=False)},
  messages: [{{ role: 'user', content: `---- COTAÇÃO ----\\n${{texto}}\\n---- FIM ----` }}],
  tools: [{{ name: 'registrar', description: 'Registra a cotação estruturada', input_schema: {json.dumps(extrair.SCHEMA, ensure_ascii=False)} }}],
  tool_choice: {{ type: 'tool', name: 'registrar' }},
}};
return [{{ json: {{ body }} }}];"""

normalizar = f"""// Mesmas regras de cotador/regras.py: conversão para unidade-base e validação. O modelo não faz conta.
const CATALOGO = {json.dumps({c['codigo']: c for c in catalogo}, ensure_ascii=False)};
{NORMALIZAR_JS}
const bloco = $input.first().json.content.find(b => b.type === 'tool_use');
const cot = bloco.input;
const itens = cot.itens.map(i => normalizar(i, CATALOGO));
const linhas = itens.map(i => ({{
  json: {{ data: $now.toFormat('yyyy-MM-dd'), fornecedor: cot.fornecedor, codigo: i.codigo_catalogo, texto: i.texto_original,
          preco_cotado: i.preco, embalagem: i.embalagem, preco_base: i.preco_base ?? null, status: i.status,
          pendencias: (i.pendencias || []).join('; '), pedido_minimo: cot.condicoes.pedido_minimo,
          frete: cot.condicoes.frete_valor,
          alertas: [...(cot.alertas || []), ...conferirCondicoes(cot.condicoes)].join(' | ') }}
}}));
return linhas;"""

resumo_revisao = """// Junta os itens que precisam de revisão humana num e-mail para o comprador.
const pend = $input.all().map(x => x.json).filter(x => x.status === 'revisao' || x.alertas);
if (!pend.length) return [];
const corpo = pend.map(p => `• ${p.fornecedor}: "${p.texto}" -> ${p.pendencias || ''} ${p.alertas ? 'ALERTA: ' + p.alertas : ''}`).join('\\n');
return [{ json: { assunto: `Cotação: ${pend.length} item(ns) para revisar`, corpo } }];"""

def no(nome, tipo, versao, pos, params, **extra):
    d = {"parameters": params, "name": nome, "type": tipo, "typeVersion": versao, "position": pos}
    d.update(extra)
    return d

nodes = [
    no("Gmail: cotação recebida", "n8n-nodes-base.gmailTrigger", 1.2, [0, 0],
       {"pollTimes": {"item": [{"mode": "everyX", "value": 15, "unit": "minutes"}]}, "simple": False,
        "filters": {"q": "subject:(cotação OR cotacao OR orçamento)"}, "options": {"downloadAttachments": True}}),
    no("Texto do PDF anexo", "n8n-nodes-base.extractFromFile", 1, [220, 0],
       {"operation": "pdf", "binaryPropertyName": "attachment_0", "options": {"joinPages": True}},
       onError="continueRegularOutput", alwaysOutputData=True),
    no("Montar chamada ao Claude", "n8n-nodes-base.code", 2, [440, 0], {"jsCode": montar_req}),
    no("Claude: estruturar cotação", "n8n-nodes-base.httpRequest", 4.2, [660, 0],
       {"method": "POST", "url": "https://api.anthropic.com/v1/messages", "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth", "sendHeaders": True,
        "headerParameters": {"parameters": [{"name": "anthropic-version", "value": "2023-06-01"}]},
        "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify($json.body) }}",
        "options": {"timeout": 120000}},
       credentials={"httpHeaderAuth": {"id": "CONFIGURAR", "name": "Anthropic API (header x-api-key)"}},
       retryOnFail=True, maxTries=2),
    no("Normalizar e validar", "n8n-nodes-base.code", 2, [880, 0], {"jsCode": normalizar}),
    no("Planilha: mapa de cotação", "n8n-nodes-base.googleSheets", 4.5, [1100, -120],
       {"operation": "append", "documentId": {"__rl": True, "mode": "url", "value": "COLE_AQUI_A_URL_DA_PLANILHA"},
        "sheetName": {"__rl": True, "mode": "name", "value": "Cotações"},
        "columns": {"mappingMode": "autoMapInputData", "value": {}}, "options": {}},
       credentials={"googleSheetsOAuth2Api": {"id": "CONFIGURAR", "name": "Google Sheets"}}),
    no("Itens para revisão", "n8n-nodes-base.code", 2, [1100, 120], {"jsCode": resumo_revisao}),
    no("Rascunho para o comprador", "n8n-nodes-base.gmail", 2.1, [1320, 120],
       {"resource": "draft", "subject": "={{ $json.assunto }}", "message": "={{ $json.corpo }}",
        "options": {"sendTo": "comprador@exemplo.com"}},
       credentials={"gmailOAuth2": {"id": "CONFIGURAR", "name": "Gmail"}}),
]
conexoes = {}
def liga(a, b):
    conexoes.setdefault(a, {"main": [[]]})["main"][0].append({"node": b, "type": "main", "index": 0})
liga("Gmail: cotação recebida", "Texto do PDF anexo")
liga("Texto do PDF anexo", "Montar chamada ao Claude")
liga("Montar chamada ao Claude", "Claude: estruturar cotação")
liga("Claude: estruturar cotação", "Normalizar e validar")
liga("Normalizar e validar", "Planilha: mapa de cotação")
liga("Normalizar e validar", "Itens para revisão")
liga("Itens para revisão", "Rascunho para o comprador")

wf = {"name": "Cotação Inteligente (Claude)", "nodes": nodes, "connections": conexoes, "active": False,
      "settings": {"executionOrder": "v1"}, "pinData": {}, "meta": {"templateCredsSetupCompleted": False}}
(RAIZ / "n8n" / "cotacao_inteligente.json").write_text(json.dumps(wf, ensure_ascii=False, indent=1), encoding="utf-8")
print("ok:", len(nodes), "nós")
