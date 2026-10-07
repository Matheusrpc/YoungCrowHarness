# Controlador de canal e fixture fixa

Frente: evolução do executor isolado, PBI 2 / YC-203.

O controlador de canal aberto e a fixture fixa estão implementados. O controlador
foi exercitado com processos reais sob o supervisor existente; a fixture conversou
com o relay real por sockets locais e upstream fictício. A integração com reserva
global e recuperação ainda precisa ser concluída antes do despacho nativo.

Base: PR [#24](https://github.com/Matheusrpc/YoungCrowHarness/pull/24), commit
`b801bec963e8af4af921b8c5473d3884ee5a7a03`. Este incremento está somente no checkout
cloud. O [incremento anterior](2026-10-07-synthetic-admission.md), seus recibos e suas
medições foram preservados; hashes anteriores continuam identificando aquele estado.

## Entrega

- `scripts/mission_controller.py`: manifesto fechado para a fixture, pipe persistente
  do launcher, identidade e namespace conferidos, intenção durável antes de preparar,
  iniciar, alterar rede e autorizar comandos. Espera `ready`, limita eventos/saídas,
  valida eco e fechamento. O processo filho herda o grupo/job do supervisor externo.
- `runtime/sbx/fixture.py`: inicialização sem rede e uma GET fixa a `127.0.0.1:62143`.
  Confere rota, marcador fictício e URL da resposta; emite hash e metadados limitados.
  Não aceita URL/código livre, não repete requisição e não chama modelos.
- Pacote: Dockerfile e allowlist incluem a fixture. Setup distribui o controlador
  e preserva arquivos existentes mesmo com `--force`. Cinco capacidades passam a
  declarar esse arquivo; cinco hashes de contrato e dez de conteúdo foram renovados.
  As permissões permanecem iguais; os 24 hashes de conteúdo não nulos conferem.
- Continuidade: README PT/EN, guia, backlog e handoff apontam a ordem das entregas
  restantes e distinguem componentes locais de aceite do executor.

O controlador é uma biblioteca interna; não há novo comando público. O coordenador
confiável deve fornecer launcher próprio e gravação durável. O teste usa um launcher
local substituto, sem comandos Docker. `client check` conserva `controller_pending`.
Nenhum resultado do controlador libera perfis ou fecha a reserva: `proof_accepted`
e `workload_reaped` permanecem falsos. Em B, retorno 126 fica `blocked_unattributed`;
uma resposta permitida fica `unexpected_allow`.

## Verificação

Comandos:

```bash
python3 -B -m unittest discover -s tests -p 'test_mission_controller.py' -v
python3 -B -m unittest discover -s tests -p 'test_isolated_fixture.py' -v
python3 -B -m unittest discover -s tests -p 'test_mission_relay.py' -v
python3 -B -m unittest discover -s tests -v
bash -n setup.sh
git diff --check
```

Os 12 testes do controlador passaram. Cobrem fragmentação de eventos, gates,
identidades divergentes, inicialização que termina sem `ready`, falha de gravação
antes e depois do despacho, replay consumido, prazo com descendentes, B sem atribuição,
B permitido, comandos extras recusados e falha parcial na abertura dos leitores.
Os cinco testes da fixture e os 12 do relay passaram; a integração nova verifica
uma requisição, intenção anterior ao upstream, eco, hash do corpo e encerramento.

Suíte completa: **524 testes, 504 passaram, 20 pulados, zero falhas/erros em 217,664s**.
Sintaxe do setup e `git diff --check` passaram; vault com três notas, sem problemas.
Resultados e escopo dos casos pulados estão na [medição](../medicoes/2026-10-07-controller-channel.json).
Logs privados em `.runtime/controller-20261007/`; hashes na medição versionada.

Dois revisores independentes conferiram protocolo/contenção e fixture/relay. Um
`RuntimeError` na criação do segundo leitor escapava da classificação: reproduzido
em teste RED, corrigido com fechamento e motivo sanitizado, depois GREEN. O timeout
da fixture também passou a ser recalculado antes do envio após conectar. A revisão
final do controlador não encontrou pendências no escopo.
Um terceiro revisor conferiu distribuição, catálogo e alegações PT/EN: sem achados;
os 14 hashes de contrato e 24 hashes de conteúdo correspondem às fontes.

Os testes não provam TLS, isolamento Docker, bloqueio nativo ou restauração. Esta
cloud não tem `sbx` nem `/dev/kvm`. Não houve build de imagem, mutação Docker,
requisição externa ou chamada de modelo. O CI do GitHub permanece desconhecido
porque a API recusou a consulta anterior. Dois dos três ciclos nativos seguem usados;
nenhuma nova tentativa nativa foi consumida.

## Próxima entrega

1. Integrar missão e reserva global a um plano imutável A/B/A2 com IDs próprios,
   candidato exato e baseline observado. Guardar os valores necessários à restauração,
   além dos hashes. Operações consumidas v1 permanecem consumidas.
2. Integrar comandos nativos fechados, controle de egress e recuperação. Testar
   interrupção em cada fronteira; preservar deriva externa; não iniciar VM parada
   para observar; provar encerramento e restauração antes de liberar a reserva.
3. Reconstruir e provar o candidato exato em A/B/A2, incluindo bloqueio atribuível
   em B. Depois, Claude e Codex por assinatura e adoção. Só então fila/agentes,
   QA e release/operação, conforme o backlog aprovado.

## English overview

The internal open-channel controller and fixed unpaid fixture are implemented and
tested with local processes and the real loopback relay using a fake upstream.
Setup distributes the controller and preserves local copies; the image build context
includes the fixture. Capability dependencies and hashes changed, permissions did not.
The controller checks durable intent, identity, network gates, bounded events and
fixed fixture results. Phase B failures remain unattributed without native evidence.

Global reservation, immutable A/B/A2 planning, fixed native commands and verified
recovery must still be integrated. Public `client check` remains blocked. No image
was rebuilt, native profile approved or model called. These changes remain local;
native proof requires a suitable environment and preserves the historical cycle cap.

ATRASO: main 1 frente sem aceite | PR #24 incremento local não publicado.
