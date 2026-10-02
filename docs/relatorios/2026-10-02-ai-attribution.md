# Atribuição de assistentes

Frente: autoria humana nos commits e PRs do YoungCrowHarness.
Data UTC: 2026-10-02.

A consulta de colaboradores retornou somente Matheusrpc, como administrador. O Claude não tem
acesso ao repositório. A listagem REST de contribuidores também retornou somente Matheusrpc, mas
quatro mensagens antigas da `main` contêm trailers `Co-Authored-By` para modelos Claude. São
registros de coautoria no histórico, distintos de uma permissão de acesso.

Esta mudança configura `attribution.commit` e `attribution.pr` como strings vazias no Claude,
preservando os hooks. Os guias de Claude e Codex passam a orientar a preservação da autoria humana,
sem acrescentar assistentes como coautores. README PT/EN e guia de uso foram atualizados com revisão
humanizer, preservando o design e os créditos de terceiros. A configuração segue a
[referência oficial](https://code.claude.com/docs/en/settings-reference#attribution).

Verificação local: JSON válido, atribuição vazia e todos os demais campos idênticos à versão anterior.
Essa configuração evita novas atribuições automáticas; não modifica as mensagens de commits existentes.

## Preparação da limpeza do histórico

A base examinada foi `78b93d4930f023b9039529b7a06418506e4e1a47`. Um bundle local completo foi criado e
verificado em `.runtime/attribution-backup/before-cleanup.bundle`, junto da cópia das regras atuais.
A prévia local remove somente as quatro linhas de coautoria Claude, preservando os textos restantes,
as identidades humanas, datas e árvores de arquivos de cada commit.

Se aplicada, essa reescrita troca seis identificadores de commit e remove uma assinatura que não
seria válida nos novos objetos. Clones existentes precisarão se alinhar ao novo histórico. A proteção
da `main` continua ativa: o histórico remoto não foi reescrito nesta preparação. A aplicação exige
autorização específica para a exceção temporária de proteção e a substituição protegida por conferência
do commit remoto esperado. Depois, as regras devem voltar ao estado anterior e ser verificadas.

O GitHub informa que estatísticas e listas de contribuidores podem levar cerca de 24 horas para
atualizar depois de uma reescrita: [documentação](https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-a-projects-contributors#contributor-data-is-stale-after-history-changes).
