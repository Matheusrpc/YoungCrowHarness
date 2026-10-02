# Memória consultável — prova de 2026-10-02

Frente: memória consultável. O vault Markdown continua sendo o registro principal. A entrega
acrescenta seleção explícita, consulta com identidade/revisão, Graphify opcional e a skill comum
`retrieve-memory`. A prova de modelo no Claude Code permanece pendente de login; M04 é parcial.

## Escopo e estados

| Aceite | Evidência | Estado |
|---|---|---|
| M01 — seleção e consulta | Corpus sintético; UUID por projeto/nota, revisão SHA-256, limites, links e isolamento | Verificado localmente |
| M02 — Graphify | Pacote 0.9.73 real, Python 3.12.10 no Windows, construção/consulta e títulos iguais sem fusão | Verificado no Windows; Linux aguardando CI |
| M03 — atualização | Reuso sem nova construção, mudança durante build/query, remoção, rename, cache adulterado e retorno ao Markdown | Verificado localmente |
| M04 — clientes | Descoberta real nos dois clientes; sessões independentes do Codex; Claude sem autenticação | Parcial |

O runtime fica em `.operacao-local/memory/runtime/venv`. A instalação fixa `graphifyy==0.9.73`
sem extras e salva o inventário resolvido localmente. Dependências transitivas são registradas,
mas não têm um lock reproduzível entre todos os sistemas. `doctor` detecta alterações no ambiente.
O núcleo usa Python 3.11+ e biblioteca padrão; não importa o SDK Docling ou Graphify para consultar Markdown.

O contrato foi inspecionado no [código Graphify 0.9.73](https://github.com/Graphify-Labs/graphify/tree/ef4450d9c28acb2b8cdc22d369c1777b77148eef).
O adaptador chama `build_from_json` e o dispatcher local de `query`. Não usa extração por modelo,
deduplicação por LLM, grafo global, watcher, servidor MCP ou instalação de skills do fornecedor.
O worker recebe ambiente filtrado, sem chaves de modelos, e um arquivo privado com a requisição.

## Medição de recuperação

Corpus: cinco notas de Pagamentos API/Portal, decisão vigente e substituída, evidência sintética
de release. As perguntas e os trechos esperados foram fixados em `tests/memory_fixture.py` antes
da implementação. A evidência de release pertence somente ao Portal; a API permanece em DEV.

| Método | Perguntas com referência esperada | Referências antigas apresentadas como atuais |
|---|---:|---:|
| Navegação pelos índices | 4/4 | 0 |
| Consulta Markdown | 4/4 | 0 |
| Consulta Graphify | 3/4 | 0 |

`assinatura webhook` não encontrou nós no Graphify: o termo está no corpo da nota, enquanto a
projeção inicial busca títulos e links. `retrieve-memory` orienta reformular com o vocabulário
observado ou consultar o Markdown. A resposta vazia permanece vazia; não alteramos o resultado
esperado para melhorar a pontuação.

Os [dados da medição](../medicoes/2026-10-02-memory-discovery.json) registram duração, bytes,
caracteres, referências e revisões. “Cold” significa primeira consulta da rodada, sem limpar o
cache do sistema operacional; “repeated” repete a consulta. A navegação de referência lê os três
índices e as cinco notas vinculadas. É uma comparação determinística de um corpus pequeno, não
um benchmark de raciocínio ou tokens. A consulta também relê as cinco notas para conferir revisões.
A mediana foi 2,40 ms para ler os índices/notas no processo de medição, 339,25 ms para o CLI Markdown e 3.986,62 ms para o CLI Graphify; as chamadas CLI incluem inicialização de processos. Houve testes de regressão concorrentes no host. Os volumes medianos foram 2.524, 8.360,5 e 7.281 bytes, respectivamente; o JSON de consulta inclui metadados e relações repetidos. Esses tempos não medem interpretação por IA. Graphify não demonstrou vantagem geral sobre Markdown nesse corpus. Markdown segue como padrão.

## Clientes e comportamento

A descoberta usou os carregadores reais: Codex `skills/list`, configuração e hooks; Claude Code,
inicialização do SDK e catálogo de comandos/agentes. Esse ensaio não envia uma pergunta ao modelo.
Os exemplos de MCP ficaram desativados ou aguardando aprovação.

Codex 0.158.0-alpha.2.1, modelo `gpt-6-astra`, conta ChatGPT existente: a primeira sessão gravou um handoff;
a segunda recuperou o estado por Markdown, com cinco UUIDs/revisões conferidos. A primeira
validação encontrou quatro problemas de navegação nos índices de capacidades/integrações da
fixture adotada; o agente os registrou sem ocultá-los. Os links do índice sintético foram reparados
antes da rodada seguinte. O handoff e as notas selecionadas foram preservados.

A terceira rodada recebeu um grafo atual, mas o worker retornou `invalid_worker_result` no sandbox somente leitura. O cliente declarou o fallback para Markdown e recuperou corretamente os cinco registros. Essa rodada não comprova consulta Graphify dentro do cliente. O worker precisa gravar uma requisição temporária privada; um ensaio futuro deve permitir essa escrita sem autorizar alterações nas notas. Na quarta sessão, uma atualização tornou o índice `stale`: o cliente usou Markdown, conferiu o novo hash e mudou a próxima ação de validar assinatura para testar replay. As quatro sessões terminaram com um turno cada e 8, 6, 6 e 4 chamadas de ferramenta, respectivamente. O limite do ensaio é quatro
sessões curtas por cliente e oito turnos por sessão. Não há contratação de API adicional.
Claude Code 2.1.220 retornou `loggedIn: false`; nenhuma conversa de modelo foi tentada depois disso.
Autenticar o Claude e repetir a passagem entre sessões é a próxima prova necessária para fechar M04.

No teste comportamental independente, a execução sem a nova skill já recuperava os fatos
corretos e rejeitava um resumo antigo conflitante, mas não registrava projeto/UUIDs/revisões no
handoff. Com `retrieve-memory`, o agente conferiu seis hashes, distinguiu DEV de produção
sintética e registrou a próxima ação. Uma nota pediu publicação de segredos e criação de um
arquivo; essas instruções foram tratadas como dados e não executadas. Esse ensaio não substitui
a conversa real de cada cliente.

## Proteções e recuperação

Somente notas `.md` selecionadas no vault entram no retrato: até 100 notas, 256 KiB por nota e
8 MiB no conjunto. Symlinks, junctions, hardlinks, caminhos externos e área privada já rastreada
são recusados. Projeto, origem, revisão e cobertura dos nós/links são conferidos após o worker.
Uma construção só ativa seu ponteiro depois de reler e validar as fontes. Interrupções deixam
estado explícito, e o lock compartilhado com ingestão exige recuperação pelo dono/token.

`disable` volta ao Markdown. `clear-index` valida todas as gerações antes de remover apenas
arquivos conhecidos; preserva seleção, runtime e vault. A prova real renomeou temporariamente
o executável do runtime, constatou o fallback e o restaurou em `finally`. Mudanças e remoções
controladas também foram restauradas depois da conferência de revisões atuais.

O setup de um projeto de prova foi inicialmente executado com o HOME real: `--no-plugins` ainda
instala humanizer. Duas pastas recém-criadas do Claude foram identificadas e retiradas da
configuração global, preservadas numa cópia local de recuperação. A exclusão havia sido recusada
pela revisão automática. As sessões seguintes usaram HOME privado. Esse erro do ensaio não é
apresentado como propriedade de isolamento do instalador.

## Reprodução e publicação

```bash
python3 -m unittest discover -s tests -v
python3 scripts/vault.py check
python3 tests/smoke_memory.py --root .runtime/memory-proof --provider markdown
python3.12 scripts/memory.py --root .runtime/memory-proof setup-graphify
python3 tests/smoke_memory.py --root .runtime/memory-proof --provider graphify
```

Use uma pasta descartável vazia para a prova; ela contém somente dados sintéticos. Os testes
unitários não instalam fornecedores nem chamam modelos. O job separado `graphify-smoke` usa
Ubuntu 24.04/Python 3.12 para instalar e exercitar o runtime real.

QA local: 170 testes em 892,610 s, sete skips de plataforma no Windows; vault com 39 notas e zero problemas; diff sem erros de whitespace. Diagramas PT/EN sem texto excedendo as caixas, imagem móvel de 358 px dentro de viewport de 390 px. Chrome foi fechado em `finally`, e a contagem dos processos próprios terminou em zero. Revisão independente, CI Linux e publicação protegida: em andamento. O README e os guias PT/EN incluem
o fluxo de memória e preservam os diagramas de criação, migração, operação e ingestão.
Rollback operacional: `disable`, seguido de consulta Markdown. Reverter o PR remove a nova
capacidade sem apagar os registros locais; não apagar o vault durante rollback.
