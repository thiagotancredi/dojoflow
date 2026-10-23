# Página de pagamento Pix — design

Data: 2026-10-22 · Status: revisado; aguardando aprovação do Thiago

## Intenção

Hoje a cobrança pelo WhatsApp leva a **chave Pix escrita no meio do texto**. No
celular, tocar na mensagem copia **o texto inteiro**, e o aluno precisa apagar
tudo em volta para sobrar só a chave. Ele também digita o valor à mão no banco
e pode errar.

A ideia: a mensagem passa a levar um **link curto** para uma página pública do
Katsuflow. Ali o aluno vê o que está em aberto e toca em **"Copiar código Pix"**.
O código é um **Pix copia e cola** com o valor já preenchido: ele cola no app do
banco, confere a tela de confirmação do banco (nome de quem recebe, banco,
valor) e confirma. Não precisa digitar nada.

Inspiração: o cartão "Copiar chave Pix" do WhatsApp (imagem enviada pelo
Thiago). Mandar esse cartão nativo exigiria a API paga do WhatsApp, então ficou
de fora.

## Objetivos

1. A mensagem de cobrança leva um link `WEB_APP_URL/pagar/<código>` no lugar da
   chave Pix.
2. A página pública mostra academia, mestre, total em aberto, a lista do que
   está em aberto, quem recebe (só o nome) e o botão "Copiar código Pix".
3. O código Pix copia e cola é gerado pelo nosso servidor, no padrão do Banco
   Central (BR Code / EMV, Pix estático com valor). O dinheiro vai direto para
   a chave do mestre, e o Katsuflow não toca em dinheiro.
4. Se o aluno não deve nada, a página mostra um estado "Tudo em dia".

## Fora do escopo

- Saber automaticamente que o aluno pagou. Com Pix estático o site não é
  avisado, então o mestre continua dando baixa à mão, como hoje.
- Cartão Pix nativo do WhatsApp ou API oficial do WhatsApp.
- QR Code na página. O aluno abre a página no próprio celular, onde copiar e
  colar é o caminho natural.
- Foto ou logo da academia.

## Anti-objetivos (seria um fracasso mesmo funcionando)

- O aluno ver a **chave Pix** solta e ficar em dúvida sobre o que copiar. Na
  página só existe **um** botão de copiar: o do código.
- Alguém conseguir abrir a página de outro aluno trocando letras no link.
- O código Pix sair com valor ou recebedor errado (o banco recusa ou, pior,
  cobra o valor errado).

## Decisões do Thiago

- **Formato:** link para uma página (não mensagem separada nem cartão do
  WhatsApp). A mensagem continua tendo texto + o link.
- **Layout B** (aprovado no navegador em 22/10):
  1. Faixa escura de ponta a ponta no topo (gradiente `#2a2d33` → `#155e75`,
     cores do tema grafite) com o **nome da academia** e, embaixo, **"Mestre
     <nome>"**. **Sem** selo, iniciais ou imagem da academia.
  2. Cartão branco "flutuando" por cima da faixa: "Olá, <nome> · total em
     aberto", valor grande e um selo "N mensalidades".
  3. Cartão "O que está em aberto": uma linha por cobrança (ex.: "Mensalidade ·
     setembro — R$ 150,00").
  4. Cartão "Pagar para": nome de quem recebe + "Recebe pelo Pix". **Sem
     mostrar a chave.**
  5. Botão grande "Copiar código Pix". Ao tocar, ele vira "Código copiado!" e
     aparece a dica "Agora abra o app do seu banco → Pix → Pix copia e cola".
     Embaixo do botão: "Cole no app do seu banco, em 'Pix copia e cola'. O
     valor de R$ X já vai preenchido."
  6. Rodapé: "Cobrança enviada pelo" + **símbolo do lutador com o nome
     Katsuflow** ao lado, legível.
- **Sem a opção "copiar só a chave"**: só o código (decidido em 22/10).
- **Cores** iguais às do sistema (tema grafite, `frontend/src/styles/theme.css`).
- **Link impossível de adivinhar.** O Thiago sugeriu um hash do ID da academia +
  e-mail do aluno. Ficou um **código aleatório longo guardado no cadastro do
  aluno**, pelos motivos abaixo (nada de login):
  - muitos alunos, principalmente menores, não têm e-mail;
  - um hash feito só com dados conhecidos pode ser recalculado por quem descobrir
    esses dados.
- **Nada pendente:** a página continua com a faixa (academia + mestre) e mostra
  uma mensagem do tipo "Tudo em dia! Nenhuma mensalidade pendente.", sem botão
  de copiar.
- **Tipo da chave Pix discriminado e obrigatório** nas configurações (CPF,
  CNPJ, Celular, E-mail, Aleatória), para o código sair com a chave no formato
  certo. O site nunca adivinha o tipo. Ver "Configurações de cobrança".
- **Academia desativada** (status diferente de ativa no painel admin): por
  enquanto o link mostra "Link inválido" e não gera código Pix.

Protótipo visual: `.superpowers/brainstorm/11366-1792715940/content/pagina-final-b2.html`
(cópia em Obsidian → `Anexos/pagina-pagamento-pix.html`).

## Como funciona

### Link do aluno

- Cada aluno ganha um código aleatório (ex.: `secrets.token_urlsafe(16)`, cerca
  de 22 caracteres), salvo em coluna própria, única e indexada. Todo aluno já
  nasce com o seu, e a migração cria um para cada aluno existente (assim a
  lista de Mensalidades, que é só leitura, nunca precisa gravar nada).
- O link é **fixo por aluno**: serve para todas as cobranças, e a página sempre
  mostra a situação **na hora em que é aberta**. Se o aluno pagar um mês e abrir
  o link de novo, vê só o que ainda falta.
- Código que não existe → página genérica "Link inválido ou expirado", sem
  dizer se o aluno existe.
- O mestre pode **gerar um link novo** para o aluno (o antigo para de
  funcionar), com um botão na ficha do aluno, área de mensalidades.

### O que conta como "em aberto"

O mesmo que a mensagem cobra hoje: as cobranças **vencidas** (`overdue`) do
aluno, com o valor que falta pagar (`open_amount`). Assim o total da página
sempre bate com o da mensagem. Sem cobranças vencidas → "Tudo em dia".

### Código Pix copia e cola (BR Code)

Montado no backend, no padrão EMV do Banco Central para Pix estático:

- chave = `pix_key` das configurações de cobrança;
- nome do recebedor = `recipient_name` (sem ele, nome da academia), em
  maiúsculas, sem acentos, até 25 caracteres;
- cidade = **campo novo** nas configurações de cobrança, em maiúsculas, sem
  acentos, até 15 caracteres;
- valor = total em aberto, com 2 casas decimais;
- identificador da transação = `***`;
- CRC16 no final (CCITT-FALSE), como manda o padrão.

Precisa de testes com códigos de referência conhecidos (exemplos públicos do
manual do BR Code) para garantir que os bancos aceitam.

### Mensagem do WhatsApp

- Marcador novo `{link}` no texto da mensagem. O texto padrão passa a ser:

  ```
  Olá, {nome}! Tudo bem? 🥋

  Passando para lembrar que a mensalidade da {academia} está em aberto:
  {valor} ({meses}).

  Para pagar pelo Pix, é só tocar aqui:
  {link}

  Se já pagou, desconsidere. Obrigado!
  ```

- `{pix}` e `{recebedor}` continuam funcionando para quem usa.
- Nas configurações, a lista de marcadores ganha `{link}` ("link da página de
  pagamento").
- O texto padrão existe em **dois lugares**: `DEFAULT_MESSAGE_TEMPLATE` em
  `src/dojoflow/services/billing.py` e a cópia em
  `frontend/src/features/settings/components/BillingSettingsSection.tsx`. Os
  dois mudam juntos. Texto salvo igual ao padrão fica gravado como nulo, então
  essas academias passam para o padrão novo sozinhas.

### Configurações de cobrança

- Campo novo **Tipo da chave**: CPF, CNPJ, Celular, E-mail ou Aleatória
  (coluna nova + migração). Ao salvar, a chave é conferida contra o tipo e
  guardada no formato do BR Code:
  - CPF: 11 dígitos, só números (dígitos verificadores válidos);
  - CNPJ: 14 dígitos, só números (dígitos verificadores válidos);
  - Celular: `+55` + DDD + número (aceita digitar com ou sem `+55`, espaços,
    parênteses e traços);
  - E-mail: minúsculas;
  - Aleatória: UUID.
- **O tipo é obrigatório** (decisão do Thiago, 22/10): não dá para salvar uma
  chave Pix sem escolher o tipo, e o site **nunca adivinha** o tipo.
- **Chaves já salvas** (sem tipo): a migração **não** preenche o tipo. Elas
  ficam sem tipo até o mestre escolher, e as configurações mostram um aviso
  pedindo para completar. Enquanto isso, a página do aluno mostra "Fale com a
  academia para pagar".
- Campo novo **Cidade** (de quem recebe o Pix).
- Sem chave, sem tipo ou sem cidade, o código não pode ser gerado. Nesse caso a
  página mostra o total e a lista e, no lugar do botão, "Fale com a academia
  para pagar", e as configurações avisam o mestre do que falta preencher.

### Página pública

- Rota do frontend `/pagar/:codigo`, fora do `RequireAuth` e do `AppLayout`
  (sem barra lateral), pensada para celular.
- Endpoint público no backend (ex.: `GET /public/pay/{codigo}`) que devolve só o
  necessário para a página: academia, mestre, primeiro nome de quem recebe a
  mensagem, itens em aberto, total, nome de quem recebe o Pix e o código
  copia e cola. **Nada de telefone, e-mail, CPF ou dados de outros alunos.**
- Sempre no tema grafite claro, independente da preferência salva no navegador.

## Restrições

- Backend: FastAPI + SQLAlchemy async, migração Alembic para as colunas novas
  (código do link no aluno, cidade nas configurações).
- O endpoint público não pode vazar se um código existe ou não, além de
  "funciona / não funciona". Limitar tentativas por IP é desejável.
- Frontend: React + Vite + Tailwind, componentes e tokens existentes.

## Decisões minhas (Claude) para conferir

- Página **sem QR Code** (só copiar e colar).
- Link **fixo por aluno**, criado junto com o aluno (e pela migração para os
  que já existem), com botão "gerar link novo" na ficha.
- "Em aberto" = só cobranças **vencidas**, igual à mensagem.
- Saudação: "Olá, <primeiro nome de quem recebe a mensagem>". Quando é o
  responsável, as linhas dizem de quem é a mensalidade (ex.: "Mensalidade de
  Ana · setembro").
- Mestre exibido = o mestre dono da conta da academia (o primeiro cadastrado).
- Quem tem texto personalizado **sem** `{link}`: o link é adicionado numa linha
  no final ("Para pagar pelo Pix, toque aqui: <link>"), para ninguém ficar sem
  ele.
- Campo **Cidade** obrigatório para gerar o código.
- Limite de tentativas no endpoint público guardado na memória de cada processo
  (são 2 workers do uvicorn), o que basta para frear quem tenta adivinhar.

## Fica com quem for construir

- Nomes de tabelas, colunas, endpoints e componentes.
- Texto exato das mensagens de erro e do estado "Tudo em dia".
- Como recortar o símbolo do lutador para o rodapé (arquivo novo em
  `src/assets/brand/` ou recorte via CSS).
