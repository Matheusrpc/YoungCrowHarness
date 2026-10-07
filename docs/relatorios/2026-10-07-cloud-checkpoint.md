# Checkpoint para continuidade na cloud

Frente: publicar o progresso do executor isolado na branch `feat/isolated-executor`.

O mantenedor autorizou enviar código, testes e relatórios para continuar o desenvolvimento
em outro ambiente. Este checkpoint parte de `932b775c385b8ab9d7ff7819e00ffcc9f3f20c95`
e mantém o executor em desenvolvimento. Não é uma release nem aprovação para executar modelos.

## Conteúdo e revisão

O conjunto inclui diagnóstico compartilhado, seleção de ambiente, guardian, launcher, relay,
reserva por conta, filtro de destino, testes, planos, medições e histórico de resultados.
O [handoff](../HANDOFF-CLOUD-2026-10-07.md) registra o backlog e o ponto de retomada.

Dois revisores trabalharam em leitura: um verificou o pacote e suas dependências; outro examinou
os JSONs/relatórios novos para publicação. Não identificaram credenciais reais nesses documentos.
Isso não é uma auditoria completa de segredos do histórico do repositório.

Ficam fora do commit `.operacao-local/`, `vault/local/`, os recibos experimentais de `.superpowers/`,
ambientes `.runtime/`, caches `%SystemDrive%/`, fixtures `docs/medicoes/setup-audit-*/` e três
arquivos históricos locais: `reproduce_setup.py`, `tracked-files.txt` e `github-metadata.json`.
As exclusões preservam os arquivos no disco. `setup-results.json` é evidência da revisão inicial,
vinculada ao commit antigo registrado no próprio JSON.

## Correções necessárias para empacotar o progresso

1. O Dockerfile copia `relay.py`, mas o `.dockerignore` o excluía do contexto. Uma regressão
   estática reproduziu a falha nessa origem; a inclusão de `!relay.py` corrigiu o contrato.
   Isso não substitui construir e provar a imagem nativa. Os arquivos do runtime usam LF
   por `.gitattributes`, mantendo seus bytes entre checkouts Windows/Linux.
2. Cinco entradas do catálogo tinham hashes antigos. O teste existente de catálogo reproduziu
   a divergência. Os helpers `mission_sbx.py`, `mission_execution.py` e `mission_egress.py`
   agora fazem parte das identidades das skills relacionadas. Os hashes foram recalculados
   pelas funções existentes de `capabilities.py`, preservando metadados e permissões.

Não houve ampliação de permissões ou preenchimento dos registros de perfis aprovados.
Atualizar um hash de catálogo registra identidade; não autoriza uso nem prova execução.

## Verificação local desta publicação

| Verificação | Resultado |
|---|---|
| Regressão do contexto Docker antes da correção | 1 teste falhou, especificamente por `relay.py` excluído |
| Executor, relay, armazenamento e dois casos de setup | 127 testes passaram, zero falhas/skips, 82,528 s |
| Catálogo antes da atualização | Teste de identidade das skills de missão falhou por hash divergente |
| Suíte `test_capabilities.py` após a atualização | 23 testes: 22 passaram, 1 skip por symlink indisponível no host; 21,406 s |
| Catálogo completo | Nenhuma divergência entre contratos, arquivos e hashes declarados |
| Sintaxe e estrutura | Python e JSON selecionados válidos; Bash do setup válido; vault com 407 notas e zero problemas |
| Seleção para o commit | 125 arquivos revisados, sem ocorrência nos padrões pesquisados de tokens e chaves privadas; resíduos excluídos |

Comando da suíte focada, na raiz do checkout original:

```powershell
$env:RUNNER_TEMP = 'C:/Users/rmfon'
$env:YC_NATIVE_RESERVATION = '1'
$env:PYTHONPATH = 'C:/Users/rmfon/YoungCrowHarness-review-20261001/tests'
C:/Python314/python.exe -X utf8 -B tests/windows_fixture_runner.py -m unittest test_mission_execution test_mission_egress test_mission_sbx test_mission_sandbox test_mission_guardian test_mission_launcher test_mission_relay test_execution_storage_diagnostics test_setup.SetupTests.test_sandbox_environment_installs_without_activating_runtime test_setup.SetupTests.test_runtime_helpers_preserve_existing_install -v
C:/Python314/python.exe -B -m unittest discover -s tests -p test_capabilities.py -v
```

As provas usam fixtures, sockets locais e respostas simuladas; uma fixture verifica permissões
Windows reais em armazenamento descartável. Não houve comando Docker, chamada a modelo, mudança
de rede global, credencial real ou GET externo nesta preparação. Os dois casos de setup passaram
antes da atualização dos hashes do catálogo; a suíte de capacidades passou depois dela.

A suíte geral atual continua sem aceite completo. Os resultados históricos de 43 e 74 testes
mantêm seus escopos e não são somados ao resultado desta publicação. O CI do GitHub tem seu
próprio resultado, a consultar no commit publicado; um push não significa CI aprovado.

## O que continua pendente

Implementar o controlador durável que une reserva, launcher, rede e recuperação; reconstruir
o pacote; obter A/B/A2 com restauração no digest resultante; provar Claude Code e Codex por
assinatura; validar adoção e interrupção. `NATIVE_PROFILES` e `REVIEWED_PROFILES` permanecem vazios.
O limite da consolidação continua em dois ciclos utilizados de três. Esta publicação não realizou
outra tentativa nativa nem reiniciou esse contador.

Cloud de desenvolvimento e runner validado são condições distintas. O clone permite continuar
o trabalho de código; não transfere VMs, autenticação, permissões Windows ou recibos operacionais.
Consulte a seção de transferência do handoff antes de executar o runtime em outro host.

ATRASO: main 1
