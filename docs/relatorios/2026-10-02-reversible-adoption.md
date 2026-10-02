# Frente: adoção reversível

O modo `setup.sh --trial` salva um ponto privado antes de alterar o projeto. A saída exige uma
prévia atual e sua confirmação. Antes de trocar as pastas, o controlador verifica uma cópia do
trabalho do teste e outra do ponto inicial. O executor fica fora do projeto e permite retomar
uma troca interrompida. Nenhum repositório real do operador foi restaurado nestes ensaios.

Estado deste relatório: implementação em validação final no PR #9; publicação e revisão final
ainda pendentes. A [medição](../medicoes/2026-10-02-reversible-adoption.json) distingue as provas.

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
| Armazenamento, ponto inicial e retorno no Windows | 39 testes passaram em 1057,491 s; um caso POSIX pulado |
| Setup trial, três clientes, repetição e falha parcial | 6 testes passaram em 411,318 s |
| Personalização | 8 testes passaram; um caso POSIX pulado |
| Catálogo | 21 testes passaram; um caso POSIX pulado |
| Vault | 22 testes passaram; um caso de symlink reservado ao Linux |
| Instrução do personalizer | Cinco controles sem orientação não localizaram o comando; cinco ensaios com a nova referência usaram trial antes das notas |
| Aprovação recuperada da memória | Dez ensaios respeitaram o pedido atual de somente leitura; nenhum foi uma restauração real |
| Diagramas PT/EN | Seis SVGs sem texto excedendo a caixa; imagem móvel com 358 px em viewport de 390 px; zero navegadores próprios vivos |

Os testes provocam encerramento real antes/depois dos dois renames, na proteção de ACL e na
finalização. Também cobrem arquivo Windows aberto sem compartilhamento de exclusão, falta de
espaço, ponto corrompido, caminho adulterado, raiz substituída e prévia antiga. O smoke usa setup,
Git e runner reais com dados sintéticos; não prova conversa ou descoberta nativa dos clientes.

O CI anterior passou no commit `35564cf`. No commit `411ba11`, a regressão encontrou um contrato
do personalizer calculado antes da normalização de metadados. O cálculo foi corrigido; a nova
regressão completa ainda precisa confirmar o resultado. O smoke também revelou duas falhas
Windows: caminhos de backup longos e cache de inicialização do PowerShell no perfil do usuário.
A primeira ganhou recusa anterior ao setup; a segunda, isolamento do ambiente do helper, com
reprodutor que falhou e depois passou sem alterar o perfil.

O efeito de cache é coerente com a inicialização documentada no
[código do PowerShell](https://github.com/PowerShell/PowerShell/blob/v6.0.0/src/Microsoft.PowerShell.ConsoleHost/host/msh/ConsoleHost.cs#L128-L147).
A prova de comportamento desta entrega foi executada no PowerShell 5.1 do Windows.

## Decisões de execução

1. Reutilizar o checkout dedicado e preservar diagnósticos alheios; não criar outro escritor.
2. Usar temporários próprios fora de Git para provar os limites reais do armazenamento.
3. Serializar recuperação de lock com trava nativa liberada na morte do processo.
4. Antecipar a criação controlada da raiz ausente para testar o retorno à ausência.
5. Registrar filhos do helper de ACL com sinal de início; recuperar só após sua saída.
6. Confirmar a transação antes de copiar; a troca só ocorre depois de verificar as duas cópias.
7. Preparar tarefas seguintes enquanto regressões longas executam, sem publicar antes das provas.
8. Expor o Git nativo no PATH isolado dos testes; Python Windows não executa o wrapper Bash.
9. Recusar caminhos derivados Windows com 248 unidades UTF-16 ou mais. O setup reserva 64
   caracteres para caminhos distribuídos; caminhos maiores criados depois podem exigir base mais curta.
10. Calcular contratos com o catálogo normalizado e isolar caches do PowerShell do perfil real.

## Limites e operação

O perfil aceita arquivos regulares e diretórios, até 100 mil entradas e 64 GiB. Exige mesmo volume,
storage privado e externo a todos os repositórios Git. Recusa links, hardlinks, worktrees, submódulos,
streams extras e permissões não preserváveis. O operador precisa encerrar escritores externos.
Não promete durabilidade contra falha de energia/disco, nem restaura serviços, configurações globais
ou publicações remotas. Instalações antigas sem ponto inicial não têm retorno retroativo.

Os [guias PT/EN](../USAGE.md#adocao-reversivel-pt) incluem setup do zero, migração, prévia, confirmação
e recuperação. A reversão da entrega do harness consiste em reverter seu merge; não em restaurar
repositórios de consumidores. Backups não têm limpeza automática.

ATRASO: main 1 — adoção reversível ainda não publicada.
