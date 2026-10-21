# Painel administrativo (admin.katsuflow.com.br)

Data: 2026-10-21 · Branch: `feat/admin-panel` (criada a partir da
`feat/deploy`, porque as duas mexem no `deploy/Caddyfile`).

## Por quê

O Katsuflow vai para produção com o cadastro público **fechado**. O fluxo
comercial da primeira versão é manual: o mestre chega pelo WhatsApp, paga, e o
Thiago cria a conta e manda o acesso por WhatsApp. Para isso o Thiago precisa
de uma área só dele para **criar e cuidar das academias**, e de um jeito de
**entrar numa academia** para conferir que tudo funciona, principalmente na
fase de implantação de cada cliente (achar bugs, deixar a academia pronta).

Prioridade: **simples e rápido**, para não atrasar a subida. Mesmo visual do
app atual.

## Objetivos

### Parte 1 — painel

1. **Endereço próprio:** `admin.katsuflow.com.br` (subdomínio, decisão do
   Thiago; não é uma rota `/admin` do site principal).
2. **Só o Thiago entra:** o e-mail `thiagotancredii@gmail.com`, definido na
   configuração do servidor (`ADMIN_EMAIL`), nunca por tela nem pelo banco.
   Qualquer outro login no painel vê "sem acesso".
3. **Lista de academias:** academia, mestre, e-mail, telefone, situação
   (ativa/desativada) e data de criação, com busca por nome (academia ou
   mestre).
4. **Criar academia:** nome da academia, nome do mestre, e-mail, telefone
   (opcional). O sistema **gera a senha inicial**. Ao salvar, o painel mostra
   uma **mensagem pronta para o WhatsApp** com botão de copiar, por exemplo:
   "Seu acesso ao Katsuflow: https://katsuflow.com.br · E-mail: … · Senha: …".
5. **Editar:** nome da academia, nome do mestre, e-mail, telefone.
6. **Trocar senha do mestre:** o sistema gera uma senha nova, mostra a mesma
   mensagem pronta para copiar e **derruba as sessões abertas** do mestre.
7. **Ativar / desativar academia:**
   - Academia desativada **não faz login** (mensagem: "Academia desativada.
     Fale com o suporte.").
   - Quem já estiver logado **cai na próxima ação**: a renovação da sessão e
     toda chamada autenticada são recusadas, e as sessões abertas são
     revogadas no momento da desativação.
   - Ativar devolve o acesso normal.
   - O painel **não deixa desativar a academia do próprio Thiago** (para não
     se trancar fora).
   - O bot do Telegram já respeita o bloqueio; nada muda nele (está
     congelado).

### Parte 2 — entrar na academia (modo suporte)

1. Na lista, cada academia tem o botão **"Entrar"**. Ele abre uma **aba nova
   em `katsuflow.com.br`**, logada **como o Thiago** (não como o mestre), vendo
   e mexendo nos **dados daquela academia** com o mesmo poder do mestre:
   alunos, faixas, mensalidades, configurações, dashboard.
2. **Faixa fixa no topo** de todas as telas: "Modo suporte: *Nome da
   academia* · Sair". **Sair** encerra a sessão de suporte e fecha a aba.
3. No modo suporte **somem as telas de conta pessoal** (trocar senha, conectar
   Telegram, definir acesso), para não mexer na conta do Thiago achando que é
   a do mestre.
4. A sessão de suporte dura **até o Sair ou no máximo 8 horas**, o que vier
   primeiro (não renova além disso).
5. **Pode entrar em academia desativada** (para deixar tudo pronto antes de
   ativar e mandar o acesso).
6. O mestre **não vê** que o Thiago entrou; o que o Thiago alterar aparece
   como alteração normal da academia.
7. **Cada entrada fica registrada** na tabela `audit_log` (quem, quando, qual
   academia). Hoje a tabela existe e não é usada.
8. A passagem do painel para o site usa um **código de uso único** de vida
   curta (ex.: 60 s), para que o link não possa ser reaproveitado.

## Fora do escopo

- Cadastro público (`/cadastro`): continua fechado; academias nascem só pelo
  painel.
- Mais de um administrador, papéis, permissões finas.
- Excluir academia.
- Tela para ver o registro de entradas (fica só no banco por enquanto).
- Editar configurações de cobrança, modalidades etc. pelo painel (isso se faz
  entrando na academia).
- Mudanças no bot do Telegram.

## Anti-objetivos (seria falha mesmo funcionando)

- Qualquer pessoa além do Thiago conseguir abrir o painel ou chamar a API do
  painel.
- Uma sessão de suporte que **mexe na conta pessoal do Thiago** sem ele
  perceber, ou que **vaza para outra academia**.
- Academia desativada que continua usando o sistema.
- Um link de "Entrar" que funciona de novo se for copiado ou reaberto.
- Atrasar o deploy com algo além do descrito aqui.

## Como o sistema funciona hoje (base para o desenho)

- **Academia:** só `name` e `status` (`active` / `blocked`). O "desativada" do
  painel é o `blocked` que já existe.
- **Mestre:** `name`, `email` (único), `phone`, `password_hash`, `academy_id`.
- **Login:** `AuthService.login` **não confere a situação da academia** —
  por isso hoje a academia bloqueada entra no site. O mesmo vale para o
  `refresh` e para `_get_current_master` (`api/dependencies/auth.py`).
- **Sessões:** token de acesso curto (30 min, em memória no site) + cookie de
  refresh (14 dias) guardado na tabela `refresh_session`, com rotação.
- **Um ponto só decide a academia de cada pedido:** `_get_current_master`
  devolve um `MasterContextRead`, e as rotas usam `current_master.academy_id`
  (53 usos) — só 2 usam `master_id`. É aqui que o modo suporte troca a
  academia, sem mexer nas rotas nem nas regras.
- **Código de uso único:** tabela `one_time_token` (`master_id`, `token`,
  `purpose`, `expires_at`, `used_at`), já usada pelo "definir acesso".
- **Site:** React + Vite, um único app servido pelo Caddy; chama a API na
  mesma origem (`/api`).

## Decisões de como fazer (do Claude; o Thiago pode mudar)

- **Um app só para os dois endereços.** O mesmo build do site, ao abrir em
  `admin.*`, monta só as rotas e o layout do painel (login, lista, criar,
  editar). Reaproveita componentes e visual. Em desenvolvimento, o painel
  abre em `admin.localhost:5173`.
- **Login do painel separado do site principal:** o cookie de refresh é por
  endereço, então entrar no `admin.` não loga em `katsuflow.com.br` e
  vice-versa. Usa o mesmo `/auth/login`; depois do login o painel confere se
  o usuário é o administrador.
- **Quem é administrador:** o mestre cujo e-mail é igual a `ADMIN_EMAIL`
  (configuração). Vazio = nenhum administrador. O Thiago tem uma academia
  própria normal (ex.: "Katsuflow"), criada na subida.
- **API do painel em `/api/v1/admin/...`**, toda protegida por "é o
  administrador". Defesa extra no Caddy: no endereço principal,
  `/api/v1/admin/*` responde 404; só o `admin.` repassa.
- **Cadastro público fechado no Caddy:** `/api/v1/auth/register` responde 404
  nos dois endereços.
- **Sessão de suporte:** é uma sessão de refresh comum do Thiago marcada com a
  **academia vista** e um **prazo máximo de 8 h**. Os tokens de acesso gerados
  a partir dela carregam essa academia. `_get_current_master` só aceita a
  troca se o dono do token ainda for o administrador; aí devolve o contexto com
  a academia vista e um sinal de "modo suporte" (que o `/auth/me` também
  devolve, para o site mostrar a faixa e esconder as telas de conta).
- **Entrada:** o painel pede um código de uso único (`one_time_token`, com a
  academia guardada junto) e abre `https://katsuflow.com.br/suporte#<código>`.
  O site troca o código por uma sessão de suporte (cookie de refresh no
  endereço principal + token de acesso). Código vencido ou já usado = erro.
- **Bloqueio de verdade:** login, refresh e `_get_current_master` recusam
  academia `blocked` (exceto sessão de suporte). Desativar revoga as sessões
  de refresh dos mestres da academia. Código de erro próprio
  (ex.: `ACADEMY_BLOCKED`) para o site mostrar a mensagem certa.
- **Criação da academia do Thiago na subida:** um comando de linha
  (`python -m dojoflow.commands.create_academy`) que cria academia + mestre e
  imprime a senha gerada; roda uma vez no servidor.
- **Deploy:** novo bloco `admin.{$DOMAIN}` no `deploy/Caddyfile` (mesmo site,
  mesmo `/api`); `ADMIN_EMAIL` no `deploy/env.prod.example`; registro DNS A
  `admin` → `192.102.140.188` (já criado pelo Thiago em 21/10).

### Decisões da releitura (Claude, 21/10)

- **Bloqueio no backend, não só na tela:** em modo suporte, as rotas de conta
  pessoal (trocar senha, ligar Telegram, definir acesso) **recusam** o pedido
  (403), além de sumirem do site. São justamente os 2 usos de `master_id`.
- **O Thiago não edita o próprio e-mail pelo painel** (trocar o e-mail do
  administrador o trancaria fora). Os outros dados dele podem ser editados.
- **Um mestre por academia** na V1 (é o que o painel cria). A lista mostra o
  primeiro mestre da academia.
- **E-mail obrigatório e único** ao criar e editar; e-mail repetido mostra
  erro no campo.
- A **academia do Thiago aparece na lista** como as outras, com "Entrar"
  funcionando; só o "Desativar" fica travado nela.
- **Sair do modo suporte** revoga aquela sessão de suporte (como um logout).
- **Limitação aceita:** no navegador do Thiago, a sessão de suporte substitui o
  login que ele tiver em `katsuflow.com.br` (o cookie é o mesmo endereço). O
  painel `admin.` não é afetado.

## Deixado para quem constrói

- Formato exato das telas do painel, dentro do visual atual (lista em tabela
  no computador e cartões no celular, por exemplo).
- Geração da senha (tamanho, caracteres legíveis), texto exato da mensagem do
  WhatsApp.
- Como guardar a academia vista na sessão de refresh e no código de uso único
  (colunas novas, migração).
- Valor novo no `AuditAction` (ou reaproveitar um existente) para a entrada em
  modo suporte.
- Como a aba de suporte se comporta ao vencer as 8 h (voltar para uma tela
  "sessão de suporte encerrada").
- Testes: isolamento (suporte só vê a academia escolhida; não-admin recebe
  403/404 em toda rota do painel), bloqueio (login, refresh e chamadas), código
  de uso único (vencido, reutilizado), não desativar a própria academia.
