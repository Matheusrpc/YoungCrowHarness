# Integração e publicação de U01

Frente: filtros retomáveis por URL no exemplo Delivery Board. O mantenedor aprovou a integração
e publicação em 12/out/2026, após conferir a entrega e suas evidências.

[PR #25](https://github.com/Matheusrpc/YoungCrowHarness/pull/25) integrado em 12/out às 07:14:12 UTC,
revisão `80edd7786f3ecb13535565f5cb358ef1f983b757`. [Build e deploy Pages](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/38216618798)
concluídos com sucesso; ambiente `github-pages` confirmou o deploy às 07:14:47 UTC.
A conferência direta de manifesto, bytes e navegação no site permanece bloqueada pela rede da cloud.

U01 foi transportado para um checkout separado, baseado na main
`932b775c385b8ab9d7ff7819e00ffcc9f3f20c95`. Os cinco hashes de implementação e teste coincidem com a
[medição aprovada](../medicoes/2026-10-12-filter-url.json). O PR #24 e o checkout do executor permanecem
preservados. Documentação recebe apenas os trechos de U01; as correções de auditoria e o histórico
P06 da outra branch não fazem parte desta integração.

O [relatório de desenvolvimento](2026-10-12-filter-url.md) e sua medição são registros históricos
da cópia de origem. Seus hashes de notas não identificam as notas adaptadas à main neste checkout.
As decisões e os bytes do código aprovado permanecem os mesmos.

Validação na cópia sobre main: 11 testes Node aprovados, zero falhas/skips; 22 notas do vault,
zero problemas; 326 links/âncoras locais conferidos. Pacote gerado com os seis arquivos públicos
e manifesto. `git diff --check` passou. `public-pilot`, `installer` e `graphify-smoke` passaram no CI
de push e PR da revisão `fcbbae86d37750e3b470f1490dad69fdfa58ad62`. O ensaio do quadro passou no
Windows; a suíte geral `adoption-windows` ainda rodava no checkpoint de integração. A proteção
da main exigiu `installer` e foi respeitada, sem bypass. O workflow Pages também passou nos
testes Node, no validador do vault e no build antes de confirmar deploy.

O primeiro CI de U01 passou nos testes do quadro, vault e pacote, mas o ensaio de adoção recusou
o resultado por esperar quatro testes do modelo. U01 tem sete testes de modelo e quatro de pacote.
`smoke_public_pilot.py` agora usa uma única contagem esperada para a linha TAP exata e os recibos.
O ensaio local passou nos consumidores novo/existente, cliente `both`, com restauração e preservação
do trial e das configurações globais. Os testes da aplicação permaneceram intactos.

A main exige PR e o check `installer`, sem bypass. O workflow Pages publica automaticamente
quando a alteração dos arquivos do quadro chega à main. A conclusão do deploy precisa ser
conferida na execução do GitHub; a verificação externa compara manifesto, seis hashes, revisão
integrada e percurso dos filtros no endereço público.

Limite atual de rede: o proxy da cloud recusou `matheusrpc.github.io` com HTTP 403. O domínio foi
adicionado ao rascunho das configurações do ambiente, mantendo `api.github.com`. Aplicação depende
de salvar e publicar o ambiente. A leitura da API GitHub funciona; a leitura HTTP do site permanece
pendente. A revisão anterior do workflow Pages era
`2134134f14dc861be803173613bfd6a0d2e855e0`, run `37122731645`. O novo deploy acima está confirmado
pela API GitHub; isso não substitui a leitura do manifesto e dos bytes servidos.

Retorno: se U01 precisar ser retirado, reverter apenas seu commit integrado por um novo PR,
aguardar os checks e o deploy automático, depois verificar manifesto e site. O trabalho do executor
não participa dessa reversão. Não foi necessário acionar retorno nesta publicação.

English: the approved U01 code is isolated on main, with local tests, vault and links passing.
The executor branch and its pending changes are preserved. GitHub PR/CI/Pages are the publication
path. PR #25 is merged and Pages confirmed deployment of `80edd7786f3e`. Direct site verification
is pending the cloud network allowance. Revert only U01 through a PR
if rollback becomes necessary, then verify the resulting deployment.

Placar: 1 significa pendente; 0 significa concluído com evidência.

ATRASO: GitHub 0 | Pages 0 | verificação externa 1
