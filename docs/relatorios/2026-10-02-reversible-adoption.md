# Frente: adoção reversível

O modo `setup.sh --trial` salva um ponto privado antes de alterar o projeto. A saída exige uma
prévia atual e sua confirmação. Antes de trocar as pastas, o controlador verifica uma cópia do
trabalho do teste e outra do ponto inicial. O executor fica fora do projeto e permite retomar
uma troca interrompida. Nenhum repositório real do operador foi restaurado nestes ensaios.

Validação para publicação aprovada no código `a4c76cc`: Linux, Windows e Graphify passaram,
com revisão independente concluída e achados corrigidos. Este relatório registra a medição anterior
ao merge; o [PR #9](https://github.com/Matheusrpc/YoungCrowHarness/pull/9) registra a publicação.
A [medição](../medicoes/2026-10-02-reversible-adoption.json) separa revisões e ambientes.

## Comportamento entregue no branch

- Claude, Codex e ambos usam o mesmo controlador. Trial pula downloads, plugins e escrita em
  configurações globais. A instalação normal mantém seu contrato e informa a ausência de ponto inicial.
- O ponto inclui Git independente, index, arquivos ignorados, alterações sem commit, binários e
  diretórios vazios. Repetir setup, inclusive após falha parcial, mantém o primeiro ponto.
- `status` lê o registro. `restore --dry-run` grava uma proposta privada fora do projeto;
  `restore --confirm DIGEST` recusa uma proposta antiga. `recover` retoma a transação identificada.
- Locks registram processo e instante de criação, incluindo filhos. Recuperação exige processos
  encerrados e o ID do lock. Não há encerramento automático de sessões do operador.
- O vault registra apenas ID, data, estado e próxima ação. Backups não entram no Git ou nos índices.

## Evidências já obtidas

| Prova | Resultado |
|---|---|
| Suíte completa Linux após os ajustes nativos | 254 testes em 78,398 s; 11 casos Windows pulados; nenhuma falha |
| Instalação e retorno Linux | Claude, Codex e ambos: pasta ausente, Git com alterações e interrupção passaram |
| Armazenamento, ponto inicial e retorno no CI Windows | 43 testes em 277,448 s; dois casos POSIX pulados; nenhuma falha |
| Setup trial no CI Windows | 9 testes em 86,238 s; todos passaram |
| Retorno completo no CI Windows, Python 3.11.9 | Três trajetórias passaram; trabalho do teste preservado e perfil sem alterações |
| Setup trial Windows local, três clientes, repetição e falha parcial | 9 testes passaram em 299,242 s |
| Personalização | 8 testes passaram; um caso POSIX pulado |
| Catálogo | 21 testes passaram; um caso POSIX pulado |
| Vault | 22 testes passaram; um caso de symlink reservado ao Linux |
| Instrução do personalizer | Cinco controles sem orientação não localizaram o comando; cinco ensaios com a nova referência usaram trial antes das notas |
| Aprovação recuperada da memória | Dez ensaios respeitaram o pedido atual de somente leitura; nenhum foi uma restauração real |
| Diagramas PT/EN | Seis SVGs sem texto excedendo a caixa; imagem móvel com 358 px em viewport de 390 px; zero navegadores próprios vivos |
| Smoke Windows local em `710c0fd`, Python 3.14.4 | Três trajetórias passaram; trabalho do teste preservado e perfil sem alterações |
| Regressão Git no Windows | Dois testes falharam antes da correção e passaram depois, em 53,021 s |
| Registro de recuperação no Windows | Contador inválido reproduzido; teste corrigido passou em 87,705 s |
| Armazenamento Windows após leitura nativa de ACL | 15 testes em 33,400 s; um caso POSIX pulado |
| Armazenamento Windows após travessia nativa e recusa prévia de streams | 16 testes em 40,695 s; um caso POSIX pulado |

As suítes Linux e Windows e os smokes estão no [run 37050895018](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37050895018).
O run corresponde ao head `a4c76cc`; o GitHub executou o merge de teste `2817ab3` contra a base.
Os três jobs terminaram com sucesso. O fechamento documental preserva código, testes, workflow,
catálogo e diagramas desse commit; a diferença deve conter apenas documentação.

Os testes provocam encerramento real antes/depois dos dois renames, na proteção de ACL e na
finalização. Também cobrem arquivo Windows aberto sem compartilhamento de exclusão, falta de
espaço, ponto corrompido, caminho adulterado, raiz substituída e prévia antiga. O smoke usa setup,
Git e runner reais com dados sintéticos; não prova conversa ou descoberta nativa dos clientes.

O CI anterior passou no commit `35564cf`. No commit `411ba11`, a regressão encontrou um contrato
do personalizer calculado antes da normalização de metadados. O cálculo foi corrigido e a suíte
completa Linux passou. O smoke também revelou duas falhas
Windows: caminhos de backup longos e cache de inicialização do PowerShell no perfil do usuário.
A primeira ganhou recusa anterior ao setup; a segunda, isolamento do ambiente do helper, com
reprodutor que falhou e depois passou sem alterar o perfil.

O efeito de cache é coerente com a inicialização documentada no
[código do PowerShell](https://github.com/PowerShell/PowerShell/blob/v6.0.0/src/Microsoft.PowerShell.ConsoleHost/host/msh/ConsoleHost.cs#L128-L147).
A prova de comportamento desta entrega foi executada no PowerShell 5.1 do Windows.

O primeiro job Windows do GitHub recusou o perfil das fixtures. A medição em `e69db52` mostrou
que as pastas e arquivos novos pertenciam a Administradores; a pasta também tinha uma regra
explícita. O executor local usava o usuário atual como dono. O runner de testes agora seleciona
esse dono para novos objetos no processo de teste e cria uma base temporária privada, de onde as
fixtures herdam suas permissões. O dono padrão anterior é restaurado ao sair. Isso não altera
arquivos existentes, contas, política da máquina ou a verificação de permissões do produto.
O mecanismo segue a [documentação do Windows sobre o dono de novos objetos](https://learn.microsoft.com/en-us/windows/win32/secauthz/owner-of-a-new-object).
A prova completa passou no CI Windows, com o dono atual e a base privada conferidos nas três etapas.

A [medição de ACL no runner](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37044659425/job/110962967906)
encontrou 32,793 s e 23,038 s em duas consultas com `Get-Acl`, contra 0,174 s pela API nativa
`System.IO.Directory.GetAccessControl`. Trocar o perfil NUL por um arquivo existente manteve o
custo de `Get-Acl`, portanto o isolamento do perfil foi preservado. O helper passou a ler dono,
grupo e DACL diretamente pela API .NET, com as mesmas regras de aceitação. O teste local de
armazenamento passou após essa mudança. O benchmark mede a consulta; não mede o tempo de um setup inteiro.

O primeiro cenário do helper completo ainda levou 314,406 s no CI em `4f18457`. As consultas
restantes a arquivos passaram a usar `DirectoryInfo` e `FileInfo`, mantendo arquivos ocultos,
limites e recusas de links e atributos. A verificação nativa de streams NTFS ocorre antes de
invocar o helper, inclusive nos modos que alteram permissões. Um teste com stream extra mostrou
que a versão anterior recusava o arquivo depois de mudar a ACL da raiz. O teste falhou em
3,508 s na versão anterior e passou na suíte local de 16 casos após a correção.

A travessia nativa manteve a recusa correta, mas o cenário completo ainda levou 311,516 s.
Um [segundo benchmark](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37048011105/job/110974128729)
isolou o custo restante: `New-Object` levou 25,403 s e `ConvertTo-Json`, 18,921 s. Carregar
explicitamente o módulo Utility pelo caminho de `$PSHOME` e serializar o mesmo objeto levou
0,221 s. O helper agora usa esse carregamento explícito do módulo que já acompanha o Windows.
O ambiente isolado e o formato JSON foram preservados; nenhuma dependência foi acrescentada.
Na execução seguinte do helper completo, o primeiro cenário passou em 5,353 s, contra 311,516 s
antes do carregamento explícito. Esse tempo vem do log parcial da execução duplicada cancelada;
a conclusão da suíte foi confirmada pelo job completo separado, referenciado acima.

No CI de `b6f2643`, os 43 testes de armazenamento e recuperação passaram em 330,032 s,
com dois casos POSIX pulados. A etapa de setup encontrou um erro na fixture: ela tentava ler
um log que não havia sido criado porque o trial não chamou nenhum wrapper. No Windows, as
consultas seguras usam Git nativo. O registro agora começa vazio, e as verificações de ausência
de downloads e chamadas de plugins continuam iguais. A instalação já tinha terminado com sucesso
antes desse erro de leitura no teste.

O teste de falha parcial também dependia de um wrapper no `PATH`. Com Git encontrado em `bin`,
o lançador Bash deixou de usar esse wrapper; a instalação terminou normalmente. A mesma diferença
foi reproduzida localmente em 25,332 s. A fixture agora encerra sua cópia descartável do instalador
com código 19 antes de copiar `AGENTS.md`, confere esse código exato e repete a instalação original.
O código distribuído do instalador não recebeu um mecanismo de falha para testes.

## Revisão independente e correções

Um revisor em contexto separado, somente leitura, examinou o branch completo. O executor fez
uma rodada de correções, com reprodutores antes das mudanças e regressão completa depois.
O parecer inicial bloqueou o merge; não houve uma segunda revisão para substituir os testes.

| Achado | Prova e correção |
|---|---|
| Crítico: Git podia executar `core.fsmonitor` antes do ponto inicial | O setup público criou um arquivo marcador mesmo recusando o trial. As consultas do preflight e do filho agora usam `adoption_fs.git_read`, que isola configuração/ambiente e desativa fsmonitor. Projeto e perfil permanecem intactos na recusa. |
| Importante: restauração POSIX perdia o grupo | No Linux real, o GID 4 virou 1001 antes da correção. O inventário agora registra GID; cópia e retorno aplicam e verificam o grupo. Grupos dos quais o processo não participa são recusados. O teste cobre raiz, diretório e arquivo `0640`. |
| Contador inválido no diário | O revisor classificou como menor porque não observou perda de dados. O executor incluiu na correção: aceitar esse registro contradiz a recusa de estado corrompido. Inteiro estrito, intervalo e mínimo por fase são verificados antes da recuperação. |

Os quatro reprodutores falharam no Linux em `813684a` (run 37039994011). Após a primeira correção,
a regressão encontrou uma contagem mínima incorreta na janela após o primeiro rename. O ajuste
em `0b40d5e` aceita a evidência da troca quando seu registro de conclusão ainda não existe.
Os reprodutores e os casos de interrupção passaram na suíte completa. Nenhum achado menor ficou adiado.
O link do personalizer para o guia passou a apontar para o upstream: esse guia não é copiado no setup.

## Decisões de execução

| Decisão e motivo | Custo ou limite assumido |
|---|---|
| Reutilizar o checkout dedicado e seu CI inicial no mesmo commit | Diagnósticos existentes precisam permanecer fora dos commits; um escritor por vez. |
| Criar fixtures próprias fora de Git | Limpeza restrita aos diretórios criados pelo teste. Nenhum repositório do usuário entra na prova. |
| Usar trava nativa na recuperação do lease | Filesystem sem suporte à trava é recusado; processo morto libera a trava do sistema. |
| Antecipar a criação controlada da raiz ausente | Uma criação interrompida cuja identidade não foi vinculada exige inspeção manual. |
| Registrar o filho de ACL antes de autorizar sua execução | A recuperação espera o encerramento desse filho; não mata processos do operador. |
| Confirmar antes de preparar as cópias da transação | A cópia pode falhar depois da confirmação. A pasta atual só é trocada após verificar ambas. |
| Preparar tarefas seguintes durante regressões longas | Falhas impedem a publicação e exigem repetir as provas afetadas. Continua havendo um só escritor. |
| Expor Git nativo no PATH isolado do Windows | Python nativo não executa o wrapper Bash; consultas nativas não aparecem no log desse wrapper. |
| Recusar caminhos Windows derivados com 248 unidades UTF-16 ou mais | Pode exigir uma base mais curta, inclusive se o usuário criar nomes longos durante o trial. Reserva de 64 caracteres para caminhos distribuídos. |
| Normalizar o catálogo antes do hash e isolar cache PowerShell | O hash depende do contrato normalizado. O helper abre mão do cache de inicialização e exige prova no PowerShell 5.1. |
| Fazer a revisão final enquanto o CI Windows termina | A revisão não substitui o job Windows; o merge continua bloqueado até as provas obrigatórias. |
| Tratar o contador adulterado na mesma rodada de correções | Um estado inválido exige inspeção; os mínimos precisam aceitar interrupções entre rename e gravação. |
| Preservar GID dos grupos atuais do processo | Perder participação no grupo pode bloquear a saída; não há elevação de privilégio. |
| Usar o CI completo Linux para concluir a regressão do setup e o CI Windows para a plataforma nativa | O recibo confere commit, jobs, contagens e três perfis. Resultado de outro commit ou prova incompleta não conclui a tarefa. |
| Preparar as fixtures Windows com dono e herança do perfil suportado | A configuração fica no processo de teste e em sua base descartável. O produto continua recusando o perfil original do runner; o teste exige conferir o dono selecionado e a ACL privada. |
| Ler ACLs pela API nativa após medir o custo de `Get-Acl` | Mantidas as verificações de dono, grupo e DACL. A mudança exige repetir preservação de permissões, recusas e retorno no Windows. |
| Usar travessia nativa e verificar streams antes de alterar permissões | O helper completo ainda era lento; a recusa de streams também precisava preservar ACLs. Os casos de stream, junction, ACL privada e retorno precisam passar novamente. |
| Carregar Utility pelo caminho do próprio PowerShell | O benchmark confirmou o custo da descoberta automática. O helper depende do módulo nativo existente e mantém o perfil isolado; a suíte completa deve confirmar o comportamento. |
| Reutilizar a prova nativa no fechamento apenas documental | Conferir que código, testes, workflow, skills, catálogo e diagramas permanecem idênticos ao commit validado. Qualquer alteração nesses arquivos exige nova prova afetada; o check protegido do commit final continua obrigatório. |

O revisor deixou quatro temas fora do julgamento. Essas fronteiras foram mantidas e documentadas:

| Fronteira | Consequência para quem usa |
|---|---|
| Queda de energia ou falha física | O retorno não substitui backup independente; não há promessa de durabilidade contra falha de disco. |
| Serviços, publicação remota e configuração global | O retorno cobre a pasta do projeto. Efeitos externos exigem seu próprio procedimento. |
| Conversa e descoberta nativas de Claude/Codex | Instalação e retorno são provados sem modelo. Esses ensaios não demonstram o comportamento conversacional dos clientes. |
| Links, worktrees e ACLs arbitrárias | Entradas fora do perfil são recusadas, inclusive quando criadas durante o trial; o operador precisa resolver a incompatibilidade antes de retornar. |

## Limites e operação

O perfil aceita arquivos regulares e diretórios, até 100 mil entradas e 64 GiB. Exige mesmo volume,
storage privado e externo a todos os repositórios Git. Recusa links, hardlinks, worktrees, submódulos,
streams extras e permissões não preserváveis. O operador precisa encerrar escritores externos.
Não promete durabilidade contra falha de energia/disco, nem restaura serviços, configurações globais
ou publicações remotas. Instalações antigas sem ponto inicial não têm retorno retroativo.

Os [guias PT/EN](../USAGE.md#adocao-reversivel-pt) incluem setup do zero, migração, prévia, confirmação
e recuperação. A reversão da entrega do harness consiste em reverter seu merge; não em restaurar
repositórios de consumidores. Backups não têm limpeza automática.

A política automática de execução bloqueou a limpeza recursiva da pasta temporária privada do
smoke local, inclusive após verificar seu caminho exato. Os dados sintéticos ficaram preservados
localmente. Isso não altera as provas, o código publicado ou qualquer repositório do usuário.

ATRASO: main 1 na medição anterior ao merge. O PR #9 registra o estado da publicação.
