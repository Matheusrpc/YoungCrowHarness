# Integração e publicação de U01

Frente: filtros retomáveis por URL no exemplo Delivery Board. O mantenedor aprovou a integração
e publicação em 12/out/2026, após conferir a entrega e suas evidências.

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
e manifesto. `git diff --check` passou. O CI remoto e o deploy serão registrados abaixo após execução.

A main exige PR e o check `installer`, sem bypass. O workflow Pages publica automaticamente
quando a alteração dos arquivos do quadro chega à main. A conclusão do deploy precisa ser
conferida na execução do GitHub; a verificação externa compara manifesto, seis hashes, revisão
integrada e percurso dos filtros no endereço público.

Limite atual de rede: o proxy da cloud recusou `matheusrpc.github.io` com HTTP 403. O domínio foi
adicionado ao rascunho das configurações do ambiente, mantendo `api.github.com`. Aplicação depende
de salvar e publicar o ambiente. A leitura da API GitHub funciona; a leitura HTTP do site permanece
pendente. O último workflow Pages consultado foi `37122731645`, aprovado para a revisão
`2134134f14dc861be803173613bfd6a0d2e855e0`; essa consulta não é nova observação dos bytes servidos.

Retorno: se U01 precisar ser retirado, reverter apenas seu commit integrado por um novo PR,
aguardar os checks e o deploy automático, depois verificar manifesto e site. O trabalho do executor
não participa dessa reversão. Não foi necessário acionar retorno nesta preparação.

English: the approved U01 code is isolated on main, with local tests, vault and links passing.
The executor branch and its pending changes are preserved. GitHub PR/CI/Pages are the publication
path; direct site verification is pending the cloud network allowance. Revert only U01 through a PR
if rollback becomes necessary, then verify the resulting deployment.

Placar: 1 significa pendente; 0 significa concluído com evidência.

ATRASO: GitHub 1 | Pages 1 | verificação externa 1
