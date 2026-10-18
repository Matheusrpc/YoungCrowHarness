# Ferramentas isoladas: entrega parcial

> Registro histórico recuperado em 17/out/2026. Os números abaixo pertencem à sessão
> original. Os arquivos JSON daquela sessão não foram recuperados; veja as
> [provas atuais e os limites da recuperação](2026-10-17-codex-workspace.md).

Frente: YC-203. O worker OCI executa edição e verificação da fixture `clamp-v1`,
exporta um snapshot após encerrar e cumpre o prazo mesmo quando o controlador morre.
Os dois aceites por assinatura continuam pendentes. Nenhum perfil foi qualificado;
`worker-check` recusa o despacho e a fila mantém `runtime_available=false`.

`2026-10-12-tool-client-acceptance.json` (registro original indisponível) ·
[Uso e reprodução](../USAGE.md#worker-oci-experimental--experimental-oci-worker) ·
[Desenho aprovado recuperado](../superpowers/specs/2026-10-12-isolated-tools-design.md)

## Código entregue

O driver usa o socket Docker local explicitamente, imagem por digest, entrada limitada
e UID 1000 para ferramentas. O contêiner não recebe rede, credenciais, montagem do
projeto ou socket Docker. O kernel é compartilhado com o host. O guardian é PID 1;
seu prazo absoluto não depende da sobrevivência do cliente ou controlador.

A saída passa por um snapshot protegido. O teste fixo roda como UID 2000 e interpreta
somente uma função `clamp` com expressão pura limitada. Não importa o módulo editado.
O resultado é mantido fora do projeto, com hashes e diff; não é aplicado ao original.
Esse teste não representa um executor geral de testes de projetos.

Os perfis fixam Codex 0.159.2 e Claude Code 2.1.296, com SHA-256 dos binários oficiais.
O coordenador integra UUID, limites, reserva global compartilhada, recibo SQLite e
recuperação por observações do Engine. Repetição não inicia outra execução. Falha de
identidade ou encerramento inconclusivo mantém a reserva. A instalação distribui os
helpers e preserva adaptadores e autenticação existentes, inclusive com `--force`.

## Provas realizadas

| Prova | Resultado e alcance |
|---|---|
| Docker 28.4.0, Linux x86_64 | Edição de `clamp.py`, três casos aprovados, snapshot conferido e original intacto |
| Fronteiras do worker | Rede, caminhos privados, escrita na imagem/snapshot e sinal ao guardian recusados; limites de PIDs e tmpfs exercitados |
| Morte do controlador | SIGKILL real; descendant do worker encerrado antes do prazo; zero processos restantes |
| Recibo forjado pelo candidato | Falhou antes da correção; após a correção, `print` + `os._exit(0)` recusados sem publicar resultado |
| Codex exec-server | RPC nativo dentro do worker passou, sem modelo; não qualifica o agente completo |
| MCP do worker | Inicialização, catálogo e comando reais passaram; não qualifica rotas tardias do Claude |
| SDK Claude | Inicialização do cliente oficial passou sem turno de modelo; não comprova login ou execução por assinatura |
| Testes direcionados | 69 passaram: worker, perfis, recibos e catálogo |
| Exportação dos arquivos do commit | 133 testes: 131 passaram, 2 ignorados; inclui instalação, sem as alterações anteriores do checkout |
| Adoção | Projeto novo, Git com alterações e interrupção: retorno preservado e perfil do usuário intacto; zero chamadas a modelos |
| Missões em consumidores descartáveis | Instalação nova/existente, replay, recuperação e retorno passaram com fixtures; zero chamadas a modelos |

A imagem após revisão é
`sha256:7932ee20a5a51886efdc4196a9d221dcecb6d335b3b04d53d08a1a898a5b1cb2`.
Os hashes dos helpers, binários e resultados estão na medição. Os testes de ledger
substituem efeitos externos e observações de seleção por fixtures declaradas. Não
constituem prova de assinatura. O contador sbx permanece 2/3; P06 não foi repetido.

A suíte geral do checkout rodou 837 testes: **797 passaram, 20 foram ignorados e
20 terminaram com erro** em `test_pilot_claude`. A causa anterior a esta frente foi
reproduzida: a nota U01 `filter-url.md` referencia seis arquivos externos ao vault,
mas `make_context` copia somente o vault e as skills. O contexto fica com seis links
quebrados; os testes param no `setUp`. Esses arquivos e o piloto foram preservados.
As oito falhas de catálogo encontradas na primeira rodada foram corrigidas nesta frente.
Não se declara a suíte geral aprovada.
Os mesmos 20 testes do piloto passaram na exportação dos arquivos do commit, sem a
alteração U01 anterior. A fixture recebeu metadados Git temporários porque um teste
exige `HEAD`; nenhuma campanha nativa P06 ou chamada de fornecedor foi iniciada.

O rascunho de `start_skill` recebeu instruções opcionais para build e provas Docker,
preservando as instruções existentes. O salvamento foi confirmado. Para reutilizar
essa configuração, revisar e salvar nas configurações do ambiente e publicar.
Publicação e restauração em nova tarefa não foram realizadas nesta rodada.

## Bloqueios dos clientes

**Codex completo:** o ensaio com cliente oficial e servidor local de respostas
determinísticas encontrou `Operation not permitted (os error 1)` ao iniciar
`exec-server`. O cliente tenta criar outro grupo de processos; o supervisor atual
proíbe essa operação para manter a árvore sob controle. O catálogo ficou sem as
ferramentas de edição e as chamadas foram recusadas. Mesmo assim, o cliente terminou
com código zero. Por isso o código de saída sozinho não aprova uma tarefa.

**Observação de seleção:** Codex `exec --json` não publica modelo nem esforço aplicado.
O fluxo headless `print stream-json` do Claude publica modelo, mas não o esforço.
O parser conserva essas ausências, e o coordenador recusa seleção ausente ou divergente.
Nenhum valor solicitado é apresentado como observado.

**Claude completo:** ferramentas tardias, reconexão e ausência de execução no host
ainda precisam de prova. A inicialização observada não tinha token de assinatura.
O controle nativo `get_settings` pode fornecer modelo/esforço aplicado, mas essa rota
não foi exercitada. Sua resposta completa contém configurações e não deve ser gravada;
uma integração deve selecionar somente os dois campos necessários.

Fontes: tipos e conversão do Codex no commit
[`ff6aec9`](https://github.com/openai/codex/blob/ff6aec96948b70d94983af2641a6b67c94faeff5/codex-rs/exec/src/exec_events.rs),
incluindo o [conversor JSONL](https://github.com/openai/codex/blob/ff6aec96948b70d94983af2641a6b67c94faeff5/codex-rs/exec/src/event_processor_with_jsonl_output.rs).
O schema e emissor headless do Claude foram conferidos no binário oficial 2.1.296;
manifesto assinado e SHA-256 foram verificados antes do uso.

## Revisão e decisões

Uma revisão independente encontrou três problemas importantes: aprovação forjada
pelo módulo importado, reserva sem recibo após limite excedido e sucesso sem conferir
seleção/protocolo do cliente. Foram reproduzidos e corrigidos em uma rodada. O teste
de troca de diretório também foi corrigido: agora exige que a troca aconteça e verifica
que nenhum arquivo externo foi aberto. Esse achado foi elevado de menor para
importante porque invalidava a prova de uma fronteira de segurança.

As escolhas de execução e seus custos foram:

- Manter o checkout existente e um ledger local ignorado: preserva o trabalho anterior;
  exige registrar manualmente os estados do plano.
- Separar o envelope do worker dos vínculos de missão: o coordenador valida ambos.
- Usar cache Buildx privado preservando proxy, CA e configuração Docker: evita escrever
  no cache global indisponível.
- Trocar `docker cp` por helpers fixos de importação/exportação: neste Engine, `cp`
  recusou escrita no tmpfs sob raiz somente leitura e leu a camada da imagem na exportação.
  Os helpers passam a integrar a imagem confiável; somente a importação do snapshot usa UID 0.
- Normalizar `OomKillDisable=false/null` após validar o mesmo efeito: outra versão do
  Engine exige nova prova; demais propriedades continuam vinculadas por hash.
- Espelhar um cwd vazio do controle por alias dentro do worker, sem bind mount: permite
  o protocolo do exec-server; o ciclo de vida desse diretório precisa ser mantido.
- Aceitar somente defaults de catálogo de plugins do sistema Codex, com plugins
  desligados conforme fonte oficial: outras configurações gerenciadas continuam recusadas.
- Restringir a fixture a expressão pura e manter `QUALIFIED` vazio: reduz o que esta
  entrega pode executar; preserva a distinção entre transporte, cliente e assinatura.

## Próximo corte

Implementar uma supervisão confiável compatível com os grupos de processos dos clientes,
mantendo encerramento da árvore e prazo após queda. Em seguida, usar observações nativas
de modelo/esforço e provar todas as rotas expostas, incluindo ferramentas tardias e
perda de transporte. Só depois cabem os dois aceites por assinatura já previstos no plano.
Login adicional sozinho não resolve os bloqueios atuais.

## English

The OCI worker, bounded snapshot, fixed pure-expression check, crash deadline and
durable receipt machinery are implemented. Native Docker, Codex exec-server and worker
MCP transport checks passed without model calls. Full subscription checks remain
blocked by Codex process-group containment, missing applied-selection observations and
unverified complete Claude routing. No client profile is promoted. The next step is
compatible trusted supervision and native selection/routing evidence before acceptance.
