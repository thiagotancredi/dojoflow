# Faixas e listas de graduação — design

Data: 2026-10-20 · Status: aprovado pelo Thiago em 20/10 (cores do taekwondo, criação de faixa e lista; tempos mínimos = sugestão editável)

## Intenção

Um mestre pediu uma forma de saber **quais alunos estão aptos a graduar** numa
modalidade. Ex.: aluno na faixa amarela de taekwondo há 3 meses, quando o tempo
mínimo da amarela é 3 meses → apto por tempo.

O "apto" é **só um aviso**: o aluno pode dominar as técnicas antes do tempo, e a
decisão é sempre do mestre. A lista de graduação é uma **conferência/registro**
("Alunos aptos a graduar em Novembro/2026"), não um processo automático.

## Objetivos

1. A academia cadastra as **faixas** de cada modalidade que oferece, em ordem.
2. Cada matrícula (aluno × modalidade) tem um **histórico de faixas** com datas,
   de onde saem a faixa atual e o tempo nela.
3. O mestre cria **listas de graduação** por modalidade, vê todos os alunos com o
   aviso de apto/não apto e adiciona quem quiser, indicando a faixa pretendida.
4. As faixas são **desenhadas pelo sistema** a partir das cores (sem upload de
   imagem).
5. Entram no catálogo global: **Musculação** e **Crossfit**.

## Fora do escopo (agora)

- Promover alunos automaticamente a partir da lista (a faixa é atualizada à mão
  na ficha; alunos podem pular faixa). A "faixa pretendida" guardada na lista
  deixa a porta aberta para um futuro "aplicar graduação".
- Upload de imagem da faixa (o desenho por cores substitui).
- Qualquer mudança no bot do Telegram.
- Agendamento de exames, notas, cobrança de taxa de exame.
- Cordões de capoeira. Se vier: campo "formato" (`faixa` | `cordão`) e um desenho
  de corda trançada usando cor principal + cor da listra como as duas cores e a
  cor da ponta nas pontas (terceira cor opcional, se algum grupo precisar).
  Sem sequência padrão (cada grupo tem a sua). Histórico e listas não mudam.
- Trilhas separadas na mesma modalidade (ex.: jiu-jitsu infantil × adulto). Hoje
  é uma sequência por modalidade (a necessidade atual é taekwondo). Se vier:
  criar "trilha", migrar as faixas existentes para uma trilha "Principal";
  histórico e listas não mudam, pois apontam para a faixa.

## Anti-objetivos (seria um fracasso mesmo funcionando)

- O sistema impedir o mestre de adicionar um aluno "não apto".
- A lista mudar sozinha depois de criada (ex.: quando o aluno troca de faixa, a
  lista antiga passar a mostrar a faixa nova).
- Exigir data exata que o mestre não sabe: a data é obrigatória, mas sempre
  editável.

## Domínio

### Catálogo
Migração de dados adiciona **Musculação** e **Crossfit** ao catálogo global
(emojis: 🏋️ e 💪 — escolha minha). Faixas são opcionais: modalidades sem faixas
simplesmente não aparecem na criação de listas de graduação.

### Faixa (`belt`) — por academia e modalidade
| Campo | Regra |
|---|---|
| nome | obrigatório, único dentro de (academia, modalidade). Ex.: "Preta 2º Dan" |
| cor principal | obrigatória (hex) |
| cor da listra | opcional (hex); vazia = faixa lisa |
| graus/dan (marcas) | inteiro 0–10, padrão 0 |
| cor das marcas | hex, padrão dourado (`#d4a017`, o do taekwondo) |
| cor da ponta | opcional (hex); vazia = marcas direto na faixa. Ex.: jiu-jitsu usa ponta preta + marcas brancas |
| tempo mínimo | opcional: número > 0 + unidade (`days` / `months` / `years`). Vazio = sem aviso de apto (ex.: última faixa) |
| posição | ordem na sequência (1 = menor). Cadastro pede da menor para a maior; dá para reordenar |

- Graus e dans são **faixas próprias** na sequência (ex.: "Azul 2 graus",
  "Preta 1º Dan"), cada uma com seu tempo mínimo.
- Uma sequência por (academia, modalidade).
- Excluir uma faixa que já aparece em algum histórico ou lista: **bloqueado**
  (409) com mensagem clara; renomear/editar é permitido. (escolha minha)
- Remover a modalidade da academia não apaga as faixas (voltam se ela for
  adicionada de novo).

### Sequência padrão do Taekwondo
Quando a academia abre as Faixas do Taekwondo e não tem nenhuma cadastrada, a
tela oferece **"Usar a sequência padrão do Taekwondo"**, que cria as 19 faixas
abaixo (depois tudo é editável). O modelo fica no código do backend (não é
tabela). Tempos: sugestão minha, a confirmar com o Thiago (dans seguem a regra
do Kukkiwon).

| # | Faixa | Principal | Listra | Marcas (douradas, sem ponta) | Tempo mínimo |
|---|---|---|---|---|---|
| 1 | Branca | branca | — | 0 | 3 meses |
| 2 | Cinza | cinza | — | 0 | 3 meses |
| 3 | Amarela | amarela | — | 0 | 3 meses |
| 4 | Laranja | laranja | — | 0 | 3 meses |
| 5 | Verde | verde | — | 0 | 3 meses |
| 6 | Verde e azul | verde | azul | 0 | 3 meses |
| 7 | Azul | azul | — | 0 | 3 meses |
| 8 | Azul e vermelha | azul | vermelha | 0 | 3 meses |
| 9 | Vermelha | vermelha | — | 0 | 3 meses |
| 10 | Vermelha e preta | vermelha | preta | 0 | 6 meses |
| 11–19 | Preta 1º a 9º Dan | preta | — | 1 a 9 | 1, 2, 3, 4, 5, 6, 8, 9 anos; 9º Dan sem tempo |

### Histórico de faixas da matrícula (`enrollment_belt`)
| Campo | Regra |
|---|---|
| matrícula | obrigatória |
| faixa | obrigatória, da mesma modalidade da matrícula |
| data da graduação | obrigatória, editável; padrão hoje na tela |

- **Faixa atual** = registro com a data mais recente (empate: o criado por último).
- **Tempo na faixa** = hoje − data da faixa atual (na ficha). Nas listas de
  graduação, o tempo mostrado é o que o aluno **terá na data do exame**.
- Registros podem ser editados (faixa e data) e excluídos.
- Alunos antigos: o mestre lança o primeiro registro (faixa atual + data
  aproximada), pela ficha ou de uma vez na tela **Lançar faixas** (tela 2b).
- Aluno novo / matrícula nova: a faixa atual pode vir já no cadastro (tela 2a).

### Apto por tempo — na **data do exame**
O critério é o dia do exame, não hoje (pedido do Thiago: quem tem 2 meses hoje e
precisa de 3 está apto se o exame for daqui a 1 mês).
`apto = data_da_faixa_atual + tempo_mínimo_da_faixa_atual <= data_do_exame` (faixa
sem tempo mínimo → sem aviso), com meses e
anos somados pelo calendário (ex.: 15/01 + 1 mês = 15/02). Sem faixa registrada
→ situação "Sem faixa registrada" (não apto), mas pode ser adicionado.

### Lista de graduação (`graduation_list`)
- Campos: nome (obrigatório), modalidade, **data do exame** (obrigatória) e data
  de criação. Pode renomear, mudar a data do exame (os avisos são recalculados) e
  excluir.
- Itens (`graduation_list_entry`): matrícula + **faixa pretendida** (padrão: a
  próxima da sequência; o mestre pode escolher qualquer outra, inclusive pular).
- Cada item guarda um **retrato** do momento em que foi adicionado: faixa atual e
  data dela. A lista não muda quando o aluno gradua depois. (escolha minha, para
  cumprir o anti-objetivo)
- Um aluno aparece no máximo uma vez por lista. Item pode ser removido.
- Candidatos = matrículas **ativas** da modalidade. (escolha minha)

Todas as tabelas levam `academy_id` e todas as consultas filtram pela academia
do mestre logado, como o resto do backend.

## Telas

### 1. Configurações → Modalidades → Faixas
- Cada card em "Oferecidas pela academia" ganha o botão **Faixas**, que abre
  `/app/configuracoes/modalidades/:modalityId/faixas`.
- Lista em ordem: posição, desenho, nome, tempo mínimo, Editar. Botões para subir
  e descer (reordenar). Botão **Nova faixa** (entra no fim da sequência).
- Formulário da faixa: nome, cor principal (paleta: branca, amarela, laranja,
  verde, azul, roxa, marrom, preta, vermelha, cinza + "outra cor"), cor da listra
  (opcional, mesma paleta), cor das marcas (paleta + dourado), cor da ponta
  (opcional), graus/dan (0–10), tempo mínimo (número + dias/meses/
  anos) e **prévia ao vivo** do desenho.
- Texto de ajuda: "Cadastre da menor para a maior. Graus e dans são faixas
  próprias (ex.: Preta 1º Dan)."

### 2. Ficha do aluno → matrícula
- Cada matrícula de modalidade com faixas mostra: desenho da faixa atual, nome,
  "há 3 meses e 12 dias" e o aviso apto/não apto.
- **Registrar graduação**: escolhe a faixa + data (padrão hoje).
- **Histórico**: lista (data, faixa) com editar e excluir.
- Depende da ficha do aluno usar dados reais (Fases 7–8 do Plano B, ainda com
  dados fictícios).

### 2a. Cadastro de aluno e nova matrícula (aprovado no protótipo de fluxo, 20/10)
- Logo depois da modalidade, se ela tiver faixas, aparece o bloco **Faixa atual
  (opcional)**: seletor com os desenhos das faixas + **Desde** (data).
- Padrão: a primeira faixa da sequência (Branca) e a data de hoje. Aluno vindo de
  outra academia: escolhe a faixa e uma data aproximada.
- Grava a matrícula e o primeiro registro do histórico juntos (tudo ou nada).
- Modalidade sem faixas: o bloco não aparece.

### 2b. Lançar faixas dos alunos antigos (aprovado no protótipo de fluxo, 20/10)
- Para o primeiro dia: a academia já tem muitos alunos sem faixa registrada.
- Na tela de Faixas da modalidade, um aviso "N alunos de <modalidade> estão sem
  faixa registrada" com o botão **Lançar faixas de todos**.
- Tela em tabela: aluno, faixa atual (seletor), desde (data). O mestre preenche só
  os que souber e salva tudo de uma vez; quem ficou em branco continua pendente.
- Lista só matrículas **ativas** da modalidade sem nenhum registro de faixa.

### 3. Graduações (item novo no menu)
- `/app/graduacoes`: listas criadas (nome, modalidade, data, nº de alunos).
- **Nova lista**: nome + modalidade (só oferecidas e com faixas) + data do exame.
- `/app/graduacoes/:listId`: alunos da lista (nome, faixa atual do retrato, tempo,
  situação, faixa pretendida, remover) e a seção **Adicionar alunos** com todos os
  candidatos.
- **Visual limpo** (pedido do Thiago): só o **desenho** da faixa, sem o nome ao
  lado (nome no tooltip/ao tocar); tempo curto ("3m 12d"); situação discreta —
  ponto verde + "Apto" quando apto, ponto âmbar + "Ainda não" (texto discreto)
  quando não; sem faixa registrada: ponto cinza + "Sem faixa"; faixa pretendida também como desenho (seletor ao
  clicar); botão "+ Adicionar" discreto. Detalhes finos da lista ainda serão
  revistos com o Thiago.

## Desenho da faixa (componente)

SVG gerado a partir de (cor principal, cor da listra, marcas, cor das marcas, cor da ponta). Protótipo aprovado
pelo Thiago em 20/10 (`2026-10-20-graduation-lists-prototype.html`, ao lado deste documento; abrir no navegador):
- Lisa: retângulo de **cantos retos** (raio ≤ 2px, parece tecido, não pílula) na
  cor principal, com costuras discretas.
- Listra: faixa horizontal central (~28% da altura) na cor da listra.
- Marcas: barras na **cor das marcas**, contadas **a partir da ponta**. Se houver
  **cor da ponta**, desenha um bloco dessa cor sob as marcas (estilo jiu-jitsu).
  O sistema não decide cor nenhuma sozinho: tudo vem do cadastro.
- Tamanhos: grande (cadastro/galeria), médio (tabelas), pequeno (listas).
- Faixa branca/clara ganha borda para não sumir no fundo.

## Restrições

- Front: React 19 + TS + Tailwind/shadcn, **nada depreciado**, tipos gerados do
  OpenAPI (`npm run gen:api`).
- Backend: FastAPI + SQLAlchemy + Alembic, testes com pytest; padrões existentes
  (`public_id` UUID na API, `academy_id` em tudo, erros `{detail, code}`).
- Sem upload de arquivos (produção sem servidor de arquivos definido).

## Ordem sugerida

1. Backend: catálogo (Musculação/Crossfit), faixas, histórico, listas + testes.
2. Front: componente do desenho + tela de Faixas nas Configurações.
3. Front: Graduações (listas).
4. Front: seção de faixas na ficha do aluno, faixa atual no cadastro (2a) e
   Lançar faixas (2b) — junto com as Fases 7–8 (alunos com dados reais).

Protótipo clicável do fluxo completo (aprovado em 20/10):
`2026-10-20-graduation-flow-prototype.html` (no Obsidian: `Anexos/faixas-fluxo-prototipo.html`).

## Deixado para quem implementar

Nomes exatos de rotas e schemas, formato do reordenamento (lista de ids vs.
mover um item), paginação das listas (provavelmente desnecessária no início).
