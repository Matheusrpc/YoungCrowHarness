# Setup local e dedicado

Frente: executor isolado / YC-203. Setup validado localmente; publicação pendente.

O setup passou a registrar onde o usuário pretende trabalhar: máquina local ou host
dedicado aberto pelo VS Code Remote SSH. A preferência é privada, fica fora do Git e
é preservada na reinstalação. O diagnóstico informa a etapa que falhou e seus limites.
O Personalizer consulta as respostas anteriores e inclui um guia instalado em PT/EN.

O [plano de três PBIs](../superpowers/plans/2026-10-05-execution-setup.md) foi confirmado
pelo mantenedor. Esta entrega prepara o uso nos dois destinos. R1 continua parcial:
nenhum perfil de execução foi certificado e nenhum agente autônomo foi habilitado.

## Comportamento entregue

| Interface | Resultado |
|---|---|
| `setup.sh --execution-location local\|dedicated` | Registra a escolha depois do baseline do trial; recusa conflito antes de copiar arquivos |
| `missions.py environment show --json` | Consulta sem escrever; ausência retorna `local/default` |
| `missions.py environment configure --location … --expected-digest … --json` | Compara digest sob lock; conserva data e bytes quando a escolha não muda |
| `missions.py client environment … --json` | Informa seleção e fases, com horário, duração, limite e motivo sanitizado |
| Personalizer | Reutiliza escolha e respostas existentes; orienta adoção e diagnóstico no host aberto |

As consultas externas conservam 30 segundos e 8 MiB de limite. Um timeout não demonstra
isolamento de rede. Helpers incompatíveis são recusados antes da consulta e permanecem
preservados para comparação e mesclagem pelo usuário.

A adoção aceita a área privada de execução apenas na inspeção do projeto já instalado.
A captura inicial mantém suas regras estritas, e diretórios privados sem relação com
essa área continuam recusados. Um runner de restauração antigo permanece imutável;
reinstalação com contrato de recuperação diferente retorna `incompatible_recovery_runner`.

## Provas observadas

Windows, Python 3.14 e Git Bash; apenas projetos e executáveis sintéticos. As
[medições](../medicoes/execution-setup.json) guardam revisão, hashes e resultados.

| Origem | Cliente | Preferência | Reinstalação preservada | Restauração |
|---|---|---|---|---|
| Projeto novo | Claude | local | Passou | Passou |
| Migração com Git sujo | Claude | local | Passou | Passou |
| Projeto novo | Claude | dedicated | Passou | Passou |
| Migração com Git sujo | Claude | dedicated | Passou | Passou |
| Projeto novo | Codex | local | Passou | Passou |
| Migração com Git sujo | Codex | local | Passou | Passou |
| Projeto novo | Codex | dedicated | Passou | Passou |
| Migração com Git sujo | Codex | dedicated | Passou | Passou |

Nos oito casos, a consulta foi somente leitura, `--force` preservou a escolha e seu
timestamp, o perfil global permaneceu igual e o trabalho do trial foi guardado. Nas
migrações, configuração de agentes, nota humana e recibo conservaram seus hashes.
`dedicated` prova somente a seleção e a adoção instalada: não houve conexão SSH real.

A revisão independente encontrou uma falha de compatibilidade: a CLI aceitava uma
função de diagnóstico antiga que não devolvia seleção ou fases. Uma fixture com a
função legada real reproduziu o erro. A CLI agora verifica a versão do contrato antes
de chamá-la. A regressão e os testes relacionados passaram: 22 testes em 17,154 segundos.

Os resultados finais cobrem os 414 testes descobertos em 23 módulos: 403 passaram e
11 foram ignorados por requisitos de ambiente. A consolidação conferiu cada identificador
de teste, incluindo a substituição do módulo guardian descrita abaixo. Os skips exigem
POSIX/Linux ou privilégio de symlink indisponível neste Windows.
Foram preservados os logs das tentativas anteriores: falha de ACL na reinstalação,
fixture com caminho longo, catálogo com hashes antigos e corrida que carregou arquivos durante a implementação.
Essas tentativas servem para diagnóstico; não entram na contagem de aprovação.

O grupo de missões expôs uma instabilidade no teste de mensagens inválidas do guardian:
quinze casos compartilhavam um único prazo real de cinco segundos. A simulação de atrasos
reproduziu `invalid_deadline` antes da asserção de parsing. O relógio foi fixado somente
nessa fixture; os testes específicos de prazo continuam separados e o código nativo
permanece igual. Os quatorze testes do módulo passaram após a correção. Seu resultado
substitui o módulo anterior na contagem final; os erros iniciais ficam registrados.

O catálogo recebeu o helper, suas dependências e o guia instalado nas cinco skills
afetadas. Apenas arquivos declarados e hashes mudaram; permissões e configurações
nativas foram preservadas. Os 23 testes do catálogo passaram, com um skip por falta de
privilégio para criar symlink. A regressão final divide todos os 23 módulos de teste
em quatro processos, cada qual com sua própria raiz temporária privada.

## Cobertura do contrato

| Risco | Verificação |
|---|---|
| Dois configuradores perderem a escolha anterior | Processos concorrentes com o mesmo digest; um vencedor e recusa do concorrente |
| Queda deixar a preferência permanentemente travada | Morte do processo libera o lock do sistema operacional |
| Preferência sair da área privada ou entrar no Git | Recusa de hardlink/junction, arquivo tracked e regra de ignore insuficiente |
| Troca de destino alterar uma missão existente | Configuração de agentes, missões e recibos mantêm seus bytes |
| Timeout esconder qual consulta falhou | Fase de virtualização inconclusiva coexistindo com versão observada; limites preservados |
| Dados privados aparecerem no diagnóstico | Canário no stderr ausente das observações sanitizadas |
| Instalação combinar helpers incompatíveis | Função legada funcional recusada antes da primeira consulta |
| Trial perder o ponto inicial ou o trabalho posterior | Reinstalação idempotente, restauração da árvore inicial e preservação da cópia do trial |

## Limites e próxima entrega

Nenhuma chamada a modelos, credencial real, modificação do Docker ou novo ensaio nativo
ocorreu nesta entrega. Os perfis continuam vazios; guardian e launcher nativos não mudaram.
O README conserva os assets e os diagramas existentes.

O uso real do runner, sua autenticação e o isolamento exigem provas próprias. Uma
sessão de IA seguindo as skills também depende do piloto nativo: a matriz exercitou os
comandos instalados. Fechar o VS Code não garante continuidade em segundo plano.
Transferência de missão e responsável único permanecem em YC-208/209.

A próxima atividade é delimitar a prova pendente de
isolamento/rede de R1 usando o diagnóstico por etapa. O ciclo v2 continua encerrado;
esta entrega não autoriza outra tentativa. A fila com três PBIs simultâneos depende
do aceite dos adaptadores em YC-203.

Os arquivos permanecem na branch `feat/isolated-executor`, sem publicação na main.
Alterações anteriores da frente e as evidências locais foram preservadas.

## Decisões durante a execução

- Os títulos dos PBIs receberam o formato `Task N` exigido pelas ferramentas da skill; o escopo foi mantido. Custo: conferir links de títulos.
- Foi reutilizado o checkout aprovado, com dependências anteriores ainda não publicadas. Custo: separar o incremento na revisão e preservar os arquivos existentes.
- Os testes usaram diretórios privados curtos, fora de Git. Custo: conservar fixtures descartáveis quando necessárias ao diagnóstico.
- Lock ocupado retorna `execution_selection_busy`; digest vencido retorna `execution_selection_conflict`. Custo: o chamador consulta novamente antes de decidir repetir.
- A inspeção de ACL após instalação reconhece somente a área privada de execução. Custo: esse caminho participa da prova de restauração; a captura inicial permanece estrita.
- Runners de restauração antigos permanecem imutáveis e recusam nova instalação incompatível. Custo: sair do trial anterior pelo runner original antes de adotar a nova versão.
- Implementação e verificações independentes se sobrepuseram. Custo: resultados de árvores em alteração foram descartados para aceite; a suíte final usa o código estabilizado.
- Os checkpoints de commit foram adiados porque os arquivos dependem da frente anterior ainda não registrada. Custo: entrega local, sem publicação.
- As regressões sobrepostas dos PBIs foram reunidas na suíte geral final. Custo: conferir seu inventário e não substituir teste ausente por essa consolidação.
- Como HEAD não mudou, a revisão usou diff do working tree, baseline capturado e hashes. Custo: a revisão precisa considerar também as dependências locais anteriores.
- A revisão somente leitura ocorreu enquanto a matriz e a primeira suíte rodavam. Custo: sua correção precisou de regressão RED/GREEN e nova suíte final.
- A fixture do runner antigo recebeu backup mais curto. Custo: comprovar que chega à recusa de compatibilidade; o limite de caminhos do produto não mudou.
- A suíte anterior foi interrompida após a correção da revisão, preservando seu log. Custo: seus resultados não contam como aceite, e suas fixtures podem permanecer para diagnóstico.
- Execução remota, autenticação e isolamento real ficaram fora do aceite deste setup. Custo: cada perfil continua bloqueado até sua própria prova.
- A matriz instalada cobre o contrato das skills sem conversa LLM. Custo: o comportamento em sessão real continua dependente do piloto nativo.
- A revisão deste incremento não certifica a frente anterior de runtime. Custo: R1 permanece parcial.
- O resultado da suíte e da matriz depende da evidência final lida pelo implementador. Custo: o parecer anterior não substitui esses gates.
- As cinco skills afetadas receberam dependências e hashes atualizados no catálogo. Custo: sem essa declaração, a auditoria acusaria alteração ou deixaria um arquivo fora da comparação; permissões permaneceram iguais.
- A suíte final foi dividida em quatro grupos sem módulos repetidos ou omitidos. Custo: qualquer dependência indevida entre grupos pode aparecer como falha; os testes usam raízes privadas independentes.

- O teste de parsing do guardian recebeu relógio fixo, preservando os testes de prazo. Custo: sua aprovação prova validação de mensagens, não cumprimento de prazo real.
- O módulo guardian foi repetido integralmente após a correção da fixture; os demais resultados da partição foram conservados. Custo: os erros anteriores devem pertencer somente ao módulo substituído, e a contagem final precisa cobrir todos os testes.

- Branch e evidências foram preservadas após a validação local. Custo: a entrega ainda não chegou à main, pois há dependências anteriores não publicadas e o plano proíbe push implícito.
- A conclusão dos PBIs usa o inventário consolidado, sem repetir três suítes sobrepostas. Custo: a consolidação deve recusar testes ausentes, duplicados ou falhas fora do módulo corrigido; esses requisitos foram conferidos pelo coletor.

Nenhum achado menor foi adiado pelo revisor. O workspace de evidências permanece guardado,
pois seus arquivos ainda não foram substituídos por registros em commits.

## English overview

Setup stores a private local/dedicated preference, preserves it during reinstallation
and supports reversible adoption. Diagnostics report bounded phases; Personalizer
reuses prior answers and ships a bilingual guide. All eight installed adoption and
restore combinations passed. The legacy-helper finding was reproduced and fixed;
22 focused tests passed. Final regression results cover all 414 discovered tests:
403 passed and 11 environment-dependent cases were skipped. The complete guardian module
passed after a test-only clock correction; its earlier errors remain in the evidence.

No SSH, model calls, native runtime experiments or profile certification occurred.
Dedicated-host execution and authentication require separate evidence. R1 remains
partial, and this work has not been published to main.

ATRASO: main 1
