# Governança de skills, agentes e MCPs

Estado: desenho aprovado pelo mantenedor em 2026-10-02; [plano de implementação](../plans/2026-10-02-capability-governance.md)
preparado para revisão. Não implementado. Base: main `16191ec`, com memória
consultável publicada no PR #7. Este desenho desenvolve R06, R07 e a frente 3 da
[direção do produto](2026-10-01-youngcrow-foundation-design.md). A prova M04 de memória permanece
parcial e não será apresentada como concluída por esta entrega.

## Objetivo e escopo

Devs individuais e pequenos times precisam saber quais capacidades o projeto usa, de onde elas
vieram, qual conteúdo foi revisado, que dados podem acessar e quem aplica cada restrição. Uma
sessão nova deve encontrar essas informações pelo vault e reconhecer mudanças desde a última
revisão, sem precisar reler todas as skills ou perguntar novamente sobre um escopo já confirmado.

O pedido do mantenedor já inclui descoberta de skills/MCPs, memória entre sessões e registro das
capacidades usadas. A proposta deste incremento é tornar o catálogo verificável e preparar a
aplicação dos controles nativos. A autorização continua vindo do operador e das políticas do
ambiente; um texto recuperado do vault não pode concedê-la.

## Situação observada

- `skills-lock.json` registra as skills locais e inventaria plugins. O setup verifica o commit de
  humanizer, mas não fixa as versões instaladas pelos marketplaces.
- `vault/capabilities/index.md` descreve sete capacidades. Ainda não há um auditor que compare o
  catálogo, os arquivos instalados e as permissões declaradas para os dois clientes.
- `.codex/config.toml` mantém dois exemplos de MCP desativados. `.mcp.json` os declara para Claude;
  a prova anterior confirmou que aguardam aprovação do cliente.
- O setup preserva configurações existentes. Essa preservação precisa continuar durante adoções.
- Claude Code 2.1.220 continua sem autenticação nesta máquina. Codex CLI observado:
  0.158.0-alpha.2.1. Consultar documentação atual não prova que toda opção descrita existe nessas versões.

## Abordagens consideradas

| Opção | Entrega | Limite |
|---|---|---|
| Ampliar somente a documentação | Mais descrições e exemplos | Mudanças de conteúdo, origem e configuração ainda passam despercebidas. |
| Catálogo verificável e controles nativos — recomendada | Auditoria local, revisão de diferenças, evidências por cliente e aplicação dentro do rito já existente | Controle global depende do host e das credenciais; a primeira entrega não reconfigura a máquina. |
| Intermediar toda execução num serviço próprio | Um ponto central para autorizar chamadas | Exige um novo serviço, altera a operação dos clientes e não cobre sozinho acessos feitos por outros meios. |

Adotar a segunda opção, começando pela auditoria e pelas provas nativas. Não acrescentar um
serviço, modelo de IA, MCP de memória ou instalação automática nesta frente.

## Catálogo e descoberta

Evoluir `skills-lock.json` para o esquema 3 e preservar a leitura do esquema 2 durante a migração.
Ele continuará sendo a fonte estruturada; não criar um segundo manifesto com os mesmos dados.
O microíndice do vault mantém descrições curtas e links para registros detalhados quando necessários.
Uma descrição deve informar quando usar a capacidade, entradas, saídas e limites.

Cada registro terá ID estável, tipo (`skill`, `agent`, `mcp` ou `runtime`), finalidade, origem,
cliente/escopo, entradas instaladas, identidade esperada e permissões solicitadas. O estado
observado será separado desses campos: versão declarada não equivale a versão verificada.

Para skills próprias, a identidade inclui o contrato compartilhado, os wrappers e seus arquivos
de apoio declarados. Calcular SHA-256 sobre nomes relativos ordenados e bytes dos arquivos; um
wrapper inalterado não pode ocultar mudança no contrato. Recusar caminhos externos, links de
filesystem, tipos especiais e IDs duplicados. Não executar scripts da skill para descobrir sua versão.

Para dependências externas, registrar origem e referência imutável quando disponível. Uma versão
de marketplace não resolvida fica `unverified`; o auditor não a transforma em um lock. Para MCP
remoto, registrar endpoint, transporte e nomes das ferramentas selecionadas, sem inventar uma
versão do serviço. Esquema e versão anunciados pelo servidor são observações datadas, não prova
da implementação que roda no fornecedor.

Permissões descrevem leitura/escrita, arquivos, destinos de rede, dados enviados, ambiente alvo
e referências a credenciais. Guardar somente o nome de uma variável de ambiente, nunca seu valor.
Não inferir que uma ferramenta é somente leitura pelo nome ou pelas anotações do servidor.

## O que cada controle pode comprovar

| Camada | Responsabilidade | Evidência esperada |
|---|---|---|
| Manifesto e vault | Intenção, origem, limites e histórico | Registro ligado à feature e ao conteúdo revisado. |
| Auditor local | Diferenças, arquivos ausentes, identidade e configuração incompatíveis | Resultado determinístico com códigos, hashes e caminhos sanitizados. |
| Claude Code/Codex | Descoberta, habilitação e regras nativas suportadas | Carregamento real e ensaio de chamada permitida/recusada. |
| Sandbox e sistema operacional | Acesso a arquivos, processos e rede | Teste da fronteira aplicável ao ambiente escolhido. |
| Credencial e serviço | Escopo de conta, projeto e ambiente | Permissões configuradas no fornecedor e teste controlado. |
| CI/publicação | Impedir promoção de uma configuração divergente | Check exigido pelo repositório consumidor. |

O auditor não será anunciado como firewall, sandbox ou prova de que todos os MCPs da máquina
estão controlados. Ele cobre as entradas do projeto e as dependências explicitamente declaradas.
Configuração global, plugins, políticas gerenciadas ou camadas não observadas ficam como limite
de cobertura. Um resultado de configuração correto não certifica o ambiente efetivo da sessão.

Na documentação consultada, Codex oferece habilitação de servidor e filtros de ferramentas;
Claude oferece regras de permissão e configuração de MCP. Há diferenças entre controles de
projeto e controles gerenciados. A implementação deverá comprovar a tradução por versão e não
copiar uma opção de um cliente para o outro.

No Claude, `allowed-tools` de uma skill concede dispensas de confirmação; não deve ser tratado
como uma lista que impede todas as outras ferramentas. O auditor deverá apontar concessões amplas,
instruções dinâmicas e hooks como superfície a revisar, sem executá-los. Ver as fontes oficiais abaixo.

## Primeiro incremento

Criar `scripts/capabilities.py` com biblioteca padrão e uma skill compartilhada `govern-capabilities`,
com wrappers para Claude Code e Codex. Reutilizar os verificadores de caminhos e identidade existentes.
As três operações propostas são:

| Operação | Resultado | Efeitos |
|---|---|---|
| `list` / `describe ID` | Catálogo curto ou contrato de uma capacidade | Somente leitura; sem conexão a MCP. |
| `audit --client claude|codex|both` | Comparação do manifesto com arquivos/configurações locais | Somente leitura; sem instalar, corrigir ou executar comandos declarados. |
| `review --id ID` | Pacote local com diferenças, hashes e sugestões por cliente | Escrita apenas em área privada, sob o lock do projeto. Não habilita a capacidade. |

O manifesto é validado por versão e campos conhecidos. Os limites iniciais são 200 capacidades,
100 arquivos declarados por capacidade, 1 MiB por arquivo de texto e 16 MiB por conjunto. Arquivos
binários, dependências e runtimes extensos usam uma identidade/inventário verificável, sem varrer
seus conteúdos. Não percorrer o diretório pessoal, repositórios vizinhos ou links de documentos.

O pacote de revisão ficará em `.operacao-local/capabilities/`, ignorado antes de qualquer escrita.
Ele terá o projeto, ID, retrato dos arquivos de entrada, hash do pacote, observações e proposta
de configuração. URLs com credenciais, headers literais sensíveis e argumentos potencialmente
secretos devem gerar um aviso sanitizado, sem ecoar o valor. Nenhuma fonte privada entra no CI.

Estados observados: `missing`, `matched`, `changed`, `unverified`, `unsupported` e `failed`.
`matched` significa correspondência no escopo auditado. Prova de execução fica num campo separado,
com cliente, versão, data e evidência. Saída JSON e texto devem distinguir diferença conhecida,
configuração ilegível e limite de cobertura. Código de sucesso exige correspondência das
capacidades que a política do projeto marcou como obrigatórias; pendência obrigatória falha.

Não incluir um comando de ativação automática neste incremento. A skill apresenta o pacote,
recupera a autorização já existente e aplica somente a alteração nativa coberta por ela, no fluxo
normal de edição e revisão. Preservar comentários, campos desconhecidos, regras mais restritivas,
credenciais e configurações de outros servidores. Se não for possível determinar o efeito de
uma camada, mantê-la inalterada e registrar a pendência.

## Revisão, mudança e revogação

Fluxo: **descobrir → conferir origem e conteúdo → comparar escopo → revisar diferença → aplicar
configuração autorizada → provar no cliente → registrar uso e resultado no vault**.

A autorização pode cobrir uma tarefa ou um escopo persistente definido pelo mantenedor. Não
pedir confirmação a cada chamada já coberta. Rever somente a diferença quando mudar conteúdo
relevante, origem, endpoint, ferramenta disponível, credencial/ambiente alvo ou permissão.
Uma redução de acesso também precisa ser aplicada sem apagar regras alheias.

O hash protege a correspondência entre a revisão e os bytes; não prova que um humano autorizou
o conteúdo. O registro no vault referencia a autorização real da sessão ou a revisão de código.
Uma nota, documento ingerido ou saída de MCP que diga “aprovado” não amplia o escopo.

Cada execução registra capacidades previstas e realmente usadas, versões conhecidas, referência
à configuração observada, evidência, desenvolvimento/produção e próxima ação. Um registro de
aprovação pode continuar válido para seu escopo; a evidência de uso precisa apontar a execução atual.

Revogar é desabilitar a entrada nativa aplicável e verificar em uma sessão nova. O registro
histórico permanece. Revogação de token pertence ao fornecedor; o harness não a declara concluída
por ter removido um arquivo. A retomada continua possível pelos índices mesmo com a capacidade desligada.

## Adoção e documentação

Em projeto novo, o personalizer seleciona capacidades necessárias e registra seus limites. Exemplos
de MCP permanecem inativos ou aguardando aprovação nativa. A ausência de fornecedor opcional não
bloqueia o núcleo; um requisito obrigatório indisponível aparece como pendência.

Na migração, primeiro auditar. Nenhuma permissão existente é substituída por um padrão mais amplo.
Conflitos recebem proposta de alteração por arquivo e forma de retorno. A auditoria offline não
deve abrir conexões, usar credenciais, chamar modelos ou disparar scripts de inicialização.

README, USAGE e PROCESS PT/EN deverão explicar catálogo, revisão e limites, preservando o design
atual. O diagrama de governança só será apresentado como operacional depois das provas. Integrar
o catálogo ao personalizer, à skill de integrações e aos encerramentos de execução.

## Critérios de aceite

| ID | Prova exigida |
|---|---|
| G01 | Esquema 2 migra sem perda de campos; esquema 3 rejeita IDs duplicados, caminhos inválidos e dados incompatíveis. |
| G02 | Alterar contrato, wrapper, arquivo de apoio, origem ou ferramenta declarada produz diferença; repetir sem mudanças é estável. |
| G03 | Auditoria preserva bytes de arquivos, não instala nada, não inicia MCP/processo declarado e não acessa a rede. |
| G04 | Configurações Claude/Codex são lidas separadamente; campos não suportados e camadas não observadas ficam explícitos. |
| G05 | Pacote de revisão é privado, sanitizado e ligado à revisão exata; mudança de entrada invalida a proposta antiga. |
| G06 | Setup novo e migração preservam as quatro configurações nativas, credenciais, skills modificadas e regras existentes. |
| G07 | MCP sintético local: chamada prevista permitida e chamada proibida recusada pelo cliente; descoberta sozinha não passa. |
| G08 | Uma nova sessão recupera capacidade, escopo revisado, mudança pendente e evidência de uso pelos microíndices. |
| G09 | Desabilitação e retorno testados sem apagar o vault; README/processos correspondem ao comportamento entregue. |

Testar G01–G06 com arquivos e Git reais; simular somente fronteiras externas. Em G07, usar servidor
local sintético e HOME isolado; não conectar provedores de produção. Começar por protocolos/SDK
locais sem modelo pago. Se isso não exercitar a decisão real do cliente, registrar o limite e
propor um ensaio de modelo com orçamento próprio, antes de executá-lo. O teto de quatro sessões
Codex da frente anterior já foi consumido e não é reutilizado como autorização para novas chamadas.
Um cliente sem autenticação ou sem a opção exigida fica pendente, sem substituição por uma promessa.

## Fora deste incremento

Proxy universal de MCP, instalação/atualização automática de plugins, auditoria de toda a máquina,
política corporativa gerenciada, migração de credenciais, claude-mem, sincronização entre máquinas,
seleção automática de notas para Graphify e orquestração autônoma de PM/Tech Lead. A esteira pública
virá com um exemplo que use as capacidades já verificadas.

## Fontes e condições de validade

Consultadas em 2026-10-02; regras documentadas devem ser verificadas contra o cliente instalado.
Os recibos de ingestão e eventuais cópias convertidas ficam no vault local e não são publicados
com este desenho. A leitura das páginas oficiais é registrada separadamente do sucesso da conversão.

- [Codex: MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli): configuração por servidor, filtros de ferramentas e limites por superfície.
- [Codex: configuração](https://learn.chatgpt.com/docs/config-file/config-reference): opções de MCP e habilitação individual de skills.
- [Claude Code: permissões](https://code.claude.com/docs/en/permissions): regras nativas e diferença entre regra de comando e isolamento de arquivos/rede.
- [Claude Code: MCP](https://code.claude.com/docs/en/mcp): escopos e distinção entre configuração de projeto e controles gerenciados.
- [Claude Code: skills](https://code.claude.com/docs/en/skills): descoberta, campos de invocação e efeitos de `allowed-tools`.

Próxima etapa: revisão do plano de implementação, que detalha arquivos, entregas, testes e o método
nativo já escolhido. A aprovação do desenho está registrada; nenhum controle novo foi ativado.
