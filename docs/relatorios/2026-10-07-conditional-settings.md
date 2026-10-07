# Escrita condicional dos settings sandbox

Frente: YC-203.6/203.5 parcial. Data: 2026-10-07.

A ativação e a recuperação podiam sobrescrever uma alteração externa feita depois
da consulta. A reprodução inseriu a mudança durante a gravação da intenção: a
ativação instalava o proxy e reiniciava; a recuperação restaurava o baseline e
liberava a reserva. O adaptador recebia apenas o alvo da escrita.

O coordenador agora chama `setting(key, target, *, expected)`. Na ativação, `expected`
é o setting original completo. Na recuperação, é o setting aplicado registrado no
diário. O adaptador confiável deve comparar e escrever indivisivelmente, recusando
divergência sem alterar o estado. Não há fallback para chamada incondicional nem
consulta adicional apresentada como atomicidade.

O diário já contém `before`/`after`; nenhum schema, campo nativo, módulo ou dependência
foi criado. V2/v3/v4 continuam legíveis. `Recovery.setting` e `restart` permanecem
bloqueados por `native_egress_contract_unverified`: ainda não há implementação atômica
comprovada no sbx local. Dez hashes de conteúdo do catálogo foram atualizados;
contratos e permissões permanecem iguais.

## Provas

Cinco regressões falharam antes da correção: mudanças após intenção de ativação e
restauração, mudança de metadado com valor igual e adaptadores incondicionais nos
dois caminhos. A execução seguinte passou nos 28 testes de rede, incluindo o
percurso local A/B/A2 v4, recuperação, resposta perdida e intenção consumida.

A fixture simula a operação atômica no armazenamento; controlador e ledger são reais.
As regressões conferem o estado externo preservado, ausência de escrita/reinício
e reserva ainda bloqueada. Elas não comprovam CAS no daemon nativo. A revisão
independente não encontrou achados bloqueantes e reproduziu dez testes focados.
Suíte pública: **612 testes, 592 aprovados e 20 pulados**, sem falhas/erros em
251.364 s. Os pulados exigem Windows nativo ou grupo secundário POSIX ausente. Código,
testes, setup e catálogo coincidem com a árvore testada; depois dela mudaram somente
documentos. Contagens, árvore pública e hashes estão na [medição](../medicoes/2026-10-07-conditional-settings.json).

Nenhum Docker, sbx, login, modelo ou novo ciclo nativo foi executado. O contador
permanece **2/3**, `proof_accepted=false`, B `blocked_unattributed` e perfis vazios.
O ambiente cloud já dispõe do Python necessário; nenhuma configuração adicional
foi necessária.

## Pesquisa nativa encerrada nesta rodada

Novas fontes oficiais, na revisão Docker Docs
`7ba25eeb0c4c594f79e6efadad1af5eaca0500a8`, não estabeleceram a compatibilidade local:

- O [guia da API](https://github.com/docker/docs/blob/7ba25eeb0c4c594f79e6efadad1af5eaca0500a8/content/manuals/ai/sandboxes-api/_index.md)
  define criação e gestão de recursos Cloud.
- Os [conceitos de endpoints](https://github.com/docker/docs/blob/7ba25eeb0c4c594f79e6efadad1af5eaca0500a8/content/manuals/ai/sandboxes-api/concepts.md)
  separam management Cloud de processos/arquivos no endpoint de cada sandbox.
- [`daemon start`](https://github.com/docker/docs/blob/7ba25eeb0c4c594f79e6efadad1af5eaca0500a8/data/sbx_cli/sbx_daemon_start.yaml)
  e [`daemon status`](https://github.com/docker/docs/blob/7ba25eeb0c4c594f79e6efadad1af5eaca0500a8/data/sbx_cli/sbx_daemon_status.yaml)
  não documentam transporte nem precondição aplicáveis à API local de secrets.
- As [notas da versão 0.46.0](https://github.com/docker/docs/blob/7ba25eeb0c4c594f79e6efadad1af5eaca0500a8/content/manuals/ai/sandboxes/release-notes.md)
  e o [release publicado](https://github.com/docker/sbx-releases/releases/tag/v0.46.0)
  registram que falhas de revogação em sandboxes ativos podem ser repetidas depois
  da exclusão do store. A ausência no store não basta para certificar revogação.

A [pesquisa anterior](2026-10-07-injection-proof.md) comprovou que a API Cloud documenta
identidade/versão e remoção condicionada. Falta uma referência aplicável ao endpoint e
store local 0.46.0, incluindo rotação, remoção atômica recusando versão antiga e
revogação observável. Também falta comprovar escrita condicional dos settings locais.
Fontes foram lidas diretamente e preservadas com hashes; conversão Docling continua
pendente por `runtime_missing` em recibo privado.

O adaptador nativo está **bloqueado por contrato externo**. A próxima ação é obter do
fornecedor essa referência aplicável; nenhum contato foi enviado. Não repetir as
mesmas buscas sem evidência nova nem criar outro roteiro experimental. Isso não
demonstra impossibilidade do sbx, apenas insuficiência da evidência disponível.

## Publicação e retorno

Código publicado em `2f4e47a12ba9879aa4448c53b571de282e6fc934`; branch e ref do PR conferidas.
Destino autorizado: `feat/isolated-executor`, [PR #24](https://github.com/Matheusrpc/YoungCrowHarness/pull/24).
Base: `bdcf766`; main permanece em `932b775`. A medição registra a publicação observada.
CI continua não verificado nesta sessão. Recibos e fontes brutas ficam fora do Git.

Retorno por revert na branch, mantendo efeitos nativos bloqueados e recuperando
registros pendentes com a versão corrigida antes do retorno. O código anterior
reintroduz a janela de sobrescrita; não deve ser habilitado para mutações. Não apagar
o ledger nem reabrir intenções consumidas.

## English overview

Activation and recovery now pass the full expected setting to a mandatory conditional
write. The trusted adapter must compare and write indivisibly. Local tests preserve
external changes made after durable intent, avoid restart and keep recovery reserved;
legacy adapters receive no unconditional fallback. The native adapter still refuses
effects because local atomic support is unproven. Additional official sources did not
connect the Cloud API contract to local sbx 0.46.0. An applicable vendor contract is
required before native implementation. No Docker, models or native cycles were run.

ATRASO: main 1 frente sem aceite | PR #24 0 incrementos pendentes de publicação | aceite nativo pendente.
