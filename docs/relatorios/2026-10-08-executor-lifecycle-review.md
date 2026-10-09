# Revisão do ciclo de configuração do executor

Frente: YC-203, viabilidade de simplificação. Data: 2026-10-08, America/Sao_Paulo.

**Separar a configuração da instalação da execução das missões pode eliminar as
escritas de settings por missão. A revisão não estabelece um caminho nativo pronto
para substituir o atual.** Recomenda-se conservar o código e os bloqueios até fechar
as condições abaixo. Abrir uma issue no Docker é opcional; nenhum contato foi enviado.

## O que já existe

A [instalação local exclusiva](../superpowers/specs/2026-10-05-exclusive-egress-decision.md)
foi aprovada em 5/out. Um runner dedicado já é alternativa, sem máquina selecionada.
Outra conta Windows ou outro daemon no mesmo host não têm isolamento comprovado.
Exclusividade, sozinha, não impede outros processos de escrever na configuração.

No código atual, `mission_network.validate_plan` exige proxy inicial vazio, `direct`
ou `system`. A fase A escolhe uma porta, altera `proxy.sandbox` e, quando necessário,
`no_proxy.sandbox`, e reinicia o daemon. A recuperação restaura o baseline e reinicia.
As escritas exigem comparação atômica do estado completo, porque uma consulta seguida
de escrita podia apagar mudanças externas. O adaptador nativo continua recusando os
efeitos. [Correção e evidência](2026-10-07-conditional-settings.md).

As credenciais são uma pendência separada. O coordenador público exige inventário
vazio e preserva credenciais/políticas durante a transação. O ensaio privado antigo
criava uma credencial fictícia e a removia por placeholder. Isso não prova remoção
condicionada à identidade/versão nem revogação nas sandboxes. Não há evidência de que
o produto crie e apague o login do usuário a cada missão: o
[desenho de autenticação](../superpowers/specs/2026-10-04-isolated-executor-design.md#autenticação-modelos-e-esforço)
já prevê preparação e login pelo fornecedor.

## Alternativas avaliadas

| Alternativa | Benefício | Limite |
|---|---|---|
| Manter ativação/restauração atual | Reaproveita coordenador, diário e recuperação testados | Exige contrato local de escrita condicional e de credenciais ainda não estabelecido |
| Conservar proxy fixo entre missões | Retira escritas/reinícios de settings do fluxo das missões | Exige propriedade do endpoint entre missões, manutenção separada e revisão do baseline; não resolve a credencial fictícia |
| Mover para runner dedicado | Separa o uso do Docker de outros trabalhos do computador | Não fornece, por si só, atomicidade, revogação ou prova contra desvio de saída |

## Condições para a alternativa de proxy fixo

Configurar uma vez significa manter a instalação reservada ao YoungCrow enquanto o
modo estiver ativo. A missão observaria o baseline, executaria seu trabalho e
encerraria os recursos próprios. Configuração, atualização e desativação ficariam
em manutenção separada, com admissões fechadas e cargas encerradas. A instalação
não voltaria ao proxy anterior ao terminar cada missão.

Isso elimina a necessidade de CAS nas escritas removidas. Qualquer manutenção
automática que ainda escreva/restaure estado compartilhado precisa de atomicidade
ou de exclusão efetiva de outros escritores. Mover os mesmos comandos para o setup
não comprova essa exclusão. Recibos antigos continuam exigindo sua recuperação original.

O endpoint fixo precisa continuar sob controle quando o guard encerra ou cai. Uma
porta livre observada no preflight pode ser ocupada depois. O controle deve impedir
substituição do endpoint e saída direta, inclusive entre missões; monitorar a
configuração não fecha essa janela. Esta revisão não escolhe nem implementa um novo
serviço permanente para resolver o problema.

Manter a autenticação do fornecedor no setup também não encerra a prova da credencial
fictícia. Deixar esse recurso instalado muda a condição de retorno aprovada. Seria
necessário definir propriedade, rotação, retirada e revogação verificável, sem
confundir ausência no inventário com revogação. A mudança não autoriza tokens na VM,
um gerenciador OAuth próprio ou fallback para API.

## Recomendação e próxima ação

**Não implementar a troca agora apenas para contornar o bloqueio externo.** A redução
de escritas é concreta, mas a alternativa ainda precisa demonstrar proteção do
endpoint e um ciclo completo de credenciais. Não seria correto chamar isso de
simplificação concluída ou prometer que libera o executor.

O caminho vigente continua: obter evidência aplicável ao contrato local, implementar
o adaptador e cumprir os aceites registrados. A issue é um meio opcional de obter
essa evidência. Uma futura proposta sem mutações por missão só deve substituir esse
caminho se fechar também instalação/manutenção, endpoint e credenciais; depois pode
receber aprovação como mudança de arquitetura. Não repetir as buscas já encerradas,
criar outro roteiro nativo ou consumir o terceiro ciclo para testar uma suposição.

## Evidência e limites

Leitura do código e das decisões no commit `7f45e5eed7537338e5037ec4468ceadd3431c31d`,
com duas revisões independentes somente leitura. A
[medição](../medicoes/2026-10-08-executor-lifecycle-review.json) registra arquivos,
hashes e verificações documentais. Não houve alteração de código, teste de produto,
Docker/sbx, login ou chamada de modelo. Os 26 testes offline publicados anteriormente
continuam sendo evidência da reprodução dos fontes de B, sem novo aceite nativo.
Permanecem 2/3 ciclos consumidos, `proof_accepted=false` e perfis bloqueados.

## Retomada da consulta em 9/out

O mantenedor autorizou retomar a publicação do texto já revisado em
`docker/sbx-releases`. A revisão independente não encontrou segredos ou afirmações
sem suporte. A issue permanece sem envio: a configuração observada está na revisão 3,
sem `api.github.com` nos hosts efetivos; a adição existe apenas no rascunho.
A chamada antes recusada não foi repetida sem mudança no ambiente. Aplicar a
configuração e verificar acesso e duplicatas precede a publicação. Nenhum ciclo
nativo foi executado ou autorizado por esta retomada.

## English overview

Exclusive local Docker use was already approved. A fixed installation proxy could
remove settings writes and daemon restarts from missions, but it is not an implemented
or proven replacement. Maintenance would still need atomic writes or effective
writer exclusion. The stable endpoint must remain controlled after guard exit, and
the dummy-credential proof still needs verified ownership, removal and revocation.
Persistent provider login was already part of setup; the current public coordinator
does not create/delete user credentials per mission.

Keep the current implementation and gates until a replacement addresses the complete
lifecycle. A vendor issue is optional. This read-only review does not authorize a
new native attempt or certify a profile. No product code or native state changed.

ATRASO: main 1 frente sem aceite | aceite nativo pendente.
