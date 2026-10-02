# Atribuição de assistentes

Frente: autoria humana nos commits e PRs do YoungCrowHarness.
Data UTC: 2026-10-02.

Na consulta inicial, os colaboradores listados incluíam somente Matheusrpc, como administrador.
O Claude não tinha acesso ao repositório. A listagem REST de contribuidores também retornou somente
Matheusrpc, mas quatro mensagens antigas da `main` continham trailers `Co-Authored-By` para modelos Claude. São
registros de coautoria no histórico, distintos de uma permissão de acesso.

Esta mudança configura `attribution.commit` e `attribution.pr` como strings vazias no Claude,
preservando os hooks. Os guias de Claude e Codex passam a orientar a preservação da autoria humana,
sem acrescentar assistentes como coautores. README PT/EN e guia de uso foram atualizados com revisão
humanizer, preservando o design e os créditos de terceiros. A configuração segue a
[referência oficial](https://code.claude.com/docs/en/settings-reference#attribution).

Verificação local: JSON válido, atribuição vazia e todos os demais campos idênticos à versão anterior.
Essa configuração evita novas atribuições automáticas; não modifica as mensagens de commits existentes.

## Limpeza do histórico autorizada e aplicada

A base examinada foi `78b93d4930f023b9039529b7a06418506e4e1a47`. Um bundle local completo foi criado e
verificado em `.runtime/attribution-backup/before-cleanup.bundle`, junto da cópia das regras atuais.
A prévia local removeu somente as quatro linhas de coautoria Claude, preservando os textos restantes,
as identidades humanas, datas e árvores de arquivos de cada commit.

Após autorização explícita do mantenedor, a `main` foi atualizada para
`aa3ff00fc38991b4c375107bd139b1cf6e0e68ad` usando uma condição que exigia o commit remoto esperado.
Os arquivos permaneceram idênticos. Foram trocados seis identificadores de commit e removida uma
assinatura que não seria válida nos novos objetos. Autores humanos, committers e datas foram preservados.

O ruleset permaneceu ativo durante a operação. A exceção temporária foi restrita à conta Matheusrpc
e removida imediatamente após a atualização. A leitura da API confirmou `protected: true`, lista de
bypass vazia e todas as regras iguais às da cópia anterior. A branch do PR #2 foi reaplicada sobre
essa base limpa para incorporar a configuração de atribuição pelo fluxo normal de PR e testes.

Clones anteriores precisam se alinhar ao novo histórico. Antes disso, salve qualquer trabalho local;
um novo clone evita misturar as duas histórias. Não reenvie a história antiga para a `main`.

O GitHub informa que estatísticas e listas de contribuidores podem levar cerca de 24 horas para
atualizar depois de uma reescrita: [documentação](https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-a-projects-contributors#contributor-data-is-stale-after-history-changes).
