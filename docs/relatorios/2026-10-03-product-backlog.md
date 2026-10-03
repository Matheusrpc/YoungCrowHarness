# Backlog completo e próxima entrega

Frente: planejamento do produto e executor limitado. Data: 2026-10-03.

O [backlog público](../BACKLOG.md) consolida a base entregue, 25 itens obrigatórios pendentes
e quatro candidatos opcionais. Cada item pendente tem ID, dependências, aceite e estado.
A contagem não estima esforço nem percentual pronto. A referência da base é a main no commit
`979c018605700fe89e99ca2362be66fefd9eead2`, publicado pelo PR #18.

O [plano do incremento 2A](../superpowers/plans/2026-10-03-mission-runtime-adapters.md) detalha
três PBIs: preflight/compatibilidade, execução limitada com recuperação e instalação/provas.
O plano aguarda revisão do mantenedor. Sua publicação como documentação não aprova sua execução.

## Decisões de planejamento

- Preservar as quatro frentes da especificação e dividir a frente 2 em executor/adaptadores,
  fila/branches e continuidade. Cada incremento tem um resultado verificável e dependências explícitas.
- Provar primeiro um diagnóstico limitado do cliente. A entrega 2B precisa validar os perfis
  de desenvolvimento; uma resposta de modelo no diagnóstico não habilita trabalho autônomo.
- Manter o método inline já escolhido, com um escritor e revisão independente ao final da implementação.
- Conservar claude-mem, relações assistidas, sincronização contínua e pinning de marketplaces
  como candidatos separados. A transferência explícita continua no núcleo aprovado.
- Publicar o backlog em `docs/BACKLOG.md` e ligá-lo pelo README e pela memória local. Os IDs
  deste roteiro não criam missões operacionais nem alteram o backlog do futuro adotante do template.

## Verificação documental

[Medições e hashes](../medicoes/2026-10-03-product-backlog.json): 174 referências locais conferidas,
zero problemas; 25 IDs obrigatórios únicos e quatro opcionais; dependências sem ciclos;
três tarefas no próximo plano; exemplos Python com sintaxe válida e fences equilibradas.
README atualizado em PT/EN e assets preservados. Revisão de redação com humanizer.

A consulta de memória encontrou seleção ausente. A retomada usou os índices Markdown e a nota
da descoberta, sem instalar Graphify nem ampliar sua seleção. O plano foi revisto contra os
contratos de configuração, SQLite, CLI, projeções, setup e provas de clientes já existentes.

Esta entrega altera documentação. Não executou testes de produto, clientes de modelo, MCPs,
produção de adotante ou navegador. Os testes/provas descritos no plano são trabalho futuro.
A pendência de login do piloto Claude continua aberta; não houve nova tentativa de autenticação.

## Próxima ação

Revisar o plano escrito de 2A e, após aprovação, implementar YC-201–203 no método preservado.
As provas nativas exigem modelo, conexão e limites declarados antes da primeira chamada.

Este registro é o checkpoint documental anterior à integração protegida. O PR de publicação
registra o estado atual do merge; a implementação de 2A permanece pendente de revisão do plano.

ATRASO: main 1
