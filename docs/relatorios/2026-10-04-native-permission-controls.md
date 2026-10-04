# Limites dos perfis nativos

Frente: 2A / YC-203. Continuação da [verificação nativa](2026-10-03-native-client-verification.md).
As provas complementares confirmam que os perfis atuais não atendem ao contrato de isolamento.
Nenhum perfil foi liberado e nenhuma chamada de modelo real foi feita.
[Medições por caso](../medicoes/native-permission-controls.json).

## O que foi testado

No Windows, os executáveis instalados Codex 0.160.0 e Claude Code 2.1.220 receberam respostas
de um fornecedor simulado em `127.0.0.1`. Cada processo teve até 30 segundos, supervisão da
árvore de descendentes e pastas de estado descartáveis dentro do espaço privado desta investigação.
As respostas continham um JSON fixo ou uma tentativa de ler um arquivo fictício. O modelo indicado
era apenas metadado do protocolo; nenhuma inferência ocorreu. A simulação do Claude usou uma
chave fictícia para esse endereço local, sem provar autenticação por assinatura ou API real.

O Codex recebeu um perfil nomeado com leitura de `:minimal` e `:workspace_roots`, sem permissões
de escrita. O argumento `--strict-config` aceitou essa configuração. O Claude recebeu o perfil
restrito existente: safe mode, catálogo de ferramentas vazio, MCP explícito vazio, `dontAsk` e
persistência de sessão desabilitada. Configurações e contas globais não foram editadas pelo teste.

| Caso | Resultado observado | O que permite concluir |
|---|---|---|
| Codex, JSON simples, `gpt-5.5` | Uma requisição local; JSON aceito pelo decoder | O controle positivo do protocolo funciona nessa combinação |
| Codex, imagem dentro da pasta permitida | Duas requisições; imagem não transmitida | A operação permitida também falha ao preparar o sandbox do Windows |
| Codex, imagem fora da pasta permitida | Duas requisições; imagem não transmitida | A mesma falha impede a leitura; isso não prova um sandbox funcional |
| Codex, JSON simples, `gpt-6.1-sol` | Cliente retorna código zero, mas emite erro de Code Mode desabilitado | O decoder recusa o resultado; catálogo atual não implica compatibilidade com o perfil |
| Claude, JSON simples | Uma requisição local; JSON aceito | O controle positivo do protocolo funciona |
| Claude, tentativa de `Read` fora da pasta | Duas requisições; ferramenta indisponível; conteúdo fictício não transmitido | A tentativa é recusada; o decoder rejeita os eventos de ferramenta |

Todas as árvores de processos supervisionadas foram encerradas. Os casos não verificam políticas
administrativas do host, rede fora do transporte simulado, login real, faturamento ou outras versões.
Os hashes dos executáveis e das evidências privadas estão nas medições. O código experimental e os
registros completos ficam no espaço privado da investigação; não são um novo comando suportado.

## Por que o bloqueio continua

Os dois clientes gravaram estado em suas pastas próprias, mesmo com persistência de sessão
desabilitada. O Codex criou bancos locais e arquivos de runtime em `CODEX_HOME`; o Claude criou
`.claude.json` e seu backup em `CLAUDE_CONFIG_DIR`. As pastas eram fictícias. A comparação cobre
essas pastas, não uma auditoria de todos os acessos ao sistema operacional.

Essas gravações não indicam vazamento. Mostram que permissões das ferramentas do agente e
comportamento interno do cliente são fronteiras diferentes. O contrato aprovado proíbe o
subprocesso de escrever no estado do coordenador ou nas suas credenciais. Uma pasta de trabalho
vazia, flags de sessão e contenção da árvore de processos não bastam para demonstrar esse contrato.

Há outra limitação: nos dois casos de imagem do Codex, os eventos JSON da CLI mostraram apenas
a resposta final e o término. O decoder aceitou o nonce, embora o fornecedor simulado tivesse
pedido uma ferramenta. Portanto, saída válida e código zero não comprovam ausência de tentativas
de ferramenta. A política precisa impor a fronteira antes do efeito. O registro de perfis continua
vazio, preservando o bloqueio de execução real.

A [documentação de safe mode do Claude](https://code.claude.com/docs/en/env-vars) informa que
políticas administrativas continuam aplicadas. Um catálogo vazio não certifica a ausência de
efeitos dessas políticas. O modo `--bare` da versão instalada exige autenticação API e não atende
ao padrão de assinatura aprovado. As fontes oficiais já ingeridas permanecem privadas no vault.

## Decisão de arquitetura pendente

Recomendação: preparar uma prova de executor em ambiente isolado, com login oficial feito pelo
desenvolvedor nesse ambiente. Isso exige ampliar o plano, que hoje proíbe instalar infraestrutura
de isolamento para contornar o bloqueio. Não há instalação, migração de credenciais ou mudança
automática de conexão incluída nesta investigação.

| Caminho | Efeito para quem adota | Limite |
|---|---|---|
| Ambiente isolado, recomendado para automação | Preparação adicional e login próprio dos clientes | O ambiente e os dois perfis ainda precisam de prova; container ou VM não é garantia por si só |
| Cliente local confiável | Aproveita a instalação e o login atuais | Exige aceitar estado próprio e políticas do cliente no host; não entrega o isolamento forte do contrato atual |
| Manter o contrato e esperar suporte nativo | Preserva as dependências atuais | Chamadas reais e a fila continuam bloqueadas, sem data de liberação comprovada |

No caminho recomendado, o coordenador conserva banco, vault, aprovações e publicação. Cada
executor recebe somente a cópia de trabalho e o contexto autorizados. Seu cliente pode manter
cache e login em estado privado próprio, sem montar a pasta pessoal, as credenciais ou o banco do
coordenador. Credenciais não entram no Git, nas evidências ou nos pacotes de transferência.
O desenvolvedor continua escolhendo Claude ou Codex, modelo e esforço; não há troca para API.

O primeiro incremento seria uma prova, antes da fila: um diagnóstico permitido funciona; leitura
e escrita fora do escopo falham; políticas desconhecidas impedem o despacho; timeout encerra os
processos; repetição não chama novamente; nenhum dado do coordenador é alterado. Só depois cabem
as duas chamadas autenticadas já autorizadas e limitadas. A plataforma de isolamento e seu setup
precisam ser definidos no desenho seguinte, sem prometer suporte antes da medição.

YC-203 / 2A continuam parciais. 2B continua dependente. A próxima decisão é escolher a fronteira
de execução acima; repetir a mesma tentativa com outras flags não encerra esse requisito.

## English overview

Six loopback controls ran against Codex 0.160.0 and Claude Code 2.1.220 on Windows, without real
model inference. Simple nonce responses worked with the tested Codex `gpt-5.5` and Claude
metadata. Both permitted and prohibited Codex image reads failed because the Windows sandbox
could not enforce the configured split read restrictions. The current Codex default model metadata
produced a Code Mode error under the disabled-host profile. Claude rejected a forced `Read` call.

Both clients wrote state in their disposable private homes. These writes are not evidence of
data leakage. They show that agent tool permissions do not contain the client's own runtime.
Codex also omitted the attempted image tool from its JSON event stream, so nonce success alone
cannot certify a tool-free run. Both production profiles remain disabled; YC-203 stays partial.

The recommended next design is a separately isolated executor with its own official client login,
authorized workspace and private runtime state. Its isolation still needs proof. This adds setup
and changes the current plan's infrastructure boundary, so it remains a proposal. Alternatives
are explicitly trusting the local client with weaker host isolation or keeping execution blocked.
