// Porte de cotador/regras.py para o nó Code do n8n. Testado contra a versão Python em n8n/testar_normalizar.py.
const CONVERSAO = { kg: ['kg', 1], g: ['kg', 0.001], L: ['L', 1], ml: ['L', 0.001], un: ['un', 1], 'dúzia': ['un', 12], 'maço': ['maço', 1] };
const LIMITE_VARIACAO = 0.35;
const arred = (v, c) => Math.round(v * 10 ** c) / 10 ** c;

function normalizar(item, catalogo) {
  const r = { ...item, pendencias: [] };
  const cod = item.codigo_catalogo;
  if (cod === null) { r.status = 'fora_catalogo'; return r; }
  if (!catalogo[cod]) { r.status = 'revisao'; r.pendencias.push(`código ${cod} não existe no catálogo`); return r; }
  if (!item.disponivel || item.preco === null) { r.status = 'indisponivel'; return r; }
  const base = catalogo[cod].unidade;
  const qtd = item.quantidade_na_embalagem, un = item.unidade_da_quantidade;
  if (qtd === null || un === null) { r.status = 'revisao'; r.pendencias.push('embalagem sem tamanho'); return r; }
  const [unBase, fator] = CONVERSAO[un] || [null, null];
  if (unBase !== base) { r.status = 'revisao'; r.pendencias.push(`unidade ${un} não converte para ${base}`); return r; }
  const tamanho = qtd * fator;
  r.embalagem_em_base = arred(tamanho, 6);
  r.preco_base = item.preco_refere_a === 'embalagem' ? arred(item.preco / tamanho, 4) : item.preco;
  if (item.preco_refere_a === 'unidade') r.embalagem_em_base = null;
  const ultimo = catalogo[cod].ultimo_preco;
  const v = r.preco_base / ultimo - 1;
  r.variacao_vs_ultimo = arred(v, 4);
  if (Math.abs(v) > LIMITE_VARIACAO) {
    const pct = `${v >= 0 ? '+' : '-'}${Math.round(Math.abs(v) * 100)}%`;
    r.pendencias.push(`preço ${pct} em relação ao último pago (R$ ${ultimo.toFixed(2).replace('.', ',')}/${base})`);
  }
  if (item.confianca === 'baixa') r.pendencias.push('confiança baixa na leitura' + (item.observacao ? `: ${item.observacao}` : ''));
  r.status = r.pendencias.length ? 'revisao' : 'ok';
  return r;
}
function conferirCondicoes(cond) {
  const frases = (cond.trechos || []).flatMap(t => t.replace(/;/g, '.').split('.')).map(f => f.toLowerCase());
  const trechos = frases.join(' ');
  const avisos = [];
  const freteCond = frases.some(f => f.includes('frete') && ['abaixo de', 'acima de', 'a partir de'].some(k => f.includes(k)));
  if (freteCond && cond.frete_gratis_acima_de == null)
    avisos.push('o texto fala de frete condicionado a um valor, mas o limite do frete grátis não foi registrado');
  if (trechos.includes('desconto') && cond.desconto_percentual == null)
    avisos.push('o texto fala de desconto, mas o percentual não foi registrado');
  // "não tem pedido mínimo" / "sem pedido mínimo" não conta
  const falaMinimo = frases.some(f => f.replace(/minimo/g, 'mínimo').includes('mínimo') && !(f.includes('não') || f.includes('nao ') || f.includes('sem ')));
  if (falaMinimo && cond.pedido_minimo == null)
    avisos.push('o texto fala de pedido mínimo, mas o valor não foi registrado');
  return avisos;
}
if (typeof module !== 'undefined') module.exports = { normalizar, conferirCondicoes };
