# Auditoria das mudanças recentes e da passagem para a cloud

Frente: auditoria do YoungCrowHarness, em 7 de outubro de 2026. Sem implementação de correções ou publicação.

Foram reproduzidos dois defeitos na base publicada. A implementação local do executor isolado descrita no handoff não está disponível neste ambiente; sua auditoria permanece pendente de transferência dos fontes e testes.

## Escopo e identidade

- Checkout: `/workspace/YoungCrowHarness`, branch local `work`, HEAD `932b775c385b8ab9d7ff7819e00ffcc9f3f20c95`.
- `git ls-remote` confirmou esse mesmo SHA na `main` remota. A listagem das branches remotas não contém `feat/isolated-executor`.
- Revisão concentrada nos commits publicados de preparação de missões, diagnóstico limitado e inspeção nativa (#18–#23), especialmente `mission_*`, `missions.py`, testes e contratos de recuperação.
- Contexto fornecido: “YoungCrowHarness — contexto completo para continuidade na cloud”, 604 linhas, SHA-256 `bcd5835ffabca4e8aacfc3f1885618d5bbcc75d463c0e9064613dea0d33d046f`.
- O texto foi lido integralmente. Docling está ausente e a seleção de memória local não existe; não se declara conversão Docling nem recuperação do vault privado original.

Os 27 arquivos modificados e 225 não rastreados são contagens informadas pelo handoff do Windows. Não são o estado medido deste checkout, que estava limpo no início da auditoria.

## Achados reproduzidos

### F1 — P2: interrupção de projeção seguida de revisão produz conflito que `repair` não resolve

Local: [scripts/mission_vault.py, linha 82](../../scripts/mission_vault.py#L82), com origem na seleção da revisão atual nas linhas 52–53.

A gravação Markdown ocorre antes do commit do hash no SQLite. Se a execução for interrompida nessa janela, o arquivo pode conter uma projeção legítima cujo hash ainda não foi confirmado. Uma revisão posterior da missão é aceita; ao tentar projetá-la, o código compara o arquivo somente com o último hash confirmado e com os bytes da revisão mais recente. Os bytes da revisão anterior gerados pelo próprio programa passam a ser classificados como conflito humano.

Reprodução com fixtures existentes, sem modelos:

1. Preparar uma missão e injetar `OSError` imediatamente após a gravação real de sua primeira nota. O evento é persistido e o resultado é `pending`.
2. Revisar somente o título usando `expected_revision=1` e um novo UUID de operação.
3. A revisão, `repair` e o replay da operação original retornam `conflict`. O SQLite está na revisão 2; o arquivo da revisão 1 continua intacto. Não houve edição humana.
4. Controle positivo: executar `repair` antes da nova revisão produz `current` em todas as operações seguintes.

Impacto: o percurso de recuperação documentado em `docs/USAGE.md` exige intervenção manual para um arquivo que o próprio produto gerou. Não houve perda demonstrada do evento no banco nem execução duplicada de fornecedor.

Correção recomendada: recuperar a projeção pendente antes de admitir outra revisão, ou reconhecer os bytes exatos de projeções anteriores vinculadas a eventos confirmados. Preservar o bloqueio para edições humanas reais. Acrescentar regressão que inclua a interrupção **após** a gravação, seguida de nova revisão.

### F2 — P2: catálogo malformado quebra a resposta JSON de `client inspect`

Local: [scripts/mission_clients.py, linha 149](../../scripts/mission_clients.py#L149).

Os elementos de `supportedReasoningEfforts` são acessados com `.get()` antes da validação de tipo. Uma resposta com `supportedReasoningEfforts: [null]` causa `AttributeError`. Nem `inspect_client` nem o tratamento de erros de `missions.main` capturam essa exceção.

Reprodução: substituir somente a resposta externa de descoberta por um catálogo com esse valor, preservando as verificações reais de arquivo/configuração da fixture, e invocar `missions.main(... client inspect ... --json)`. Resultado: `AttributeError` escapa e a saída JSON fica vazia. Nenhum cliente nativo foi iniciado.

Impacto: uma resposta inesperada da CLI rompe o contrato de diagnóstico estruturado e impede o consumidor de interpretar a falha. O caminho de inspeção está disponível mesmo com os perfis de execução nativa bloqueados.

Correção recomendada: validar a lista e cada objeto antes de acessar seus campos; recusar o conteúdo com erro de protocolo sanitizado. Cobrir também estruturas aninhadas nulas na descoberta. Não basta ocultar exceções arbitrárias sem validar o contrato.

## Limite da auditoria do executor mais recente

Os nove arquivos com hashes de implementação na seção 14 do handoff estão ausentes, incluindo `mission_execution.py`, `mission_egress.py`, `mission_sbx.py`, `mission_sandbox.py`, guardian, launcher, relay, Dockerfile e plano de consolidação. Também faltam os testes novos, o relatório, as medições e a memória privada de 7/out. O inventário completo está na [medição desta auditoria](../medicoes/2026-10-07-cloud-audit.json).

Consequências:

- Não foi possível conferir as correções de reserva, relay e filtro, seus hashes ou os checkpoints de 43 e 74 testes relatados no anexo.
- A/B/A2 no candidato atual, recuperação após efeitos e provas autenticadas nos dois clientes permanecem pendências **declaradas pelo handoff**, sem verificação independente aqui.
- A suíte verde da `main` não certifica a árvore local que contém essas mudanças. O próprio handoff informa que a suíte geral dessa árvore ainda não está aprovada.
- Não se deve reescrever os componentes ausentes nem habilitar perfis com base nesse texto. O registro `NATIVE_PROFILES` da base inspecionada continua vazio.

Para completar essa parte da auditoria, é necessário transferir uma cópia revisada dos fontes e testes da branch local, incluindo modificados e novos. Preservar o checkout Windows original; excluir credenciais, caches e estado operacional de Docker do pacote de código. O Markdown de contexto não substitui esses arquivos.

## Evidência e resultado

Nesta auditoria foi executada a suíte focada em configuração, backlog, missões, runs, clientes e processos: **82 testes, 80 aprovados, 2 ignorados por serem exclusivos de Windows**, em 52,832 segundos; código de saída zero. O vault disponível teve 3 notas e zero problemas. Os dois casos de reprodução acima não são cobertos pela suíte existente.

Comandos e resultados estruturados: [2026-10-07-cloud-audit.json](../medicoes/2026-10-07-cloud-audit.json). Reprodução local: `python3 -B .runtime/audit-20261007/reproduce_findings.py`; a saída está em `.runtime/audit-20261007/reproductions.json`, e o log da suíte em `.runtime/audit-20261007/mission-tests.log`. Esses auxiliares ignorados pertencem a esta instância cloud e não acompanham um clone comum.

Houve duas revisões independentes somente leitura: estado/idempotência e adaptadores/supervisão. O executor principal reproduziu os achados. Foram aplicadas as orientações de Karpathy, Ponytail, `retrieve-memory`, `ingest-source`, delegação e verificação antes da conclusão. Nenhum MCP de fornecedor foi ativado.

Não houve chamada a modelo externo, operação Docker, alteração de código/testes versionados, commit, push ou publicação. Foram acrescentados apenas este relatório e sua medição; auxiliares de reprodução ficaram em `.runtime/`. Não foi realizada evidência visual nem certificação de produção. A prioridade de continuidade é obter a árvore local correta e reavaliar nela os dois achados, que podem já ter sido alterados desde a `main`.
