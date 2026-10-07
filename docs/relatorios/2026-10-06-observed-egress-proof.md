# Prova de saída observada: falha no contrato de settings

Frente: executor isolado / YC-203, R1. Estado: operação inconclusiva, restauração confirmada, correção local validada.

O operador executou a prova em 2026-10-06 UTC. O roteiro parou antes das GETs por uma
comparação incorreta de settings. A operação está consumida, sem recuperação pendente.
[Plano e limites](../superpowers/plans/2026-10-06-observed-egress-proof.md).
[Medição atualizada](../medicoes/observed-egress-proof.json).

## Causa e correção

Ao gravar `no_proxy.sandbox=""`, o controlador exigia `source=override`. Docker documenta
que atribuir o valor padrão remove o override; nesse caso, a origem esperada é `default`.
A mesma expectativa errada estava na fixture, por isso os testes anteriores passaram.
A regra está na [documentação oficial de settings](https://docs.docker.com/ai/sandboxes/configuration/settings/).

Corrigimos a fixture primeiro: o teste reproduziu `settings_readback_failed`. Depois,
um helper passou a calcular a origem esperada a partir do padrão registrado no snapshot.
Ativação, conferência de fase e reconciliação usam esse contrato. A comparação entre
origem e valor permanece estrita; ambiente e alterações de terceiros não são aceitos.
A suíte focada passou em 75 testes, sem skips, falhas ou erros. Inclui perda da resposta
ao gravar o padrão e preservação de uma origem de ambiente mesmo com valor igual.

O arquivo executado foi preservado antes da alteração, com SHA-256
`3edc8f391ea87e4d1ceb22e0d21fd59a619311fb3057c1227c844f37a4203b1d`.
Recibos e medição da preparação foram conservados. O wrapper consumido não foi repinado.
A correção é privada e local; não houve nova prova nativa, commit, push ou liberação de perfil.

## Execução e restauração verificadas

Entre 02:56:55Z e 02:57:31Z, os 60 comandos registrados terminaram com código zero,
sem timeout. O controlador falhou após o set/get de `no_proxy.sandbox`. O registro de
comandos guarda categorias e resultados, sem o conteúdo do readback naquele instante;
a sequência, o código e a regra do fornecedor identificam a comparação incorreta.
Essa falha não explica o timeout histórico da v2.

Foram duas escritas de setting e um unset de restauração. Nenhuma fase A/B/A2 foi
executada, nenhuma credencial fictícia foi registrada e nenhuma regra foi criada.
O guard da fase A foi preparado e recolhido. O único reinício do serviço ocorreu durante
a restauração. Não houve GET ou chamada a modelo.

Às 03:06:59Z, a conferência independente, somente leitura, confirmou os settings originais,
política preservada, inventário de credenciais preservado, cinco VMs conhecidas paradas,
porta temporária sem listener e identidade do daemon igual à registrada pela limpeza.
A comparação de política conserva a regra documentada no controlador para IDs de kit
regenerados pelo serviço. Nenhum valor de credencial foi lido ou publicado.
`restoration-verified.json` preserva essa observação e os hashes dos quatro recibos.

Não execute novamente `-RunApprovedProbe` ou `-Reconcile` para essa saída. Não há
limpeza pendente. R1 permanece parcial: a correção local ainda não passou pelo ensaio
nativo de rede. Nenhuma nova operação foi criada nesta correção.

## Histórico da preparação

## Observação local

Quatro consultas somente leitura passaram em 2026-10-06, entre 01:55:31Z e 01:55:35Z:

| Consulta | Duração | Resultado |
|---|---:|---|
| Estado do daemon antes | 1,107 s | Em execução |
| Identidade do processo | 1,516 s | Um processo com o executável esperado |
| Inventário das sandboxes | 0,543 s | Cinco VMs conhecidas, todas paradas |
| Estado do daemon depois | 0,420 s | Em execução |

Cada consulta usou limite de 15 segundos; as árvores de processos próprias foram
recolhidas. Não houve consulta de settings, reinício, VM iniciada, tráfego de eco ou
chamada de modelo. O timeout histórico não se repetiu; sua causa permanece desconhecida.

A primeira versão do coletor falhou após consultar o daemon ao tentar ler um campo
`stderr` ausente no retorno do supervisor. O registro parcial foi preservado, o coletor
passou a usar somente os campos reais e a observação acima foi gravada separadamente.
Essa falha de coleta não é evidência de falha no Docker.

## Diferença preparada e testes

`observed_egress.py` grava `attempt.json` antes do preflight, conserva o consumo mesmo
se não houver `control.json`, usa o lock já existente e registra cada chamada síncrona
ao Docker/PowerShell, incluindo o transporte delegado à VM. Categoria, UTC, duração,
prazo e resultado ficam em `commands.jsonl`; argumentos, saídas e texto de exceção ficam
fora desse registro. O tempo da gravação inicial é descontado do prazo.

O roteiro exige `-RunApprovedProbe` e hashes correspondentes. Sem flag, recusa antes
de Python. `-Reconcile` não inicia outra prova. Os testes cobrem timeout, falha ao
gravar intenção, sigilo, preservação de retorno, prazo expirado, consumo da tentativa,
reconciliação, mudança de fonte e transporte delegado. Dois testes usam um processo
Python real e limitado, sem Docker ou rede.

Comando da verificação: `python -B -m unittest discover -s .superpowers/sdd/2026-10-04-isolated-executor -p 'test_*egress.py' -v`.
Resultado: 72 testes aprovados, sem skips, falhas ou erros; 60 herdados e 12 novos.
O resultado final e os hashes ficam na medição ligada acima. A suíte pública de 414
testes é evidência da entrega anterior de setup; não foi repetida nesta preparação.

## Revisão e decisões

Uma revisão independente apontou que `guardian_vm.execute` usava outro vínculo com
`subprocess`, deixando `ls`, `inspect` e `exec` fora do registro novo. A regressão falhou
com `delegated transport was not observed`; após instrumentar ambos os módulos,
passou e confirmou a restauração das dependências após timeout. Fontes herdadas intactas.
Nenhum outro achado foi emitido; não houve segunda revisão.

A plataforma recusou abrir um revisor novo por limite de threads. Foi reutilizado um
revisor independente que havia examinado o setup, em modo somente leitura. Isso preserva
a separação do autor, mas não equivale a contexto novo.

Decisões: conservar o candidato anterior e seus limites; separar o novo estado; executar
somente leituras nesta rodada; manter a execução nativa como ação explícita do operador.
O custo de a hipótese falhar é uma rodada inconclusiva ou reprovada, sem liberar R1.
Não houve mudança de requisito, backend, política, autenticação ou perfil.

O revisor não julgou viabilidade/restauração nativas, a implementação integral anterior
de SOCKS/TLS/DNS ou a certificação de OAuth/MCP/clientes. Esses limites foram mantidos:
nenhum teste local é apresentado como prova dessas propriedades.

## Próxima ação

Avaliar uma operação futura com o contrato corrigido e seus limites explícitos. A rodada
consumida não será reaberta. A prova A/B/A2, OAuth, isolamento do intermediário e MCP,
pacote atualizado e suspensão seguem pendentes. R2/R3 dependem do aceite de R1.

## English overview

The proof stopped before any GET because the controller expected `override` when assigning
a default-valued setting. Docker removes the stored override in that case. The fixture had
the same incorrect assumption. After reproducing the failure, the shared applied-setting
expectation was corrected; 75 local tests passed. Source/value checks remain strict.

All 60 native commands returned zero. Two settings were written and one was unset during
cleanup; the only daemon restart restored the original settings. No dummy credential,
policy rule, echo request or model call was dispatched. Independent read-only checks
confirmed restoration, five stopped VMs and the closed temporary port. No recovery is needed.

The executed source and receipts remain preserved; the consumed wrapper was not repinned.
The correction has not been tested in a new native operation. R1 remains partial and no
product profile, commit, push or production deployment is claimed.

ATRASO: main 1
