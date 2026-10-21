# Mensalidades: cobranças, baixa manual e cobrança por WhatsApp

Data: 2026-10-21 · Protótipos aprovados:
`.superpowers/brainstorm/217162-1792553058/content/mensalidades-baixa.html` e
`mensalidades-cobranca.html` (cópias em `Anexos/` no Obsidian).

## Intenção

Mensalidades são o núcleo do produto: hoje o mestre controla quem pagou em
caderno ou planilha. O DojoFlow passa a **gerar as cobranças**, deixar o mestre
**dar baixa** nos pagamentos (feitos por fora — Pix, dinheiro, etc.), mostrar
**quem está devendo** e **cobrar pelo WhatsApp** com um clique. É a prioridade
urgente do Thiago (21/10).

**Sucesso:** o mestre abre o site, vê quem está atrasado, manda a cobrança pelo
WhatsApp em um clique e, quando o aluno paga, dá baixa (total ou parcial) e o
histórico fica certo — inclusive para alunos que já chegaram devendo.

## Decisões do Thiago

1. **Cobranças geradas automaticamente no dia 1** de cada mês, uma por matrícula.
2. **"Atrasada" é calculada pela data** (vencimento passou e não foi quitada);
   não é gravada.
3. **Pagamento abate do mais antigo para o mais novo.**
4. **Matrícula exige valor da mensalidade e dia de vencimento, ou "isenta"** —
   não existe mais matrícula sem valor. Vale no cadastro e na edição, no **site e
   no bot**.
5. **Baixa manual, só no site:** sem integração financeira. O mestre informa o
   **valor** (total ou parcial) e a **data** do pagamento. Parcial fica como saldo
   em aberto daquele mês. O **histórico** mostra cada pagamento e o que ele
   quitou (ex.: R$ 50 em janeiro → janeiro; R$ 150 em fevereiro → R$ 50 do resto
   de janeiro + R$ 100 de fevereiro).
6. **Telegram fora:** o bot continua só com cadastro de aluno (o fluxo do bot será
   revisto depois; talvez ele seja desativado). Nada de mensalidade no bot.
7. **Taxa de matrícula separada da mensalidade:** ao matricular, cobra-se a taxa
   (valor **digitado na hora da matrícula**); o mestre pode isentá-la. A
   **mensalidade começa no mês seguinte**, no dia combinado. Ex.: matrícula em
   20/10 com vencimento dia 10 → taxa em 20/10, 1ª mensalidade em 10/11 (não existe
   10/10).
8. **Lançar dívidas de meses anteriores:** a academia não nasce junto com o
   sistema; o mestre precisa lançar mensalidades antigas de quem já chega devendo.
9. **Link de WhatsApp** para inadimplentes, com **texto padrão de cobrança**.
10. **Configuração de cobrança** (Pix, dados bancários). Maquininha: bem depois.

## Objetivos

1. Cobranças (taxa de matrícula e mensalidades) criadas e calculadas pelo backend.
2. Aba **Mensalidades** na ficha do aluno: em aberto, mês a mês, histórico,
   Dar baixa, WhatsApp, Isentar, Lançar mês anterior.
3. Página **Mensalidades** no menu: números do mês e lista de quem deve / vai
   vencer / pagou, com WhatsApp e Dar baixa por aluno.
4. **Configurações → Cobrança:** chave Pix, recebedor, dados bancários e texto da
   mensagem.
5. Cadastro/edição de matrícula com valor obrigatório (ou isenta) e taxa de
   matrícula, no site e no bot.
6. Dashboard: blocos "inadimplentes" e "vencem em 7 dias" com dados reais.

## Fora do escopo

- Integração financeira (Pix automático, boleto, maquininha, conciliação).
- Mensalidades no bot do Telegram.
- Avisos automáticos (o modelo `Notification` existe, mas não entra agora).
- *Minha escolha:* multa/juros por atraso, desconto, adiantamento (pagar mais que
  o devido), recibo em PDF e relatórios — não foram pedidos.

## Anti-objetivos

- Histórico que não bate: a soma das baixas tem que explicar exatamente o que foi
  quitado em cada cobrança.
- Cobrança duplicada do mesmo mês para a mesma matrícula.
- Mensalidade "nascendo atrasada" (vencimento no passado ao ser criada
  automaticamente).
- Mandar WhatsApp para quem não deve.

## Regras do domínio

### Cobranças (`Payment`)

- Dois tipos (*minha escolha de nome:* `kind`): **`monthly`** (mensalidade) e
  **`enrollment_fee`** (taxa de matrícula).
- Situação gravada: `pending` | `partial` | `paid` | `waived` (isenta).
  `overdue` é **calculado** (`due_date < hoje` e não `paid`/`waived`).
  `pending_configuration` deixa de ser usado.
- **Taxa de matrícula:** criada no momento da matrícula, vence na data da
  matrícula, valor digitado; "isentar taxa" cria a cobrança já `waived` (fica no
  histórico) — *minha escolha*; valor 0 equivale a isentar. Uma por matrícula; se
  o aluno entra em duas modalidades no mesmo cadastro, cada matrícula tem a sua
  (*minha escolha*).
- **Mensalidade:** uma por matrícula × mês de referência (constraint única já
  existe: academia + matrícula + mês; precisa incluir `kind` ou a taxa usar outro
  campo — decisão do construtor). Valor = `monthly_fee` da matrícula no momento
  em que a cobrança é criada; vencimento = `due_day` daquele mês.
- **Primeira mensalidade:** mês seguinte ao da matrícula (*minha leitura da
  decisão 7, também para matrícula antes do dia de vencimento: matrícula em 05/10
  com vencimento dia 10 → 1ª mensalidade em 10/11*).
- **Geração automática:** no dia 1, para cada matrícula **ativa, não isenta, com
  valor e dia** cujo início de cobrança já chegou, cria a mensalidade do mês se não
  existir. Tem que ser **idempotente** (rodar duas vezes não duplica).
  *Minha escolha:* além do disparo diário, a mesma rotina roda "sob demanda"
  antes de mostrar mensalidades (ficha, página, dashboard), para o sistema
  funcionar mesmo se o disparo diário falhar. Como agendar no servidor fica para o
  construtor (a produção está sendo remontada na StayCloud).
- **Alunos que já existem quando a funcionalidade entra:** mensalidades
  automáticas a partir do **primeiro vencimento igual ou posterior ao dia em que o
  recurso é ligado** (*minha escolha*, para nenhuma nascer atrasada: ligado em
  21/10, vencimento dia 10 → primeira automática em 10/11; outubro, se devido,
  entra pelo "Lançar mês anterior"); nada retroativo automático. Dívidas anteriores entram pelo "Lançar mês anterior". Não se cobra
  taxa de matrícula de matrículas antigas.
- **Lançar mês anterior:** na aba Mensalidades do aluno, escolhe a matrícula, o
  mês de referência (anterior ao primeiro gerado), valor (padrão: mensalidade
  atual) e vencimento (padrão: dia de vencimento daquele mês). Não deixa lançar um
  mês que já tem cobrança daquela matrícula.
- **Isentar este mês:** marca a cobrança como `waived` (só se não tiver baixa
  alocada); dá para desfazer.
- *Minha escolha:* mudar o valor/dia da matrícula vale para as cobranças criadas
  **depois**; as já criadas mantêm o valor. O mestre pode **editar valor e
  vencimento de uma cobrança sem baixa**.
- **Matrícula inativada:** para de gerar cobranças; as em aberto continuam
  devidas. Reativada: volta a gerar a partir do mês seguinte (*minha escolha*).
- **Matrícula isenta:** não gera mensalidades.

### Baixa (`PaymentTransaction` + `PaymentAllocation`)

- **Por aluno**, não por mês: valor recebido + data do pagamento (obrigatórios);
  forma (dinheiro, Pix, cartão crédito/débito, transferência, outro) e observação
  opcionais. Taxa e valor líquido do modelo não são usados agora.
- O sistema distribui o valor pelas cobranças em aberto do aluno, **da mais antiga
  para a mais nova** (ordem: vencimento, depois criação), atravessando matrículas
  e incluindo a taxa de matrícula. Cada pedaço vira uma `PaymentAllocation`.
- A janela mostra **antes de confirmar** como vai abater.
- **Valor maior que o total em aberto:** recusado, com aviso do máximo
  (*minha escolha*; sem crédito/adiantamento por enquanto).
- **Excluir baixa:** desfaz as alocações; as cobranças voltam ao saldo anterior.
- Cobrança fica `paid` quando o alocado = valor; `partial` quando 0 < alocado <
  valor.

### WhatsApp

- Botão **WhatsApp** em quem tem valor em atraso (página Mensalidades e ficha).
- Abre `https://wa.me/55<telefone>?text=<mensagem>` em nova aba (sem API).
- **Destinatário** (*minha escolha*): o telefone do aluno; se o aluno for **menor
  de 18** (pela data de nascimento) e tiver responsável com telefone, o do
  responsável. Sem telefone: botão desabilitado com dica.
- **Mensagem padrão** editável em Configurações → Cobrança, com marcadores
  `{nome}`, `{academia}`, `{valor}` (total em atraso), `{meses}` (ex.: "janeiro e
  fevereiro"), `{pix}`, `{recebedor}`. Texto inicial (do protótipo):
  "Olá, {nome}! Tudo bem? 🥋 Passando para lembrar que a mensalidade da
  {academia} está em aberto: {valor} ({meses}). Você pode pagar pelo Pix: {pix}
  ({recebedor}). Se já pagou, desconsidere. Obrigado!"

### Configurações → Cobrança

- Por academia: chave Pix, nome de quem recebe, dados bancários (texto livre,
  opcional), texto da mensagem de cobrança. Sem maquininha.

## Telas

### Ficha do aluno → aba nova "Mensalidades" (`mensalidades-baixa.html`)

- Topo: **total em aberto** (com os meses) + botões **WhatsApp** e **Dar baixa**.
- Lista mês a mês (mais novo em cima): mês, modalidade (ou "Taxa de matrícula"),
  vencimento, valor, pago, situação (Paga / Parcial · falta R$ X / Atrasada /
  A vencer / Isenta). Ações por linha: Isentar/Desfazer, Editar (sem baixa).
- **Histórico de pagamentos:** valor, data, forma e para onde foi
  ("→ janeiro R$ 50"); excluir baixa.
- **Lançar mês anterior** (regra acima).

### Página "Mensalidades" no menu (`mensalidades-cobranca.html`)

- Seletor de mês; números: **previsto no mês**, **recebido no mês**, **em atraso**
  (todos os meses, com nº de alunos), **vencem em 7 dias**.
- Filtros: Atrasadas (todos os meses) / A vencer / Pagas / Todas + busca.
- Linha por aluno: nome (e responsável, se a cobrança vai para ele), modalidades,
  em aberto, dias de atraso (da cobrança mais antiga), **WhatsApp**, **Dar baixa**
  (mesma janela da ficha).

### Configurações → seção "Cobrança"

Campos da regra acima, com os marcadores clicáveis/listados sob o texto.

### Cadastro e edição de matrícula (site: cadastro em 4 etapas, "Nova matrícula", editar)

- Mensalidade (> R$ 0) e dia de vencimento obrigatórios, a menos que "Isenta"
  (*minha escolha:* mensalidade R$ 0 sem marcar isenta é recusada).
- Na **criação**: campo **Taxa de matrícula** (R$) + "Isentar taxa".
- Matrículas antigas sem valor: continuam existindo até serem editadas (a edição
  exige completar); não geram cobrança; aparecem no dashboard como pendência de
  cadastro (como hoje).

### Bot do Telegram (cadastro de aluno)

- Ao criar matrícula, exigir valor + dia ou "isenta" (hoje permite pular).
- *Minha escolha:* perguntar a taxa de matrícula ("valor ou 0 para isentar").

### Dashboard

- "Inadimplentes" e "vencem em 7 dias" passam a usar os dados reais.

## Restrições

- Toda regra nos *services* do backend (site e bot chamam o mesmo código).
- Dinheiro em `Decimal` (2 casas); datas sem fuso (data local da academia).
- Multi-tenant: tudo filtrado por `academy_id` do token; ids públicos (UUID) na API.
- Frontend no tema grafite + petróleo, tokens de `theme.css`, claro e escuro.
- Sem testes automáticos de frontend (decisão da V1); backend com testes.

## Deixado para o construtor

- Nomes de rotas, schemas e tabelas novas (configuração de cobrança), migrações.
- Como gravar o "início da cobrança" de cada matrícula (campo novo ou derivado).
- Como agendar o disparo do dia 1 no servidor.
- Paginação e ordenação da página Mensalidades.
- Formatação de `{meses}` e de valores na mensagem.
