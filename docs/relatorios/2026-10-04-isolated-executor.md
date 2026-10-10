# Executor isolado: diagnóstico do ambiente

Frente: 2A-R1 / YC-203. Desenvolvimento local; aceite completo da VM pendente.

Este registro preserva o diagnóstico anterior à criação das VMs. A continuação está na
[prova do supervisor interno](2026-10-04-supervisor-spike.md), com resultados sintéticos reais
e limites ainda pendentes. Nenhum perfil de execução foi habilitado.

O [plano aprovado](../superpowers/plans/2026-10-04-isolated-executor.md) tem três PBIs.
Este registro cobre o diagnóstico inicial de R1. R1 só termina quando isolamento,
identidade, política e prazo forem comprovados no runtime real, sem modelo.
R2 e R3 ainda não começaram.

## Comportamento implementado

`client environment --executable PATH --json` lê a versão e o hash do `sbx`,
consulta pré-requisitos do sistema e informa o que falta. O comando não instala
componentes, habilita recursos do Windows, cria uma VM, faz login ou chama modelos.
Versão detectada não libera execução: `profile_ids` permanece vazio e o resultado
inclui `runtime_profile_unverified`, com código de saída 1.

O setup distribui o helper nos dois clientes e preserva cópias existentes,
inclusive com `--force`. Um helper preservado com interface incompatível recebe
`incompatible_helper`. O catálogo inclui o arquivo e seus hashes nas capacidades
que dependem dos comandos de missão. Isso verifica os arquivos instalados;
não demonstra que uma skill foi aplicada por um modelo.

## Evidências e limites

| Prova | Resultado observado | O que não comprova |
|---|---|---|
| Contratos do diagnóstico | 9 testes passaram; binário ausente, versão, troca de hash, plataforma, metadados inválidos, migração incompatível e consulta Windows sem cache no perfil | Uma VM real ou perfil seguro |
| Distribuição do novo helper | Teste falhou antes da inclusão no setup e passou depois; diagnóstico instalado preservou os arquivos do destino | Diagnóstico autenticado |
| Catálogo de capacidades | Quatro skills de missão com arquivos correspondentes nos dois clientes; permissões de rede mantidas | Execução nativa das skills |
| Host Windows | Windows 11 AMD64, build 26200; sbx 0.46.0; WHP 1 após reinício observado | Isolamento ou prazo de uma VM |
| Regressão completa no Windows | Interrompida pelo reinício; sem resultado final | Aceite de R1 |
| Adoção e retorno, repetição após login | Ensaio completo passou nos perfis Claude/Codex: projeto novo e repositório com alterações locais restaurados, trial preservado e perfil global sem alterações | Execução real dos clientes ou da VM |
| Setup após reinício | 2 testes passaram: diagnóstico instalado e helpers existentes preservados | Prova da VM |
| Login Docker | Concluído pelo operador; `sbx ls --json` retornou lista vazia | OAuth dos clientes de IA |
| Regressão dos clientes e processos | 19 testes de clientes passaram; processos: 9 passaram e 1 exclusivo de Linux foi omitido no Windows | Prazo independente dentro de uma VM |

O operador ativou WHP e recebeu `RestartNeeded: True`. Depois de um adiamento,
o sistema registrou novo início às 00h52 de 2026-10-04 (São Paulo). O diagnóstico
após o reinício confirmou WHP 1 e a mesma versão/hash do `sbx`. Nove testes do
diagnóstico passaram novamente. O operador concluiu o login Docker e a consulta
de sandboxes passou a funcionar, retornando uma lista vazia. A política inicial
de rede continua pendente. Nenhuma política global foi alterada.
`whp_state: 1` não comprova isolamento de uma VM.

O ensaio de adoção encontrou gravações de cache feitas pelo PowerShell da consulta
de pré-requisitos. Um teste com perfil fictício e PowerShell real reproduziu a falha.
A consulta agora usa destinos nulos para perfil/cache e apenas os módulos do sistema,
seguindo o tratamento já usado pelo helper de permissões do harness. O teste passou
após a correção; os ambientes dos clientes de IA conservam o comportamento existente.

A primeira tentativa de retorno também confirmou a recusa documentada de caminhos
longos no Windows. A repetição usa diretórios de teste curtos e mantém o limite de
248 unidades UTF-16. Nenhuma proteção de adoção foi reduzida.

Após o login, o ensaio instalado foi repetido até o fim com fixtures e retornou
código zero nos dois cenários. Timeout e queda do coordenador conservaram a incerteza;
a reconciliação não repetiu a execução. A consulta do ambiente manteve o projeto
sem alterações e o perfil sem prova. Nove testes do diagnóstico passaram novamente,
assim como o teste do catálogo de missão. O recibo vincula os resultados aos hashes
dos arquivos locais, ainda não publicados.

Nenhuma VM, autenticação de cliente de IA ou chamada real a Claude/Codex foi iniciada no diagnóstico descrito acima.
Os perfis nativos continuam bloqueados. Não há fallback para API ou outro executor.

## Impedimento no supervisor

O plano propõe colocar o supervisor no entrypoint da imagem e usá-lo como PID 1
do contêiner. A documentação de [lançamento do Docker](https://docs.docker.com/ai/sandboxes/customize/author/base-images/#declare-the-agent-launch-contract)
descreve outro comportamento: o runtime mantém o contêiner e lança o agente como
processo separado. O [contrato `sbx@1`](https://github.com/docker/sandbox-kit-spec/blob/main/docs/spec/capabilities/com.docker.sandbox/sbx%401.md)
proíbe que o entrypoint da imagem seja PID 1. Portanto, usar esse entrypoint diretamente
não sustenta a garantia de encerramento que o plano exige.

Isso é uma incompatibilidade documental com a implementação proposta. Depois desse diagnóstico,
o mantenedor autorizou o [ensaio com contêiner adicional](2026-10-04-supervisor-spike.md).
As provas parciais desse mecanismo estão separadas do preflight e não certificam o perfil final.

Na instalação `sbx 0.46.0`, `kit validate CAMINHO --json` retornou código 1 para dois
descritores v3 sintéticos: esse caminho de validação não tinha um builder configurado.
A resposta ocorreu antes de avaliar o campo candidato de limite de processos. Ela não
prova que esse limite foi recusado ou aplicado. `kit builder status` confirmou builder
não criado; nenhuma imagem foi construída. As observações estão no
[recibo sanitizado](../medicoes/isolated-executor.json).

O login está resolvido. A continuação depende de completar o protocolo e as provas
listadas no ensaio do supervisor. R1 permanece incompleto; R2/R3 não começaram.

## Reprodução

Na raiz do repositório, use os [passos do diagnóstico](../USAGE.md#sandbox-environment).
Os testes determinísticos não exigem Docker, conta ou modelo:

```bash
python3 -B -m unittest discover -s tests -p test_mission_sandbox.py -v
python3 -B -m unittest discover -s tests -p test_capabilities.py -v
python3 -B -m unittest discover -s tests -p test_setup.py -v
```

No Windows, use `python`. A suíte nativa também usa o executor de fixtures descrito
em [tests/windows_fixture_runner.py](../../tests/windows_fixture_runner.py), que
prepara permissões somente para o processo de teste e seus diretórios temporários.

## Próximo aceite

Formalizar o mecanismo parcialmente provado no [ensaio do supervisor](2026-10-04-supervisor-spike.md),
implementar o protocolo de despacho único e completar os casos pendentes de R1.
Preparação do ambiente e provas já concluídas não precisam ser repetidas sem mudança
de identidade ou configuração. Interface ou controle não observável mantém o perfil bloqueado.

## English overview

The read-only environment diagnostic and installer support are implemented locally.
It discovers the runtime and prerequisites without creating a VM or calling a model.
All profiles remain unverified. Setup preserves existing helpers during migration;
the capability catalog includes the new helper in its integrity checks.

Windows restarted after WHP was enabled. The post-boot diagnostic and two installer
checks passed; the earlier broad suite was interrupted without a final result.
The installed adoption smoke was rerun successfully after sign-in: new and dirty
Git consumers were restored, with trial data preserved and global profiles unchanged.
These checks used fixtures and made no model calls. At this initial checkpoint,
Docker sign-in was complete and the authenticated listing was empty. Network policy
had not yet been initialized. Later setup changes and VM tests are recorded separately below.

The proposed entrypoint/PID 1 supervisor conflicts with the documented `sbx@1`
launch contract. This is a design blocker, not a completed VM test. Local v3 kit
validation also stopped because its load path had no configured builder; it did not
evaluate the candidate process-limit field. No VM or model was started at that checkpoint. The
[sanitized observation](../medicoes/isolated-executor.json) records these limits.
The subsequent [nested supervisor probe](2026-10-04-supervisor-spike.md#english-overview) records partial real-runtime proof. R1 remains incomplete; R2/R3 have not started.
