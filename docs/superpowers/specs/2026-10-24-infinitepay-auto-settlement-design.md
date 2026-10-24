# Baixa automática pela InfinitePay — design

Data: 2026-10-24 · Status: **aprovado pelo Thiago (24/10)**, com a chave de API incluída a pedido dele

## Intenção

Hoje o aluno paga a mensalidade pelo Pix copia e cola da página `/pagar`, o
dinheiro cai na conta do mestre e **o Katsuflow não fica sabendo**: o mestre
confere o banco e dá a baixa à mão.

A ideia: o mestre que quiser liga o **recebimento pela InfinitePay**. O link da
cobrança passa a levar o aluno ao checkout da InfinitePay, criado pelo
Katsuflow com um número próprio (`order_nsu`). Quando o aluno paga, a
InfinitePay avisa o Katsuflow (webhook), o Katsuflow **confere com a própria
InfinitePay** e dá a baixa sozinho, na hora. O Pix na InfinitePay **não tem
taxa**. É um bônus da plataforma: quem não quiser, segue como hoje.

O Katsuflow **nunca toca no dinheiro**: o pagamento vai do aluno direto para a
conta InfinitePay do mestre. Só ficamos sabendo que foi pago.

### Por que InfinitePay (resumo do estudo de 23–24/10)

- Pix estático com txid próprio: **recusado** por Inter e InfinitePay como
  recebedores (teste real) → não dá para identificar o pagamento no Pix de hoje.
- Importar extrato: inviável — a conta do mestre mistura academia, família e
  vendas.
- Empresas com API Pix (Asaas, Efí…): cobram por Pix; webhook direto de banco
  só para PJ e com certificado.
- InfinitePay Checkout Integrado: Pix sem taxa, conta PF serve, integração só
  com a InfiniteTag, webhook com o nosso `order_nsu` e conferência
  (`payment_check`). **Testado de ponta a ponta em 24/10** (R$ 2,00).

Detalhes e prints no Obsidian: "Integração InfinitePay (ideia)" e "Guia do
mestre — ligar a InfinitePay (rascunho)".

## Objetivos

1. Em Configurações → Cobrança, o mestre liga a baixa automática por uma
   janela de 3 etapas e informa a InfiniteTag; o Katsuflow testa e liga.
2. Com a integração ligada, a página `/pagar` mostra **"Pagar mensalidade"**
   (ou "Pagar mensalidades"), que leva ao checkout da InfinitePay com o
   **total em aberto**.
3. Ao receber o aviso da InfinitePay, o Katsuflow confere com o
   `payment_check` e dá a baixa automática (abatendo do mais antigo, a mesma
   regra da baixa manual).
4. O mestre vê a baixa automática marcada como tal, com o recibo da
   InfinitePay, ao lado das manuais.
5. A baixa manual continua existindo e funcionando igual.

## Fora do escopo

- **O que fazer se a InfinitePay passar a cobrar pelo Pix** — PENDENTE, a
  revisar depois; nada definido (ver Obsidian). Nenhuma trava/aviso nesta
  versão.
- Envio de cobrança por e-mail (worker) — tema próprio, depois.
- Pagamento de exames de graduação — tema próprio, depois (vai reaproveitar
  esta integração).
- Pagamento parcial ou escolha de meses pelo aluno (ver Decisões).
- Criar a conta da InfinitePay por dentro do Katsuflow (não existe API para
  isso; é feito no app deles).
- Prints e vídeo dentro da janela de etapas — o guia com imagens está sendo
  montado no Obsidian; nesta versão a janela tem o texto dos passos (ver
  "Deixado ao construtor").

## Decisões do Thiago (24/10)

- **Opcional por academia.** "Quem não quiser usar, beleza" — a automação é
  oferecida, não imposta.
- **A dívida vai completa.** "O aluno nunca escolhe, ele é o devedor." O link
  cobra **todo o total em aberto** que a página `/pagar` mostra. Sem "pagar
  outro valor": parcial ou parcelamento só negociando com o mestre, que lança
  à mão.
- **A baixa manual nunca sai do sistema** (dinheiro, negociação, Pix direto).
- **Botão na página do aluno: "Pagar mensalidade"** — não "Pagar com Pix",
  porque o checkout oferece Pix e cartão.
- **Cartão fica disponível** (a InfinitePay não deixa desligar); o mestre
  configura no app deles "repassar as taxas" para a taxa do cartão ficar com o
  aluno. O Pix segue sem taxa.
- **Tela do mestre: opção "B" no layout atual** — um convite "Receba com baixa
  automática · GRÁTIS" dentro do cartão **Cobrança** de Configurações; "Ligar"
  abre uma **janela de 3 etapas** (Conta → Checkout → Sua tag). Menu e seções
  continuam iguais.
- **Passo a passo completo**, com as pegadinhas reais (ver "Ligar a
  integração").

## Como funciona

### 1. Ligar a integração (mestre)

Cartão **Cobrança** em Configurações ganha, no topo, o convite "Receba com
baixa automática · GRÁTIS — o aluno paga pela InfinitePay e a mensalidade fica
paga sozinha, na hora. Pix sem taxa." com o botão **Ligar**.

"Ligar" abre uma janela (o mesmo componente de janela/gaveta do site) com 3
etapas:

1. **Conta** — baixar o app da InfinitePay, criar a conta (CPF serve),
   cadastrar uma chave Pix lá dentro e anotar a InfiniteTag (o nome com `$`).
2. **Checkout** — no app da InfinitePay, em Checkout → Configurações:
   criar o primeiro checkout se o app pedir; **ligar "Habilitar Checkout
   Integrado" pelo app do celular** (pela web o botão aparecia ligado mas não
   valia — só funcionou desligando e ligando de novo no app); **desligar
   "Etapa de endereço"**; em Meios de pagamento, deixar o cartão com "repassar
   todas as taxas". Mostrar também os nomes em inglês (o app pode estar em
   inglês: Settings, Enable Integrated Checkout, Address step, Payment
   methods, Pass on all fees).
3. **Sua tag e sua chave** — campo "Sua InfiniteTag" (aceita com ou sem `$`)
   e campo **"Chave de API"**: no app da InfinitePay, Checkout →
   Configurações → **API Keys** → criar uma chave (ex.: nome "katsuflow") →
   copiar (ela aparece **uma vez só**) e colar aqui. Botão **Testar e ligar**.

**Testar e ligar**: o servidor tenta criar um link de checkout de teste
(R$ 1,00, item "Teste de conexão Katsuflow", sem webhook) **usando a chave de
API** (header `X-Api-Key`). Não é pago e expira sozinho.

- Link criado → salva a tag, liga a integração, guarda a data do teste.
- Chave recusada (HTTP 403 "Forbidden") → **não liga** e mostra: "A chave
  de API não foi aceita. Crie uma chave nova no app da InfinitePay (Checkout →
  Configurações → API Keys) e cole aqui."
- Erro `external_checkout_not_enabled` → **não liga** e mostra o que fazer:
  "A InfinitePay ainda não liberou o checkout para essa tag. Confira se a tag
  está certa e, no app da InfinitePay, desligue e ligue de novo 'Habilitar
  Checkout Integrado'." (Atenção: a InfinitePay devolve esse mesmo erro para
  tag inexistente — a mensagem cobre os dois casos.)
- Falha de rede/timeout → "Não foi possível falar com a InfinitePay agora.
  Tente de novo."

Ligada, o convite vira: "✓ Baixa automática ligada · $tag · testada em
24/10/2026" com **Trocar chave** e **Desligar** (confirmação simples). A chave
**nunca volta a aparecer** na tela (no máximo os 4 últimos caracteres). Desligar volta a página
`/pagar` ao copia e cola na hora; o que já foi pago continua registrado.

O bloco Pix (chave, tipo, cidade) continua como está e continua sendo usado
quando a integração está desligada.

### 2. O aluno paga

Página `/pagar/<token>` com a integração **ligada** e algo em aberto:

- Mesmo topo de hoje (academia, mestre, total, lista do que está em aberto).
- Botão principal **"Pagar mensalidade"** (plural se mais de uma cobrança).
- Texto curto embaixo: "Você vai para a página segura da InfinitePay. Lá você
  escolhe Pix ou cartão e confirma com um código que chega no seu WhatsApp."
- **Sem** o "Copiar código Pix" nesse modo (um caminho só).

Quando o mestre dá **baixa manual** num aluno que tem link em aberto, o
Katsuflow marca esse link como cancelado do seu lado: a página `/pagar` não
reaproveita mais esse link (se ainda houver dívida, cria outro com o valor
certo). Na InfinitePay o link antigo continua pagável (não há como cancelar
pela API) — se for pago, cai no passo 5 da seção 3.

Ao tocar, o navegador chama `POST /public/pay/{token}/checkout`. O servidor:

1. Recalcula o total em aberto (a mesma conta da página — hoje, as cobranças
   vencidas).
2. Reaproveita um link ainda válido do mesmo aluno com **o mesmo total**
   (para não criar um link novo a cada toque); senão cria um na InfinitePay:
   - autenticação pela **chave de API** da academia (header `X-Api-Key`);
     com ela a InfinitePay identifica a conta (a tag não é obrigatória na
     criação do link);
   - `order_nsu`: identificador **aleatório e impossível de adivinhar**,
     gerado pelo Katsuflow, guardado com academia, aluno e valor;
   - `items`: uma linha por cobrança em aberto (o mesmo rótulo da página,
     ex. "Mensalidade outubro/2026 — Kickboxing"), preço em centavos;
   - `customer`: nome e telefone de quem paga (a mesma regra do WhatsApp:
     menor de 18 com responsável → o responsável), e-mail se houver;
   - `redirect_url`: volta para `/pagar/<token>`;
   - `webhook_url`: rota pública de avisos do Katsuflow.
3. Devolve a URL; o navegador abre o checkout.

No checkout (da InfinitePay, não muda): escolhe Pix ou cartão → "Fazer
Pedido" → código no WhatsApp → copia o Pix → paga no banco.

Ao voltar para `/pagar/<token>`: se a baixa já entrou, a página mostra o
estado "Tudo em dia"/"Pagamento recebido"; se o aviso ainda não chegou,
mostra "Confirmando seu pagamento…" e tenta de novo por alguns segundos.

Com a integração **desligada**, a página fica exatamente como hoje.

### 3. O aviso chega e a baixa entra

Rota pública `POST /webhooks/infinitepay` (sem login). Corpo enviado pela
InfinitePay: `order_nsu`, `transaction_nsu`, `invoice_slug`, `amount`,
`paid_amount`, `capture_method` (`pix` ou `credit_card`), `installments`,
`receipt_url`, `items`.

1. Procura o link pelo `order_nsu`. Desconhecido → responde 200 e ignora
   (registra no log).
2. **Confere com a InfinitePay** (`POST /payment_check` com `handle`,
   `order_nsu`, `transaction_nsu`, `slug`). O aviso não tem assinatura;
   **nada de baixa sem `paid: true` vindo do `payment_check`**. Valor pago
   conferido tem que ser ≥ valor do link.
3. **Uma vez só**: se esse `transaction_nsu` já virou baixa, responde 200 e
   não faz nada (a InfinitePay reenvia avisos).
4. Dá a baixa com a mesma regra da baixa manual (abate do mais antigo), valor
   = valor do link, data = hoje (horário de Brasília), forma = Pix ou cartão
   (`capture_method`), origem = InfinitePay, com `transaction_nsu`, `slug` e
   `receipt_url` guardados.
5. **A baixa só entra se o valor do link ainda bate com o que o aluno deve
   naquele momento** (o mesmo total vencido que a página `/pagar` mostraria).
   Se não bater — ex.: o mestre deu baixa à mão no meio do caminho e o aluno
   pagou o link também — **nada é lançado sozinho** (nem como adiantamento):
   o pagamento inteiro fica **"recebido, a conferir"** e aparece ao mestre na
   ficha do aluno → Mensalidades: "Pagamento de R$ X recebido pela InfinitePay
   em DD/MM, mas o valor em aberto mudou. Confira e, se for o caso, lance à mão
   ou devolva." (com o recibo). O mestre pode marcar como resolvido.
   O Thiago considera esse caso **muito raro** ("acho difícil bem difícil de
   pagar duplicado"); por isso não há divisão automática do valor.
6. Responde rápido (a InfinitePay pede < 1 s). Se a conferência falhar por
   rede, responde erro para a InfinitePay reenviar.

**Se o aviso se perder** (decisão do Claude, revisão de 24/10): quando o aluno
volta do checkout para `/pagar/<token>`, a InfinitePay acrescenta ao endereço
`order_nsu`, `transaction_nsu`, `slug` e `receipt_url`. A página manda esses
dados ao servidor, que roda **exatamente o mesmo processamento do aviso**
(passos 1–5: confere no `payment_check`, uma vez só). Assim a baixa entra mesmo
se o aviso nunca chegar, desde que o aluno volte para a página. Mesma proteção
de limite de requisições da página pública.

**Links abertos ao desligar ou trocar a tag** (decisão do Claude, revisão de
24/10): cada link guarda a tag com que foi criado. Se o aluno pagar um link
antigo depois de o mestre desligar a integração ou trocar a tag, o pagamento
**ainda entra automaticamente**, conferido com a tag guardada no link (o
dinheiro foi para a conta do mestre do mesmo jeito).

### 4. O que o mestre vê

- Ficha do aluno → Mensalidades → histórico de pagamentos: a baixa
  automática aparece com o selo **"Automática · InfinitePay"**, a forma (Pix
  ou cartão) e o link **"Ver recibo"**. As manuais seguem como hoje.
- Desfazer uma baixa automática funciona como a manual (o dinheiro já está na
  conta InfinitePay do mestre; desfazer só mexe no controle do Katsuflow).
- Página Mensalidades e dashboard não mudam: os números já refletem as baixas.

## Dados (indicativo — o construtor ajusta)

- Configurações de cobrança da academia: `infinitepay_handle`,
  `infinitepay_api_key` (**criptografada**), `infinitepay_enabled`,
  `infinitepay_tested_at`.
- Tabela nova de links de checkout: academia, aluno, tag usada,
  `order_nsu` (único),
  valor, URL, criado em, situação (aberto / pago / recebido a conferir /
  resolvido), dados do pagamento (`transaction_nsu` único, `invoice_slug`,
  `receipt_url`, `capture_method`, `paid_amount`, `installments`).
- Baixa (`payment_transaction`): marcar a **origem** (manual ou InfinitePay)
  e ligar ao link de checkout.
- Isolamento por academia em tudo (como no resto do sistema).

## Segurança

- Baixa só depois do `payment_check` confirmar; `order_nsu` aleatório e longo;
  `transaction_nsu` único (sem baixa dobrada).
- Rota de avisos e rota de criar link com limite de requisições (como a
  `/public/pay`).
- A InfiniteTag não é segredo (aparece no checkout). A **chave de API é
  segredo**: guardada criptografada no banco (chave de criptografia em
  variável de ambiente do servidor, fora do banco), nunca devolvida pela API
  do Katsuflow nem escrita em log. Com a chave, só o Katsuflow cria links em
  nome do mestre.
- A conferência (`payment_check`) usa a tag guardada no link (a documentação
  pede `handle`); o construtor confere se ela também aceita a chave.
- Nada de dados do aluno além de nome, telefone e e-mail vai para a
  InfinitePay.

## Testes

- Backend com TDD; a InfinitePay é simulada nos testes (nenhum teste chama a
  API real).
- Casos: criar link (valor, itens, quem paga, reaproveitar link), testar e
  ligar (sucesso, checkout desligado, rede), aviso válido → baixa abatendo do
  mais antigo, aviso repetido, aviso com `payment_check` negativo, aviso de
  `order_nsu` desconhecido, valor já não devido → "a conferir", isolamento
  entre academias, página `/pagar` ligada × desligada.
- Fechamento: um pagamento real de R$ 2,00 em ambiente de produção com a
  conta do Thiago, conferindo a baixa automática na ficha.

## Deixado ao construtor

- Nomes de tabelas, colunas, rotas e componentes; migração.
- Cliente HTTP da InfinitePay (httpx já está no projeto), timeouts.
- Biblioteca e formato da criptografia da chave de API (não há nada de
  criptografia no projeto hoje) e o nome da variável de ambiente.
- Tempo de reaproveitamento de link (o código Pix do checkout vale 72 h).
- Onde configurar a URL pública da rota de avisos (hoje só existe
  `WEB_APP_URL`).
- Textos finais da janela de etapas (base: o guia no Obsidian). Imagens e
  vídeo entram depois, quando o guia com prints de uma conta nova estiver
  pronto.

## Pendências (fora desta versão)

- ⏸ **Validade curta do link (`valid_until`)**: opção avançada da InfinitePay
  (exige a chave de API, que já entra nesta versão). **Pendente** — o Thiago
  não confirmou se entra agora. Falta também testar se o Pix já copiado pelo
  aluno deixa de valer quando o link vence.

- ⏸ Taxa no Pix da InfinitePay: o que fazer se passarem a cobrar — revisar
  depois, nada definido.
- Confirmar com uma conta nova (mestre do beta) se "criar o primeiro
  checkout" e "chave Pix na InfinitePay" são mesmo obrigatórios, e completar
  os prints do guia.
