# Isolated executor implementation plan

**Atualização de 06/10, 21h50 (São Paulo):** a entrada corrigida foi executada e
parou em `sbx secret ls --json`, com código 1. Foram 25 consultas: proprietário,
configurações e políticas passaram; nenhuma ação de alteração foi iniciada.
`cleanup.restored=true`, sem erros. Não repetir nem reconciliar essa operação.
A consulta passou em duas verificações locais, uma com o auxiliar Windows original;
a mensagem da falha remota não foi capturada. A causa permanece desconhecida.
Próximo: obter o erro dessa consulta no contexto remoto, com diagnóstico somente
leitura, antes de preparar outro ensaio completo. A/B/A2 e o aceite de R1 continuam
pendentes. Os 102 testes anteriores verificaram preparação e respostas simuladas.

**Current checkpoint:** the corrected entry was consumed at 21:50 São Paulo time
on October 6. `sbx secret ls --json` exited 1 after ownership, settings and policy
checks passed. All 25 commands were reads; no mutation began. Cleanup is verified.
Do not replay or reconcile this operation. Two local inventory queries passed,
including one through the existing Windows helper, but the remote error message was
not retained. Its cause remains unknown. Next: capture only that read-only query's
error in the remote context before preparing another full probe. Native A/B/A2 and
R1 acceptance remain pending; the earlier 102 tests used simulated Docker replies.
Earlier next actions below are historical.


> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The operator already selected inline execution and one independent final review; do not ask for that choice again.

**Goal:** Executar um diagnóstico autenticado de Claude e outro de Codex em isolamento local comprovado, com prazo independente do coordenador e recuperação sem repetição.

**Architecture:** Acrescentar um adaptador Docker Sandboxes aos recibos e reservas existentes. O coordenador conserva SQLite/vault; uma microVM sem montagem do projeto recebe apenas a fixture do diagnóstico. Um supervisor protegido limita o cliente dentro do executor, e a confirmação da parada da sandbox participa do resultado durável.

**Tech Stack:** Python 3.11+ e biblioteca padrão, SQLite esquema 2, `unittest`, Docker Sandboxes local (`sbx`), clientes oficiais e contêiner Linux interno. Sem SDK de modelo, serviço de roteamento ou backend alternativo.

**Spec:** [Executor isolado](../specs/2026-10-04-isolated-executor-design.md), aprovado pelo mantenedor em 2026-10-04 UTC: “aprovado bora”.

Frente: 2A / YC-203. Plano aprovado pelo mantenedor; execução inline iniciada, R1 em andamento. Base: main `932b775c385b8ab9d7ff7819e00ffcc9f3f20c95`.
As três tarefas abaixo correspondem a 2A-R1, 2A-R2 e 2A-R3; não acrescentam itens aos 25 do backlog.

**Retomada atual:** setup local/dedicado validado. A
[prova observada](2026-10-06-observed-egress-proof.md) parou antes das GETs: comparação
incorreta da origem de um valor padrão. Correção validada em 75 testes locais; restauração
confirmada por leitura. Operação consumida, sem limpeza pendente ou nova tentativa criada.
V2 encerrada, R1 parcial e perfis vazios. O timeout histórico continua sem causa comprovada.
A continuação executou `run-corrected-egress-proof.ps1`: controle positivo aprovado,
controle negativo inconclusivo e A2 não executado. Restauração confirmada; não repetir
ou reconciliar. A análise atribuiu B à recusa do guard no log do daemon; o coletor não
reconheceu essa evidência. O [coletor separado](../../relatorios/2026-10-06-captured-egress-evidence.md)
passou em onze testes offline. A [integração](../../relatorios/2026-10-06-integrated-egress-controller.md)
também foi validada sem Docker, incluindo recuperação sem repetição. A entrada nativa
está preparada; 113 testes passaram. Próximo: uma execução pelo mantenedor no PowerShell
normal, conforme o [guia](../../USAGE.md#entrada-do-ensaio-integrado-somente-mantenedor).
Preflight desta preparação inconclusivo por timeout; consulta isolada retornou daemon
em execução. Nenhuma operação nativa nova criada.
[Resultado nativo anterior](../../relatorios/2026-10-06-corrected-egress-proof.md).

**Impedimento encontrado durante R1:** o contrato `sbx@1` não permite que o entrypoint
da imagem seja PID 1, premissa usada na etapa 3. A [revisão técnica](../../relatorios/2026-10-04-isolated-executor.md#impedimento-no-supervisor)
registra a fonte e as consultas à CLI instalada. As etapas dependentes estão interrompidas;
o texto aprovado abaixo permanece como histórico, sem autorizar contornos ou declarar R1 concluído.

**Continuação autorizada:** o [ensaio do supervisor interno](../../relatorios/2026-10-04-supervisor-spike.md)
comprovou parte das fronteiras com fixture descartável, usando lançador confiável e
um contêiner adicional. A retomada de R1 deve formalizar esse mecanismo, preservar
os demais requisitos e testar o protocolo de despacho único antes de R2.
Não reutilizar a fixture como executor do produto. O recibo distingue controles
observados das pendências de rede, autenticação, suspensão e recuperação em execução.

**Refinamento implementado em R1:** o [contrato do protocolo](../specs/2026-10-04-isolated-executor-design.md#protocolo-do-guardian-refinamento-de-r1-2026-10-04)
usa `runtime/sbx/guardian.py` em contêiner separado, com diretório de controle root/0700 na
microVM e claim exclusivo sincronizado antes de iniciar processos. A [prova em Python](../../relatorios/2026-10-04-guardian-protocol.md)
cobre as duas fases, recusa de repetição/reinício e retirada do bounding set do cliente.
`tests/test_mission_guardian.py`, `tests/fixtures/guardian_attack.py` e
`tests/smoke_mission_guardian.py` detalham esse trecho da etapa 3. O smoke é parcial e exige
imagem preparada na VM; não substitui o futuro `smoke_mission_sandbox.py` nem certifica R1.

## Global Constraints

**Revisão atual, aprovada e medida:** [saída por domínio](../specs/2026-10-05-hostname-egress-decision.md).
O [ensaio A/B/A](../../relatorios/2026-10-05-hostname-cidr-proof.md) retornou três HTTP 200,
inclusive sob negação universal de IP. A combinação nativa está reprovada para o
requisito de destino final. A [instalação local exclusiva](../specs/2026-10-05-exclusive-egress-decision.md)
foi aprovada para saída após a injeção. O [adendo de R1](2026-10-05-exclusive-egress-proof.md)
detalha controle descartável, ativação/restauração e prova nativa; aguarda revisão do
plano antes de implementar. Método inline e três PBIs preservados. Nenhum PBI concluído
por essa prova, nenhum relay ou perfil habilitado.

**Checkpoint nativo:** a [prova com o proxy real](../../relatorios/2026-10-05-native-proxy-compatibility.md)
concluiu quatro TLS nos provedores, mas a substituição de credencial descartável passou
somente por domínio. Para dois serviços de eco, o runtime recusou o nome no túnel por IP
sem interceptação (`forward-bypass`). Credenciais falsas removidas, inventário e políticas
restaurados, cinco VMs paradas. Próximo: revisar o contrato usando o caminho por domínio
com controle observável do destino final. Não integrar a fixture ou desabilitar o guard;
OAuth, isolamento, R1 e R2/R3 seguem pendentes. Runtime do produto inalterado.

**Checkpoint da prova conjunta:** o mantenedor aprovou a investigação e os
[três ciclos sintéticos](../../relatorios/2026-10-05-auth-egress-spike.md) terminaram.
Túnel genérico e domínio fixo isoladamente falharam nas fixtures; IP do CONNECT,
SNI e Host fixos passaram nos casos simulados, com credencial falsa. Nenhum proxy
Docker ou cliente autenticado participou. Próximo: comprovar compatibilidade nativa
antes de integrar um intermediário. A prova não autoriza distribuir a fixture nem
habilitar perfis; isolamento de processos, OAuth e R2/R3 continuam pendentes.

**Checkpoint de DNS/proxy:** a [investigação seguinte](../../relatorios/2026-10-05-proxy-resolution.md)
mediu DNS direto e proteção dos arquivos de resolução, mas não estabeleceu o destino final.
O controle fora do Docker reproduziu o TLS com IP divergente; não atribuir a causa ao Docker.
A autenticação com tokens retidos no host depende do forward proxy, inacessível ao cliente
na candidata atual. A próxima investigação proposta trata autenticação e isolamento MCP
juntos e aguarda aprovação própria. Não autoriza novo proxy, backend ou exposição de tokens.
R1 parcial, perfis vazios; mudança de DNS, redirecionamentos, pacote, suspensão e R2/R3 pendentes.
Este checkpoint atualiza a próxima ação sem alterar os critérios do plano aprovado.

**Checkpoint de endereços e sentinelas:** os [ensaios seguintes](../../relatorios/2026-10-05-gateway-endpoints.md)
usaram o mesmo launcher e dois provedores: 124 tentativas TCP sem conexão, quatro
respostas TLS e zero acessos às sentinelas Windows. Recibos consumidos; políticas
restauradas e VM parada. A prova cobre os endereços observados e conserva as limitações
de DNS/IPv6 do relatório. Próximo: DNS/redirecionamentos e resolução no proxy transparente.
R1 parcial; perfis vazios; pacote corrigido, suspensão e R2/R3 continuam pendentes.

**Checkpoint de rede integrado:** o [launcher v2](../../relatorios/2026-10-04-network-launcher.md)
fixa um domínio/IPv4 público, instala DROP antes da bridge e exige um recibo privado
para cada fase. O manifesto v1 continua sem rede. Oito casos nativos e dois ensaios
de transporte TLS com provedores passaram. Reinício ativo v2 executado: verificação
reprovada por usar o horário recuperado após novo boot. Logs do host indicam parada
anterior ao deadline; recibo preservado. Nova observação antes de exec comprovou a VM
parada 3,756s antes do limite e repetição recusada após boot. Suíte de produto anterior: 390 testes, zero falhas/erros e 11 skips.
R1 permanece parcial e os perfis vazios.
Esse checkpoint substitui a pendência de integração da prova anterior, preservando
seus recibos e hashes. Não antecipa R2/R3, pacote corrigido ou autenticação.

**Checkpoint do launcher:** [prova e impedimento do pacote](../../relatorios/2026-10-04-launcher-boundary.md).
`runtime/sbx/launcher.py` separa criação e início com claims duráveis e validação efetiva.
`tests/test_mission_launcher.py` e `tests/smoke_mission_launcher.py` cobrem esse contrato;
o smoke segue parcial. O builder gerenciado falhou no startup; um
[build nativo com Buildx](../../relatorios/2026-10-04-native-kit-build.md) construiu e importou
a receita v3. A criação pelo pacote ainda depende de confiança HTTPS no registry local;
o ensaio autorizado por HTTP foi recusado e a exceção de origem foi retirada.
A [criação pelo pacote passou](../../relatorios/2026-10-04-native-package-proof.md) com
`--pull missing`, mesmo digest, 2 CPUs/4 GiB e nenhuma montagem do projeto. Certificado,
origem e portas foram restaurados. Arquivos protegidos, recusa sem coordenador e três casos
do launcher passaram nessa VM. Freeze/thaw do contêiner terminou com prazo vencido e repetição
recusada, mas não prova suspensão do host nem ausência de execução transitória após a retomada.
O [reinício ativo falhou no prazo estrito](../../relatorios/2026-10-04-shutdown-reserve.md).
Refinamento: reservar um segundo dentro do prazo original para encerramento, compartilhando
a regra entre guardian e launcher. Os novos testes reproduziram a falta dessa reserva; nove
cenários sintéticos passaram com a candidata. O novo reinício ativo passou com 993,6312 ms
de sobra e repetição recusada. Código e recibo separados preservam a prova anterior, sem
aceitar tolerância após o limite ou atualizar seus hashes. Próxima prova: rede/MCP e sentinelas.
R1 não foi concluído; a distribuição dos assets continua dependente da prova do pacote.

Duas provas adicionais encerraram o coordenador Python e o transporte `sbx` no Windows
após o início do cliente. Ambos os contêineres terminaram antes do prazo de cinco segundos,
com PID 0, e recusaram novo início. A candidata 0.47.0-rc2 foi inspecionada sem instalação;
compatibilidade do builder não estabelecida. Reconstrução do pacote corrigido, suspensão, rede/MCP
e autenticação continuam pendentes; essas provas não antecipam o aceite de R1 ou R2.

Refinamento aprovado em 2026-10-04: aplicar a [decisão de fronteira MCP](../specs/2026-10-04-mcp-boundary-decision.md).
A presença do gateway externo deve ser registrada; a ausência de acesso pelo cliente exige
prova própria antes de habilitar o perfil. A criação e a inspeção não concedem esse aceite.
`observe_stop` recebe o seletor durável `{id, name, image_digest, executable_sha256}`; consulta
`ls/inspect/ls` na versão observada. Estado parado da VM não basta para `workload_reaped`.
As etapas abaixo que pedem ausência total de MCP devem ser lidas sob esse refinamento;
os demais requisitos, dependências R1/R2/R3 e execução inline permanecem.

- “120 segundos por cliente e uma tentativa por manifesto.” Na prova final, dois manifestos, um por cliente; nenhuma repetição automática.
- “A reserva existe antes de criar/iniciar recurso externo ou fazer chamada ao fornecedor.” Inclui recursos para descoberta de catálogo, mesmo sem inferência.
- “O diagnóstico começa sem montar o projeto.” Entram apenas manifesto sanitizado, nonce e arquivos fictícios; pacote de código e notas de produto pertence a 2B.
- “Não há fallback para API, outro fornecedor, execução no host ou outro modelo.” `NATIVE_PROFILES` continua vazio.
- “Mudanças em versão, imagem, configuração efetiva, política ou mecanismo de autenticação invalidam a prova anterior.” Nome de perfil e recibo local não concedem autoridade.
- “Um controle não observável deixa o perfil sem suporte.” Isso inclui identidade da VM, OAuth efetivo, rede, compartilhamentos e encerramento.
- “O agente não pode matar, reconfigurar ou estender o prazo do supervisor.” A hipótese deve ser provada antes de integrar chamadas reais.
- “Nenhum modelo é fixado no código do produto ou trocado para fazer um teste passar.” Preservar `latest`, `client-default` e valores explícitos.
- “O retorno do trial continua restaurando o repositório.” Runtime, conta Docker e logins têm remoção separada; nenhum reset global ou reinício automático.
- “Uma prova de diagnóstico não certifica o futuro perfil de desenvolvimento.” Missões continuam `prepared`; fila, PBIs em execução, QA, merge e deploy permanecem fora deste incremento.
- Um escritor por checkout; publicação por PR protegido; autor humano; README/guia PT/EN revisados com humanizer e design existente.

## Review Focus

1. `sbx exec` inicia uma sandbox parada: consulta e reconciliação devem usar observação sem executar dentro dela. Testes nas tarefas 1 e 2.
2. Resposta de criação perdida ou nome reutilizado: nome sozinho não autoriza parar/remover; manter incerteza sem novo despacho. Tarefas 1 e 2.
3. Cliente usa `setsid`, satura processos, encerra o pai ou tenta alterar o relógio: o prazo precisa sobreviver fora de sua identidade e recolher descendentes. Tarefa 1.
4. OAuth aparente encobre API global, passthrough ou regra de kit mais ampla: recusar antes da inferência, conservando configurações do usuário. Tarefas 1 e 3.
5. Documentação local funciona, mas o projeto instalado recebe links ou helpers ausentes: testar o conjunto instalado em projeto novo e migração, incluindo rollback. Tarefa 3.

## Arquivos e responsabilidades

| Caminho | Trabalho previsto |
|---|---|
| `scripts/mission_sandbox.py` (novo) | Preflight local, política/identidade normalizadas e ciclo de vida do único backend `sbx` |
| `runtime/sbx/guardian.py`, `runtime/sbx/youngcrow.dockerfile`, `runtime/sbx/youngcrow.yaml` (novos) | Supervisor protegido, cliente sem privilégios e workload v3 próprio, validado na versão instalada |
| `runtime/sbx/profiles.json` (novo) | Identidades revisadas do diagnóstico; começa com lista vazia e só ganha combinação após prova |
| `scripts/mission_runs.py` | Reserva comum, eventos do recurso externo, execução e reconciliação |
| `scripts/mission_clients.py` | Reusar catálogo/parser e separar escolha de modelo da montagem do comando nativo |
| `scripts/missions.py` | Expor ambiente, selecionar o adaptador pelo manifesto e preservar comandos atuais |
| `tests/test_mission_sandbox.py`, `tests/fixtures/sandbox_cli.py`, `tests/fixtures/sandbox_attack.py` (novos) | Contratos determinísticos, falhas do gerenciador e ataques sintéticos sem modelo |
| `tests/smoke_mission_sandbox.py` (novo) | Prova real do ambiente sem inferência e prova autenticada separada |
| `tests/test_mission_runs.py`, `tests/test_mission_clients.py`, `tests/test_setup.py`, `tests/smoke_mission_runtime.py` | Regressões de estado, modelos, instalação e compatibilidade |
| `setup.sh`, `skills-lock.json`, `.github/workflows/test.yml` | Distribuição dos arquivos necessários, hashes e CI sem conta/modelo |
| `skills/yc-config/SKILL.md`, `skills/yc-status/SKILL.md` | Orientação de ambiente e leitura dos recibos; atualizar wrappers só se o contrato exigir |
| `README.md`, `docs/USAGE.md`, `docs/BACKLOG.md`, `docs/relatorios/2026-10-04-isolated-executor.md`, `docs/medicoes/isolated-executor.json` | Uso, suporte realmente provado e evidência sanitizada |

Reusar `hash_executable`, `model_catalog`, `parse_events`, `decode_result`, `mission_process.supervise`,
`safe_path`, `atomic_write`, `canonical`, `mission_store.reader/transaction` e `mission_vault.project_run`.
O último já projeta o snapshot inteiro: não criar outro banco ou outro mecanismo de memória.
Não refatorar Docling, Graphify, trial ou configuração de agentes.

## Contratos que as tarefas compartilham

### Preflight e perfil

`inspect_environment(root: Path, executable: Path) -> dict`, em `mission_sandbox.py`, devolve
`schema_version: 1`, `kind: sbx`, `executable`, `executable_sha256`, `version`, `platform`,
`prerequisites`, `gaps`, `profile_ids` e `checked_at`. Não inicia daemon, VM, login ou inferência.
Usa versão/ajuda local e observações do SO, com os limites existentes de 30 segundos e 8 MiB.
Sem binário, informa `runtime_missing`; no Windows, WHP `InstallState=2` informa `whp_disabled`.
Não interpretar `HypervisorPresent=true` como WHP habilitado.

`validate_runtime(observation: dict, profile: dict) -> dict` produz `gaps` e um `identity_digest`
dos fatos efetivos: versão/hash do `sbx`, plataforma, imagens por digest, guardian/kit por hash,
versão/hash do cliente, protocolo, política de rede, montagens, portas, compartilhamentos e
mecanismo de autenticação. O registro público tem `schema_version: 1` e `profiles: []` inicialmente.
Nenhum campo `verified: true` recebido de um arquivo de usuário habilita execução.
O perfil revisado define campos e valores esperados; desconhecido ou divergente bloqueia.

Capturar a saída real de cada consulta suportada e normalizá-la por versão. Não inventar um
`sbx inspect`: a referência consultada documenta `sbx ls --json`. Se as interfaces oficiais não
expuserem um fato necessário sem revelar segredos, registrar a incompatibilidade e parar o caminho
dependente. Não raspar keychain, tokens ou arquivos internos do daemon para completar a observação.

### Manifesto e estado

Conservar o manifesto versão 1 para o caminho nativo atual. A versão 2 tem as mesmas chaves mais
`runtime`, com chaves exatas `kind: sbx`, `executable_sha256`, `profile_id`, `profile_sha256`.
Validar `agent_seconds` entre 1 e 120, dentro do limite da missão, `max_runs: 1`, `fixture_id: echo-v1`,
conexão `authenticated`, orçamento API nulo e nenhuma capacidade de agente pedida.
`profile_sha256` vincula o registro revisado; a identidade efetiva é conferida novamente no executor.
O caminho do binário vem de `--executable`; seu hash precisa coincidir antes de cada efeito.

Manter SQLite no esquema 2; os novos campos pertencem aos snapshots JSON e eventos existentes.
O snapshot recebe `runtime` com identidade esperada/observada, intenção de nome único, ID estável
do gerenciador, nonce de propriedade, deadline, estado do recurso, referências de provas e
timestamps de criação, liberação e parada. Campos ainda não observados são nulos.
Não guardar stdout bruto, valores de credenciais ou comandos recebidos do modelo no recibo.

`reserve_sandbox_check(root: Path, manifest: dict, environment: dict) -> dict` reutiliza a transação
de `reserve_check`, extraída para `_reserve(root, manifest, plan) -> dict`. Repetição consulta o
registro antes de qualquer ferramenta externa; a reserva congela configuração, limites e alvo.
Modelo resolvido pode ficar nulo até a descoberta controlada dentro do executor, antes da inferência.

`check_sandbox(root: Path, manifest: dict, executable: Path) -> dict` faz reserva, claim por CAS,
criação, descoberta, validação, despacho único, parada e projeção. Acrescentar eventos estritos
`runtime_claimed`, `runtime_created`, `runtime_ready` e `runtime_stopped` em `transition_run`.
Cada evento tem allowlist própria: dono local na claim; ID/propriedade na criação; identidade,
catálogo e seleção na preparação; identidade/estado observado na parada. Eventos não podem
substituir missão, manifesto, orçamento, operação ou autorização.

Claim muda `reserved` para `running` antes de criar a VM. O dono do coordenador e o dono da VM são
registros diferentes; morte do processo local não prova parada do recurso externo. Um segundo
coordenador perde o CAS e só consulta. Resposta perdida após um efeito conserva `uncertain`.
Nenhum novo UUID contorna `reserved`, `running` ou `uncertain` no projeto.

### Execução, encerramento e modelos

`supervise_check(plan: dict, *, on_created, on_ready, stop_requested) -> dict`, em `mission_sandbox.py`,
usa `mission_process.supervise` para cada transporte host e o guardian para o prazo do cliente.
Retorna os campos de processo existentes mais `runtime_identity`, `workload_reaped`,
`sandbox_stopped` e `termination_ref`. Callbacks persistem criação e preparação antes da liberação
do cliente; uma exceção impede a liberação. `on_created(runtime: dict) -> None` grava identidade;
`on_ready(observation: dict) -> dict` valida/persiste catálogo e devolve a seleção e argv gerados
pelo adaptador. `stop_requested() -> bool` conserva o contrato local existente.
O plano contém apenas argumentos estruturados gerados
pelo harness, dados sintéticos e as identidades revisadas; nunca shell fornecido pelo projeto.

`observe_stop(executable: Path, runtime: dict) -> dict` consulta identidade e estado sem iniciar a VM.
Saída: `identity_matches`, `sandbox_stopped`, `workload_reaped`, `evidence_sha256`, `gaps`.
Ausência em uma lista, código zero de `stop`, timeout de transporte ou nome com prefixo YoungCrow
não bastam como prova. Falha de confirmação mantém incerteza. Não usar `exec` para verificar parada.

`select_model(agent: dict, models: list[dict]) -> dict`, em `mission_clients.py`, extrai a seleção
já existente de `build_check`: retorna `requested_model`, `resolved_model`, `requested_effort`.
Preserva erros de ambiguidade/esforço e não muda os argumentos atuais do caminho nativo.
O adaptador isolado usa essa função, os protocolos nativos documentados e `decode_result`.
Se uma versão exigir flags diferentes dentro da VM, elas pertencem ao perfil revisado daquela
versão; não herdar automaticamente o comando padrão do kit, que pode ampliar permissões.

## Task 1: 2A-R1 — ambiente e prova sem modelo

**Files:** novos arquivos de sandbox/runtime/fixtures descritos acima; modificar `scripts/missions.py`,
`README.md` e `docs/USAGE.md`. O comando utilizável desta tarefa é `client environment --executable PATH --json`.

**Interfaces:** produz `inspect_environment`, `validate_runtime`, `observe_stop` e o envelope que
`supervise_check` usará. O ensaio `smoke_mission_sandbox.py --mode envelope --root PATH --executable PATH`
produz um recibo privado com identidade, casos, prazo, descendentes e estado final; não registra
perfil público nem aceita um comando arbitrário ou chama modelo. Retorna 0 só com todos os casos
obrigatórios comprovados; pré-requisito ausente retorna 2 com motivo, nunca um sucesso com skips.

- [ ] **Step 1: escrever os testes que definem o preflight e as recusas.**

Em `SandboxEnvironmentTests`, construir observações normalizadas fictícias no próprio teste,
com paths temporários e hashes reais. A fixture de CLI só responde a operações enumeradas e
mantém um log local de invocações. Fixar estas asserções:

```python
def test_missing_runtime_is_readonly(self):
    before = self.snapshot()
    result = inspect_environment(self.root, self.root / 'missing-sbx')
    self.assertIn('runtime_missing', result['gaps'])
    self.assertEqual(self.snapshot(), before)

def test_unknown_or_widened_profile_never_authorizes(self):
    for change in ('api_precedence', 'oauth_passthrough', 'host_mount',
                   'ssh', 'skills', 'mcp', 'clipboard', 'open_port',
                   'global_network_allow', 'missing_runtime_id'):
        self.assertTrue(validate_runtime(self.changed_observation(change),
                                         self.profile)['gaps'])
```

Definir `snapshot()` a partir da árvore temporária, `profile` e `changed_observation(change)`
em `SandboxEnvironmentTests`; nenhum deles afirma suporte real. Acrescentar testes de WHP=2,
hash alterado, JSON duplicado/truncado, 8 MiB excedidos e catálogo de perfil vazio.
`test_observe_stop_never_starts_sandbox` exige que o log só contenha consultas permitidas e
continue incerto quando falta a identidade. Reusar o parser JSON estrito existente.

- [ ] **Step 2: executar os testes e confirmar a falha antes da implementação.**

`python -B -m unittest discover -s tests -p test_mission_sandbox.py -v` deve falhar pela ausência
das funções novas, não por credencial, rede ou dependência externa.

- [ ] **Step 3: implementar preflight e preparar o envelope de prova.**

Implementar os contratos sem daemon próprio. O setup inicial é guiado: artefato oficial verificado,
conta Docker, WHP/virtualização e eventual reinício visíveis ao operador. Não ativar recursos do SO
ou fazer login dentro de um comando de diagnóstico. Registrar versão/ajuda da instalação usada.

Criar sandbox sem PATH de workspace e sem compartilhamento de skills, SSH, MCP, clipboard ou portas.
Não usar `sbx run` sem argumentos de montagem: ele pode selecionar o diretório atual. Não usar cloud,
`--clone`, socket host ou reset global. A configuração efetiva precisa confirmar as recusas antes
de qualquer workload. Identidade de imagem é digest, com pull controlado durante setup.
Usar workload v3 próprio, com o guardian no entrypoint, conforme a referência de autoria abaixo;
não combinar mixin v3 com atalhos v2 `claude`/`codex`. Imagens contêm os clientes oficiais.
Capacidade declarada no YAML mas não aplicada pelo runtime reprova o perfil; sucesso de create
não basta. Hooks de startup assíncronos não controlam a liberação do cliente.

O guardian é PID 1 no contêiner interno. Seu protocolo aceita uma inicialização para descoberta
e, depois, no máximo uma liberação de diagnóstico pelo canal privado do coordenador, dentro do
mesmo prazo; mensagens repetidas ou desconhecidas encerram sem novo despacho. O cliente não
acessa esse canal. Código, configuração e recibo de controle não são graváveis pelo cliente. O cliente
roda com UID/GID distintos, sem sudo/capabilities/socket e com `no_new_privs`; seu HOME é privado
e gravável. Fixar o teto inicial do diagnóstico em 2 CPUs, 4 GiB e 64 PIDs, registrando os valores
efetivamente aplicados. Saída combinada usa o limite existente de 8 MiB.

Antes de criar a VM de ensaio, gravar intenção exclusiva na pasta privada do ensaio com UUID,
hashes e nonce; antes de iniciá-la, conferir propriedade. Esse journal é só do ensaio sem modelo;
o produto usa SQLite na tarefa 2. Colisão ou criação de resultado desconhecido bloqueia nova criação.
Não abrir permissões de produção para conseguir rodar o ensaio.

- [ ] **Step 4: provar duração e fronteiras no runtime real, sem inferência.**

Rodar `smoke_mission_sandbox.py --mode envelope` com limite de 5 segundos para workloads sintéticos.
Verificar resposta permitida; leitura/escrita em sentinelas fora do pacote recusadas; HOME interno
gravável; domínio permitido de fixture acessível e host/rede privada/metadata/domínio proibido
inacessíveis. Somente arquivos fictícios entram no teste, inclusive os que simulam credenciais.

Executar `sandbox_attack.py` nos modos `descendants`, `setsid`, `signal-guardian`, `rewrite-deadline`,
`process-limit` e `output-limit`. Matar o coordenador deliberadamente, perder transporte, reiniciar
daemon e retomar VM suspensa: nenhum caso pode conceder um novo prazo ou reexecutar workload.
Até 5 segundos adicionais servem para observar a limpeza; não ampliam o tempo permitido do cliente.
Provar zero descendentes após o prazo por observador fora da identidade do cliente.
Ao retomar estado expirado, impedir despacho antes de liberar rede/cliente.

Conferir a política efetiva combinada com regras globais/kit. Não editar política global para fazer
passar. Se o runtime não suportar as garantias de prazo, propriedade ou inspeção, publicar a prova
negativa e interromper 2A-R2/R3; não trocar de backend nem anunciar execução segura.

- [ ] **Step 5: repetir os testes determinísticos e registrar o aceite de R1.**

O comando da etapa 2 precisa passar. Guardar JSON/hash sanitizado da prova real e o estado final
de cada recurso. Atualizar README/guia com o preflight disponível e a matriz realmente observada.
Commit por caminhos explícitos: `feat: add isolated executor environment and envelope proof`.
R1 fecha somente com prova real; preflight funcionando sozinho é uma entrega parcial.

## Task 2: 2A-R2 — execução durável, parada e recuperação

**Files:** `scripts/mission_runs.py`, `scripts/mission_clients.py`, `scripts/mission_sandbox.py`,
`scripts/missions.py`, `tests/test_mission_runs.py`, `tests/test_mission_clients.py`,
`tests/test_mission_sandbox.py`, `tests/runtime_fixtures.py`, `README.md`, `docs/USAGE.md`.

**Interfaces:** consome os contratos/provas de R1; produz `select_model`, `reserve_sandbox_check`,
`check_sandbox` e `supervise_check`. `client check` escolhe `sbx` apenas por manifesto v2 válido.
`reconcile_check` ganha `*, executable: Path | None = None`; em run `sbx`, exige binário vinculado
e observação de parada, além das referências exatas de término/efeito já exigidas hoje.
Comandos de leitura não iniciam VM nem reparam estado. `client inspect` nativo permanece intacto;
catálogo do executor é descoberto depois da reserva e registrado com sua origem/data.

- [ ] **Step 1: escrever regressões de repetição, claim e efeito desconhecido.**

Estender `RuntimeCase.make_manifest()` com helper separado `make_sandbox_manifest()`; os testes
antigos mantêm v1. Usar o gerenciador fictício da tarefa 1 com catálogo `model-a`/`model-b`, esforço
`low`/`high` e contador de despachos. A fixture não deve entrar no registry público.

```python
def test_sandbox_replay_does_not_dispatch_twice(self):
    manifest = self.make_sandbox_manifest()
    first = self.sandbox_check(manifest)
    again = self.sandbox_check(manifest)
    self.assertEqual(first['id'], again['id'])
    self.assertEqual(self.dispatch_count(), 1)

def test_cli_exit_without_vm_stop_stays_uncertain(self):
    run = self.sandbox_check(self.make_sandbox_manifest(), mode='stop-unconfirmed')
    self.assertEqual(run['state'], 'uncertain')
    with self.assertRaisesRegex(ValueError, 'unresolved_run'):
        self.sandbox_check(self.make_sandbox_manifest())
```

Definir `sandbox_check(manifest, mode='success')` e `dispatch_count()` na fixture de teste usando
o log do gerenciador. Acrescentar testes que matem o coordenador antes/depois de create, depois
de dispatch e antes do recibo; dois coordenadores no mesmo UUID; payload divergente; create sem
resposta/ID; VM com nome reutilizado; troca de perfil/binário/política entre observação e efeito;
falha de projeção e nota humana; v1 e banco esquema 1 continuam legíveis sem migração na consulta.

- [ ] **Step 2: executar os novos testes e confirmar falha de contrato.**

`python -B -m unittest discover -s tests -p test_mission_runs.py -v` deve mostrar falhas nas entradas
novas ainda ausentes, mantendo identificáveis as regressões antigas. Não aceitar skip como prova.

- [ ] **Step 3: implementar o fluxo com estado persistido antes dos efeitos.**

Extrair `_reserve` e `select_model` sem mudar os contratos v1. Em `check_sandbox`, preservar
consulta idempotente primeiro, reserva com alvo e limites, claim CAS, create, identidade persistida,
descoberta sem inferência, revalidação e liberação única. A descoberta usa o mesmo envelope limitado;
não instala extensões nem executa hooks/MCP para obter catálogo.

O prazo total autorizado começa na liberação do envelope e inclui descoberta; a chamada ao modelo
recebe só o saldo. Registrar `started_at`, deadline e seleção antes de enviar o nonce. Sem saldo,
parar sem inferência. O guardian só aceita um despacho e não aceita renovar o prazo.

Interpretar eventos nativos com os parsers existentes. `succeeded` exige protocolo válido,
modelo observado compatível quando disponível, workload recolhido e sandbox parada com identidade
confirmada. Informação de esforço/modelo ausente continua nula. Evento de ferramenta omitido pelo
cliente não substitui a prova externa de isolamento.

Toda falha após liberação mantém `uncertain` até confirmação do efeito e término. Falha comprovada
antes de qualquer efeito pode terminar `failed`, preservando reserva/contadores. Expor motivos
sanitizados `runtime_unverified`, `runtime_identity_changed`, `runtime_stop_unconfirmed` e
`deadline_unverified` na allowlist CLI; não incluir stderr do fornecedor em mensagens públicas.
Estender a reconciliação sem usar PID local ou nome da VM como autorização de encerramento.

- [ ] **Step 4: testar o fluxo completo sem modelo e ler os recibos produzidos.**

`python -B -m unittest discover -s tests -p 'test_mission*.py' -v` precisa passar.
No ensaio real de envelope, repetir as falhas de transporte/coordenador com SQLite ligado:
uma intenção, no máximo um despacho, mesma operação recuperável e bloqueio por incerteza.
Hashes/configuração/identidade/prazos precisam aparecer no recibo privado e em `client runs`.
`status` conserva `runnable: false`; nenhum teste marca missão/PBI como concluído.

- [ ] **Step 5: atualizar documentação operacional e consolidar R2.**

Documentar manifesto v2, preflight, consulta e reconciliação; exemplos usam somente valores
fictícios e não anunciam prova autenticada. Commit: `feat: persist sandbox execution and recovery`.
Conservar o estado de R3 como pendente; a revisão independente cobre o incremento completo.

## Task 3: 2A-R3 — adoção e prova autenticada nos dois clientes

**Files:** `runtime/sbx/profiles.json`, `tests/smoke_mission_sandbox.py`,
`tests/smoke_mission_runtime.py`, `tests/test_setup.py`, `setup.sh`, `skills-lock.json`,
`.github/workflows/test.yml`, `skills/yc-config/SKILL.md`, `skills/yc-status/SKILL.md`,
README, guia, backlog, relatório e medição listados no mapa de arquivos.

**Interfaces:** `smoke_mission_sandbox.py --mode native --root PATH --manifest PATH --executable PATH`
consome uma missão preparada e manifesto v2 explicitamente autorizado; chama `check_sandbox` uma
vez e devolve o recibo. O modo padrão continua sem inferência. A opção nativa recusa manifestos
ausentes, mais de uma tentativa, API e prazo maior que 120. Não escolhe outro modelo/esforço.

- [ ] **Step 1: escrever as provas de adoção e conexão.**

Acrescentar `test_installed_sandbox_helpers_and_links_exist`, `test_missing_runtime_does_not_install`,
`test_native_mode_requires_explicit_manifest`, `test_oauth_conflict_never_dispatches` e
`test_unknown_model_or_effort_does_not_fallback`. Fixar, em código de teste:

```python
self.assertEqual(dispatches_without_manifest, 0)
self.assertEqual(dispatches_with_api_precedence, 0)
self.assertEqual(before_global_config, after_global_config)
self.assertEqual(vault.check(installed_root)['issues'], [])
self.assertEqual(before_trial_tree, restored_tree)
self.assertEqual(original_requested_model, receipt['requested_model'])
```

Os valores vêm do ensaio/fixtures, não de constantes fingindo uma execução. Exercitar `latest`
com recomendação fictícia mudando de `model-a` para `model-b`; catálogo atual resolve o segundo,
enquanto pedido explícito conserva o primeiro ou recusa a combinação.

- [ ] **Step 2: executar as provas novas antes de incluir os arquivos na instalação.**

`python -B -m unittest discover -s tests -p test_setup.py -k sandbox -v` deve falhar pela ausência
dos helpers no destino. Testes de conexão em `test_mission_sandbox.py` devem recusar o despacho.

- [ ] **Step 3: distribuir o incremento e documentar os dois primeiros setups.**

Incluir helpers e receitas de runtime por caminhos explícitos no instalador, sem instalar Docker
ou autenticar durante adoção/trial. Atualizar hashes do catálogo quando os arquivos vinculados
mudarem e testar preservação dos perfis globais. Usar writing-skills ao alterar as duas skills.
Notas desta pesquisa ficam em `vault/local/`; o índice compartilhado permanece portátil.

No guia PT/EN, separar: projeto do zero; migração com baseline/trial; preparação do runtime;
login Docker/OAuth nativo; agentes/modelo/esforço; prova; operação/recuperação; remoção de recursos
próprios. Remoção mostra propriedade e recibos antes de agir, não executa prune/reset/logout global.
Manter a paleta/diagramas existentes; indicar que a nova prova cobre diagnóstico, sem fila autônoma.

- [ ] **Step 4: preparar autenticação e executar as duas provas reais.**

Revalidar versão, política, imagens e prova R1. Realizar logins pelo fornecedor com interação do
operador; nenhum cache host é copiado pelo harness. Confirmar o mecanismo OAuth efetivo sem ler
o segredo. Se API tiver precedência, pedir ao operador ajuste específico; não apagar sua credencial.
Autenticação indisponível encerra o ensaio com pendência; não muda para API.
Depois de revisar as provas de envelope, política e mecanismo OAuth, registrar a combinação exata
em `profiles.json` para permitir somente o diagnóstico autorizado. Compatibilidade real do modelo
continua `not_verified` antes da chamada. Um perfil arbitrário passado por arquivo não pode
contornar esse registro; o teste determinístico substitui a dependência apenas dentro da fixture.

Criar dois manifestos sob a autorização de diagnóstico, com `max_runs: 1` e `agent_seconds <= 120`.
Usar a configuração escolhida: recomendação atual para `latest`, esforço nativo quando configurado,
ou valores explícitos. Não reabrir a escolha de modelos já respondida nem selecionar modelo antigo
para obter sucesso. Rodar primeiro um cliente, confirmar parada, depois o outro.
Guardar solicitado/resolvido/observado, autenticação, timestamps, uso disponível, custo desconhecido
quando não informado, hashes e estado final. Uma falha incerta não permite nova tentativa automática.

Os resultados registram compatibilidade por cliente/modelo observado; não certificam outros
builds/plataformas nem habilitam execução geral. Se não houver como observar OAuth/catálogo
dentro da fronteira aprovada, registrar a limitação antes da inferência.

- [ ] **Step 5: verificar adoção, fazer revisão independente e publicar.**

Executar a suíte `python -B -m unittest discover -s tests -v`, o piloto público, o ensaio de runtime
instalado para `both` e `vault.py check --json`. O CI determinístico roda em Linux/Windows sem conta,
modelo, Docker ou instalação de hipervisor. O ensaio real permanece separado e explicita plataforma;
Ubuntu/Windows só entram na matriz pública quando testados, sem generalizar uma prova do outro.

Aplicar requesting-code-review para uma revisão independente da implementação completa no modelo
mais capaz disponível, conforme o método já escolhido. Corrigir achados e repetir apenas verificações
afetadas. Registrar a publicação por PR protegido, revisão exata e procedimento de retorno.
Commit: `feat: verify isolated Claude and Codex adoption`. Atualizar README/backlog com o resultado
real: 2A só concluído se ambos os diagnósticos e os controles exigidos passarem.

## Fontes e aceite do plano

O [desenho aprovado](../specs/2026-10-04-isolated-executor-design.md) contém as fontes de isolamento,
login, TTL e política. Para os comandos deste plano, foram consultadas as referências oficiais de
[create](https://docs.docker.com/reference/cli/sbx/create/),
[exec](https://docs.docker.com/reference/cli/sbx/exec/),
[ls](https://docs.docker.com/reference/cli/sbx/ls/) e
[stop](https://docs.docker.com/reference/cli/sbx/stop/) em 2026-10-04 UTC.
O formato do workload segue [Author kits](https://docs.docker.com/ai/sandboxes/customize/author/),
recurso Early Access que precisa de compatibilidade e aplicação de controles observadas em R1.
Documentação não comprova os formatos/controles da instalação futura; R1 mede essa compatibilidade.

Auto-revisão: requisitos de fronteira/prazo em R1, durabilidade/modelos em R2, adoção/autenticação
e publicação em R3. Os cinco casos de Review Focus têm testes atribuídos. Não há implementação
do pacote de desenvolvimento, fila ou deploy neste plano. A hipótese do guardian continua sujeita
à prova real; falha encerra a etapa dependente, sem transformar mock em suporte.

Plano confirmado pelo mantenedor: “Confirmar o plano e implementar”. Método preservado: implementação nesta sessão
com `executing-plans` e uma revisão independente ao final.
