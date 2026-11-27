# Plano do protótipo: Cotação Inteligente

## Problema
Num restaurante, a cotação semanal de compras chega de cinco jeitos diferentes: mensagem de WhatsApp, áudio transcrito, PDF de orçamento, planilha do fornecedor e e-mail. Cada fornecedor cota numa embalagem diferente, como caixa de 20 kg, bolinha de 125 g ou fardo de 12 garrafas. Cada um também tem suas condições: pedido mínimo, frete e desconto acima de certo valor. Hoje alguém passa tudo para uma planilha à mão, converte para o preço por quilo, compara e monta os pedidos. Isso leva horas e tem erros de digitação.

## O que o protótipo faz
1. **Lê** as cotações do jeito que elas chegam: texto, PDF ou planilha.
2. **Extrai com o Claude.** O Claude transforma cada cotação em dados estruturados (item do catálogo, embalagem, preço e condições) e marca o grau de confiança e o motivo de cada dúvida. O Claude não faz conta.
3. **Calcula e valida com código.** O código converte para o preço por unidade-base e compara com o último preço pago. Manda para revisão humana as variações acima de 35%, a confiança baixa, a embalagem sem tamanho e os itens fora do catálogo.
4. **Compara.** Acha o melhor fornecedor por item e aplica o pedido mínimo, o frete e o desconto. A necessidade é calculada pelo consumo semanal menos o estoque, arredondada para embalagens inteiras.
5. **Entrega:**
   - o mapa de cotação em Excel, com as abas Mapa, Pedido, Revisão e Log;
   - as mensagens de pedido de cada fornecedor, prontas para o WhatsApp;
   - o resumo para o gestor, com a economia em relação ao último preço pago.
6. **Pessoa no circuito.** Nada é enviado sozinho. O humano aprova a aba Revisão e as mensagens.
7. **Avaliação.** Um gabarito por cotação mede a acurácia da extração. Rodo, meço, corrijo e registro as falhas no `docs/falhas.md`.

## Decisões de desenho (AI Fluency)
- **Delegation:** o Claude faz o que regra fixa não faz bem, que é ler texto bagunçado e casar "mussarela bufala bolinha" com o item do catálogo. Conta, conversão e regra de negócio ficam com o código, que é determinístico e auditável.
- **Description:** um prompt com o catálogo, um esquema JSON obrigatório (structured output) e as regras de unidade.
- **Discernment:** o modelo dá a confiança e o motivo de cada item, o código confere contra o histórico e os casos duvidosos vão para revisão.
- **Diligence:** o gabarito e as métricas, o log de cada execução e nenhum envio automático.
- **Automation × augmentation:** a extração e o mapa são automação. A decisão de compra é augmentation, porque o humano aprova.

## Dados
Os dados são sintéticos, baseados na operação real de compras de um restaurante italiano: 18 itens e 5 fornecedores. Cada cotação tem armadilhas de propósito: preço por embalagem, número por extenso, erro de digitação, item fora do catálogo, item em falta e desconto condicional.

## Fora do escopo desta noite
- Deixei pronto um fluxo do n8n equivalente (`n8n/`), mas **não o testei**, porque o n8n não está instalado. Instalar exige a sua autorização.
- Não há integração real com o WhatsApp nem com o Gmail. As entradas são arquivos numa pasta.

## Entregáveis
- `cotador/`: o código.
- `python -m cotador` roda tudo de ponta a ponta.
- `saida/`: os resultados.
- `docs/`: o estudo de caso, as falhas encontradas, os prints e o roteiro para entrevista.
