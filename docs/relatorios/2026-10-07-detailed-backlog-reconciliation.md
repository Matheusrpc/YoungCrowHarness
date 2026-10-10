# Backlog detalhado e estado da cloud

Frente: continuidade do produto e conferência do backlog recebido.

O anexo `BACKLOG-DETALHADO-2026-10-07.md` organiza as frentes com IDs, dependências,
critérios de aceite e próxima entrega. É coerente com o desenho aprovado. Sua base
é `b801bec`; o estado de alguns itens precede os incrementos locais desta sessão.
Este relatório registra a comparação, sem alterar o anexo original.

Fonte recebida: 760 linhas, 50.978 bytes, SHA-256
`62442e85ea9b52e042946e4ea07bc10be53785dcd6127574a475ef589d8842e8`.
Leitura direta do Markdown concluída; cópia exata e registro mantidos localmente.
O ingestor registrou `unsupported_source` para esse formato, com revisão nula;
não houve conversão Docling. A ausência de seleção de memória foi contornada pela
consulta direta aos relatórios e ao handoff, sem criar índice Graphify.

## Atualização dos estados

| Item | Estado sustentado pelas evidências atuais |
|---|---|
| AUD-01 | Defeito de projeção já reproduzido na base e no PR #24; correção pendente |
| AUD-02 | Catálogo com `supportedReasoningEfforts: [null]` já reproduzido; correção pendente |
| 203.2 | Admissão `isolated-egress-v1`, limites, recibo e replay implementados; despacho conserva `controller_pending` |
| 203.3 | Controlador interno implementado e testado; ligação nativa ao coordenador/reserva/recuperação pendente |
| 203.4–203.5 | Próximo núcleo de integração: plano completo A/B/A2, reserva global, identidade e recuperação |
| 203.6 | Filtro e relay existentes; fixture exercitada com relay local. Integração global e prova nativa pendentes |
| 203.7 | Fontes da fixture incluídos no Dockerfile/allowlist; controlador distribuído. Build e prova do candidato pendentes |
| 203.8–203.12 | Testes e documentação avançaram; aceites integrados, clientes, adoção e publicação continuam abertos |

Os reproduzidores de AUD-01 e AUD-02 estão preservados; a próxima correção deve
reutilizá-los e acrescentar regressões permanentes. As auditorias estão em
[base](2026-10-07-cloud-audit.md) e [PR #24](2026-10-07-pr24-cloud-audit.md).

Há ainda um defeito aberto que não aparece no anexo: **PR24-F2**, timeout de Git
na primeira leitura de ambiente, que escapa da resposta JSON sanitizada. **PR24-F1**,
criação privada do lock POSIX, já foi corrigido no
[incremento de admissão](2026-10-07-synthetic-admission.md).

O [incremento do controlador](2026-10-07-controller-channel.md) registra a última
suíte executada: 524 testes, 504 aprovados, 20 pulados e zero falhas. Essa é evidência
anterior à leitura deste anexo; não houve nova execução da suíte para esta comparação.

## Sequência preservada

1. Corrigir os três defeitos abertos com as reproduções já existentes e regressões.
2. Integrar 203.4 e 203.5 usando o controlador entregue. Persistir o plano imutável
   completo A/B/A2 antes do primeiro efeito, com identidades próprias e baseline
   restaurável; conservar operações consumidas.
3. Integrar egress, reconstruir o candidato exato, provar A/B/A2 e a matriz de falhas.
4. Provar Claude/Codex por assinatura, adoção e ambientes anunciados; fechar YC-203.
5. Avançar para fila/agentes, continuidade, QA, release/produção e aceite do produto.

Os 25 itens principais, as extensões opcionais e a separação entre três PBIs ativos
e três execuções simultâneas permanecem. O contador nativo continua em dois de três
ciclos; a comparação não consome ciclo nem autoriza novas operações externas.

## CI e limites

O anexo informa sucesso dos grupos `public-pilot`, `installer`, `adoption-windows`
e `graphify-smoke` nos runs [push](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37584603053)
e [PR](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37584633952).
Trata-se de informação recebida para o checkpoint. A API havia recusado a consulta
desta cloud; não foi feita nova verificação direta. Esses runs não cobrem os
incrementos locais posteriores.

Um revisor independente conferiu o mapeamento sem escrever no checkout. Foram usadas
`ingest-source` e `retrieve-memory`, leitura de arquivos e comparação de evidências.
Não houve mudança de código, inferência externa, Docker, commit, push, merge ou deploy.
A fonte original e a memória de ingestão permanecem locais. A identidade do projeto
foi inicializada pelo ingestor em `vault/project.json`; não foi publicada.

ATRASO: main 1 frente sem aceite | PR #24 incrementos locais não publicados.
