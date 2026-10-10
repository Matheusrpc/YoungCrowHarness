# Execução local e runner dedicado

Frente: executor isolado. Decisão de produto registrada em 2026-10-05.

O mantenedor confirmou manter as duas opções após discutir a adoção pelo VS Code:
“deixa as duas opções então pode ser?”. A execução local será o padrão; um runner
dedicado será opcional. Este registro define o escopo para o desenho técnico seguinte.
Os dois destinos ainda dependem de implementação e provas de execução.

## Experiência prevista

| Destino | Como será usado | Condição de uso |
|---|---|---|
| Local, padrão | Abrir o projeto no VS Code, executar o setup, escolher Claude Code ou Codex e personalizar o projeto. O executor roda na mesma máquina | A máquina precisa estar disponível e o perfil de execução precisa passar nas verificações |
| Runner dedicado, opcional | Trabalhar no VS Code e executar a missão em outra máquina ou servidor escolhido pelo usuário | O runner precisa ser preparado, autenticado e validado; conexão e transferência têm de preservar o responsável pela missão |

Agentes, backlog, skills, controles de MCP, referências do vault, QA e critérios de
release pertencem à mesma esteira. A escolha de destino não altera DoR/DoD, limites de
três PBIs/três agentes, até três ciclos de correção ou os gates de produção.
Os dois destinos devem atender Claude Code e Codex; nenhuma combinação será anunciada
como funcional antes de sua prova específica.

Dev Container pode padronizar as dependências de desenvolvimento como recurso opcional.
Ele não substitui a prova de isolamento do executor. Uso supervisionado também não
substitui o objetivo aprovado de uma esteira autônoma.

## Encaixe no backlog

- YC-203 / 2A-R1 a R3: concluir ambiente, execução/recuperação e adoção autenticada.
  A execução local mantém a prioridade de adoção. Cada perfil exige provas próprias.
- YC-208 e YC-209: aproveitar o pacote privado e a transferência local/servidor já
  previstos. Transferir exige pausa, um único responsável e exclusão de credenciais;
  o destino autentica seus próprios clientes.
- O [desenho técnico aprovado](2026-10-05-execution-setup-design.md) detalha seleção,
  pré-requisitos, diagnóstico e acesso ao runner. Próxima atividade: revisar o
  [plano](../plans/2026-10-05-execution-setup.md). A máquina de teste remoto ainda não foi escolhida.

## Estado e limites

O [ciclo anterior](../../relatorios/2026-10-05-exclusive-egress-proof.md) está encerrado,
sem recuperação pendente e com resultado de rede inconclusivo. Seus recibos e bloqueios
permanecem preservados. Manter duas opções no produto não reabre o ensaio v2 nem
autoriza uma v3, contratação, provisionamento ou migração de dados e credenciais.

R1 continua parcial; R2/R3 não começaram e os perfis de execução permanecem bloqueados.
Esta decisão não comprova que outro sistema operacional resolverá o timeout observado.

## English overview

The product will offer two execution locations: local execution as the default for
VS Code users, and an optional dedicated machine or server. Both belong to the same
pipeline and must support Claude Code and Codex under the same QA, memory and safety
requirements. Availability still depends on implementation and per-profile evidence.

Reuse YC-203 for executor validation and YC-208/209 for private transfer and ownership.
An optional Dev Container can standardize development dependencies; it does not certify
executor isolation. The [technical setup design](2026-10-05-execution-setup-design.md#english-overview)
is approved and its implementation plan awaits review. No machine has been selected or provisioned. The previous
probe remains closed, with no recovery pending and no product execution profile enabled.
